"""Durable DB queue worker; no work depends on FastAPI BackgroundTasks."""
import argparse
import logging
import time
from app.config import get_settings
from app.db import make_engine, session_factory
from app.services.jobs import maybe_schedule, run_next_job

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    settings = get_settings()
    engine = make_engine(settings.database_url)
    factory = session_factory(engine)
    try:
        while True:
            try:
                maybe_schedule(factory, settings)
                job_id = run_next_job(factory, settings)
                if job_id:
                    logging.info("Processed job %s. Inspect its recorded status.", job_id)
            except Exception as exc:
                logging.error("worker_iteration_failed error_type=%s", type(exc).__name__)
            if args.once:
                break
            time.sleep(5)
    except KeyboardInterrupt:
        pass
    finally:
        engine.dispose()

if __name__ == "__main__":
    main()
