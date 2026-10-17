from datetime import datetime,timezone
import time
import unittest
from unittest.mock import patch,Mock
from urllib.parse import parse_qs,urlsplit
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from authlib.jose import JsonWebToken
from authlib.jose import JsonWebKey
from identity_gateway import providers
from identity_gateway.config import ProviderConfig
from identity_gateway.service import IdentityError


class ProviderProtocolTests(unittest.TestCase):
    def test_google_signed_claims_nonce_issuer_audience_and_algorithm(self):
        private=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        pem=private.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption())
        public=private.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo)
        cfg=ProviderConfig('google',True,'https://chaos.re/auth/google/callback','client','secret')
        claims=dict(iss='https://accounts.google.com',aud='client',sub='subject',exp=int(time.time())+120,
                    iat=int(time.time()),nonce='nonce',email='user@example.test',email_verified=True)
        def verify(payload):
            token=JsonWebToken(['RS256']).encode({'alg':'RS256'},payload,pem).decode()
            with patch.object(providers,'http',return_value=Mock(json=lambda: public)):
                return providers.verify_google({'id_token':token,'access_token':'access'},cfg,{'nonce':'nonce'})
        self.assertEqual(verify(claims)['subject'],'subject')
        for override in ({'nonce':'wrong'},{'iss':'https://evil.test'},{'aud':'other'},{'exp':1},{'sub':''}):
            with self.subTest(override=override), self.assertRaises(IdentityError):
                verify({**claims,**override})
        with patch.object(providers,'http',return_value=Mock(json=lambda:public)),self.assertRaises(IdentityError):
            providers.verify_google({'id_token':'eyJhbGciOiJub25lIn0.e30.','access_token':'access'},cfg,{'nonce':'nonce'})
        attacker=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        attacker_pem=attacker.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption())
        injected=JsonWebKey.import_key(attacker_pem).as_dict(is_private=False)
        forged=JsonWebToken(['RS256']).encode({'alg':'RS256','jwk':injected},claims,attacker_pem).decode()
        with patch.object(providers,'http',return_value=Mock(json=lambda:public)),self.assertRaises(IdentityError):
            providers.verify_google({'id_token':forged,'access_token':'access'},cfg,{'nonce':'nonce'})

    def test_pkce_and_fixed_callback(self):
        for name in ('google','github'):
            cfg=ProviderConfig(name,True,'https://chaos.re/auth/'+name+'/callback','client','secret')
            url,flow=providers.authorization(cfg,'state','https://chaos.re')
            query=parse_qs(urlsplit(url).query)
            self.assertEqual(query['code_challenge_method'],['S256'])
            self.assertEqual(query['state'],['state'])
            self.assertNotIn('secret',url)
            self.assertNotIn(flow['verifier'],url)

    def test_steam_signed_return_and_server_verification(self):
        cfg=ProviderConfig('steam',True,'https://chaos.re/auth/steam/callback')
        _,flow=providers.authorization(cfg,'state','https://chaos.re')
        args={'openid.ns':'http://specs.openid.net/auth/2.0','openid.mode':'id_res',
              'openid.op_endpoint':providers.STEAM,'openid.return_to':flow['return_to'],
              'openid.identity':'https://steamcommunity.com/openid/id/76561198000000000',
              'openid.claimed_id':'https://steamcommunity.com/openid/id/76561198000000000',
              'openid.response_nonce':datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')+'nonce',
              'openid.assoc_handle':'assoc','openid.signed':'op_endpoint,claimed_id,identity,return_to,response_nonce,assoc_handle'}
        with patch.object(providers,'http',return_value=Mock(text='is_valid:true\n')) as call:
            self.assertEqual(providers.verify_steam(args,flow)['subject'],'76561198000000000')
            self.assertEqual(call.call_args.args,('POST',providers.STEAM))
            for override in ({'openid.return_to':'https://evil.test'},{'openid.signed':'identity'},
                             {'openid.op_endpoint':'http://127.0.0.1'},{'openid.response_nonce':'old'}):
                with self.assertRaises(IdentityError):providers.verify_steam({**args,**override},flow)
        with patch.object(providers,'http',return_value=Mock(text='is_valid:false\n')),self.assertRaises(IdentityError):
            providers.verify_steam(args,flow)

    def test_discord_and_github_server_identity_no_unverified_email(self):
        for name in ('discord','github'):
            cfg=ProviderConfig(name,True,'https://chaos.re/auth/'+name+'/callback','client','secret')
            replies=[Mock(json=lambda:{'access_token':'access','token_type':'Bearer'}),
                     Mock(json=lambda:{'id':123,'email':'private@example.test','verified':False})]
            if name=='github':replies.append(Mock(json=lambda:[{'email':'private@example.test','primary':True,'verified':False}]))
            with patch.object(providers,'http',side_effect=replies):
                result=providers.resolve(cfg,{'code':'code'},{'verifier':'verifier'})
            self.assertEqual(result['subject'],'123')
            self.assertFalse(result['email_verified'])

    def test_http_no_redirects_and_timeout(self):
        with patch.object(providers.requests,'request',return_value=Mock(status_code=302,content=b'')) as call:
            with self.assertRaises(IdentityError):providers.http('POST','https://fixed.test',data={})
            self.assertFalse(call.call_args.kwargs['allow_redirects'])
            self.assertEqual(call.call_args.kwargs['timeout'],(3,12))
