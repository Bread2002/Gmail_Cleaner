"""
Set required environment variables before any app module is imported.
`conftest.py` is executed by pytest before test collection, so these values
are in place when `app.config.Settings()` runs at module-load time.
Real credentials are never needed in tests — the Gmail API is always mocked.
"""

import os

os.environ.setdefault("GOOGLE_CLIENT_ID", "test-client-id")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test-client-secret")
os.environ.setdefault("GOOGLE_PROJECT_ID", "test-project-id")
