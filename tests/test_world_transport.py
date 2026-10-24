from dataclasses import replace
import os
import socket
import time
import unittest
from unittest.mock import Mock, patch

from poi_infrastructure.secure_transport import request
from poi_infrastructure.service import Config, POIError
from poi_infrastructure.world_adapters import plan_geoapify, plan_maplark
from poi_infrastructure.world_contract import ContractError


class WorldTransportTests(unittest.TestCase):
    def test_geoapify_uses_structured_post_with_header_secret(self):
        import json
        plan=plan_geoapify(52,21,300,categories=('commercial',),limit=100,offset=100)
        response=Mock(status=200)
        response.getheader.side_effect=lambda key,default=None: default
        response.read.return_value=b'{"type":"FeatureCollection","features":[]}'
        response.isclosed.return_value=True
        connection=Mock();connection.getresponse.return_value=response
        context=Mock();context.wrap_socket.return_value=Mock()
        rows=[(socket.AF_INET,socket.SOCK_STREAM,6,'',('8.8.8.8',443))]
        with patch.dict(os.environ,CHAOS_GEOAPIFY_API_KEY='synthetic-key'),patch('socket.getaddrinfo',return_value=rows),\
                patch('socket.socket'),patch('ssl.create_default_context',return_value=context),\
                patch('http.client.HTTPSConnection',return_value=connection):
            result=request(Config(),plan.endpoint,'',25,time.monotonic()+35,feature_plan=plan)
        args,kwargs=connection.request.call_args
        self.assertEqual(args,('POST','/v2/places'))
        self.assertEqual(kwargs['headers']['x-api-key'],'synthetic-key')
        body=json.loads(kwargs['body'])
        self.assertEqual(body['offset'],100)
        self.assertEqual(body['filter'],dict(type='circle',lon=21.,lat=52.,radius=300.))
        self.assertNotIn('synthetic-key',str(result))
        self.assertNotIn('synthetic-key',str(body))

    def test_wire_allows_only_reconstructed_plans(self):
        plans = [plan_maplark(52.23198765, 21.00671234, 300),
                 plan_geoapify(52.23198765, 21.00671234, 300, categories=('commercial',))]
        with patch.dict(os.environ, {'CHAOS_MAPLARK_API_KEY': 'synthetic-key', 'CHAOS_GEOAPIFY_API_KEY': 'synthetic-key'}):
            for plan in plans:
                path, headers = plan.authenticated_wire()
                self.assertNotIn('synthetic-key', path)
                self.assertEqual(len(headers), 1)
                for bad in [replace(plan, endpoint='https://127.0.0.1/v3/osm_features'),
                            replace(plan, secret_ref='SECRET_KEY'),
                            replace(plan, params=plan.params + (('apiKey', 'evil'),)),
                            replace(plan, params=plan.params + (plan.params[0],))]:
                    with self.assertRaisesRegex(ContractError, 'request_plan_not_allowlisted'):
                        bad.authenticated_wire()

    def test_secret_missing_or_header_injection_stops_before_dns(self):
        plan = plan_maplark(52, 21, 300)
        for value in ('', 'key\r\nHost: localhost'):
            with patch.dict(os.environ, {'CHAOS_MAPLARK_API_KEY': value}), \
                    patch('socket.getaddrinfo') as dns, self.assertRaises(POIError):
                request(Config(), plan.endpoint, '', 25, time.monotonic()+35, feature_plan=plan)
            dns.assert_not_called()

    def test_pinned_tls_get_preserves_headers_and_redacts_error_body(self):
        plan = plan_maplark(52, 21, 300)
        for status in (200, 403, 302):
            response = Mock(status=status)
            values = {'X-Returned': '0', 'X-Has-More': 'false', 'X-Usage-Units-Charged': '5'}
            response.getheader.side_effect = lambda key, default=None: values.get(key, default)
            response.read.side_effect = [b'{"type":"FeatureCollection","features":[]}']
            response.isclosed.return_value = True
            connection = Mock(); connection.getresponse.return_value = response
            tls = Mock(); context = Mock(); context.wrap_socket.return_value = tls
            rows = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('8.8.8.8', 443))]
            with patch.dict(os.environ, {'CHAOS_MAPLARK_API_KEY': 'synthetic-key'}), \
                    patch('socket.getaddrinfo', return_value=rows) as dns, \
                    patch('socket.socket'), patch('ssl.create_default_context', return_value=context), \
                    patch('http.client.HTTPSConnection', return_value=connection):
                result = request(Config(diagnostic_errors=True), plan.endpoint, '', 25,
                                 time.monotonic()+35, feature_plan=plan)
            self.assertEqual(dns.call_count, 1)
            self.assertEqual(context.wrap_socket.call_args.kwargs['server_hostname'], 'api.maplark.com')
            args, kwargs = connection.request.call_args
            self.assertEqual(args[0], 'GET')
            self.assertNotIn('synthetic-key', args[1])
            self.assertEqual(kwargs['headers']['Authorization'], 'Bearer synthetic-key')
            self.assertNotIn('synthetic-key', str(result))
            self.assertEqual(result[2]['response_headers']['X-Usage-Units-Charged'], '5')
            if status != 200:
                response.read.assert_not_called()
                self.assertIsNone(result[2]['body'])
            self.assertEqual(connection.request.call_count, 1)
