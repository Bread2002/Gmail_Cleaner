"""
Scan router — /scan/*

POST /scan/start         → kick off background scan, return scan_id
GET  /scan/{id}/stream   → SSE stream of scan progress (token via query param)
GET  /scan/{id}/results  → polling fallback for completed scan
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Annotated, AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.models.sender import ScanRequest, ScanStartResponse, ScanResult
from app.dependencies import (
    get_session_from_header,
    get_session_from_query,
    get_gmail_service,
)
from app.services import gmail_scan
from app import store

router = APIRouter(prefix="/scan", tags=["scan"])
log = logging.getLogger("gmail_cleaner.routers.scan")


def _session_token(session: dict) -> str:
    from app.store.session import _sessions

    token = next((t for t, s in _sessions.items() if s is session), None)
    if not token:
        raise HTTPException(status_code=500, detail="Session lookup failed")
    return token


@router.post("/start", response_model=ScanStartResponse)
async def start_scan(
    body: ScanRequest,
    session: Annotated[dict, Depends(get_session_from_header)],
    service: Annotated[object, Depends(get_gmail_service)],
) -> ScanStartResponse:
    """Start a background scan. Returns a scan_id to subscribe to the SSE stream."""
    scan_id = str(uuid.uuid4())
    session_token = _session_token(session)

    log.info(
        "Starting scan %s for session …%s (dry_run=%s, threshold=%d, max_senders=%d)",
        scan_id,
        session_token[-6:],
        body.dry_run,
        body.consecutive_unread_threshold,
        body.max_senders,
    )

    queue = store.session.create_queue(session_token, scan_id)

    store.session.store_scan_result(
        session_token,
        scan_id,
        {
            "scan_id": scan_id,
            "status": "running",
            "dry_run": body.dry_run,
            "senders": [],
        },
    )

    def _store_result(result: dict) -> None:
        store.session.store_scan_result(session_token, scan_id, result)

    task = asyncio.create_task(
        gmail_scan.run_scan(
            service=service,
            queue=queue,
            scan_id=scan_id,
            dry_run=body.dry_run,
            consecutive_unread_threshold=body.consecutive_unread_threshold,
            max_senders=body.max_senders,
            max_messages_per_sender=body.max_messages_per_sender,
            store_result_fn=_store_result,
        )
    )

    # Log any unhandled exception that escapes run_scan (shouldn't happen, but safety net)
    def _on_task_done(t: asyncio.Task) -> None:
        if not t.cancelled() and t.exception():
            log.error(
                "Scan task %s died with unhandled exception:",
                scan_id,
                exc_info=t.exception(),
            )

    task.add_done_callback(_on_task_done)

    return ScanStartResponse(scan_id=scan_id)


@router.get("/{scan_id}/stream")
async def scan_stream(
    scan_id: str,
    session: Annotated[dict, Depends(get_session_from_query)],
) -> StreamingResponse:
    """
    SSE stream of scan progress events.
    Token passed as ?token= query param because EventSource doesn't support headers.
    """
    session_token = _session_token(session)
    queue = store.session.get_queue(session_token, scan_id)
    if queue is None:
        raise HTTPException(status_code=404, detail="Scan not found")

    log.info("SSE stream opened for scan %s", scan_id)

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            while True:
                # ── CRITICAL FIX: handle timeout inside the loop ─────────────
                # The outer try/except caused the generator to EXIT on timeout.
                # Now we catch TimeoutError per-iteration and continue looping.
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=60.0)
                except asyncio.TimeoutError:
                    # Send a heartbeat comment so the browser doesn't close the connection
                    log.debug("SSE heartbeat sent for scan %s", scan_id)
                    yield ": heartbeat\n\n"
                    continue

                if event is None:  # sentinel — scan finished
                    log.info(
                        "SSE stream for scan %s received sentinel, closing", scan_id
                    )
                    yield "event: done\ndata: {}\n\n"
                    break

                event_type = event["type"]
                data = json.dumps(event["data"])
                log.debug("SSE → %s: %s", event_type, data[:120])
                yield f"event: {event_type}\ndata: {data}\n\n"

        except asyncio.CancelledError:
            log.info("SSE stream for scan %s cancelled (client disconnected)", scan_id)
        finally:
            store.session.delete_queue(session_token, scan_id)
            log.info("SSE stream for scan %s closed", scan_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/{scan_id}/results", response_model=ScanResult)
async def scan_results(
    scan_id: str,
    session: Annotated[dict, Depends(get_session_from_header)],
) -> ScanResult:
    """Polling fallback: return current scan results."""
    session_token = _session_token(session)
    result = store.session.get_scan_result(session_token, scan_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    log.debug(
        "Returning scan results for %s: status=%s, senders=%d",
        scan_id,
        result.get("status"),
        len(result.get("senders", [])),
    )
    return ScanResult(**result)
