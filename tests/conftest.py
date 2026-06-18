import shutil
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

import app.main as legacy


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


@pytest.fixture
def legacy_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    source_database = Path(__file__).resolve().parents[1] / "data" / "overpriceon_web.db"
    test_database = tmp_path / "overpriceon_web.db"
    shutil.copy2(source_database, test_database)
    monkeypatch.setattr(legacy, "DB_PATH", test_database)
    _patch_legacy_template_response(monkeypatch)

    with TestClient(legacy.app) as client:
        yield client
