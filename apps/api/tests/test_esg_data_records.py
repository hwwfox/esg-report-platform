from app.modules.esg_data_router import promote_submission_to_esg_data_records


class _Result:
    def __init__(self, rowcount=0):
        self.rowcount = rowcount


class _Db:
    def __init__(self):
        self.calls = []

    def execute(self, statement, params):
        query = str(statement)
        self.calls.append((query, params))
        if query.lstrip().startswith("INSERT INTO esg_data_records"):
            return _Result(2)
        return _Result(0)


def test_promote_submission_to_esg_data_records_is_project_and_source_scoped():
    db = _Db()

    count = promote_submission_to_esg_data_records(
        db,
        tenant_id="tenant-1",
        enterprise_id="enterprise-1",
        project_id="project-1",
        task_id="task-1",
        submission_id="submission-1",
    )

    assert count == 2
    delete_query, delete_params = db.calls[0]
    insert_query, insert_params = db.calls[1]
    assert "tenant_id=:tenant_id" in delete_query
    assert "project_id=:project_id" in delete_query
    assert "source_task_id=:task_id" in delete_query
    assert "source_submission_id=:submission_id" in delete_query
    assert "INSERT INTO esg_data_records" in insert_query
    assert "source_task_id" in insert_query
    assert "source_submission_id" in insert_query
    assert "source_file_ids" in insert_query
    assert insert_params["enterprise_id"] == "enterprise-1"
    assert delete_params["tenant_id"] == "tenant-1"


def test_esg_data_record_sources_uses_existing_project_scoped_file_columns(monkeypatch):
    from types import SimpleNamespace
    import app.modules.esg_data_router as esg_data_router

    monkeypatch.setattr(
        esg_data_router,
        "_authorize_project",
        lambda request, db, user, project_id: {"project_id": project_id, "enterprise_id": "enterprise-1"},
    )

    class _Mappings:
        def __init__(self, rows):
            self.rows = rows

        def first(self):
            return self.rows[0] if self.rows else None

        def all(self):
            return self.rows

    class _QueryResult:
        def __init__(self, rows):
            self.rows = rows

        def mappings(self):
            return _Mappings(self.rows)

    class _SourcesDb:
        def __init__(self):
            self.calls = []

        def execute(self, statement, params):
            query = str(statement)
            self.calls.append((query, params))
            if "FROM esg_data_records" in query:
                return _QueryResult([
                    {
                        "data_record_id": "record-1",
                        "source_task_id": "task-1",
                        "source_submission_id": "submission-1",
                        "source_submission_item_id": "item-1",
                        "source_file_ids": ["file-1"],
                        "topic_name": "topic",
                        "metric_name": "metric",
                    }
                ])
            return _QueryResult([])

    request = SimpleNamespace(state=SimpleNamespace(request_id="req-1"))
    user = {"current_tenant_id": "tenant-1"}
    db = _SourcesDb()

    response = esg_data_router.esg_data_record_sources("project-1", "record-1", request, db, user)

    file_query, file_params = db.calls[1]
    assert "file_name AS original_filename" in file_query
    assert "uploaded_at AS created_at" in file_query
    assert "original_filename" not in file_query.split("FROM file_objects")[0].replace("file_name AS original_filename", "")
    assert "created_at" not in file_query.split("FROM file_objects")[0].replace("uploaded_at AS created_at", "")
    assert "enterprise_id=:enterprise_id" in file_query
    assert "project_id=:project_id" in file_query
    assert "tenant_id=:tenant_id" in file_query
    assert file_params["enterprise_id"] == "enterprise-1"
    assert file_params["project_id"] == "project-1"
    assert response["success"] is True
