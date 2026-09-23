"""로컬 백엔드 준비·실행 도구입니다. 운영 배포는 별도 마이그레이션·프로세스 관리가 필요합니다."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
import venv

ROOT = Path(__file__).resolve().parent
MIN_PYTHON = (3, 11)

# 비밀값이 섞일 수 있으므로 설정 검증 오류의 입력 사전은 출력하지 않습니다.
SETTINGS_PROBE = """
import json
import sys
from pydantic import ValidationError
from app.config import get_settings
try:
    s = get_settings()
except ValidationError as exc:
    print('백엔드 설정 오류 (.env 또는 환경변수):', file=sys.stderr)
    for error in exc.errors(include_input=False, include_context=False, include_url=False):
        field = '.'.join(str(part) for part in error['loc']) or 'configuration'
        print(f"  {field}: {error['msg']}", file=sys.stderr)
    print('backend/.env의 해당 항목을 확인하세요. 비밀값 자체는 공유하지 마세요.', file=sys.stderr)
    raise SystemExit(1)
print(json.dumps([s.host, s.port, s.app_env]))
"""


def run(command: list[str], *, capture: bool = False) -> subprocess.CompletedProcess:
    """Keep normal child output visible; preserve captured errors for entrypoint()."""
    if capture:
        return subprocess.run(command, cwd=ROOT, check=True, capture_output=True,
                              text=True, encoding="utf-8", errors="replace")
    return subprocess.run(command, cwd=ROOT, check=True)


def ensure_env() -> None:
    envpath = ROOT / ".env"
    if envpath.exists():
        print("기존 backend/.env를 변경하지 않고 유지합니다.", flush=True)
        return
    data = (ROOT / ".env.example").read_text(encoding="utf-8-sig")
    marker = "SECRET_KEY=\n"
    if marker not in data:
        raise RuntimeError(".env.example is missing its blank SECRET_KEY line.")
    data = data.replace(marker, "SECRET_KEY=" + secrets.token_urlsafe(48) + "\n", 1)
    fd = os.open(envpath, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as output:
        output.write(data)
    print("무작위 비밀키로 backend/.env를 생성했습니다. 이 파일은 GitHub에 올리지 마세요.", flush=True)


def load_settings(py: Path) -> tuple[str, int, str]:
    result = run([str(py), "-c", SETTINGS_PROBE], capture=True)
    host, port, environment = json.loads(result.stdout)
    return str(host), int(port), str(environment)


def serve(py: Path, host: str, port: int) -> int:
    commands = [
        ("API", [str(py), "-m", "uvicorn", "app.asgi:app", "--host", host,
                 "--port", str(port), "--no-access-log", "--no-proxy-headers"]),
        ("worker", [str(py), "-m", "app.worker"]),
    ]
    children: list[tuple[str, subprocess.Popen]] = []
    try:
        for name, command in commands:
            children.append((name, subprocess.Popen(command, cwd=ROOT)))
        print(f"\n{host}:{port}에서 백엔드를 시작합니다. 아래 주소의 응답까지 확인해야 실행 성공입니다.", flush=True)
        print(f"API 시험: http://localhost:{port}/docs\n상태 확인: http://localhost:{port}/health", flush=True)
        print("프론트엔드와 가짜 공지는 포함하지 않습니다. 종료는 Ctrl+C입니다.", flush=True)
        while True:
            for name, process in children:
                code = process.poll()
                if code is not None:
                    raise RuntimeError(f"{name} 프로세스가 예기치 않게 종료되었습니다 (종료 코드 {code}). "
                                       "위 오류를 확인하세요. 실행 성공 상태가 아닙니다.")
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n백엔드와 작업 처리기를 종료합니다.", flush=True)
        return 0
    finally:
        for _, process in children:
            if process.poll() is None:
                process.terminate()
        for _, process in children:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


def main() -> int:
    parser = argparse.ArgumentParser(description="로컬 SCNU PICK 백엔드를 준비하고 실행합니다.")
    parser.add_argument("--setup-only", action="store_true")
    parser.add_argument("--dev", action="store_true", help="자동 테스트 패키지도 설치합니다.")
    parser.add_argument("--no-install", action="store_true", help="준비된 .venv를 사용하고 패키지 설치를 생략합니다.")
    args = parser.parse_args()
    if sys.version_info < MIN_PYTHON:
        raise RuntimeError("Python 3.11 이상이 필요합니다. py -0p 명령으로 설치된 버전을 확인하세요.")
    os.chdir(ROOT)
    os.environ.setdefault("PYTHONUTF8", "1")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    print(f"백엔드 폴더: {ROOT}\n실행 Python: {sys.executable}", flush=True)
    for relative in ("app/config.py", "requirements.txt", "requirements-dev.txt", ".env.example"):
        if not (ROOT / relative).is_file():
            raise RuntimeError(f"{relative} 파일이 없습니다. backend 폴더 전체를 먼저 압축 해제하세요.")

    print("[1/5] 개인 환경설정", flush=True)
    ensure_env()
    print("[2/5] 가상환경", flush=True)
    py = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not py.exists():
        if args.no_install:
            raise RuntimeError(".venv가 없습니다. 먼저 START.cmd --dev --setup-only를 실행하세요.")
        venv.EnvBuilder(with_pip=True).create(ROOT / ".venv")
    probe = run([str(py), "-c", "import json,sys; print(json.dumps(list(sys.version_info[:3])))"],
                capture=True)
    version = json.loads(probe.stdout)
    if tuple(version[:2]) < MIN_PYTHON:
        raise RuntimeError("기존 .venv의 Python이 3.11보다 낮습니다. .venv만 저장소 밖으로 옮긴 뒤 "
                           "Python 3.11 이상으로 다시 실행하세요. .env와 data는 보존하세요.")
    print(f"가상환경 Python: {'.'.join(map(str, version))}", flush=True)

    print("[3/5] 의존 패키지", flush=True)
    requirements = ROOT / ("requirements-dev.txt" if args.dev else "requirements.txt")
    stamp = ROOT / ".venv" / ".requirements.sha256"
    content = (ROOT / "requirements.txt").read_bytes() + requirements.read_bytes()
    fingerprint = hashlib.sha256(content).hexdigest()
    if not args.no_install and (not stamp.exists() or stamp.read_text() != fingerprint):
        run([str(py), "-m", "pip", "install", "-r", str(requirements)])
        stamp.write_text(fingerprint, encoding="utf-8")
    else:
        print("패키지 설치를 생략합니다. 재설치하려면 .venv/.requirements.sha256 파일만 제거하세요.", flush=True)

    print("[4/5] 설정 검증", flush=True)
    host, port, environment = load_settings(py)
    if environment == "production":
        raise RuntimeError("운영 배포에는 서비스 관리자 또는 Docker와 별도 DB 마이그레이션이 필요합니다. "
                           "docs/DEPLOYMENT.md를 확인하세요.")
    print("[5/5] DB 마이그레이션", flush=True)
    run([str(py), "-m", "app.cli", "init-db"])
    if args.setup_only:
        print("준비가 완료되었습니다. START.cmd 또는 python start.py로 실행하세요.", flush=True)
        return 0
    return serve(py, host, port)


def entrypoint() -> int:
    try:
        return main()
    except subprocess.CalledProcessError as exc:
        # The original launcher discarded these captured diagnostics.
        for output in (exc.stdout, exc.stderr):
            if output:
                if isinstance(output, bytes):
                    output = output.decode("utf-8", errors="replace")
                print(output.rstrip(), file=sys.stderr, flush=True)
        print(f"[오류] 하위 명령이 실패했습니다 (종료 코드 {exc.returncode}). "
              "위 오류를 확인하고 .env나 data를 삭제하지 마세요.", file=sys.stderr, flush=True)
        return 1
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"[오류] {exc}", file=sys.stderr, flush=True)
        return 1
    except KeyboardInterrupt:
        print("\n사용자가 취소했습니다.", flush=True)
        return 130


if __name__ == "__main__":
    sys.exit(entrypoint())
