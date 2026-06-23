from datetime import date

from app.core.errors import ApiError
from app.modules.projects.router import _validate_project_user_scope, validate_project_required_update_fields, validate_report_language, validate_report_year, validate_status_transition


class _ScalarResult:
    def __init__(self, row):
        self._row = row

    def first(self):
        return self._row


class _ProjectUserScopeDb:
    def __init__(self, *, user_in_scope: bool, org_unit_in_scope: bool = True):
        self.user_in_scope = user_in_scope
        self.org_unit_in_scope = org_unit_in_scope
        self.queries = []

    def execute(self, statement, params):
        query = str(statement)
        self.queries.append((query, params))
        if "FROM users u" in query:
            return _ScalarResult(("user-1",) if self.user_in_scope else None)
        if "FROM org_units" in query:
            return _ScalarResult(("org-1",) if self.org_unit_in_scope else None)
        raise AssertionError(f"Unexpected query: {query}")


def test_project_default_status_flow_allows_first_step():
    validate_status_transition("draft", "peer_analysis")


def test_project_status_illegal_transition_blocked():
    try:
        validate_status_transition("draft", "completed")
    except ApiError as exc:
        assert exc.code == "PROJECT_STATUS_TRANSITION_INVALID"
    else:
        raise AssertionError("Illegal transition should raise ApiError")


def test_project_report_year_must_be_legal():
    validate_report_year(date.today().year)
    try:
        validate_report_year(1999)
    except ApiError as exc:
        assert exc.code == "PROJECT_INVALID_REPORT_YEAR"
    else:
        raise AssertionError("Invalid report year should raise ApiError")


def test_project_member_user_must_belong_to_tenant_and_enterprise_scope():
    db = _ProjectUserScopeDb(user_in_scope=False)
    try:
        _validate_project_user_scope(
            db,
            tenant_id="tenant-1",
            enterprise_id="enterprise-1",
            user_id="foreign-user",
        )
    except ApiError as exc:
        assert exc.code == "PROJECT_MEMBER_USER_INVALID"
    else:
        raise AssertionError("Cross-tenant or out-of-enterprise users should be rejected")


def test_project_member_org_unit_must_belong_to_enterprise_scope():
    db = _ProjectUserScopeDb(user_in_scope=True, org_unit_in_scope=False)
    try:
        _validate_project_user_scope(
            db,
            tenant_id="tenant-1",
            enterprise_id="enterprise-1",
            user_id="user-1",
            org_unit_id="foreign-org",
        )
    except ApiError as exc:
        assert exc.code == "PROJECT_MEMBER_ORG_UNIT_INVALID"
    else:
        raise AssertionError("Cross-enterprise org units should be rejected")


def test_project_report_language_must_match_contract_enum():
    validate_report_language("zh")
    validate_report_language("en")
    validate_report_language("bilingual")
    try:
        validate_report_language("fr")
    except ApiError as exc:
        assert exc.code == "PROJECT_INVALID_REPORT_LANGUAGE"
    else:
        raise AssertionError("Unsupported report language should raise ApiError")


def test_project_patch_required_fields_cannot_be_null():
    try:
        validate_project_required_update_fields({"project_name": None})
    except ApiError as exc:
        assert exc.code == "PROJECT_REQUIRED_FIELD_NULL"
    else:
        raise AssertionError("Required project fields should reject explicit null updates")
