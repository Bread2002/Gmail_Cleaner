# Copyright (c) 2026, Rye Stahle-Smith; All rights reserved.
# Gmail Cleaner
# Last Updated: May 28th, 2026
# Description: Defines API endpoints for authentication operations (login, callback, logout, and get current user) using Google OAuth and session management.

# Import necessary libraries and modules
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.models.auth import LoginResponse, CallbackRequest, CallbackResponse, MeResponse
from app.services import gmail_auth
from app import store
from app.dependencies import get_session_from_header

# Define the API router for authentication-related endpoints with a prefix and tags for documentation
router = APIRouter(prefix="/auth", tags=["auth"])


# Define the GET endpoint to initiate the OAuth login flow by generating the Google authorization URL (no authentication required)
@router.get("/login", response_model=LoginResponse)
async def login() -> LoginResponse:
    """Initiate the OAuth login flow by generating the Google authorization URL (no authentication required)."""
    auth_url, _ = await gmail_auth.build_authorization_url()
    return LoginResponse(auth_url=auth_url)


# Define the POST endpoint to handle the OAuth callback from Google, exchange the authorization code for tokens, create a server-side session, and return session details (no authentication required)
@router.post("/callback", response_model=CallbackResponse)
async def callback(body: CallbackRequest) -> CallbackResponse:
    """Handle the OAuth callback from Google, exchange the authorization code for tokens, create a server-side session, and return session details (no authentication required)."""
    try:
        credentials = await gmail_auth.exchange_code(code=body.code, state=body.state)
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
    await store.session.create_session(session_token, credentials, user_email, expires_at)

    return CallbackResponse(
        session_token=session_token,
        user_email=user_email,
        expires_at=expires_at,
    )


# Define the POST endpoint to log out the user by revoking the Google token and deleting the server-side session (requires a valid session token)
@router.post("/logout", status_code=204)
async def logout(
    session: Annotated[dict, Depends(get_session_from_header)],
) -> None:
    """Log out the user by revoking the Google token and deleting the server-side session (requires a valid session token)."""
    credentials = session.get("credentials")
    if credentials and credentials.token:
        try:
            import urllib.request

            urllib.request.urlopen(
                f"https://oauth2.googleapis.com/revoke?token={credentials.token}"
            )
        except Exception:
            pass  # Best-effort revocation

    await store.session.delete_session(session["_token"])


# Define the GET endpoint to return the authenticated user's email and authentication status (requires a valid session token)
@router.get("/me", response_model=MeResponse)
async def me(session: Annotated[dict, Depends(get_session_from_header)]) -> MeResponse:
    """Return the authenticated user's email and authentication status (requires a valid session token)."""
    return MeResponse(email=session["user_email"], authenticated=True)
