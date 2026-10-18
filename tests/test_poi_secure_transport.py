import socket
import ssl
import time
import unittest
from unittest.mock import Mock, patch

from poi_infrastructure.secure_transport import request
from poi_infrastructure.service import Config,POIError


class SecureTransportTests(unittest.TestCase):
    def perform(self,status=200,raw=None):
        response=Mock(status=status)
        response.getheader.side_effect=lambda key,default=None: default
        response.read.side_effect=[raw or b'{"elements":[]}',b'']
        connection=Mock()
        connection.getresponse.return_value=response
        sock=Mock()
        ctx=Mock()
        ctx.wrap_socket.return_value=Mock()
        rows=[(socket.AF_INET,socket.SOCK_STREAM,6,'',('8.8.8.8',443))]
        with patch('socket.getaddrinfo',return_value=rows) as dns,patch('socket.socket',return_value=sock), \
             patch('ssl.create_default_context',return_value=ctx),patch('http.client.HTTPSConnection',return_value=connection):
            result=request(Config(),'https://example.org/api/interpreter','query',2,time.monotonic()+5)
        self.assertEqual(dns.call_count,1)
        sock.connect.assert_called_once_with(('8.8.8.8',443))
        ctx.wrap_socket.assert_called_once_with(sock,server_hostname='example.org')
        self.assertEqual(connection.request.call_count,1)
        return result

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
