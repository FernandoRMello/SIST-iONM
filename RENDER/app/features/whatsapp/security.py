import base64
import hashlib
import hmac


def mask_secret(value: str | None) -> str:
    if not value:
        return "Não configurado"
    if len(value) <= 8:
        return "•" * len(value)
    return f"{value[:4]}{'•' * (len(value) - 8)}{value[-4:]}"


def hash_verify_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def hash_state_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def verify_token_matches(token: str, stored_hash: str) -> bool:
    if not token or not stored_hash:
        return False
    return hmac.compare_digest(hash_verify_token(token), stored_hash)


def _secret_stream(master_key: str, length: int) -> bytes:
    seed = hashlib.sha256(master_key.encode("utf-8")).digest()
    stream = bytearray()
    counter = 0
    while len(stream) < length:
        stream.extend(hashlib.sha256(seed + counter.to_bytes(8, "big")).digest())
        counter += 1
    return bytes(stream[:length])


def encrypt_secret(value: str, master_key: str) -> str:
    raw = value.encode("utf-8")
    stream = _secret_stream(master_key, len(raw))
    encrypted = bytes(left ^ right for left, right in zip(raw, stream, strict=False))
    return base64.urlsafe_b64encode(encrypted).decode("ascii")


def decrypt_secret(value: str, master_key: str) -> str:
    try:
        raw = base64.urlsafe_b64decode(value.encode("ascii"))
    except Exception:
        return ""
    stream = _secret_stream(master_key, len(raw))
    decrypted = bytes(left ^ right for left, right in zip(raw, stream, strict=False))
    try:
        return decrypted.decode("utf-8")
    except UnicodeDecodeError:
        return ""


def valid_meta_signature(
    raw_body: bytes,
    signature_header: str | None,
    app_secret: str,
) -> bool:
    if not raw_body or not signature_header or not app_secret:
        return False
    if not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(
        app_secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    provided = signature_header.removeprefix("sha256=")
    return hmac.compare_digest(expected, provided)
