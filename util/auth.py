"""
登录认证基础能力：密码哈希、JWT 生成与校验。
密码哈希与 JWT 均使用标准库实现，避免环境里不同 jwt 包的兼容性问题。
"""
from datetime import datetime, timedelta, timezone
import base64
import hashlib
import hmac
import json
import os
import re
from config import AUTH_SECRET_KEY, AUTH_TOKEN_EXPIRE_MINUTES, AUTH_PBKDF2_ITERATIONS

JWT_ALGORITHM = 'HS256'
PASSWORD_HASH_PREFIX = 'pbkdf2_sha256'


class AuthError(Exception):
    """认证相关业务异常"""



def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip('=')



def _b64url_decode(text: str) -> bytes:
    padding = '=' * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + padding)



def _json_dumps(data: dict) -> bytes:
    return json.dumps(data, separators=(',', ':'), ensure_ascii=False).encode('utf-8')



def _sign(signing_input: bytes) -> str:
    signature = hmac.new(
        AUTH_SECRET_KEY.encode('utf-8'),
        signing_input,
        hashlib.sha256,
    ).digest()
    return _b64url_encode(signature)



def validate_password_strength(password: str):
    """基础密码强度校验。"""
    if len(password) < 8:
        raise AuthError('密码长度不能少于 8 位')
    if not re.search(r'[A-Za-z]', password):
        raise AuthError('密码必须至少包含 1 个字母')
    if not re.search(r'\d', password):
        raise AuthError('密码必须至少包含 1 个数字')



def hash_password(password: str, iterations: int = AUTH_PBKDF2_ITERATIONS) -> str:
    """生成 PBKDF2-SHA256 格式密码串。"""
    validate_password_strength(password)
    salt = _b64url_encode(os.urandom(16))
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), iterations)
    return f'{PASSWORD_HASH_PREFIX}${iterations}${salt}${_b64url_encode(dk)}'



def verify_password(password: str, stored_hash: str) -> bool:
    """校验密码是否与库中哈希匹配。"""
    try:
        prefix, iterations_str, salt, hash_value = stored_hash.split('$', 3)
        if prefix != PASSWORD_HASH_PREFIX:
            return False
        iterations = int(iterations_str)
    except (ValueError, TypeError):
        return False

    new_dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), iterations)
    return hmac.compare_digest(_b64url_encode(new_dk), hash_value)



def create_access_token(user_id: int, username: str, expires_minutes: int = AUTH_TOKEN_EXPIRE_MINUTES) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        'sub': str(user_id),
        'username': username,
        'type': 'access',
        'iat': int(now.timestamp()),
        'exp': int((now + timedelta(minutes=expires_minutes)).timestamp()),
    }
    header = {
        'alg': JWT_ALGORITHM,
        'typ': 'JWT',
    }
    header_b64 = _b64url_encode(_json_dumps(header))
    payload_b64 = _b64url_encode(_json_dumps(payload))
    signing_input = f'{header_b64}.{payload_b64}'.encode('utf-8')
    signature_b64 = _sign(signing_input)
    return f'{header_b64}.{payload_b64}.{signature_b64}'



def decode_access_token(token: str) -> dict:
    try:
        header_b64, payload_b64, signature_b64 = token.split('.')
    except ValueError as exc:
        raise AuthError('无效的登录凭证') from exc

    signing_input = f'{header_b64}.{payload_b64}'.encode('utf-8')
    expected_signature = _sign(signing_input)
    if not hmac.compare_digest(signature_b64, expected_signature):
        raise AuthError('无效的登录凭证')

    try:
        header = json.loads(_b64url_decode(header_b64).decode('utf-8'))
        payload = json.loads(_b64url_decode(payload_b64).decode('utf-8'))
    except Exception as exc:
        raise AuthError('无效的登录凭证') from exc

    if header.get('alg') != JWT_ALGORITHM or payload.get('type') != 'access' or 'sub' not in payload:
        raise AuthError('无效的登录凭证')

    exp = payload.get('exp')
    if not isinstance(exp, int):
        raise AuthError('无效的登录凭证')

    now_ts = int(datetime.now(timezone.utc).timestamp())
    if now_ts >= exp:
        raise AuthError('登录已过期，请重新登录')

    return payload
