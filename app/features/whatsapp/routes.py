import os
import secrets
from pathlib import Path
from typing import Callable

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse, RedirectResponse

from app.features.whatsapp.repository import WhatsAppSettingsRepository
from app.features.whatsapp.security import (
    encrypt_secret,
    hash_verify_token,
    mask_secret,
)


def _master_key() -> str:
    return (
        os.getenv("WHATSAPP_SECRET_KEY")
        or os.getenv("SIST_IONM_SESSION_SECRET")
        or "sist-ionm-local-whatsapp-secret"
    )


def create_whatsapp_router(
    *,
    database_path: Path,
    render: Callable,
    require_admin: Callable[[Request], bool],
    current_user: Callable[[Request], dict | None],
) -> APIRouter:
    router = APIRouter()
    repository = WhatsAppSettingsRepository(database_path)

    def admin_required(request: Request) -> PlainTextResponse | None:
        if not require_admin(request):
            return PlainTextResponse("Sem permissão", status_code=403)
        return None

    @router.get("/admin/integrations/whatsapp")
    def whatsapp_wizard(request: Request):
        denied = admin_required(request)
        if denied:
            return denied
        settings = repository.get_settings()
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
                "departments": repository.departments(),
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
        repository.save_settings(
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
        repository.set_enabled(
            str(form.get("enabled") or "") == "Sim",
            int(user.get("id") or 0),
        )
        return RedirectResponse("/admin/integrations/whatsapp", status_code=303)

    return router
