"""
Auth router — /auth/*

GET  /auth/login     → returns Google OAuth URL
POST /auth/callback  → exchanges code for tokens, creates session
POST /auth/logout    → revokes token, destroys session
GET  /auth/me        → returns current user email
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from app.models.auth import LoginResponse, CallbackRequest, CallbackResponse, MeResponse
from app.services import gmail_auth
from app import store
from app.dependencies import get_session_from_header

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login", response_model=LoginResponse)
async def login() -> LoginResponse:
    """
    Step 1 of OAuth flow: build the Google authorization URL.
    The frontend redirects window.location to this URL.
    """
    auth_url, _state = gmail_auth.build_authorization_url()
    return LoginResponse(auth_url=auth_url)


@router.post("/callback", response_model=CallbackResponse)
async def callback(body: CallbackRequest) -> CallbackResponse:
    """
    Step 2 of OAuth flow: exchange authorization code for tokens.
    Called by the frontend CallbackPage after Google redirects back.
    """
    try:
        credentials = gmail_auth.exchange_code(code=body.code, state=body.state)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"OAuth exchange failed: {exc}")

    # Get the user's email from Google
    try:
        user_email = gmail_auth.get_user_email(credentials)
    except Exception:
        user_email = "unknown@gmail.com"

    # Create a server-side session
    session_token = str(uuid.uuid4())
    from app.config import settings

    expires_at = datetime.now(timezone.utc) + timedelta(
        seconds=settings.session_ttl_seconds
    )
    store.session.create_session(session_token, credentials, user_email, expires_at)

    return CallbackResponse(
        session_token=session_token,
        user_email=user_email,
        expires_at=expires_at,
    )


@router.post("/logout", status_code=204)
async def logout(
    session: Annotated[dict, Depends(get_session_from_header)],
    authorization: str = "",
) -> None:
    """Revoke the Google token and destroy the server-side session."""
    from fastapi import Header

    # We need the raw token to delete the session; extract from session dict
    # (FastAPI injects session via Depends, so we can't easily get the token here;
    #  we store it as a header for lookup)
    # Simple approach: find by credentials object identity — not great for scale,
    # but fine for local use. A proper fix would pass session_token through Depends.
    credentials = session.get("credentials")
    if credentials and credentials.token:
        try:
            import urllib.request

            urllib.request.urlopen(
                f"https://oauth2.googleapis.com/revoke?token={credentials.token}"
            )
        except Exception:
            pass  # Best-effort revocation

    # Find and delete the session by credentials identity
    from app.store.session import _sessions

    token_to_delete = None
    for tok, sess in list(_sessions.items()):
        if sess.get("credentials") is credentials:
            token_to_delete = tok
            break
    if token_to_delete:
        store.session.delete_session(token_to_delete)


@router.get("/me", response_model=MeResponse)
async def me(session: Annotated[dict, Depends(get_session_from_header)]) -> MeResponse:
    """Return the authenticated user's email."""
    return MeResponse(email=session["user_email"], authenticated=True)
