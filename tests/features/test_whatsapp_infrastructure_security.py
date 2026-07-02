import hashlib
import hmac

import pytest

from app.features.whatsapp.infrastructure.security import WhatsAppSecurityEngine


def test_security_engine_encrypts_and_detects_ciphertext_tampering(monkeypatch) -> None:
    monkeypatch.setenv("WHATSAPP_SECRET_KEY", "test-secret-key")
    engine = WhatsAppSecurityEngine()

    encrypted = engine.encrypt_secret("meta-token")

    assert encrypted != "meta-token"
    assert engine.decrypt_secret(encrypted) == "meta-token"
    with pytest.raises(ValueError, match="Ciphertext tampering"):
        engine.decrypt_secret(encrypted[:-2] + "xx")


def test_security_engine_requires_explicit_key_in_production(monkeypatch) -> None:
    monkeypatch.setenv("SIST_IONM_ENVIRONMENT", "production")
    monkeypatch.delenv("WHATSAPP_SECRET_KEY", raising=False)

    with pytest.raises(RuntimeError, match="WHATSAPP_SECRET_KEY"):
        WhatsAppSecurityEngine()


def test_security_engine_verifies_meta_hmac_signature(monkeypatch) -> None:
    monkeypatch.setenv("WHATSAPP_SECRET_KEY", "test-secret-key")
    engine = WhatsAppSecurityEngine()
    payload = b'{"entry":[]}'
    app_secret = "meta-app-secret"
    digest = hmac.new(app_secret.encode(), payload, hashlib.sha256).hexdigest()

    assert engine.verify_webhook_signature(payload, f"sha256={digest}", app_secret)
    assert not engine.verify_webhook_signature(payload + b"x", f"sha256={digest}", app_secret)
