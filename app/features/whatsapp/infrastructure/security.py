import os
import base64
import hashlib
import hmac
from typing import Optional
from cryptography.fernet import Fernet

class WhatsAppSecurityEngine:
    """
    Infraestrutura de segurança para proteção de tokens da API Graph da Meta
    e validação de assinaturas de Webhooks (WA-011).
    """
    def __init__(self):
        self.env = os.getenv("SIST_IONM_ENVIRONMENT", "development")
        secret_key = os.getenv("WHATSAPP_SECRET_KEY")
        
        if not secret_key:
            if self.env == "production":
                raise RuntimeError(
                    "CRITICAL SECURITY ALERT: 'WHATSAPP_SECRET_KEY' must be defined in production env."
                )
            secret_key = "sist-ionm-local-whatsapp-secret-development-key-32chrs!"

        hashed_key = hashlib.sha256(secret_key.encode()).digest()
        self._fernet = Fernet(base64.urlsafe_b64encode(hashed_key))

    def encrypt_secret(self, raw_secret: str) -> str:
        if not raw_secret:
            return ""
        return self._fernet.encrypt(raw_secret.encode()).decode()

    def decrypt_secret(self, encrypted_secret: str) -> str:
        if not encrypted_secret:
            return ""
        try:
            return self._fernet.decrypt(encrypted_secret.encode()).decode()
        except Exception as e:
            raise ValueError("Security violation: Ciphertext tampering detected or invalid key.") from e

    def hash_verify_token(self, verify_token: str) -> str:
        return hashlib.sha256(verify_token.encode()).hexdigest()

    def verify_webhook_signature(self, payload: bytes, signature_header: Optional[str], app_secret: str) -> bool:
        if not signature_header or not signature_header.startswith("sha256="):
            return False
        
        actual_signature = signature_header.split("sha256=")[1]
        expected_signature = hmac.new(
            app_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(actual_signature, expected_signature)
