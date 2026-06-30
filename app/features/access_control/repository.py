import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

SEED_PROFILES = (
    ("Admin", "Acesso administrativo completo", True),
    ("Vendedor", "Operação comercial e relacionamento com clientes", True),
    ("Financeiro", "Rotinas financeiras e relatórios sensíveis", True),
    ("RH", "Colaboradores, benefícios, comissões e folha", True),
    ("TI", "Suporte técnico e integrações", True),
    ("Gestor", "Gestão de equipe e aprovações", True),
)

SEED_PERMISSIONS = (
    ("access.manage", "Administração", "Perfis", "configurar", "Gerenciar perfis e permissões"),
    ("users.manage", "Administração", "Usuários", "configurar", "Gerenciar usuários"),
    ("whatsapp.configure", "Integrações", "WhatsApp Business", "configurar", "Configurar WhatsApp Business"),
    ("hr.view", "RH", "Colaboradores", "visualizar", "Visualizar módulo de RH"),
    ("hr.manage", "RH", "Colaboradores", "editar", "Criar e editar colaboradores"),
    ("hr.payroll.view", "RH", "Folha", "visualizar", "Visualizar folha de pagamento"),
    ("hr.payroll.process", "RH", "Folha", "criar", "Gerar folha mensal"),
    ("hr.payroll.approve", "RH", "Folha", "aprovar", "Aprovar folha mensal"),
    ("hr.payroll.pay", "RH", "Folha", "pagar", "Marcar folha como paga"),
    ("finance.sensitive.view", "Financeiro", "Valores", "visualizar", "Visualizar dados financeiros sensíveis"),
)

ADMIN_PERMISSION_CODES = {permission[0] for permission in SEED_PERMISSIONS}
RH_PERMISSION_CODES = {
    "hr.view",
    "hr.manage",
    "hr.payroll.view",
    "hr.payroll.process",
    "hr.payroll.approve",
}
FINANCE_PERMISSION_CODES = {"finance.sensitive.view", "hr.payroll.pay"}


class AccessControlRepository:
    def __init__(self, database_path: Path | str):
        self.database_path = Path(database_path)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def init_schema(self) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS access_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    is_system TEXT DEFAULT 'Não',
                    is_active TEXT DEFAULT 'Sim',
                    created_at TEXT,
                    updated_at TEXT
                )
                """,
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS access_permissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE NOT NULL,
                    module TEXT,
                    screen TEXT,
                    action TEXT,
                    description TEXT
                )
                """,
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS access_profile_permissions (
                    profile_id INTEGER,
                    permission_id INTEGER,
                    scope TEXT DEFAULT 'all',
                    enabled TEXT DEFAULT 'Não',
                    PRIMARY KEY(profile_id, permission_id)
                )
                """,
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS user_access_profiles (
                    user_id INTEGER,
                    profile_id INTEGER,
                    assigned_by_user_id INTEGER,
                    assigned_at TEXT,
                    PRIMARY KEY(user_id, profile_id)
                )
                """,
            )
            connection.commit()

    def ensure_seed_data(self) -> None:
        self.init_schema()
        now = datetime.now().isoformat(timespec="seconds")
        with self.connect() as connection:
            for name, description, is_system in SEED_PROFILES:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO access_profiles(
                        name, description, is_system, is_active, created_at, updated_at
                    )
                    VALUES(?,?,?,?,?,?)
                    """,
                    (name, description, "Sim" if is_system else "Não", "Sim", now, now),
                )
            for code, module, screen, action, description in SEED_PERMISSIONS:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO access_permissions(
                        code, module, screen, action, description
                    )
                    VALUES(?,?,?,?,?)
                    """,
                    (code, module, screen, action, description),
                )
            admin = connection.execute(
                "SELECT id FROM access_profiles WHERE name='Admin'",
            ).fetchone()
            rh = connection.execute(
                "SELECT id FROM access_profiles WHERE name='RH'",
            ).fetchone()
            financeiro = connection.execute(
                "SELECT id FROM access_profiles WHERE name='Financeiro'",
            ).fetchone()
            permissions = connection.execute("SELECT id, code FROM access_permissions").fetchall()
            for permission in permissions:
                if admin:
                    connection.execute(
                        """
                        INSERT OR IGNORE INTO access_profile_permissions(
                            profile_id, permission_id, scope, enabled
                        )
                        VALUES(?,?,?,?)
                        """,
                        (admin["id"], permission["id"], "all", "Sim"),
                    )
                if rh and permission["code"] in RH_PERMISSION_CODES:
                    connection.execute(
                        """
                        INSERT OR IGNORE INTO access_profile_permissions(
                            profile_id, permission_id, scope, enabled
                        )
                        VALUES(?,?,?,?)
                        """,
                        (rh["id"], permission["id"], "all", "Sim"),
                    )
                if financeiro and permission["code"] in FINANCE_PERMISSION_CODES:
                    connection.execute(
                        """
                        INSERT OR IGNORE INTO access_profile_permissions(
                            profile_id, permission_id, scope, enabled
                        )
                        VALUES(?,?,?,?)
                        """,
                        (financeiro["id"], permission["id"], "all", "Sim"),
                    )
            connection.commit()

    def profiles(self) -> list[dict[str, Any]]:
        self.init_schema()
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM access_profiles ORDER BY is_system DESC, name",
            ).fetchall()
        return [dict(row) for row in rows]

    def permissions(self) -> list[dict[str, Any]]:
        self.init_schema()
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM access_permissions ORDER BY module, screen, action, code",
            ).fetchall()
        return [dict(row) for row in rows]

    def permission_by_code(self, code: str) -> dict[str, Any] | None:
        self.init_schema()
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM access_permissions WHERE code=?",
                (code,),
            ).fetchone()
        return dict(row) if row else None

    def create_profile(
        self,
        *,
        name: str,
        description: str,
        is_system: bool = False,
    ) -> int:
        self.init_schema()
        now = datetime.now().isoformat(timespec="seconds")
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO access_profiles(
                    name, description, is_system, is_active, created_at, updated_at
                )
                VALUES(?,?,?,?,?,?)
                """,
                (
                    name.strip(),
                    description.strip(),
                    "Sim" if is_system else "Não",
                    "Sim",
                    now,
                    now,
                ),
            )
            connection.commit()
            return int(cursor.lastrowid)

    def set_profile_permission(
        self,
        *,
        profile_id: int,
        permission_id: int,
        enabled: bool,
        scope: str = "all",
    ) -> None:
        self.init_schema()
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO access_profile_permissions(
                    profile_id, permission_id, scope, enabled
                )
                VALUES(?,?,?,?)
                ON CONFLICT(profile_id, permission_id) DO UPDATE SET
                    scope=excluded.scope,
                    enabled=excluded.enabled
                """,
                (profile_id, permission_id, scope, "Sim" if enabled else "Não"),
            )
            connection.commit()

    def assign_profile(
        self,
        *,
        user_id: int,
        profile_id: int,
        assigned_by_user_id: int,
    ) -> None:
        self.init_schema()
        now = datetime.now().isoformat(timespec="seconds")
        with self.connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO user_access_profiles(
                    user_id, profile_id, assigned_by_user_id, assigned_at
                )
                VALUES(?,?,?,?)
                """,
                (user_id, profile_id, assigned_by_user_id, now),
            )
            connection.commit()

    def replace_user_profiles(
        self,
        *,
        user_id: int,
        profile_ids: list[int],
        assigned_by_user_id: int,
    ) -> None:
        self.init_schema()
        now = datetime.now().isoformat(timespec="seconds")
        with self.connect() as connection:
            connection.execute(
                "DELETE FROM user_access_profiles WHERE user_id=?",
                (user_id,),
            )
            for profile_id in profile_ids:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO user_access_profiles(
                        user_id, profile_id, assigned_by_user_id, assigned_at
                    )
                    VALUES(?,?,?,?)
                    """,
                    (user_id, profile_id, assigned_by_user_id, now),
                )
            connection.commit()

    def user_profile_ids(self, user_id: int) -> set[int]:
        self.init_schema()
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT profile_id FROM user_access_profiles WHERE user_id=?",
                (user_id,),
            ).fetchall()
        return {int(row["profile_id"]) for row in rows}

    def matrix(self) -> list[dict[str, Any]]:
        self.init_schema()
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    profile.id AS profile_id,
                    profile.name AS profile_name,
                    permission.id AS permission_id,
                    permission.code,
                    permission.module,
                    permission.screen,
                    permission.action,
                    permission.description,
                    COALESCE(profile_permission.enabled, 'Não') AS enabled,
                    COALESCE(profile_permission.scope, 'all') AS scope
                FROM access_profiles profile
                CROSS JOIN access_permissions permission
                LEFT JOIN access_profile_permissions profile_permission
                    ON profile_permission.profile_id = profile.id
                    AND profile_permission.permission_id = permission.id
                WHERE profile.is_active='Sim'
                ORDER BY profile.name, permission.module, permission.screen, permission.action
                """,
            ).fetchall()
        return [dict(row) for row in rows]

    def user_has_permission(
        self,
        user_id: int,
        code: str,
        legacy_role: str | None = None,
    ) -> bool:
        if legacy_role == "admin":
            return True
        self.init_schema()
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT 1
                FROM user_access_profiles user_profile
                JOIN access_profile_permissions profile_permission
                    ON profile_permission.profile_id = user_profile.profile_id
                    AND profile_permission.enabled='Sim'
                JOIN access_permissions permission
                    ON permission.id = profile_permission.permission_id
                JOIN access_profiles profile
                    ON profile.id = user_profile.profile_id
                    AND profile.is_active='Sim'
                WHERE user_profile.user_id=? AND permission.code=?
                LIMIT 1
                """,
                (user_id, code),
            ).fetchone()
        return row is not None
