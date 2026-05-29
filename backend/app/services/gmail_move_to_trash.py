# Copyright (c) 2026, Rye Stahle-Smith; All rights reserved.
# Gmail Cleaner
# Last Updated: May 28th, 2026
# Description: Implements move-to-trash logic (messages moved here are recoverable for 30 days via Gmail).

# Import necessary libraries and modules
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from googleapiclient.errors import HttpError

# Initialize logging for this module
log = logging.getLogger("gmail_cleaner.move_to_trash")

# Configure the maximum IDs per batchModify call (Gmail API limit).
_BATCH_SIZE = 1000


# Define a helper function to execute a Google API request with exponential backoff on rate-limit errors (403/429).
def _execute_with_backoff(request: Any, max_retries: int = 5) -> Any:
    for attempt in range(max_retries):
        try:
            return request.execute()
        except HttpError as exc:
            if exc.resp.status in (429, 403) and attempt < max_retries - 1:
                wait = 2**attempt  # 1 s, 2 s, 4 s, 8 s, 16 s
                log.warning(
                    "Rate limit hit (attempt %d/%d) — backing off %ds…",
                    attempt + 1,
                    max_retries,
                    wait,
                )
                time.sleep(wait)
            else:
                raise


# Define the main function to move all messages from a specified sender to Gmail Trash (recoverable for 30 days),
# emitting progress events to a queue.
async def run_move_to_trash(
    service: Any,
    queue: asyncio.Queue,
    sender_email: str,
    dry_run: bool,
    store_result_fn: Any,
) -> None:
    loop = asyncio.get_running_loop()
    log.info(
        "Move-to-trash job starting for sender=%r dry_run=%s", sender_email, dry_run
    )

    async def api(fn):
        return await loop.run_in_executor(None, fn)

    async def emit(event_type: str, data: dict) -> None:
        log.debug("[move-to-trash SSE] %s: %s", event_type, data)
        await queue.put({"type": event_type, "data": data})

    try:
        # Fetch all messages from the sender
        sender_messages: list[dict] = []
        page_token = None
        while True:
            kwargs: dict = {
                "userId": "me",
                "q": f"from:{sender_email}",
                "maxResults": 500,
            }
            if page_token:
                kwargs["pageToken"] = page_token
            result = await api(
                lambda k=kwargs: _execute_with_backoff(
                    service.users().messages().list(**k)
                )
            )
            sender_messages.extend(result.get("messages", []))
            page_token = result.get("nextPageToken")
            if not page_token:
                break

        log.info(
            "Move-to-trash job: found %d messages from %r",
            len(sender_messages),
            sender_email,
        )

        total = len(sender_messages)
        await emit(
            "progress",
            {
                "trashed": 0,
                "total": total,
                "batch": 0,
                "message": f"Found {total} messages…",
            },
        )

        if dry_run:
            store_result_fn(
                {"trashed_count": total, "sender": sender_email, "dry_run": True}
            )
            await emit(
                "complete",
                {"trashed_count": total, "sender": sender_email, "dry_run": True},
            )
            return

        # Move to trash in batches of 1000 using batchModify (recoverable via Gmail for 30 days)
        message_batches = [
            sender_messages[i : i + _BATCH_SIZE]
            for i in range(0, len(sender_messages), _BATCH_SIZE)
        ]
        total_batches = len(message_batches)
        moved_so_far = 0

        for batch_idx, batch_messages in enumerate(message_batches):
            ids = [m["id"] for m in batch_messages]
            await api(
                lambda id_list=ids: _execute_with_backoff(
                    service.users()
                    .messages()
                    .batchModify(
                        userId="me",
                        body={"ids": id_list, "addLabelIds": ["TRASH"]},
                    )
                )
            )
            moved_so_far += len(batch_messages)
            await emit(
                "progress",
                {
                    "trashed": moved_so_far,
                    "total": total,
                    "batch": batch_idx + 1,
                    "total_batches": total_batches,
                },
            )

        result = {
            "trashed_count": moved_so_far,
            "sender": sender_email,
            "dry_run": False,
        }
        store_result_fn(result)
        await emit("complete", result)

    except Exception as exc:
        await emit("error", {"detail": str(exc)})
    finally:
        await queue.put(None)  # Closes the SSE stream
