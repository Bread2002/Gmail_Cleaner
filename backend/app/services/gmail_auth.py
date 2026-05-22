"""
Web OAuth 2.0 flow — replaces InstalledAppFlow from original main.py.

Key difference from original: uses Flow (not InstalledAppFlow), redirects
the user's browser to Google and back to the frontend callback page.
The backend never opens a local port.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

import logging

from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
import google.auth.transport.requests

from app.config import settings
from app import store

log = logging.getLogger("gmail_cleaner.auth")


def build_authorization_url() -> tuple[str, str]:
    """
    Create a new OAuth Flow, generate a state nonce, persist the Flow,
    and return (authorization_url, state).

    The caller returns auth_url to the frontend which redirects window.location.
    """
    flow = Flow.from_client_config(
        settings.google_auth_config,
        scopes=settings.gmail_scopes,
        redirect_uri=settings.google_redirect_uri,
    )

    state = secrets.token_urlsafe(32)
    log.info("Building OAuth authorization URL (state=%s…)", state[:8])
    auth_url, _ = flow.authorization_url(
        access_type="offline",  # request refresh_token
        include_granted_scopes="true",
        prompt="consent",  # always show consent screen so refresh_token is returned
        state=state,
    )

    # Store the Flow object keyed by state nonce (expires in 10 minutes)
    expiry = datetime.now(timezone.utc) + timedelta(minutes=10)
    store.session.store_state(state, flow, expiry)

    return auth_url, state


def exchange_code(code: str, state: str) -> Credentials:
    """
    Validate the state nonce, exchange the authorization code for tokens,
    and return a google.oauth2.credentials.Credentials object.

    Raises ValueError if state is invalid or expired.
    """
    log.info("Exchanging OAuth code for tokens (state=%s…)", state[:8])
    flow: Flow | None = store.session.pop_state(state)
    if flow is None:
        log.warning("OAuth state not found or expired: %s…", state[:8])
        raise ValueError("Invalid or expired OAuth state parameter")

    # Exchange code for tokens
    flow.fetch_token(code=code)
    log.info("OAuth token exchange successful")
    return flow.credentials


def refresh_if_expired(credentials: Credentials) -> Credentials:
    """
    Refresh the access token if it has expired (or is about to).
    Returns the (potentially updated) credentials.
    """
    if credentials.expired and credentials.refresh_token:
        log.info("Access token expired — refreshing…")
        request = google.auth.transport.requests.Request()
        credentials.refresh(request)
        log.info("Token refreshed successfully")
    return credentials


def get_user_email(credentials: Credentials) -> str:
    """
    Fetch the authenticated user's email address via the OAuth2 userinfo endpoint.
    """
    import urllib.request
    import json

    req = urllib.request.Request(
        "https://www.googleapis.com/oauth2/v3/userinfo",
        headers={"Authorization": f"Bearer {credentials.token}"},
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
    return data.get("email", "unknown@gmail.com")
