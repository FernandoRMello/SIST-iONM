import sqlite3
from collections.abc import Callable
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse, RedirectResponse

from app.features.access_control.repository import AccessControlRepository
from app.features.hr.repository import HRRepository

JOB_TITLES = [
    "Vendedor",
    "Representante",
    "Analista",
    "Financeiro",
    "RH",
    "TI",
    "Gestor",
    "Diretoria",
]
CONTRACT_TYPES = ["CLT", "PJ", "Representante", "Estágio", "Autônomo", "Sócio", "Outro"]


def _to_float(value: object) -> float:
    text = str(value or "0").strip()
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
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
                "job_titles": JOB_TITLES,
                "contract_types": CONTRACT_TYPES,
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
            is_seller=str(form.get("is_seller") or "") == "Sim",
            seller_commission_rate=_to_float(form.get("seller_commission_rate")),
        )
        return RedirectResponse("/hr/employees", status_code=303)

    @router.post("/hr/employees/{employee_id}/update")
    async def employee_update(request: Request, employee_id: int):
        denied = require_permission(request, "hr.manage")
        if denied:
            return denied
        form = await request.form()
        hr_repository().update_employee(
            employee_id,
            full_name=str(form.get("full_name") or ""),
            document=str(form.get("document") or ""),
            email=str(form.get("email") or ""),
            phone=str(form.get("phone") or ""),
            job_title=str(form.get("job_title") or ""),
            contract_type=str(form.get("contract_type") or "CLT"),
            admission_date=str(form.get("admission_date") or ""),
            status=str(form.get("status") or "Ativo"),
            base_salary=_to_float(form.get("base_salary")),
            notes=str(form.get("notes") or ""),
            is_seller=str(form.get("is_seller") or "") == "Sim",
            seller_commission_rate=_to_float(form.get("seller_commission_rate")),
        )
        return RedirectResponse("/hr/employees", status_code=303)

    @router.post("/hr/employees/{employee_id}/delete")
    def employee_delete(request: Request, employee_id: int):
        denied = require_permission(request, "hr.manage")
        if denied:
            return denied
        hr_repository().delete_employee(employee_id)
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
                    employee.get("seller_id"),
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
                "adjustment_rules": repo.payroll_adjustment_rules(),
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

    @router.post("/hr/commission-rules/{rule_id}/update")
    async def commission_rule_update(request: Request, rule_id: int):
        denied = require_permission(request, "hr.manage")
        if denied:
            return denied
        form = await request.form()
        raw_employee_id = str(form.get("employee_id") or "").strip()
        hr_repository().update_commission_rule(
            rule_id,
            name=str(form.get("name") or ""),
            employee_id=int(raw_employee_id) if raw_employee_id.isdigit() else None,
            basis=str(form.get("basis") or "sale_total"),
            calculation_scope=str(form.get("calculation_scope") or "company"),
            fixed_percentage=_to_float(form.get("fixed_percentage")),
            is_active=str(form.get("is_active") or "") == "Sim",
        )
        return RedirectResponse("/hr/rules", status_code=303)

    @router.post("/hr/commission-rules/{rule_id}/delete")
    def commission_rule_delete(request: Request, rule_id: int):
        denied = require_permission(request, "hr.manage")
        if denied:
            return denied
        hr_repository().delete_commission_rule(rule_id)
        return RedirectResponse("/hr/rules", status_code=303)

    @router.post("/hr/payroll-adjustment-rules")
    async def payroll_adjustment_rule_create(request: Request):
        denied = require_permission(request, "hr.manage")
        if denied:
            return denied
        form = await request.form()
        hr_repository().create_payroll_adjustment_rule(
            name=str(form.get("name") or ""),
            target_contract=str(form.get("target_contract") or "CLT"),
            item_type=str(form.get("item_type") or "discount"),
            basis=str(form.get("basis") or "base_salary"),
            fixed_amount=_to_float(form.get("fixed_amount")),
            percentage=_to_float(form.get("percentage")),
            is_active=str(form.get("is_active") or "") == "Sim",
        )
        return RedirectResponse("/hr/rules", status_code=303)

    @router.post("/hr/payroll-adjustment-rules/{rule_id}/update")
    async def payroll_adjustment_rule_update(request: Request, rule_id: int):
        denied = require_permission(request, "hr.manage")
        if denied:
            return denied
        form = await request.form()
        hr_repository().update_payroll_adjustment_rule(
            rule_id,
            name=str(form.get("name") or ""),
            target_contract=str(form.get("target_contract") or "CLT"),
            item_type=str(form.get("item_type") or "discount"),
            basis=str(form.get("basis") or "base_salary"),
            fixed_amount=_to_float(form.get("fixed_amount")),
            percentage=_to_float(form.get("percentage")),
            is_active=str(form.get("is_active") or "") == "Sim",
        )
        return RedirectResponse("/hr/rules", status_code=303)

    @router.post("/hr/payroll-adjustment-rules/{rule_id}/delete")
    def payroll_adjustment_rule_delete(request: Request, rule_id: int):
        denied = require_permission(request, "hr.manage")
        if denied:
            return denied
        hr_repository().delete_payroll_adjustment_rule(rule_id)
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

    @router.post("/hr/benefit-rules/{rule_id}/update")
    async def benefit_rule_update(request: Request, rule_id: int):
        denied = require_permission(request, "hr.manage")
        if denied:
            return denied
        form = await request.form()
        raw_employee_id = str(form.get("employee_id") or "").strip()
        hr_repository().update_benefit_rule(
            rule_id,
            name=str(form.get("name") or ""),
            employee_id=int(raw_employee_id) if raw_employee_id.isdigit() else None,
            benefit_type=str(form.get("benefit_type") or "fixed_monthly"),
            basis=str(form.get("basis") or "fixed"),
            calculation_scope=str(form.get("calculation_scope") or "individual"),
            fixed_amount=_to_float(form.get("fixed_amount")),
            percentage=_to_float(form.get("percentage")),
            target_value=_to_float(form.get("target_value")),
            is_active=str(form.get("is_active") or "") == "Sim",
        )
        return RedirectResponse("/hr/rules", status_code=303)

    @router.post("/hr/benefit-rules/{rule_id}/delete")
    def benefit_rule_delete(request: Request, rule_id: int):
        denied = require_permission(request, "hr.manage")
        if denied:
            return denied
        hr_repository().delete_benefit_rule(rule_id)
        return RedirectResponse("/hr/rules", status_code=303)

    @router.get("/hr/payroll")
    def payroll_page(request: Request, period: str = ""):
        denied = require_permission(request, "hr.payroll.view")
        if denied:
            return denied
        repo = hr_repository()
        periods = repo.payroll_periods()
        current_period = None
        if period:
            current_period = next((row for row in periods if row.get("period") == period), None)
        if current_period is None:
            current_period = periods[0] if periods else None
        items = repo.payroll_items(int(current_period["id"])) if current_period else []
        return render(
            request,
            "hr_payroll.html",
            {"periods": periods, "current_period": current_period, "items": items},
        )

    @router.get("/hr/payroll/{period_id}/print-clt")
    def payroll_print_clt(request: Request, period_id: int):
        denied = require_permission(request, "hr.payroll.view")
        if denied:
            return denied
        repo = hr_repository()
        return render(
            request,
            "hr_payroll_print.html",
            {
                "period": repo.payroll_period(period_id),
                "summaries": repo.payroll_summaries(period_id, contract_type="CLT"),
            },
        )

    @router.get("/hr/payroll/{period_id}/statements")
    def payroll_statements(request: Request, period_id: int):
        denied = require_permission(request, "hr.payroll.view")
        if denied:
            return denied
        repo = hr_repository()
        summaries = [
            summary
            for summary in repo.payroll_summaries(period_id)
            if (summary.get("employee") or {}).get("contract_type") != "CLT"
        ]
        return render(
            request,
            "hr_payment_statement.html",
            {
                "period": repo.payroll_period(period_id),
                "summaries": summaries,
                "single_document": False,
            },
        )

    @router.get("/hr/payroll/{period_id}/employees/{employee_id}/statement")
    def employee_statement(request: Request, period_id: int, employee_id: int):
        denied = require_permission(request, "hr.payroll.view")
        if denied:
            return denied
        repo = hr_repository()
        return render(
            request,
            "hr_payment_statement.html",
            {
                "period": repo.payroll_period(period_id),
                "summaries": [repo.employee_payment_summary(period_id, employee_id)],
                "single_document": True,
            },
        )

    @router.post("/hr/payroll/generate")
    async def payroll_generate(request: Request):
        denied = require_permission(request, "hr.payroll.process")
        if denied:
            return denied
        form = await request.form()
        user = current_user(request) or {}
        period = str(form.get("period") or "")
        hr_repository().generate_payroll_period(
            period=period,
            created_by_user_id=int(user.get("id") or 0),
        )
        return RedirectResponse(f"/hr/payroll?period={period}", status_code=303)

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

    @router.post("/hr/payroll/{period_id}/reopen")
    def payroll_reopen(request: Request, period_id: int):
        denied = require_permission(request, "hr.payroll.process")
        if denied:
            return denied
        hr_repository().set_payroll_status(
            period_id=period_id,
            status="Rascunho",
            user_id=int((current_user(request) or {}).get("id") or 0),
        )
        return RedirectResponse("/hr/payroll", status_code=303)

    @router.post("/hr/payroll/{period_id}/delete")
    def payroll_delete(request: Request, period_id: int):
        denied = require_permission(request, "hr.payroll.process")
        if denied:
            return denied
        hr_repository().delete_payroll_period(period_id)
        return RedirectResponse("/hr/payroll", status_code=303)

    return router
