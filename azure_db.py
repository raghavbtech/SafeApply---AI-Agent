"""
SafeApply - Azure Cosmos DB Persistence Layer
==============================================

Replaces the previous local-JSON `database.py`.

Design notes
------------
* One Cosmos container ("emails") holds every recruitment message SafeApply has
  ever seen, partitioned by `/user_id`. This gives per-user isolation
  (Flaw 18) and survives Streamlit restarts (Flaw 19).
* A second container ("audit") holds a hash-chained action log. Each record
  stores the hash of the previous record, so deleting or editing a record
  breaks the chain and is detectable. This makes the "tamper-evident"
  claim in the UI actually true (Flaw 17).
* A third logical record type ("state") stores per-user sync bookkeeping,
  e.g. the timestamp of the last successful mailbox sync.
* If Cosmos is not configured or unreachable, every function silently falls
  back to a local JSON file. The app therefore still runs on a laptop with no
  network, which matters on presentation day.

Credentials are read from environment variables only. Never commit .env.
"""

import os
import json
import hashlib
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from dotenv import load_dotenv

load_dotenv()


# =========================================================
# CONFIGURATION
# =========================================================

COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT", "").strip()
COSMOS_KEY = os.getenv("COSMOS_KEY", "").strip()
COSMOS_DATABASE = os.getenv("COSMOS_DATABASE", "safeapply").strip()
COSMOS_EMAIL_CONTAINER = os.getenv("COSMOS_EMAIL_CONTAINER", "emails").strip()
COSMOS_AUDIT_CONTAINER = os.getenv("COSMOS_AUDIT_CONTAINER", "audit").strip()

# Identifies whose mailbox this is. In a real multi-user deployment this comes
# from the login session; for the prototype it comes from .env.
DEFAULT_USER_ID = os.getenv("SAFEAPPLY_USER_ID", "demo@safeapply.local").strip()

LOCAL_FALLBACK_PATH = os.getenv(
    "SAFEAPPLY_LOCAL_DB",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), ".safeapply_local_db.json"),
)

_client_lock = threading.Lock()
_containers: Dict[str, Any] = {}
_cosmos_failed = False


def is_cosmos_configured() -> bool:
    """True when real Cosmos credentials are present (not placeholders)."""
    return bool(
        COSMOS_ENDPOINT
        and COSMOS_KEY
        and COSMOS_ENDPOINT.startswith("https://")
        and not COSMOS_ENDPOINT.startswith("https://your-")
        and not COSMOS_KEY.startswith("your_")
    )


def storage_backend() -> str:
    """Human-readable backend name, for the sidebar status line."""
    if is_cosmos_configured() and not _cosmos_failed:
        return "Azure Cosmos DB"
    if is_cosmos_configured() and _cosmos_failed:
        return "Local JSON (Cosmos unreachable)"
    return "Local JSON (Cosmos not configured)"


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# =========================================================
# COSMOS CONNECTION
# =========================================================

def _get_container(name: str):
    """
    Lazily create the database/container and return a container client.
    Returns None if Cosmos is unavailable, which triggers local fallback.
    """
    global _cosmos_failed

    if not is_cosmos_configured() or _cosmos_failed:
        return None

    if name in _containers:
        return _containers[name]

    with _client_lock:
        if name in _containers:
            return _containers[name]
        try:
            from azure.cosmos import CosmosClient, PartitionKey
            from azure.cosmos.exceptions import CosmosResourceNotFoundError

            client = CosmosClient(COSMOS_ENDPOINT, credential=COSMOS_KEY)
            database = client.get_database_client(COSMOS_DATABASE)
            container = database.get_container_client(name)
            try:
                container.read()
            except CosmosResourceNotFoundError:
                database = client.create_database_if_not_exists(id=COSMOS_DATABASE)
                container = database.create_container_if_not_exists(
                    id=name,
                    partition_key=PartitionKey(path="/user_id"),
                )
            _containers[name] = container
            return container
        except Exception as exc:  # noqa: BLE001 - we intentionally degrade gracefully
            print(f"[azure_db] Cosmos unavailable ({exc}). Falling back to local JSON.")
            _cosmos_failed = True
            return None


# =========================================================
# LOCAL FALLBACK STORE
# =========================================================

def _local_load() -> Dict[str, List[Dict[str, Any]]]:
    if not os.path.exists(LOCAL_FALLBACK_PATH):
        return {"emails": [], "audit": [], "state": []}
    try:
        with open(LOCAL_FALLBACK_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        for key in ("emails", "audit", "state"):
            data.setdefault(key, [])
        return data
    except Exception:
        return {"emails": [], "audit": [], "state": []}


def _local_save(data: Dict[str, List[Dict[str, Any]]]) -> None:
    tmp = LOCAL_FALLBACK_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, default=str)
    os.replace(tmp, LOCAL_FALLBACK_PATH)


def _local_upsert(bucket: str, doc: Dict[str, Any]) -> None:
    data = _local_load()
    rows = data.get(bucket, [])
    for idx, existing in enumerate(rows):
        if existing.get("id") == doc.get("id") and existing.get("user_id") == doc.get("user_id"):
            rows[idx] = doc
            break
    else:
        rows.append(doc)
    data[bucket] = rows
    _local_save(data)


def _local_query(bucket: str, user_id: str) -> List[Dict[str, Any]]:
    return [r for r in _local_load().get(bucket, []) if r.get("user_id") == user_id]


# =========================================================
# STABLE DOCUMENT IDS
# =========================================================

def make_email_doc_id(message_id: str, sender: str = "", subject: str = "", date: str = "") -> str:
    """
    Build a stable, provider-independent document id.

    IMAP sequence numbers change between sessions, so they cannot be used as
    identity. The RFC 5322 Message-ID header is stable and globally unique.
    When it is missing (rare, but some bulk senders omit it) we hash the
    sender/subject/date triple instead.
    """
    basis = (message_id or "").strip()
    if not basis:
        basis = f"{sender}|{subject}|{date}"
    digest = hashlib.sha256(basis.encode("utf-8", errors="replace")).hexdigest()[:32]
    return f"msg_{digest}"


# =========================================================
# EMAIL DOCUMENTS
# =========================================================

EMAIL_DEFAULTS: Dict[str, Any] = {
    "doc_type": "email",
    "status": "unscanned",       # unscanned | scanned | error
    "folder": "inbox",           # inbox | spam   (SafeApply's own view)
    "mailbox_action": "none",    # none | moved_to_junk | move_failed | restored
    "user_decision": "none",     # none | applied | ignored
    "is_recruitment": True,
    "risk_score": None,
    "risk_level": None,
    "analysis": None,
    "company_name": "Unknown",
    "role_title": "Not Specified",
}


def _normalise_email(email: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Ensure an email dict has an id, a user_id, and all expected fields."""
    doc = dict(EMAIL_DEFAULTS)
    doc.update(email)

    if not doc.get("id"):
        doc["id"] = make_email_doc_id(
            doc.get("message_id", ""),
            doc.get("sender", ""),
            doc.get("subject", ""),
            doc.get("date", ""),
        )

    doc["user_id"] = user_id
    doc["doc_type"] = "email"
    doc.setdefault("synced_at", _utcnow())
    doc["updated_at"] = _utcnow()
    return doc


def db_save_emails(emails: List[Dict[str, Any]], user_id: str = DEFAULT_USER_ID) -> int:
    """
    Upsert a batch of emails. Existing documents are merged rather than
    replaced, so a re-sync never wipes an analysis that has already been done.
    Returns the number of documents written.
    """
    container = _get_container(COSMOS_EMAIL_CONTAINER)
    written = 0

    for raw in emails:
        doc = _normalise_email(raw, user_id)
        existing = db_fetch_email(doc["id"], user_id)

        if existing:
            # Preserve analysis state across re-syncs.
            for field in (
                "status", "folder", "mailbox_action", "user_decision",
                "risk_score", "risk_level", "analysis", "scanned_at",
                "original_risk_score", "original_risk_level", "user_override",
            ):
                if existing.get(field) not in (None, "", "unscanned", "none", "inbox"):
                    doc[field] = existing[field]
            doc["synced_at"] = existing.get("synced_at", doc["synced_at"])

        if container is not None:
            try:
                container.upsert_item(body=doc)
                written += 1
                continue
            except Exception as exc:  # noqa: BLE001
                print(f"[azure_db] upsert failed for {doc['id']}: {exc}")

        _local_upsert("emails", doc)
        written += 1

    return written


def db_fetch_email(doc_id: str, user_id: str = DEFAULT_USER_ID) -> Optional[Dict[str, Any]]:
    """Read a single email document, or None when it does not exist."""
    container = _get_container(COSMOS_EMAIL_CONTAINER)
    if container is not None:
        try:
            return container.read_item(item=doc_id, partition_key=user_id)
        except Exception:
            return None

    for row in _local_query("emails", user_id):
        if row.get("id") == doc_id:
            return row
    return None


def db_fetch_all_emails(
    user_id: str = DEFAULT_USER_ID,
    folder: Optional[str] = None,
    status: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Return this user's stored recruitment emails, newest sync first.
    Optionally filter by SafeApply folder ('inbox' / 'spam') or status.
    """
    container = _get_container(COSMOS_EMAIL_CONTAINER)

    if container is not None:
        query = "SELECT * FROM c WHERE c.doc_type = 'email'"
        params: List[Dict[str, Any]] = []
        if folder:
            query += " AND c.folder = @folder"
            params.append({"name": "@folder", "value": folder})
        if status:
            query += " AND c.status = @status"
            params.append({"name": "@status", "value": status})
        query += " ORDER BY c.synced_at DESC"
        try:
            return list(
                container.query_items(
                    query=query,
                    parameters=params,
                    partition_key=user_id,
                )
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[azure_db] query failed: {exc}")

    rows = _local_query("emails", user_id)
    if folder:
        rows = [r for r in rows if r.get("folder") == folder]
    if status:
        rows = [r for r in rows if r.get("status") == status]
    return sorted(rows, key=lambda r: r.get("synced_at", ""), reverse=True)


def db_get_known_identifiers(user_id: str = DEFAULT_USER_ID) -> Tuple[Set[str], Set[str]]:
    """
    Return sets of (known_imap_uids, known_message_ids) for this user.
    Enables O(1) deduplication check so already-stored emails are never re-downloaded.
    """
    known_uids: Set[str] = set()
    known_msg_ids: Set[str] = set()

    container = _get_container(COSMOS_EMAIL_CONTAINER)
    if container is not None:
        try:
            items = container.query_items(
                query="SELECT c.imap_uid, c.message_id FROM c WHERE c.doc_type = 'email'",
                partition_key=user_id,
            )
            for item in items:
                uid = item.get("imap_uid")
                if uid:
                    known_uids.add(str(uid).strip())
                msg_id = item.get("message_id")
                if msg_id:
                    known_msg_ids.add(str(msg_id).strip())
            return known_uids, known_msg_ids
        except Exception as exc:  # noqa: BLE001
            print(f"[azure_db] known-identifiers query failed: {exc}")

    for r in _local_query("emails", user_id):
        if r.get("imap_uid"):
            known_uids.add(str(r["imap_uid"]).strip())
        if r.get("message_id"):
            known_msg_ids.add(str(r["message_id"]).strip())

    return known_uids, known_msg_ids


def db_update_email_fields(
    doc_id: str,
    fields: Dict[str, Any],
    user_id: str = DEFAULT_USER_ID,
) -> Optional[Dict[str, Any]]:
    """Patch specific fields on one stored email and persist the result."""
    doc = db_fetch_email(doc_id, user_id)
    if not doc:
        return None

    doc.update(fields)
    doc["updated_at"] = _utcnow()

    container = _get_container(COSMOS_EMAIL_CONTAINER)
    if container is not None:
        try:
            container.upsert_item(body=doc)
            return doc
        except Exception as exc:  # noqa: BLE001
            print(f"[azure_db] update failed for {doc_id}: {exc}")

    _local_upsert("emails", doc)
    return doc


def db_update_email_status(
    doc_id: str,
    new_status: str,
    user_id: str = DEFAULT_USER_ID,
) -> Optional[Dict[str, Any]]:
    """Backwards-compatible helper kept from the original database.py API."""
    return db_update_email_fields(doc_id, {"status": new_status}, user_id)


def db_mailbox_stats(user_id: str = DEFAULT_USER_ID) -> Dict[str, int]:
    """Counts used by the metric row in the Streamlit UI."""
    rows = db_fetch_all_emails(user_id)
    return {
        "total": len(rows),
        "inbox": len([r for r in rows if r.get("folder") == "inbox"]),
        "spam": len([r for r in rows if r.get("folder") == "spam"]),
        "unscanned": len([r for r in rows if r.get("status") == "unscanned"]),
        "critical": len([r for r in rows if r.get("risk_level") == "Critical"]),
        "high": len([r for r in rows if r.get("risk_level") == "High"]),
        "medium": len([r for r in rows if r.get("risk_level") == "Medium"]),
        "low": len([r for r in rows if r.get("risk_level") == "Low"]),
        "applied": len([r for r in rows if r.get("user_decision") == "applied"]),
        "ignored": len([r for r in rows if r.get("user_decision") == "ignored"]),
    }


# =========================================================
# HASH-CHAINED AUDIT LOG  (addresses Flaw 17)
# =========================================================

def _hash_record(record: Dict[str, Any]) -> str:
    payload = {k: v for k, v in record.items() if k != "record_hash"}
    blob = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def db_write_audit(
    action: str,
    email_doc_id: str,
    details: Dict[str, Any],
    user_id: str = DEFAULT_USER_ID,
) -> Dict[str, Any]:
    """
    Append an action to the audit chain.

    Each record embeds the hash of the previous record. Editing or removing
    any record breaks every hash after it, which db_verify_audit_chain()
    detects. This is what makes the log genuinely tamper-evident rather than
    just labelled that way.
    """
    history = db_fetch_audit(user_id)
    prev_hash = history[-1]["record_hash"] if history else "GENESIS"

    record = {
        "id": f"audit_{len(history) + 1:06d}_{hashlib.sha1(email_doc_id.encode()).hexdigest()[:8]}",
        "user_id": user_id,
        "doc_type": "audit",
        "sequence": len(history) + 1,
        "action": action,
        "email_doc_id": email_doc_id,
        "details": details,
        "timestamp": _utcnow(),
        "prev_hash": prev_hash,
    }
    record["record_hash"] = _hash_record(record)

    container = _get_container(COSMOS_AUDIT_CONTAINER)
    if container is not None:
        try:
            container.upsert_item(body=record)
            return record
        except Exception as exc:  # noqa: BLE001
            print(f"[azure_db] audit write failed: {exc}")

    _local_upsert("audit", record)
    return record


def db_fetch_audit(user_id: str = DEFAULT_USER_ID) -> List[Dict[str, Any]]:
    """Return the audit chain in sequence order."""
    container = _get_container(COSMOS_AUDIT_CONTAINER)
    if container is not None:
        try:
            return list(
                container.query_items(
                    query="SELECT * FROM c WHERE c.doc_type = 'audit' ORDER BY c.sequence ASC",
                    partition_key=user_id,
                )
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[azure_db] audit query failed: {exc}")

    return sorted(_local_query("audit", user_id), key=lambda r: r.get("sequence", 0))


def db_verify_audit_chain(user_id: str = DEFAULT_USER_ID) -> Dict[str, Any]:
    """
    Walk the chain and confirm every record's stored hash still matches its
    content, and that each record points at its predecessor.
    """
    records = db_fetch_audit(user_id)
    prev_hash = "GENESIS"

    for rec in records:
        if rec.get("prev_hash") != prev_hash:
            return {
                "valid": False,
                "records": len(records),
                "broken_at": rec.get("sequence"),
                "reason": "Previous-hash link does not match.",
            }
        if _hash_record(rec) != rec.get("record_hash"):
            return {
                "valid": False,
                "records": len(records),
                "broken_at": rec.get("sequence"),
                "reason": "Record content has been modified since it was written.",
            }
        prev_hash = rec["record_hash"]

    return {"valid": True, "records": len(records), "broken_at": None, "reason": ""}


# =========================================================
# APPLIED JOB PACKAGES
# =========================================================
# Kept in the same Cosmos account as the mail store (doc_type = "applied_job",
# same /user_id partition) so application history closes Flaw 18 the same way
# the mailbox does, instead of living in a separate local JSON file.

def db_save_applied_job(record: Dict[str, Any], user_id: str = DEFAULT_USER_ID) -> Dict[str, Any]:
    """Persist one prepared application package."""
    doc = dict(record)
    doc["id"] = doc.get("submission_id") or f"app_{hashlib.sha1(_utcnow().encode()).hexdigest()[:12]}"
    doc["user_id"] = user_id
    doc["doc_type"] = "applied_job"
    doc.setdefault("recorded_at", _utcnow())

    container = _get_container(COSMOS_EMAIL_CONTAINER)
    if container is not None:
        try:
            container.upsert_item(body=doc)
            return doc
        except Exception as exc:  # noqa: BLE001
            print(f"[azure_db] applied-job write failed: {exc}")

    _local_upsert("emails", doc)  # shares the same local fallback file
    return doc


def db_get_applied_jobs(user_id: str = DEFAULT_USER_ID) -> List[Dict[str, Any]]:
    """Return this user's prepared application packages, newest first."""
    container = _get_container(COSMOS_EMAIL_CONTAINER)
    if container is not None:
        try:
            return list(
                container.query_items(
                    query=(
                        "SELECT * FROM c WHERE c.doc_type = 'applied_job' "
                        "ORDER BY c.recorded_at DESC"
                    ),
                    partition_key=user_id,
                )
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[azure_db] applied-job query failed: {exc}")

    rows = [r for r in _local_query("emails", user_id) if r.get("doc_type") == "applied_job"]
    return sorted(rows, key=lambda r: r.get("recorded_at", ""), reverse=True)


# =========================================================
# PER-USER STATE (sync bookkeeping)
# =========================================================

def db_set_state(key: str, value: Any, user_id: str = DEFAULT_USER_ID) -> None:
    doc = {
        "id": f"state_{key}",
        "user_id": user_id,
        "doc_type": "state",
        "key": key,
        "value": value,
        "updated_at": _utcnow(),
    }
    container = _get_container(COSMOS_EMAIL_CONTAINER)
    if container is not None:
        try:
            container.upsert_item(body=doc)
            return
        except Exception as exc:  # noqa: BLE001
            print(f"[azure_db] state write failed: {exc}")
    _local_upsert("state", doc)


def db_get_state(key: str, default: Any = None, user_id: str = DEFAULT_USER_ID) -> Any:
    container = _get_container(COSMOS_EMAIL_CONTAINER)
    if container is not None:
        try:
            item = container.read_item(item=f"state_{key}", partition_key=user_id)
            return item.get("value", default)
        except Exception:
            return default

    for row in _local_query("state", user_id):
        if row.get("id") == f"state_{key}":
            return row.get("value", default)
    return default


# =========================================================
# SELF TEST
# =========================================================

if __name__ == "__main__":
    print(f"Storage backend: {storage_backend()}")

    sample = {
        "message_id": "<selftest-001@safeapply.local>",
        "sender": "hr.test@gmail.com",
        "sender_name": "Test HR",
        "subject": "Selection Letter",
        "date": "2026-09-18 10:00",
        "body": "Pay Rs 1499 registration fee to confirm.",
        "is_recruitment": True,
    }

    db_save_emails([sample])
    stored = db_fetch_all_emails()
    print(f"Stored emails for {DEFAULT_USER_ID}: {len(stored)}")

    db_write_audit("self_test", stored[0]["id"], {"note": "connectivity check"})
    print("Audit chain:", db_verify_audit_chain())