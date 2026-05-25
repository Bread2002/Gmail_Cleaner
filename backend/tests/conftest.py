# Copyright (c) 2026, Rye Stahle-Smith; All rights reserved.
# Gmail Cleaner
# Last Updated: May 24th, 2026
# Description: Sets required environment variables for tests before any app modules are imported and defines pytest fixtures for use in tests
#              Tests use httpx + FastAPI's test client (no real Gmail or Google OAuth calls).
# Note: You must run the following command within the Python virtual environment to install development dependencies:
#       pip install -e ".[dev]"

# Import necessary libraries and modules
import os
import uuid

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


# Define a pytest fixture to clean the session storage before and after each test (ensures test isolation)
@pytest.fixture(autouse=True)
def clean_sessions():
    session_store._sessions.clear()
    session_store._pending_states.clear()
    yield
    session_store._sessions.clear()
    session_store._pending_states.clear()


# Define a pytest fixture to provide a valid session token (for tests that require authentication)
@pytest.fixture
def session_token():
    token = str(uuid.uuid4())
    session_store.create_session(
        token,
        MagicMock(),
        "test@gmail.com",
        datetime.now(timezone.utc) + timedelta(hours=1),
    )
    return token


# Define a pytest fixture that sets up a session with one flagged sender (for tests that need pre-seeded sender data)
@pytest.fixture
def session_with_sender():
    token = str(uuid.uuid4())
    session_store.create_session(
        token,
        MagicMock(),
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
