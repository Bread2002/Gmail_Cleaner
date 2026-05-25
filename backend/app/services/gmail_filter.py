# Copyright (c) 2026, Rye Stahle-Smith; All rights reserved.
# Gmail Cleaner
# Last Updated: May 24th, 2026
# Description: Implements the filter creation logic for blocking senders in Gmail.

# Import necessary libraries and modules
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import HTTPException
from googleapiclient import errors as google_errors


# Define a helper function to create a Gmail filter that trashes future emails from a specified sender
async def create_block_filter(service: Any, sender_email: str) -> str:
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
