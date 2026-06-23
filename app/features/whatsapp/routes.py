import os
import json
import secrets
from pathlib import Path
from typing import Callable

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse, RedirectResponse

from app.features.whatsapp.client import MetaWhatsAppClient
from app.features.whatsapp.repository import WhatsAppSettingsRepository
from app.features.whatsapp.security import (
    decrypt_secret,
    encrypt_secret,
    hash_verify_token,
    mask_secret,
    valid_meta_signature,
    verify_token_matches,
)
from app.features.whatsapp.service import handle_inbound_message, normalize_inbound_payload


def _master_key() -> str:
    return (
        os.getenv("WHATSAPP_SECRET_KEY")
        or os.getenv("SIST_IONM_SESSION_SECRET")
        or "sist-ionm-local-whatsapp-secret"
    )


def create_whatsapp_router(
    *,
    database_path: Path | Callable[[], Path],
    render: Callable,
    require_admin: Callable[[Request], bool],
    current_user: Callable[[Request], dict | None],
) -> APIRouter:
    router = APIRouter()

    def repository() -> WhatsAppSettingsRepository:
        resolved = database_path() if callable(database_path) else database_path
        return WhatsAppSettingsRepository(resolved)

    def admin_required(request: Request) -> PlainTextResponse | None:
        if not require_admin(request):
            return PlainTextResponse("Sem permissão", status_code=403)
        return None

    @router.get("/integrations/whatsapp/webhook")
    def whatsapp_webhook_verify(request: Request):
        repo = repository()
        settings = repo.get_settings()
        params = request.query_params
        verify_token = str(params.get("hub.verify_token") or "")
        if (
            params.get("hub.mode") == "subscribe"
            and verify_token_matches(verify_token, settings.get("verify_token_hash") or "")
        ):
            return PlainTextResponse(str(params.get("hub.challenge") or ""))
        return PlainTextResponse("Verify token inválido", status_code=403)

    @router.post("/integrations/whatsapp/webhook")
    async def whatsapp_webhook_receive(request: Request):
        repo = repository()
        settings = repo.get_settings()
        app_secret = decrypt_secret(settings.get("app_secret_encrypted") or "", _master_key())
        raw_body = await request.body()
        signature = request.headers.get("X-Hub-Signature-256")
        if not valid_meta_signature(raw_body, signature, app_secret):
            return PlainTextResponse("Assinatura inválida", status_code=403)
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            return PlainTextResponse("Payload inválido", status_code=400)
        results = [
            handle_inbound_message(repo, message)
            for message in normalize_inbound_payload(payload)
        ]
        return {"ok": True, "processed": len(results), "created": sum(1 for item in results if item.created)}

    @router.get("/admin/integrations/whatsapp")
    def whatsapp_wizard(request: Request):
        denied = admin_required(request)
        if denied:
            return denied
        repo = repository()
        settings = repo.get_settings()
        masked = {
            "access_token": mask_secret(settings.get("access_token_encrypted")),
            "app_secret": mask_secret(settings.get("app_secret_encrypted")),
            "verify_token": (
                "Configurado" if settings.get("verify_token_hash") else "Não configurado"
            ),
        }
        webhook_url = settings.get("public_webhook_url") or (
            f"{str(request.base_url).rstrip('/')}/integrations/whatsapp/webhook"
        )
        return render(
            request,
            "whatsapp_settings.html",
            {
                "settings": settings,
                "masked": masked,
                "departments": repo.departments(),
                "generated_verify_token": request.session.pop(
                    "whatsapp_generated_verify_token",
                    "",
                ),
                "webhook_url": webhook_url,
            },
        )

    @router.post("/admin/integrations/whatsapp/save")
    async def whatsapp_save(request: Request):
        denied = admin_required(request)
        if denied:
            return denied
        user = current_user(request) or {}
        form = await request.form()
        access_token = str(form.get("access_token") or "").strip()
        app_secret = str(form.get("app_secret") or "").strip()
        verify_token = str(form.get("verify_token") or "").strip()
        repository().save_settings(
            api_version=str(form.get("api_version") or "v23.0"),
            phone_number_id=str(form.get("phone_number_id") or ""),
            whatsapp_business_account_id=str(
                form.get("whatsapp_business_account_id") or "",
            ),
            public_webhook_url=str(form.get("public_webhook_url") or ""),
            access_token_encrypted=(
                encrypt_secret(access_token, _master_key()) if access_token else None
            ),
            app_secret_encrypted=(
                encrypt_secret(app_secret, _master_key()) if app_secret else None
            ),
            verify_token_hash=hash_verify_token(verify_token) if verify_token else None,
            updated_by_user_id=int(user.get("id") or 0),
        )
        return RedirectResponse("/admin/integrations/whatsapp", status_code=303)

    @router.post("/admin/integrations/whatsapp/generate-token")
    def whatsapp_generate_token(request: Request):
        denied = admin_required(request)
        if denied:
            return denied
        request.session["whatsapp_generated_verify_token"] = secrets.token_urlsafe(32)
        return RedirectResponse("/admin/integrations/whatsapp", status_code=303)

    @router.post("/admin/integrations/whatsapp/toggle")
    async def whatsapp_toggle(request: Request):
        denied = admin_required(request)
        if denied:
            return denied
        user = current_user(request) or {}
        form = await request.form()
        repository().set_enabled(
            str(form.get("enabled") or "") == "Sim",
            int(user.get("id") or 0),
        )
        return RedirectResponse("/admin/integrations/whatsapp", status_code=303)

    @router.post("/admin/integrations/whatsapp/test")
    async def whatsapp_test_connection(request: Request):
        denied = admin_required(request)
        if denied:
            return denied
        user = current_user(request) or {}
        form = await request.form()
        repo = repository()
        settings = repo.get_settings()
        access_token = decrypt_secret(
            settings.get("access_token_encrypted") or "",
            _master_key(),
        )
        try:
            MetaWhatsAppClient().send_text(
                api_version=settings.get("api_version") or "v23.0",
                phone_number_id=settings.get("phone_number_id") or "",
                access_token=access_token,
                to_phone=str(form.get("to_phone") or ""),
                message=str(form.get("message") or "Teste SIST-iONM"),
            )
        except Exception as exc:
            repo.record_test_status(
                status="error",
                message=f"Falha no teste: {exc}",
                updated_by_user_id=int(user.get("id") or 0),
            )
        else:
            repo.record_test_status(
                status="success",
                message="Teste enviado",
                updated_by_user_id=int(user.get("id") or 0),
            )
        return RedirectResponse("/admin/integrations/whatsapp", status_code=303)

    return router
