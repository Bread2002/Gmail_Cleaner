# Copyright (c) 2026, Rye Stahle-Smith; All rights reserved.
# Gmail Cleaner
# Last Updated: May 24th, 2026
# Description: Defines API endpoints for managing flagged senders and related actions (preview, delete, block) with authentication via session tokens.

# Import necessary libraries and modules
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Annotated, AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from googleapiclient.discovery import build as build_service

from app.models.sender import (
    PreviewResponse,
    DeleteRequest,
    DeleteStartResponse,
    BlockResponse,
    BulkDeleteRequest,
    BulkDeleteResponse,
    MoveToTrashRequest,
    MoveToTrashStartResponse,
    BulkMoveToTrashRequest,
    BulkMoveToTrashResponse,
    BulkBlockRequest,
    BulkBlockResponse,
    BulkSkipRequest,
    BulkSkipResponse,
)
from app.dependencies import (
    get_session_from_header,
    get_session_from_query,
    get_gmail_service,
)
from app.services import gmail_delete, gmail_move_to_trash, gmail_filter
from app import store

# Define the API router for senders-related endpoints with a prefix and tags for documentation
router = APIRouter(prefix="/senders", tags=["senders"])

# Initialize logging for this module
log = logging.getLogger("gmail_cleaner.routers.senders")


# Define a helper function to look up a flagged sender by ID across all scan results in the session
def _find_sender_in_scan(session: dict, sender_id: str) -> dict | None:
    for result in session.get("scan_results", {}).values():
        for sender in result.get("senders", []):
            if sender.get("id") == sender_id:
                return sender
    return None


# Define a helper function to retrieve the session token from the session dictionary
def _get_session_token(session: dict) -> str:
    return session["_token"]


# Define the POST endpoint to start batch-delete jobs for multiple senders (requires authentication via session token)
@router.post("/bulk/delete", response_model=BulkDeleteResponse)
async def bulk_delete(
    body: BulkDeleteRequest,
    session: Annotated[dict, Depends(get_session_from_header)],
) -> BulkDeleteResponse:
    """Start batch-delete jobs for multiple senders (requires authentication via session token)."""
    session_token = _get_session_token(session)
    credentials = session["credentials"]
    jobs = []

    for sender_id in body.sender_ids:
        sender = _find_sender_in_scan(session, sender_id)
        if sender is None:
            continue

        job_id = str(uuid.uuid4())
        sender_email = sender["email"]
        queue = store.session.create_queue(session_token, job_id)

        # Build a dedicated service per task — httplib2.Http is not thread-safe
        # and sharing one service across concurrent tasks corrupts responses.
        task_service = build_service("gmail", "v1", credentials=credentials)

        asyncio.create_task(
            gmail_delete.run_delete(
                service=task_service,
                queue=queue,
                sender_email=sender_email,
                dry_run=body.dry_run,
                store_result_fn=lambda r, jid=job_id: store.session.store_scan_result(
                    session_token, f"delete_{jid}", r
                ),
            )
        )
        jobs.append({"sender_id": sender_id, "job_id": job_id})

    return BulkDeleteResponse(jobs=jobs)


# Define the POST endpoint to start batch-block jobs for multiple senders (requires authentication via session token)
@router.post("/bulk/block", response_model=BulkBlockResponse)
async def bulk_block(
    body: BulkBlockRequest,
    session: Annotated[dict, Depends(get_session_from_header)],
    service: Annotated[object, Depends(get_gmail_service)],
) -> BulkBlockResponse:
    """Start batch-block jobs for multiple senders (requires authentication via session token)."""
    blocked = []
    failed = []

    for sender_id in body.sender_ids:
        sender = _find_sender_in_scan(session, sender_id)
        if sender is None:
            failed.append(sender_id)
            continue

        sender_email = sender["email"]
        try:
            await gmail_filter.create_block_filter(service, sender_email)
            blocked.append(sender_email)
        except Exception:
            failed.append(sender_email)

    return BulkBlockResponse(blocked=blocked, failed=failed)


# Define the POST endpoint to acknowledge bulk-skip actions for multiple senders (requires authentication via session token)
@router.post("/bulk/skip", response_model=BulkSkipResponse)
async def bulk_skip(
    body: BulkSkipRequest,
    session: Annotated[dict, Depends(get_session_from_header)],
) -> BulkSkipResponse:
    """Acknowledge bulk-skip actions for multiple senders (requires authentication via session token)."""
    skipped = []
    failed = []

    for sender_id in body.sender_ids:
        if _find_sender_in_scan(session, sender_id) is not None:
            skipped.append(sender_id)
        else:
            failed.append(sender_id)

    return BulkSkipResponse(skipped=skipped, failed=failed)


# Define the POST endpoint to start batch-move-to-trash jobs for multiple senders (requires authentication via session token)
@router.post("/bulk/move-to-trash", response_model=BulkMoveToTrashResponse)
async def bulk_move_to_trash(
    body: BulkMoveToTrashRequest,
    session: Annotated[dict, Depends(get_session_from_header)],
) -> BulkMoveToTrashResponse:
    """Start batch-move-to-trash jobs for multiple senders (recoverable for 30 days via Gmail)."""
    session_token = _get_session_token(session)
    credentials = session["credentials"]
    jobs = []

    for sender_id in body.sender_ids:
        sender = _find_sender_in_scan(session, sender_id)
        if sender is None:
            continue

        job_id = str(uuid.uuid4())
        sender_email = sender["email"]
        queue = store.session.create_queue(session_token, job_id)

        task_service = build_service("gmail", "v1", credentials=credentials)

        asyncio.create_task(
            gmail_move_to_trash.run_move_to_trash(
                service=task_service,
                queue=queue,
                sender_email=sender_email,
                dry_run=body.dry_run,
                store_result_fn=lambda r, jid=job_id: store.session.store_scan_result(
                    session_token, f"move_to_trash_{jid}", r
                ),
            )
        )
        jobs.append({"sender_id": sender_id, "job_id": job_id})

    return BulkMoveToTrashResponse(jobs=jobs)


# Define the GET endpoint to retrieve a preview of the sender's most recent message (requires authentication via session token)
@router.get("/{sender_id}/preview", response_model=PreviewResponse)
async def get_preview(
    sender_id: str,
    session: Annotated[dict, Depends(get_session_from_header)],
    service: Annotated[object, Depends(get_gmail_service)],
) -> PreviewResponse:
    """Retrieve a preview of the sender's most recent message (requires authentication via session token)."""
    sender = _find_sender_in_scan(session, sender_id)
    if sender is None:
        raise HTTPException(status_code=404, detail="Sender not found")

    loop = asyncio.get_running_loop()
    sender_email = sender["email"]
    log.info("Fetching preview for sender %r", sender_email)

    # Fetch the most recent message from this sender
    result = await loop.run_in_executor(
        None,
        lambda: service.users()
        .messages()
        .list(userId="me", q=f"from:{sender_email}", maxResults=1)
        .execute(),
    )
    messages = result.get("messages", [])
    if not messages:
        return PreviewResponse(
            sender_id=sender_id,
            email=sender_email,
            snippet=sender.get("snippet"),
            subject=sender.get("subject"),
        )

    msg_id = messages[0]["id"]
    msg_info = await loop.run_in_executor(
        None,
        lambda: service.users()
        .messages()
        .get(
            userId="me",
            id=msg_id,
            format="metadata",
            metadataHeaders=["Subject", "Date"],
        )
        .execute(),
    )

    subject = None
    date_str = None
    for header in msg_info.get("payload", {}).get("headers", []):
        if header["name"] == "Subject":
            subject = header["value"]
        elif header["name"] == "Date":
            date_str = header["value"]

    date_parsed = None
    if date_str:
        try:
            from email.utils import parsedate_to_datetime

            date_parsed = parsedate_to_datetime(date_str)
        except Exception:
            pass

    return PreviewResponse(
        sender_id=sender_id,
        email=sender_email,
        subject=subject or sender.get("subject"),
        snippet=msg_info.get("snippet") or sender.get("snippet"),
        date=date_parsed,
    )


# Define the POST endpoint to start a batch-delete job for all messages from a specific sender (requires authentication via session token)
@router.post("/{sender_id}/delete", response_model=DeleteStartResponse)
async def start_delete(
    sender_id: str,
    body: DeleteRequest,
    session: Annotated[dict, Depends(get_session_from_header)],
    service: Annotated[object, Depends(get_gmail_service)],
) -> DeleteStartResponse:
    """Start a batch-delete job for all messages from a specific sender (requires authentication via session token)."""
    sender = _find_sender_in_scan(session, sender_id)
    if sender is None:
        raise HTTPException(status_code=404, detail="Sender not found")

    session_token = _get_session_token(session)
    job_id = str(uuid.uuid4())
    sender_email = sender["email"]
    estimated_count = sender.get("message_count", 0)

    queue = store.session.create_queue(session_token, job_id)

    delete_results: dict = {}

    def _store_result(result: dict) -> None:
        delete_results.update(result)
        store.session.store_scan_result(session_token, f"delete_{job_id}", result)

    asyncio.create_task(
        gmail_delete.run_delete(
            service=service,
            queue=queue,
            sender_email=sender_email,
            dry_run=body.dry_run,
            store_result_fn=_store_result,
        )
    )

    return DeleteStartResponse(
        job_id=job_id, sender=sender_email, estimated_count=estimated_count
    )


# Define the GET endpoint to retrieve a stream of progress updates for a batch-delete job (requires authentication via session token)
@router.get("/{sender_id}/delete/{job_id}/stream")
async def delete_stream(
    sender_id: str,
    job_id: str,
    session: Annotated[dict, Depends(get_session_from_query)],
) -> StreamingResponse:
    """Stream progress updates for a batch-delete job via Server-Sent Events (SSE) (requires authentication via session token)."""
    session_token = _get_session_token(session)
    queue = store.session.get_queue(session_token, job_id)
    if queue is None:
        raise HTTPException(status_code=404, detail="Delete job not found")

    log.info("SSE delete stream opened for job %s", job_id)

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            while True:
                # CRITICAL FIX: catch TimeoutError per-iteration so we keep looping
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=60.0)
                except asyncio.TimeoutError:
                    log.debug("SSE delete heartbeat for job %s", job_id)
                    yield ": heartbeat\n\n"
                    continue

                if event is None:
                    log.info("SSE delete stream for job %s complete", job_id)
                    yield "event: done\ndata: {}\n\n"
                    break

                event_type = event["type"]
                data = json.dumps(event["data"])
                log.debug("SSE delete → %s: %s", event_type, data[:120])
                yield f"event: {event_type}\ndata: {data}\n\n"

        except asyncio.CancelledError:
            log.info("SSE delete stream for job %s cancelled", job_id)
        finally:
            store.session.delete_queue(session_token, job_id)
            log.info("SSE delete stream for job %s closed", job_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# Define the POST endpoint to start a move-to-trash job for all messages from a specific sender (requires authentication via session token)
@router.post("/{sender_id}/move-to-trash", response_model=MoveToTrashStartResponse)
async def start_move_to_trash(
    sender_id: str,
    body: MoveToTrashRequest,
    session: Annotated[dict, Depends(get_session_from_header)],
    service: Annotated[object, Depends(get_gmail_service)],
) -> MoveToTrashStartResponse:
    """Start a move-to-trash job for all messages from a specific sender (recoverable for 30 days via Gmail)."""
    sender = _find_sender_in_scan(session, sender_id)
    if sender is None:
        raise HTTPException(status_code=404, detail="Sender not found")

    session_token = _get_session_token(session)
    job_id = str(uuid.uuid4())
    sender_email = sender["email"]
    estimated_count = sender.get("message_count", 0)

    queue = store.session.create_queue(session_token, job_id)

    move_results: dict = {}

    def _store_result(result: dict) -> None:
        move_results.update(result)
        store.session.store_scan_result(
            session_token, f"move_to_trash_{job_id}", result
        )

    asyncio.create_task(
        gmail_move_to_trash.run_move_to_trash(
            service=service,
            queue=queue,
            sender_email=sender_email,
            dry_run=body.dry_run,
            store_result_fn=_store_result,
        )
    )

    return MoveToTrashStartResponse(
        job_id=job_id, sender=sender_email, estimated_count=estimated_count
    )


# Define the GET endpoint to retrieve a stream of progress updates for a move-to-trash job (requires authentication via session token)
@router.get("/{sender_id}/move-to-trash/{job_id}/stream")
async def move_to_trash_stream(
    sender_id: str,
    job_id: str,
    session: Annotated[dict, Depends(get_session_from_query)],
) -> StreamingResponse:
    """Stream progress updates for a move-to-trash job via Server-Sent Events (SSE)."""
    session_token = _get_session_token(session)
    queue = store.session.get_queue(session_token, job_id)
    if queue is None:
        raise HTTPException(status_code=404, detail="Move-to-trash job not found")

    log.info("SSE move-to-trash stream opened for job %s", job_id)

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=60.0)
                except asyncio.TimeoutError:
                    log.debug("SSE move-to-trash heartbeat for job %s", job_id)
                    yield ": heartbeat\n\n"
                    continue

                if event is None:
                    log.info("SSE move-to-trash stream for job %s complete", job_id)
                    yield "event: done\ndata: {}\n\n"
                    break

                event_type = event["type"]
                data = json.dumps(event["data"])
                log.debug("SSE move-to-trash → %s: %s", event_type, data[:120])
                yield f"event: {event_type}\ndata: {data}\n\n"

        except asyncio.CancelledError:
            log.info("SSE move-to-trash stream for job %s cancelled", job_id)
        finally:
            store.session.delete_queue(session_token, job_id)
            log.info("SSE move-to-trash stream for job %s closed", job_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# Define the POST endpoint to create a Gmail filter to block future emails from a specific sender (requires authentication via session token)
@router.post("/{sender_id}/block", response_model=BlockResponse)
async def block_sender(
    sender_id: str,
    session: Annotated[dict, Depends(get_session_from_header)],
    service: Annotated[object, Depends(get_gmail_service)],
) -> BlockResponse:
    """Create a Gmail filter to block future emails from a specific sender (requires authentication via session token)."""
    sender = _find_sender_in_scan(session, sender_id)
    if sender is None:
        raise HTTPException(status_code=404, detail="Sender not found")

    sender_email = sender["email"]
    filter_id = await gmail_filter.create_block_filter(service, sender_email)
    return BlockResponse(filter_id=filter_id, sender=sender_email)
