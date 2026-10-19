"""Compare the real encoded POST of both transports on a loopback fixture."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import socket
import json
import threading
import time
import unittest
from unittest.mock import Mock, patch
from urllib.parse import parse_qs

import requests
from poiFetchClass import POIFetcher
from poi_infrastructure.secure_transport import request
from poi_infrastructure.service import Config


class WireContractTests(unittest.TestCase):
    def test_form_body_host_and_path_match_requests(self):
        self.compare(b'{"elements":[]}')

    def test_multichunk_response_completes_before_socket_is_closed(self):
        self.compare(b'{"elements":[],"padding":"' + b'x'*3000 + b'"}')

    def compare(self, body):
        captured = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                captured.append((self.path, self.headers,
                                 self.rfile.read(int(self.headers['Content-Length']))))
                self.send_response(200)
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            path = '/osm/tools/overpass/api/interpreter'
            query = POIFetcher(tag_filters=['shop', 'amenity', 'atm=yes'])._build_query(52.2319,21.0067)
            with requests.Session() as session:
                session.trust_env = False
                response = session.post(f'http://127.0.0.1:{server.server_port}{path}',
                                        data={'data':query}, headers={'Host':'example.org'}, timeout=3)
                self.assertEqual(response.status_code,200)
            # Only the fixture bypasses TLS/public DNS. The real http.client
            # serialization and socket I/O remain intact for wire comparison.
            context = Mock()
            context.wrap_socket.side_effect = lambda sock, **kwargs: sock
            addresses = [(socket.AF_INET, socket.SOCK_STREAM, 6, server.server_address)]
            trace = {}
            with patch('poi_infrastructure.secure_transport.public_addresses',return_value=addresses), \
                 patch('ssl.create_default_context',return_value=context):
                self.assertEqual(request(Config(), 'https://example.org'+path,
                                         query,3,time.monotonic()+5, trace=trace), (200,None,json.loads(body)))
            self.assertEqual(trace['stage'],'complete')
            self.assertEqual(trace['bytes_received'],len(body))
            self.assertEqual(trace['http_status'],200)
            self.assertGreaterEqual(trace['body_complete_seconds'],trace['headers_seconds'])
            self.assertEqual(len(captured),2)
            old,new = captured
            self.assertEqual(old[0],new[0])
            self.assertEqual(old[2],new[2])
            self.assertEqual(parse_qs(new[2].decode())['data'],[query])
            for header in ('Host','Content-Length','Content-Type'):
                self.assertEqual(old[1][header],new[1][header])
            self.assertIsNone(new[1]['Transfer-Encoding'])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(3)


if __name__ == '__main__':
    unittest.main()
