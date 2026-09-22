"""Session helpers: validate session id, track activity, cleanup expired sessions."""
import json
import re
from datetime import datetime, timezone, timedelta
from typing import Optional, List

from utils.config import SESSIONS_FILE, SESSION_TTL_MINUTES, UPLOAD_DIR, INDEX_DIR
from pathlib import Path

_SESSION_RE = re.compile(r"^[a-zA-Z0-9_-]{8,64}$")


def valid_session_id(session_id: Optional[str]) -> bool:
    if not session_id or not isinstance(session_id, str):
        return False
    return bool(_SESSION_RE.match(session_id.strip()))


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _load_sessions() -> dict:
    if SESSIONS_FILE.exists():
        try:
            return json.loads(SESSIONS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_sessions(data: dict) -> None:
    SESSIONS_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def touch_session(session_id: str) -> None:
    """Update last activity time for a session."""
    if not valid_session_id(session_id):
        return
    data = _load_sessions()
    data[session_id] = {"last_active": _now().isoformat()}
    _save_sessions(data)


def get_expired_session_ids() -> List[str]:
    data = _load_sessions()
    cutoff = _now() - timedelta(minutes=SESSION_TTL_MINUTES)
    expired = []
    for sid, info in data.items():
        try:
            last = datetime.fromisoformat(info.get("last_active", ""))
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            if last < cutoff:
                expired.append(sid)
        except Exception:
            expired.append(sid)
    return expired


def remove_sessions(session_ids: List[str]) -> None:
    if not session_ids:
        return
    data = _load_sessions()
    for sid in session_ids:
        data.pop(sid, None)
    _save_sessions(data)


def cleanup_expired_sessions(store) -> int:
    """
    Delete expired sessions and their documents from the store.
    `store` must be DocumentStore instance with delete_documents_for_session.
    Returns number of sessions cleaned.
    """
    expired = get_expired_session_ids()
    if not expired:
        return 0
    for sid in expired:
        try:
            store.delete_documents_for_session(sid)
        except Exception:
            pass
    remove_sessions(expired)
    return len(expired)
