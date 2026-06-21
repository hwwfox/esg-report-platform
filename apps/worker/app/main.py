"""Local worker entrypoint.

MVP implementation should register queues for document parsing, AI parsing,
recommendation, knowledge indexing, report writing, review, and export.
"""

import time


def main() -> None:
    print("[worker] starting placeholder worker with Redis configured")
    print("[worker] TODO: wire RQ/Celery queues and async_jobs status updates")
    while True:
        time.sleep(5)


if __name__ == "__main__":
    main()
