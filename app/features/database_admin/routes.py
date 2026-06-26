import os
from collections.abc import Callable
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse, RedirectResponse

from app.features.database_admin.repository import DatabaseSettingsRepository
from app.features.database_admin.service import DatabaseAdminService


def _to_int(value: object, default: int = 5432) -> int:
    try:
        return int(str(value or "").strip() or default)
    except ValueError:
        return default


def _master_key() -> str:
    return (
        os.getenv("DATABASE_ADMIN_SECRET_KEY")
        or os.getenv("SIST_IONM_SESSION_SECRET")
        or "sist-ionm-local-database-admin-secret"
    )


def create_database_admin_router(
    *,
    database_path: Path | Callable[[], Path],
    require_admin: Callable[[Request], bool],
    current_user: Callable[[Request], dict | None],
) -> APIRouter:
    router = APIRouter()

    def resolved_database_path() -> Path:
        return database_path() if callable(database_path) else database_path

    def repository() -> DatabaseSettingsRepository:
        repo = DatabaseSettingsRepository(resolved_database_path())
        repo.init_schema()
        return repo

    def denied(request: Request) -> PlainTextResponse | None:
        if not require_admin(request):
            return PlainTextResponse("Sem permissão", status_code=403)
        return None

    @router.post("/settings/database/save")
    async def database_save(request: Request):
        if blocked := denied(request):
            return blocked
        form = await request.form()
        user = current_user(request) or {}
        repository().save_config(
            name=str(form.get("name") or ""),
            engine="postgresql",
            host=str(form.get("host") or ""),
            port=_to_int(form.get("port")),
            database_name=str(form.get("database_name") or ""),
            username=str(form.get("username") or ""),
            password=str(form.get("password") or ""),
            ssl_mode=str(form.get("ssl_mode") or "prefer"),
            notes=str(form.get("notes") or ""),
            updated_by_user_id=int(user.get("id") or 0),
            master_key=_master_key(),
        )
        return RedirectResponse("/settings", status_code=303)

    @router.post("/settings/database/test")
    def database_test(request: Request):
        if blocked := denied(request):
            return blocked
        repo = repository()
        result = DatabaseAdminService().test_connection(
            repo.get_config(),
            repo.get_password(master_key=_master_key()),
        )
        repo.record_test_result(status=result.status, message=result.message)
        return RedirectResponse("/settings", status_code=303)

    @router.post("/settings/database/prepare")
    def database_prepare(request: Request):
        if blocked := denied(request):
            return blocked
        repo = repository()
        result = DatabaseAdminService().prepare_environment(
            repo.get_config(),
            repo.get_password(master_key=_master_key()),
        )
        repo.record_prepare_result(status=result.status, message=result.message)
        return RedirectResponse("/settings", status_code=303)

    return router
