import sqlite3
from collections.abc import Callable
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse, RedirectResponse

from app.features.access_control.repository import AccessControlRepository
from app.features.hr.repository import HRRepository


def _to_float(value: object) -> float:
    text = str(value or "0").replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return 0.0


def create_hr_router(
    *,
    database_path: Path | Callable[[], Path],
    render: Callable,
    current_user: Callable[[Request], dict | None],
    hash_password: Callable[[str], str],
) -> APIRouter:
    router = APIRouter()

    def resolved_database_path() -> Path:
        return database_path() if callable(database_path) else database_path

    def hr_repository() -> HRRepository:
        repo = HRRepository(resolved_database_path())
        repo.init_schema()
        return repo

    def access_repository() -> AccessControlRepository:
        repo = AccessControlRepository(resolved_database_path())
        repo.ensure_seed_data()
        return repo

    def allowed(request: Request, code: str) -> bool:
        user = current_user(request)
        if not user:
            return False
        return access_repository().user_has_permission(
            int(user.get("id") or 0),
            code,
            legacy_role=str(user.get("role") or ""),
        )

    def require_permission(request: Request, code: str) -> PlainTextResponse | None:
        if not allowed(request, code):
            return PlainTextResponse("Sem permissão", status_code=403)
        return None

    @router.get("/hr/employees")
    def employees_page(request: Request):
        denied = require_permission(request, "hr.view")
        if denied:
            return denied
        repo = hr_repository()
        return render(
            request,
            "hr_employees.html",
            {
                "employees": repo.employees(),
                "profiles": access_repository().profiles(),
            },
        )

    @router.post("/hr/employees")
    async def employee_create(request: Request):
        denied = require_permission(request, "hr.manage")
        if denied:
            return denied
        form = await request.form()
        hr_repository().create_employee(
            full_name=str(form.get("full_name") or ""),
            document=str(form.get("document") or ""),
            email=str(form.get("email") or ""),
            phone=str(form.get("phone") or ""),
            department_id=None,
            job_title=str(form.get("job_title") or ""),
            contract_type=str(form.get("contract_type") or "CLT"),
            admission_date=str(form.get("admission_date") or ""),
            status=str(form.get("status") or "Ativo"),
            base_salary=_to_float(form.get("base_salary")),
            user_id=None,
            manager_user_id=None,
            notes=str(form.get("notes") or ""),
        )
        return RedirectResponse("/hr/employees", status_code=303)

    @router.post("/hr/employees/{employee_id}/create-user")
    async def employee_create_user(request: Request, employee_id: int):
        denied = require_permission(request, "users.manage")
        if denied:
            return denied
        form = await request.form()
        username = str(form.get("username") or "").strip()
        password = str(form.get("password") or "").strip()
        profile_id = str(form.get("profile_id") or "").strip()
        employee = hr_repository().employee(employee_id)
        if not employee:
            return PlainTextResponse("Colaborador não encontrado", status_code=404)
        if not username or not password:
            return PlainTextResponse("Usuário e senha são obrigatórios", status_code=400)
        with sqlite3.connect(resolved_database_path()) as connection:
            existing = connection.execute(
                "SELECT id FROM users WHERE username=?",
                (username,),
            ).fetchone()
            if existing:
                return PlainTextResponse("Usuário já existe", status_code=400)
            cursor = connection.execute(
                """
                INSERT INTO users(username,password_hash,role,seller_id,active,email)
                VALUES(?,?,?,?,?,?)
                """,
                (
                    username,
                    hash_password(password),
                    "vendedor",
                    None,
                    "Sim",
                    employee.get("email") or "",
                ),
            )
            user_id = int(cursor.lastrowid)
            connection.execute(
                "UPDATE hr_employees SET user_id=?, updated_at=datetime('now') WHERE id=?",
                (user_id, employee_id),
            )
            connection.execute(
                "INSERT OR IGNORE INTO user_profiles(user_id,full_name,email) VALUES(?,?,?)",
                (user_id, employee.get("full_name") or username, employee.get("email") or ""),
            )
            connection.commit()
        if profile_id.isdigit():
            access_repository().assign_profile(
                user_id=user_id,
                profile_id=int(profile_id),
                assigned_by_user_id=int((current_user(request) or {}).get("id") or 0),
            )
        return RedirectResponse("/hr/employees", status_code=303)

    @router.get("/hr/rules")
    def rules_page(request: Request):
        denied = require_permission(request, "hr.manage")
        if denied:
            return denied
        repo = hr_repository()
        return render(
            request,
            "hr_rules.html",
            {
                "employees": repo.employees(),
                "commission_rules": repo.commission_rules(),
                "benefit_rules": repo.benefit_rules(),
            },
        )

    @router.post("/hr/commission-rules")
    async def commission_rule_create(request: Request):
        denied = require_permission(request, "hr.manage")
        if denied:
            return denied
        form = await request.form()
        raw_employee_id = str(form.get("employee_id") or "").strip()
        hr_repository().create_commission_rule(
            name=str(form.get("name") or ""),
            employee_id=int(raw_employee_id) if raw_employee_id.isdigit() else None,
            profile_id=None,
            basis=str(form.get("basis") or "sale_total"),
            calculation_scope=str(form.get("calculation_scope") or "company"),
            percentage_type="fixed",
            fixed_percentage=_to_float(form.get("fixed_percentage")),
            is_active=str(form.get("is_active") or "") == "Sim",
        )
        return RedirectResponse("/hr/rules", status_code=303)

    @router.post("/hr/benefit-rules")
    async def benefit_rule_create(request: Request):
        denied = require_permission(request, "hr.manage")
        if denied:
            return denied
        form = await request.form()
        raw_employee_id = str(form.get("employee_id") or "").strip()
        hr_repository().create_benefit_rule(
            name=str(form.get("name") or ""),
            employee_id=int(raw_employee_id) if raw_employee_id.isdigit() else None,
            profile_id=None,
            benefit_type=str(form.get("benefit_type") or "fixed_monthly"),
            basis=str(form.get("basis") or "fixed"),
            calculation_scope=str(form.get("calculation_scope") or "individual"),
            fixed_amount=_to_float(form.get("fixed_amount")),
            percentage=_to_float(form.get("percentage")),
            target_value=_to_float(form.get("target_value")),
            is_active=str(form.get("is_active") or "") == "Sim",
        )
        return RedirectResponse("/hr/rules", status_code=303)

    @router.get("/hr/payroll")
    def payroll_page(request: Request):
        denied = require_permission(request, "hr.payroll.view")
        if denied:
            return denied
        repo = hr_repository()
        periods = repo.payroll_periods()
        current_period = periods[0] if periods else None
        items = repo.payroll_items(int(current_period["id"])) if current_period else []
        return render(
            request,
            "hr_payroll.html",
            {"periods": periods, "current_period": current_period, "items": items},
        )

    @router.post("/hr/payroll/generate")
    async def payroll_generate(request: Request):
        denied = require_permission(request, "hr.payroll.process")
        if denied:
            return denied
        form = await request.form()
        user = current_user(request) or {}
        hr_repository().generate_payroll_period(
            period=str(form.get("period") or ""),
            created_by_user_id=int(user.get("id") or 0),
        )
        return RedirectResponse("/hr/payroll", status_code=303)

    @router.post("/hr/payroll/{period_id}/approve")
    def payroll_approve(request: Request, period_id: int):
        denied = require_permission(request, "hr.payroll.approve")
        if denied:
            return denied
        hr_repository().set_payroll_status(
            period_id=period_id,
            status="Aprovada",
            user_id=int((current_user(request) or {}).get("id") or 0),
        )
        return RedirectResponse("/hr/payroll", status_code=303)

    @router.post("/hr/payroll/{period_id}/pay")
    def payroll_pay(request: Request, period_id: int):
        denied = require_permission(request, "hr.payroll.pay")
        if denied:
            return denied
        hr_repository().set_payroll_status(
            period_id=period_id,
            status="Paga",
            user_id=int((current_user(request) or {}).get("id") or 0),
        )
        return RedirectResponse("/hr/payroll", status_code=303)

    return router
