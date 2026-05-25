# Copyright (c) 2026, Rye Stahle-Smith; All rights reserved.
# Gmail Cleaner
# Last Updated: May 24th, 2026
# Description: CORS configuration and application settings for the Gmail Cleaner backend.

# Import necessary libraries and modules
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import List

# Define the Settings class using Pydantic for environment variable management and validation
class Settings(BaseSettings):
    # Configure Pydantic to read from the .env file
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Configure Google OAuth credentials
    google_client_id: str
    google_client_secret: str
    google_project_id: str
    google_redirect_uri: str = "http://localhost:5173/auth/callback"

    # Configure CORS settings
    frontend_origin: str = "http://localhost:5173"

    # Configure session management
    session_ttl_seconds: int = 3600

    # Configure Gmail OAuth scopes
    gmail_scopes: List[str] = [
        "https://mail.google.com/",
        "https://www.googleapis.com/auth/gmail.settings.basic",
        "https://www.googleapis.com/auth/gmail.settings.sharing",
        "https://www.googleapis.com/auth/userinfo.email",
        "openid",
    ]

    # Build the client config property for authentication flows
    @property
    def google_auth_config(self) -> dict:
        return {
            "web": {
                "client_id": self.google_client_id,
                "project_id": self.google_project_id,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_secret": self.google_client_secret,
                "redirect_uris": [self.google_redirect_uri],
            }
        }

# Define a singleton instance of the Settings class to be used throughout the application
settings = Settings()
