"""Server-only configuration. Never serialize secrets into status or templates."""
from dataclasses import dataclass, field
import os
from urllib.parse import urlsplit

PROVIDERS = ('google', 'discord', 'github', 'steam')


def flag(env, name):
    value = env.get(name, '0').strip().lower()
    if value not in ('0', '1', 'false', 'true'):
        raise ValueError('invalid_flag:' + name)
    return value in ('1', 'true')


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    enabled: bool
    callback: str
    client_id: str = field(default='', repr=False)
    client_secret: str = field(default='', repr=False)

    @property
    def configured(self):
        return self.name == 'steam' or bool(self.client_id and self.client_secret)

    def status(self):
        return dict(provider=self.name, enabled=self.enabled,
                    configured=self.configured, callback=self.callback)


@dataclass(frozen=True)
class MailConfig:
    mode: str = 'disabled'
    host: str = field(default='', repr=False)
    port: int = 587
    sender: str = field(default='', repr=False)
    username: str = field(default='', repr=False)
    password: str = field(default='', repr=False)
    tls: str = 'starttls'

    @property
    def configured(self):
        return self.mode == 'smtp' and bool(self.host and self.sender)


@dataclass(frozen=True)
class GatewayConfig:
    origin: str
    enabled: bool
    registration_enabled: bool
    linking_enabled: bool
    providers: tuple
    mail: MailConfig
    intent_ttl_seconds: int = 600
    registration_ttl_seconds: int = 1800
    reauth_ttl_seconds: int = 300
    email_token_ttl_seconds: int = 1800

    def status(self):
        # Configuration readiness is NOT an assertion that a provider works live.
        return dict(enabled=self.enabled, registration_enabled=self.registration_enabled,
                    linking_enabled=self.linking_enabled,
                    providers=[provider.status() for provider in self.providers],
                    mail=dict(mode=self.mail.mode, configured=self.mail.configured))


def load_config(env=None, *, testing=False):
    env = os.environ if env is None else env
    origin = env.get('CHAOS_IDENTITY_PUBLIC_ORIGIN', 'https://chaos.re').strip().rstrip('/')
    url = urlsplit(origin)
    # Accessing port validates its syntax/range; backslashes are interpreted
    # inconsistently by URL consumers and must never enter callback URLs.
    try:
        port = url.port
    except ValueError:
        raise ValueError('invalid_identity_public_origin') from None
    local = testing and url.scheme == 'http' and url.hostname in ('localhost', '127.0.0.1')
    if (not url.hostname or (url.scheme != 'https' and not local) or url.username
            or url.password or url.path or url.query or url.fragment or '\\' in origin
            or port == 0 or any(c.isspace() for c in origin)):
        raise ValueError('invalid_identity_public_origin')
    providers = tuple(ProviderConfig(
        name=name, enabled=flag(env, f'CHAOS_IDENTITY_{name.upper()}_ENABLED'),
        callback=f'{origin}/auth/{name}/callback',
        client_id=env.get(f'CHAOS_IDENTITY_{name.upper()}_CLIENT_ID', '').strip(),
        client_secret=env.get(f'CHAOS_IDENTITY_{name.upper()}_CLIENT_SECRET', '').strip(),
    ) for name in PROVIDERS)
    mode = env.get('CHAOS_IDENTITY_MAIL_MODE', 'disabled').strip()
    if mode not in ('disabled', 'smtp', 'mock') or (mode == 'mock' and not testing):
        raise ValueError('invalid_identity_mail_mode')
    tls = env.get('CHAOS_IDENTITY_SMTP_TLS', 'starttls')
    if tls not in ('starttls', 'ssl'):
        raise ValueError('identity_smtp_tls_required')
    try:
        port = int(env.get('CHAOS_IDENTITY_SMTP_PORT', '587'))
    except ValueError:
        raise ValueError('invalid_identity_smtp_port') from None
    if not 1 <= port <= 65535:
        raise ValueError('invalid_identity_smtp_port')
    mail = MailConfig(mode, env.get('CHAOS_IDENTITY_SMTP_HOST', '').strip(), port,
                      env.get('CHAOS_IDENTITY_MAIL_FROM', '').strip(),
                      env.get('CHAOS_IDENTITY_SMTP_USERNAME', ''),
                      env.get('CHAOS_IDENTITY_SMTP_PASSWORD', ''), tls)
    return GatewayConfig(origin, flag(env, 'CHAOS_IDENTITY_ENABLED'),
                         flag(env, 'CHAOS_IDENTITY_REGISTRATION_ENABLED'),
                         flag(env, 'CHAOS_IDENTITY_LINKING_ENABLED'), providers, mail)
