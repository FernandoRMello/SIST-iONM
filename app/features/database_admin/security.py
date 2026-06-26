import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken


def _fernet(master_key: str) -> Fernet:
    digest = hashlib.sha256(master_key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_database_password(value: str, master_key: str) -> str:
    if not value:
        return ""
    return _fernet(master_key).encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_database_password(value: str, master_key: str) -> str:
    if not value:
        return ""
    try:
        return _fernet(master_key).decrypt(value.encode("ascii")).decode("utf-8")
    except (InvalidToken, UnicodeDecodeError, ValueError):
        return ""


def password_status(encrypted_value: str | None) -> str:
    return "Configurada" if encrypted_value else "Não configurada"
