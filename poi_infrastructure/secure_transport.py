"""HTTPS transport pinned to checked public DNS addresses; no env proxy/redirect."""
import http.client
import errno
import ipaddress
import json
import socket
import ssl
import time
from urllib.parse import urlencode, urlsplit

from .providers import endpoint_host
from .service import POIError, UpstreamUnavailable


def public_addresses(host):
    try:
        rows = socket.getaddrinfo(host,443,type=socket.SOCK_STREAM)
    except OSError as exc:
        raise UpstreamUnavailable('dns_failed') from exc
    addresses = []
    for family, kind, proto, _, sockaddr in rows:
        address = ipaddress.ip_address(sockaddr[0])
        if (not address.is_global or address.is_multicast or address.is_reserved
                or getattr(address,'ipv4_mapped',None) is not None):
            raise POIError('provider_nonpublic_address')
        addresses.append((family,kind,proto,sockaddr))
    if not addresses:
        raise UpstreamUnavailable('dns_empty')
    return addresses


def request(config, endpoint, query, timeout, deadline, *, pinned_ip=None, trace=None, feature_plan=None):
    started = time.monotonic()
    def mark(stage, **fields):
        if trace is not None:
            trace.update(stage=stage, seconds=round(time.monotonic()-started, 4), **fields)
    wire_headers = {'Content-Type':'application/x-www-form-urlencoded','Accept':'application/json',
                    'Accept-Encoding':'identity','User-Agent':'CHAOS/POI-v160 (+https://chaos.re; year2108@chaos.re)'}
    method, path, body = 'POST', urlsplit(endpoint).path, urlencode({'data':query}).encode()
    if feature_plan is None:
        host = endpoint_host(endpoint)
    else:
        from .world_adapters import RequestPlan
        from .world_contract import ContractError
        if not isinstance(feature_plan, RequestPlan) or endpoint != feature_plan.endpoint:
            raise POIError('request_plan_not_allowlisted')
        try:
            path, auth_headers = feature_plan.authenticated_wire()
        except ContractError as exc:
            raise POIError(str(exc)) from None
        host = urlsplit(endpoint).hostname
        method, body = 'GET', None
        wire_headers.update(auth_headers)
        wire_headers['Accept'] = 'application/geo+json,application/json'
        if endpoint == 'https://api.geoapify.com/v2/places':
            # Official POST contract supports x-api-key: never put secrets in URLs.
            params = dict(feature_plan.params)
            lon,lat,radius = map(float,params['filter'].split(':',1)[1].split(','))
            method,path = 'POST','/v2/places'
            body = json.dumps(dict(categories=params['categories'].split(','),
                filter=dict(type='circle',lon=lon,lat=lat,radius=radius),
                limit=int(params['limit']),offset=int(params['offset']))).encode()
            wire_headers['Content-Type'] = 'application/json'
    mark('dns')
    addresses = public_addresses(host)
    if pinned_ip is not None:
        # Diagnostic pinning is restricted to this hostname's validated DNS set.
        addresses = [row for row in addresses if row[3][0] == pinned_ip]
        if not addresses:
            raise POIError('pinned_ip_not_in_public_dns')
    remaining = deadline-time.monotonic()
    if remaining <= 0:
        raise UpstreamUnavailable('deadline')
    connection = http.client.HTTPSConnection(host,443,timeout=min(timeout,remaining))
    sock = None
    stage = 'connect'
    try:
        # Address fallback is allowed only before sending any HTTP request.
        # All DNS answers were validated above; no second resolution or proxy.
        connect_deadline = min(deadline,time.monotonic()+config.connect_timeout)
        candidates = addresses[:4]
        for index,(family,kind,proto,sockaddr) in enumerate(candidates):
            available = connect_deadline-time.monotonic()
            if available <= 0:
                raise UpstreamUnavailable('connect_timeout')
            try:
                sock = socket.socket(family,kind,proto)
                sock.settimeout(available/(len(candidates)-index))
                sock.connect(sockaddr)
                mark('tcp_connected', remote_ip=sockaddr[0], tcp_seconds=round(time.monotonic()-started,4))
                break
            except OSError as exc:
                if sock:
                    sock.close()
                    sock = None
                if index+1 == len(candidates):
                    code = ('connect_timeout' if isinstance(exc,TimeoutError) else
                            'connect_unreachable' if exc.errno in (errno.ENETUNREACH,errno.EHOSTUNREACH) else
                            'connect_refused' if exc.errno == errno.ECONNREFUSED else 'connect_failed')
                    raise UpstreamUnavailable(code) from exc
        stage = 'tls'
        remaining = deadline-time.monotonic()
        if remaining <= 0:
            raise UpstreamUnavailable('deadline')
        sock.settimeout(min(config.connect_timeout,remaining))
        connection.sock = ssl.create_default_context().wrap_socket(sock,server_hostname=host)
        tls_sock = connection.sock
        mark('tls_connected', tls_seconds=round(time.monotonic()-started,4))
        if time.monotonic() >= deadline:
            raise UpstreamUnavailable('deadline')
        connection.sock.settimeout(min(timeout,max(.01,deadline-time.monotonic())))
        stage = 'http_write'
        connection.request(method,path,body=body,headers=wire_headers)
        stage = 'http_read'
        mark('waiting_headers')
        response = connection.getresponse()
        feature_headers = {name: response.getheader(name) for name in (
            'X-Returned', 'X-Has-More', 'X-Next-Cursor', 'X-Usage-Units-Charged')
            if response.getheader(name) is not None} if feature_plan is not None else None
        def result(status, retry, data):
            if feature_plan is not None:
                return status, retry, {'response_headers': feature_headers, 'body': data}
            return status, retry, data
        mark('reading_body', http_status=response.status, headers_seconds=round(time.monotonic()-started,4))
        if response.status != 200:
            if config.diagnostic_errors and feature_plan is None:
                detail = {'content_type': str(response.getheader('Content-Type', ''))[:200]}
                # Opt-in CLI diagnostics only; never follow redirects or read an
                # unbounded error page. Preserve the HTTP status on body failure.
                try:
                    remaining = deadline-time.monotonic()
                    if remaining <= 0:
                        raise TimeoutError()
                    tls_sock.settimeout(min(2, remaining))
                    if response.getheader('Content-Encoding', 'identity').lower() != 'identity':
                        detail['body_unavailable'] = 'unsupported_content_encoding'
                    else:
                        raw = response.read(2049)
                        detail['body_excerpt'] = ''.join(
                            c if c.isprintable() or c in '\n\t' else ' '
                            for c in raw[:2048].decode('utf-8', errors='replace'))
                        detail['body_truncated'] = len(raw) > 2048
                except (OSError, http.client.HTTPException) as exc:
                    detail['body_unavailable'] = type(exc).__name__
                return response.status,response.getheader('Retry-After'),detail
            return result(response.status,response.getheader('Retry-After'),None)
        if response.getheader('Content-Encoding','identity').lower() != 'identity':
            raise POIError('unsupported_content_encoding')
        raw = bytearray()
        while True:
            if time.monotonic() >= deadline:
                raise UpstreamUnavailable('deadline')
            # getresponse() may detach connection.sock for Connection: close;
            # the response still owns the file stream over this TLS socket.
            tls_sock.settimeout(min(timeout,max(.01,deadline-time.monotonic())))
            chunk = response.read(1024)
            if not chunk:
                break
            raw.extend(chunk)
            mark('reading_body', bytes_received=len(raw))
            if len(raw)>config.max_response:
                raise POIError('response_limit')
            # HTTPResponse closes its file after consuming Content-Length.
            # With Connection: close this also closes the detached TLS socket;
            # another settimeout on that socket would reject a complete 200.
            if response.isclosed():
                break
        try:
            data = json.loads(raw)
            mark('complete', body_complete_seconds=round(time.monotonic()-started,4))
            return result(200,None,data)
        except (ValueError,UnicodeError) as exc:
            raise POIError('invalid_json') from exc
    except ssl.SSLError as exc:
        raise POIError('tls_failed') from exc
    except TimeoutError as exc:
        raise UpstreamUnavailable(stage+'_timeout') from exc
    except (OSError,http.client.HTTPException) as exc:
        raise UpstreamUnavailable(stage+'_failed') from exc
    finally:
        connection.close()
        if sock:
            sock.close()
