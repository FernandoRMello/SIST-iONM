import json
import os
import secrets
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlencode

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse, RedirectResponse

from app.features.whatsapp.client import MetaWhatsAppClient
from app.features.whatsapp.repository import WhatsAppSettingsRepository
from app.features.whatsapp.security import (
    decrypt_secret,
    encrypt_secret,
    hash_state_token,
    hash_verify_token,
    mask_secret,
    valid_meta_signature,
    verify_token_matches,
)
from app.features.whatsapp.service import (
    handle_inbound_message,
    normalize_inbound_payload,
)


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

    def embedded_signup_redirect_uri(request: Request) -> str:
        return os.getenv("META_EMBEDDED_SIGNUP_REDIRECT_URI") or (
            f"{str(request.base_url).rstrip('/')}"
            "/admin/integrations/whatsapp/embedded/callback"
        )

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
                "automation_rules": repo.automation_rules(),
                "qr_codes": repo.qr_codes(),
                "whatsapp_users": repo.active_users(),
                "generated_verify_token": request.session.pop(
                    "whatsapp_generated_verify_token",
                    "",
                ),
                "whatsapp_setup_warning": request.session.pop(
                    "whatsapp_setup_warning",
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

    @router.post("/admin/integrations/whatsapp/embedded/start")
    def whatsapp_embedded_signup_start(request: Request):
        denied = admin_required(request)
        if denied:
            return denied
        user = current_user(request) or {}
        app_id = os.getenv("META_EMBEDDED_SIGNUP_APP_ID")
        config_id = os.getenv("META_EMBEDDED_SIGNUP_CONFIG_ID")
        redirect_uri = os.getenv("META_EMBEDDED_SIGNUP_REDIRECT_URI")
        missing = [
            name
            for name, value in {
                "META_EMBEDDED_SIGNUP_APP_ID": app_id,
                "META_EMBEDDED_SIGNUP_CONFIG_ID": config_id,
                "META_EMBEDDED_SIGNUP_REDIRECT_URI": redirect_uri,
            }.items()
            if not value
        ]
        if missing:
            request.session["whatsapp_setup_warning"] = (
                "Configure "
                + ", ".join(missing)
                + " no .env antes de conectar com a Meta."
            )
            return RedirectResponse("/admin/integrations/whatsapp", status_code=303)
        state_token = secrets.token_urlsafe(32)
        repository().create_embedded_signup_session(
            started_by_user_id=int(user.get("id") or 0),
            state_token_hash=hash_state_token(state_token),
        )
        query = urlencode(
            {
                "client_id": app_id,
                "redirect_uri": redirect_uri or embedded_signup_redirect_uri(request),
                "state": state_token,
                "config_id": config_id,
            },
        )
        return RedirectResponse(
            f"https://www.facebook.com/dialog/oauth?{query}",
            status_code=303,
        )

    @router.get("/admin/integrations/whatsapp/embedded/callback")
    def whatsapp_embedded_signup_callback(request: Request):
        denied = admin_required(request)
        if denied:
            return denied
        state = str(request.query_params.get("state") or "")
        if not state:
            return PlainTextResponse("State inválido", status_code=403)
        state_hash = hash_state_token(state)
        repo = repository()
        session = repo.find_embedded_signup_session(state_hash)
        if not session or session.get("status") != "pending":
            return PlainTextResponse("State inválido", status_code=403)
        provider_payload = {
            "code": str(request.query_params.get("code") or ""),
            "status": str(request.query_params.get("status") or ""),
            "error": str(request.query_params.get("error") or ""),
        }
        repo.complete_embedded_signup_session(
            state_token_hash=state_hash,
            provider_payload_json=json.dumps(provider_payload),
        )
        return RedirectResponse("/admin/integrations/whatsapp", status_code=303)

    @router.post("/admin/integrations/whatsapp/automation-rules")
    async def whatsapp_automation_rules_save(request: Request):
        denied = admin_required(request)
        if denied:
            return denied
        user = current_user(request) or {}
        form = await request.form()
        name = str(form.get("name") or "").strip()
        trigger_value = str(form.get("trigger_value") or "").strip()
        if not name or not trigger_value:
            return PlainTextResponse("Nome e gatilho são obrigatórios", status_code=400)
        raw_department_id = str(form.get("target_department_id") or "").strip()
        target_department_id = (
            int(raw_department_id) if raw_department_id.isdigit() else None
        )
        repository().create_automation_rule(
            name=name,
            trigger_type=str(form.get("trigger_type") or "keyword"),
            trigger_value=trigger_value,
            response_type=str(form.get("response_type") or "human_handoff"),
            response_text=str(form.get("response_text") or ""),
            target_department_id=target_department_id,
            is_active=str(form.get("is_active") or "") == "Sim",
            created_by_user_id=int(user.get("id") or 0),
        )
        return RedirectResponse("/admin/integrations/whatsapp", status_code=303)

    @router.post("/admin/integrations/whatsapp/qr-codes")
    async def whatsapp_qr_codes_create(request: Request):
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
        result = MetaWhatsAppClient().create_qr_code(
            api_version=settings.get("api_version") or "v23.0",
            phone_number_id=settings.get("phone_number_id") or "",
            access_token=access_token,
            prefilled_message=str(form.get("prefilled_message") or ""),
        )
        repo.save_qr_code(
            name=str(form.get("name") or "Atendimento"),
            code=str(result.get("code") or ""),
            short_link=str(
                result.get("deep_link_url")
                or result.get("short_link")
                or result.get("qr_image_url")
                or "",
            ),
            prefilled_message=str(form.get("prefilled_message") or ""),
            created_by_user_id=int(user.get("id") or 0),
        )
        return RedirectResponse("/admin/integrations/whatsapp", status_code=303)

    @router.post("/admin/integrations/whatsapp/departments")
    async def whatsapp_departments_save(request: Request):
        denied = admin_required(request)
        if denied:
            return denied
        user = current_user(request) or {}
        form = await request.form()
        repository().save_departments(
            {key: str(value) for key, value in form.items()},
            int(user.get("id") or 0),
        )
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
