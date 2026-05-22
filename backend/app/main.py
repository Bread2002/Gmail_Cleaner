"""
Gmail Cleaner — FastAPI application entry point.
"""

import logging
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, scan, senders, settings as settings_router

# ---------------------------------------------------------------------------
# Logging — structured, goes to stdout so uvicorn captures it
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)

# Quiet noisy third-party libraries
logging.getLogger("googleapiclient.discovery").setLevel(logging.WARNING)
logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.WARNING)
logging.getLogger("google.auth").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("httplib2").setLevel(logging.WARNING)

log = logging.getLogger("gmail_cleaner")

app = FastAPI(
    title="Gmail Cleaner API",
    description="Backend API for the Gmail Cleaner web application",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(auth.router)
app.include_router(scan.router)
app.include_router(senders.router)
app.include_router(settings_router.router)


@app.get("/health", tags=["meta"])
async def health() -> dict:
    return {"status": "ok"}
