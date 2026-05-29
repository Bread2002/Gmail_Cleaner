# Copyright (c) 2026, Rye Stahle-Smith; All rights reserved.
# Gmail Cleaner
# Last Updated: May 28th, 2026
# Description: Defines API endpoints for user settings management (get and update settings) with authentication via session tokens.

# Import necessary libraries and modules
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.models.settings import UserSettings, SettingsPatch
from app.dependencies import get_session_from_header
from app import store

# Define the API router for settings-related endpoints with a prefix and tags for documentation
router = APIRouter(prefix="/settings", tags=["settings"])


# Define a helper function to retrieve the session token from the session dictionary
def _get_session_token(session: dict) -> str:
    return session["_token"]


# Define the GET endpoint to retrieve the current user's settings (requires authentication via session token)
@router.get("", response_model=UserSettings)
async def get_settings(
    session: Annotated[dict, Depends(get_session_from_header)],
) -> UserSettings:
    """Retrieve the current user's settings (requires authentication via session token)."""
    session_token = _get_session_token(session)
    raw = await store.session.get_settings(session_token)
    return UserSettings(**raw)


# Define the PATCH endpoint to update the current user's settings (requires authentication via session token)
@router.patch("", response_model=UserSettings)
async def patch_settings(
    body: SettingsPatch,
    session: Annotated[dict, Depends(get_session_from_header)],
) -> UserSettings:
    """Update the current user's settings (requires authentication via session token)."""
    session_token = _get_session_token(session)
    # Only apply fields that were explicitly provided (not None)
    patch = {k: v for k, v in body.model_dump().items() if v is not None}
    updated = await store.session.update_settings(session_token, patch)
    return UserSettings(**updated)
