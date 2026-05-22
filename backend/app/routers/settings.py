"""
Settings router — /settings/*

GET   /settings  → load user settings for this session
PATCH /settings  → update one or more settings fields
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.models.settings import UserSettings, SettingsPatch
from app.dependencies import get_session_from_header
from app import store

router = APIRouter(prefix="/settings", tags=["settings"])


def _get_session_token(session: dict) -> str:
    from app.store.session import _sessions

    return next((t for t, s in _sessions.items() if s is session), "")


@router.get("", response_model=UserSettings)
async def get_settings(
    session: Annotated[dict, Depends(get_session_from_header)],
) -> UserSettings:
    session_token = _get_session_token(session)
    raw = store.session.get_settings(session_token)
    return UserSettings(**raw)


@router.patch("", response_model=UserSettings)
async def patch_settings(
    body: SettingsPatch,
    session: Annotated[dict, Depends(get_session_from_header)],
) -> UserSettings:
    session_token = _get_session_token(session)
    # Only apply fields that were explicitly provided (not None)
    patch = {k: v for k, v in body.model_dump().items() if v is not None}
    updated = store.session.update_settings(session_token, patch)
    return UserSettings(**updated)
