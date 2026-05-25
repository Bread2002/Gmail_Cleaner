# Copyright (c) 2026, Rye Stahle-Smith; All rights reserved.
# Gmail Cleaner
# Last Updated: May 24th, 2026
# Description: Implements the email scanning logic using the batch API to efficiently identify senders with a high number of unread messages.

# Import necessary libraries and modules
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any

from googleapiclient.errors import HttpError

# Initialize logging for this module
log = logging.getLogger("gmail_cleaner.scan")


# Define a helper function to execute Google API requests with exponential backoff on rate-limit errors (403/429)
def _execute_with_backoff(request: Any, max_retries: int = 5) -> dict:
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


# Define a helper function to extract the email address from a "From" header string (handles formats like "Display Name <user@host.com>")
def _extract_email(from_header: str) -> str:
    s = from_header.find("<")
    e = from_header.find(">")
    if s != -1 and e != -1:
        return from_header[s + 1 : e].strip().lower()
    return from_header.strip().lower()


# Define a helper function to extract the display name from a "From" header string (returns None if no display name is present)
def _extract_display_name(from_header: str) -> str | None:
    lt = from_header.find("<")
    if lt > 0:
        return from_header[:lt].strip().strip("\"'") or None
    return None


# Define a helper function to perform a batch request for message metadata (From, Subject, Date) for a list of message IDs
def _batch_get_headers(service: Any, message_ids: list[str]) -> dict[str, dict]:
    results: dict[str, dict] = {}
    errors: list[tuple] = []

    def _cb(request_id: str, response: Any, exception: Any) -> None:
        if exception is not None:
            errors.append((request_id, exception))
            return
        headers: dict[str, str] = {}
        for h in response.get("payload", {}).get("headers", []):
            headers[h["name"]] = h["value"]
        results[request_id] = {
            "from": headers.get("From", ""),
            "subject": headers.get("Subject", ""),
            "date": headers.get("Date", ""),
            "snippet": response.get("snippet", ""),
        }

    batch = service.new_batch_http_request(callback=_cb)
    for msg_id in message_ids:
        batch.add(
            service.users()
            .messages()
            .get(
                userId="me",
                id=msg_id,
                format="metadata",
                metadataHeaders=["From", "Subject", "Date"],
            ),
            request_id=msg_id,
        )
    batch.execute()

    if errors:
        log.warning(
            "Batch had %d failed requests out of %d", len(errors), len(message_ids)
        )

    return results


# Define the main scanning function that will be run as a background task.
# It lists unread messages, identifies senders with a high number of unread messages, and emits progress events to the provided queue.
async def run_scan(
    service: Any,
    queue: asyncio.Queue,
    scan_id: str,
    dry_run: bool,
    consecutive_unread_threshold: int,
    max_senders: int,
    store_result_fn: Any,
) -> None:
    loop = asyncio.get_running_loop()
    senders_found: list[dict] = []

    log.info(
        "Scan %s starting (dry_run=%s, threshold=%d unread, max_senders=%d)",
        scan_id,
        dry_run,
        consecutive_unread_threshold,
        max_senders,
    )

    # Define a helper function to run a blocking API call in the default executor and return the result (to avoid blocking the event loop)
    async def api(fn: Any) -> Any:
        return await loop.run_in_executor(None, fn)

    # Define a helper function to emit progress events to the queue
    async def emit(event_type: str, data: dict) -> None:
        await queue.put({"type": event_type, "data": data})

    try:
        # List all unread message IDs (one page at a time)
        log.info("Scan %s: listing unread messages…", scan_id)
        await emit(
            "progress",
            {"phase": "listing_unread", "message": "Fetching unread messages…"},
        )

        MAX_MESSAGES = 20_000

        unread_messages: list[dict] = []
        page_token: str | None = None
        page_num = 0

        while True:
            page_num += 1
            log.info(
                "Scan %s: messages.list page %d (have %d so far)",
                scan_id,
                page_num,
                len(unread_messages),
            )

            pt = page_token  # Capture current value for lambda
            result: dict = await api(
                lambda _pt=pt: service.users()
                .messages()
                .list(
                    userId="me",
                    q="is:unread",
                    maxResults=500,
                    **({"pageToken": _pt} if _pt else {}),
                )
                .execute()
            )

            batch = result.get("messages", [])
            unread_messages.extend(batch)
            page_token = result.get("nextPageToken")

            log.info(
                "Scan %s: page %d returned %d messages (running total: %d)",
                scan_id,
                page_num,
                len(batch),
                len(unread_messages),
            )

            if len(unread_messages) >= MAX_MESSAGES:
                unread_messages = unread_messages[:MAX_MESSAGES]
                log.info(
                    "Scan %s: reached %d-message cap, stopping listing",
                    scan_id,
                    MAX_MESSAGES,
                )
                await emit(
                    "progress",
                    {
                        "phase": "listing_unread",
                        "message": f"Capped at {MAX_MESSAGES:,} messages. Analyzing senders…",
                    },
                )
                break

            if not page_token:
                break  # Emit the final count below

            # Let the user see we're still listing
            await emit(
                "progress",
                {
                    "phase": "listing_unread",
                    "message": f"Fetching messages… ({len(unread_messages):,} so far)",
                },
            )

        total_unread = len(unread_messages)
        log.info("Scan %s: found %d unread messages total", scan_id, total_unread)
        await emit(
            "progress",
            {
                "phase": "listing_unread",
                "total_unread": total_unread,
                "message": f"Found {total_unread:,} unread messages. Analyzing senders…",
            },
        )

        if total_unread == 0:
            log.info("Scan %s: inbox is genuinely empty — nothing to scan", scan_id)

        # Batch-fetch from headers (100 messages per HTTP call) and count unread messages per sender
        sender_map: dict[str, dict] = {}
        batch_size = 100

        for batch_start in range(0, total_unread, batch_size):
            batch_ids = [
                m["id"] for m in unread_messages[batch_start : batch_start + batch_size]
            ]
            batch_end = min(batch_start + batch_size, total_unread)

            log.info(
                "Scan %s: batch %d–%d / %d",
                scan_id,
                batch_start + 1,
                batch_end,
                total_unread,
            )

            await emit(
                "progress",
                {
                    "phase": "analyzing_senders",
                    "current": batch_end,
                    "total": total_unread,
                    "message": f"Analyzing {batch_end:,}/{total_unread:,} messages…",
                },
            )

            # Single HTTP round-trip for up to 100 messages
            batch_headers = await api(
                lambda ids=batch_ids: _batch_get_headers(service, ids)
            )

            for msg_id, headers in batch_headers.items():
                sender_email = _extract_email(headers["from"])
                if not sender_email:
                    continue

                if sender_email not in sender_map:
                    sender_map[sender_email] = {
                        "email": sender_email,
                        "display_name": _extract_display_name(headers["from"]),
                        "snippet": headers["snippet"],
                        "subject": headers["subject"],
                        "date": headers["date"],
                        "unread_count": 0,
                    }
                sender_map[sender_email]["unread_count"] += 1

        log.info(
            "Scan %s: found %d distinct senders among unread messages",
            scan_id,
            len(sender_map),
        )

        # Flag senders above threshold (one API call per sender, but we stop once we reach max_senders)
        await emit(
            "progress",
            {
                "phase": "flagging",
                "message": f"Checking {len(sender_map)} senders against threshold…",
            },
        )

        for sender_email, info in sender_map.items():
            if len(senders_found) >= max_senders:
                log.info(
                    "Scan %s: reached max_senders limit (%d)", scan_id, max_senders
                )
                break

            unread_count = info["unread_count"]
            log.info(
                "Scan %s: sender %r has %d unread (threshold=%d)",
                scan_id,
                sender_email,
                unread_count,
                consecutive_unread_threshold,
            )

            if unread_count < consecutive_unread_threshold:
                continue

            # Get estimated total message count (1 API call, retried on rate limit)
            try:
                total_result = await api(
                    lambda e=sender_email: _execute_with_backoff(
                        service.users()
                        .messages()
                        .list(userId="me", q=f"from:{e}", maxResults=1)
                    )
                )
                total_estimate = total_result.get("resultSizeEstimate", unread_count)
            except Exception as exc:
                log.warning(
                    "Could not fetch total count for %r (%s) — using unread count",
                    sender_email,
                    exc,
                )
                total_estimate = unread_count

            log.info(
                "Scan %s: FLAGGED %r — %d unread, ~%d total",
                scan_id,
                sender_email,
                unread_count,
                total_estimate,
            )

            sender_record = {
                "id": str(uuid.uuid4()),
                "email": sender_email,
                "display_name": info["display_name"],
                "message_count": total_estimate,
                "consecutive_unread_count": unread_count,
                "snippet": info["snippet"],
                "subject": info["subject"],
                "first_message_date": info["date"] or None,
            }
            senders_found.append(sender_record)
            await emit("sender_found", sender_record)

            # Write running state so preview/trash endpoints can find this sender (if the user acts before the scan completes)
            store_result_fn(
                {
                    "scan_id": scan_id,
                    "status": "running",
                    "dry_run": dry_run,
                    "senders": list(senders_found),
                }
            )

        # Scan complete
        log.info("Scan %s complete: %d sender(s) flagged", scan_id, len(senders_found))
        store_result_fn(
            {
                "scan_id": scan_id,
                "status": "complete",
                "dry_run": dry_run,
                "senders": senders_found,
            }
        )
        await emit(
            "complete",
            {
                "scan_id": scan_id,
                "senders_found": len(senders_found),
                "dry_run": dry_run,
            },
        )

    except Exception as exc:
        import traceback

        tb = traceback.format_exc()
        detail = f"{type(exc).__name__}: {exc}" if str(exc) else repr(exc)
        log.error("Scan %s CRASHED:\n%s", scan_id, tb)
        store_result_fn(
            {
                "scan_id": scan_id,
                "status": "error",
                "dry_run": dry_run,
                "senders": senders_found,
                "error": detail,
            }
        )
        await emit("error", {"detail": detail})

    finally:
        await queue.put(None)  # Closes the SSE stream
