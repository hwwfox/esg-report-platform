from types import SimpleNamespace

from app.core.errors import ApiError
from app.modules.peer import router as peer_router


def test_gics_candidate_defaults_to_industrial_machinery():
    class FakeDb:
        def execute(self, statement, params):
            assert params["codes"] == ["20106010", "20106020"]
            return SimpleNamespace(mappings=lambda: SimpleNamespace(all=lambda: [
                {"gics_code": "20106010", "gics_name_en": "Industrial Machinery", "gics_name_cn": "工业机械", "gics_level": 4, "parent_gics_code": "201060"},
            ]))

    candidates = peer_router._candidate_gics(FakeDb(), {"enterprise_name": "示例股份", "main_business": "工业设备制造"})

    assert candidates[0]["gics_code"] == "20106010"


def test_gics_candidate_can_match_specialty_chemicals():
    class FakeDb:
        def execute(self, statement, params):
            assert params["codes"] == ["15101050"]
            return SimpleNamespace(mappings=lambda: SimpleNamespace(all=lambda: []))

    peer_router._candidate_gics(FakeDb(), {"enterprise_name": "化工企业", "main_business": "特种化学品"})


def test_peer_recommendation_requires_confirmed_gics(monkeypatch):
    monkeypatch.setattr(peer_router, "_authorize_project", lambda request, db, user, project_id: {"project_id": project_id, "enterprise_id": "enterprise-1"})
    monkeypatch.setattr(peer_router, "_current_enterprise_gics", lambda db, tenant_id, enterprise_id: None)

    try:
        peer_router.recommend_peers(
            project_id="project-1",
            payload=peer_router.PeerRecommendRequest(),
            request=SimpleNamespace(state=SimpleNamespace(request_id="req-1")),
            db=SimpleNamespace(),
            user={"current_tenant_id": "tenant-1", "user_id": "user-1", "name": "Owner"},
        )
    except ApiError as exc:
        assert exc.code == "GICS_NOT_CONFIRMED"
    else:
        raise AssertionError("Unconfirmed GICS should block peer recommendation")


def test_confirm_peer_pool_requires_selection(monkeypatch):
    monkeypatch.setattr(peer_router, "_authorize_project", lambda request, db, user, project_id: {"project_id": project_id, "enterprise_id": "enterprise-1"})

    try:
        peer_router.confirm_peer_pool(
            project_id="project-1",
            payload=peer_router.PeerConfirmRequest(selected_peer_company_ids=[]),
            request=SimpleNamespace(state=SimpleNamespace(request_id="req-1")),
            db=SimpleNamespace(),
            user={"current_tenant_id": "tenant-1", "user_id": "user-1", "name": "Owner"},
        )
    except ApiError as exc:
        assert exc.code == "PEER_SELECTION_REQUIRED"
    else:
        raise AssertionError("Peer pool confirmation requires selected peers")


def test_peer_payload_exposes_project_peer_id_for_selection():
    payload = peer_router._peer_payload({
        "project_peer_company_id": "project-peer-1",
        "peer_company_id": "profile-1",
        "company_name": "同行A",
        "stock_code": "600101",
        "exchange": "SSE",
        "gics_level_4_code": "20106010",
        "gics_level_4_name": "工业机械",
        "business_similarity_score": 0.9,
        "industry_leader_score": 0.8,
        "report_availability_score": 0.7,
        "overall_score": 0.82,
        "recommendation_reason": "同属GICS四级行业",
        "latest_report_year": None,
        "has_report_in_library": False,
        "selected": True,
        "confirmed_at": None,
    })

    assert payload["peer_company_id"] == "project-peer-1"
    assert payload["profile_peer_company_id"] == "profile-1"
    assert payload["selected"] is True


def test_resolve_existing_peer_profile_by_id():
    class FakeResult:
        def mappings(self):
            return self

        def first(self):
            return {"peer_company_id": "profile-1"}

    class FakeDb:
        def execute(self, statement, params):
            assert "FROM peer_company_profiles" in str(statement)
            assert params == {"peer_company_id": "profile-1"}
            return FakeResult()

    row = peer_router._resolve_or_create_peer_profile(
        FakeDb(),
        peer_router.PeerCompanyCreateRequest(peer_company_id="profile-1", company_name="同行A"),
    )

    assert row == {"peer_company_id": "profile-1"}


def test_resolve_existing_peer_profile_rejects_unknown_id():
    class FakeResult:
        def mappings(self):
            return self

        def first(self):
            return None

    class FakeDb:
        def execute(self, statement, params):
            return FakeResult()

    try:
        peer_router._resolve_or_create_peer_profile(
            FakeDb(),
            peer_router.PeerCompanyCreateRequest(peer_company_id="missing", company_name="不存在同行"),
        )
    except ApiError as exc:
        assert exc.code == "PEER_COMPANY_INVALID"
    else:
        raise AssertionError("Unknown peer profile id should be rejected")
