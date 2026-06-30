import sqlite3

from fastapi.testclient import TestClient


def test_costs_page_has_variable_recurring_and_category_tabs(
    admin_client: TestClient,
) -> None:
    response = admin_client.get("/finance?segment=costs&cost_tab=recurring")

    assert response.status_code == 200
    assert "Lançamentos variáveis" in response.text
    assert "Custos fixos recorrentes" in response.text
    assert "Categorias" in response.text
    assert 'action="/finance/recurring-costs/add"' in response.text
    assert 'name="due_day"' in response.text
    assert 'name="category_id"' in response.text
    categories = admin_client.get("/finance?segment=costs&cost_tab=categories")
    assert 'action="/finance/business-holidays/add"' in categories.text


def test_finance_user_can_create_category_and_recurring_cost(
    admin_client: TestClient,
    legacy_test_state,
) -> None:
    category_response = admin_client.post(
        "/finance/cost-categories/add",
        data={"name": "Aluguel QA"},
        follow_redirects=False,
    )
    assert category_response.status_code == 303

    with sqlite3.connect(legacy_test_state.database_path) as connection:
        category_id = connection.execute(
            "SELECT id FROM cost_categories WHERE name='Aluguel QA'"
        ).fetchone()[0]

    cost_response = admin_client.post(
        "/finance/recurring-costs/add",
        data={
            "description": "Aluguel escritório QA",
            "category_id": str(category_id),
            "cost_center": "Administrativo",
            "amount": "2450,00",
            "due_day": "10",
            "start_date": "2026-06-01",
            "end_date": "",
            "party_type": "",
            "supplier_id": "",
            "seller_id": "",
            "vendor": "Imobiliária QA",
            "payment_method": "Boleto",
            "bank_account": "Conta principal",
            "notes": "",
        },
        follow_redirects=False,
    )

    assert cost_response.status_code == 303
    page = admin_client.get("/finance?segment=costs&cost_tab=recurring")
    assert "Aluguel escritório QA" in page.text
    assert "Aluguel QA" in page.text


def test_delete_keeps_used_recurring_cost_history(
    admin_client: TestClient,
    legacy_test_state,
) -> None:
    with sqlite3.connect(legacy_test_state.database_path) as connection:
        now = "2026-06-26T10:00:00"
        category_id = connection.execute(
            "INSERT INTO cost_categories(name,active,created_at) VALUES('Internet QA','Sim',?)",
            (now,),
        ).lastrowid
        cost_id = connection.execute(
            """
            INSERT INTO recurring_costs(
                description,category_id,amount,due_day,start_date,status,created_at,updated_at
            ) VALUES('Link QA',?,300,10,'2026-06-01','Ativo',?,?)
            """,
            (category_id, now, now),
        ).lastrowid
        payable_id = connection.execute(
            """
            INSERT INTO payables(description,category,amount,due_date,status,recurring_cost_id,recurring_period)
            VALUES('Link QA · 2026-06','Internet QA',300,'2026-06-10','Aberto',?,'2026-06')
            """,
            (cost_id,),
        ).lastrowid
        connection.execute(
            """
            INSERT INTO recurring_cost_occurrences(
                recurring_cost_id,period,payable_id,amount,due_date,created_at
            ) VALUES(?,?,?,?,?,?)
            """,
            (cost_id, "2026-06", payable_id, 300, "2026-06-10", now),
        )
        connection.commit()

    response = admin_client.post(
        f"/finance/recurring-costs/{cost_id}/delete",
        follow_redirects=False,
    )

    assert response.status_code == 303
    with sqlite3.connect(legacy_test_state.database_path) as connection:
        status, deleted_at = connection.execute(
            "SELECT status,deleted_at FROM recurring_costs WHERE id=?",
            (cost_id,),
        ).fetchone()
        assert status == "Excluído"
        assert deleted_at
        assert connection.execute(
            "SELECT COUNT(*) FROM payables WHERE id=?", (payable_id,)
        ).fetchone()[0] == 1


def test_recurring_cost_can_be_edited_without_changing_generated_payable(
    admin_client: TestClient,
    legacy_test_state,
) -> None:
    with sqlite3.connect(legacy_test_state.database_path) as connection:
        now = "2026-06-26T10:00:00"
        category_id = connection.execute(
            "INSERT INTO cost_categories(name,active,created_at) VALUES('Energia QA','Sim',?)",
            (now,),
        ).lastrowid
        cost_id = connection.execute(
            """
            INSERT INTO recurring_costs(
                description,category_id,cost_center,amount,due_day,start_date,status,created_at,updated_at
            ) VALUES('Energia antiga',?,'Administrativo',500,8,'2026-06-01','Ativo',?,?)
            """,
            (category_id, now, now),
        ).lastrowid
        payable_id = connection.execute(
            """
            INSERT INTO payables(description,category,amount,due_date,status,recurring_cost_id,recurring_period)
            VALUES('Energia antiga · 2026-06','Energia QA',500,'2026-06-08','Aberto',?,'2026-06')
            """,
            (cost_id,),
        ).lastrowid
        connection.execute(
            """
            INSERT INTO recurring_cost_occurrences(
                recurring_cost_id,period,payable_id,amount,due_date,created_at
            ) VALUES(?,?,?,?,?,?)
            """,
            (cost_id, "2026-06", payable_id, 500, "2026-06-08", now),
        )
        connection.commit()

    response = admin_client.post(
        f"/finance/recurring-costs/{cost_id}/edit",
        data={
            "description": "Energia nova",
            "category_id": str(category_id),
            "cost_center": "Administrativo",
            "amount": "650,00",
            "due_day": "12",
            "start_date": "2026-06-01",
            "end_date": "",
            "payment_method": "Débito automático",
            "bank_account": "Principal",
            "notes": "",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    with sqlite3.connect(legacy_test_state.database_path) as connection:
        assert connection.execute(
            "SELECT description,amount,due_day FROM recurring_costs WHERE id=?", (cost_id,)
        ).fetchone() == ("Energia nova", 650, 12)
        assert connection.execute(
            "SELECT description,amount,due_date FROM payables WHERE id=?", (payable_id,)
        ).fetchone() == ("Energia antiga · 2026-06", 500, "2026-06-08")


def test_variable_cost_created_by_user_can_be_deleted(
    admin_client: TestClient,
    legacy_test_state,
) -> None:
    with sqlite3.connect(legacy_test_state.database_path) as connection:
        cost_id = connection.execute(
            """
            INSERT INTO costs(description,category,cost_center,amount,date)
            VALUES('Excluir custo QA','Outros','Administrativo',10,'2026-06-26')
            """
        ).lastrowid
        connection.commit()

    response = admin_client.post(
        f"/finance/costs/{cost_id}/delete",
        follow_redirects=False,
    )

    assert response.status_code == 303
    with sqlite3.connect(legacy_test_state.database_path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM costs WHERE id=?", (cost_id,)
        ).fetchone()[0] == 0
