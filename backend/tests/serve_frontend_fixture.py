"""Serve temporary synthetic notices for the real-browser integration test."""
import argparse
from datetime import timedelta
import hashlib
import os
from pathlib import Path
import sys
import tempfile
import threading

import uvicorn
from app.cli import migrate
from app.config import Settings
from app.factory import create_app
from app.models import Notice
from app.schemas import Schedule
from app.services.analysis import analyze, apply_analysis
from app.services.dates import local_today


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--frontend-port", type=int, required=True)
    args = parser.parse_args()
    for name in Settings.model_fields:
        os.environ.pop(name.upper(), None)
    with tempfile.TemporaryDirectory(prefix="scnu-browser-test-") as directory:
        settings = Settings(_env_file=None, app_env="test",
            database_url=f"sqlite:///{Path(directory, 'test.sqlite3').as_posix()}",
            secret_key="isolated-browser-fixture-only-" * 2,
            cors_origins=f"http://127.0.0.1:{args.frontend_port}",
            frontend_url=f"http://127.0.0.1:{args.frontend_port}",
            request_limit_per_minute=10000, auth_limit_per_15_minutes=1000)
        migrate(settings)
        app = create_app(settings)
        today = local_today()
        with app.state.sessions() as db:
            for index in range(1, 24):
                title = f"통합 시험 AI 해커톤 {index}"
                body = "대상: 컴퓨터공학과 2학년 재학생\nAI 해커톤 교육 프로그램"
                data, provider, status, warnings = analyze(settings, title, body, False)
                schedules = [] if index == 23 else [Schedule(
                    kind="event", label="시험 행사", start_date=today,
                    end_date=today + timedelta(days=2), start_time=None, end_time=None, evidence=body)]
                data = data.model_copy(update={"category": "education" if index % 2 else "contest", "schedules": schedules})
                item = Notice(source_code="SCNU_SW", external_id=str(index), title=title, body_text=body,
                    posted_date=today, original_url=f"https://www.scnu.ac.kr/?test={index}",
                    content_hash=hashlib.sha256((title + body).encode()).hexdigest(),
                    attachments=[], image_only=False)
                apply_analysis(item, data, provider, status, warnings)
                db.add(item)
            db.commit()
        server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=args.port, log_level="warning"))
        # Parent closes stdin or sends a line to request graceful shutdown and DB cleanup.
        def stop_on_input():
            sys.stdin.readline()
            server.should_exit = True
        threading.Thread(target=stop_on_input, daemon=True).start()
        try:
            server.run()
        finally:
            app.state.engine.dispose()


if __name__ == "__main__":
    main()
