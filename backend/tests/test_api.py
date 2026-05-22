"""
Unit & integration tests for the Gmail Cleaner backend API.
Uses httpx + FastAPI's test client — no real Gmail or Google OAuth calls.

Run:  pytest                     (spec output via addopts = --spec in pyproject.toml)
      pytest -k TestBulkSkip     (single class)
"""

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.store import session as session_store

# ── helpers ───────────────────────────────────────────────────────────────────


def _make_session(settings_override: dict | None = None) -> tuple[str, dict]:
    """Insert a fake session and return (token, session_dict)."""
    token = str(uuid.uuid4())
    creds = MagicMock()
    creds.expired = False
    creds.refresh_token = "fake-refresh-token"
    creds.token = "fake-access-token"
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    session_store.create_session(token, creds, "test@gmail.com", expires_at)
    if settings_override:
        session_store.update_settings(token, settings_override)
    return token, session_store.get_session(token)


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def clean_sessions():
    session_store._sessions.clear()
    session_store._pending_states.clear()
    yield
    session_store._sessions.clear()
    session_store._pending_states.clear()


@pytest.fixture
def session_token():
    token, _ = _make_session()
    return token


@pytest.fixture
def session_with_sender():
    """Session pre-seeded with one flagged sender. Returns (token, sender_id, sender_email)."""
    token, _ = _make_session()
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


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


# ═══════════════════════════════════════════════════════════════════════════════
# GET /health
# ═══════════════════════════════════════════════════════════════════════════════


class TestHealth:

    async def test_returns_200_with_ok_status(self, client):
        r = await client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}


# ═══════════════════════════════════════════════════════════════════════════════
# GET /auth/login
# ═══════════════════════════════════════════════════════════════════════════════


class TestAuthLogin:

    async def test_returns_google_oauth_url(self, client):
        with patch("app.services.gmail_auth.Flow") as MockFlow:
            instance = MagicMock()
            instance.authorization_url.return_value = (
                "https://accounts.google.com/o/oauth2/auth?fake",
                "state123",
            )
            MockFlow.from_client_config.return_value = instance
            r = await client.get("/auth/login")

        assert r.status_code == 200
        assert r.json()["auth_url"].startswith("https://")


# ═══════════════════════════════════════════════════════════════════════════════
# GET /auth/me
# ═══════════════════════════════════════════════════════════════════════════════


class TestAuthMe:

    async def test_returns_email_and_authenticated_true_with_valid_token(
        self, client, session_token
    ):
        r = await client.get("/auth/me", headers=_auth(session_token))
        assert r.status_code == 200
        assert r.json()["email"] == "test@gmail.com"
        assert r.json()["authenticated"] is True

    async def test_returns_401_when_no_authorization_header_present(self, client):
        r = await client.get("/auth/me")
        assert r.status_code == 401

    async def test_returns_401_for_unrecognised_token(self, client):
        r = await client.get("/auth/me", headers=_auth("not-a-real-token"))
        assert r.status_code == 401

    async def test_returns_401_for_expired_session(self, client):
        token = str(uuid.uuid4())
        expired_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        session_store.create_session(token, MagicMock(), "old@gmail.com", expired_at)

        r = await client.get("/auth/me", headers=_auth(token))
        assert r.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# POST /auth/logout
# ═══════════════════════════════════════════════════════════════════════════════


class TestAuthLogout:

    async def test_session_is_rejected_after_logout(self, client, session_token):
        assert (
            await client.get("/auth/me", headers=_auth(session_token))
        ).status_code == 200

        r = await client.post("/auth/logout", headers=_auth(session_token))
        assert r.status_code == 204

        assert (
            await client.get("/auth/me", headers=_auth(session_token))
        ).status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# POST /scan/start
# ═══════════════════════════════════════════════════════════════════════════════


class TestScanStart:

    async def test_returns_valid_uuid_scan_id(self, client, session_token):
        with patch(
            "app.routers.scan.gmail_scan.run_scan", new_callable=AsyncMock
        ), patch("app.dependencies.build", return_value=MagicMock()):
            r = await client.post(
                "/scan/start",
                headers=_auth(session_token),
                json={
                    "dry_run": True,
                    "consecutive_unread_threshold": 20,
                    "max_senders": 10,
                    "max_messages_per_sender": 100,
                },
            )

        assert r.status_code == 200
        uuid.UUID(r.json()["scan_id"])  # raises if not a valid UUID

    async def test_returns_401_without_auth(self, client):
        r = await client.post("/scan/start", json={"dry_run": False})
        assert r.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# GET /scan/{scan_id}/results
# ═══════════════════════════════════════════════════════════════════════════════


class TestScanResults:

    async def test_returns_404_for_unknown_scan_id(self, client, session_token):
        r = await client.get(
            f"/scan/{uuid.uuid4()}/results", headers=_auth(session_token)
        )
        assert r.status_code == 404

    async def test_returns_stored_result(self, client, session_token):
        scan_id = str(uuid.uuid4())
        session_store.store_scan_result(
            session_token,
            scan_id,
            {"scan_id": scan_id, "status": "complete", "dry_run": False, "senders": []},
        )

        r = await client.get(f"/scan/{scan_id}/results", headers=_auth(session_token))
        assert r.status_code == 200
        assert r.json()["status"] == "complete"

    async def test_includes_full_sender_objects_in_senders_list(
        self, client, session_token
    ):
        scan_id = str(uuid.uuid4())
        sender_id = str(uuid.uuid4())
        session_store.store_scan_result(
            session_token,
            scan_id,
            {
                "scan_id": scan_id,
                "status": "complete",
                "dry_run": False,
                "senders": [
                    {
                        "id": sender_id,
                        "email": "spam@newsletter.com",
                        "display_name": "Newsletter",
                        "message_count": 42,
                        "consecutive_unread_count": 30,
                        "snippet": "Unsubscribe",
                        "subject": "Weekly Digest",
                        "first_message_date": None,
                    }
                ],
            },
        )

        r = await client.get(f"/scan/{scan_id}/results", headers=_auth(session_token))
        senders = r.json()["senders"]
        assert len(senders) == 1
        assert senders[0]["email"] == "spam@newsletter.com"
        assert senders[0]["consecutive_unread_count"] == 30


# ═══════════════════════════════════════════════════════════════════════════════
# GET + PATCH /settings
# ═══════════════════════════════════════════════════════════════════════════════


class TestSettings:

    async def test_get_returns_all_default_keys(self, client, session_token):
        r = await client.get("/settings", headers=_auth(session_token))
        assert r.status_code == 200
        for key in (
            "consecutive_unread_threshold",
            "max_senders",
            "max_messages_per_sender",
            "dry_run_by_default",
        ):
            assert key in r.json()

    async def test_patch_updates_specified_keys_and_preserves_others(
        self, client, session_token
    ):
        r = await client.patch(
            "/settings",
            headers=_auth(session_token),
            json={"consecutive_unread_threshold": 50, "max_senders": 25},
        )
        assert r.status_code == 200
        assert r.json()["consecutive_unread_threshold"] == 50
        assert r.json()["max_senders"] == 25

    async def test_get_returns_401_without_auth(self, client):
        assert (await client.get("/settings")).status_code == 401

    async def test_patch_returns_401_without_auth(self, client):
        assert (
            await client.patch("/settings", json={"max_senders": 5})
        ).status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# GET /senders/{id}/preview
# ═══════════════════════════════════════════════════════════════════════════════


class TestSenderPreview:

    async def test_returns_404_when_sender_not_in_session(self, client, session_token):
        with patch("app.dependencies.build", return_value=MagicMock()):
            r = await client.get(
                f"/senders/{uuid.uuid4()}/preview", headers=_auth(session_token)
            )
        assert r.status_code == 404

    async def test_returns_subject_snippet_and_email_from_gmail_message(
        self, client, session_with_sender
    ):
        token, sender_id, sender_email = session_with_sender
        svc = MagicMock()
        svc.users.return_value.messages.return_value.list.return_value.execute.return_value = {
            "messages": [{"id": "msg-abc"}]
        }
        svc.users.return_value.messages.return_value.get.return_value.execute.return_value = {
            "snippet": "Great deals inside!",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Weekly Newsletter"},
                    {"name": "Date", "value": "Thu, 01 May 2025 10:00:00 +0000"},
                ]
            },
        }

        with patch("app.dependencies.build", return_value=svc):
            r = await client.get(f"/senders/{sender_id}/preview", headers=_auth(token))

        assert r.status_code == 200
        body = r.json()
        assert body["subject"] == "Weekly Newsletter"
        assert body["snippet"] == "Great deals inside!"
        assert body["email"] == sender_email

    async def test_falls_back_to_session_data_when_gmail_has_no_messages(
        self, client, session_with_sender
    ):
        token, sender_id, sender_email = session_with_sender
        svc = MagicMock()
        svc.users.return_value.messages.return_value.list.return_value.execute.return_value = {
            "messages": []
        }

        with patch("app.dependencies.build", return_value=svc):
            r = await client.get(f"/senders/{sender_id}/preview", headers=_auth(token))

        assert r.status_code == 200
        body = r.json()
        assert body["email"] == sender_email
        # Falls back to values seeded in the fixture
        assert body["subject"] == "Weekly Ad"
        assert body["snippet"] == "Click here"


# ═══════════════════════════════════════════════════════════════════════════════
# POST /senders/{id}/trash  (individual)
# ═══════════════════════════════════════════════════════════════════════════════


class TestSenderTrash:

    async def test_returns_404_when_sender_not_in_session(self, client, session_token):
        with patch("app.dependencies.build", return_value=MagicMock()):
            r = await client.post(
                f"/senders/{uuid.uuid4()}/trash",
                headers=_auth(session_token),
                json={"dry_run": True},
            )
        assert r.status_code == 404

    async def test_returns_job_id_sender_email_and_estimated_count(
        self, client, session_with_sender
    ):
        token, sender_id, sender_email = session_with_sender

        with patch("app.dependencies.build", return_value=MagicMock()), patch(
            "app.services.gmail_trash.run_trash", new_callable=AsyncMock
        ):
            r = await client.post(
                f"/senders/{sender_id}/trash",
                headers=_auth(token),
                json={"dry_run": False},
            )

        assert r.status_code == 200
        body = r.json()
        uuid.UUID(body["job_id"])
        assert body["sender"] == sender_email
        assert body["estimated_count"] == 50  # matches fixture message_count


# ═══════════════════════════════════════════════════════════════════════════════
# POST /senders/{id}/block  (individual)
# ═══════════════════════════════════════════════════════════════════════════════


class TestSenderBlock:

    async def test_returns_404_when_sender_not_in_session(self, client, session_token):
        with patch("app.dependencies.build", return_value=MagicMock()):
            r = await client.post(
                f"/senders/{uuid.uuid4()}/block", headers=_auth(session_token)
            )
        assert r.status_code == 404

    async def test_returns_filter_id_and_sender_email_on_success(
        self, client, session_with_sender
    ):
        token, sender_id, sender_email = session_with_sender

        with patch("app.dependencies.build", return_value=MagicMock()), patch(
            "app.services.gmail_filter.create_block_filter",
            new_callable=AsyncMock,
            return_value="filter-abc",
        ):
            r = await client.post(f"/senders/{sender_id}/block", headers=_auth(token))

        assert r.status_code == 200
        assert r.json()["filter_id"] == "filter-abc"
        assert r.json()["sender"] == sender_email

    async def test_returns_401_without_auth(self, client):
        r = await client.post(f"/senders/{uuid.uuid4()}/block")
        assert r.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# POST /senders/bulk/trash
# ═══════════════════════════════════════════════════════════════════════════════


class TestBulkTrash:
    # bulk_trash now calls build_service() directly (one service per task) rather
    # than receiving a shared service via dependency injection, so we patch
    # app.routers.senders.build_service instead of app.dependencies.build.

    async def test_returns_401_without_auth(self, client):
        r = await client.post(
            "/senders/bulk/trash", json={"sender_ids": [], "dry_run": False}
        )
        assert r.status_code == 401

    async def test_returns_one_job_entry_per_known_sender(
        self, client, session_with_sender
    ):
        token, sender_id, _ = session_with_sender

        with patch(
            "app.routers.senders.build_service", return_value=MagicMock()
        ), patch("app.services.gmail_trash.run_trash", new_callable=AsyncMock):
            r = await client.post(
                "/senders/bulk/trash",
                headers=_auth(token),
                json={"sender_ids": [sender_id], "dry_run": False},
            )

        assert r.status_code == 200
        jobs = r.json()["jobs"]
        assert len(jobs) == 1
        assert jobs[0]["sender_id"] == sender_id
        uuid.UUID(jobs[0]["job_id"])

    async def test_silently_omits_unknown_sender_ids_from_jobs(
        self, client, session_with_sender
    ):
        token, sender_id, _ = session_with_sender
        unknown = str(uuid.uuid4())

        with patch(
            "app.routers.senders.build_service", return_value=MagicMock()
        ), patch("app.services.gmail_trash.run_trash", new_callable=AsyncMock):
            r = await client.post(
                "/senders/bulk/trash",
                headers=_auth(token),
                json={"sender_ids": [sender_id, unknown], "dry_run": False},
            )

        jobs = r.json()["jobs"]
        assert len(jobs) == 1
        assert jobs[0]["sender_id"] == sender_id

    async def test_each_sender_gets_its_own_service_instance(
        self, client, session_with_sender
    ):
        """Regression guard: a fresh service is built per task so tasks don't
        share an httplib2 connection pool (which is not thread-safe)."""
        token, sender_id, _ = session_with_sender
        second_id = str(uuid.uuid4())
        # Add a second sender to the session so two jobs are queued.
        scan_id = str(uuid.uuid4())
        session_store.store_scan_result(
            token,
            scan_id,
            {
                "scan_id": scan_id,
                "status": "complete",
                "dry_run": False,
                "senders": [
                    {
                        "id": second_id,
                        "email": "second@bulk.com",
                        "display_name": "Second",
                        "message_count": 5,
                        "consecutive_unread_count": 5,
                        "snippet": "",
                        "subject": "",
                        "first_message_date": None,
                    }
                ],
            },
        )

        build_calls = []

        def counting_build(*args, **kwargs):
            svc = MagicMock()
            build_calls.append(svc)
            return svc

        with patch(
            "app.routers.senders.build_service", side_effect=counting_build
        ), patch("app.services.gmail_trash.run_trash", new_callable=AsyncMock):
            r = await client.post(
                "/senders/bulk/trash",
                headers=_auth(token),
                json={"sender_ids": [sender_id, second_id], "dry_run": False},
            )

        assert r.status_code == 200
        assert len(r.json()["jobs"]) == 2
        assert len(build_calls) == 2, "Expected one build_service call per sender"
        assert (
            build_calls[0] is not build_calls[1]
        ), "Each task must get a distinct service"

    async def test_returns_empty_jobs_list_when_no_sender_ids_provided(
        self, client, session_token
    ):
        r = await client.post(
            "/senders/bulk/trash",
            headers=_auth(session_token),
            json={"sender_ids": [], "dry_run": False},
        )
        assert r.status_code == 200
        assert r.json()["jobs"] == []

    async def test_route_is_not_shadowed_by_sender_id_path_parameter(
        self, client, session_token
    ):
        """Regression guard: /bulk/trash must not match /{sender_id}/trash with sender_id='bulk'."""
        r = await client.post(
            "/senders/bulk/trash",
            headers=_auth(session_token),
            json={"sender_ids": [], "dry_run": False},
        )
        # If routing were broken this would be 404 "Sender not found"
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# POST /senders/bulk/block
# ═══════════════════════════════════════════════════════════════════════════════


class TestBulkBlock:

    async def test_returns_401_without_auth(self, client):
        r = await client.post("/senders/bulk/block", json={"sender_ids": []})
        assert r.status_code == 401

    async def test_returns_sender_email_in_blocked_list_on_success(
        self, client, session_with_sender
    ):
        token, sender_id, sender_email = session_with_sender

        with patch("app.dependencies.build", return_value=MagicMock()), patch(
            "app.services.gmail_filter.create_block_filter",
            new_callable=AsyncMock,
            return_value="filter-xyz",
        ):
            r = await client.post(
                "/senders/bulk/block",
                headers=_auth(token),
                json={"sender_ids": [sender_id]},
            )

        assert r.status_code == 200
        assert sender_email in r.json()["blocked"]
        assert r.json()["failed"] == []

    async def test_places_unknown_sender_ids_in_failed_list(
        self, client, session_token
    ):
        unknown = str(uuid.uuid4())

        with patch("app.dependencies.build", return_value=MagicMock()):
            r = await client.post(
                "/senders/bulk/block",
                headers=_auth(session_token),
                json={"sender_ids": [unknown]},
            )

        assert r.status_code == 200
        assert r.json()["blocked"] == []
        assert unknown in r.json()["failed"]

    async def test_places_sender_email_in_failed_list_when_gmail_api_raises(
        self, client, session_with_sender
    ):
        token, sender_id, sender_email = session_with_sender

        with patch("app.dependencies.build", return_value=MagicMock()), patch(
            "app.services.gmail_filter.create_block_filter",
            new_callable=AsyncMock,
            side_effect=Exception("Gmail API unavailable"),
        ):
            r = await client.post(
                "/senders/bulk/block",
                headers=_auth(token),
                json={"sender_ids": [sender_id]},
            )

        assert r.status_code == 200
        assert r.json()["blocked"] == []
        assert sender_email in r.json()["failed"]

    async def test_returns_empty_lists_when_no_sender_ids_provided(
        self, client, session_token
    ):
        with patch("app.dependencies.build", return_value=MagicMock()):
            r = await client.post(
                "/senders/bulk/block",
                headers=_auth(session_token),
                json={"sender_ids": []},
            )

        assert r.status_code == 200
        assert r.json() == {"blocked": [], "failed": []}

    async def test_route_is_not_shadowed_by_sender_id_path_parameter(
        self, client, session_token
    ):
        """Regression guard: /bulk/block must not match /{sender_id}/block with sender_id='bulk'."""
        with patch("app.dependencies.build", return_value=MagicMock()):
            r = await client.post(
                "/senders/bulk/block",
                headers=_auth(session_token),
                json={"sender_ids": []},
            )
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# POST /senders/bulk/skip
# ═══════════════════════════════════════════════════════════════════════════════


class TestBulkSkip:

    async def test_returns_401_without_auth(self, client):
        r = await client.post("/senders/bulk/skip", json={"sender_ids": []})
        assert r.status_code == 401

    async def test_returns_sender_ids_in_skipped_when_all_are_known(
        self, client, session_with_sender
    ):
        token, sender_id, _ = session_with_sender

        r = await client.post(
            "/senders/bulk/skip", headers=_auth(token), json={"sender_ids": [sender_id]}
        )

        assert r.status_code == 200
        assert sender_id in r.json()["skipped"]
        assert r.json()["failed"] == []

    async def test_places_unknown_ids_in_failed_list(self, client, session_token):
        unknown = str(uuid.uuid4())

        r = await client.post(
            "/senders/bulk/skip",
            headers=_auth(session_token),
            json={"sender_ids": [unknown]},
        )

        assert r.status_code == 200
        assert r.json()["skipped"] == []
        assert unknown in r.json()["failed"]

    async def test_correctly_splits_known_and_unknown_ids(
        self, client, session_with_sender
    ):
        token, sender_id, _ = session_with_sender
        unknown = str(uuid.uuid4())

        r = await client.post(
            "/senders/bulk/skip",
            headers=_auth(token),
            json={"sender_ids": [sender_id, unknown]},
        )

        assert r.status_code == 200
        assert sender_id in r.json()["skipped"]
        assert unknown in r.json()["failed"]

    async def test_returns_empty_lists_when_no_sender_ids_provided(
        self, client, session_token
    ):
        r = await client.post(
            "/senders/bulk/skip", headers=_auth(session_token), json={"sender_ids": []}
        )

        assert r.status_code == 200
        assert r.json() == {"skipped": [], "failed": []}


# ═══════════════════════════════════════════════════════════════════════════════
# Session store — pure unit tests (no HTTP)
# ═══════════════════════════════════════════════════════════════════════════════


class TestSessionStore:

    def _fresh_token(self) -> str:
        token = str(uuid.uuid4())
        session_store.create_session(
            token,
            MagicMock(),
            "user@gmail.com",
            datetime.now(timezone.utc) + timedelta(hours=1),
        )
        return token

    def test_create_and_retrieve_session(self):
        token = self._fresh_token()
        s = session_store.get_session(token)
        assert s is not None
        assert s["user_email"] == "user@gmail.com"

    def test_expired_session_returns_none(self):
        token = str(uuid.uuid4())
        session_store.create_session(
            token,
            MagicMock(),
            "old@gmail.com",
            datetime.now(timezone.utc) - timedelta(seconds=1),
        )
        assert session_store.get_session(token) is None

    def test_deleted_session_returns_none(self):
        token = self._fresh_token()
        session_store.delete_session(token)
        assert session_store.get_session(token) is None

    def test_scan_result_stored_and_retrieved_by_key(self):
        token = self._fresh_token()
        scan_id = str(uuid.uuid4())
        payload = {"scan_id": scan_id, "status": "complete", "senders": []}
        session_store.store_scan_result(token, scan_id, payload)
        assert session_store.get_scan_result(token, scan_id) == payload

    def test_queue_is_accessible_after_creation(self):
        token = self._fresh_token()
        q = session_store.create_queue(token, "q1")
        assert session_store.get_queue(token, "q1") is q

    def test_queue_returns_none_after_deletion(self):
        token = self._fresh_token()
        session_store.create_queue(token, "q1")
        session_store.delete_queue(token, "q1")
        assert session_store.get_queue(token, "q1") is None

    def test_settings_update_overrides_given_keys_and_preserves_defaults(self):
        token = self._fresh_token()
        updated = session_store.update_settings(token, {"max_senders": 99})
        assert updated["max_senders"] == 99
        assert "consecutive_unread_threshold" in updated  # other defaults preserved


# ═══════════════════════════════════════════════════════════════════════════════
# Email address parsing — unit tests
# ═══════════════════════════════════════════════════════════════════════════════

from app.services.gmail_scan import _extract_display_name, _extract_email


class TestEmailParsing:

    def test_extracts_email_from_display_name_and_angle_bracket_format(self):
        assert _extract_email("John Doe <john@example.com>") == "john@example.com"

    def test_extracts_bare_email_address(self):
        assert _extract_email("john@example.com") == "john@example.com"

    def test_lowercases_and_strips_surrounding_whitespace(self):
        assert _extract_email("  JOHN@EXAMPLE.COM  ") == "john@example.com"

    def test_extracts_email_when_only_angle_brackets_are_present(self):
        assert _extract_email("<news@newsletter.com>") == "news@newsletter.com"

    def test_extracts_display_name_from_full_format(self):
        assert _extract_display_name("John Doe <john@example.com>") == "John Doe"

    def test_returns_none_when_input_is_a_bare_email_with_no_name(self):
        assert _extract_display_name("john@example.com") is None

    def test_strips_surrounding_quotes_from_display_name(self):
        assert _extract_display_name('"Newsletter" <news@co.com>') == "Newsletter"


# ═══════════════════════════════════════════════════════════════════════════════
# gmail_filter service — unit tests
# ═══════════════════════════════════════════════════════════════════════════════

from app.services.gmail_filter import create_block_filter


class TestGmailFilterService:

    async def test_returns_filter_id_on_success(self):
        svc = MagicMock()
        svc.users.return_value.settings.return_value.filters.return_value.create.return_value.execute.return_value = {
            "id": "filter-xyz-123"
        }

        filter_id = await create_block_filter(svc, "spam@example.com")
        assert filter_id == "filter-xyz-123"

    async def test_raises_http_500_on_google_api_error(self):
        from fastapi import HTTPException
        from googleapiclient.errors import HttpError

        svc = MagicMock()
        svc.users.return_value.settings.return_value.filters.return_value.create.return_value.execute.side_effect = HttpError(
            resp=MagicMock(status=403), content=b"forbidden"
        )

        with pytest.raises(HTTPException) as exc_info:
            await create_block_filter(svc, "spam@example.com")

        assert exc_info.value.status_code == 500


# ═══════════════════════════════════════════════════════════════════════════════
# gmail_scan service — integration tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestGmailScanService:

    async def test_flags_sender_whose_unread_count_meets_the_threshold(self):
        from app.services.gmail_scan import run_scan

        svc = MagicMock()
        svc.users.return_value.messages.return_value.list.return_value.execute.side_effect = [
            {"messages": [{"id": f"msg{i}"} for i in range(25)]},
            {"messages": [], "resultSizeEstimate": 25},
        ]
        headers = {
            f"msg{i}": {
                "from": "Spammer <spam@bulk.com>",
                "subject": "Buy now!",
                "date": "Thu, 01 Jan 2026 00:00:00 +0000",
                "snippet": "Click here",
            }
            for i in range(25)
        }
        store: dict = {}
        with patch("app.services.gmail_scan._batch_get_headers", return_value=headers):
            await run_scan(
                service=svc,
                queue=asyncio.Queue(),
                scan_id="s1",
                dry_run=False,
                consecutive_unread_threshold=20,
                max_senders=10,
                max_messages_per_sender=100,
                store_result_fn=lambda r: store.update(r),
            )

        assert store["status"] == "complete"
        assert len(store["senders"]) == 1
        assert store["senders"][0]["email"] == "spam@bulk.com"

    async def test_does_not_flag_sender_below_the_threshold(self):
        from app.services.gmail_scan import run_scan

        svc = MagicMock()
        svc.users.return_value.messages.return_value.list.return_value.execute.return_value = {
            "messages": [{"id": f"msg{i}"} for i in range(5)],
        }
        headers = {
            f"msg{i}": {"from": "n@co.com", "subject": "", "date": "", "snippet": ""}
            for i in range(5)
        }
        store: dict = {}
        with patch("app.services.gmail_scan._batch_get_headers", return_value=headers):
            await run_scan(
                service=svc,
                queue=asyncio.Queue(),
                scan_id="s2",
                dry_run=False,
                consecutive_unread_threshold=20,
                max_senders=10,
                max_messages_per_sender=100,
                store_result_fn=lambda r: store.update(r),
            )

        assert store["status"] == "complete"
        assert store["senders"] == []

    async def test_completes_successfully_for_an_empty_inbox(self):
        from app.services.gmail_scan import run_scan

        svc = MagicMock()
        svc.users.return_value.messages.return_value.list.return_value.execute.return_value = {
            "messages": []
        }
        store: dict = {}
        with patch("app.services.gmail_scan._batch_get_headers", return_value={}):
            await run_scan(
                service=svc,
                queue=asyncio.Queue(),
                scan_id="s3",
                dry_run=True,
                consecutive_unread_threshold=20,
                max_senders=10,
                max_messages_per_sender=100,
                store_result_fn=lambda r: store.update(r),
            )

        assert store["status"] == "complete"
        assert store["senders"] == []

    async def test_sets_error_status_when_gmail_listing_call_fails(self):
        from app.services.gmail_scan import run_scan

        svc = MagicMock()
        svc.users.return_value.messages.return_value.list.return_value.execute.side_effect = Exception(
            "503 backendError"
        )
        store: dict = {}
        await run_scan(
            service=svc,
            queue=asyncio.Queue(),
            scan_id="s4",
            dry_run=False,
            consecutive_unread_threshold=20,
            max_senders=10,
            max_messages_per_sender=100,
            store_result_fn=lambda r: store.update(r),
        )

        assert store["status"] == "error"
        assert "503" in store.get("error", "")

    async def test_falls_back_gracefully_when_rate_limited_during_total_count_lookup(
        self,
    ):
        from app.services.gmail_scan import run_scan
        from googleapiclient.errors import HttpError

        svc = MagicMock()
        svc.users.return_value.messages.return_value.list.return_value.execute.return_value = {
            "messages": [{"id": f"msg{i}"} for i in range(25)],
        }
        headers = {
            f"msg{i}": {"from": "s@s.com", "subject": "", "date": "", "snippet": ""}
            for i in range(25)
        }
        store: dict = {}
        with patch(
            "app.services.gmail_scan._batch_get_headers", return_value=headers
        ), patch(
            "app.services.gmail_scan._execute_with_backoff",
            side_effect=HttpError(
                resp=MagicMock(status=403), content=b"rateLimitExceeded"
            ),
        ):
            await run_scan(
                service=svc,
                queue=asyncio.Queue(),
                scan_id="s-rl",
                dry_run=False,
                consecutive_unread_threshold=20,
                max_senders=10,
                max_messages_per_sender=100,
                store_result_fn=lambda r: store.update(r),
            )

        assert store["status"] == "complete"
        assert len(store["senders"]) == 1
        assert store["senders"][0]["message_count"] == 25  # falls back to unread count

    async def test_calls_store_result_fn_incrementally_after_each_flagged_sender(self):
        from app.services.gmail_scan import run_scan

        svc = MagicMock()
        svc.users.return_value.messages.return_value.list.return_value.execute.side_effect = [
            {"messages": [{"id": f"msg{i}"} for i in range(25)]},
            {"messages": [], "resultSizeEstimate": 25},
        ]
        headers = {
            f"msg{i}": {"from": "s@s.com", "subject": "", "date": "", "snippet": ""}
            for i in range(25)
        }
        snapshots: list[dict] = []
        with patch("app.services.gmail_scan._batch_get_headers", return_value=headers):
            await run_scan(
                service=svc,
                queue=asyncio.Queue(),
                scan_id="s-inc",
                dry_run=False,
                consecutive_unread_threshold=20,
                max_senders=10,
                max_messages_per_sender=100,
                store_result_fn=lambda r: snapshots.append(
                    {"status": r["status"], "count": len(r["senders"])}
                ),
            )

        assert snapshots[0] == {"status": "running", "count": 1}
        assert snapshots[-1]["status"] == "complete"

    async def test_stops_listing_messages_once_20000_cap_is_reached(self):
        from app.services.gmail_scan import run_scan

        svc = MagicMock()
        svc.users.return_value.messages.return_value.list.return_value.execute.side_effect = [
            {
                "messages": [{"id": f"m{i}"} for i in range(20_000)],
                "nextPageToken": "p2",
            },
            {
                "messages": [{"id": f"x{i}"} for i in range(500)]
            },  # must never be fetched
        ]
        store: dict = {}
        with patch("app.services.gmail_scan._batch_get_headers", return_value={}):
            await run_scan(
                service=svc,
                queue=asyncio.Queue(),
                scan_id="s-cap",
                dry_run=False,
                consecutive_unread_threshold=99999,
                max_senders=10,
                max_messages_per_sender=100,
                store_result_fn=lambda r: store.update(r),
            )

        assert store["status"] == "complete"
        assert svc.users.return_value.messages.return_value.list.call_count == 1

    async def test_stops_flagging_once_max_senders_limit_is_reached(self):
        from app.services.gmail_scan import run_scan

        svc = MagicMock()
        svc.users.return_value.messages.return_value.list.return_value.execute.return_value = {
            "messages": [{"id": f"msg{i}"} for i in range(60)],
            "resultSizeEstimate": 20,
        }
        headers: dict = {}
        for i in range(20):
            headers[f"msg{i}"] = {
                "from": "a@a.com",
                "subject": "",
                "date": "",
                "snippet": "",
            }
            headers[f"msg{i+20}"] = {
                "from": "b@b.com",
                "subject": "",
                "date": "",
                "snippet": "",
            }
            headers[f"msg{i+40}"] = {
                "from": "c@c.com",
                "subject": "",
                "date": "",
                "snippet": "",
            }
        store: dict = {}
        with patch("app.services.gmail_scan._batch_get_headers", return_value=headers):
            await run_scan(
                service=svc,
                queue=asyncio.Queue(),
                scan_id="s-max",
                dry_run=False,
                consecutive_unread_threshold=20,
                max_senders=2,
                max_messages_per_sender=100,
                store_result_fn=lambda r: store.update(r),
            )

        assert store["status"] == "complete"
        assert len(store["senders"]) <= 2


# ═══════════════════════════════════════════════════════════════════════════════
# gmail_trash service — integration tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestGmailTrashService:

    async def test_listing_query_includes_already_trashed_messages(self):
        """Query must be 'from:X' with no -in:trash — we permanently delete everything."""
        from app.services.gmail_trash import run_trash

        svc = MagicMock()
        svc.users.return_value.messages.return_value.list.return_value.execute.return_value = {
            "messages": [{"id": f"msg{i}"} for i in range(5)]
        }
        svc.users.return_value.messages.return_value.batchDelete.return_value.execute.return_value = (
            None
        )

        with patch(
            "app.services.gmail_trash._execute_with_backoff",
            side_effect=lambda req: req.execute(),
        ):
            await run_trash(
                service=svc,
                queue=asyncio.Queue(),
                sender_email="spam@bulk.com",
                dry_run=False,
                store_result_fn=lambda _: None,
            )

        list_call = svc.users.return_value.messages.return_value.list.call_args
        q_arg = list_call.kwargs.get("q", "")
        assert "spam@bulk.com" in q_arg
        assert "-in:trash" not in q_arg

    async def test_uses_batch_delete_not_trash(self):
        """Permanently deletes via batchDelete; never calls messages.trash."""
        from app.services.gmail_trash import run_trash

        svc = MagicMock()
        svc.users.return_value.messages.return_value.list.return_value.execute.return_value = {
            "messages": [{"id": f"msg{i}"} for i in range(10)]
        }
        svc.users.return_value.messages.return_value.batchDelete.return_value.execute.return_value = (
            None
        )

        with patch(
            "app.services.gmail_trash._execute_with_backoff",
            side_effect=lambda req: req.execute(),
        ):
            await run_trash(
                service=svc,
                queue=asyncio.Queue(),
                sender_email="spam@bulk.com",
                dry_run=False,
                store_result_fn=lambda _: None,
            )

        svc.users.return_value.messages.return_value.batchDelete.assert_called()
        svc.users.return_value.messages.return_value.trash.assert_not_called()

    async def test_emits_complete_with_accurate_deleted_count(self):
        from app.services.gmail_trash import run_trash

        svc = MagicMock()
        svc.users.return_value.messages.return_value.list.return_value.execute.return_value = {
            "messages": [{"id": f"msg{i}"} for i in range(15)]
        }
        svc.users.return_value.messages.return_value.batchDelete.return_value.execute.return_value = (
            None
        )
        store: dict = {}

        with patch(
            "app.services.gmail_trash._execute_with_backoff",
            side_effect=lambda req: req.execute(),
        ):
            await run_trash(
                service=svc,
                queue=asyncio.Queue(),
                sender_email="s@s.com",
                dry_run=False,
                store_result_fn=lambda r: store.update(r),
            )

        assert store["trashed_count"] == 15
        assert store["dry_run"] is False

    async def test_splits_large_message_lists_into_batches_of_1000(self):
        """1500 messages → 2 batchDelete calls: first with 1000 IDs, second with 500."""
        from app.services.gmail_trash import run_trash

        svc = MagicMock()
        svc.users.return_value.messages.return_value.list.return_value.execute.return_value = {
            "messages": [{"id": f"msg{i}"} for i in range(1500)]
        }
        svc.users.return_value.messages.return_value.batchDelete.return_value.execute.return_value = (
            None
        )

        with patch(
            "app.services.gmail_trash._execute_with_backoff",
            side_effect=lambda req: req.execute(),
        ):
            await run_trash(
                service=svc,
                queue=asyncio.Queue(),
                sender_email="s@s.com",
                dry_run=False,
                store_result_fn=lambda _: None,
            )

        calls = svc.users.return_value.messages.return_value.batchDelete.call_args_list
        assert len(calls) == 2
        assert len(calls[0].kwargs["body"]["ids"]) == 1000
        assert len(calls[1].kwargs["body"]["ids"]) == 500

    async def test_handles_paginated_message_listing(self):
        """Fetches all pages before deleting; total count spans all pages."""
        from app.services.gmail_trash import run_trash

        svc = MagicMock()
        svc.users.return_value.messages.return_value.list.return_value.execute.side_effect = [
            {
                "messages": [{"id": f"p1_{i}"} for i in range(500)],
                "nextPageToken": "tok",
            },
            {"messages": [{"id": f"p2_{i}"} for i in range(200)]},
        ]
        svc.users.return_value.messages.return_value.batchDelete.return_value.execute.return_value = (
            None
        )
        store: dict = {}

        with patch(
            "app.services.gmail_trash._execute_with_backoff",
            side_effect=lambda req: req.execute(),
        ):
            await run_trash(
                service=svc,
                queue=asyncio.Queue(),
                sender_email="s@s.com",
                dry_run=False,
                store_result_fn=lambda r: store.update(r),
            )

        assert store["trashed_count"] == 700  # 500 + 200

    async def test_dry_run_reports_message_count_without_calling_delete(self):
        from app.services.gmail_trash import run_trash

        svc = MagicMock()
        svc.users.return_value.messages.return_value.list.return_value.execute.return_value = {
            "messages": [{"id": f"msg{i}"} for i in range(20)],
        }
        store: dict = {}

        with patch(
            "app.services.gmail_trash._execute_with_backoff",
            side_effect=lambda req: req.execute(),
        ):
            await run_trash(
                service=svc,
                queue=asyncio.Queue(),
                sender_email="s@s.com",
                dry_run=True,
                store_result_fn=lambda r: store.update(r),
            )

        assert store["dry_run"] is True
        assert store["trashed_count"] == 20
        svc.users.return_value.messages.return_value.batchDelete.assert_not_called()

    async def test_emits_error_when_batch_delete_fails(self):
        """A hard failure on batchDelete (e.g. exhausted retries) emits an error event."""
        from app.services.gmail_trash import run_trash
        from googleapiclient.errors import HttpError

        svc = MagicMock()
        svc.users.return_value.messages.return_value.list.return_value.execute.return_value = {
            "messages": [{"id": f"msg{i}"} for i in range(10)]
        }
        svc.users.return_value.messages.return_value.batchDelete.return_value.execute.side_effect = HttpError(
            resp=MagicMock(status=429), content=b"rateLimitExceeded"
        )

        q: asyncio.Queue = asyncio.Queue()
        with patch(
            "app.services.gmail_trash._execute_with_backoff",
            side_effect=lambda req: req.execute(),
        ):
            await run_trash(
                service=svc,
                queue=q,
                sender_email="s@s.com",
                dry_run=False,
                store_result_fn=lambda _: None,
            )

        events = [
            item["type"]
            for item in [q.get_nowait() for _ in range(q.qsize())]
            if item is not None
        ]
        assert "error" in events
        assert "complete" not in events
