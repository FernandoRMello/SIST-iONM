import hashlib
import hmac

from app.features.whatsapp.security import (
    decrypt_secret,
    encrypt_secret,
    hash_verify_token,
    mask_secret,
    valid_meta_signature,
    verify_token_matches,
)


def test_mask_secret_keeps_only_safe_hint() -> None:
    assert mask_secret(None) == "Não configurado"
    assert mask_secret("") == "Não configurado"
    assert mask_secret("short") == "•••••"
    assert mask_secret("EAAB1234567890TOKEN") == "EAAB•••••••••••OKEN"


def test_verify_token_hash_matches_without_revealing_token() -> None:
    stored = hash_verify_token("verify-token-company")

    assert stored != "verify-token-company"
    assert verify_token_matches("verify-token-company", stored)
    assert not verify_token_matches("wrong-token", stored)


def test_encrypt_secret_roundtrip_requires_same_master_key() -> None:
    encrypted = encrypt_secret("meta-access-token", "master-key-for-tests")

    assert encrypted != "meta-access-token"
    assert decrypt_secret(encrypted, "master-key-for-tests") == "meta-access-token"
    assert decrypt_secret(encrypted, "other-master-key") != "meta-access-token"


def test_valid_meta_signature_checks_hmac_sha256() -> None:
    body = b'{"entry":[{"changes":[{"value":{"messages":[]}}]}]}'
    secret = "meta-app-secret"
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    assert valid_meta_signature(body, f"sha256={digest}", secret)
    assert not valid_meta_signature(body + b"x", f"sha256={digest}", secret)
    assert not valid_meta_signature(body, "sha256=bad", secret)
    assert not valid_meta_signature(body, None, secret)
