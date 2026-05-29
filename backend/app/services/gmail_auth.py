# Copyright (c) 2026, Rye Stahle-Smith; All rights reserved.
# Gmail Cleaner
# Last Updated: May 28th, 2026
# Description: Implements the authentication service using Google OAuth 2.0.

# Import necessary libraries and modules
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

import logging

from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
import google.auth.transport.requests

from app.config import settings
from app import store

# Initialize logging for this module
log = logging.getLogger("gmail_cleaner.auth")


# Define a helper function to build the Google OAuth authorization URL and generate an OAuth flow
async def build_authorization_url() -> tuple[str, str]:
    flow = Flow.from_client_config(
        settings.google_auth_config,
        scopes=settings.gmail_scopes,
        redirect_uri=settings.google_redirect_uri,
    )

    state = secrets.token_urlsafe(32)
    log.info("Building OAuth authorization URL (state=%s…)", state[:8])
    auth_url, _ = flow.authorization_url(
        access_type="offline",  # Request refresh_token
        include_granted_scopes="true",
        prompt="consent",  # Always show consent screen so refresh_token is returned
        state=state,
    )

    # Store a TTL-bound existence marker for this state in Redis; flow is rebuilt on retrieval
    expiry = datetime.now(timezone.utc) + timedelta(minutes=10)
    await store.session.store_state(state, flow, expiry)

    return auth_url, state


# Define a helper function to exchange an authorization code for tokens and return a Credentials object
async def exchange_code(code: str, state: str) -> Credentials:
    log.info("Exchanging OAuth code for tokens (state=%s…)", state[:8])
    flow: Flow | None = await store.session.pop_state(state)
    if flow is None:
        log.warning("OAuth state not found or expired: %s…", state[:8])
        raise ValueError("Invalid or expired OAuth state parameter")

    # Exchange code for tokens
    flow.fetch_token(code=code)
    log.info("OAuth token exchange successful")
    return flow.credentials


# Define a helper function to refresh the access token if it has expired (returns updated credentials)
def refresh_if_expired(credentials: Credentials) -> Credentials:
    if credentials.expired and credentials.refresh_token:
        log.info("Access token expired — refreshing…")
        request = google.auth.transport.requests.Request()
        credentials.refresh(request)
        log.info("Token refreshed successfully")
    return credentials


# Define a helper function to fetch the authenticated user's email address using the credentials
def get_user_email(credentials: Credentials) -> str:
    import urllib.request
    import json

    req = urllib.request.Request(
        "https://www.googleapis.com/oauth2/v3/userinfo",
        headers={"Authorization": f"Bearer {credentials.token}"},
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
    return data.get("email", "unknown@gmail.com")
