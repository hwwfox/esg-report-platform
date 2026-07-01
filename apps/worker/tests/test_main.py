from app.main import PsycopgDbAdapter


class FakeCursor:
    def __init__(self):
        self.calls = []

    def execute(self, statement, params):
        self.calls.append((statement, params))
        return self


def test_psycopg_adapter_converts_named_params_and_json_payloads():
    cursor = FakeCursor()
    adapter = PsycopgDbAdapter(cursor)

    adapter.execute("UPDATE async_jobs SET result_payload=:result_payload WHERE tenant_id=:tenant_id", {"tenant_id": "tenant-1", "result_payload": {"ok": True}})

    statement, params = cursor.calls[0]
    assert statement == "UPDATE async_jobs SET result_payload=%(result_payload)s WHERE tenant_id=%(tenant_id)s"
    assert params["tenant_id"] == "tenant-1"
    assert params["result_payload"].obj == {"ok": True}
