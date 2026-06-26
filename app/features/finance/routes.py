import sqlite3
from collections.abc import Callable
from datetime import date, datetime
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse, RedirectResponse

from app.features.finance.recurring_costs import (
    ensure_recurring_cost_schema,
    generate_due_recurring_costs,
)


def _money(value: object) -> float:
    text = str(value or "0").strip().replace("R$", "").replace(" ", "")
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    return float(text)


def create_finance_router(
    database_path: Callable[[], Path],
    current_user: Callable,
) -> APIRouter:
    router = APIRouter()

    def authorized(request: Request) -> bool:
        user = current_user(request) or {}
        return user.get("role") in {"admin", "financeiro"}

    def connect() -> sqlite3.Connection:
        connection = sqlite3.connect(database_path())
        connection.row_factory = sqlite3.Row
        ensure_recurring_cost_schema(connection)
        return connection

    def denied():
        return PlainTextResponse("Sem permissão", status_code=403)

    @router.post("/finance/cost-categories/add")
    async def add_category(request: Request):
        if not authorized(request):
            return denied()
        form = await request.form()
        name = str(form.get("name") or "").strip()
        if not name:
            return PlainTextResponse("Informe o nome da categoria.", status_code=400)
        user = current_user(request)
        now = datetime.now().isoformat(timespec="seconds")
        with connect() as connection:
            connection.execute(
                """
                INSERT INTO cost_categories(name,active,created_by_user_id,created_at,updated_at)
                VALUES(?,?,?,?,?)
                """,
                (name, "Sim", user.get("id"), now, now),
            )
        return RedirectResponse("/finance?segment=costs&cost_tab=categories", status_code=303)

    @router.post("/finance/cost-categories/{category_id}/edit")
    async def edit_category(category_id: int, request: Request):
        if not authorized(request):
            return denied()
        form = await request.form()
        name = str(form.get("name") or "").strip()
        if not name:
            return PlainTextResponse("Informe o nome da categoria.", status_code=400)
        with connect() as connection:
            connection.execute(
                "UPDATE cost_categories SET name=?,updated_at=? WHERE id=? AND deleted_at IS NULL",
                (name, datetime.now().isoformat(timespec="seconds"), category_id),
            )
        return RedirectResponse("/finance?segment=costs&cost_tab=categories", status_code=303)

    @router.post("/finance/cost-categories/{category_id}/delete")
    def delete_category(category_id: int, request: Request):
        if not authorized(request):
            return denied()
        with connect() as connection:
            used = connection.execute(
                """
                SELECT 1 FROM recurring_costs WHERE category_id=?
                UNION SELECT 1 FROM costs
                WHERE category=(SELECT name FROM cost_categories WHERE id=?)
                LIMIT 1
                """,
                (category_id, category_id),
            ).fetchone()
            if used:
                connection.execute(
                    """
                    UPDATE cost_categories
                    SET active='Não',deleted_at=?,updated_at=?
                    WHERE id=?
                    """,
                    (datetime.now().isoformat(timespec="seconds"), datetime.now().isoformat(timespec="seconds"), category_id),
                )
            else:
                connection.execute("DELETE FROM cost_categories WHERE id=?", (category_id,))
        return RedirectResponse("/finance?segment=costs&cost_tab=categories", status_code=303)

    @router.post("/finance/recurring-costs/add")
    async def add_recurring_cost(request: Request):
        if not authorized(request):
            return denied()
        form = await request.form()
        user = current_user(request)
        now = datetime.now().isoformat(timespec="seconds")
        due_day = int(form.get("due_day") or 0)
        if not 1 <= due_day <= 31:
            return PlainTextResponse("Dia de vencimento inválido.", status_code=400)
        amount = _money(form.get("amount"))
        if amount <= 0:
            return PlainTextResponse("O valor deve ser maior que zero.", status_code=400)
        supplier_id = int(form["supplier_id"]) if str(form.get("supplier_id") or "").isdigit() else None
        seller_id = int(form["seller_id"]) if str(form.get("seller_id") or "").isdigit() else None
        with connect() as connection:
            connection.execute(
                """
                INSERT INTO recurring_costs(
                    description,category_id,supplier_id,seller_id,vendor,cost_center,
                    amount,due_day,start_date,end_date,payment_method,bank_account,notes,
                    status,created_by_user_id,created_at,updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    str(form.get("description") or "").strip(), int(form.get("category_id")),
                    supplier_id, seller_id, str(form.get("vendor") or "").strip(),
                    form.get("cost_center"), amount, due_day, form.get("start_date"),
                    form.get("end_date") or None, form.get("payment_method"),
                    form.get("bank_account"), form.get("notes"), "Ativo",
                    user.get("id"), now, now,
                ),
            )
            generate_due_recurring_costs(connection, date.today(), user.get("id"))
        return RedirectResponse("/finance?segment=costs&cost_tab=recurring", status_code=303)

    @router.post("/finance/recurring-costs/{cost_id}/edit")
    async def edit_recurring_cost(cost_id: int, request: Request):
        if not authorized(request):
            return denied()
        form = await request.form()
        amount = _money(form.get("amount"))
        due_day = int(form.get("due_day") or 0)
        if amount <= 0 or not 1 <= due_day <= 31:
            return PlainTextResponse("Valor ou vencimento inválido.", status_code=400)
        with connect() as connection:
            connection.execute(
                """
                UPDATE recurring_costs SET description=?,category_id=?,cost_center=?,
                    amount=?,due_day=?,start_date=?,end_date=?,payment_method=?,
                    bank_account=?,notes=?,updated_at=?
                WHERE id=? AND deleted_at IS NULL
                """,
                (
                    form.get("description"), int(form.get("category_id")),
                    form.get("cost_center"), amount, due_day, form.get("start_date"),
                    form.get("end_date") or None, form.get("payment_method"),
                    form.get("bank_account"), form.get("notes"),
                    datetime.now().isoformat(timespec="seconds"), cost_id,
                ),
            )
        return RedirectResponse("/finance?segment=costs&cost_tab=recurring", status_code=303)

    @router.post("/finance/recurring-costs/{cost_id}/status")
    async def recurring_cost_status(cost_id: int, request: Request):
        if not authorized(request):
            return denied()
        form = await request.form()
        status = str(form.get("status") or "")
        if status not in {"Ativo", "Pausado"}:
            return PlainTextResponse("Status inválido.", status_code=400)
        with connect() as connection:
            connection.execute(
                "UPDATE recurring_costs SET status=?,updated_at=? WHERE id=? AND deleted_at IS NULL",
                (status, datetime.now().isoformat(timespec="seconds"), cost_id),
            )
        return RedirectResponse("/finance?segment=costs&cost_tab=recurring", status_code=303)

    @router.post("/finance/recurring-costs/{cost_id}/delete")
    def delete_recurring_cost(cost_id: int, request: Request):
        if not authorized(request):
            return denied()
        now = datetime.now().isoformat(timespec="seconds")
        with connect() as connection:
            used = connection.execute(
                "SELECT 1 FROM recurring_cost_occurrences WHERE recurring_cost_id=? LIMIT 1",
                (cost_id,),
            ).fetchone()
            if used:
                connection.execute(
                    "UPDATE recurring_costs SET status='Excluído',deleted_at=?,updated_at=? WHERE id=?",
                    (now, now, cost_id),
                )
            else:
                connection.execute("DELETE FROM recurring_costs WHERE id=?", (cost_id,))
        return RedirectResponse("/finance?segment=costs&cost_tab=recurring", status_code=303)

    @router.post("/finance/costs/{cost_id}/delete")
    def delete_variable_cost(cost_id: int, request: Request):
        if not authorized(request):
            return denied()
        with connect() as connection:
            connection.execute("DELETE FROM costs WHERE id=?", (cost_id,))
        return RedirectResponse("/finance?segment=costs&cost_tab=variable", status_code=303)

    @router.post("/finance/business-holidays/add")
    async def add_business_holiday(request: Request):
        if not authorized(request):
            return denied()
        form = await request.form()
        holiday_date = str(form.get("holiday_date") or "")
        description = str(form.get("description") or "").strip()
        try:
            date.fromisoformat(holiday_date)
        except ValueError:
            return PlainTextResponse("Data de feriado inválida.", status_code=400)
        if not description:
            return PlainTextResponse("Informe a descrição do feriado.", status_code=400)
        with connect() as connection:
            connection.execute(
                """
                INSERT INTO business_holidays(
                    holiday_date,description,created_by_user_id,created_at
                ) VALUES(?,?,?,?)
                """,
                (
                    holiday_date, description, current_user(request).get("id"),
                    datetime.now().isoformat(timespec="seconds"),
                ),
            )
        return RedirectResponse("/finance?segment=costs&cost_tab=categories", status_code=303)

    @router.post("/finance/business-holidays/{holiday_id}/delete")
    def delete_business_holiday(holiday_id: int, request: Request):
        if not authorized(request):
            return denied()
        with connect() as connection:
            connection.execute("DELETE FROM business_holidays WHERE id=?", (holiday_id,))
        return RedirectResponse("/finance?segment=costs&cost_tab=categories", status_code=303)

    return router
