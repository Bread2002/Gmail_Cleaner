"""
Permanent email deletion — replaces the old move-to-trash approach.

Changes vs original:
- Uses messages.batchDelete (permanent, up to 1000 IDs per call) instead of
  messages.trash (which only moves to the Trash label for 30 days).
- Requires the https://mail.google.com/ scope instead of gmail.modify.
- Query is "from:X" with no -in:trash filter — catches messages already sitting
  in Trash from previous runs as well as inbox/other messages.
- No cleanup pass needed: batchDelete is atomic per batch, no pagination race.
- No verification step: deleted means gone, nothing to count afterwards.
- run_in_executor wraps each batchDelete call (blocking I/O in thread pool).
- Progress events emitted to asyncio.Queue after each batch.
- dry_run mode skips actual API calls but still reports what would happen.
- _execute_with_backoff retries 403/429 rate-limit errors with exponential backoff.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from googleapiclient.errors import HttpError

log = logging.getLogger("gmail_cleaner.trash")

# Maximum IDs per batchDelete call (Gmail API limit).
_BATCH_SIZE = 1000


def _execute_with_backoff(request: Any, max_retries: int = 5) -> Any:
    """
    Execute a Google API request, retrying with exponential backoff on
    rate-limit errors (403 rateLimitExceeded / 429 Too Many Requests).
    Runs in a thread-pool executor — time.sleep() is safe here.
    """
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


async def run_trash(
    service: Any,
    queue: asyncio.Queue,
    sender_email: str,
    dry_run: bool,
    store_result_fn: Any,
) -> None:
    """
    Background task: permanently deletes all messages from sender_email
    using messages.batchDelete (up to 1000 IDs per API call).

    Unlike the old approach this catches messages already sitting in Trash
    and removes them immediately rather than waiting for Gmail's 30-day purge.

    Emits SSE progress events to `queue`.
    """
    loop = asyncio.get_running_loop()
    log.info("Delete job starting for sender=%r dry_run=%s", sender_email, dry_run)

    async def api(fn):
        return await loop.run_in_executor(None, fn)

    async def emit(event_type: str, data: dict) -> None:
        log.debug("[trash SSE] %s: %s", event_type, data)
        await queue.put({"type": event_type, "data": data})

    try:
        # ── Fetch ALL messages from sender ───────────────────────────────────
        # No -in:trash filter — we want everything: inbox, sent, spam, trash.
        # batchDelete handles already-deleted IDs gracefully (no error).
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
            "Delete job: found %d messages from %r",
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

        # ── Permanently delete in batches of 1000 ───────────────────────────
        # batchDelete is a single POST with a JSON body of IDs — far fewer API
        # calls than the old batch-HTTP-request approach (1000 vs 50 per call).
        # It returns 204 No Content on success; HttpError on failure.
        message_batches = [
            sender_messages[i : i + _BATCH_SIZE]
            for i in range(0, len(sender_messages), _BATCH_SIZE)
        ]
        total_batches = len(message_batches)
        deleted_so_far = 0

        for batch_idx, batch_messages in enumerate(message_batches):
            ids = [m["id"] for m in batch_messages]
            await api(
                lambda id_list=ids: _execute_with_backoff(
                    service.users().messages().batchDelete(
                        userId="me", body={"ids": id_list}
                    )
                )
            )
            deleted_so_far += len(batch_messages)
            await emit(
                "progress",
                {
                    "trashed": deleted_so_far,
                    "total": total,
                    "batch": batch_idx + 1,
                    "total_batches": total_batches,
                },
            )

        result = {
            "trashed_count": deleted_so_far,
            "sender": sender_email,
            "dry_run": False,
        }
        store_result_fn(result)
        await emit("complete", result)

    except Exception as exc:
        await emit("error", {"detail": str(exc)})
    finally:
        await queue.put(None)  # SSE sentinel
