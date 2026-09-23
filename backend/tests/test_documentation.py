"""한국어 문서·실행 양식·API 명세의 일치 여부를 확인합니다."""
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


def markdown_files():
    return [ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md"))]


def test_all_markdown_documents_have_korean_titles():
    for path in markdown_files():
        text = path.read_text(encoding="utf-8")
        title = next(line for line in text.splitlines() if line.startswith("# "))
        assert re.search("[가-힣]", title), path.name
        assert "\ufffd" not in text, path.name


def test_local_markdown_links_resolve():
    for path in markdown_files():
        text = path.read_text(encoding="utf-8")
        for link in re.findall(r"\[[^\]]+\]\(([^)\s]+)\)", text):
            parsed = urlsplit(link)
            if parsed.scheme or not parsed.path:
                continue
            target = (path.parent / unquote(parsed.path)).resolve()
            assert target.is_relative_to(ROOT), (path.name, link)
            assert target.exists(), (path.name, link)


def test_startup_note_is_korean_and_already_integrated():
    text = (ROOT / "docs/STARTUP_FIX.md").read_text("utf-8")
    assert "이미" in text and "반영" in text
    assert "Apply this patch" not in text
    assert "NOT performed" not in text


def test_generated_openapi_matches_running_code(client):
    recorded = json.loads((ROOT / "docs/openapi.json").read_text("utf-8"))
    assert client.get("/openapi.json").json() == recorded


def test_every_api_operation_has_a_korean_summary(client):
    schema = client.get("/openapi.json").json()
    for path, methods in schema["paths"].items():
        for method, spec in methods.items():
            if method in {"get", "post", "put", "delete", "patch"}:
                assert re.search("[가-힣]", spec["summary"]), (method, path)


def test_environment_template_is_safe_and_not_private():
    values = {}
    for line in (ROOT / ".env.example").read_text("utf-8").splitlines():
        if line and not line.startswith("#") and "=" in line:
            name, value = line.split("=", 1)
            values[name] = value
    assert values["SECRET_KEY"] == ""
    assert values["OPENAI_API_KEY"] == ""
    assert values["SMTP_PASSWORD"] == ""
    assert values["CRAWL_ENABLED"] == "false"
    assert values["AUTO_CRAWL"] == "false"
    assert values["MAIL_BACKEND"] == "file"
    assert values["AI_PROVIDER"] == "rules"


def test_windows_launcher_line_endings_and_arguments():
    data = (ROOT / "START.cmd").read_bytes()
    assert data.isascii()
    # ZIP 배포 파일은 CRLF입니다. Git 설정에 따른 LF도 파이썬 테스트를 막지는 않습니다.
    assert b"\r\r\n" not in data
    assert b'"start.py" %*' in data
    assert b"setlocal" in data
    assert b"pause" in data
