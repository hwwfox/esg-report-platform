from app.modules.collection_tasks_router import build_validation_issues


def test_build_validation_issues_blocks_missing_required_metric():
    issues = build_validation_issues([
        {
            "project_metric_id": "metric-1",
            "metric_name": "范围一温室气体排放量",
            "is_required": True,
            "value": None,
            "text_value": None,
            "data_type": "number",
            "metric_snapshot": {},
            "attachment_file_ids": [],
        }
    ])

    assert issues[0]["issue_type"] == "required_missing"
    assert issues[0]["blocks_submission"] is True


def test_build_validation_issues_warns_when_evidence_missing():
    issues = build_validation_issues([
        {
            "project_metric_id": "metric-1",
            "metric_name": "安全培训记录",
            "is_required": False,
            "value": None,
            "text_value": "已完成",
            "data_type": "text",
            "metric_snapshot": {"attachment_required": True},
            "attachment_file_ids": [],
        }
    ])

    assert issues[0]["issue_type"] == "evidence_missing"
    assert issues[0]["blocks_submission"] is False


def test_build_validation_issues_warns_for_negative_number():
    issues = build_validation_issues([
        {
            "project_metric_id": "metric-1",
            "metric_name": "用水量",
            "is_required": False,
            "value": "-1",
            "text_value": None,
            "data_type": "number",
            "metric_snapshot": {},
            "attachment_file_ids": [],
        }
    ])

    assert issues[0]["issue_type"] == "negative_value"
    assert issues[0]["blocks_submission"] is False
