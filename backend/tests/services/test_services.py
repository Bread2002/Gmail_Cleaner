# Copyright (c) 2026, Rye Stahle-Smith; All rights reserved.
# Gmail Cleaner
# Last Updated: May 28th, 2026
# Description: Defines various tests for Gmail services (Parsing, scanning, blocking/filtering,
#              permanent deletion via batchDelete, and recoverable move-to-trash via batchModify)

# Import necessary libraries and modules
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.store import session as session_store
from app.services.gmail_filter import create_block_filter
from app.services.gmail_scan import run_scan, _extract_display_name, _extract_email
from app.services.gmail_delete import run_delete
from app.services.gmail_move_to_trash import run_move_to_trash


# Define a test class for the email parsing helper functions
class TestEmailParsing:
    # Test that _extract_email correctly extracts the email address from a string in the format "Display Name <email@example.com>"
    def test_extracts_email_from_display_name_and_angle_bracket_format(self):
        assert _extract_email("John Doe <john@example.com>") == "john@example.com"

    # Test that _extract_email correctly extracts a bare email address when no display name or angle brackets are present
    def test_extracts_bare_email_address(self):
        assert _extract_email("john@example.com") == "john@example.com"

    # Test that _extract_email lowercases the email address and strips any surrounding whitespace
    def test_lowercases_and_strips_surrounding_whitespace(self):
        assert _extract_email("  JOHN@EXAMPLE.COM  ") == "john@example.com"

    # Test that _extract_email correctly extracts the email address when the input is in the format "<email@example.com>"
    def test_extracts_email_when_only_angle_brackets_are_present(self):
        assert _extract_email("<news@newsletter.com>") == "news@newsletter.com"

    # Test that _extract_display_name correctly extracts the display name from a string in the format "Display Name <email@example.com>"
    def test_extracts_display_name_from_full_format(self):
        assert _extract_display_name("John Doe <john@example.com>") == "John Doe"

    # Test that _extract_display_name returns None when the input string does not follow the expected format/ does not contain a display name
    def test_returns_none_when_input_is_a_bare_email_with_no_name(self):
        assert _extract_display_name("john@example.com") is None

    # Test that _extract_display_name correctly extracts the display name even when it contains surrounding artifcats
    def test_strips_surrounding_quotes_from_display_name(self):
        assert _extract_display_name('"Newsletter" <news@co.com>') == "Newsletter"


# Define a test class for the session storage
class TestSessionStore:
    # Helper method to create a fresh session and return its token
    async def _fresh_token(self) -> str:
        import json
        from unittest.mock import MagicMock

        token = str(uuid.uuid4())
        creds = MagicMock()
        creds.to_json.return_value = json.dumps(
            {
                "token": "t",
                "refresh_token": "r",
                "client_id": "c",
                "client_secret": "s",
                "token_uri": "https://oauth2.googleapis.com/token",
                "scopes": [],
                "expiry": "2099-12-31T23:59:59Z",
            }
        )
        await session_store.create_session(
            token,
            creds,
            "test@gmail.com",
            datetime.now(timezone.utc) + timedelta(hours=1),
        )
        return token

    # Test that a session can be created and then retrieved by its token, and that the retrieved session contains the correct user email
    async def test_create_and_retrieve_session(self):
        token = await self._fresh_token()
        s = await session_store.get_session(token)
        assert s is not None
        assert s["user_email"] == "test@gmail.com"

    # Test that a session with an expiration time in the past is treated as expired and get_session returns None for its token
    async def test_expired_session_returns_none(self):
        import json
        from unittest.mock import MagicMock

        token = str(uuid.uuid4())
        creds = MagicMock()
        creds.to_json.return_value = json.dumps(
            {
                "token": "t",
                "refresh_token": "r",
                "client_id": "c",
                "client_secret": "s",
                "token_uri": "https://oauth2.googleapis.com/token",
                "scopes": [],
                "expiry": "2099-12-31T23:59:59Z",
            }
        )
        await session_store.create_session(
            token,
            creds,
            "old@gmail.com",
            datetime.now(timezone.utc) - timedelta(seconds=1),
        )
        assert await session_store.get_session(token) is None

    # Test that a session that has been deleted from the store returns None when get_session is called with its token
    async def test_deleted_session_returns_none(self):
        token = await self._fresh_token()
        await session_store.delete_session(token)
        assert await session_store.get_session(token) is None

    # Test that a scan result can be stored in the session storage with a specific token and scan_id, and that it can be retrieved correctly
    async def test_scan_result_stored_and_retrieved_by_key(self):
        token = await self._fresh_token()
        scan_id = str(uuid.uuid4())
        payload = {"scan_id": scan_id, "status": "complete", "senders": []}
        session_store.store_scan_result(token, scan_id, payload)
        assert session_store.get_scan_result(token, scan_id) == payload

    # Test that a queue created for a specific token is accessible via get_queue and that it returns the same queue object that was created
    async def test_queue_is_accessible_after_creation(self):
        token = await self._fresh_token()
        q = session_store.create_queue(token, "q1")
        assert session_store.get_queue(token, "q1") is q

    # Test that a queue that has been deleted from the session storage returns None when get_queue is called with its token and queue name
    async def test_queue_returns_none_after_deletion(self):
        token = await self._fresh_token()
        session_store.create_queue(token, "q1")
        session_store.delete_queue(token, "q1")
        assert session_store.get_queue(token, "q1") is None

    # Test that updating settings with a dictionary containing specific keys correctly updates those keys in the session's settings
    async def test_settings_update_overrides_given_keys_and_preserves_defaults(self):
        token = await self._fresh_token()
        updated = await session_store.update_settings(token, {"max_senders": 99})
        assert updated["max_senders"] == 99
        assert "consecutive_unread_threshold" in updated  # Other defaults preserved


# Define a test class for the Gmail filter service
class TestGmailFilterService:
    # Test that create_block_filter returns the filter ID from the Gmail API response when a filter is successfully created
    async def test_returns_filter_id_on_success(self):
        svc = MagicMock()
        svc.users.return_value.settings.return_value.filters.return_value.create.return_value.execute.return_value = {
            "id": "filter-xyz-123"
        }

        filter_id = await create_block_filter(svc, "spam@example.com")
        assert filter_id == "filter-xyz-123"

    # Test that create_block_filter raises an HTTPException with status code 500 when the Gmail API raises an HttpError during filter creation
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


# Define a test class for the Gmail scan service
class TestGmailScanService:
    # Test that run_scan correctly flags a sender whose number of unread messages meets the specified threshold
    async def test_flags_sender_whose_unread_count_meets_the_threshold(self):
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

    # Test that run_scan does not flag a sender whose number of unread messages is below the specified threshold
    async def test_does_not_flag_sender_below_the_threshold(self):
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

    # Test that run_scan completes successfully and returns an empty senders list when the user's inbox contains no messages
    async def test_completes_successfully_for_an_empty_inbox(self):
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

    # Test that run_scan sets the scan result raises an error when the Gmail API raises an exception during the listing of messages
    async def test_sets_error_status_when_gmail_listing_call_fails(self):
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

    # Test that run_scan falls back to using the total count of messages returned by the Gmail API when it encounters a rate limit error
    async def test_falls_back_gracefully_when_rate_limited_during_total_count_lookup(
        self,
    ):
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

    # Test that run_scan calls the store_result_fn incrementally after processing each flagged sender
    async def test_calls_store_result_fn_incrementally_after_each_flagged_sender(self):
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

    # Test that run_scan stops fetching messages and completes once the specified cap on total messages processed is reached
    async def test_stops_listing_messages_once_20000_cap_is_reached(self):
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

    # Test that run_scan stops fetching messages and completes once the specified cap on unique senders flagged is reached
    async def test_stops_flagging_once_max_senders_limit_is_reached(self):
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


# Define a test class for the Gmail delete service
class TestGmailDeleteService:
    # Test that run_delete permanently deletes messages via batchDelete and does not call the messages.delete method at all
    async def test_uses_batch_delete(self):
        svc = MagicMock()
        svc.users.return_value.messages.return_value.list.return_value.execute.return_value = {
            "messages": [{"id": f"msg{i}"} for i in range(10)]
        }
        svc.users.return_value.messages.return_value.batchDelete.return_value.execute.return_value = (
            None
        )

        with patch(
            "app.services.gmail_delete._execute_with_backoff",
            side_effect=lambda req: req.execute(),
        ):
            await run_delete(
                service=svc,
                queue=asyncio.Queue(),
                sender_email="spam@bulk.com",
                dry_run=False,
                store_result_fn=lambda _: None,
            )

        svc.users.return_value.messages.return_value.batchDelete.assert_called()
        svc.users.return_value.messages.return_value.delete.assert_not_called()

    # Test that run_delete emits a "complete" event with the accurate count of messages deleted
    async def test_emits_complete_with_accurate_deleted_count(self):
        svc = MagicMock()
        svc.users.return_value.messages.return_value.list.return_value.execute.return_value = {
            "messages": [{"id": f"msg{i}"} for i in range(15)]
        }
        svc.users.return_value.messages.return_value.batchDelete.return_value.execute.return_value = (
            None
        )
        store: dict = {}

        with patch(
            "app.services.gmail_delete._execute_with_backoff",
            side_effect=lambda req: req.execute(),
        ):
            await run_delete(
                service=svc,
                queue=asyncio.Queue(),
                sender_email="s@s.com",
                dry_run=False,
                store_result_fn=lambda r: store.update(r),
            )

        assert store["deleted_count"] == 15
        assert store["dry_run"] is False

    # Test that run_delete correctly splits large lists of message IDs into batches of 1000 when calling batchDelete
    async def test_splits_large_message_lists_into_batches_of_1000(self):
        svc = MagicMock()
        svc.users.return_value.messages.return_value.list.return_value.execute.return_value = {
            "messages": [{"id": f"msg{i}"} for i in range(1500)]
        }
        svc.users.return_value.messages.return_value.batchDelete.return_value.execute.return_value = (
            None
        )

        with patch(
            "app.services.gmail_delete._execute_with_backoff",
            side_effect=lambda req: req.execute(),
        ):
            await run_delete(
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

    # Test that run_delete correctly handles paginated results from the Gmail API and sums the total count of messages deleted across all pages
    async def test_handles_paginated_message_listing(self):
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
            "app.services.gmail_delete._execute_with_backoff",
            side_effect=lambda req: req.execute(),
        ):
            await run_delete(
                service=svc,
                queue=asyncio.Queue(),
                sender_email="s@s.com",
                dry_run=False,
                store_result_fn=lambda r: store.update(r),
            )

        assert store["deleted_count"] == 700  # 500 + 200

    # Test that when run_delete is called with dry_run=True, it reports the count of messages that would be deleted but does not call batchDelete at all
    async def test_dry_run_reports_message_count_without_calling_delete(self):
        svc = MagicMock()
        svc.users.return_value.messages.return_value.list.return_value.execute.return_value = {
            "messages": [{"id": f"msg{i}"} for i in range(20)],
        }
        store: dict = {}

        with patch(
            "app.services.gmail_delete._execute_with_backoff",
            side_effect=lambda req: req.execute(),
        ):
            await run_delete(
                service=svc,
                queue=asyncio.Queue(),
                sender_email="s@s.com",
                dry_run=True,
                store_result_fn=lambda r: store.update(r),
            )

        assert store["dry_run"] is True
        assert store["deleted_count"] == 20
        svc.users.return_value.messages.return_value.batchDelete.assert_not_called()

    # Test that run_delete emits an "error" event when the batchDelete method raises a hard failure
    async def test_emits_error_when_batch_delete_fails(self):
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
            "app.services.gmail_delete._execute_with_backoff",
            side_effect=lambda req: req.execute(),
        ):
            await run_delete(
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


# Define a test class for the Gmail move-to-trash service (recoverable — uses batchModify, not batchDelete)
class TestGmailMoveToTrashService:
    # Test that run_move_to_trash queries by sender email without excluding already-trashed messages
    async def test_listing_query_includes_sender_email(self):
        svc = MagicMock()
        svc.users.return_value.messages.return_value.list.return_value.execute.return_value = {
            "messages": [{"id": f"msg{i}"} for i in range(5)]
        }
        svc.users.return_value.messages.return_value.batchModify.return_value.execute.return_value = (
            None
        )

        with patch(
            "app.services.gmail_move_to_trash._execute_with_backoff",
            side_effect=lambda req: req.execute(),
        ):
            await run_move_to_trash(
                service=svc,
                queue=asyncio.Queue(),
                sender_email="spam@bulk.com",
                dry_run=False,
                store_result_fn=lambda _: None,
            )

        list_call = svc.users.return_value.messages.return_value.list.call_args
        q_arg = list_call.kwargs.get("q", "")
        assert "spam@bulk.com" in q_arg

    # Test that run_move_to_trash uses batchModify (not batchDelete) to move messages to Gmail Trash
    async def test_uses_batch_modify_not_batch_delete(self):
        svc = MagicMock()
        svc.users.return_value.messages.return_value.list.return_value.execute.return_value = {
            "messages": [{"id": f"msg{i}"} for i in range(10)]
        }
        svc.users.return_value.messages.return_value.batchModify.return_value.execute.return_value = (
            None
        )

        with patch(
            "app.services.gmail_move_to_trash._execute_with_backoff",
            side_effect=lambda req: req.execute(),
        ):
            await run_move_to_trash(
                service=svc,
                queue=asyncio.Queue(),
                sender_email="spam@bulk.com",
                dry_run=False,
                store_result_fn=lambda _: None,
            )

        svc.users.return_value.messages.return_value.batchModify.assert_called()
        svc.users.return_value.messages.return_value.batchDelete.assert_not_called()

    # Test that run_move_to_trash passes addLabelIds=['TRASH'] in the batchModify body (not removeLabel)
    async def test_batch_modify_body_adds_trash_label(self):
        svc = MagicMock()
        svc.users.return_value.messages.return_value.list.return_value.execute.return_value = {
            "messages": [{"id": f"msg{i}"} for i in range(5)]
        }
        svc.users.return_value.messages.return_value.batchModify.return_value.execute.return_value = (
            None
        )

        with patch(
            "app.services.gmail_move_to_trash._execute_with_backoff",
            side_effect=lambda req: req.execute(),
        ):
            await run_move_to_trash(
                service=svc,
                queue=asyncio.Queue(),
                sender_email="s@s.com",
                dry_run=False,
                store_result_fn=lambda _: None,
            )

        call_kwargs = (
            svc.users.return_value.messages.return_value.batchModify.call_args.kwargs
        )
        assert "TRASH" in call_kwargs["body"]["addLabelIds"]

    # Test that run_move_to_trash emits a "complete" event with the accurate count of messages moved
    async def test_emits_complete_with_accurate_moved_count(self):
        svc = MagicMock()
        svc.users.return_value.messages.return_value.list.return_value.execute.return_value = {
            "messages": [{"id": f"msg{i}"} for i in range(15)]
        }
        svc.users.return_value.messages.return_value.batchModify.return_value.execute.return_value = (
            None
        )
        store: dict = {}

        with patch(
            "app.services.gmail_move_to_trash._execute_with_backoff",
            side_effect=lambda req: req.execute(),
        ):
            await run_move_to_trash(
                service=svc,
                queue=asyncio.Queue(),
                sender_email="s@s.com",
                dry_run=False,
                store_result_fn=lambda r: store.update(r),
            )

        assert store["trashed_count"] == 15
        assert store["dry_run"] is False

    # Test that run_move_to_trash correctly splits large message lists into batches of 1000
    async def test_splits_large_message_lists_into_batches_of_1000(self):
        svc = MagicMock()
        svc.users.return_value.messages.return_value.list.return_value.execute.return_value = {
            "messages": [{"id": f"msg{i}"} for i in range(1500)]
        }
        svc.users.return_value.messages.return_value.batchModify.return_value.execute.return_value = (
            None
        )

        with patch(
            "app.services.gmail_move_to_trash._execute_with_backoff",
            side_effect=lambda req: req.execute(),
        ):
            await run_move_to_trash(
                service=svc,
                queue=asyncio.Queue(),
                sender_email="s@s.com",
                dry_run=False,
                store_result_fn=lambda _: None,
            )

        calls = svc.users.return_value.messages.return_value.batchModify.call_args_list
        assert len(calls) == 2
        assert len(calls[0].kwargs["body"]["ids"]) == 1000
        assert len(calls[1].kwargs["body"]["ids"]) == 500

    # Test that run_move_to_trash handles paginated results and sums the total correctly
    async def test_handles_paginated_message_listing(self):
        svc = MagicMock()
        svc.users.return_value.messages.return_value.list.return_value.execute.side_effect = [
            {
                "messages": [{"id": f"p1_{i}"} for i in range(500)],
                "nextPageToken": "tok",
            },
            {"messages": [{"id": f"p2_{i}"} for i in range(200)]},
        ]
        svc.users.return_value.messages.return_value.batchModify.return_value.execute.return_value = (
            None
        )
        store: dict = {}

        with patch(
            "app.services.gmail_move_to_trash._execute_with_backoff",
            side_effect=lambda req: req.execute(),
        ):
            await run_move_to_trash(
                service=svc,
                queue=asyncio.Queue(),
                sender_email="s@s.com",
                dry_run=False,
                store_result_fn=lambda r: store.update(r),
            )

        assert store["trashed_count"] == 700  # 500 + 200

    # Test that when run_move_to_trash is called with dry_run=True, it reports the count without calling batchModify
    async def test_dry_run_reports_count_without_calling_batch_modify(self):
        svc = MagicMock()
        svc.users.return_value.messages.return_value.list.return_value.execute.return_value = {
            "messages": [{"id": f"msg{i}"} for i in range(20)],
        }
        store: dict = {}

        with patch(
            "app.services.gmail_move_to_trash._execute_with_backoff",
            side_effect=lambda req: req.execute(),
        ):
            await run_move_to_trash(
                service=svc,
                queue=asyncio.Queue(),
                sender_email="s@s.com",
                dry_run=True,
                store_result_fn=lambda r: store.update(r),
            )

        assert store["dry_run"] is True
        assert store["trashed_count"] == 20
        svc.users.return_value.messages.return_value.batchModify.assert_not_called()

    # Test that run_move_to_trash emits an "error" event when batchModify raises a hard failure
    async def test_emits_error_when_batch_modify_fails(self):
        from googleapiclient.errors import HttpError

        svc = MagicMock()
        svc.users.return_value.messages.return_value.list.return_value.execute.return_value = {
            "messages": [{"id": f"msg{i}"} for i in range(10)]
        }
        svc.users.return_value.messages.return_value.batchModify.return_value.execute.side_effect = HttpError(
            resp=MagicMock(status=429), content=b"rateLimitExceeded"
        )

        q: asyncio.Queue = asyncio.Queue()
        with patch(
            "app.services.gmail_move_to_trash._execute_with_backoff",
            side_effect=lambda req: req.execute(),
        ):
            await run_move_to_trash(
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
