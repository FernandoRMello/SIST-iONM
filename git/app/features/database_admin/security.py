import base64
import hashlib


def encrypt_database_password(value: str, master_key: str) -> str:
    if not value:
        return ""
    raw = value.encode("utf-8")
    stream = _secret_stream(master_key, len(raw))
    encrypted = bytes(left ^ right for left, right in zip(raw, stream, strict=False))
    return base64.urlsafe_b64encode(encrypted).decode("ascii")


def decrypt_database_password(value: str, master_key: str) -> str:
    if not value:
        return ""
    try:
        raw = base64.urlsafe_b64decode(value.encode("ascii"))
    except ValueError:
        return ""
    stream = _secret_stream(master_key, len(raw))
    decrypted = bytes(left ^ right for left, right in zip(raw, stream, strict=False))
    try:
        return decrypted.decode("utf-8")
    except UnicodeDecodeError:
        return ""


def password_status(encrypted_value: str | None) -> str:
    return "Configurada" if encrypted_value else "Não configurada"


def _secret_stream(master_key: str, length: int) -> bytes:
    seed = hashlib.sha256(master_key.encode("utf-8")).digest()
    stream = bytearray()
    counter = 0
    while len(stream) < length:
        stream.extend(hashlib.sha256(seed + counter.to_bytes(8, "big")).digest())
        counter += 1
    return bytes(stream[:length])
