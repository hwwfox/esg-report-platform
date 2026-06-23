from app.modules.standard_library_router import _library_visibility_clause


def test_standard_library_visibility_includes_public_and_current_tenant():
    clause = _library_visibility_clause("s")
    assert "s.tenant_id IS NULL" in clause
    assert "s.tenant_id = :tenant_id" in clause


def test_standard_library_visibility_without_alias_is_tenant_scoped():
    clause = _library_visibility_clause()
    assert "tenant_id IS NULL" in clause
    assert "tenant_id = :tenant_id" in clause
