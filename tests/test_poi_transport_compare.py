import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
from urllib.parse import urlencode

from tools.poi_transport_compare import curl_request, python_child
from poi_infrastructure.service import UpstreamUnavailable


class CompareTests(unittest.TestCase):
    def test_curl_pin_wire_body_limits_and_summary(self):
        query = '[out:json];node(1);out;\n'
        def run(command, **kwargs):
            self.assertIn('--http1.1',command)
            self.assertEqual(command[command.index('--resolve')+1],'example.org:443:8.8.8.8')
            self.assertEqual(command[command.index('--max-time')+1],'35')
            self.assertNotIn('--retry',command)
            bodypath=command[command.index('--data-binary')+1][1:]
            self.assertEqual(Path(bodypath).read_bytes(),urlencode({'data':query}).encode())
            Path(command[command.index('-o')+1]).write_text('{"elements":[]}',encoding='utf-8')
            Path(command[command.index('-D')+1]).write_text('HTTP/1.1 200 OK\n',encoding='utf-8')
            return Mock(returncode=0,stderr='',stdout=json.dumps(dict(http_code=200,remote_ip='8.8.8.8',time_total=1)))
        with patch('tools.poi_transport_compare.subprocess.run',side_effect=run):
            result=curl_request('https://example.org/api/interpreter',query,'8.8.8.8')
        self.assertTrue(result['validated'])
        self.assertEqual(result['elements'],0)

    def test_python_timeout_keeps_stage_and_ip(self):
        pipe=Mock()
        def fail(*args, **kwargs):
            kwargs['trace'].update(stage='waiting_headers',remote_ip='8.8.8.8')
            raise UpstreamUnavailable('http_read_timeout')
        with patch('tools.poi_transport_compare.request',side_effect=fail):
            python_child(pipe,'https://example.org/api/interpreter','q','8.8.8.8',100)
        result=pipe.send.call_args.args[0]
        self.assertEqual(result['error'],'http_read_timeout')
        self.assertEqual(result['trace']['stage'],'waiting_headers')
        pipe.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()
