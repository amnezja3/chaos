import socket
import errno
import ssl
import time
import unittest
from unittest.mock import Mock, patch

from poi_infrastructure.secure_transport import request
from poi_infrastructure.service import Config,POIError


class SecureTransportTests(unittest.TestCase):
    def perform(self,status=200,raw=None,diagnostic=False,body_error=None):
        response=Mock(status=status)
        response.isclosed.return_value=False
        response.getheader.side_effect=lambda key,default=None: default
        response.read.side_effect=[raw or b'{"elements":[]}',b'']
        if body_error:
            response.read.side_effect=body_error
        connection=Mock()
        connection.getresponse.return_value=response
        sock=Mock()
        ctx=Mock()
        ctx.wrap_socket.return_value=Mock()
        rows=[(socket.AF_INET,socket.SOCK_STREAM,6,'',('8.8.8.8',443))]
        with patch('socket.getaddrinfo',return_value=rows) as dns,patch('socket.socket',return_value=sock), \
             patch('ssl.create_default_context',return_value=ctx),patch('http.client.HTTPSConnection',return_value=connection):
            result=request(Config(diagnostic_errors=diagnostic),'https://example.org/api/interpreter','query',2,time.monotonic()+5)
        self.assertEqual(dns.call_count,1)
        sock.connect.assert_called_once_with(('8.8.8.8',443))
        ctx.wrap_socket.assert_called_once_with(sock,server_hostname='example.org')
        self.assertEqual(connection.request.call_count,1)
        if status != 200 and diagnostic:
            response.read.assert_called_once_with(2049)
        elif status != 200:
            response.read.assert_not_called()
        return result

    def test_error_excerpt_is_bounded_and_opt_in(self):
        status, retry, detail = self.perform(status=502, raw=b'x'*2049, diagnostic=True)
        self.assertEqual(status,502)
        self.assertEqual(len(detail['body_excerpt']),2048)
        self.assertTrue(detail['body_truncated'])
        self.assertEqual(self.perform(status=502),(502,None,None))

    def test_error_body_timeout_preserves_http_status(self):
        status, retry, detail = self.perform(status=502, diagnostic=True, body_error=TimeoutError())
        self.assertEqual(status,502)
        self.assertEqual(detail['body_unavailable'],'TimeoutError')

    def test_public_dns_is_pinned_and_tls_uses_original_hostname(self):
        self.assertEqual(self.perform(),(200,None,{'elements':[]}))

    def test_redirect_not_followed(self):
        self.assertEqual(self.perform(status=302),(302,None,None))

    def test_bad_json_is_not_health_success(self):
        with self.assertRaisesRegex(POIError,'invalid_json'):
            self.perform(raw=b'<html>error</html>')

    def test_any_private_dns_answer_rejects_before_connect(self):
        rows=[(socket.AF_INET,socket.SOCK_STREAM,6,'',(ip,443)) for ip in ('8.8.8.8','127.0.0.1')]
        with patch('socket.getaddrinfo',return_value=rows),patch('socket.socket') as sock,self.assertRaisesRegex(POIError,'nonpublic'):
            request(Config(),'https://example.org/api/interpreter','query',1,time.monotonic()+5)
        sock.assert_not_called()

    def test_ipv6_unreachable_falls_back_before_single_post(self):
        rows=[(socket.AF_INET6,socket.SOCK_STREAM,6,'',('2606:4700:4700::1111',443,0,0)),
              (socket.AF_INET,socket.SOCK_STREAM,6,'',('8.8.8.8',443))]
        bad,good=Mock(),Mock()
        bad.connect.side_effect=OSError(errno.ENETUNREACH,'unreachable')
        response=Mock(status=200)
        response.isclosed.return_value=False
        response.getheader.side_effect=lambda k,default=None:default
        response.read.side_effect=[b'{"elements":[]}',b'']
        conn=Mock();conn.getresponse.return_value=response
        ctx=Mock()
        with patch('socket.getaddrinfo',return_value=rows) as dns,patch('socket.socket',side_effect=[bad,good]), \
             patch('ssl.create_default_context',return_value=ctx),patch('http.client.HTTPSConnection',return_value=conn):
            self.assertEqual(request(Config(),'https://example.org/api/interpreter','q',2,time.monotonic()+5),
                             (200,None,{'elements':[]}))
        bad.close.assert_called_once()
        good.connect.assert_called_once_with(('8.8.8.8',443))
        ctx.wrap_socket.assert_called_once_with(good,server_hostname='example.org')
        conn.request.assert_called_once()
        dns.assert_called_once()
        self.assertLessEqual(sum(s.args[0] for s in bad.settimeout.call_args_list),Config().connect_timeout)

    def test_read_timeout_does_not_retry_post_or_other_address(self):
        rows=[(socket.AF_INET,socket.SOCK_STREAM,6,'',(ip,443)) for ip in ('8.8.8.8','1.1.1.1')]
        conn=Mock();conn.getresponse.side_effect=TimeoutError('read timed out')
        with patch('socket.getaddrinfo',return_value=rows),patch('socket.socket') as sockets, \
             patch('ssl.create_default_context'),patch('http.client.HTTPSConnection',return_value=conn), \
             self.assertRaisesRegex(POIError,'http_read_timeout'):
            request(Config(),'https://example.org/api/interpreter','q',2,time.monotonic()+5)
        self.assertEqual(sockets.call_count,1)
        conn.request.assert_called_once()

    def test_exhausted_connect_budget_never_starts_another_socket(self):
        rows=[(socket.AF_INET,socket.SOCK_STREAM,6,'',(ip,443)) for ip in ('8.8.8.8','1.1.1.1')]
        clock=[0.0]
        sock=Mock()
        def timeout(*args):
            clock[0]=4.0
            raise TimeoutError('connect timed out')
        sock.connect.side_effect=timeout
        with patch('socket.getaddrinfo',return_value=rows),patch('socket.socket',return_value=sock) as sockets, \
             patch('time.monotonic',side_effect=lambda:clock[0]),patch('http.client.HTTPSConnection') as conn, \
             self.assertRaisesRegex(POIError,'connect_timeout'):
            request(Config(),'https://example.org/api/interpreter','q',2,10)
        self.assertEqual(sockets.call_count,1)
        conn.return_value.request.assert_not_called()
