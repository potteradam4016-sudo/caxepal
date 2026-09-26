"""Run a local HTTP smoke check against an isolated temporary database."""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description="임시 DB에서 실제 HTTP 인증 흐름 검증")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error("--port는 0~65535 범위여야 합니다.")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", args.port))
        port = sock.getsockname()[1]
    checks = []
    with tempfile.TemporaryDirectory(prefix="scnu-pick-http-") as tmp:
        env = dict(os.environ, APP_ENV="test", SECRET_KEY="isolated-http-test-secret-" * 2,
                   DATABASE_URL=f"sqlite:///{Path(tmp, 'test.sqlite3').as_posix()}",
                   HOST="127.0.0.1", PORT=str(port), PYTHONUTF8="1")
        subprocess.run([sys.executable, "-m", "app.cli", "init-db"], cwd=ROOT, env=env,
                       check=True, capture_output=True, timeout=60)
        server = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.asgi:app", "--host", "127.0.0.1",
                                   "--port", str(port)], cwd=ROOT, env=env,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            base = f"http://127.0.0.1:{port}"

            def request(method, path, expected, body=None, token=None):
                headers = {"Content-Type": "application/json"}
                if token:
                    headers["Authorization"] = "Bearer " + token
                req = Request(base + path, data=json.dumps(body).encode() if body is not None else None,
                              headers=headers, method=method)
                try:
                    with urlopen(req, timeout=5) as response:
                        status = response.status
                        content = response.read()
                except HTTPError as exc:
                    status, content = exc.code, exc.read()
                assert status == expected, (path, expected, status, content[:200])
                checks.append({"path": path, "expected": expected, "status": status})
                try:
                    return json.loads(content) if content else None
                except json.JSONDecodeError:
                    return content.decode("utf-8", errors="replace")

            for _ in range(60):
                try:
                    request("GET", "/health", 200)
                    break
                except (URLError, TimeoutError):
                    if server.poll() is not None:
                        raise RuntimeError("API process exited")
                    time.sleep(0.2)
            else:
                raise RuntimeError("API did not start")
            request("GET", "/docs", 200)
            credentials = {"username": "alice", "password": "initial-passphrase-123"}
            request("POST", "/api/auth/register", 201, credentials)
            request("POST", "/api/auth/register", 409, credentials)
            login = request("POST", "/api/auth/login", 200, credentials)
            token = login["access_token"]
            assert request("GET", "/api/auth/me", 200, token=token)["username"] == "alice"
            request("POST", "/api/auth/change-password", 401,
                    {"current_password": "wrong", "new_password": "updated-passphrase-123"}, token)
            request("POST", "/api/auth/change-password", 200,
                    {"current_password": credentials["password"], "new_password": "updated-passphrase-123"}, token)
            request("GET", "/api/auth/me", 401, token=token)
            request("POST", "/api/auth/login", 401, credentials)
            request("POST", "/api/auth/login", 200,
                    {"username": "alice", "password": "updated-passphrase-123"})
            request("GET", "/api/notices", 200)
            report = {"passed": True, "http_request_count": len(checks), "http_requests": checks,
                      "real_school_crawl": False, "uses_existing_user_database": False}
        finally:
            if os.name == "nt" and server.poll() is None:
                # The Windows venv launcher can own a child holding the SQLite file.
                subprocess.run(["taskkill", "/PID", str(server.pid), "/T", "/F"],
                               capture_output=True, timeout=10, check=False)
            else:
                server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
