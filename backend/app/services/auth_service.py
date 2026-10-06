from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time

from backend.app.config import settings


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    iterations = 310_000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    encode = lambda value: base64.urlsafe_b64encode(value).decode().rstrip("=")
    return f"pbkdf2_sha256${iterations}${encode(salt)}${encode(digest)}"


def verify_password(password: str, stored: str) -> bool:
    if stored.startswith("pbkdf2_sha256$"):
        try:
            _, iterations, encoded_salt, encoded_digest = stored.split("$", 3)
            decode = lambda value: base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
            expected = decode(encoded_digest)
            actual = hashlib.pbkdf2_hmac("sha256", password.encode(), decode(encoded_salt), int(iterations))
            return hmac.compare_digest(actual, expected)
        except (ValueError, TypeError):
            return False
    return stored == f"hash:{password}" or stored == password


def create_access_token(user_id: int, email: str, role: str) -> str:
    payload = json.dumps({"sub": user_id, "email": email, "role": role, "exp": int(time.time()) + 28_800}).encode()
    body = base64.urlsafe_b64encode(payload).decode().rstrip("=")
    signature = hmac.new(settings.jwt_secret.encode(), body.encode(), hashlib.sha256).digest()
    encoded_signature = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    return f"{body}.{encoded_signature}"


def decode_access_token(token: str) -> dict | None:
    try:
        body, encoded_signature = token.split(".", 1)
        signature = base64.urlsafe_b64decode(encoded_signature + "=" * (-len(encoded_signature) % 4))
        expected = hmac.new(settings.jwt_secret.encode(), body.encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(signature, expected):
            return None
        payload = base64.urlsafe_b64decode(body + "=" * (-len(body) % 4))
        claims = json.loads(payload)
        if claims.get("exp", 0) <= int(time.time()):
            return None
        return claims
    except (ValueError, TypeError, json.JSONDecodeError):
        return None