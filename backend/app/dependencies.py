"""
FastAPI dependency: get_gmail_service

Validates the session token from the Authorization header,
refreshes credentials if expired, and returns a ready-to-use Gmail service.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends, HTTPException, Header, Query
from googleapiclient.discovery import build

from app import store
from app.services.gmail_auth import refresh_if_expired


def _resolve_session(session_token: str) -> dict:
    """Shared logic: validate session token and return session dict."""
    session = store.session.get_session(session_token)
    if session is None:
        raise HTTPException(status_code=401, detail="Invalid or expired session token")

    # Refresh credentials if needed
    credentials = session["credentials"]
    credentials = refresh_if_expired(credentials)
    store.session.update_credentials(session_token, credentials)
    session["credentials"] = credentials

    return session


def get_session_from_header(
    authorization: Annotated[str | None, Header()] = None,
) -> dict:
    """Dependency for standard REST endpoints (Authorization: Bearer <token>)."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401, detail="Missing or invalid Authorization header"
        )
    session_token = authorization.removeprefix("Bearer ").strip()
    return _resolve_session(session_token)


def get_session_from_query(
    token: Annotated[str | None, Query()] = None,
) -> dict:
    """
    Dependency for SSE endpoints.
    The browser's native EventSource cannot send custom headers,
    so the session token is passed as ?token=... query parameter.
    """
    if not token:
        raise HTTPException(status_code=401, detail="Missing token query parameter")
    return _resolve_session(token)


def get_gmail_service(
    session: Annotated[dict, Depends(get_session_from_header)],
) -> Any:
    """Returns a Gmail API service object for the authenticated user."""
    return build("gmail", "v1", credentials=session["credentials"])


def get_gmail_service_from_query(
    session: Annotated[dict, Depends(get_session_from_query)],
) -> Any:
    """Same as get_gmail_service but reads token from query param (for SSE routes)."""
    return build("gmail", "v1", credentials=session["credentials"])
