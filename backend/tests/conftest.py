# Copyright (c) 2026, Rye Stahle-Smith; All rights reserved.
# Gmail Cleaner
# Last Updated: May 28th, 2026
# Description: Sets required environment variables for tests before any app modules are imported and defines pytest fixtures for use in tests
#              Tests use httpx + FastAPI's test client (no real Gmail or Google OAuth calls).
# Note: You must run the following command within the Python virtual environment to install development dependencies:
#       pip install -e ".[dev]"

# Import necessary libraries and modules
import json
import os
import uuid

import fakeredis
import pytest
from httpx import ASGITransport, AsyncClient

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from app.main import app
from app.store import session as session_store

# Set default environment variables for testing
os.environ.setdefault("GOOGLE_CLIENT_ID", "test-client-id")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test-client-secret")
os.environ.setdefault("GOOGLE_PROJECT_ID", "test-project-id")


# Define a helper to build a mock Credentials object whose to_json() returns valid JSON
def _mock_credentials() -> MagicMock:
    creds = MagicMock()
    creds.to_json.return_value = json.dumps({
        "token": "test-access-token",
        "refresh_token": "test-refresh-token",
        "client_id": "test-client-id",
        "client_secret": "test-client-secret",
        "token_uri": "https://oauth2.googleapis.com/token",
        "scopes": [],
        "expiry": "2099-12-31T23:59:59Z",
    })
    creds.expired = False
    creds.token = "test-access-token"
    creds.refresh_token = "test-refresh-token"
    return creds


# Define a pytest fixture to inject a fresh fakeredis instance and clear volatile state before/after each test
@pytest.fixture(autouse=True)
async def clean_sessions():
    session_store._redis = fakeredis.FakeAsyncRedis()
    session_store._volatile.clear()
    yield
    session_store._volatile.clear()
    session_store._redis = None


# Define a pytest fixture to provide a valid session token (for tests that require authentication)
@pytest.fixture
async def session_token():
    token = str(uuid.uuid4())
    await session_store.create_session(
        token,
        _mock_credentials(),
        "test@gmail.com",
        datetime.now(timezone.utc) + timedelta(hours=1),
    )
    return token


# Define a pytest fixture that sets up a session with one flagged sender (for tests that need pre-seeded sender data)
@pytest.fixture
async def session_with_sender():
    token = str(uuid.uuid4())
    await session_store.create_session(
        token,
        _mock_credentials(),
        "test@gmail.com",
        datetime.now(timezone.utc) + timedelta(hours=1),
    )
    sender_id = str(uuid.uuid4())
    scan_id = str(uuid.uuid4())
    sender_email = "spam@bulk.com"
    session_store.store_scan_result(
        token,
        scan_id,
        {
            "scan_id": scan_id,
            "status": "complete",
            "dry_run": False,
            "senders": [
                {
                    "id": sender_id,
                    "email": sender_email,
                    "display_name": "Bulk Sender",
                    "message_count": 50,
                    "consecutive_unread_count": 35,
                    "snippet": "Click here",
                    "subject": "Weekly Ad",
                    "first_message_date": None,
                }
            ],
        },
    )
    return token, sender_id, sender_email


# Define a pytest fixture that provides an async httpx client
@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
