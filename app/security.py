"""Secret handling: SNMP credential encryption-at-rest and user password hashing.

SNMP community strings are never stored in plaintext, never returned by the
API, and never written to logs. The encryption key itself is a secret and
must come from the environment, not from source control.
"""
import base64
import hashlib

from cryptography.fernet import Fernet
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _fernet() -> Fernet:
    # Allow operators to supply any passphrase in FRAMPOL_CREDENTIAL_KEY;
    # derive a valid 32-byte urlsafe-base64 Fernet key from it so the .env
    # value doesn't have to be a Fernet key verbatim.
    digest = hashlib.sha256(settings.credential_key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(plaintext: str) -> bytes:
    return _fernet().encrypt(plaintext.encode("utf-8"))


def decrypt_secret(ciphertext: bytes) -> str:
    return _fernet().decrypt(ciphertext).decode("utf-8")


def hash_password(plaintext: str) -> str:
    return pwd_context.hash(plaintext)


def verify_password(plaintext: str, password_hash: str) -> bool:
    return pwd_context.verify(plaintext, password_hash)
