from types import SimpleNamespace

from app.core.errors import ApiError
from app.modules.standard_library import router as standard_router


def test_standard_library_tenant_scope_allows_public_and_current_tenant_only():
    assert standard_router.tenant_scope_clause("s") == "(s.tenant_id IS NULL OR s.tenant_id=:tenant_id)"


def test_standard_scope_api_expr_normalizes_database_scope_values():
    assert standard_router.standard_scope_api_expr("s") == "CASE WHEN s.scope_type IN ('tenant', 'tenant_private') THEN 'tenant' ELSE 'platform' END"


def test_standard_library_keyword_filter_uses_parameterized_ilike():
    clauses = []
    params = {}
    standard_router.add_like_filter(clauses, params, ["s.standard_code", "s.standard_name"], "GRI")

    assert clauses == ["(s.standard_code ILIKE :keyword OR s.standard_name ILIKE :keyword)"]
    assert params == {"keyword": "%GRI%"}


def test_topic_category_filter_rejects_invalid_enum_before_query():
    try:
        standard_router.list_topics(
            request=SimpleNamespace(state=SimpleNamespace(request_id="req-1")),
            db=None,
            user={"current_tenant_id": "tenant-1"},
            topic_category="X",
            page=1,
            page_size=50,
        )
    except ApiError as exc:
        assert exc.status_code == 400
        assert exc.code == "TOPIC_INVALID_CATEGORY"
    else:
        raise AssertionError("Invalid topic category should raise ApiError")


def test_metric_type_filter_rejects_invalid_enum_before_query():
    try:
        standard_router.list_metrics(
            request=SimpleNamespace(state=SimpleNamespace(request_id="req-1")),
            db=None,
            user={"current_tenant_id": "tenant-1"},
            metric_type="currency",
            page=1,
            page_size=50,
        )
    except ApiError as exc:
        assert exc.status_code == 400
        assert exc.code == "METRIC_INVALID_TYPE"
    else:
        raise AssertionError("Invalid metric type should raise ApiError")


def test_topic_scoped_metric_filter_requires_topic_permission(monkeypatch):
    audit_calls = []

    class FakeDb:
        def commit(self):
            audit_calls.append("commit")

    def fake_write_audit_log(*args, **kwargs):
        audit_calls.append(kwargs)

    monkeypatch.setattr(standard_router, "write_audit_log", fake_write_audit_log)

    try:
        standard_router.list_metrics(
            request=SimpleNamespace(
                state=SimpleNamespace(request_id="req-1"),
                client=SimpleNamespace(host="127.0.0.1"),
                headers={"user-agent": "pytest"},
            ),
            db=FakeDb(),
            user={
                "current_tenant_id": "tenant-1",
                "user_id": "user-1",
                "name": "Metric Reader",
                "permissions": ["metric:read"],
            },
            topic_code="TOPIC_ENV",
            page=1,
            page_size=50,
        )
    except ApiError as exc:
        assert exc.status_code == 403
        assert exc.code == "AUTH_FORBIDDEN"
    else:
        raise AssertionError("Topic-scoped metrics should require topic:read")

    assert audit_calls[0]["action_type"] == "security.permission_denied"
    assert "topic:read" in audit_calls[0]["description"]
    assert audit_calls[1] == "commit"


def test_status_filter_rejects_invalid_enum_before_query():
    try:
        standard_router.validate_status_filter("archived")
    except ApiError as exc:
        assert exc.status_code == 400
        assert exc.code == "STANDARD_LIBRARY_INVALID_STATUS"
    else:
        raise AssertionError("Invalid status should raise ApiError")


def test_status_filter_accepts_known_status_values():
    for status in (None, "draft", "active", "inactive"):
        standard_router.validate_status_filter(status)
