"""
Gmail filter creation — async port of stop_sender() from original main.py.

Changes vs original:
- Returns filter_id instead of printing
- Raises HTTPException instead of silently printing errors
- Async (run_in_executor wraps the blocking API call)
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import HTTPException
from googleapiclient import errors as google_errors


async def create_block_filter(service: Any, sender_email: str) -> str:
    """
    Create a Gmail filter that permanently trashes future emails from sender_email.

    Ported from stop_sender() in original main.py (lines 40–58).
    Returns the created filter's ID.
    """
    loop = asyncio.get_event_loop()

    filter_request = {
        "criteria": {
            "from": sender_email,
        },
        "action": {
            "removeLabelIds": ["INBOX"],
            "addLabelIds": ["TRASH"],
        },
    }

    try:
        result = await loop.run_in_executor(
            None,
            lambda: service.users()
            .settings()
            .filters()
            .create(userId="me", body=filter_request)
            .execute(),
        )
        return result.get("id", "")
    except google_errors.HttpError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create Gmail filter for {sender_email}: {e}",
        )
