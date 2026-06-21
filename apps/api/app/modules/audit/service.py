from sqlalchemy import text
from sqlalchemy.orm import Session


def write_audit_log(db: Session, *, tenant_id: str, action_type: str, user_id: str | None = None, user_name: str | None = None, enterprise_id: str | None = None, project_id: str | None = None, object_type: str | None = None, object_id: str | None = None, description: str | None = None, ip_address: str | None = None, user_agent: str | None = None) -> None:
    db.execute(text("""
        INSERT INTO audit_logs (tenant_id, enterprise_id, project_id, user_id, user_name, action_type, object_type, object_id, description, ip_address, user_agent)
        VALUES (:tenant_id, :enterprise_id, :project_id, :user_id, :user_name, :action_type, :object_type, :object_id, :description, :ip_address, :user_agent)
    """), locals())
