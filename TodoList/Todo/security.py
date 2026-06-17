import base64
import hashlib

from cryptography.fernet import Fernet
from django.conf import settings


TEXT_PREFIX = 'fernet:'
BYTES_PREFIX = b'fernet:'


def _fernet():
    digest = hashlib.sha256(settings.SECRET_KEY.encode('utf-8')).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_text(value):
    if not value or value.startswith(TEXT_PREFIX):
        return value
    token = _fernet().encrypt(value.encode('utf-8')).decode('ascii')
    return f'{TEXT_PREFIX}{token}'


def decrypt_text(value):
    if not value or not value.startswith(TEXT_PREFIX):
        return value
    token = value[len(TEXT_PREFIX):].encode('ascii')
    return _fernet().decrypt(token).decode('utf-8')


def encrypt_bytes(value):
    if not value or bytes(value).startswith(BYTES_PREFIX):
        return value
    return BYTES_PREFIX + _fernet().encrypt(bytes(value))


def decrypt_bytes(value):
    if not value:
        return b''
    value = bytes(value)
    if not value.startswith(BYTES_PREFIX):
        return value
    return _fernet().decrypt(value[len(BYTES_PREFIX):])
