# Copyright (c) 2026, Rye Stahle-Smith; All rights reserved.
# Gmail Cleaner
# Last Updated: May 24th, 2026
# Description: Defines various tests for the API endpoints.

# Import necessary libraries and modules
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.store import session as session_store


# Define a helper function to format the Authorization header (for authenticated requests)
def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# Define a test class for the /health endpoint
class TestHealth:
    # Test that the GET endpoint returns a 200 status code and the expected JSON response
    async def test_returns_200_with_ok_status(self, client):
        r = await client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}


# Define a test class for the /auth/login endpoint
class TestAuthLogin:
    # Test that the GET endpoint returns a 200 status code and a valid Google OAuth URL when called
    async def test_returns_google_oauth_url(self, client):
        with patch("app.services.gmail_auth.Flow") as MockFlow:
            instance = MagicMock()
            instance.authorization_url.return_value = (
                "https://accounts.google.com/o/oauth2/auth?fake",
                "state123",
            )
            # store_state reads these from flow.oauth2session; None keeps them JSON-serializable
            instance.oauth2session._code_verifier = None
            instance.oauth2session.code_challenge_method = None
            MockFlow.from_client_config.return_value = instance
            r = await client.get("/auth/login")

        assert r.status_code == 200
        assert r.json()["auth_url"].startswith("https://")


# Define a test class for the /auth/me endpoint
class TestAuthMe:
    # Test that the GET endpoint returns the user's email and authenticated status when a valid token is provided
    async def test_returns_email_and_authenticated_true_with_valid_token(
        self, client, session_token
    ):
        r = await client.get("/auth/me", headers=_auth(session_token))
        assert r.status_code == 200
        assert r.json()["email"] == "test@gmail.com"
        assert r.json()["authenticated"] is True

    # Test that the GET endpoint returns a 401 status code when no authorization header is present
    async def test_returns_401_when_no_authorization_header_present(self, client):
        r = await client.get("/auth/me")
        assert r.status_code == 401

    # Test that the GET endpoint returns a 401 status code for an unrecognised token
    async def test_returns_401_for_unrecognised_token(self, client):
        r = await client.get("/auth/me", headers=_auth("not-a-real-token"))
        assert r.status_code == 401

    # Test that the GET endpoint returns a 401 status code for an expired session
    async def test_returns_401_for_expired_session(self, client):
        import json
        token = str(uuid.uuid4())
        expired_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        creds = MagicMock()
        creds.to_json.return_value = json.dumps({
            "token": "t", "refresh_token": "r",
            "client_id": "c", "client_secret": "s",
            "token_uri": "https://oauth2.googleapis.com/token", "scopes": [],
            "expiry": "2099-12-31T23:59:59Z",
        })
        await session_store.create_session(token, creds, "old@gmail.com", expired_at)

        r = await client.get("/auth/me", headers=_auth(token))
        assert r.status_code == 401


# Define a test class for the /auth/logout endpoint
class TestAuthLogout:
    # Test that the POST endpoint successfully logs out the user and invalidates the session token
    async def test_session_is_rejected_after_logout(self, client, session_token):
        assert (
            await client.get("/auth/me", headers=_auth(session_token))
        ).status_code == 200

        r = await client.post("/auth/logout", headers=_auth(session_token))
        assert r.status_code == 204

        assert (
            await client.get("/auth/me", headers=_auth(session_token))
        ).status_code == 401


# Define a test class for the /scan/start endpoint
class TestScanStart:
    # Test that the POST endpoint returns a 200 status code and a valid UUID scan_id when a scan is successfully started
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

    # Test that the POST endpoint returns a 401 status code when no authorization header is present
    async def test_returns_401_without_auth(self, client):
        r = await client.post("/scan/start", json={"dry_run": False})
        assert r.status_code == 401


# Define a test class for the /scan/{scan_id}/results endpoint
class TestScanResults:
    # Test that the GET endpoint returns a 404 status code when an unknown scan_id is requested
    async def test_returns_404_for_unknown_scan_id(self, client, session_token):
        r = await client.get(
            f"/scan/{uuid.uuid4()}/results", headers=_auth(session_token)
        )
        assert r.status_code == 404

    # Test that the GET endpoint returns the stored scan result for a known scan_id
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

    # Test that the GET endpoint includes all sender details in the response for a known scan result
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


# Define a test class for the /settings endpoint
class TestSettings:
    # Test that the GET endpoint returns all default settings keys in the response
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

    # Test that the PATCH endpoint updates specified keys and preserves others
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


# Define a test class for the /senders/{id}/preview endpoint
class TestSenderPreview:
    # Test that the GET endpoint returns a 404 status code when the requested sender_id is not in the user's session
    async def test_returns_404_when_sender_not_in_session(self, client, session_token):
        with patch("app.dependencies.build", return_value=MagicMock()):
            r = await client.get(
                f"/senders/{uuid.uuid4()}/preview", headers=_auth(session_token)
            )
        assert r.status_code == 404

    # Test that the GET endpoint returns the subject, snippet, and email for a sender when Gmail messages are available
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

    # Test that the GET endpoint falls back to session data when Gmail returns no messages for the sender
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


# Define a test class for the /senders/{id}/trash endpoint
class TestSenderTrash:
    # Test that the POST endpoint returns a 404 status code when the requested sender_id is not in the user's session
    async def test_returns_404_when_sender_not_in_session(self, client, session_token):
        with patch("app.dependencies.build", return_value=MagicMock()):
            r = await client.post(
                f"/senders/{uuid.uuid4()}/trash",
                headers=_auth(session_token),
                json={"dry_run": True},
            )
        assert r.status_code == 404

    # Test that the POST endpoint returns a job_id, sender email, and estimated count when a trash job is successfully queued for a sender
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


# Define a test class for the /senders/{id}/block endpoint
class TestSenderBlock:
    # Test that the POST endpoint returns a 404 status code when the requested sender_id is not in the user's session
    async def test_returns_404_when_sender_not_in_session(self, client, session_token):
        with patch("app.dependencies.build", return_value=MagicMock()):
            r = await client.post(
                f"/senders/{uuid.uuid4()}/block", headers=_auth(session_token)
            )
        assert r.status_code == 404

    # Test that the POST endpoint returns the created filter_id and sender email when a block filter is successfully created for a sender
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

    # Test that the POST endpoint returns a 500 status code when the Gmail API raises an error during block filter creation
    async def test_returns_401_without_auth(self, client):
        r = await client.post(f"/senders/{uuid.uuid4()}/block")
        assert r.status_code == 401


# Define a test class for the /senders/bulk/trash endpoint
class TestBulkTrash:
    # Test that the POST endpoint returns a 401 status code when no authorization header is present
    async def test_returns_401_without_auth(self, client):
        r = await client.post(
            "/senders/bulk/trash", json={"sender_ids": [], "dry_run": False}
        )
        assert r.status_code == 401

    # Test that the POST endpoint returns one job entry for each known sender_id provided in the request,
    # and that each job entry contains a valid UUID job_id and the correct sender_id
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

    # Test that the POST endpoint silently ignores unknown sender_ids and does not include them in the jobs list
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

    # Test that the POST endpoint creates a fresh service instance for each sender_id processed
    async def test_each_sender_gets_its_own_service_instance(
        self, client, session_with_sender
    ):
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

    # Test that the POST endpoint returns an empty jobs list when no sender_ids are provided in the request
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

    # Test that the POST endpoint does not match the /{sender_id}/trash route when sender_id='bulk'
    async def test_route_is_not_shadowed_by_sender_id_path_parameter(
        self, client, session_token
    ):
        r = await client.post(
            "/senders/bulk/trash",
            headers=_auth(session_token),
            json={"sender_ids": [], "dry_run": False},
        )
        # If routing were broken this would be 404 "Sender not found"
        assert r.status_code == 200


# Define a test class for the /senders/bulk/block endpoint
class TestBulkBlock:
    # Test that the POST endpoint returns a 401 status code when no authorization header is present
    async def test_returns_401_without_auth(self, client):
        r = await client.post("/senders/bulk/block", json={"sender_ids": []})
        assert r.status_code == 401

    # Test that the POST endpoint returns the blocked sender email in the blocked list,
    # and an empty failed list when a block filter is successfully created for a known sender_id
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

    # Test that the POST endpoint places unknown sender_ids in the failed list and does not include them in the blocked list
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

    # Test that the POST endpoint places sender emails corresponding to sender_ids that cause Gmail API errors into the failed list
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

    # Test that the POST endpoint returns empty blocked and failed lists when no sender_ids are provided in the request
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

    # Test that the POST endpoint does not match the /{sender_id}/block route when sender_id='bulk'
    async def test_route_is_not_shadowed_by_sender_id_path_parameter(
        self, client, session_token
    ):
        with patch("app.dependencies.build", return_value=MagicMock()):
            r = await client.post(
                "/senders/bulk/block",
                headers=_auth(session_token),
                json={"sender_ids": []},
            )
        assert r.status_code == 200


# Define a test class for the /senders/bulk/skip endpoint
class TestBulkSkip:
    # Test that the POST endpoint returns a 401 status code when no authorization header is present
    async def test_returns_401_without_auth(self, client):
        r = await client.post("/senders/bulk/skip", json={"sender_ids": []})
        assert r.status_code == 401

    # Test that the POST endpoint returns the sender_id in the skipped list, and an empty failed list when all provided sender_ids are known and successfully processed
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

    # Test that the POST endpoint places unknown sender_ids into the failed list and does not include them in the skipped list
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

    # Test that the POST endpoint correctly splits known and unknown sender_ids into the skipped and failed lists
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

    # Test that the POST endpoint returns empty skipped and failed lists when no sender_ids are provided in the request
    async def test_returns_empty_lists_when_no_sender_ids_provided(
        self, client, session_token
    ):
        r = await client.post(
            "/senders/bulk/skip", headers=_auth(session_token), json={"sender_ids": []}
        )

        assert r.status_code == 200
        assert r.json() == {"skipped": [], "failed": []}
