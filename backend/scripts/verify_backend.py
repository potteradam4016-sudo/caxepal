"""임시 DB와 실제 HTTP 서버로 주요 사용자 흐름을 검증합니다.

학교 사이트, SMTP, 외부 AI에는 연결하지 않습니다.
기존 .env와 서비스 DB를 사용하지 않고 임시 폴더를 정리합니다.
실행에는 requirements.txt의 패키지가 설치된 Python이 필요합니다.
"""
from __future__ import annotations

import argparse
from datetime import date
from email import policy
from email.parser import BytesParser
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import build_opener, ProxyHandler, Request

ROOT = Path(__file__).resolve().parents[1]

# 이 코드는 검증 전용 복사본의 임시 DB에만 합성 자료를 넣습니다.
SEED_CODE = r"""
import hashlib
import json
from datetime import date
from sqlalchemy import select, func
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from app.config import get_settings
from app.db import Base, make_engine, session_factory
from app.models import Notice, Source, Interest
from app.services.analysis import analyze, apply_analysis

settings = get_settings()
engine = make_engine(settings.database_url)
with engine.connect() as conn:
    assert compare_metadata(MigrationContext.configure(conn), Base.metadata) == []
with session_factory(engine)() as db:
    assert db.scalar(select(func.count()).select_from(Notice)) == 0
    assert db.scalar(select(func.count()).select_from(Source)) == 3
    assert db.scalar(select(func.count()).select_from(Interest)) == 15
    bodies = [
        "대상: 컴퓨터공학과 2학년 재학생\n신청 기간: 2070.09.01 ~ 2070.09.30\n행사 기간: 2070.09.29 ~ 2070.10.03",
        "대상: 컴퓨터공학과 2학년 재학생\n신청 마감: 2000.09.30\n행사 기간: 2070.09.29 ~ 2070.10.03",
        "일정은 추후 안내합니다.",
    ]
    ids = []
    for index, body in enumerate(bodies):
        title = f"[합성 검증 자료] AI 해커톤 {index}"
        notice = Notice(
            source_code="SCNU_SW", external_id=f"test-{index}",
            title=title, body_text=body,
            posted_date=date(2070, 9, 18 - index),
            original_url=f"https://www.scnu.ac.kr/scnusw/na/ntt/selectNttInfo.do?nttSn={900000 + index}",
            content_hash=hashlib.sha256((title + body).encode()).hexdigest(),
            attachments=[], image_only=False,
        )
        apply_analysis(notice, *analyze(settings, title, body, False))
        db.add(notice)
        db.flush()
        ids.append(notice.id)
    db.commit()
print(json.dumps(ids))
engine.dispose()
"""


def check(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def run_step(workspace: Path, env: dict[str, str], args: list[str]) -> subprocess.CompletedProcess:
    result = subprocess.run(
        [sys.executable, *args], cwd=workspace, env=env, capture_output=True,
        text=True, encoding="utf-8", errors="replace", timeout=60,
    )
    # 전체 출력에는 시험 토큰이 포함될 수 있으므로 실패 메시지에 덤프하지 않습니다.
    check(result.returncode == 0, f"검증 하위 명령 실패: {args[:2]} (종료 코드 {result.returncode})")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="임시 데이터로 백엔드 HTTP 흐름 검증")
    parser.add_argument("--port", type=int, default=0, help="기본 0: 빈 임시 포트 선택")
    parser.add_argument("--output", type=Path, help="비밀값 없는 결과 JSON 저장 경로")
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error("--port는 0~65535 범위여야 합니다.")
    if sys.version_info < (3, 11):
        parser.error("Python 3.11 이상이 필요합니다.")

    results: list[dict] = []
    requests: list[dict] = []

    def passed(name: str) -> None:
        results.append({"name": name, "passed": True})
        print(f"[통과] {name}", flush=True)

    report: dict = {
        "purpose": "임시 합성 자료와 실제 로컬 HTTP 요청 검증",
        "real_school_crawl": False, "real_smtp": False, "real_external_ai": False,
        "uses_existing_user_database": False,
    }
    try:
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", args.port))
            port = reservation.getsockname()[1]
        report["port"] = port

        with tempfile.TemporaryDirectory(prefix="scnu-pick-http-test-") as temporary:
            workspace = Path(temporary)
            for directory in ("app", "config", "migrations"):
                shutil.copytree(
                    ROOT / directory, workspace / directory,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
                )
            shutil.copy2(ROOT / "alembic.ini", workspace / "alembic.ini")
            env = os.environ.copy()
            # 사용자 또는 운영 서버의 설정이 시험 환경으로 유입되지 않도록 제거합니다.
            config_keys = {
                "APP_ENV", "DATABASE_URL", "SECRET_KEY", "HOST", "PORT", "ALLOWED_HOSTS",
                "CORS_ORIGINS", "DOCS_ENABLED", "SESSION_HOURS", "MAIL_BACKEND", "MAIL_FROM",
                "MAIL_DIRECTORY", "FRONTEND_URL", "SMTP_HOST", "SMTP_PORT", "SMTP_USERNAME",
                "SMTP_PASSWORD", "SMTP_TLS", "CRAWL_ENABLED", "AUTO_CRAWL", "CRAWL_INTERVAL_SECONDS",
                "CRAWL_REQUEST_DELAY", "CRAWL_TIMEOUT", "CRAWL_USER_AGENT", "ROBOTS_POLICY",
                "AI_PROVIDER", "OPENAI_API_KEY", "OPENAI_MODEL", "REQUEST_LIMIT_PER_MINUTE",
                "AUTH_LIMIT_PER_15_MINUTES", "MAX_REQUEST_BYTES",
            }
            for key in list(env):
                if key.upper() in config_keys:
                    del env[key]
            env.update({
                "PYTHONPATH": str(workspace), "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8",
                "APP_ENV": "test", "SECRET_KEY": secrets.token_urlsafe(48),
                "DATABASE_URL": f"sqlite:///{(workspace / 'data/fresh.sqlite3').as_posix()}",
                "MAIL_DIRECTORY": str(workspace / "data/mail"), "MAIL_BACKEND": "file",
                "CRAWL_ENABLED": "false", "AUTO_CRAWL": "false", "AI_PROVIDER": "rules",
                "REQUEST_LIMIT_PER_MINUTE": "1000", "AUTH_LIMIT_PER_15_MINUTES": "100",
            })
            check(not (workspace / "data").exists(), "시험 DB 상위 폴더가 이미 존재합니다.")
            run_step(workspace, env, ["-m", "app.cli", "init-db"])
            run_step(workspace, env, ["-m", "app.cli", "init-db"])
            good, expired, undated = json.loads(run_step(workspace, env, ["-c", SEED_CODE]).stdout)
            passed("새 DB 상위 폴더 생성·마이그레이션 반복·스키마 일치·초기 공지 0건")
            passed("실제 DB와 분리한 합성 공지 3건 구성")

            log_path = workspace / "process-output.txt"
            children: list[subprocess.Popen] = []
            with log_path.open("w", encoding="utf-8") as log:
                try:
                    children.append(subprocess.Popen(
                        [sys.executable, "-m", "uvicorn", "app.asgi:app", "--host", "127.0.0.1",
                         "--port", str(port), "--no-access-log", "--no-proxy-headers"],
                        cwd=workspace, env=env, stdout=log, stderr=subprocess.STDOUT,
                    ))
                    children.append(subprocess.Popen(
                        [sys.executable, "-m", "app.worker"],
                        cwd=workspace, env=env, stdout=log, stderr=subprocess.STDOUT,
                    ))
                    opener = build_opener(ProxyHandler({}))
                    base_url = f"http://127.0.0.1:{port}"
                    health_url = base_url + "/health"
                    deadline = time.monotonic() + 25
                    ready = False
                    while time.monotonic() < deadline:
                        check(all(p.poll() is None for p in children), "API 또는 작업 처리기가 시작 중 종료되었습니다.")
                        try:
                            with opener.open(health_url, timeout=1) as response:
                                ready = response.status == 200
                            if ready:
                                break
                        except (URLError, TimeoutError, OSError):
                            time.sleep(0.15)
                    check(ready, "제한 시간 안에 /health가 응답하지 않았습니다.")

                    def request(method: str, path: str, expected: int = 200,
                                body: dict | None = None, token: str | None = None,
                                headers: dict | None = None):
                        actual_headers = {"Content-Type": "application/json", **(headers or {})}
                        if token:
                            actual_headers["Authorization"] = "Bearer " + token
                        data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
                        req = Request(base_url + path, data=data, headers=actual_headers, method=method)
                        try:
                            response = opener.open(req, timeout=10)
                        except HTTPError as error:
                            response = error
                        with response:
                            status = response.status
                            content_type = response.headers.get("Content-Type", "")
                            raw = response.read()
                            response_headers = dict(response.headers)
                        requests.append({"method": method, "path": path, "status": status, "expected": expected})
                        check(status == expected, f"{method} {path}: 기대 상태 {expected}, 실제 상태 {status}")
                        if not raw:
                            return None, response_headers
                        if "application/json" in content_type:
                            return json.loads(raw), response_headers
                        return raw.decode("utf-8", errors="replace"), response_headers

                    health, _ = request("GET", "/health")
                    check(health == {"status": "ok", "database": "ok", "frontend_included": False},
                          "/health 응답이 계약과 다릅니다.")
                    request("GET", "/")
                    request("GET", "/docs")
                    spec, _ = request("GET", "/openapi.json")
                    report["openapi_paths"] = len(spec["paths"])
                    interests, _ = request("GET", "/api/interests")
                    check(len(interests) == 15, "관심사 사전 건수가 다릅니다.")
                    sources, _ = request("GET", "/api/sources")
                    check(len(sources) == 3, "공지 출처가 세 곳이 아닙니다.")
                    request("GET", "/api/profile", expected=401)
                    request("GET", "/api/notices", expected=401, token="invalid-test-token")
                    passed("서버 상태·Swagger·OpenAPI·공개 사전·비인증 요청 거부")

                    password = secrets.token_urlsafe(30)

                    def email_token(address: str, purpose: str) -> str:
                        paths = sorted((workspace / "data/mail").glob("*.eml"),
                                       key=lambda p: p.stat().st_mtime_ns, reverse=True)
                        for path in paths:
                            mail = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
                            if str(mail["To"]) != address:
                                continue
                            plain = mail.get_body(preferencelist=("plain",))
                            content = plain.get_content() if plain else ""
                            route = "verify-email" if purpose == "verify" else "reset-password"
                            found = re.search(rf"/{route}#token=([A-Za-z0-9_-]+)", content)
                            if found:
                                return found.group(1)
                        raise RuntimeError("임시 개발 메일에서 필요한 확인 토큰을 찾지 못했습니다.")

                    def create_user(address: str) -> str:
                        credentials = {"email": address, "password": password}
                        request("POST", "/api/auth/register", 202, credentials)
                        request("POST", "/api/auth/login", 403, credentials)
                        verification = email_token(address, "verify")
                        request("POST", "/api/auth/verify-email", body={"token": verification})
                        request("POST", "/api/auth/verify-email", 400, {"token": verification})
                        login, _ = request("POST", "/api/auth/login", body=credentials)
                        return login["access_token"]

                    alice = create_user("alice@example.com")
                    bob = create_user("bob@example.com")
                    request("GET", "/api/auth/me", token=alice)
                    request("GET", "/api/notices/recommended", 409, token=alice)
                    passed("가입·개발 메일 확인·일회용 토큰·로그인·미완성 프로필 거부")

                    profile = {
                        "department": "컴퓨터공학과", "grade": 2, "academic_status": "enrolled",
                        "interest_ids": ["ai_sw", "hackathon"], "expected_version": 0,
                    }
                    saved, _ = request("PUT", "/api/profile", body=profile, token=alice)
                    check(saved["onboarding_complete"], "프로필 온보딩이 완료되지 않았습니다.")
                    request("PUT", "/api/profile", 409, profile, alice)
                    recommendations, _ = request("GET", "/api/notices/recommended", token=alice)
                    ids = {item["id"] for item in recommendations["items"]}
                    check(good in ids and expired not in ids, "추천 또는 마감 제외가 잘못되었습니다.")
                    item = next(item for item in recommendations["items"] if item["id"] == good)
                    check(item["recommendation"]["score"] == 100, "명시적 자격 일치 점수가 잘못되었습니다.")
                    check(len(item["recommendation"]["reasons"]) > 0, "추천 이유가 없습니다.")
                    new_items, _ = request("GET", "/api/notices/new")
                    check([item["id"] for item in new_items["items"]] == [good, expired, undated],
                          "원문 등록일 최신순 정렬이 다릅니다.")
                    searched, _ = request("GET", "/api/notices?q=AI")
                    check(searched["total"] == 3, "검색 결과가 다릅니다.")
                    request("GET", "/api/notices?page=0", 422)
                    request("GET", "/api/notices/999999", 404)
                    passed("프로필 저장·수정 충돌·추천 점수와 이유·마감 제외·검색·신규 정렬")

                    for ident in (good, good, expired, undated):
                        request("POST", f"/api/bookmarks/{ident}", 204, token=alice)
                    bookmark_list, _ = request("GET", "/api/bookmarks", token=alice)
                    check(bookmark_list["total"] == 3, "찜 중복 방지가 잘못되었습니다.")
                    bob_bookmarks, _ = request("GET", "/api/bookmarks", token=bob)
                    check(bob_bookmarks["total"] == 0, "다른 사용자의 찜이 노출되었습니다.")
                    request("DELETE", f"/api/bookmarks/{good}", 204, token=bob)
                    calendar, _ = request("GET", "/api/calendar?month=2070-09", token=alice)
                    check({event["kind"] for event in calendar["events"]} == {"application", "event"},
                          "신청·행사 일정 구분이 다릅니다.")
                    check(any(event["notice_id"] == expired for event in calendar["events"]),
                          "마감한 공지의 향후 행사가 사라졌습니다.")
                    check(any(item["notice_id"] == undated for item in calendar["undated"]),
                          "일정 미정 안내가 없습니다.")
                    october, _ = request("GET", "/api/calendar?month=2070-10", token=alice)
                    check(len(october["events"]) == 2, "월 경계를 넘는 행사가 누락되었습니다.")
                    request("GET", "/api/calendar?month=2070-13", 422, token=alice)
                    detail, _ = request("GET", f"/api/notices/{good}", token=alice)
                    check(detail["is_bookmarked"], "타인이 본인의 찜을 삭제했습니다.")
                    passed("찜 중복 방지·사용자 격리·신청/행사 분리·월 경계·일정 미정")

                    updated = {**profile, "interest_ids": ["arts", "volunteer"],
                               "expected_version": saved["version"]}
                    request("PUT", "/api/profile", body=updated, token=alice)
                    changed, _ = request("GET", "/api/notices/recommended", token=alice)
                    changed_item = next(item for item in changed["items"] if item["id"] == good)
                    check(changed_item["recommendation"]["score"] < item["recommendation"]["score"],
                          "관심사 변경이 추천에 반영되지 않았습니다.")
                    preserved, _ = request("GET", "/api/bookmarks", token=alice)
                    check(preserved["total"] == 3, "프로필 수정으로 찜이 사라졌습니다.")
                    passed("관심사 변경 시 추천 재계산·기존 찜 보존")

                    request("POST", "/api/admin/crawl-jobs", 403, {"sources": ["SCNU_MAIN"]}, bob)
                    run_step(workspace, env, ["-m", "app.cli", "grant-admin", "--email", "alice@example.com"])
                    request("GET", "/api/admin/crawl-jobs", token=alice)
                    blocked, _ = request("POST", "/api/admin/crawl-jobs", 403, {"sources": ["SCNU_MAIN"]}, alice)
                    check(blocked["error"]["code"] == "CRAWLING_DISABLED", "기본 수집이 차단되지 않았습니다.")
                    _, cors_headers = request("OPTIONS", "/api/profile", headers={
                        "Origin": "http://localhost:5173", "Access-Control-Request-Method": "PUT",
                        "Access-Control-Request-Headers": "authorization,content-type",
                    })
                    check(cors_headers.get("access-control-allow-origin") == "http://localhost:5173"
                          or cors_headers.get("Access-Control-Allow-Origin") == "http://localhost:5173",
                          "허용된 출처의 CORS 응답이 다릅니다.")
                    request("OPTIONS", "/api/profile", 400, headers={
                        "Origin": "https://untrusted.example", "Access-Control-Request-Method": "PUT",
                    })
                    passed("관리자 권한·기본 수집 차단·허용/비허용 CORS")

                    request("POST", "/api/auth/forgot-password", 202, {"email": "alice@example.com"})
                    reset_token = email_token("alice@example.com", "reset")
                    new_password = secrets.token_urlsafe(30)
                    request("POST", "/api/auth/reset-password", body={"token": reset_token, "password": new_password})
                    request("GET", "/api/auth/me", 401, token=alice)
                    request("POST", "/api/auth/login", 401, {"email": "alice@example.com", "password": password})
                    renewed, _ = request("POST", "/api/auth/login",
                                         body={"email": "alice@example.com", "password": new_password})
                    alice = renewed["access_token"]
                    request("POST", "/api/auth/logout", 204, token=alice)
                    request("GET", "/api/auth/me", 401, token=alice)
                    request("DELETE", "/api/auth/account", 204, {"password": password}, bob)
                    request("GET", "/api/auth/me", 401, token=bob)
                    check(all(p.poll() is None for p in children), "검증 도중 API 또는 작업 처리기가 종료되었습니다.")
                    passed("비밀번호 재설정·기존 세션 폐기·로그아웃·본인 탈퇴")
                finally:
                    for child in children:
                        if child.poll() is None:
                            child.terminate()
                    for child in children:
                        try:
                            child.wait(timeout=10)
                        except subprocess.TimeoutExpired:
                            child.kill()
                            child.wait(timeout=5)
            passed("검증 API·작업 처리기 종료")
        passed("임시 DB·시험 계정·개발 메일·로그 정리")
        report["passed"] = True
    except Exception as exc:
        report["passed"] = False
        report["error_type"] = type(exc).__name__
        # 오류 내용은 이 도구가 만든 안전한 진단 또는 일반 예외 유형만 표시합니다.
        message = str(exc) if isinstance(exc, RuntimeError) else type(exc).__name__
        report["error"] = message
        print(f"[실패] {message}", file=sys.stderr)
    report["checks"] = results
    report["http_requests"] = requests
    report["http_request_count"] = len(requests)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"검증 결과: {'통과' if report['passed'] else '실패'}, HTTP 요청 {len(requests)}회", flush=True)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
