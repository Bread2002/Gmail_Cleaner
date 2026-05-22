from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Google OAuth credentials
    google_client_id: str
    google_client_secret: str
    google_project_id: str
    google_redirect_uri: str = "http://localhost:5173/auth/callback"

    # CORS
    frontend_origin: str = "http://localhost:5173"

    # Session management
    session_ttl_seconds: int = 3600

    # Gmail OAuth scopes
    # https://mail.google.com/ is required for messages.batchDelete (permanent deletion).
    # Users who authenticated under the old gmail.modify scope will be prompted
    # to re-authorise once; after that the refresh token covers all scopes silently.
    gmail_scopes: List[str] = [
        "https://mail.google.com/",
        "https://www.googleapis.com/auth/gmail.settings.basic",
        "https://www.googleapis.com/auth/gmail.settings.sharing",
        "https://www.googleapis.com/auth/userinfo.email",
        "openid",
    ]

    @property
    def google_auth_config(self) -> dict:
        """Build the client config dict for google_auth_oauthlib.flow.Flow."""
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


# Singleton instance — import this throughout the app
settings = Settings()  # type: ignore[call-arg]
