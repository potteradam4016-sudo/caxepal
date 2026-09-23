"""Launcher regressions. Windows .cmd needs a separate native Windows smoke test."""
import importlib.util
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock

import pytest

SPEC = importlib.util.spec_from_file_location("backend_launcher", Path(__file__).resolve().parents[1] / "start.py")
launcher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(launcher)


def test_env_creation_generates_secret(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(launcher, "ROOT", tmp_path)
    (tmp_path / ".env.example").write_text("APP_ENV=development\nSECRET_KEY=\n", encoding="utf-8")
    launcher.ensure_env()
    secret = (tmp_path / ".env").read_text().split("SECRET_KEY=")[1].strip()
    assert len(secret) >= 32
    assert secret not in capsys.readouterr().out


def test_existing_env_is_never_replaced(tmp_path, monkeypatch):
    monkeypatch.setattr(launcher, "ROOT", tmp_path)
    original = b"SECRET_KEY=\r\n# preserve even invalid user settings\r\n"
    (tmp_path / ".env").write_bytes(original)
    launcher.ensure_env()
    assert (tmp_path / ".env").read_bytes() == original


def test_invalid_template_does_not_create_env(tmp_path, monkeypatch):
    monkeypatch.setattr(launcher, "ROOT", tmp_path)
    (tmp_path / ".env.example").write_text("APP_ENV=development\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        launcher.ensure_env()
    assert not (tmp_path / ".env").exists()


def test_captured_errors_are_visible(monkeypatch, capsys):
    error = subprocess.CalledProcessError(1, ["python", "-c", "probe"],
                                          output="probe output\n", stderr="secret_key: too short\n")
    monkeypatch.setattr(launcher, "main", Mock(side_effect=error))
    assert launcher.entrypoint() == 1
    output = capsys.readouterr().err
    assert "secret_key: too short" in output
    assert "probe output" in output


def test_captured_byte_errors_are_visible(monkeypatch, capsys):
    error = subprocess.CalledProcessError(2, ["python"], stderr=b"test byte diagnostic")
    monkeypatch.setattr(launcher, "main", Mock(side_effect=error))
    assert launcher.entrypoint() == 1
    assert "test byte diagnostic" in capsys.readouterr().err


def test_unexpected_process_exit_is_failure(monkeypatch, capsys):
    monkeypatch.setattr(launcher, "main", Mock(side_effect=RuntimeError("API stopped unexpectedly")))
    assert launcher.entrypoint() == 1
    assert "API stopped unexpectedly" in capsys.readouterr().err


class FakeProcess:
    def __init__(self, code=None):
        self.code = code
        self.terminated = False
        self.waited = False

    def poll(self):
        return self.code

    def terminate(self):
        self.terminated = True
        self.code = -15

    def wait(self, timeout=None):
        self.waited = True
        return self.code

    def kill(self):
        self.code = -9


@pytest.mark.parametrize("code", [0, 1, 3])
def test_api_exit_stops_worker_and_raises(monkeypatch, code):
    api, worker = FakeProcess(code), FakeProcess()
    monkeypatch.setattr(launcher.subprocess, "Popen", Mock(side_effect=[api, worker]))
    with pytest.raises(RuntimeError, match="API 프로세스가 예기치 않게 종료"):
        launcher.serve(Path(sys.executable), "127.0.0.1", 3104)
    assert worker.terminated and worker.waited
    assert api.waited


def test_worker_exit_stops_api(monkeypatch):
    api, worker = FakeProcess(), FakeProcess(1)
    monkeypatch.setattr(launcher.subprocess, "Popen", Mock(side_effect=[api, worker]))
    with pytest.raises(RuntimeError, match="worker 프로세스가 예기치 않게 종료"):
        launcher.serve(Path(sys.executable), "127.0.0.1", 3104)
    assert api.terminated and api.waited


def test_ctrl_c_stops_both_children(monkeypatch):
    api, worker = FakeProcess(), FakeProcess()
    monkeypatch.setattr(launcher.subprocess, "Popen", Mock(side_effect=[api, worker]))
    monkeypatch.setattr(launcher.time, "sleep", Mock(side_effect=KeyboardInterrupt))
    assert launcher.serve(Path(sys.executable), "127.0.0.1", 3104) == 0
    assert api.terminated and worker.terminated


def test_worker_spawn_error_cleans_up_api(monkeypatch):
    api = FakeProcess()
    monkeypatch.setattr(launcher.subprocess, "Popen", Mock(side_effect=[api, OSError("test spawn failure")]))
    with pytest.raises(OSError, match="test spawn failure"):
        launcher.serve(Path(sys.executable), "127.0.0.1", 3104)
    assert api.terminated and api.waited


def test_settings_probe_does_not_print_secret_inputs(tmp_path, monkeypatch):
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "__init__.py").touch()
    source = Path(__file__).resolve().parents[1] / "app" / "config.py"
    (tmp_path / "app" / "config.py").write_bytes(source.read_bytes())
    secret = "must-never-appear-in-output-" * 3
    (tmp_path / ".env").write_text(
        f"SECRET_KEY={secret}\nFRONTEND_URL=not-a-valid-origin\n", encoding="utf-8")
    monkeypatch.setattr(launcher, "ROOT", tmp_path)
    for key in ("SECRET_KEY", "FRONTEND_URL", "APP_ENV"):
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(subprocess.CalledProcessError) as error:
        launcher.load_settings(Path(sys.executable))
    assert "백엔드 설정 오류" in error.value.stderr
    assert secret not in error.value.stderr
    assert "input_value=" not in error.value.stderr


def test_settings_probe_reports_short_key(tmp_path, monkeypatch):
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "__init__.py").touch()
    source = Path(__file__).resolve().parents[1] / "app" / "config.py"
    (tmp_path / "app" / "config.py").write_bytes(source.read_bytes())
    (tmp_path / ".env").write_text("SECRET_KEY=\n", encoding="utf-8")
    monkeypatch.setattr(launcher, "ROOT", tmp_path)
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(subprocess.CalledProcessError) as error:
        launcher.load_settings(Path(sys.executable))
    assert "secret_key:" in error.value.stderr
    assert "32" in error.value.stderr


def test_fresh_db_creates_missing_parent_before_migration(settings, tmp_path):
    from app.cli import migrate
    from sqlalchemy import create_engine, text
    database = tmp_path / "absent-data" / "nested" / "fresh.sqlite3"
    config = settings.model_copy(update={"database_url": f"sqlite:///{database.as_posix()}"})
    assert not database.parent.exists()
    migrate(config)
    migrate(config)
    engine = create_engine(config.database_url)
    try:
        with engine.connect() as connection:
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0001"
            assert connection.execute(text("SELECT count(*) FROM notices")).scalar_one() == 0
            assert connection.execute(text("SELECT count(*) FROM sources")).scalar_one() == 3
    finally:
        engine.dispose()


def test_direct_alembic_creates_missing_parent(tmp_path):
    from alembic import command
    from alembic.config import Config
    backend = Path(__file__).resolve().parents[1]
    database = tmp_path / "absent-direct-data" / "direct.sqlite3"
    config = Config(str(backend / "alembic.ini"))
    config.set_main_option("script_location", str(backend / "migrations"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database.as_posix()}".replace("%", "%%"))
    assert not database.parent.exists()
    command.upgrade(config, "head")
    assert database.is_file()
