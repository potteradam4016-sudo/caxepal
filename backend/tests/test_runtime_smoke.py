"""실제 API 프로세스 검증은 임시 데이터에서만 수행합니다."""
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_real_http_workflow_in_temporary_workspace(tmp_path):
    report = tmp_path / "http-result.json"
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/verify_backend.py"), "--output", str(report)],
        cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    data = json.loads(report.read_text("utf-8"))
    assert data["passed"] is True
    assert data["http_request_count"] >= 12
    assert all(item["status"] == item["expected"] for item in data["http_requests"])
    assert data["real_school_crawl"] is False
    assert data["uses_existing_user_database"] is False
