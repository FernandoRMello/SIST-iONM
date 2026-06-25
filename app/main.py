
import hashlib
import os
import secrets
import shutil
import socket
import sqlite3
import subprocess
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path

from fastapi import FastAPI, File, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
    Response,
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jinja2 import ChoiceLoader, FileSystemLoader
from starlette.middleware.sessions import SessionMiddleware

from app.features.access_control.repository import AccessControlRepository
from app.features.access_control.routes import create_access_control_router
from app.features.catalog_import.service import (
    MAX_FILE_BYTES,
    SpreadsheetImportError,
    build_template,
    import_rows,
    parse_workbook,
)
from app.features.profile_avatar.service import AvatarValidationError, process_avatar
from app.features.whatsapp.repository import WhatsAppSettingsRepository
from app.features.whatsapp.routes import create_whatsapp_router

APP_NAME = "SIST-iONM"
ASSET_VERSION = "20260623.1"
BASE_DIR = Path(__file__).resolve().parent.parent
SHARED_STATIC_DIR = BASE_DIR / "app" / "shared" / "web" / "static"
LEGACY_TEMPLATE_DIR = BASE_DIR / "app" / "templates"
SHARED_TEMPLATE_DIR = BASE_DIR / "app" / "shared" / "web" / "templates"
DATA_DIR = BASE_DIR / "data"
PDF_DIR = BASE_DIR / "exports" / "pdf"
XML_DIR = BASE_DIR / "exports" / "xml"
UPLOAD_DIR = BASE_DIR / "uploads"
DB_PATH = DATA_DIR / "overpriceon_web.db"
MAX_CHAT_ATTACHMENT_BYTES = 10 * 1024 * 1024
CHAT_ATTACHMENT_EXTENSIONS = {
    ".csv", ".doc", ".docx", ".gif", ".jpeg", ".jpg", ".pdf", ".png",
    ".ppt", ".pptx", ".txt", ".webp", ".xls", ".xlsx", ".zip",
}
CHAT_IMAGE_EXTENSIONS = {".gif", ".jpeg", ".jpg", ".png", ".webp"}

for folder in [DATA_DIR, PDF_DIR, XML_DIR, UPLOAD_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

app = FastAPI(title=APP_NAME)
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SIST_IONM_SESSION_SECRET", "sist-ionm-local-session-key"),
    same_site="lax",
    https_only=os.getenv("SIST_IONM_ENVIRONMENT") == "production",
)
app.mount("/assets", StaticFiles(directory=SHARED_STATIC_DIR), name="assets")
app.mount("/static", StaticFiles(directory=BASE_DIR / "app" / "static"), name="static")
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
templates = Jinja2Templates(directory=LEGACY_TEMPLATE_DIR)
templates.env.loader = ChoiceLoader(
    [FileSystemLoader(LEGACY_TEMPLATE_DIR), FileSystemLoader(SHARED_TEMPLATE_DIR)]
)


@app.middleware("http")
async def response_cache_policy(request: Request, call_next):
    response = await call_next(request)
    content_type = response.headers.get("content-type", "")
    if request.url.path.startswith("/assets/") and request.query_params.get("v"):
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    elif "text/html" in content_type:
        response.headers["Cache-Control"] = "no-store"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; "
        "img-src 'self' data:; connect-src 'self' ws: wss:; "
        "object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
    )
    if request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
    return response

class ChatConnectionManager:
    def __init__(self):
        self.active = {}

    async def connect(self, room_id, websocket: WebSocket):
        await websocket.accept()
        self.active.setdefault(int(room_id), []).append(websocket)

    def disconnect(self, room_id, websocket: WebSocket):
        room_id = int(room_id)
        if room_id in self.active and websocket in self.active[room_id]:
            self.active[room_id].remove(websocket)
        if room_id in self.active and not self.active[room_id]:
            del self.active[room_id]

    async def broadcast(self, room_id, payload):
        room_id = int(room_id)
        for ws in list(self.active.get(room_id, [])):
            try:
                await ws.send_json(payload)
            except Exception:
                self.disconnect(room_id, ws)


chat_manager = ChatConnectionManager()


class NotificationConnectionManager:
    def __init__(self):
        self.active = {}

    async def connect(self, user_id, websocket: WebSocket):
        await websocket.accept()
        self.active.setdefault(int(user_id), []).append(websocket)

    def disconnect(self, user_id, websocket: WebSocket):
        user_id = int(user_id)
        if user_id in self.active and websocket in self.active[user_id]:
            self.active[user_id].remove(websocket)
        if user_id in self.active and not self.active[user_id]:
            del self.active[user_id]

    async def notify(self, user_id, payload):
        user_id = int(user_id)
        for ws in list(self.active.get(user_id, [])):
            try:
                await ws.send_json(payload)
            except Exception:
                self.disconnect(user_id, ws)


notify_manager = NotificationConnectionManager()


STATUS_OPP = [
    "Lead", "R.O cadastrada", "R.O enviada", "Proposta em elaboração",
    "Proposta enviada", "Negociação", "Aguardando cliente",
    "Ganho", "Perdido", "Cancelado", "Faturado", "Recebido"
]
STATUS_FISCAL = [
    "Aguardando faturamento fornecedor", "NF fornecedor recebida",
    "NF iONM pendente", "NF iONM emitida", "Cancelado"
]
STATUS_FINANCE = [
    "Aguardando recebimento", "Recebido parcial", "Recebido",
    "Inadimplente", "Cancelado"
]
COST_CATEGORIES = [
    "Frete", "Instalação", "Deslocamento", "Hospedagem", "Alimentação",
    "Material extra", "Mão de obra", "Imposto", "Taxa bancária",
    "Marketing", "Software", "Administrativo", "Comissão", "Outros"
]
COST_CENTERS = [
    "Comercial", "Operacional", "Financeiro", "Marketing",
    "Instalação", "Administrativo", "Projeto específico"
]

CRUDS = {
    "clients": {
        "title": "Clientes",
        "fields": [
            ("name", "Nome/Razão Social"), ("document", "CNPJ/CPF"),
            ("contact", "Contato"), ("email", "E-mail"), ("phone", "Telefone"),
            ("address", "Endereço"), ("city", "Cidade"), ("state", "UF"),
            ("segment", "Segmento"), ("notes", "Observações")
        ]
    },
    "suppliers": {
        "title": "Fornecedores",
        "fields": [
            ("name", "Nome"), ("document", "CNPJ"), ("contact", "Contato"),
            ("email", "E-mail R.O"), ("phone", "Telefone"),
            ("payment_terms", "Condição comercial"), ("notes", "Observações")
        ]
    },
    "sellers": {
        "title": "Vendedores",
        "fields": [
            ("name", "Nome"), ("username", "Usuário"), ("email", "E-mail"),
            ("phone", "Telefone"), ("commission_rate", "% Comissão"),
            ("active", "Ativo")
        ]
    },
    "products": {
        "title": "Produtos",
        "fields": [
            ("supplier_id", "Fornecedor ID"), ("supplier_code", "Código Fornecedor"),
            ("internal_code", "Código Interno"), ("name", "Produto"),
            ("category", "Categoria"), ("detailed_description", "Descrição detalhada proposta"),
            ("supplier_price", "Preço Fornecedor"), ("ionm_price", "Preço Padrão"),
            ("price_table_1", "Tabela 1"), ("price_table_2", "Tabela 2"), ("price_table_3", "Tabela 3"),
            ("min_price", "Preço Mínimo"), ("active", "Ativo")
        ]
    }
}


@contextmanager
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def q(sql, params=(), one=False):
    with db() as conn:
        cur = conn.execute(sql, params)
        rows = cur.fetchall()
        if one:
            return dict(rows[0]) if rows else None
        return [dict(row) for row in rows]


def exec_sql(sql, params=()):
    with db() as conn:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid


def money(value):
    try:
        v = float(value or 0)
    except Exception:
        v = 0
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def prob_class(value):
    try:
        p = float(value or 0)
    except Exception:
        p = 0
    if p < 25:
        return "prob-red"
    if p < 50:
        return "prob-orange"
    if p < 75:
        return "prob-yellow"
    return "prob-green"


def calc_daily_rate(annual_rate, business_days=252):
    try:
        annual = float(annual_rate or 0)
    except Exception:
        annual = 0
    return ((1 + annual) ** (1 / business_days)) - 1


def num(value):
    if value is None or value == "":
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip().replace("R$", "").replace(" ", "")
    s = (
        s.replace(".", "").replace(",", ".")
        if "," in s and "." in s
        else s.replace(",", ".")
    )
    try:
        return float(s)
    except Exception:
        return 0.0


def pagination_values(total, page=1, page_size=25):
    try:
        normalized_total = max(0, int(total or 0))
    except (TypeError, ValueError):
        normalized_total = 0
    try:
        normalized_page = max(1, int(page or 1))
    except (TypeError, ValueError):
        normalized_page = 1
    try:
        normalized_size = int(page_size or 25)
    except (TypeError, ValueError):
        normalized_size = 25
    if normalized_size < 1:
        normalized_size = 25
    normalized_size = min(normalized_size, 100)
    pages = max(1, (normalized_total + normalized_size - 1) // normalized_size)
    normalized_page = min(normalized_page, pages)
    return {
        "page": normalized_page,
        "page_size": normalized_size,
        "total": normalized_total,
        "pages": pages,
    }


def today():
    return date.today().isoformat()


def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120000)
    return salt + "$" + dk.hex()


def verify_password(password, stored):
    try:
        salt, _ = stored.split("$", 1)
        return hash_password(password, salt) == stored
    except Exception:
        return False


def current_user(request: Request):
    return request.session.get("user")


def render(request: Request, template: str, context=None):
    user = current_user(request)
    ctx = context or {}
    ctx.update({
        "request": request,
        "user": user,
        "cfg": config(),
        "money": money,
        "prob_class": prob_class,
        "app_name": APP_NAME,
        "asset_version": ASSET_VERSION,
        "current_path": request.url.path,
        "can_view_bi": bool(user and user.get("username") == "fernando.mello"),
    })
    return templates.TemplateResponse(template, ctx)


def require_login(request: Request):
    return bool(current_user(request))


def require_admin(request: Request):
    user = current_user(request)
    return bool(user and user.get("role") == "admin")


app.include_router(
    create_access_control_router(
        database_path=lambda: DB_PATH,
        render=render,
        require_admin=require_admin,
        current_user=current_user,
    ),
)

app.include_router(
    create_whatsapp_router(
        database_path=lambda: DB_PATH,
        render=render,
        require_admin=require_admin,
        current_user=current_user,
    ),
)


def can_view_seller(request: Request, seller_id):
    user = current_user(request)
    if not user:
        return False
    if user.get("role") == "admin":
        return True
    return int(user.get("seller_id") or 0) == int(seller_id or 0)


def redirect_login():
    return RedirectResponse("/login", status_code=303)


def config():
    return {r["key"]: r["value"] for r in q("SELECT key,value FROM config")}


def set_config(key, value):
    exec_sql("INSERT OR REPLACE INTO config(key,value) VALUES(?,?)", (key, value))


def log(request, entity, entity_id, action, description):
    user = current_user(request) or {}
    exec_sql(
        "INSERT INTO history(created_at,user_id,entity,entity_id,action,description) VALUES(?,?,?,?,?,?)",
        (datetime.now().isoformat(timespec="seconds"), user.get("id"), entity, entity_id, action, description)
    )


def get_general_room_id():
    room = q("SELECT id FROM chat_rooms WHERE room_type='general' ORDER BY id LIMIT 1", one=True)
    if room:
        return room["id"]
    return exec_sql("INSERT INTO chat_rooms(name,created_at,room_type) VALUES(?,?,?)",
                    ("Geral", datetime.now().isoformat(timespec="seconds"), "general"))


def get_or_create_private_room(user_a, user_b):
    a, b = sorted([int(user_a), int(user_b)])
    room = q("""
        SELECT id FROM chat_rooms
        WHERE room_type='private' AND user1_id=? AND user2_id=?
        LIMIT 1
    """, (a, b), one=True)
    if room:
        return room["id"]

    ua = q("SELECT username FROM users WHERE id=?", (a,), one=True) or {"username": str(a)}
    ub = q("SELECT username FROM users WHERE id=?", (b,), one=True) or {"username": str(b)}
    return exec_sql("""
        INSERT INTO chat_rooms(name,created_at,room_type,user1_id,user2_id)
        VALUES(?,?,?,?,?)
    """, (f"{ua['username']} ↔ {ub['username']}", datetime.now().isoformat(timespec="seconds"), "private", a, b))


def user_can_access_room(user_id, room_id):
    room = q("SELECT * FROM chat_rooms WHERE id=?", (room_id,), one=True)
    if not room:
        return False
    if room.get("room_type") == "general":
        return True
    return int(user_id) in [int(room.get("user1_id") or 0), int(room.get("user2_id") or 0)]


def room_participants(room_id):
    room = q("SELECT * FROM chat_rooms WHERE id=?", (room_id,), one=True)
    if not room:
        return []
    if room.get("room_type") == "general":
        return [r["id"] for r in q("SELECT id FROM users WHERE active='Sim'")]
    return [int(room.get("user1_id") or 0), int(room.get("user2_id") or 0)]


def mark_room_read(user_id, room_id):
    last_message = q(
        "SELECT COALESCE(MAX(id),0) AS id FROM chat_messages WHERE room_id=?",
        (room_id,),
        one=True,
    )
    last_message_id = int((last_message or {}).get("id") or 0)
    exec_sql(
        """
        INSERT INTO chat_read_state(user_id,room_id,last_read_message_id,updated_at)
        VALUES(?,?,?,?)
        ON CONFLICT(user_id,room_id) DO UPDATE SET
            last_read_message_id=excluded.last_read_message_id,
            updated_at=excluded.updated_at
        """,
        (user_id, room_id, last_message_id, datetime.now().isoformat(timespec="seconds")),
    )
    return last_message_id


def unread_room_counts(user_id):
    rows = q(
        """
        SELECT cr.id AS room_id, COUNT(cm.id) AS unread
        FROM chat_rooms cr
        LEFT JOIN chat_read_state rs
          ON rs.room_id=cr.id AND rs.user_id=?
        LEFT JOIN chat_messages cm
          ON cm.room_id=cr.id
         AND cm.id>COALESCE(rs.last_read_message_id,0)
         AND cm.user_id<>?
        WHERE cr.room_type='general' OR cr.user1_id=? OR cr.user2_id=?
        GROUP BY cr.id
        """,
        (user_id, user_id, user_id, user_id),
    )
    return {int(row["room_id"]): int(row["unread"] or 0) for row in rows}


def chat_message_payload(message_id):
    row = q("""
        SELECT cm.*, u.username, up.full_name, up.avatar_path
        FROM chat_messages cm
        LEFT JOIN users u ON u.id=cm.user_id
        LEFT JOIN user_profiles up ON up.user_id=u.id
        WHERE cm.id=?
    """, (message_id,), one=True)
    if not row:
        return None
    return {
        "id": row["id"],
        "room_id": row["room_id"],
        "user_id": row["user_id"],
        "username": row.get("username") or "",
        "full_name": row.get("full_name") or row.get("username") or "",
        "avatar_path": row.get("avatar_path") or "",
        "content": row.get("content") or "",
        "attachment_path": row.get("attachment_path") or "",
        "attachment_is_image": is_chat_image(row.get("attachment_path")),
        "created_at": row.get("created_at") or "",
    }


def is_chat_image(attachment_path):
    return Path(str(attachment_path or "")).suffix.lower() in CHAT_IMAGE_EXTENSIONS


def mark_chat_images(messages):
    for message in messages:
        message["attachment_is_image"] = is_chat_image(message.get("attachment_path"))
    return messages


async def publish_chat_message(message_id, sender_id):
    payload = chat_message_payload(message_id)
    if not payload:
        return None
    room_id = int(payload["room_id"])
    await chat_manager.broadcast(room_id, payload)
    for user_id in room_participants(room_id):
        if int(user_id) != int(sender_id):
            await notify_manager.notify(
                user_id,
                {"type": "chat_message", "room_id": room_id, "message": payload},
            )
    return payload


async def save_chat_attachment(attachment):
    if not attachment or not attachment.filename:
        return ""
    suffix = Path(attachment.filename).suffix.lower()
    if suffix not in CHAT_ATTACHMENT_EXTENSIONS:
        raise ValueError("Formato de arquivo não permitido no chat.")
    content = await attachment.read(MAX_CHAT_ATTACHMENT_BYTES + 1)
    if len(content) > MAX_CHAT_ATTACHMENT_BYTES:
        raise ValueError("O anexo excede o limite de 10 MiB.")
    safe_name = (
        f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}_"
        f"{secrets.token_hex(6)}{suffix}"
    )
    (UPLOAD_DIR / safe_name).write_bytes(content)
    return f"uploads/{safe_name}"


def next_number(prefix, table, column):
    year = datetime.now().year
    like = f"{prefix}-{year}-%"
    row = q(f"SELECT COUNT(*) AS c FROM {table} WHERE {column} LIKE ?", (like,), one=True)
    return f"{prefix}-{year}-{int(row['c']) + 1:04d}"


def ensure_column(table, column, column_type):
    existing = q(f"PRAGMA table_info({table})")
    names = [row["name"] for row in existing]
    if column not in names:
        exec_sql(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")


def init_db():
    with db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT
        );

        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'vendedor',
            seller_id INTEGER,
            active TEXT DEFAULT 'Sim'
        );

        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            document TEXT,
            contact TEXT,
            email TEXT,
            phone TEXT,
            address TEXT,
            city TEXT,
            state TEXT,
            segment TEXT,
            notes TEXT
        );

        CREATE TABLE IF NOT EXISTS suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            document TEXT,
            contact TEXT,
            email TEXT,
            phone TEXT,
            payment_terms TEXT,
            notes TEXT
        );

        CREATE TABLE IF NOT EXISTS sellers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            username TEXT,
            email TEXT,
            phone TEXT,
            commission_rate REAL DEFAULT 10,
            active TEXT DEFAULT 'Sim'
        );

        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier_id INTEGER,
            supplier_code TEXT,
            internal_code TEXT,
            name TEXT NOT NULL,
            category TEXT,
            supplier_price REAL DEFAULT 0,
            ionm_price REAL DEFAULT 0,
            min_price REAL DEFAULT 0,
            active TEXT DEFAULT 'Sim'
        );

        CREATE TABLE IF NOT EXISTS opportunities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ro_number TEXT UNIQUE,
            created_at TEXT,
            client_id INTEGER,
            supplier_id INTEGER,
            seller_id INTEGER,
            status TEXT DEFAULT 'Lead',
            probability REAL DEFAULT 40,
            forecast_date TEXT,
            next_followup TEXT,
            payment_terms TEXT,
            lost_reason TEXT,
            notes TEXT,
            created_by INTEGER,
            approved_by INTEGER,
            approval_status TEXT DEFAULT 'Não aplicável'
        );

        CREATE TABLE IF NOT EXISTS opportunity_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            opportunity_id INTEGER,
            product_id INTEGER,
            quantity REAL DEFAULT 1,
            supplier_unit_price REAL DEFAULT 0,
            sale_unit_price REAL DEFAULT 0,
            seller_commission_rate REAL DEFAULT 10
        );

        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_number TEXT UNIQUE,
            opportunity_id INTEGER,
            created_at TEXT,
            status TEXT DEFAULT 'Aguardando faturamento',
            invoice_forecast TEXT,
            payment_terms TEXT,
            notes TEXT
        );

        CREATE TABLE IF NOT EXISTS closings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER UNIQUE,
            supplier_invoice TEXT,
            ionm_invoice TEXT,
            supplier_invoice_date TEXT,
            ionm_invoice_date TEXT,
            expected_receipt_date TEXT,
            receipt_date TEXT,
            fiscal_status TEXT DEFAULT 'Aguardando faturamento fornecedor',
            financial_status TEXT DEFAULT 'Aguardando recebimento',
            received_amount REAL DEFAULT 0,
            notes TEXT
        );

        CREATE TABLE IF NOT EXISTS receivables (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            client_id INTEGER,
            description TEXT,
            category TEXT,
            amount REAL DEFAULT 0,
            issue_date TEXT,
            due_date TEXT,
            received_date TEXT,
            status TEXT DEFAULT 'Aberto',
            payment_method TEXT,
            bank_account TEXT,
            notes TEXT
        );

        CREATE TABLE IF NOT EXISTS payables (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            seller_id INTEGER,
            supplier_id INTEGER,
            description TEXT,
            category TEXT,
            amount REAL DEFAULT 0,
            issue_date TEXT,
            due_date TEXT,
            paid_date TEXT,
            status TEXT DEFAULT 'Aberto',
            payment_method TEXT,
            bank_account TEXT,
            notes TEXT
        );

        CREATE TABLE IF NOT EXISTS costs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            description TEXT,
            category TEXT,
            cost_center TEXT,
            amount REAL DEFAULT 0,
            date TEXT,
            vendor TEXT,
            document TEXT,
            billable TEXT DEFAULT 'Não',
            notes TEXT
        );

        CREATE TABLE IF NOT EXISTS seller_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seller_id INTEGER,
            period TEXT,
            organization_score INTEGER DEFAULT 0,
            followup_score INTEGER DEFAULT 0,
            opportunity_quality_score INTEGER DEFAULT 0,
            margin_score INTEGER DEFAULT 0,
            predictability_score INTEGER DEFAULT 0,
            strengths TEXT,
            improvements TEXT,
            notes TEXT,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT,
            user_id INTEGER,
            entity TEXT,
            entity_id INTEGER,
            action TEXT,
            description TEXT
        );
        """)
        conn.commit()

    defaults = {
        "company_name": "iONM SOLUÇÕES E TECNOLOGIA",
        "company_document": "",
        "company_email": "atendimento@ionm.com.br",
        "company_phone": "",
        "company_address": "",
        "server_printer": "",
        "sumatra_path": "",
        "allow_server_print": "Não",
    }
    for key, value in defaults.items():
        if not q("SELECT key FROM config WHERE key=?", (key,), one=True):
            set_config(key, value)

    ensure_column("opportunities", "payment_terms", "TEXT")

    if not q("SELECT id FROM users WHERE username=?", ("fernando.mello",), one=True):
        exec_sql(
            "INSERT INTO users(username,password_hash,role,active) VALUES(?,?,?,?)",
            ("fernando.mello", hash_password("Dr@g3378"), "admin", "Sim")
        )

    if not q("SELECT id FROM suppliers LIMIT 1", one=True):
        exec_sql(
            "INSERT INTO suppliers(name,email,contact) VALUES(?,?,?)",
            ("Fornecedor Padrão", "comercial@fornecedor.com.br", "Comercial")
        )

    if not q("SELECT id FROM sellers LIMIT 1", one=True):
        seller_id = exec_sql(
            "INSERT INTO sellers(name,username,email,commission_rate) VALUES(?,?,?,?)",
            ("Vendedor Padrão", "vendedor", "vendedor@empresa.com.br", 10)
        )
        exec_sql(
            "INSERT OR IGNORE INTO users(username,password_hash,role,seller_id,active) VALUES(?,?,?,?,?)",
            ("vendedor", hash_password("123456"), "vendedor", seller_id, "Sim")
        )

    if not q("SELECT id FROM products LIMIT 1", one=True):
        supplier_id = q("SELECT id FROM suppliers LIMIT 1", one=True)["id"]
        samples = [
            (supplier_id, "DISP65", "IONM-65", 'Display Interativo 65"', "Displays", 8500, 17990, 13000),
            (supplier_id, "SB100", "IONM-SB", "SoundBar Bluetooth 100W RMS", "Acessórios", 2990, 6990, 4500),
            (supplier_id, "SUP-ELET", "IONM-SE", "Suporte Elétrico com Regulagem de Altura", "Acessórios", 4490, 5990, 5200),
        ]
        for row in samples:
            exec_sql(
                """INSERT INTO products(supplier_id,supplier_code,internal_code,name,category,supplier_price,ionm_price,min_price)
                   VALUES(?,?,?,?,?,?,?,?)""",
                row
            )



def init_portal_modules():
    WhatsAppSettingsRepository(DB_PATH).init_schema()
    AccessControlRepository(DB_PATH).ensure_seed_data()
    exec_sql("""CREATE TABLE IF NOT EXISTS feed_posts (id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,content TEXT,attachment_path TEXT,created_at TEXT)""")
    exec_sql("""CREATE TABLE IF NOT EXISTS feed_likes (id INTEGER PRIMARY KEY AUTOINCREMENT,post_id INTEGER,user_id INTEGER,created_at TEXT,UNIQUE(post_id,user_id))""")
    exec_sql("""CREATE TABLE IF NOT EXISTS feed_reactions (id INTEGER PRIMARY KEY AUTOINCREMENT,post_id INTEGER,user_id INTEGER,reaction TEXT CHECK(reaction IN ('like','dislike')),created_at TEXT,UNIQUE(post_id,user_id))""")
    exec_sql("""INSERT OR IGNORE INTO feed_reactions(post_id,user_id,reaction,created_at) SELECT post_id,user_id,'like',created_at FROM feed_likes""")
    exec_sql("""CREATE TABLE IF NOT EXISTS feed_comments (id INTEGER PRIMARY KEY AUTOINCREMENT,post_id INTEGER,user_id INTEGER,content TEXT,created_at TEXT)""")
    exec_sql("""CREATE TABLE IF NOT EXISTS departments (id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT,parent_id INTEGER,manager_user_id INTEGER)""")
    exec_sql("""CREATE TABLE IF NOT EXISTS user_profiles (user_id INTEGER PRIMARY KEY,full_name TEXT,email TEXT,phone TEXT,role_title TEXT,department_id INTEGER,bio TEXT,avatar_path TEXT)""")
    exec_sql("""CREATE TABLE IF NOT EXISTS role_permissions (id INTEGER PRIMARY KEY AUTOINCREMENT,role TEXT,module TEXT,can_view TEXT DEFAULT 'Sim',can_create TEXT DEFAULT 'Não',can_edit TEXT DEFAULT 'Não',can_delete TEXT DEFAULT 'Não',UNIQUE(role,module))""")
    exec_sql("""CREATE TABLE IF NOT EXISTS role_email_settings (id INTEGER PRIMARY KEY AUTOINCREMENT,role TEXT UNIQUE,email_from TEXT,smtp_host TEXT,smtp_port TEXT,smtp_user TEXT,smtp_password TEXT,signature TEXT)""")
    exec_sql("""CREATE TABLE IF NOT EXISTS opportunity_comments (id INTEGER PRIMARY KEY AUTOINCREMENT,opportunity_id INTEGER,user_id INTEGER,content TEXT,created_at TEXT)""")
    exec_sql("""CREATE TABLE IF NOT EXISTS opportunity_notes (id INTEGER PRIMARY KEY AUTOINCREMENT,opportunity_id INTEGER,user_id INTEGER,title TEXT,content TEXT,created_at TEXT)""")
    exec_sql("""CREATE TABLE IF NOT EXISTS opportunity_documents (id INTEGER PRIMARY KEY AUTOINCREMENT,opportunity_id INTEGER,user_id INTEGER,title TEXT,doc_type TEXT,file_path TEXT,created_at TEXT)""")
    exec_sql("""CREATE TABLE IF NOT EXISTS purchases (id INTEGER PRIMARY KEY AUTOINCREMENT,supplier_id INTEGER,description TEXT,amount REAL DEFAULT 0,status TEXT DEFAULT 'Aberto',issue_date TEXT,due_date TEXT,notes TEXT)""")
    exec_sql("""CREATE TABLE IF NOT EXISTS chat_rooms (id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT,created_at TEXT)""")
    exec_sql("""CREATE TABLE IF NOT EXISTS chat_messages (id INTEGER PRIMARY KEY AUTOINCREMENT,room_id INTEGER,user_id INTEGER,content TEXT,attachment_path TEXT,created_at TEXT)""")
    exec_sql("""CREATE TABLE IF NOT EXISTS chat_read_state (user_id INTEGER,room_id INTEGER,last_read_message_id INTEGER DEFAULT 0,updated_at TEXT,PRIMARY KEY(user_id,room_id))""")
    ensure_column("chat_rooms", "room_type", "TEXT DEFAULT 'general'")
    ensure_column("chat_rooms", "user1_id", "INTEGER")
    ensure_column("chat_rooms", "user2_id", "INTEGER")

    ensure_column("products", "detailed_description", "TEXT")
    ensure_column("products", "price_table_1", "REAL DEFAULT 0")
    ensure_column("products", "price_table_2", "REAL DEFAULT 0")
    ensure_column("products", "price_table_3", "REAL DEFAULT 0")
    ensure_column("users", "email", "TEXT")
    ensure_column("users", "smtp_email", "TEXT")
    ensure_column("users", "smtp_password", "TEXT")
    ensure_column("users", "smtp_host", "TEXT")
    ensure_column("users", "smtp_port", "TEXT")
    ensure_column("users", "email_signature", "TEXT")

    modules = ["feed","crm","pipeline","clientes","produtos","backoffice","dashboard","chat","admin","bi"]
    for role in ["admin","vendedor","financeiro"]:
        exec_sql("""INSERT OR IGNORE INTO role_email_settings(role,email_from,smtp_host,smtp_port,smtp_user,smtp_password,signature) VALUES(?,?,?,?,?,?,?)""",
                 (role, "", "", "587", "", "", ""))
    for role in ["admin","vendedor","financeiro"]:
        for module in modules:
            can = "Sim"
            if role != "admin" and module in ["admin","bi"]:
                can = "Não"
            exec_sql("""INSERT OR IGNORE INTO role_permissions(role,module,can_view,can_create,can_edit,can_delete) VALUES(?,?,?,?,?,?)""",
                     (role, module, can, can if can=="Sim" else "Não", can if can=="Sim" else "Não", "Sim" if role=="admin" else "Não"))

    if not q("SELECT id FROM departments LIMIT 1", one=True):
        exec_sql("INSERT INTO departments(name,parent_id,manager_user_id) VALUES(?,?,?)", ("Diretoria", None, 1))
        exec_sql("INSERT INTO departments(name,parent_id,manager_user_id) VALUES(?,?,?)", ("Comercial", 1, None))
        exec_sql("INSERT INTO departments(name,parent_id,manager_user_id) VALUES(?,?,?)", ("Financeiro", 1, None))
        exec_sql("INSERT INTO departments(name,parent_id,manager_user_id) VALUES(?,?,?)", ("Operações", 1, None))
    if not q("SELECT id FROM chat_rooms WHERE room_type='general' LIMIT 1", one=True):
        exec_sql("INSERT INTO chat_rooms(name,created_at,room_type) VALUES(?,?,?)", ("Geral", datetime.now().isoformat(timespec="seconds"), "general"))
    exec_sql("UPDATE chat_rooms SET room_type='general' WHERE room_type IS NULL OR room_type=''" )
    for u in q("SELECT id, username, email FROM users"):
        if not q("SELECT user_id FROM user_profiles WHERE user_id=?", (u["id"],), one=True):
            exec_sql("INSERT INTO user_profiles(user_id,full_name,email,phone,role_title,department_id,bio) VALUES(?,?,?,?,?,?,?)",
                     (u["id"], u["username"], u.get("email") or "", "", "", None, ""))


def opp_summary(opp_id):
    opp = q("""
        SELECT o.*, c.name AS client_name, c.document AS client_doc,
               s.name AS supplier_name,
               v.name AS seller_name, v.commission_rate AS seller_default_commission
        FROM opportunities o
        LEFT JOIN clients c ON c.id=o.client_id
        LEFT JOIN suppliers s ON s.id=o.supplier_id
        LEFT JOIN sellers v ON v.id=o.seller_id
        WHERE o.id=?
    """, (opp_id,), one=True)
    if not opp:
        return None

    items = q("""
        SELECT oi.*, p.name AS product_name, p.min_price
        FROM opportunity_items oi
        LEFT JOIN products p ON p.id=oi.product_id
        WHERE oi.opportunity_id=?
        ORDER BY oi.id
    """, (opp_id,))

    total_supplier = total_sale = total_over = total_comm = 0
    below_min = False
    for item in items:
        qty = float(item["quantity"] or 0)
        supplier_total = qty * float(item["supplier_unit_price"] or 0)
        sale_total = qty * float(item["sale_unit_price"] or 0)
        over = sale_total - supplier_total
        comm = over * float(item["seller_commission_rate"] or 0) / 100
        if float(item["sale_unit_price"] or 0) < float(item.get("min_price") or 0):
            below_min = True
        item.update({
            "supplier_total": supplier_total,
            "sale_total": sale_total,
            "overprice": over,
            "commission": comm,
        })
        total_supplier += supplier_total
        total_sale += sale_total
        total_over += over
        total_comm += comm

    opp["items"] = items
    opp["total_supplier"] = total_supplier
    opp["total_sale"] = total_sale
    opp["total_overprice"] = total_over
    opp["total_commission"] = total_comm
    opp["weighted_overprice"] = total_over * float(opp["probability"] or 0) / 100
    opp["below_min"] = below_min
    return opp


def opportunity_summaries(seller_id=None, limit=25, offset=0):
    where = "WHERE o.seller_id=?" if seller_id else ""
    params = [seller_id] if seller_id else []
    params.extend([int(limit), int(offset)])
    rows = q(f"""
        WITH item_totals AS (
            SELECT
                oi.opportunity_id,
                COALESCE(SUM(oi.quantity * oi.supplier_unit_price), 0) AS total_supplier,
                COALESCE(SUM(oi.quantity * oi.sale_unit_price), 0) AS total_sale,
                COALESCE(SUM(oi.quantity * (oi.sale_unit_price - oi.supplier_unit_price)), 0) AS total_overprice,
                COALESCE(SUM(oi.quantity * (oi.sale_unit_price - oi.supplier_unit_price) * oi.seller_commission_rate / 100.0), 0) AS total_commission,
                MAX(CASE WHEN oi.sale_unit_price < COALESCE(p.min_price, 0) THEN 1 ELSE 0 END) AS below_min
            FROM opportunity_items oi
            LEFT JOIN products p ON p.id=oi.product_id
            GROUP BY oi.opportunity_id
        )
        SELECT
            o.*, c.name AS client_name, c.document AS client_doc,
            s.name AS supplier_name,
            v.name AS seller_name, v.commission_rate AS seller_default_commission,
            COALESCE(t.total_supplier, 0) AS total_supplier,
            COALESCE(t.total_sale, 0) AS total_sale,
            COALESCE(t.total_overprice, 0) AS total_overprice,
            COALESCE(t.total_commission, 0) AS total_commission,
            COALESCE(t.below_min, 0) AS below_min
        FROM opportunities o
        LEFT JOIN clients c ON c.id=o.client_id
        LEFT JOIN suppliers s ON s.id=o.supplier_id
        LEFT JOIN sellers v ON v.id=o.seller_id
        LEFT JOIN item_totals t ON t.opportunity_id=o.id
        {where}
        ORDER BY o.id DESC
        LIMIT ? OFFSET ?
    """, params)
    for row in rows:
        row["weighted_overprice"] = (
            float(row.get("total_overprice") or 0)
            * float(row.get("probability") or 0)
            / 100
        )
        row["below_min"] = bool(row.get("below_min"))
    return rows


def opportunity_kpis(seller_id=None):
    where = "WHERE o.seller_id=?" if seller_id else ""
    params = (seller_id,) if seller_id else ()
    return q(f"""
        WITH item_totals AS (
            SELECT
                oi.opportunity_id,
                COALESCE(SUM(oi.quantity * (oi.sale_unit_price - oi.supplier_unit_price)), 0) AS total_overprice,
                COALESCE(SUM(oi.quantity * (oi.sale_unit_price - oi.supplier_unit_price) * oi.seller_commission_rate / 100.0), 0) AS total_commission
            FROM opportunity_items oi
            GROUP BY oi.opportunity_id
        )
        SELECT
            COUNT(o.id) AS opps,
            COALESCE(SUM(
                CASE WHEN o.status NOT IN ('Ganho','Perdido','Cancelado','Faturado','Recebido')
                THEN COALESCE(t.total_overprice, 0) * COALESCE(o.probability, 0) / 100.0
                ELSE 0 END
            ), 0) AS weighted_overprice,
            COALESCE(SUM(COALESCE(t.total_commission, 0)), 0) AS total_commission
        FROM opportunities o
        LEFT JOIN item_totals t ON t.opportunity_id=o.id
        {where}
    """, params, one=True)


def order_summary(order_id):
    order = q("""
        SELECT od.*, o.ro_number, o.id AS opportunity_id
        FROM orders od
        LEFT JOIN opportunities o ON o.id=od.opportunity_id
        WHERE od.id=?
    """, (order_id,), one=True)
    if not order:
        return None
    order["opp"] = opp_summary(order["opportunity_id"])
    order["closing"] = q("SELECT * FROM closings WHERE order_id=?", (order_id,), one=True)
    costs = q("SELECT COALESCE(SUM(amount),0) AS total FROM costs WHERE order_id=?", (order_id,), one=True)
    order["costs_total"] = costs["total"] if costs else 0
    return order


def seller_metrics(seller_id=None):
    where = ""
    params = []
    if seller_id:
        where = "WHERE o.seller_id=?"
        params = [seller_id]

    rows = q(f"SELECT id,status FROM opportunities o {where}", params)
    summaries = [opp_summary(r["id"]) for r in rows]

    sent_status = ["Proposta enviada", "Negociação", "Aguardando cliente", "Ganho", "Faturado", "Recebido"]
    won_status = ["Ganho", "Faturado", "Recebido"]

    sent = [o for o in summaries if o.get("status") in sent_status]
    won = [o for o in summaries if o.get("status") in won_status]

    total_sale = sum(float(o.get("total_sale") or 0) for o in summaries)
    total_over = sum(float(o.get("total_overprice") or 0) for o in summaries)
    total_comm = sum(float(o.get("total_commission") or 0) for o in summaries)
    conversion = (len(won) / len(sent) * 100) if sent else 0

    return {
        "opps": len(summaries),
        "sent": len(sent),
        "won": len(won),
        "conversion": conversion,
        "total_sale": total_sale,
        "total_over": total_over,
        "total_comm": total_comm,
    }


def commission_rows(seller_id=None):
    where = ""
    params = []
    if seller_id:
        where = "WHERE s.id=?"
        params = [seller_id]

    rows = q(f"""
        SELECT s.id AS seller_id, s.name AS seller_name,
               od.order_number, c.name AS client_name, p.name AS product_name,
               oi.quantity, oi.supplier_unit_price, oi.sale_unit_price,
               oi.seller_commission_rate,
               cl.financial_status, pa.status AS payable_status
        FROM opportunity_items oi
        JOIN opportunities o ON o.id=oi.opportunity_id
        JOIN sellers s ON s.id=o.seller_id
        LEFT JOIN orders od ON od.opportunity_id=o.id
        LEFT JOIN clients c ON c.id=o.client_id
        LEFT JOIN products p ON p.id=oi.product_id
        LEFT JOIN closings cl ON cl.order_id=od.id
        LEFT JOIN payables pa ON pa.order_id=od.id AND pa.seller_id=s.id
        {where}
        ORDER BY s.name, od.id DESC, o.id DESC
    """, params)

    out = []
    for row in rows:
        qty = float(row["quantity"] or 0)
        supplier_total = qty * float(row["supplier_unit_price"] or 0)
        sale_total = qty * float(row["sale_unit_price"] or 0)
        over = sale_total - supplier_total
        comm = over * float(row["seller_commission_rate"] or 0) / 100

        if row.get("payable_status") == "Pago":
            status = "Paga"
        elif row.get("financial_status") == "Recebido":
            status = "Liberada"
        elif row.get("order_number"):
            status = "Aguardando faturamento"
        else:
            status = "Prevista"

        row.update({
            "supplier_total": supplier_total,
            "sale_total": sale_total,
            "overprice": over,
            "commission": comm,
            "commission_status": status,
        })
        out.append(row)
    return out



def generate_pdf_ro_supplier(opp_id):
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_RIGHT
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    opp = opp_summary(opp_id)
    path = PDF_DIR / f"{opp['ro_number']}_RO_fornecedor.pdf"

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Cell", parent=styles["Normal"], fontSize=8, leading=10))
    styles.add(ParagraphStyle(name="RightCell", parent=styles["Normal"], fontSize=8, leading=10, alignment=TA_RIGHT))
    styles.add(ParagraphStyle(name="Small", parent=styles["Normal"], fontSize=9, leading=12))

    doc = SimpleDocTemplate(str(path), pagesize=landscape(A4), rightMargin=22, leftMargin=22, topMargin=22, bottomMargin=22)
    story = []
    cfg = config()

    story.append(Paragraph(f"<b>{cfg.get('company_name','SIST-iONM')}</b>", styles["Title"]))
    story.append(Paragraph(f"Registro de Oportunidade para Fornecedor — {opp['ro_number']}", styles["Heading2"]))
    story.append(Paragraph("Documento para avaliação comercial, reserva/registro da oportunidade e faturamento futuro.", styles["Small"]))
    story.append(Spacer(1, 10))

    info = [
        ["Cliente", opp.get("client_name") or "", "Documento", opp.get("client_doc") or ""],
        ["Fornecedor", opp.get("supplier_name") or "", "Vendedor", opp.get("seller_name") or ""],
        ["Status", opp.get("status") or "", "Probabilidade", f"{float(opp.get('probability') or 0):.0f}%"],
        ["Previsão fechamento", opp.get("forecast_date") or "", "Pagamento desejado", opp.get("payment_terms") or ""],
    ]
    info_table = Table(info, colWidths=[110, 270, 130, 270])
    info_table.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.35, colors.HexColor("#D8E2EF")),
        ("BACKGROUND", (0,0), (0,-1), colors.HexColor("#EEF2FF")),
        ("BACKGROUND", (2,0), (2,-1), colors.HexColor("#EEF2FF")),
        ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTNAME", (2,0), (2,-1), "Helvetica-Bold"),
        ("PADDING", (0,0), (-1,-1), 6),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 10))

    rows = [[
        Paragraph("Produto", styles["Cell"]),
        Paragraph("Qtd", styles["RightCell"]),
        Paragraph("Valor fornecedor", styles["RightCell"]),
        Paragraph("Valor negociado", styles["RightCell"]),
        Paragraph("Overprice", styles["RightCell"]),
        Paragraph("Comissão", styles["RightCell"]),
    ]]

    for item in opp["items"]:
        rows.append([
            Paragraph(str(item["product_name"]), styles["Cell"]),
            Paragraph(str(item["quantity"]), styles["RightCell"]),
            Paragraph(money(item["supplier_total"]), styles["RightCell"]),
            Paragraph(money(item["sale_total"]), styles["RightCell"]),
            Paragraph(money(item["overprice"]), styles["RightCell"]),
            Paragraph(money(item["commission"]), styles["RightCell"]),
        ])

    rows.append([
        Paragraph("<b>TOTAL</b>", styles["Cell"]),
        "",
        Paragraph(f"<b>{money(opp['total_supplier'])}</b>", styles["RightCell"]),
        Paragraph(f"<b>{money(opp['total_sale'])}</b>", styles["RightCell"]),
        Paragraph(f"<b>{money(opp['total_overprice'])}</b>", styles["RightCell"]),
        Paragraph(f"<b>{money(opp['total_commission'])}</b>", styles["RightCell"]),
    ])

    table = Table(rows, colWidths=[360, 55, 100, 110, 100, 100], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#0B1730")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("GRID", (0,0), (-1,-1), 0.35, colors.HexColor("#D8E2EF")),
        ("BACKGROUND", (0,-1), (-1,-1), colors.HexColor("#F1F5F9")),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("PADDING", (0,0), (-1,-1), 5),
    ]))
    story.append(table)

    if opp.get("notes"):
        story.append(Spacer(1, 10))
        story.append(Paragraph(f"<b>Observações:</b> {opp.get('notes')}", styles["Small"]))

    doc.build(story)
    return path


def generate_pdf_proposal(opp_id):
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_RIGHT
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    opp = opp_summary(opp_id)
    path = PDF_DIR / f"{opp['ro_number']}_proposta.pdf"

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Cell", parent=styles["Normal"], fontSize=8, leading=10))
    styles.add(ParagraphStyle(name="RightCell", parent=styles["Normal"], fontSize=8, leading=10, alignment=TA_RIGHT))

    doc = SimpleDocTemplate(str(path), pagesize=landscape(A4), rightMargin=22, leftMargin=22, topMargin=22, bottomMargin=22)
    story = []
    cfg = config()

    story.append(Paragraph(f"<b>{cfg.get('company_name','SIST-iONM')}</b>", styles["Title"]))
    story.append(Paragraph(f"Proposta Comercial — {opp['ro_number']} | Cliente: {opp['client_name'] or ''}", styles["Normal"]))
    story.append(Spacer(1, 10))

    rows = [[
        Paragraph("Produto", styles["Cell"]),
        Paragraph("Qtd", styles["RightCell"]),
        Paragraph("Valor unit.", styles["RightCell"]),
        Paragraph("Total", styles["RightCell"]),
    ]]

    for item in opp["items"]:
        rows.append([
            Paragraph(str(item["product_name"]), styles["Cell"]),
            Paragraph(str(item["quantity"]), styles["RightCell"]),
            Paragraph(money(item["sale_unit_price"]), styles["RightCell"]),
            Paragraph(money(item["sale_total"]), styles["RightCell"]),
        ])

    rows.append([
        Paragraph("<b>TOTAL</b>", styles["Cell"]),
        "",
        "",
        Paragraph(f"<b>{money(opp['total_sale'])}</b>", styles["RightCell"])
    ])

    table = Table(rows, colWidths=[500, 60, 110, 110], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#0B1730")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("GRID", (0,0), (-1,-1), 0.35, colors.HexColor("#D8E2EF")),
        ("BACKGROUND", (0,-1), (-1,-1), colors.HexColor("#F1F5F9")),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("PADDING", (0,0), (-1,-1), 5),
    ]))
    story.append(table)
    doc.build(story)
    return path


def print_pdf_server(path):
    cfg = config()
    if cfg.get("allow_server_print") != "Sim":
        return False, "Impressão no servidor não está habilitada."
    printer = cfg.get("server_printer", "").strip()
    sumatra = cfg.get("sumatra_path", "").strip()
    if not printer or not sumatra or not os.path.exists(sumatra):
        return False, "Configure impressora e caminho do SumatraPDF em Configurações."
    try:
        subprocess.Popen([sumatra, "-print-to", printer, str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True, "Arquivo enviado para impressão no servidor."
    except Exception as exc:
        return False, str(exc)


def create_financial_entries(order_id, form):
    order = order_summary(order_id)
    opp = order["opp"]

    exec_sql("DELETE FROM receivables WHERE order_id=?", (order_id,))
    rec_status = "Recebido" if form.get("financial_status") == "Recebido" else "Aberto"

    exec_sql("""
        INSERT INTO receivables(order_id,client_id,description,category,amount,issue_date,due_date,received_date,status,notes)
        VALUES(?,?,?,?,?,?,?,?,?,?)
    """, (
        order_id, opp["client_id"], f"Overprice pedido {order['order_number']}",
        "Overprice", opp["total_overprice"], form.get("ionm_invoice_date"),
        form.get("expected_receipt_date"), form.get("receipt_date"), rec_status,
        "Gerado pelo fechamento do pedido"
    ))

    if form.get("financial_status") == "Recebido":
        exec_sql("DELETE FROM payables WHERE order_id=? AND category='Comissão vendedor'", (order_id,))
        exec_sql("""
            INSERT INTO payables(order_id,seller_id,description,category,amount,issue_date,due_date,status,notes)
            VALUES(?,?,?,?,?,?,?,?,?)
        """, (
            order_id, opp["seller_id"], f"Comissão pedido {order['order_number']}",
            "Comissão vendedor", opp["total_commission"], today(),
            form.get("receipt_date"), "Aberto",
            "Comissão liberada após recebimento do overprice"
        ))


@app.on_event("startup")
def startup():
    init_db()
    init_portal_modules()


@app.get("/favicon.ico")
def favicon():
    return PlainTextResponse("", status_code=204)


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if current_user(request):
        return RedirectResponse("/", status_code=303)
    return render(request, "login.html", {"error": None})


@app.post("/login")
async def login(request: Request):
    form = await request.form()
    username = str(form.get("username", "")).strip()
    password = str(form.get("password", ""))

    row = q("SELECT * FROM users WHERE username=? AND active='Sim'", (username,), one=True)
    if not row or not verify_password(password, row["password_hash"]):
        return render(request, "login.html", {"error": "Usuário ou senha inválidos."})

    request.session["user"] = {
        "id": row["id"],
        "username": row["username"],
        "role": row["role"],
        "seller_id": row["seller_id"],
    }
    return RedirectResponse("/", status_code=303)


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    if not require_login(request):
        return redirect_login()

    user = current_user(request)
    seller_id = None if user.get("role") == "admin" else user.get("seller_id")
    opportunities = opportunity_summaries(seller_id=seller_id, limit=20)
    opportunity_totals = opportunity_kpis(seller_id=seller_id)
    financial_totals = q("""
        SELECT
            (SELECT COUNT(*) FROM orders) AS orders,
            (SELECT COALESCE(SUM(amount),0) FROM receivables WHERE status IN ('Aberto','Vencido','Inadimplente')) AS recv,
            (SELECT COALESCE(SUM(amount),0) FROM payables WHERE status='Aberto') AS pay
    """, one=True)

    kpis = {
        "opps": opportunity_totals["opps"],
        "orders": financial_totals["orders"],
        "over": opportunity_totals["weighted_overprice"],
        "comm": opportunity_totals["total_commission"],
        "recv": financial_totals["recv"],
        "pay": financial_totals["pay"],
    }
    return render(request, "dashboard.html", {"kpis": kpis, "opps": opportunities})



# ---------------- Portal CRM V2 ----------------

@app.get("/feed", response_class=HTMLResponse)
def feed(request: Request):
    if not require_login(request): return redirect_login()
    user_id = current_user(request)["id"]
    posts = q("""
        SELECT fp.*, u.username, up.full_name, up.avatar_path,
               (SELECT COUNT(*) FROM feed_reactions fr WHERE fr.post_id=fp.id AND fr.reaction='like') AS likes_count,
               (SELECT COUNT(*) FROM feed_reactions fr WHERE fr.post_id=fp.id AND fr.reaction='dislike') AS dislikes_count,
               (SELECT reaction FROM feed_reactions fr WHERE fr.post_id=fp.id AND fr.user_id=?) AS current_reaction
        FROM feed_posts fp
        LEFT JOIN users u ON u.id=fp.user_id
        LEFT JOIN user_profiles up ON up.user_id=u.id
        ORDER BY fp.id DESC
    """, (user_id,))
    comments = q("""SELECT fc.*, u.username, up.full_name, up.avatar_path FROM feed_comments fc LEFT JOIN users u ON u.id=fc.user_id LEFT JOIN user_profiles up ON up.user_id=u.id ORDER BY fc.id ASC""")
    by_post = {}
    for c in comments: by_post.setdefault(c["post_id"], []).append(c)
    return render(request, "feed.html", {"posts": posts, "comments_by_post": by_post})

@app.post("/feed/post")
async def feed_post(request: Request, attachment: UploadFile = File(None)):
    if not require_login(request): return redirect_login()
    form = await request.form(); content = str(form.get("content","")).strip(); attachment_path = ""
    if attachment and attachment.filename:
        safe = f"feed_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{attachment.filename}".replace(" ","_")
        dest = UPLOAD_DIR / safe; dest.write_bytes(await attachment.read())
        attachment_path = str(dest.relative_to(BASE_DIR)).replace("\\","/")
    if content or attachment_path:
        exec_sql("INSERT INTO feed_posts(user_id,content,attachment_path,created_at) VALUES(?,?,?,?)",(current_user(request)["id"],content,attachment_path,datetime.now().isoformat(timespec="seconds")))
    return RedirectResponse("/feed", status_code=303)

@app.get("/feed/like/{post_id}")
def feed_like(request: Request, post_id:int):
    if not require_login(request): return redirect_login()
    toggle_feed_reaction(post_id, current_user(request)["id"], "like")
    return RedirectResponse("/feed", status_code=303)


def toggle_feed_reaction(post_id, user_id, reaction):
    current = q(
        "SELECT reaction FROM feed_reactions WHERE post_id=? AND user_id=?",
        (post_id, user_id),
        one=True,
    )
    if current and current["reaction"] == reaction:
        exec_sql("DELETE FROM feed_reactions WHERE post_id=? AND user_id=?", (post_id, user_id))
    elif current:
        exec_sql(
            "UPDATE feed_reactions SET reaction=?,created_at=? WHERE post_id=? AND user_id=?",
            (reaction, datetime.now().isoformat(timespec="seconds"), post_id, user_id),
        )
    else:
        exec_sql(
            "INSERT INTO feed_reactions(post_id,user_id,reaction,created_at) VALUES(?,?,?,?)",
            (post_id, user_id, reaction, datetime.now().isoformat(timespec="seconds")),
        )


@app.post("/feed/reaction/{post_id}/{reaction}")
def feed_reaction(request: Request, post_id: int, reaction: str):
    if not require_login(request): return redirect_login()
    if reaction not in {"like", "dislike"}:
        return PlainTextResponse("Reação inválida", status_code=400)
    if not q("SELECT id FROM feed_posts WHERE id=?", (post_id,), one=True):
        return PlainTextResponse("Publicação não encontrada", status_code=404)
    toggle_feed_reaction(post_id, current_user(request)["id"], reaction)
    return RedirectResponse("/feed", status_code=303)

@app.post("/feed/comment/{post_id}")
async def feed_comment(request: Request, post_id:int):
    if not require_login(request): return redirect_login()
    form=await request.form(); content=str(form.get("content","")).strip()
    if content: exec_sql("INSERT INTO feed_comments(post_id,user_id,content,created_at) VALUES(?,?,?,?)",(post_id,current_user(request)["id"],content,datetime.now().isoformat(timespec="seconds")))
    return RedirectResponse("/feed", status_code=303)

@app.get("/profile", response_class=HTMLResponse)
def profile(request: Request):
    if not require_login(request): return redirect_login()
    prof=q("""SELECT up.*,u.username,u.role,d.name AS department_name FROM user_profiles up LEFT JOIN users u ON u.id=up.user_id LEFT JOIN departments d ON d.id=up.department_id WHERE up.user_id=?""",(current_user(request)["id"],),one=True)
    return render(request,"profile.html",{"profile":prof,"departments":q("SELECT * FROM departments ORDER BY name")})

@app.post("/profile/save")
async def profile_save(request: Request):
    if not require_login(request): return redirect_login()
    f=await request.form(); uid=current_user(request)["id"]
    exec_sql("UPDATE user_profiles SET full_name=?,email=?,phone=?,role_title=?,department_id=?,bio=? WHERE user_id=?",(f.get("full_name"),f.get("email"),f.get("phone"),f.get("role_title"),f.get("department_id") or None,f.get("bio"),uid))
    exec_sql("UPDATE users SET email=? WHERE id=?",(f.get("email"),uid))
    return RedirectResponse("/profile", status_code=303)


@app.post("/profile/avatar")
async def profile_avatar(request: Request, avatar: UploadFile = File(None)):
    if not require_login(request):
        return redirect_login()
    uid = current_user(request)["id"]
    if avatar and avatar.filename:
        try:
            normalized = process_avatar(await avatar.read(10 * 1024 * 1024 + 1))
        except AvatarValidationError as exc:
            await avatar.close()
            return PlainTextResponse(str(exc), status_code=400)
        safe_name = f"profile_{uid}_{secrets.token_hex(8)}.jpg"
        dest = UPLOAD_DIR / safe_name
        dest.write_bytes(normalized)
        avatar_path = f"uploads/{safe_name}"
        exec_sql("UPDATE user_profiles SET avatar_path=? WHERE user_id=?", (avatar_path, uid))
        await avatar.close()
    return RedirectResponse("/profile", status_code=303)


@app.get("/orgchart", response_class=HTMLResponse)
def orgchart(request: Request):
    if not require_login(request): return redirect_login()
    deps=q("SELECT d.*,u.username AS manager_username FROM departments d LEFT JOIN users u ON u.id=d.manager_user_id ORDER BY COALESCE(d.parent_id,0),d.name")
    people=q("SELECT up.*,u.username,u.role,d.name AS department_name FROM user_profiles up LEFT JOIN users u ON u.id=up.user_id LEFT JOIN departments d ON d.id=up.department_id ORDER BY d.name,up.full_name")
    return render(request,"orgchart.html",{"departments":deps,"people":people})

@app.get("/chat", response_class=HTMLResponse)
def chat(request: Request, room_id: int = None, page: int = 1, page_size: int = 25):
    if not require_login(request):
        return redirect_login()
    user = current_user(request)
    if room_id is None:
        room_id = get_general_room_id()
    if not user_can_access_room(user["id"], room_id):
        return PlainTextResponse("Sem permissão para este chat.", status_code=403)

    rooms = q("""
        SELECT * FROM chat_rooms
        WHERE room_type='general'
           OR user1_id=?
           OR user2_id=?
        ORDER BY room_type, name
    """, (user["id"], user["id"]))

    users = q("""
        SELECT u.id, u.username, u.role, up.full_name, up.avatar_path
        FROM users u
        LEFT JOIN user_profiles up ON up.user_id=u.id
        WHERE u.active='Sim' AND u.id<>?
        ORDER BY COALESCE(up.full_name,u.username)
    """, (user["id"],))

    total = q(
        "SELECT COUNT(*) AS total FROM chat_messages WHERE room_id=?",
        (room_id,),
        one=True,
    )["total"]
    pager = pagination_values(total, page, page_size)
    offset = (pager["page"] - 1) * pager["page_size"]
    msgs = q("""
        SELECT cm.*,u.username,up.full_name,up.avatar_path
        FROM chat_messages cm
        LEFT JOIN users u ON u.id=cm.user_id
        LEFT JOIN user_profiles up ON up.user_id=u.id
        WHERE cm.room_id=?
        ORDER BY cm.id DESC
        LIMIT ? OFFSET ?
    """, (room_id, pager["page_size"], offset))
    msgs.reverse()
    mark_chat_images(msgs)

    return render(request,"chat.html",{
        "rooms": rooms,
        "users": users,
        "room_id": room_id,
        "messages": msgs,
        "pager": pager,
    })


@app.post("/chat/send")
async def chat_send(request: Request, attachment: UploadFile = File(None)):
    if not require_login(request):
        return redirect_login()
    f = await request.form()
    user = current_user(request)
    room_id = int(f.get("room_id") or get_general_room_id())
    if not user_can_access_room(user["id"], room_id):
        return PlainTextResponse("Sem permissão para este chat.", status_code=403)

    wants_json = "application/json" in request.headers.get("accept", "")
    content = str(f.get("content", "")).strip()
    try:
        attachment_path = await save_chat_attachment(attachment)
    except ValueError as exc:
        if wants_json:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)
        return PlainTextResponse(str(exc), status_code=400)
    finally:
        if attachment:
            await attachment.close()

    if not content and not attachment_path:
        if wants_json:
            return JSONResponse(
                {"ok": False, "error": "Digite uma mensagem ou selecione um arquivo."},
                status_code=400,
            )
        return RedirectResponse(f"/chat?room_id={room_id}", status_code=303)

    message_id = exec_sql(
        "INSERT INTO chat_messages(room_id,user_id,content,attachment_path,created_at) VALUES(?,?,?,?,?)",
        (room_id, user["id"], content, attachment_path, datetime.now().isoformat(timespec="seconds")),
    )
    payload = await publish_chat_message(message_id, user["id"])
    if wants_json:
        return {"ok": True, "message": payload}
    return RedirectResponse(f"/chat?room_id={room_id}", status_code=303)


@app.get("/admin/permissions", response_class=HTMLResponse)
def admin_permissions(request: Request):
    if not require_login(request): return redirect_login()
    if not require_admin(request): return PlainTextResponse("Sem permissão",status_code=403)
    return render(request,"permissions.html",{"rows":q("SELECT * FROM role_permissions ORDER BY role,module")})

@app.post("/admin/permissions/save")
async def admin_permissions_save(request: Request):
    if not require_login(request): return redirect_login()
    if not require_admin(request): return PlainTextResponse("Sem permissão",status_code=403)
    f=await request.form()
    for r in q("SELECT * FROM role_permissions"):
        rid=r["id"]
        exec_sql("UPDATE role_permissions SET can_view=?,can_create=?,can_edit=?,can_delete=? WHERE id=?",("Sim" if f.get(f"view_{rid}") else "Não","Sim" if f.get(f"create_{rid}") else "Não","Sim" if f.get(f"edit_{rid}") else "Não","Sim" if f.get(f"delete_{rid}") else "Não",rid))
    return RedirectResponse("/admin/permissions", status_code=303)

@app.get("/opportunities/{opp_id}/card", response_class=HTMLResponse)
def opportunity_card(request: Request, opp_id:int):
    if not require_login(request): return redirect_login()
    opp=opp_summary(opp_id)
    if not opp or not can_view_seller(request,opp["seller_id"]): return PlainTextResponse("Sem permissão", status_code=403)
    comments=q("SELECT oc.*,u.username,up.full_name FROM opportunity_comments oc LEFT JOIN users u ON u.id=oc.user_id LEFT JOIN user_profiles up ON up.user_id=u.id WHERE oc.opportunity_id=? ORDER BY oc.id ASC",(opp_id,))
    notes=q("SELECT n.*,u.username FROM opportunity_notes n LEFT JOIN users u ON u.id=n.user_id WHERE n.opportunity_id=? ORDER BY n.id DESC",(opp_id,))
    docs=q("SELECT d.*,u.username FROM opportunity_documents d LEFT JOIN users u ON u.id=d.user_id WHERE d.opportunity_id=? ORDER BY d.id DESC",(opp_id,))
    products = q("SELECT * FROM products WHERE active='Sim' ORDER BY name")
    return render(request,"opportunity_card.html",{"o":opp,"comments":comments,"notes":notes,"docs":docs,"products":products})

@app.post("/opportunities/{opp_id}/comment")
async def opportunity_comment(request: Request, opp_id:int):
    if not require_login(request): return redirect_login()
    f=await request.form(); content=str(f.get("content","")).strip()
    if content: exec_sql("INSERT INTO opportunity_comments(opportunity_id,user_id,content,created_at) VALUES(?,?,?,?)",(opp_id,current_user(request)["id"],content,datetime.now().isoformat(timespec="seconds")))
    return RedirectResponse(f"/opportunities/{opp_id}/card", status_code=303)

@app.post("/opportunities/{opp_id}/note")
async def opportunity_note(request: Request, opp_id:int):
    if not require_login(request): return redirect_login()
    f=await request.form()
    exec_sql("INSERT INTO opportunity_notes(opportunity_id,user_id,title,content,created_at) VALUES(?,?,?,?,?)",(opp_id,current_user(request)["id"],f.get("title"),f.get("content"),datetime.now().isoformat(timespec="seconds")))
    return RedirectResponse(f"/opportunities/{opp_id}/card", status_code=303)

@app.post("/opportunities/{opp_id}/document")
async def opportunity_document(request: Request, opp_id:int, file: UploadFile = File(None)):
    if not require_login(request): return redirect_login()
    f=await request.form(); fp=""
    if file and file.filename:
        safe=f"opp_{opp_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}".replace(" ","_")
        dest=UPLOAD_DIR/safe; dest.write_bytes(await file.read()); fp=str(dest.relative_to(BASE_DIR)).replace("\\","/")
    exec_sql("INSERT INTO opportunity_documents(opportunity_id,user_id,title,doc_type,file_path,created_at) VALUES(?,?,?,?,?,?)",(opp_id,current_user(request)["id"],f.get("title"),f.get("doc_type"),fp,datetime.now().isoformat(timespec="seconds")))
    return RedirectResponse(f"/opportunities/{opp_id}/card", status_code=303)

@app.get("/backoffice/purchases", response_class=HTMLResponse)
def purchases(request: Request):
    if not require_login(request): return redirect_login()
    if current_user(request).get("role") not in ["admin","financeiro"]: return PlainTextResponse("Sem permissão",status_code=403)
    rows=q("SELECT p.*,s.name AS supplier_name FROM purchases p LEFT JOIN suppliers s ON s.id=p.supplier_id ORDER BY p.id DESC")
    return render(request,"purchases.html",{"rows":rows,"suppliers":q("SELECT * FROM suppliers ORDER BY name")})

@app.post("/backoffice/purchases/add")
async def purchases_add(request: Request):
    if not require_login(request): return redirect_login()
    if current_user(request).get("role") not in ["admin","financeiro"]: return PlainTextResponse("Sem permissão",status_code=403)
    f=await request.form()
    exec_sql("INSERT INTO purchases(supplier_id,description,amount,status,issue_date,due_date,notes) VALUES(?,?,?,?,?,?,?)",(f.get("supplier_id"),f.get("description"),num(f.get("amount")),f.get("status") or "Aberto",f.get("issue_date"),f.get("due_date"),f.get("notes")))
    return RedirectResponse("/backoffice/purchases", status_code=303)



@app.post("/chat/quick-send")
async def chat_quick_send(request: Request):
    if not require_login(request):
        return redirect_login()
    form = await request.form()
    user = current_user(request)
    content = str(form.get("content", "")).strip()
    room_id = int(form.get("room_id") or get_general_room_id())
    if not user_can_access_room(user["id"], room_id):
        return PlainTextResponse("Sem permissão para este chat.", status_code=403)
    if content:
        exec_sql("INSERT INTO chat_messages(room_id,user_id,content,attachment_path,created_at) VALUES(?,?,?,?,?)",
                 (room_id, user["id"], content, "", datetime.now().isoformat(timespec="seconds")))
    return RedirectResponse(form.get("next") or request.headers.get("referer") or "/feed", status_code=303)


@app.get("/chat/private/{other_user_id}")
def chat_private_redirect(request: Request, other_user_id: int):
    if not require_login(request):
        return redirect_login()
    user = current_user(request)
    other = q("SELECT id FROM users WHERE id=? AND active='Sim'", (other_user_id,), one=True)
    if not other:
        return PlainTextResponse("Usuário não encontrado", status_code=404)
    room_id = get_or_create_private_room(user["id"], other_user_id)
    return RedirectResponse(f"/chat?room_id={room_id}", status_code=303)


@app.get("/chat/context")
def chat_context(request: Request):
    if not require_login(request):
        return JSONResponse({"ok": False, "error": "not_logged"}, status_code=401)
    user = current_user(request)
    general_id = get_general_room_id()
    users = q("""
        SELECT u.id, u.username, u.role, up.full_name, up.avatar_path
        FROM users u
        LEFT JOIN user_profiles up ON up.user_id=u.id
        WHERE u.active='Sim' AND u.id<>?
        ORDER BY COALESCE(up.full_name,u.username)
    """, (user["id"],))
    rooms = q("""
        SELECT * FROM chat_rooms
        WHERE room_type='general'
           OR user1_id=?
           OR user2_id=?
        ORDER BY room_type, name
    """, (user["id"], user["id"]))
    return {
        "ok": True,
        "current_user_id": user["id"],
        "current_username": user.get("username"),
        "general_room_id": general_id,
        "users": users,
        "rooms": rooms,
        "unread": unread_room_counts(user["id"]),
    }


@app.post("/chat/read/{room_id}")
def chat_mark_read(request: Request, room_id: int):
    if not require_login(request):
        return JSONResponse({"ok": False, "error": "not_logged"}, status_code=401)
    user = current_user(request)
    if not user_can_access_room(user["id"], room_id):
        return JSONResponse({"ok": False, "error": "forbidden"}, status_code=403)
    mark_room_read(user["id"], room_id)
    return {"ok": True, "room_id": room_id, "unread": 0}


@app.get("/chat/private-room/{other_user_id}")
def chat_private_room(request: Request, other_user_id: int):
    if not require_login(request):
        return JSONResponse({"ok": False, "error": "not_logged"}, status_code=401)
    user = current_user(request)
    other = q("SELECT id FROM users WHERE id=? AND active='Sim'", (other_user_id,), one=True)
    if not other:
        return JSONResponse({"ok": False, "error": "user_not_found"}, status_code=404)
    room_id = get_or_create_private_room(user["id"], other_user_id)
    return {"ok": True, "room_id": room_id}


@app.get("/chat/messages/{room_id}")
def chat_messages(request: Request, room_id: int, page: int = 1, page_size: int = 25):
    if not require_login(request):
        return JSONResponse({"ok": False, "error": "not_logged"}, status_code=401)
    user = current_user(request)
    if not user_can_access_room(user["id"], room_id):
        return JSONResponse({"ok": False, "error": "forbidden"}, status_code=403)
    total = q(
        "SELECT COUNT(*) AS total FROM chat_messages WHERE room_id=?",
        (room_id,),
        one=True,
    )["total"]
    pager = pagination_values(total, page, page_size)
    offset = (pager["page"] - 1) * pager["page_size"]
    rows = q("""
        SELECT cm.*, u.username, up.full_name, up.avatar_path
        FROM chat_messages cm
        LEFT JOIN users u ON u.id=cm.user_id
        LEFT JOIN user_profiles up ON up.user_id=u.id
        WHERE cm.room_id=?
        ORDER BY cm.id DESC
        LIMIT ? OFFSET ?
    """, (room_id, pager["page_size"], offset))
    rows.reverse()
    mark_chat_images(rows)
    return {"ok": True, "messages": rows, "pagination": pager}


@app.websocket("/ws/notify")
async def websocket_notify(websocket: WebSocket):
    user = websocket.session.get("user") if hasattr(websocket, "session") else None
    if not user:
        await websocket.close(code=1008)
        return
    await notify_manager.connect(user["id"], websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        notify_manager.disconnect(user["id"], websocket)
    except Exception:
        notify_manager.disconnect(user["id"], websocket)


@app.websocket("/ws/chat/{room_id}")
async def websocket_chat(websocket: WebSocket, room_id: int):
    user = websocket.session.get("user") if hasattr(websocket, "session") else None
    if not user or not user_can_access_room(user["id"], room_id):
        await websocket.close(code=1008)
        return
    await chat_manager.connect(room_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            content = str(data.get("content", "")).strip()
            if not content:
                continue
            msg_id = exec_sql("""
                INSERT INTO chat_messages(room_id,user_id,content,attachment_path,created_at)
                VALUES(?,?,?,?,?)
            """, (room_id, user["id"], content, "", datetime.now().isoformat(timespec="seconds")))
            await publish_chat_message(msg_id, user["id"])
    except WebSocketDisconnect:
        chat_manager.disconnect(room_id, websocket)
    except Exception:
        chat_manager.disconnect(room_id, websocket)



# ---------------- Cadastros ----------------

CATALOG_IMPORT_TABLES = {"clients", "suppliers"}


def catalog_import_authorized(request: Request, table: str) -> bool:
    if table == "clients":
        return require_login(request)
    return require_admin(request)


def catalog_import_feedback(request: Request, table: str):
    feedback = request.session.get("catalog_import_feedback")
    if feedback and feedback.get("table") == table:
        request.session.pop("catalog_import_feedback", None)
        return feedback
    return None


@app.get("/cadastros/{table}/import-template")
def catalog_import_template(request: Request, table: str):
    if not require_login(request):
        return redirect_login()
    if table not in CATALOG_IMPORT_TABLES:
        return PlainTextResponse("Importação não encontrada", status_code=404)
    if not catalog_import_authorized(request, table):
        return PlainTextResponse("Sem permissão", status_code=403)

    filename = "modelo_clientes.xlsx" if table == "clients" else "modelo_fornecedores.xlsx"
    return Response(
        content=build_template(table),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/cadastros/{table}/import")
async def catalog_import_upload(
    request: Request,
    table: str,
    file: UploadFile = File(...),
):
    if not require_login(request):
        return redirect_login()
    if table not in CATALOG_IMPORT_TABLES:
        return PlainTextResponse("Importação não encontrada", status_code=404)
    if not catalog_import_authorized(request, table):
        return PlainTextResponse("Sem permissão", status_code=403)

    feedback = {
        "table": table,
        "created": 0,
        "updated": 0,
        "ignored": 0,
        "errors": [],
    }
    try:
        if not file.filename or not file.filename.lower().endswith(".xlsx"):
            raise SpreadsheetImportError("Use um arquivo .xlsx baseado no modelo oficial.")
        content = await file.read(MAX_FILE_BYTES + 1)
        rows = parse_workbook(table, content)
        with db() as connection:
            result = import_rows(connection, table, rows)
        feedback.update(result.as_dict())
    except SpreadsheetImportError as exc:
        feedback["errors"] = [str(exc)]
    except sqlite3.DatabaseError:
        feedback["errors"] = ["Falha ao gravar a importação. Nenhum dado foi alterado."]
    finally:
        await file.close()

    request.session["catalog_import_feedback"] = feedback
    return RedirectResponse(f"/cadastros/{table}", status_code=303)

@app.get("/cadastros/{table}", response_class=HTMLResponse)
def crud_list(request: Request, table: str, page: int = 1, page_size: int = 25):
    if not require_login(request):
        return redirect_login()
    if table not in CRUDS:
        return PlainTextResponse("Cadastro não encontrado", status_code=404)
    total = q(f"SELECT COUNT(*) AS total FROM {table}", one=True)["total"]
    pager = pagination_values(total, page, page_size)
    offset = (pager["page"] - 1) * pager["page_size"]
    rows = q(
        f"SELECT * FROM {table} ORDER BY id DESC LIMIT ? OFFSET ?",
        (pager["page_size"], offset),
    )
    return render(request, "crud.html", {
        "table": table,
        "meta": CRUDS[table],
        "rows": rows,
        "edit": None,
        "pager": pager,
        "import_feedback": catalog_import_feedback(request, table),
    })


@app.get("/cadastros/{table}/edit/{record_id}", response_class=HTMLResponse)
def crud_edit(request: Request, table: str, record_id: int, page: int = 1, page_size: int = 25):
    if not require_login(request):
        return redirect_login()
    if table not in CRUDS:
        return PlainTextResponse("Cadastro não encontrado", status_code=404)
    total = q(f"SELECT COUNT(*) AS total FROM {table}", one=True)["total"]
    pager = pagination_values(total, page, page_size)
    offset = (pager["page"] - 1) * pager["page_size"]
    rows = q(
        f"SELECT * FROM {table} ORDER BY id DESC LIMIT ? OFFSET ?",
        (pager["page_size"], offset),
    )
    edit = q(f"SELECT * FROM {table} WHERE id=?", (record_id,), one=True)
    return render(request, "crud.html", {
        "table": table,
        "meta": CRUDS[table],
        "rows": rows,
        "edit": edit,
        "pager": pager,
        "import_feedback": catalog_import_feedback(request, table),
    })


@app.post("/cadastros/{table}/save-form")
async def crud_save(request: Request, table: str):
    if not require_login(request):
        return redirect_login()
    if table not in CRUDS:
        return PlainTextResponse("Cadastro não encontrado", status_code=404)

    user = current_user(request)
    if user["role"] != "admin" and table not in ["clients"]:
        return PlainTextResponse("Sem permissão", status_code=403)

    form = await request.form()
    fields = CRUDS[table]["fields"]
    data = {key: str(form.get(key, "")).strip() for key, _ in fields}
    record_id = str(form.get("id", "")).strip()

    if table == "sellers":
        data["commission_rate"] = num(data.get("commission_rate"))
    if table == "products":
        for key in ["supplier_id", "supplier_price", "ionm_price", "price_table_1", "price_table_2", "price_table_3", "min_price"]:
            data[key] = int(num(data[key])) if key == "supplier_id" else num(data[key])

    if record_id:
        sets = ",".join([f"{key}=?" for key in data])
        exec_sql(f"UPDATE {table} SET {sets} WHERE id=?", list(data.values()) + [record_id])
        log(request, table, record_id, "update", f"Atualizou {CRUDS[table]['title']}")
    else:
        cols = ",".join(data.keys())
        placeholders = ",".join(["?"] * len(data))
        new_id = exec_sql(f"INSERT INTO {table}({cols}) VALUES({placeholders})", list(data.values()))
        log(request, table, new_id, "create", f"Criou {CRUDS[table]['title']}")

        if (
            table == "sellers"
            and data.get("username")
            and not q("SELECT id FROM users WHERE username=?", (data["username"],), one=True)
        ):
            exec_sql(
                "INSERT INTO users(username,password_hash,role,seller_id,active) VALUES(?,?,?,?,?)",
                (data["username"], hash_password("123456"), "vendedor", new_id, "Sim")
            )

    return RedirectResponse(f"/cadastros/{table}", status_code=303)


@app.get("/cadastros/{table}/delete/{record_id}")
def crud_delete(request: Request, table: str, record_id: int):
    if not require_login(request):
        return redirect_login()
    if not require_admin(request):
        return PlainTextResponse("Sem permissão", status_code=403)
    if table not in CRUDS:
        return PlainTextResponse("Cadastro não encontrado", status_code=404)
    exec_sql(f"DELETE FROM {table} WHERE id=?", (record_id,))
    log(request, table, record_id, "delete", f"Excluiu {CRUDS[table]['title']}")
    return RedirectResponse(f"/cadastros/{table}", status_code=303)


# ---------------- Oportunidades ----------------

@app.get("/opportunities", response_class=HTMLResponse)
def opportunities(request: Request, view_mode: str = "kanban", page: int = 1, page_size: int = 25):
    if not require_login(request):
        return redirect_login()

    user = current_user(request)
    sellers = q("SELECT * FROM sellers WHERE active='Sim' ORDER BY name")
    clients = q("SELECT * FROM clients ORDER BY name")
    suppliers = q("SELECT * FROM suppliers ORDER BY name")
    seller_id = None if user.get("role") == "admin" else user.get("seller_id")
    if seller_id:
        total = q("SELECT COUNT(*) AS total FROM opportunities WHERE seller_id=?", (seller_id,), one=True)["total"]
    else:
        total = q("SELECT COUNT(*) AS total FROM opportunities", one=True)["total"]
    pager = pagination_values(total, page, page_size)
    offset = (pager["page"] - 1) * pager["page_size"]
    opps = opportunity_summaries(
        seller_id=seller_id,
        limit=pager["page_size"],
        offset=offset,
    )
    kanban = {status: [] for status in STATUS_OPP}
    for opp in opps:
        kanban.setdefault(opp.get("status") or "Lead", []).append(opp)
    return render(request, "opportunities.html", {
        "opps": opps,
        "kanban": kanban,
        "view_mode": view_mode,
        "clients": clients,
        "suppliers": suppliers,
        "sellers": sellers,
        "statuses": STATUS_OPP,
        "pager": pager,
    })


@app.post("/opportunities/create")
async def opportunity_create(request: Request):
    if not require_login(request):
        return redirect_login()

    form = await request.form()
    user = current_user(request)
    seller_id = int(form.get("seller_id") or user.get("seller_id") or 0)
    if user.get("role") != "admin":
        seller_id = int(user.get("seller_id") or 0)

    ro_number = next_number("RO", "opportunities", "ro_number")
    new_id = exec_sql("""
        INSERT INTO opportunities(ro_number,created_at,client_id,supplier_id,seller_id,status,probability,forecast_date,next_followup,payment_terms,notes,created_by)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        ro_number, today(), form.get("client_id"), form.get("supplier_id"), seller_id,
        form.get("status") or "Lead", num(form.get("probability") or 40),
        form.get("forecast_date"), form.get("next_followup"),
        form.get("payment_terms"), form.get("notes"),
        user["id"]
    ))
    log(request, "opportunity", new_id, "create", f"Criou R.O {ro_number}")
    return RedirectResponse("/opportunities", status_code=303)


@app.post("/opportunities/{opp_id}/add-item")
async def opportunity_add_item(request: Request, opp_id: int):
    if not require_login(request):
        return redirect_login()

    opp = opp_summary(opp_id)
    if not opp or not can_view_seller(request, opp["seller_id"]):
        return PlainTextResponse("Sem permissão", status_code=403)

    form = await request.form()
    product = q("SELECT * FROM products WHERE id=?", (form.get("product_id"),), one=True)
    seller = q("SELECT * FROM sellers WHERE id=?", (opp["seller_id"],), one=True)

    sale_price = num(form.get("sale_unit_price") or product["ionm_price"])
    approval_status = "Não aplicável"
    if sale_price < float(product.get("min_price") or 0):
        approval_status = "Aguardando aprovação"

    exec_sql("""
        INSERT INTO opportunity_items(opportunity_id,product_id,quantity,supplier_unit_price,sale_unit_price,seller_commission_rate)
        VALUES(?,?,?,?,?,?)
    """, (
        opp_id, product["id"], num(form.get("quantity") or 1),
        product["supplier_price"], sale_price,
        num(form.get("seller_commission_rate") or seller["commission_rate"])
    ))
    exec_sql("UPDATE opportunities SET approval_status=? WHERE id=?", (approval_status, opp_id))
    log(request, "opportunity", opp_id, "add_item", "Adicionou item na R.O")
    return RedirectResponse("/opportunities", status_code=303)


@app.get("/opportunities/{opp_id}/make-order")
def make_order(request: Request, opp_id: int):
    if not require_login(request):
        return redirect_login()

    opp = opp_summary(opp_id)
    if not opp or not can_view_seller(request, opp["seller_id"]):
        return PlainTextResponse("Sem permissão", status_code=403)

    existing = q("SELECT id FROM orders WHERE opportunity_id=?", (opp_id,), one=True)
    if existing:
        return RedirectResponse("/orders", status_code=303)

    number = next_number("PED", "orders", "order_number")
    order_id = exec_sql("""
        INSERT INTO orders(order_number,opportunity_id,created_at,status,invoice_forecast,payment_terms)
        VALUES(?,?,?,?,?,?)
    """, (
        number, opp_id, today(), "Aguardando faturamento",
        opp.get("forecast_date"), ""
    ))
    exec_sql("UPDATE opportunities SET status='Ganho' WHERE id=?", (opp_id,))
    log(request, "order", order_id, "create", f"Criou pedido {number}")
    return RedirectResponse("/orders", status_code=303)


@app.get("/opportunities/{opp_id}/proposal-pdf")
def proposal_pdf(request: Request, opp_id: int):
    if not require_login(request):
        return redirect_login()
    path = generate_pdf_proposal(opp_id)
    return FileResponse(path, filename=path.name)


@app.get("/opportunities/{opp_id}/ro-supplier-pdf")
def ro_supplier_pdf(request: Request, opp_id: int):
    if not require_login(request):
        return redirect_login()
    path = generate_pdf_ro_supplier(opp_id)
    return FileResponse(path, filename=path.name)


@app.get("/opportunities/{opp_id}/print-ro-supplier")
def ro_supplier_print(request: Request, opp_id: int):
    if not require_login(request):
        return redirect_login()
    path = generate_pdf_ro_supplier(opp_id)
    ok, msg = print_pdf_server(path)
    return PlainTextResponse(msg if ok else "Falha: " + msg)


@app.get("/opportunities/{opp_id}/print-proposal")
def proposal_print(request: Request, opp_id: int):
    if not require_login(request):
        return redirect_login()
    path = generate_pdf_proposal(opp_id)
    ok, msg = print_pdf_server(path)
    return PlainTextResponse(msg if ok else "Falha: " + msg)



@app.get("/opportunities/{opp_id}/move/{direction}")
def opportunity_move(request: Request, opp_id: int, direction: str):
    if not require_login(request):
        return redirect_login()
    opp = opp_summary(opp_id)
    if not opp or not can_view_seller(request, opp["seller_id"]):
        return PlainTextResponse("Sem permissão", status_code=403)
    statuses = STATUS_OPP
    try:
        idx = statuses.index(opp["status"])
    except Exception:
        idx = 0
    if direction == "next":
        idx = min(idx + 1, len(statuses) - 1)
    elif direction == "prev":
        idx = max(idx - 1, 0)
    else:
        return RedirectResponse("/opportunities", status_code=303)
    new_status = statuses[idx]
    exec_sql("UPDATE opportunities SET status=? WHERE id=?", (new_status, opp_id))
    log(request, "opportunity", opp_id, "move", f"Moveu para {new_status}")
    return RedirectResponse("/opportunities", status_code=303)


# ---------------- Pedidos ----------------

@app.get("/orders", response_class=HTMLResponse)
def orders(request: Request):
    if not require_login(request):
        return redirect_login()

    user = current_user(request)
    rows = q("SELECT id FROM orders ORDER BY id DESC")
    orders_list = []
    for row in rows:
        order = order_summary(row["id"])
        if user.get("role") == "admin" or can_view_seller(request, order["opp"]["seller_id"]):
            orders_list.append(order)

    return render(request, "orders.html", {
        "orders": orders_list,
        "status_fiscal": STATUS_FISCAL,
        "status_finance": STATUS_FINANCE,
    })


@app.post("/orders/{order_id}/closing")
async def save_closing(request: Request, order_id: int):
    if not require_login(request):
        return redirect_login()
    if current_user(request).get("role") not in ["admin", "financeiro"]:
        return PlainTextResponse("Sem permissão", status_code=403)

    form = await request.form()
    existing = q("SELECT id FROM closings WHERE order_id=?", (order_id,), one=True)

    data = (
        form.get("supplier_invoice"), form.get("ionm_invoice"),
        form.get("supplier_invoice_date"), form.get("ionm_invoice_date"),
        form.get("expected_receipt_date"), form.get("receipt_date"),
        form.get("fiscal_status"), form.get("financial_status"),
        num(form.get("received_amount")), form.get("notes")
    )

    if existing:
        exec_sql("""
            UPDATE closings SET supplier_invoice=?,ionm_invoice=?,supplier_invoice_date=?,ionm_invoice_date=?,
            expected_receipt_date=?,receipt_date=?,fiscal_status=?,financial_status=?,received_amount=?,notes=?
            WHERE order_id=?
        """, data + (order_id,))
    else:
        exec_sql("""
            INSERT INTO closings(order_id,supplier_invoice,ionm_invoice,supplier_invoice_date,ionm_invoice_date,
            expected_receipt_date,receipt_date,fiscal_status,financial_status,received_amount,notes)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)
        """, (order_id,) + data)

    create_financial_entries(order_id, form)
    log(request, "closing", order_id, "save", "Salvou fechamento/faturamento")
    return RedirectResponse("/orders", status_code=303)


# ---------------- Comissões ----------------

@app.get("/commissions", response_class=HTMLResponse)
def commissions(request: Request):
    if not require_login(request):
        return redirect_login()
    user = current_user(request)
    rows = commission_rows(None if user.get("role") == "admin" else user.get("seller_id"))
    return render(request, "commissions.html", {"rows": rows})


# ---------------- Fiscal / Financeiro ----------------

@app.get("/finance", response_class=HTMLResponse)
def finance(request: Request, segment: str = "receivables", page: int = 1, page_size: int = 25):
    if not require_login(request):
        return redirect_login()
    if current_user(request).get("role") not in ["admin", "financeiro"]:
        return PlainTextResponse("Sem permissão", status_code=403)

    if segment not in {"receivables", "payables", "costs"}:
        segment = "receivables"

    rows = []
    if segment == "receivables":
        summary = q("SELECT COUNT(*) AS total, COALESCE(SUM(amount),0) AS amount FROM receivables", one=True)
        pager = pagination_values(summary["total"], page, page_size)
        offset = (pager["page"] - 1) * pager["page_size"]
        rows = q("""
            SELECT r.*, c.name AS client_name, o.order_number
            FROM receivables r
            LEFT JOIN clients c ON c.id=r.client_id
            LEFT JOIN orders o ON o.id=r.order_id
            ORDER BY r.id DESC
            LIMIT ? OFFSET ?
        """, (pager["page_size"], offset))
    elif segment == "payables":
        summary = q("SELECT COUNT(*) AS total, COALESCE(SUM(amount),0) AS amount FROM payables", one=True)
        pager = pagination_values(summary["total"], page, page_size)
        offset = (pager["page"] - 1) * pager["page_size"]
        rows = q("""
            SELECT p.*, s.name AS seller_name, sp.name AS supplier_name, o.order_number
            FROM payables p
            LEFT JOIN sellers s ON s.id=p.seller_id
            LEFT JOIN suppliers sp ON sp.id=p.supplier_id
            LEFT JOIN orders o ON o.id=p.order_id
            ORDER BY p.id DESC
            LIMIT ? OFFSET ?
        """, (pager["page_size"], offset))
    else:
        summary = q("SELECT COUNT(*) AS total, COALESCE(SUM(amount),0) AS amount FROM costs", one=True)
        pager = pagination_values(summary["total"], page, page_size)
        offset = (pager["page"] - 1) * pager["page_size"]
        rows = q("""
            SELECT c.*, o.order_number
            FROM costs c
            LEFT JOIN orders o ON o.id=c.order_id
            ORDER BY c.id DESC
            LIMIT ? OFFSET ?
        """, (pager["page_size"], offset))

    orders_list = q("SELECT * FROM orders ORDER BY id DESC") if segment == "costs" else []

    return render(request, "finance.html", {
        "segment": segment,
        "rows": rows,
        "total": summary["amount"],
        "pager": pager,
        "orders": orders_list,
        "cost_categories": COST_CATEGORIES,
        "cost_centers": COST_CENTERS,
    })


@app.post("/finance/costs/add")
async def add_cost(request: Request):
    if not require_login(request):
        return redirect_login()
    if current_user(request).get("role") not in ["admin", "financeiro"]:
        return PlainTextResponse("Sem permissão", status_code=403)

    form = await request.form()
    exec_sql("""
        INSERT INTO costs(order_id,description,category,cost_center,amount,date,vendor,document,billable,notes)
        VALUES(?,?,?,?,?,?,?,?,?,?)
    """, (
        form.get("order_id") or None, form.get("description"), form.get("category"),
        form.get("cost_center"), num(form.get("amount")), form.get("date") or today(),
        form.get("vendor"), form.get("document"), form.get("billable") or "Não",
        form.get("notes")
    ))
    return RedirectResponse("/finance?segment=costs", status_code=303)


# ---------------- Relatórios ----------------

@app.get("/reports/sellers", response_class=HTMLResponse)
def report_sellers(request: Request, page: int = 1, page_size: int = 25):
    if not require_login(request):
        return redirect_login()
    if not require_admin(request):
        return PlainTextResponse("Sem permissão", status_code=403)

    sellers = q("SELECT * FROM sellers ORDER BY name")
    pager = pagination_values(len(sellers), page, page_size)
    offset = (pager["page"] - 1) * pager["page_size"]
    report_sellers_page = sellers[offset:offset + pager["page_size"]]
    report = []
    for seller in report_sellers_page:
        metrics = seller_metrics(seller["id"])
        review = q(
            "SELECT * FROM seller_reviews WHERE seller_id=? ORDER BY id DESC LIMIT 1",
            (seller["id"],),
            one=True
        )
        quality = None
        if review:
            scores = [
                review["organization_score"], review["followup_score"],
                review["opportunity_quality_score"], review["margin_score"],
                review["predictability_score"]
            ]
            quality = sum(scores) / len(scores)
        report.append({"seller": seller, "metrics": metrics, "review": review, "quality": quality})

    return render(request, "seller_reports.html", {"report": report, "sellers": sellers, "pager": pager})


@app.post("/reports/sellers/review")
async def save_seller_review(request: Request):
    if not require_login(request):
        return redirect_login()
    if not require_admin(request):
        return PlainTextResponse("Sem permissão", status_code=403)

    form = await request.form()
    exec_sql("""
        INSERT INTO seller_reviews(seller_id,period,organization_score,followup_score,opportunity_quality_score,
        margin_score,predictability_score,strengths,improvements,notes,created_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?)
    """, (
        form.get("seller_id"), form.get("period"),
        int(num(form.get("organization_score"))), int(num(form.get("followup_score"))),
        int(num(form.get("opportunity_quality_score"))), int(num(form.get("margin_score"))),
        int(num(form.get("predictability_score"))), form.get("strengths"),
        form.get("improvements"), form.get("notes"), today()
    ))
    return RedirectResponse("/reports/sellers", status_code=303)



# ---------------- BI Gerencial ----------------

@app.get("/bi-gerencial", response_class=HTMLResponse)
def bi_gerencial(request: Request):
    if not require_login(request):
        return redirect_login()

    user = current_user(request)
    if user.get("username") != "fernando.mello":
        return PlainTextResponse("Sem permissão. O BI Gerencial é exclusivo do administrador principal.", status_code=403)

    if user.get("role") == "admin":
        opp_rows = q("SELECT id FROM opportunities ORDER BY id DESC")
    else:
        opp_rows = q("SELECT id FROM opportunities WHERE seller_id=? ORDER BY id DESC", (user.get("seller_id"),))

    opportunities = [opp_summary(row["id"]) for row in opp_rows]
    receivables_total = q("SELECT COALESCE(SUM(amount),0) AS total FROM receivables WHERE status IN ('Aberto','Vencido','Inadimplente')", one=True)["total"]
    payables_total = q("SELECT COALESCE(SUM(amount),0) AS total FROM payables WHERE status='Aberto'", one=True)["total"]
    costs_total = q("SELECT COALESCE(SUM(amount),0) AS total FROM costs", one=True)["total"]

    active = [o for o in opportunities if o.get("status") not in ["Perdido", "Cancelado"]]
    proposal_value = sum(float(o.get("total_sale") or 0) for o in active)
    weighted_sale = sum(float(o.get("total_sale") or 0) * float(o.get("probability") or 0) / 100 for o in active)
    weighted_over = sum(float(o.get("total_overprice") or 0) * float(o.get("probability") or 0) / 100 for o in active)
    weighted_commission = sum(float(o.get("total_commission") or 0) * float(o.get("probability") or 0) / 100 for o in active)

    projected_ll = weighted_over - weighted_commission - float(costs_total or 0)
    capital_aplicado = max(projected_ll, 0)

    cdi_annual = 0.1475
    investment_sources = [
        {"name": "Renda fixa 100% CDI", "kind": "Conservador", "annual_rate": cdi_annual, "risk": "Baixo"},
        {"name": "CDB 110% CDI", "kind": "Conservador+", "annual_rate": cdi_annual * 1.10, "risk": "Baixo/Médio"},
        {"name": "Fundo DI 95% CDI", "kind": "Liquidez", "annual_rate": cdi_annual * 0.95, "risk": "Baixo"},
        {"name": "Renda variável", "kind": "Estimativa", "annual_rate": 0.18, "risk": "Alto"},
        {"name": "Criptoativos", "kind": "Estimativa", "annual_rate": 0.35, "risk": "Muito alto"},
    ]
    for item in investment_sources:
        item["daily_rate"] = calc_daily_rate(item["annual_rate"])
        item["daily_gain"] = float(capital_aplicado or 0) * item["daily_rate"]
        item["monthly_gain"] = item["daily_gain"] * 30

    product_map = {}
    client_map = {}
    for opp in active:
        prob = float(opp.get("probability") or 0) / 100
        client = opp.get("client_name") or "Sem cliente"
        client_map.setdefault(client, {"client": client, "count": 0, "weighted_sale": 0, "weighted_over": 0, "prob_sum": 0})
        client_map[client]["count"] += 1
        client_map[client]["weighted_sale"] += float(opp.get("total_sale") or 0) * prob
        client_map[client]["weighted_over"] += float(opp.get("total_overprice") or 0) * prob
        client_map[client]["prob_sum"] += float(opp.get("probability") or 0)

        for it in opp.get("items", []):
            prod = it.get("product_name") or "Sem produto"
            product_map.setdefault(prod, {"product": prod, "qty": 0, "weighted_sale": 0, "weighted_over": 0, "score": 0})
            product_map[prod]["qty"] += float(it.get("quantity") or 0)
            product_map[prod]["weighted_sale"] += float(it.get("sale_total") or 0) * prob
            product_map[prod]["weighted_over"] += float(it.get("overprice") or 0) * prob
            product_map[prod]["score"] += float(it.get("overprice") or 0) * prob + float(it.get("sale_total") or 0) * prob * 0.10

    product_focus = sorted(product_map.values(), key=lambda x: x["score"], reverse=True)[:10]
    client_focus = sorted(client_map.values(), key=lambda x: x["weighted_over"], reverse=True)[:10]
    for c in client_focus:
        c["avg_probability"] = c["prob_sum"] / c["count"] if c["count"] else 0

    kpis = {
        "proposal_value": proposal_value,
        "weighted_sale": weighted_sale,
        "receivables_total": receivables_total,
        "payables_total": payables_total,
        "weighted_over": weighted_over,
        "weighted_commission": weighted_commission,
        "costs_total": costs_total,
        "projected_ll": projected_ll,
        "capital_aplicado": capital_aplicado,
    }
    return render(request, "bi_gerencial.html", {
        "kpis": kpis,
        "investment_sources": investment_sources,
        "product_focus": product_focus,
        "client_focus": client_focus,
        "opps": opportunities[:30],
    })



# ---------------- Configurações ----------------

def role_email_settings_for_view():
    """Return editable role e-mail settings without exposing stored passwords."""
    return q("""
        SELECT id, role, email_from, smtp_host, smtp_port, smtp_user, signature
        FROM role_email_settings
        ORDER BY role
    """)


def access_profiles_for_settings():
    repo = AccessControlRepository(DB_PATH)
    repo.ensure_seed_data()
    return repo.profiles()


def user_access_profile_map():
    rows = q("SELECT user_id, profile_id FROM user_access_profiles")
    mapping = {}
    for row in rows:
        mapping.setdefault(row["user_id"], set()).add(row["profile_id"])
    return mapping

@app.get("/settings", response_class=HTMLResponse)
def settings(request: Request):
    if not require_login(request):
        return redirect_login()
    if not require_admin(request):
        return PlainTextResponse("Sem permissão", status_code=403)

    users = q("""
        SELECT u.*, s.name AS seller_name
        FROM users u
        LEFT JOIN sellers s ON s.id=u.seller_id
        ORDER BY u.id DESC
    """)
    sellers = q("SELECT * FROM sellers ORDER BY name")
    role_emails = role_email_settings_for_view()
    return render(request, "settings.html", {
        "users": users,
        "sellers": sellers,
        "edit_user": None,
        "role_emails": role_emails,
        "access_profiles": access_profiles_for_settings(),
        "user_access_profile_ids": user_access_profile_map(),
    })


@app.post("/settings/save")
async def settings_save(request: Request):
    if not require_login(request):
        return redirect_login()
    if not require_admin(request):
        return PlainTextResponse("Sem permissão", status_code=403)

    form = await request.form()
    for key in [
        "company_name", "company_document", "company_email", "company_phone",
        "company_address", "server_printer", "sumatra_path", "allow_server_print"
    ]:
        set_config(key, form.get(key, ""))
    return RedirectResponse("/settings", status_code=303)



@app.get("/settings/users/edit/{user_id}", response_class=HTMLResponse)
def user_edit(request: Request, user_id: int):
    if not require_login(request):
        return redirect_login()
    if not require_admin(request):
        return PlainTextResponse("Sem permissão", status_code=403)

    users = q("""
        SELECT u.*, s.name AS seller_name
        FROM users u
        LEFT JOIN sellers s ON s.id=u.seller_id
        ORDER BY u.id DESC
    """)
    sellers = q("SELECT * FROM sellers ORDER BY name")
    role_emails = role_email_settings_for_view()
    edit_user = q("SELECT * FROM users WHERE id=?", (user_id,), one=True)
    return render(request, "settings.html", {
        "users": users,
        "sellers": sellers,
        "edit_user": edit_user,
        "role_emails": role_emails,
        "access_profiles": access_profiles_for_settings(),
        "user_access_profile_ids": user_access_profile_map(),
    })


@app.post("/settings/users/update/{user_id}")
async def user_update(request: Request, user_id: int):
    if not require_login(request):
        return redirect_login()
    if not require_admin(request):
        return PlainTextResponse("Sem permissão", status_code=403)

    form = await request.form()
    username = str(form.get("username", "")).strip()
    email = str(form.get("email", "")).strip()
    password = str(form.get("password", "")).strip()
    role = str(form.get("role", "")).strip()
    seller_id = form.get("seller_id") or None
    active = form.get("active") or "Sim"
    smtp_email = str(form.get("smtp_email", "")).strip()
    smtp_host = str(form.get("smtp_host", "")).strip()
    smtp_port = str(form.get("smtp_port", "")).strip()
    email_signature = str(form.get("email_signature", "")).strip()

    if not username:
        return PlainTextResponse("Usuário é obrigatório", status_code=400)

    # Evita remover o próprio admin da tela sem querer.
    existing = q("SELECT * FROM users WHERE id=?", (user_id,), one=True)
    if existing and existing["username"] == "fernando.mello":
        role = "admin"
        active = "Sim"

    if password:
        exec_sql("""
            UPDATE users
            SET username=?, password_hash=?, role=?, seller_id=?, active=?, email=?, smtp_email=?, smtp_host=?, smtp_port=?, email_signature=?
            WHERE id=?
        """, (username, hash_password(password), role, seller_id, active, email, smtp_email, smtp_host, smtp_port, email_signature, user_id))
    else:
        exec_sql("""
            UPDATE users
            SET username=?, role=?, seller_id=?, active=?, email=?, smtp_email=?, smtp_host=?, smtp_port=?, email_signature=?
            WHERE id=?
        """, (username, role, seller_id, active, email, smtp_email, smtp_host, smtp_port, email_signature, user_id))

    log(request, "user", user_id, "update", f"Atualizou usuário {username}")
    return RedirectResponse("/settings", status_code=303)


@app.get("/settings/users/toggle/{user_id}")
def user_toggle(request: Request, user_id: int):
    if not require_login(request):
        return redirect_login()
    if not require_admin(request):
        return PlainTextResponse("Sem permissão", status_code=403)

    target = q("SELECT * FROM users WHERE id=?", (user_id,), one=True)
    if not target:
        return RedirectResponse("/settings", status_code=303)

    # Protege o usuário admin principal.
    if target["username"] == "fernando.mello":
        return RedirectResponse("/settings", status_code=303)

    new_status = "Não" if target["active"] == "Sim" else "Sim"
    exec_sql("UPDATE users SET active=? WHERE id=?", (new_status, user_id))
    log(request, "user", user_id, "toggle", f"Alterou ativo para {new_status}")
    return RedirectResponse("/settings", status_code=303)



@app.post("/settings/users/create")
async def user_create(request: Request):
    if not require_login(request):
        return redirect_login()
    if not require_admin(request):
        return PlainTextResponse("Sem permissão", status_code=403)

    form = await request.form()
    username = str(form.get("username", "")).strip()
    email = str(form.get("email", "")).strip()
    password = str(form.get("password", "")).strip()

    if not username or not password:
        return PlainTextResponse("Usuário e senha são obrigatórios.", status_code=400)

    if q("SELECT id FROM users WHERE username=?", (username,), one=True):
        return PlainTextResponse("Já existe um usuário com esse login.", status_code=400)

    user_id = exec_sql("""
        INSERT INTO users(username,password_hash,role,seller_id,active,email)
        VALUES(?,?,?,?,?,?)
    """, (
        username, hash_password(password),
        form.get("role"), form.get("seller_id") or None,
        form.get("active") or "Sim", email
    ))
    exec_sql(
        "INSERT OR IGNORE INTO user_profiles(user_id,full_name,email) VALUES(?,?,?)",
        (user_id, username, email),
    )
    return RedirectResponse("/settings", status_code=303)



@app.post("/settings/role-email/save")
async def role_email_save(request: Request):
    if not require_login(request):
        return redirect_login()
    if not require_admin(request):
        return PlainTextResponse("Sem permissão", status_code=403)

    form = await request.form()
    roles = q("SELECT * FROM role_email_settings ORDER BY role")
    for r in roles:
        rid = r["id"]
        submitted_password = str(form.get(f"smtp_password_{rid}", "")).strip()
        smtp_password = submitted_password or r["smtp_password"]
        exec_sql("""
            UPDATE role_email_settings
            SET email_from=?, smtp_host=?, smtp_port=?, smtp_user=?, smtp_password=?, signature=?
            WHERE id=?
        """, (
            form.get(f"email_from_{rid}"),
            form.get(f"smtp_host_{rid}"),
            form.get(f"smtp_port_{rid}"),
            form.get(f"smtp_user_{rid}"),
            smtp_password,
            form.get(f"signature_{rid}"),
            rid
        ))
    return RedirectResponse("/settings", status_code=303)


@app.get("/backup/export-db")
def export_db(request: Request):
    if not require_login(request):
        return redirect_login()
    if not require_admin(request):
        return PlainTextResponse("Sem permissão", status_code=403)
    return FileResponse(DB_PATH, filename=f"overpriceon_web_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")


@app.post("/backup/import-db")
async def import_db(request: Request, file: UploadFile = File(...)):
    if not require_login(request):
        return redirect_login()
    if not require_admin(request):
        return PlainTextResponse("Sem permissão", status_code=403)

    backup = DATA_DIR / f"backup_antes_import_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    if DB_PATH.exists():
        shutil.copy2(DB_PATH, backup)
    content = await file.read()
    DB_PATH.write_bytes(content)
    init_db()
    return RedirectResponse("/settings", status_code=303)


@app.get("/server-info")
def server_info():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
    except Exception:
        ip = "127.0.0.1"
    return {"local": "http://127.0.0.1:8000", "rede": f"http://{ip}:8000"}
