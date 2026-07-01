from app import main


def test_worker_entrypoint_exposes_process_one_job():
    assert callable(main.process_one_job)
