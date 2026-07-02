from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_windows_launcher_repairs_venv_and_uses_locked_dependencies() -> None:
    launcher = (ROOT / "iniciar_overpriceon.bat").read_text(encoding="utf-8")

    assert 'if not exist ".venv\\pyvenv.cfg"' in launcher
    assert "python -m venv --clear .venv" in launcher
    assert '".venv\\Scripts\\python.exe" -m pip install -r requirements.lock' in launcher
    assert '".venv\\Scripts\\python.exe" -m uvicorn' in launcher
    assert "activate" not in launcher.lower()
    assert "requirements.txt" not in launcher
