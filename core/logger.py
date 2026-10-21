"""
Enterprise Transaction Audit Logging Engine.

Integrates directly into the SQLAlchemy session lifecycle.
Ensures audit logs are committed ONLY when the parent business transaction succeeds,
and rolls back completely if the main transaction fails.
"""

from typing import Optional, Any
from uuid import UUID
from fastapi import Request
from sqlalchemy.orm import Session
from sqlalchemy import text
import json
from decimal import Decimal
from datetime import date, datetime

from shared.users.models import User


def _json_serial(obj):
    """JSON serializer for non-serializable types (UUID, Decimal, Date)."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Type {type(obj)} not JSON serializable")


class AuditLogger:
    """Enterprise audit logging utility tied to FastAPI request context and SQLAlchemy sessions."""

    @staticmethod
    def log_action(
            db: Session,
            request: Request,
            current_user: User,
            module: str,  # e.g., 'RM_INVENTORY'
            action: str,  # 'INSERT', 'UPDATE', 'SOFT_DELETE', 'RESTORE'
            table_name: str,  # e.g., 'tbl_raw_materials'
            record_id: UUID,  # Primary key of the affected record
            payload: Optional[Any] = None
    ) -> None:
        """
        Records a detailed audit log entry into schema_master.tbl_system_audit_logs
        and commits immediately.
        """
        try:
            client_ip = request.client.host if (request and request.client) else "127.0.0.1"
            workstation = getattr(current_user, "workstation_name", None) or "UNKNOWN-PC"

            # Convert payload to dict
            snapshot = None
            if payload is not None:
                if hasattr(payload, "model_dump"):
                    snapshot = payload.model_dump(mode="json")
                elif hasattr(payload, "dict"):
                    snapshot = payload.dict()
                elif isinstance(payload, dict):
                    snapshot = payload.copy()

            # 🟢 AUTOMATIC OVERWRITE: If the snapshot has created_by_id or updated_by_id,
            # guarantee it holds the real authenticated user ID (never a dummy Swagger UUID)!
            if isinstance(snapshot, dict):
                if action == "INSERT" and "created_by_id" in snapshot:
                    snapshot["created_by_id"] = str(current_user.id)
                elif action == "UPDATE" and "updated_by_id" in snapshot:
                    snapshot["updated_by_id"] = str(current_user.id)

            payload_json = json.dumps(snapshot, default=_json_serial) if snapshot else "{}"

            insert_sql = text("""
                    INSERT INTO schema_master.tbl_system_audit_logs (
                        timestamp, module, user_id, username, role, department, 
                        ip_address, workstation_name, action, table_name, 
                        record_id, payload_snapshot
                    ) VALUES (
                        NOW(), :module, :user_id, :username, :role, :department,
                        :ip_address, :workstation_name, :action, :table_name,
                        :record_id, CAST(:payload_snapshot AS JSONB)
                    )
                """)

            db.execute(insert_sql, {
                "module": module.upper(),
                "user_id": current_user.id,
                "username": current_user.username,
                "role": str(current_user.role),
                "department": str(current_user.department),
                "ip_address": client_ip,
                "workstation_name": workstation,
                "action": action.upper(),
                "table_name": table_name,
                "record_id": record_id,
                "payload_snapshot": payload_json
            })

            # Commit the audit entry permanently to PostgreSQL!
            db.commit()
            print(
                f"[AUDIT LOG SUCCESS] Logged {action} on {table_name} (Record ID: {record_id}) for user '{current_user.username}'")

        except Exception as err:
            db.rollback()
            print(f"[AUDIT LOG ERROR] Failed to write audit log: {str(err)}")