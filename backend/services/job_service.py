"""
Background job status and execution tracker service.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
import azure_db


class JobService:
    @staticmethod
    def get_job_status(job_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        return azure_db.db_get_state(f"job_{job_id}", default=None, user_id=user_id)

    @staticmethod
    def record_job_progress(job_id: str, status: str, progress_pct: float, details: Dict[str, Any], user_id: str) -> None:
        azure_db.db_set_state(
            f"job_{job_id}",
            {
                "job_id": job_id,
                "status": status,
                "progress_pct": progress_pct,
                "details": details,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            user_id=user_id,
        )
