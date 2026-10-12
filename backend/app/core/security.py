import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

hasher = PasswordHasher()
DUMMY_HASH = hasher.hash("dummy-nonaccount-password")


def digest(value: str):
    return hashlib.sha256(value.encode()).hexdigest()


def token():
    return secrets.token_urlsafe(32)


def verify(password: str, hashed: str):
    try:
        return hasher.verify(hashed, password)
    except (VerificationError, InvalidHashError):
        return False
