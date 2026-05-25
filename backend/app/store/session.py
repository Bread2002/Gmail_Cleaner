# Copyright (c) 2026, Rye Stahle-Smith; All rights reserved.
# Gmail Cleaner
# Last Updated: May 24th, 2026
# Description: In-memory session store for the Gmail Cleaner backend.
#              Designed for easy replacement with Redis in the future.

# Import necessary libraries and modules
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from google.oauth2.credentials import Credentials

# Define in-memory session storage structure
_sessions: dict[str, dict[str, Any]] = {}

# Define temporary storage structure for pending OAuth flows (by state)
_pending_states: dict[str, tuple[Any, datetime]] = {}

# Define a helper function to create and store a new session for an authenticated user
def create_session(
    session_token: str, credentials: Credentials, user_email: str, expires_at: datetime
) -> None:
    _sessions[session_token] = {
        "credentials": credentials,
        "user_email": user_email,
        "expires_at": expires_at,
        # Per-session settings (mutable state)
        "settings": {
            "consecutive_unread_threshold": 20,
            "max_senders": 10,
            "max_messages_per_sender": 100,
            "dry_run_by_default": False,
        },
        "scan_results": {},
        "queues": {},
    }

# Define a helper function to retrieve the session for a given session token (returns None if missing/expired)
def get_session(session_token: str) -> dict[str, Any] | None:
    session = _sessions.get(session_token)
    if session is None:
        return None
    if session["expires_at"] < datetime.now(timezone.utc):
        delete_session(session_token)
        return None
    return session

# Define a helper function to delete a session (e.g. logout or token expiry)
def delete_session(session_token: str) -> None:
    _sessions.pop(session_token, None)

# Define a helper function to update the credentials for an existing session (e.g. token refresh)
def update_credentials(session_token: str, credentials: Credentials) -> None:
    session = _sessions.get(session_token)
    if session:
        session["credentials"] = credentials

# Define helper functions to access the user settings for a session
def get_settings(session_token: str) -> dict[str, Any]:
    session = _sessions[session_token]
    return session["settings"].copy()

# Define a helper function to update user settings for a session
def update_settings(session_token: str, patch: dict[str, Any]) -> dict[str, Any]:
    session = _sessions[session_token]
    session["settings"].update(patch)
    return session["settings"].copy()

# Define a helper function to retrieve scan results for a session
def get_scan_result(session_token: str, scan_id: str) -> dict[str, Any] | None:
    return _sessions[session_token]["scan_results"].get(scan_id)

# Define a helper functions to store scan results for a session
def store_scan_result(session_token: str, scan_id: str, result: dict[str, Any]) -> None:
    _sessions[session_token]["scan_results"][scan_id] = result

# Define a helper function to create a new queue for a session (e.g. for streaming scan results)
def create_queue(session_token: str, queue_id: str) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue()
    _sessions[session_token]["queues"][queue_id] = q
    return q

# Define a helper function to retrieve a queue for a session
def get_queue(session_token: str, queue_id: str) -> asyncio.Queue | None:
    session = _sessions.get(session_token)
    if session is None:
        return None
    return session["queues"].get(queue_id)

# Define a helper function to delete a queue for a session (e.g. when streaming is done)
def delete_queue(session_token: str, queue_id: str) -> None:
    session = _sessions.get(session_token)
    if session:
        session["queues"].pop(queue_id, None)

# Define a helper function to store a pending OAuth flow
def store_state(state: str, flow: Any, expiry: datetime) -> None:
    _pending_states[state] = (flow, expiry)

# Define a helper function to retrieve and remove a pending OAuth flow (returns None if missing/expired)
def pop_state(state: str) -> Any | None:
    entry = _pending_states.pop(state, None)
    if entry is None:
        return None
    flow, expiry = entry
    if expiry < datetime.now(timezone.utc):
        return None
    return flow
