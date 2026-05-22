"""
In-memory session store.

Key: session_token (UUID string)
Value: SessionData dict

Designed so a Redis backend can replace this later with the same interface.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from google.oauth2.credentials import Credentials

# ---------------------------------------------------------------------------
# Internal store
# ---------------------------------------------------------------------------

_sessions: dict[str, dict[str, Any]] = {}
# pending OAuth state nonces → (Flow object, expiry timestamp)
_pending_states: dict[str, tuple[Any, datetime]] = {}


# ---------------------------------------------------------------------------
# Session CRUD
# ---------------------------------------------------------------------------


def create_session(
    session_token: str, credentials: Credentials, user_email: str, expires_at: datetime
) -> None:
    """Store a new authenticated session."""
    _sessions[session_token] = {
        "credentials": credentials,
        "user_email": user_email,
        "expires_at": expires_at,
        # Per-session mutable state
        "settings": {
            "consecutive_unread_threshold": 20,
            "max_senders": 10,
            "max_messages_per_sender": 100,
            "dry_run_by_default": False,
        },
        # scan_id → ScanResult (dict)
        "scan_results": {},
        # scan_id / job_id → asyncio.Queue
        "queues": {},
    }


def get_session(session_token: str) -> dict[str, Any] | None:
    """Return the session dict or None if missing / expired."""
    session = _sessions.get(session_token)
    if session is None:
        return None
    if session["expires_at"] < datetime.now(timezone.utc):
        delete_session(session_token)
        return None
    return session


def delete_session(session_token: str) -> None:
    _sessions.pop(session_token, None)


def update_credentials(session_token: str, credentials: Credentials) -> None:
    session = _sessions.get(session_token)
    if session:
        session["credentials"] = credentials


def get_settings(session_token: str) -> dict[str, Any]:
    session = _sessions[session_token]
    return session["settings"].copy()


def update_settings(session_token: str, patch: dict[str, Any]) -> dict[str, Any]:
    session = _sessions[session_token]
    session["settings"].update(patch)
    return session["settings"].copy()


# ---------------------------------------------------------------------------
# Scan / job result storage
# ---------------------------------------------------------------------------


def store_scan_result(session_token: str, scan_id: str, result: dict[str, Any]) -> None:
    _sessions[session_token]["scan_results"][scan_id] = result


def get_scan_result(session_token: str, scan_id: str) -> dict[str, Any] | None:
    return _sessions[session_token]["scan_results"].get(scan_id)


# ---------------------------------------------------------------------------
# SSE queues (one asyncio.Queue per scan or trash job)
# ---------------------------------------------------------------------------


def create_queue(session_token: str, queue_id: str) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue()
    _sessions[session_token]["queues"][queue_id] = q
    return q


def get_queue(session_token: str, queue_id: str) -> asyncio.Queue | None:
    session = _sessions.get(session_token)
    if session is None:
        return None
    return session["queues"].get(queue_id)


def delete_queue(session_token: str, queue_id: str) -> None:
    session = _sessions.get(session_token)
    if session:
        session["queues"].pop(queue_id, None)


# ---------------------------------------------------------------------------
# OAuth state nonce management
# ---------------------------------------------------------------------------


def store_state(state: str, flow: Any, expiry: datetime) -> None:
    _pending_states[state] = (flow, expiry)


def pop_state(state: str) -> Any | None:
    """Retrieve and remove a pending OAuth flow by state nonce."""
    entry = _pending_states.pop(state, None)
    if entry is None:
        return None
    flow, expiry = entry
    if expiry < datetime.now(timezone.utc):
        return None
    return flow
