"""Bounded Mapillary thumbnail adapter. No calls without explicit server gates.

Contract reference: official mapillary-python-sdk Entities API v4 documentation.
Live rights/retention remain operator gates; fixtures never grant live consent.
"""
import hashlib
import http.client
import io
import json
import math
import os
import socket
import ssl
import time
from urllib.parse import urlencode, urlsplit

from poi_infrastructure.secure_transport import public_addresses


class SourceError(ValueError):
    def __init__(self, code, retry_after=300):
        super().__init__(code)
        self.retry_after = min(86400, max(60, int(retry_after)))


def get_bytes(url, *, token=None, limit=10*1024*1024, deadline=None):
    """Reuse the game's public-DNS validation; pin TLS to the checked address.

    No proxy, redirect, implicit retries, private DNS or arbitrary caller host.
    """
    deadline = deadline or time.monotonic()+30
    parsed = urlsplit(url)
    hosts = {h.strip() for h in os.environ.get('CHAOS_CAMERA_CDN_HOSTS', '').split(',') if h.strip()}
    if (parsed.scheme != 'https' or parsed.username or parsed.password or parsed.port not in (None,443)
            or parsed.fragment or (parsed.hostname != 'graph.mapillary.com' and parsed.hostname not in hosts)
            or (token and parsed.hostname != 'graph.mapillary.com')):
        raise SourceError('source_host_denied')
    remaining = deadline-time.monotonic()
    if remaining <= 0:
        raise SourceError('source_deadline')
    addresses = public_addresses(parsed.hostname)
    family, kind, proto, sockaddr = addresses[0]
    sock = socket.socket(family, kind, proto)
    conn = http.client.HTTPSConnection(parsed.hostname, timeout=min(10, remaining))
    try:
        sock.settimeout(min(5, max(.01, deadline-time.monotonic())))
        sock.connect(sockaddr)
        conn.sock = ssl.create_default_context().wrap_socket(sock, server_hostname=parsed.hostname)
        tls = conn.sock
        headers = {'Accept-Encoding':'identity', 'User-Agent':'CHAOS/CameraStreetView'}
        if token:
            headers['Authorization'] = 'OAuth '+token
        conn.request('GET', parsed.path + ('?'+parsed.query if parsed.query else ''), headers=headers)
        response = conn.getresponse()
        if response.status != 200:
            retry = response.getheader('Retry-After', '300')
            raise SourceError('source_http_'+str(response.status), int(retry) if retry.isdigit() else 300)
        if response.getheader('Content-Encoding','identity').lower() != 'identity':
            raise SourceError('source_encoding')
        raw = bytearray()
        while True:
            remaining = deadline-time.monotonic()
            if remaining <= 0:
                raise SourceError('source_deadline')
            tls.settimeout(min(10,remaining))
            chunk = response.read(min(65536, limit+1-len(raw)))
            raw.extend(chunk)
            if len(raw)>limit:
                raise SourceError('source_byte_limit')
            if not chunk or response.isclosed():
                break
        return bytes(raw), response.getheader('Content-Type','').split(';')[0]
    finally:
        conn.close(); sock.close()


def distance(lat, lon, other_lat, other_lon):
    a,b=math.radians(lat),math.radians(other_lat)
    d=math.sin((b-a)/2)**2+math.cos(a)*math.cos(b)*math.sin(math.radians(other_lon-lon)/2)**2
    return 6371000*2*math.asin(min(1,math.sqrt(d)))


def select_images(rows, target):
    """One bounded page; direction, sequence, distance and id form stable order."""
    lat,lon=float(target['lat']),float(target.get('lng',target.get('lon')))
    candidates={}
    for raw in rows[:30]:
        try:
            coords=(raw.get('computed_geometry') or raw['geometry'])['coordinates']
            x,y=map(float,coords[:2]); metres=distance(lat,lon,y,x)
            if not (-180<=x<=180 and -90<=y<=90) or metres>100 or raw.get('is_pano') or raw.get('camera_type')=='spherical':
                continue
            image_id=str(raw['id'])
            if not image_id.isdigit() or not (raw.get('creator') or {}).get('username'):
                continue
            thumbnail=raw.get('thumb_1024_url') or raw.get('thumb_256_url')
            if not thumbnail:
                continue
            heading=raw.get('computed_compass_angle',raw.get('compass_angle'))
            heading=float(heading)%360 if heading is not None else None
            candidates[image_id]={**raw,'id':image_id,'distance_m':round(metres,2),
                'photo_lat':y,'photo_lon':x,'heading':heading,'thumbnail':thumbnail,
                'thumbnail_variant':'1024' if raw.get('thumb_1024_url') else '256'}
        except (KeyError,TypeError,ValueError,OverflowError):
            continue
    candidates=sorted(candidates.values(),key=lambda r:(r['distance_m'],r['id']))
    if not candidates:
        return []
    reference=target.get('heading')
    if reference is None:
        reference=next((r['heading'] for r in candidates if r['heading'] is not None),None)
    if reference is None:
        return candidates[:1]
    reference=float(reference)%360
    aligned=[r for r in candidates if r['heading'] is not None and abs((r['heading']-reference+180)%360-180)<=45]
    if not aligned:
        return []
    sequence=aligned[0].get('sequence')
    for r in aligned:
        r['direction_reference']=reference
        r['direction_origin']='camera' if target.get('heading') is not None else 'nearest_photo'
        r['direction_delta']=abs((r['heading']-reference+180)%360-180)
    return sorted(aligned,key=lambda r:(r['direction_delta'],r.get('sequence')!=sequence,r['distance_m'],r['id']))[:3]


def optimize(raw):
    from PIL import Image, ImageOps
    if len(raw)>10*1024*1024:
        raise SourceError('image_byte_limit')
    with Image.open(io.BytesIO(raw)) as source:
        if source.format not in ('JPEG','PNG','WEBP') or getattr(source,'n_frames',1)!=1 or source.width*source.height>20_000_000:
            raise SourceError('image_format_or_dimensions')
        image=ImageOps.exif_transpose(source).convert('RGB')
        image.thumbnail((960,540))
        output=io.BytesIO(); image.save(output,format='WEBP',quality=70)
        data=output.getvalue()
        return data,dict(width=image.width,height=image.height,format='webp',bytes=len(data),
                         sha256=hashlib.sha256(data).hexdigest(),transform_version=1,
                         changes=['exif orientation','resize max 960x540, no upscale','WebP quality 70','metadata removed'])


class MapillarySource:
    name='mapillary'

    def __init__(self, transport=get_bytes):
        self.transport=transport

    def fetch(self,target,reserve):
        token=os.environ.get('MAPILLARY_ACCESS_TOKEN','')
        if not token or os.environ.get('CHAOS_CAMERA_ACQUISITION')!='1' or not all(os.environ.get(k) for k in
                ('CHAOS_CAMERA_RIGHTS_REFERENCE','CHAOS_CAMERA_LICENSE','CHAOS_CAMERA_LICENSE_URL')):
            raise SourceError('source_policy_blocked')
        lat,lon=float(target['lat']),float(target.get('lng',target.get('lon')))
        dy=100/111320; dx=dy/max(.01,math.cos(math.radians(lat)))
        fields='id,geometry,computed_geometry,compass_angle,computed_compass_angle,captured_at,creator,sequence,is_pano,thumb_1024_url,thumb_256_url'
        query=urlencode(dict(bbox=f'{lon-dx},{lat-dy},{lon+dx},{lat+dy}',limit=30,fields=fields))
        deadline=time.monotonic()+90
        reserve(1024*1024)
        raw,mime=self.transport('https://graph.mapillary.com/images?'+query,token=token,limit=1024*1024,deadline=deadline)
        if mime not in ('application/json','application/geo+json'):
            raise SourceError('metadata_mime')
        rows=json.loads(raw).get('data',[])
        result=[]
        for row in select_images(rows,target):
            if os.environ.get('CHAOS_CAMERA_ACQUISITION')!='1':
                raise SourceError('source_policy_blocked')
            reserve(10*1024*1024)
            raw,mime=self.transport(row['thumbnail'],limit=10*1024*1024,deadline=deadline)
            if mime not in ('image/jpeg','image/png','image/webp'):
                raise SourceError('image_mime')
            data,meta=optimize(raw)
            result.append((data,{**meta,'image_id':row['id'],'sequence_id':row.get('sequence'),
                'source':'Mapillary','author':row['creator']['username'],'captured_at':row.get('captured_at'),
                'source_url':'https://www.mapillary.com/app/?pKey='+row['id'],
                'license':os.environ.get('CHAOS_CAMERA_LICENSE',''),
                'license_url':os.environ.get('CHAOS_CAMERA_LICENSE_URL',''),
                'rights_reference':os.environ.get('CHAOS_CAMERA_RIGHTS_REFERENCE',''),
                **{k:row.get(k) for k in ('photo_lat','photo_lon','distance_m','heading','direction_reference','direction_origin','direction_delta','thumbnail_variant')}}))
        return result
