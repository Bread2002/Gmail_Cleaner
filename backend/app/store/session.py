# Copyright (c) 2026, Rye Stahle-Smith; All rights reserved.
# Gmail Cleaner
# Last Updated: May 28th, 2026
# Description: Session store for the Gmail Cleaner backend.
#              When USE_REDIS=true (default), durable session data lives in Redis.
#              When USE_REDIS=false, a simple in-memory dict is used instead (local dev only).
#              Process-local data (queues, scan results) always stays in-memory regardless.

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

import redis.asyncio as aioredis
from google.oauth2.credentials import Credentials

from app.config import settings

log = logging.getLogger("gmail_cleaner.session")

# In-memory storage for process-local volatile data (queues and scan results).
# These cannot be serialized to Redis and are only needed within a single process.
_volatile: dict[str, dict[str, Any]] = {}

# Redis client (initialized lazily via _get_redis, only used when settings.use_redis is True)
_redis: aioredis.Redis | None = None

# In-memory fallback storage (used when settings.use_redis is False)
_mem_sessions: dict[str, dict[str, Any]] = {}
_mem_states: dict[str, dict[str, Any]] = {}


def _get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


def _session_key(token: str) -> str:
    return f"session:{token}"


def _state_key(state: str) -> str:
    return f"state:{state}"


async def create_session(
    session_token: str, credentials: Credentials, user_email: str, expires_at: datetime
) -> None:
    data = {
        "credentials_json": credentials.to_json(),
        "user_email": user_email,
        "expires_at": expires_at.isoformat(),
        "settings": {
            "consecutive_unread_threshold": 20,
            "max_senders": 10,
            "max_messages_per_sender": 100,
            "dry_run_by_default": False,
        },
    }
    _volatile[session_token] = {"scan_results": {}, "queues": {}}
    if settings.use_redis:
        await _get_redis().set(
            _session_key(session_token),
            json.dumps(data),
            ex=settings.session_ttl_seconds,
        )
    else:
        _mem_sessions[session_token] = data


async def get_session(session_token: str) -> dict[str, Any] | None:
    if settings.use_redis:
        raw = await _get_redis().get(_session_key(session_token))
    else:
        entry = _mem_sessions.get(session_token)
        raw = json.dumps(entry) if entry is not None else None

    if raw is None:
        return None

    data = json.loads(raw)
    expires_at = datetime.fromisoformat(data["expires_at"])
    if expires_at < datetime.now(timezone.utc):
        await delete_session(session_token)
        return None

    volatile = _volatile.setdefault(session_token, {"scan_results": {}, "queues": {}})

    return {
        "_token": session_token,
        "credentials": Credentials.from_authorized_user_info(json.loads(data["credentials_json"])),
        "user_email": data["user_email"],
        "expires_at": expires_at,
        "settings": data["settings"],
        "scan_results": volatile["scan_results"],
        "queues": volatile["queues"],
    }


async def delete_session(session_token: str) -> None:
    if settings.use_redis:
        await _get_redis().delete(_session_key(session_token))
    else:
        _mem_sessions.pop(session_token, None)
    _volatile.pop(session_token, None)


async def update_credentials(session_token: str, credentials: Credentials) -> None:
    if settings.use_redis:
        key = _session_key(session_token)
        raw = await _get_redis().get(key)
        if raw is None:
            return
        data = json.loads(raw)
        data["credentials_json"] = credentials.to_json()
        await _get_redis().set(key, json.dumps(data), keepttl=True)
    else:
        if session_token not in _mem_sessions:
            return
        _mem_sessions[session_token]["credentials_json"] = credentials.to_json()


async def get_settings(session_token: str) -> dict[str, Any]:
    if settings.use_redis:
        raw = await _get_redis().get(_session_key(session_token))
        if raw is None:
            return {}
        return json.loads(raw)["settings"].copy()
    else:
        entry = _mem_sessions.get(session_token)
        if entry is None:
            return {}
        return entry["settings"].copy()


async def update_settings(session_token: str, patch: dict[str, Any]) -> dict[str, Any]:
    if settings.use_redis:
        key = _session_key(session_token)
        raw = await _get_redis().get(key)
        if raw is None:
            return {}
        data = json.loads(raw)
        data["settings"].update(patch)
        await _get_redis().set(key, json.dumps(data), keepttl=True)
        return data["settings"].copy()
    else:
        entry = _mem_sessions.get(session_token)
        if entry is None:
            return {}
        entry["settings"].update(patch)
        return entry["settings"].copy()


# Scan results — in-memory (process-local, ephemeral)

def get_scan_result(session_token: str, scan_id: str) -> dict[str, Any] | None:
    volatile = _volatile.get(session_token)
    if volatile is None:
        return None
    return volatile["scan_results"].get(scan_id)


def store_scan_result(session_token: str, scan_id: str, result: dict[str, Any]) -> None:
    _volatile.setdefault(session_token, {"scan_results": {}, "queues": {}})["scan_results"][scan_id] = result


# Queues — in-memory (asyncio.Queue objects, process-local)

def create_queue(session_token: str, queue_id: str) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue()
    _volatile.setdefault(session_token, {"scan_results": {}, "queues": {}})["queues"][queue_id] = q
    return q


def get_queue(session_token: str, queue_id: str) -> asyncio.Queue | None:
    volatile = _volatile.get(session_token)
    if volatile is None:
        return None
    return volatile["queues"].get(queue_id)


def delete_queue(session_token: str, queue_id: str) -> None:
    volatile = _volatile.get(session_token)
    if volatile:
        volatile["queues"].pop(queue_id, None)


# OAuth pending state — Redis with TTL, or in-memory with manual expiry check
# The PKCE code_verifier (if used) is stored alongside the state so it can be
# restored when the flow is reconstructed during the callback.

async def store_state(
    state: str, flow: Any, expiry: datetime, *, code_verifier: str | None = None
) -> None:
    ttl = int((expiry - datetime.now(timezone.utc)).total_seconds())
    if ttl <= 0:
        return
    if code_verifier is None:
        code_verifier = getattr(flow.oauth2session, "_code_verifier", None)
    log.debug("store_state: code_verifier present=%s", code_verifier is not None)
    value = json.dumps({
        "code_verifier": code_verifier,
        "code_challenge_method": "S256" if code_verifier else None,
    })
    if settings.use_redis:
        await _get_redis().set(_state_key(state), value, ex=ttl)
    else:
        _mem_states[state] = {"value": value, "expires_at": expiry}


async def pop_state(state: str) -> Any | None:
    if settings.use_redis:
        raw = await _get_redis().get(_state_key(state))
        if raw is None:
            return None
        await _get_redis().delete(_state_key(state))
    else:
        entry = _mem_states.pop(state, None)
        if entry is None:
            return None
        if entry["expires_at"] < datetime.now(timezone.utc):
            return None
        raw = entry["value"]

    data = json.loads(raw)

    from google_auth_oauthlib.flow import Flow
    from app.config import settings as app_settings
    flow = Flow.from_client_config(
        app_settings.google_auth_config,
        scopes=app_settings.gmail_scopes,
        redirect_uri=app_settings.google_redirect_uri,
    )
    code_verifier = data.get("code_verifier")
    if code_verifier:
        flow.oauth2session._code_verifier = code_verifier
        flow._stored_code_verifier = code_verifier
    if data.get("code_challenge_method"):
        flow.oauth2session.code_challenge_method = data["code_challenge_method"]
    return flow
