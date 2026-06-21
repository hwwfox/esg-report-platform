"""Local worker entrypoint.

MVP implementation should register queues for document parsing, AI parsing,
recommendation, knowledge indexing, report writing, review, and export.
"""

import os
import time


def main() -> None:
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    print(f"[worker] starting placeholder worker with REDIS_URL={redis_url}")
    print("[worker] TODO: wire RQ/Celery queues and async_jobs status updates")
    while True:
        time.sleep(5)


if __name__ == "__main__":
    main()
