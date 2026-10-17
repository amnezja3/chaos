"""Encrypted operator configuration and TLS-only SMTP. No pretend deliveries."""
import base64
from dataclasses import asdict
from email.message import EmailMessage
from email.utils import parseaddr
import hashlib
import json
import smtplib
import ssl
import time
from cryptography.fernet import Fernet
from .config import MailConfig
from .service import IdentityError


def cipher(secret):
    if not secret:
        raise IdentityError('mail_secret_required')
    raw = secret.encode() if isinstance(secret,str) else secret
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(b'chaos-identity-smtp-v1\0'+raw).digest()))


def load(conn, fallback, secret):
    row = conn.execute('SELECT settings_json,password_ciphertext FROM identity_mail_settings WHERE id=1').fetchone()
    if not row:
        return fallback
    values = json.loads(row[0])
    try:
        values['password'] = cipher(secret).decrypt(row[1].encode()).decode() if row[1] else ''
    except Exception:
        raise IdentityError('mail_secret_unavailable') from None
    return MailConfig(**values)


def public(config):
    result = asdict(config)
    result['password_configured'] = bool(result.pop('password'))
    result['configured'] = config.configured
    return result


def save(conn, data, previous, secret):
    mode = data.get('mode','disabled')
    host = str(data.get('host','')).strip()
    sender = str(data.get('sender','')).strip()
    username = str(data.get('username','')).strip()
    tls = data.get('tls','starttls')
    try:
        port = int(data.get('port',587))
    except (TypeError,ValueError):
        raise IdentityError('invalid_mail_config') from None
    if (mode not in ('disabled','smtp') or tls not in ('starttls','ssl') or not 1<=port<=65535
            or any(c in host+sender+username for c in '\r\n') or len(host)>253 or len(username)>320
            or len(sender)>320 or (mode=='smtp' and (not host or '@' not in parseaddr(sender)[1]))):
        raise IdentityError('invalid_mail_config')
    password = str(data.get('password') or previous.password)
    if data.get('clear_password') is True:
        password = ''
    if len(password)>4096:
        raise IdentityError('invalid_mail_config')
    config = MailConfig(mode,host,port,sender,username,password,tls)
    values = asdict(config)
    values.pop('password')
    encrypted = cipher(secret).encrypt(password.encode()).decode() if password else ''
    conn.execute('INSERT OR REPLACE INTO identity_mail_settings VALUES (1,?,?,?)',
                 (json.dumps(values),encrypted,int(time.time())))
    return config


def deliver(config, recipient, code, locale='pl', *, testing=False, outbox=None, minutes=30):
    if config.mode == 'mock' and testing and outbox is not None:
        outbox.append(dict(recipient=recipient,code=code,locale=locale))
        return
    if not config.configured:
        raise IdentityError('mail_unavailable')
    message = EmailMessage()
    message['From'], message['To'] = config.sender, recipient
    message['Subject'] = 'CHAOS — verification code' if locale=='en' else 'CHAOS — kod potwierdzenia'
    message.set_content((f'Your CHAOS code: {code}\nValid for {minutes} minutes. Do not share this code.\n'
                         'If you did not request it, ignore this message.' if locale=='en' else
                         f'Twój kod CHAOS: {code}\nWażny {minutes} minut. Nie udostępniaj tego kodu.\n'
                         'Jeśli nie wysłano prośby o kod, zignoruj tę wiadomość.'))
    context = ssl.create_default_context()
    factory = smtplib.SMTP_SSL if config.tls=='ssl' else smtplib.SMTP
    try:
        kwargs = dict(timeout=15)
        if config.tls=='ssl':
            kwargs['context'] = context
        with factory(config.host,config.port,**kwargs) as smtp:
            if config.tls=='starttls':
                smtp.ehlo()
                smtp.starttls(context=context)
                smtp.ehlo()
            if config.username:
                smtp.login(config.username,config.password)
            smtp.send_message(message)
    except (OSError,smtplib.SMTPException):
        raise IdentityError('mail_delivery_failed') from None
