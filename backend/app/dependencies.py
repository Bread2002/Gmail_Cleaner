# Copyright (c) 2026, Rye Stahle-Smith; All rights reserved.
# Gmail Cleaner
# Last Updated: May 28th, 2026
# Description: FastAPI dependencies for the Gmail Cleaner backend
#              Provides shared logic for validating sessions and creating Gmail API service objects.

# Import necessary libraries and modules
from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends, HTTPException, Header, Query
from googleapiclient.discovery import build

from app import store
from app.services.gmail_auth import refresh_if_expired

# Define a helper function to resolve a session token and return the session dict
async def _resolve_session(session_token: str) -> dict:
    session = await store.session.get_session(session_token)
    if session is None:
        raise HTTPException(status_code=401, detail="Invalid or expired session token")

    # Refresh credentials if needed
    credentials = session["credentials"]
    credentials = refresh_if_expired(credentials)
    await store.session.update_credentials(session_token, credentials)
    session["credentials"] = credentials

    return session

# Define a helper function to extract the session from the Authorization header (for REST endpoints)
async def get_session_from_header(
    authorization: Annotated[str | None, Header()] = None,
) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401, detail="Missing or invalid Authorization header"
        )
    session_token = authorization.removeprefix("Bearer ").strip()
    return await _resolve_session(session_token)

# Define a helper function to extract the session from a query parameter (for SSE endpoints)
async def get_session_from_query(
    token: Annotated[str | None, Query()] = None,
) -> dict:
    if not token:
        raise HTTPException(status_code=401, detail="Missing token query parameter")
    return await _resolve_session(token)

# Define a helper function to create a Gmail API service object for the authenticated user
def get_gmail_service(
    session: Annotated[dict, Depends(get_session_from_header)],
) -> Any:
    return build("gmail", "v1", credentials=session["credentials"])

# Define a helper function to create a Gmail API service object for SSE endpoints
def get_gmail_service_from_query(
    session: Annotated[dict, Depends(get_session_from_query)],
) -> Any:
    return build("gmail", "v1", credentials=session["credentials"])
