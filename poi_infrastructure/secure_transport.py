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


def request(config, endpoint, query, timeout, deadline):
    host = endpoint_host(endpoint)
    addresses = public_addresses(host)
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
        if time.monotonic() >= deadline:
            raise UpstreamUnavailable('deadline')
        connection.sock.settimeout(min(timeout,max(.01,deadline-time.monotonic())))
        body = urlencode({'data':query}).encode()
        stage = 'http_write'
        connection.request('POST',urlsplit(endpoint).path,body=body,headers={
            'Content-Type':'application/x-www-form-urlencoded','Accept':'application/json',
            'Accept-Encoding':'identity','User-Agent':'CHAOS/POI-v160 (+https://chaos.re; year2108@chaos.re)'})
        stage = 'http_read'
        response = connection.getresponse()
        if response.status != 200:
            return response.status,response.getheader('Retry-After'),None
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
            if len(raw)>config.max_response:
                raise POIError('response_limit')
        try:
            return 200,None,json.loads(raw)
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
