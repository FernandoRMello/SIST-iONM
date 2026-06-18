import shutil
import sqlite3
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

import app.main as legacy

TEST_ADMIN_USERNAME = "fernando.mello"
TEST_ADMIN_PASSWORD = "TempAdmin!123"
TEST_SELLER_USERNAME = "qa.seller"
TEST_SELLER_PASSWORD = "TempSeller!123"


@dataclass(frozen=True)
class LegacyTestState:
    database_path: Path
    admin_username: str
    admin_password: str
    seller_username: str
    seller_password: str
    ids: dict[str, int]


def _patch_legacy_template_response(monkeypatch: pytest.MonkeyPatch) -> None:
    original_template_response = legacy.templates.TemplateResponse

    def compat_template_response(*args: Any, **kwargs: Any) -> Any:
        if args and isinstance(args[0], str):
            name = args[0]
            context = args[1] if len(args) > 1 else kwargs.get("context")
            request = (context or {}).get("request")
            return original_template_response(request, name, context, **kwargs)
        return original_template_response(*args, **kwargs)

    monkeypatch.setattr(legacy.templates, "TemplateResponse", compat_template_response)


def _seed_legacy_database(database_path: Path) -> LegacyTestState:
    now = "2026-06-18T09:00:00"
    today = "2026-06-18"

    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row

        admin_id = int(
            connection.execute(
                "SELECT id FROM users WHERE username=?",
                (TEST_ADMIN_USERNAME,),
            ).fetchone()[0]
        )
        seller_row = connection.execute(
            "SELECT id, seller_id FROM users WHERE id=2",
        ).fetchone()
        settings_user_id = int(seller_row["id"])
        seller_id = int(seller_row["seller_id"] or 1)
        supplier_id = int(
            connection.execute("SELECT id FROM suppliers ORDER BY id LIMIT 1").fetchone()[0]
        )
        product_id = int(
            connection.execute("SELECT id FROM products ORDER BY id LIMIT 1").fetchone()[0]
        )

        connection.execute(
            """
            UPDATE users
            SET password_hash=?, role='admin', active='Sim', email=?
            WHERE id=?
            """,
            (
                legacy.hash_password(TEST_ADMIN_PASSWORD, salt="seed-admin-qa"),
                "admin.qa@example.invalid",
                admin_id,
            ),
        )
        connection.execute(
            """
            UPDATE users
            SET username=?, password_hash=?, role='vendedor', seller_id=?, active='Sim', email=?
            WHERE id=?
            """,
            (
                TEST_SELLER_USERNAME,
                legacy.hash_password(TEST_SELLER_PASSWORD, salt="seed-seller-qa"),
                seller_id,
                "qa.seller@example.invalid",
                settings_user_id,
            ),
        )
        connection.execute(
            """
            UPDATE sellers
            SET name=?, username=?, email=?, phone=?, commission_rate=?, active='Sim'
            WHERE id=?
            """,
            (
                "Vendedor QA Render",
                TEST_SELLER_USERNAME,
                "qa.seller@example.invalid",
                "(11) 90000-0001",
                10,
                seller_id,
            ),
        )
        connection.execute(
            """
            UPDATE user_profiles
            SET full_name=?, email=?, phone=?, role_title=?, department_id=?, bio=?
            WHERE user_id=?
            """,
            (
                "Administrador QA Render",
                "admin.qa@example.invalid",
                "(11) 90000-0000",
                "Administrador",
                1,
                "Perfil administrativo de caracterização",
                admin_id,
            ),
        )
        connection.execute(
            """
            UPDATE user_profiles
            SET full_name=?, email=?, phone=?, role_title=?, department_id=?, bio=?
            WHERE user_id=?
            """,
            (
                "Vendedor QA Render",
                "qa.seller@example.invalid",
                "(11) 90000-0001",
                "Consultor Comercial",
                2,
                "Perfil vendedor de caracterização",
                settings_user_id,
            ),
        )
        connection.execute(
            """
            UPDATE suppliers
            SET name=?, document=?, contact=?, email=?, phone=?, payment_terms=?, notes=?
            WHERE id=?
            """,
            (
                "Fornecedor QA Render",
                "12.345.678/0001-90",
                "Contato QA",
                "fornecedor.qa@example.invalid",
                "(11) 3000-1000",
                "28 dias",
                "Fornecedor seed de render",
                supplier_id,
            ),
        )
        connection.execute(
            """
            UPDATE products
            SET supplier_id=?, supplier_code=?, internal_code=?, name=?, category=?, supplier_price=?,
                ionm_price=?, min_price=?, active='Sim', detailed_description=?, price_table_1=?, price_table_2=?, price_table_3=?
            WHERE id=?
            """,
            (
                supplier_id,
                "QA-PROD-001",
                "IONM-QA-001",
                "Produto QA Render",
                "Displays",
                9000,
                15000,
                12500,
                "Produto seed de caracterização",
                15500,
                16000,
                16500,
                product_id,
            ),
        )

        client_id = int(
            connection.execute(
                """
                INSERT INTO clients(name, document, contact, email, phone, address, city, state, segment, notes)
                VALUES(?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    "Cliente QA Render",
                    "98.765.432/0001-10",
                    "Compras QA",
                    "cliente.qa@example.invalid",
                    "(11) 4000-2000",
                    "Rua QA, 100",
                    "São Paulo",
                    "SP",
                    "Educação",
                    "Cliente seed de render",
                ),
            ).lastrowid
        )

        connection.execute("DELETE FROM opportunity_items WHERE opportunity_id=1")
        connection.execute("DELETE FROM opportunity_comments WHERE opportunity_id=1")
        connection.execute("DELETE FROM opportunity_notes WHERE opportunity_id=1")
        connection.execute("DELETE FROM opportunity_documents WHERE opportunity_id=1")
        connection.execute(
            """
            UPDATE opportunities
            SET ro_number=?, created_at=?, client_id=?, supplier_id=?, seller_id=?, status=?, probability=?,
                forecast_date=?, next_followup=?, payment_terms=?, notes=?, created_by=?, approved_by=?, approval_status=?
            WHERE id=1
            """,
            (
                "RO-QA-0001",
                today,
                client_id,
                supplier_id,
                seller_id,
                "Lead",
                67,
                "2026-06-30",
                "2026-06-20",
                "Boleto 28 dias",
                "Oportunidade seed de render",
                admin_id,
                admin_id,
                "Não aplicável",
            ),
        )
        connection.executemany(
            """
            INSERT INTO opportunity_items(opportunity_id, product_id, quantity, supplier_unit_price, sale_unit_price, seller_commission_rate)
            VALUES(?,?,?,?,?,?)
            """,
            [
                (1, product_id, 2, 9000, 15000, 10),
                (1, 2, 1, 2990, 6990, 10),
            ],
        )
        connection.execute(
            """
            INSERT INTO opportunity_comments(opportunity_id, user_id, content, created_at)
            VALUES(?,?,?,?)
            """,
            (1, admin_id, "Comentário QA do card", now),
        )
        connection.execute(
            """
            INSERT INTO opportunity_notes(opportunity_id, user_id, title, content, created_at)
            VALUES(?,?,?,?,?)
            """,
            (1, admin_id, "Nota QA", "Anotação QA do card", now),
        )
        connection.execute(
            """
            INSERT INTO opportunity_documents(opportunity_id, user_id, title, doc_type, file_path, created_at)
            VALUES(?,?,?,?,?,?)
            """,
            (1, admin_id, "Documento QA", "Outro", "", now),
        )

        connection.execute("DELETE FROM orders")
        connection.execute("DELETE FROM closings")
        connection.execute("DELETE FROM receivables")
        connection.execute("DELETE FROM payables")
        connection.execute("DELETE FROM costs")
        order_id = int(
            connection.execute(
                """
                INSERT INTO orders(order_number, opportunity_id, created_at, status, invoice_forecast, payment_terms, notes)
                VALUES(?,?,?,?,?,?,?)
                """,
                (
                    "PED-QA-0001",
                    1,
                    today,
                    "Aguardando faturamento",
                    "2026-06-30",
                    "Boleto 28 dias",
                    "Pedido seed de render",
                ),
            ).lastrowid
        )
        connection.execute(
            """
            INSERT INTO closings(order_id, supplier_invoice, ionm_invoice, supplier_invoice_date, ionm_invoice_date,
                expected_receipt_date, receipt_date, fiscal_status, financial_status, received_amount, notes)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                order_id,
                "NF-FORN-QA",
                "NF-IONM-QA",
                today,
                today,
                "2026-07-05",
                "",
                "NF fornecedor recebida",
                "Aguardando recebimento",
                0,
                "Fechamento seed de render",
            ),
        )
        connection.execute(
            """
            INSERT INTO receivables(order_id, client_id, description, category, amount, issue_date, due_date, received_date, status, payment_method, bank_account, notes)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                order_id,
                client_id,
                "Overprice pedido PED-QA-0001",
                "Overprice",
                9000,
                today,
                "2026-07-05",
                "",
                "Aberto",
                "PIX",
                "Conta QA",
                "Conta a receber seed",
            ),
        )
        connection.execute(
            """
            INSERT INTO payables(order_id, seller_id, supplier_id, description, category, amount, issue_date, due_date, paid_date, status, payment_method, bank_account, notes)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                order_id,
                seller_id,
                supplier_id,
                "Comissão pedido PED-QA-0001",
                "Comissão vendedor",
                999,
                today,
                "2026-07-10",
                "",
                "Aberto",
                "TED",
                "Conta QA",
                "Conta a pagar seed",
            ),
        )
        connection.execute(
            """
            INSERT INTO costs(order_id, description, category, cost_center, amount, date, vendor, document, billable, notes)
            VALUES(?,?,?,?,?,?,?,?,?,?)
            """,
            (
                order_id,
                "Frete seed QA",
                "Frete",
                "Operacional",
                450,
                today,
                "Transportadora QA",
                "DOC-QA",
                "Não",
                "Custo seed",
            ),
        )

        connection.execute("DELETE FROM purchases")
        connection.execute(
            """
            INSERT INTO purchases(supplier_id, description, amount, status, issue_date, due_date, notes)
            VALUES(?,?,?,?,?,?,?)
            """,
            (
                supplier_id,
                "Compra seed QA",
                2500,
                "Aberto",
                today,
                "2026-06-25",
                "Compra seed de caracterização",
            ),
        )

        connection.execute("DELETE FROM seller_reviews")
        connection.execute(
            """
            INSERT INTO seller_reviews(seller_id, period, organization_score, followup_score, opportunity_quality_score,
                margin_score, predictability_score, strengths, improvements, notes, created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                seller_id,
                "06/2026",
                5,
                4,
                5,
                4,
                5,
                "Relacionamento",
                "Follow-up",
                "Avaliação seed",
                today,
            ),
        )

        connection.execute("DELETE FROM feed_comments")
        connection.execute("DELETE FROM feed_likes")
        connection.execute("DELETE FROM feed_posts")
        post_id = int(
            connection.execute(
                """
                INSERT INTO feed_posts(user_id, content, attachment_path, created_at)
                VALUES(?,?,?,?)
                """,
                (admin_id, "Post seed QA", "", now),
            ).lastrowid
        )
        connection.execute(
            """
            INSERT INTO feed_comments(post_id, user_id, content, created_at)
            VALUES(?,?,?,?)
            """,
            (post_id, settings_user_id, "Comentário seed QA", now),
        )
        connection.execute(
            """
            INSERT INTO feed_likes(post_id, user_id, created_at)
            VALUES(?,?,?)
            """,
            (post_id, settings_user_id, now),
        )

        connection.commit()

    return LegacyTestState(
        database_path=database_path,
        admin_username=TEST_ADMIN_USERNAME,
        admin_password=TEST_ADMIN_PASSWORD,
        seller_username=TEST_SELLER_USERNAME,
        seller_password=TEST_SELLER_PASSWORD,
        ids={
            "client_id": client_id,
            "supplier_id": supplier_id,
            "product_id": product_id,
            "seller_id": seller_id,
            "opportunity_id": 1,
            "settings_user_id": settings_user_id,
        },
    )


def _login(client: TestClient, username: str, password: str) -> None:
    response = client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/"


@pytest.fixture
def legacy_test_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> LegacyTestState:
    source_database = Path(__file__).resolve().parents[1] / "data" / "overpriceon_web.db"
    test_database = tmp_path / "overpriceon_web.db"
    shutil.copy2(source_database, test_database)
    monkeypatch.setattr(legacy, "DB_PATH", test_database)
    _patch_legacy_template_response(monkeypatch)
    return _seed_legacy_database(test_database)


@pytest.fixture
def legacy_client(legacy_test_state: LegacyTestState) -> Iterator[TestClient]:
    with TestClient(legacy.app) as client:
        yield client


@pytest.fixture
def authenticated_client(legacy_test_state: LegacyTestState) -> Iterator[TestClient]:
    with TestClient(legacy.app) as client:
        _login(client, legacy_test_state.seller_username, legacy_test_state.seller_password)
        yield client


@pytest.fixture
def admin_client(legacy_test_state: LegacyTestState) -> Iterator[TestClient]:
    with TestClient(legacy.app) as client:
        _login(client, legacy_test_state.admin_username, legacy_test_state.admin_password)
        yield client
