from collections.abc import Callable
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse, RedirectResponse

from app.features.access_control.repository import AccessControlRepository


def create_access_control_router(
    *,
    database_path: Path | Callable[[], Path],
    render: Callable,
    require_admin: Callable[[Request], bool],
    current_user: Callable[[Request], dict | None],
) -> APIRouter:
    router = APIRouter()

    def repository() -> AccessControlRepository:
        resolved = database_path() if callable(database_path) else database_path
        repo = AccessControlRepository(resolved)
        repo.ensure_seed_data()
        return repo

    def admin_required(request: Request) -> PlainTextResponse | None:
        if not require_admin(request):
            return PlainTextResponse("Sem permissão", status_code=403)
        return None

    @router.get("/admin/access-profiles")
    def access_profiles(request: Request):
        denied = admin_required(request)
        if denied:
            return denied
        repo = repository()
        return render(
            request,
            "access_profiles.html",
            {
                "profiles": repo.profiles(),
                "permissions": repo.permissions(),
                "matrix": repo.matrix(),
            },
        )

    @router.post("/admin/access-profiles")
    async def access_profile_create(request: Request):
        denied = admin_required(request)
        if denied:
            return denied
        form = await request.form()
        name = str(form.get("name") or "").strip()
        if not name:
            return PlainTextResponse("Nome do perfil é obrigatório", status_code=400)
        repository().create_profile(
            name=name,
            description=str(form.get("description") or ""),
        )
        return RedirectResponse("/admin/access-profiles", status_code=303)

    @router.post("/admin/access-profiles/permissions")
    async def access_profile_permissions_save(request: Request):
        denied = admin_required(request)
        if denied:
            return denied
        form = await request.form()
        repo = repository()
        for row in repo.matrix():
            profile_id = int(row["profile_id"])
            permission_id = int(row["permission_id"])
            repo.set_profile_permission(
                profile_id=profile_id,
                permission_id=permission_id,
                enabled=str(form.get(f"perm_{profile_id}_{permission_id}") or "") == "Sim",
                scope=str(form.get(f"scope_{profile_id}_{permission_id}") or "all"),
            )
        return RedirectResponse("/admin/access-profiles", status_code=303)

    @router.post("/settings/users/{user_id}/profiles")
    async def user_profiles_save(request: Request, user_id: int):
        denied = admin_required(request)
        if denied:
            return denied
        user = current_user(request) or {}
        form = await request.form()
        repo = repository()
        profile_ids = [
            int(profile["id"])
            for profile in repo.profiles()
            if str(form.get(f"profile_{profile['id']}") or "") == "Sim"
        ]
        repo.replace_user_profiles(
            user_id=user_id,
            profile_ids=profile_ids,
            assigned_by_user_id=int(user.get("id") or 0),
        )
        return RedirectResponse("/settings", status_code=303)

    return router
