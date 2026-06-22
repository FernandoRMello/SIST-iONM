# Versões verificadas

Verificação local em 18/06/2026.

| Componente | Versão |
|---|---:|
| SIST-iONM | 2.6.0 |
| Python | 3.13.7 |
| FastAPI | 0.137.1 |
| Starlette | 1.3.1 |
| Jinja2 | 3.1.6 |
| Uvicorn | 0.49.0 |
| openpyxl | 3.1.5 |
| Pillow | 12.2.0 |
| Pytest | 9.1.0 |
| Git local | 2.53.0.windows.2 |

As dependências de aplicação e desenvolvimento estão fixadas em `pyproject.toml` e `requirements.lock`. O projeto exige Python `>=3.13,<3.14`.

## Banco de dados

- Ativo nesta entrega visual: SQLite, arquivo `data/overpriceon_web.db`.
- Driver PostgreSQL já fixado: `psycopg[binary] 3.3.4`.
- ORM/migração já fixados: SQLAlchemy 2.0.51 e Alembic 1.18.4.
- PostgreSQL ainda não está conectado ao monólito; o cutover será feito no próximo workstream com migração validada e rollback.

## Sistema operacional alvo

O handoff e os comandos de execução foram preparados para Linux/Ubuntu. A validação desta sessão ocorreu em Windows; por isso o deploy Ubuntu deve repetir integralmente os comandos de `docs/development.md` e o gate automatizado antes da liberação.

## Como reverificar

```bash
python --version
python -c "import fastapi,jinja2,starlette,uvicorn,pytest; print(fastapi.__version__, jinja2.__version__, starlette.__version__, uvicorn.__version__, pytest.__version__)"
python -m pip check
```
