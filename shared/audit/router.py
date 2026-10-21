"""
API Router for Global System Audit Logs.

Provides company-wide audit trail inspection across all modules (RM, FG, Production).
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from core.database import get_db
from core.dependencies import require_role

# Notice the prefix is global (/api/v1/system/audit-logs), not tied to /rm/
router = APIRouter(prefix="/api/v1/system/audit-logs", tags=["Global System Audit Logs"])


@router.get(
    "/",
    summary="Retrieve global system audit logs (Admin / Supervisor only)"
)
def get_system_audit_logs(
    module: Optional[str] = Query(None, description="Filter by module (e.g. 'RM_INVENTORY')"),
    username: Optional[str] = Query(None, description="Filter by operator username"),
    table_name: Optional[str] = Query(None, description="Filter by table name"),
    action: Optional[str] = Query(None, description="Filter by action ('INSERT', 'UPDATE', 'SOFT_DELETE')"),
    limit: int = Query(100, ge=1, le=1000, description="Max records to return"),
    offset: int = Query(0, ge=0, description="Records to skip for pagination"),
    db: Session = Depends(get_db),
    current_user = Depends(require_role("ADMIN", "RM_SUPERVISOR"))
):
    """
    Returns a paginated list of global audit entries logged across all departments.
    Restricted to ADMIN and RM_SUPERVISOR roles.
    """
    query = """
            SELECT 
                id, timestamp, module, username, role, department, 
                ip_address, workstation_name, action, table_name, 
                record_id, payload_snapshot
            FROM schema_master.tbl_system_audit_logs
            WHERE 1 = 1
        """
    params = {"limit": limit, "offset": offset}

    if module and module.strip().lower() != "all":
        query += " AND module = :module"
        params["module"] = module.strip().upper()

    if username and username.strip().lower() != "all":
        query += " AND LOWER(username) = :username"
        params["username"] = username.strip().lower()

    if table_name and table_name.strip().lower() != "all":
        query += " AND table_name = :table_name"
        params["table_name"] = table_name.strip()

    if action and action.strip().lower() != "all":
        query += " AND action = :action"
        params["action"] = action.strip().upper()

    query += " ORDER BY timestamp DESC LIMIT :limit OFFSET :offset"

    result = db.execute(text(query), params)
    rows = result.mappings().all()

    return [dict(row) for row in rows]