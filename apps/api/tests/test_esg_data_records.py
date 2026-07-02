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
