"""Fixed provider endpoints; server-side code exchange and verified subjects only."""
import base64
from datetime import datetime, timezone
import hashlib
import re
import secrets
import time
from urllib.parse import urlencode
import requests
from .service import IdentityError

STEAM = 'https://steamcommunity.com/openid/login'
ENDPOINTS = {
    'google': ('https://accounts.google.com/o/oauth2/v2/auth','https://oauth2.googleapis.com/token','openid email'),
    'github': ('https://github.com/login/oauth/authorize','https://github.com/login/oauth/access_token','read:user user:email'),
    'discord': ('https://discord.com/oauth2/authorize','https://discord.com/api/oauth2/token','identify email'),
}


def http(method, url, **kwargs):
    # Never follow a redirect carrying an Authorization header or client secret.
    try:
        response = requests.request(method,url,timeout=(3,12),allow_redirects=False,**kwargs)
        if response.status_code != 200 or len(response.content) > 256000:
            raise IdentityError('provider_unavailable')
        return response
    except requests.RequestException:
        raise IdentityError('provider_unavailable') from None


def authorization(provider, state, origin):
    data = dict(nonce=secrets.token_urlsafe(32), verifier=secrets.token_urlsafe(48))
    if provider.name == 'steam':
        data['return_to'] = provider.callback + '?' + urlencode({'state':state})
        args = {'openid.ns':'http://specs.openid.net/auth/2.0','openid.mode':'checkid_setup',
                'openid.return_to':data['return_to'],'openid.realm':origin+'/',
                'openid.identity':'http://specs.openid.net/auth/2.0/identifier_select',
                'openid.claimed_id':'http://specs.openid.net/auth/2.0/identifier_select'}
        return STEAM+'?'+urlencode(args), data
    args = dict(client_id=provider.client_id,redirect_uri=provider.callback,response_type='code',
                scope=ENDPOINTS[provider.name][2],state=state)
    if provider.name in ('google','github'):
        args.update(code_challenge_method='S256',code_challenge=base64.urlsafe_b64encode(
            hashlib.sha256(data['verifier'].encode()).digest()).rstrip(b'=').decode())
    if provider.name == 'google':
        args['nonce'] = data['nonce']
    return ENDPOINTS[provider.name][0]+'?'+urlencode(args), data


def verify_google(token, provider, flow):
    from authlib.jose import JsonWebToken
    from authlib.oidc.core import CodeIDToken
    keys = http('GET','https://www.googleapis.com/oauth2/v3/certs').json()
    try:
        claims = JsonWebToken(['RS256']).decode(token['id_token'],keys,claims_cls=CodeIDToken,
            claims_options={'iss':{'essential':True,'values':['https://accounts.google.com','accounts.google.com']},
                            'aud':{'essential':True,'value':provider.client_id},
                            'exp':{'essential':True},'iat':{'essential':True},'sub':{'essential':True}},
            claims_params={'nonce':flow['nonce'],'client_id':provider.client_id,'access_token':token['access_token']})
        claims.validate(leeway=30)
        if (claims.get('nonce') != flow['nonce'] or not isinstance(claims.get('sub'),str)
                or not 1 <= len(claims['sub']) <= 255):
            raise ValueError()
        return dict(provider='google',subject=claims['sub'],email=claims.get('email'),
                    email_verified=claims.get('email_verified') is True)
    except Exception:
        raise IdentityError('invalid_provider_response') from None


def verify_steam(args, flow):
    fields = ('op_endpoint','claimed_id','identity','return_to','response_nonce','assoc_handle')
    signed = set(args.get('openid.signed','').split(','))
    claimed = args.get('openid.claimed_id','')
    if (args.get('openid.ns') != 'http://specs.openid.net/auth/2.0'
            or args.get('openid.mode') != 'id_res' or args.get('openid.op_endpoint') != STEAM
            or args.get('openid.return_to') != flow['return_to']
            or args.get('openid.identity') != claimed or not set(fields).issubset(signed)
            or not re.fullmatch(r'https://steamcommunity\.com/openid/id/[0-9]{17}',claimed)):
        raise IdentityError('invalid_provider_response')
    try:
        stamp = datetime.strptime(args['openid.response_nonce'][:20],'%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc).timestamp()
        if not -30 <= time.time()-stamp <= 600:
            raise ValueError()
    except (KeyError, ValueError):
        raise IdentityError('invalid_provider_response') from None
    body = {k:v for k,v in args.items() if k.startswith('openid.')}
    body['openid.mode'] = 'check_authentication'
    lines = dict(line.split(':',1) for line in http('POST',STEAM,data=body).text.splitlines() if ':' in line)
    if lines.get('is_valid') != 'true':
        raise IdentityError('invalid_provider_response')
    return dict(provider='steam',subject=claimed.rsplit('/',1)[1],email=None,email_verified=False)


def resolve(provider, args, flow):
    if args.get('error') or args.get('openid.mode') == 'cancel':
        raise IdentityError('provider_cancelled')
    if provider.name == 'steam':
        return verify_steam(args,flow)
    code = args.get('code','')
    if not code or len(code)>8192:
        raise IdentityError('invalid_provider_response')
    payload = dict(grant_type='authorization_code',code=code,redirect_uri=provider.callback,
                   client_id=provider.client_id,client_secret=provider.client_secret)
    if provider.name in ('google','github'):
        payload['code_verifier'] = flow['verifier']
    token = http('POST',ENDPOINTS[provider.name][1],data=payload,headers={'Accept':'application/json'}).json()
    access = token.get('access_token')
    if not isinstance(access,str) or not access or token.get('token_type','').lower() != 'bearer':
        raise IdentityError('invalid_provider_response')
    if provider.name == 'google':
        return verify_google(token,provider,flow)
    headers = {'Authorization':'Bearer '+access,'Accept':'application/json','User-Agent':'CHAOS-Identity-Gateway'}
    url = 'https://api.github.com/user' if provider.name == 'github' else 'https://discord.com/api/users/@me'
    user = http('GET',url,headers=headers).json()
    subject = str(user.get('id',''))
    if not re.fullmatch('[0-9]{1,24}',subject):
        raise IdentityError('invalid_provider_response')
    email, verified = user.get('email'), user.get('verified') is True
    if provider.name == 'github':
        addresses = http('GET','https://api.github.com/user/emails',headers=headers).json()
        primary = next((item for item in addresses if item.get('primary') is True and item.get('verified') is True), {})
        email, verified = primary.get('email'), bool(primary)
    return dict(provider=provider.name,subject=subject,email=email,email_verified=verified)
