# Copyright (c) 2026, Rye Stahle-Smith; All rights reserved.
# Gmail Cleaner
# Last Updated: May 24th, 2026
# Description: FastAPI backend for the Gmail Cleaner web application.
#              Provides endpoints for authentication, scanning, sender management, and user settings.

# Import necessary libraries and modules
import logging
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, scan, senders, settings as settings_router

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)

# Reduce noise from third-party libraries
logging.getLogger("googleapiclient.discovery").setLevel(logging.WARNING)
logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.WARNING)
logging.getLogger("google.auth").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("httplib2").setLevel(logging.WARNING)

# Create a logger for the application
log = logging.getLogger("gmail_cleaner")

# Initialize the FastAPI application
app = FastAPI(
    title="Gmail Cleaner API",
    description="Backend API for the Gmail Cleaner web application",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS middleware to allow requests from the frontend origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers for various functionalities
app.include_router(auth.router)
app.include_router(scan.router)
app.include_router(senders.router)
app.include_router(settings_router.router)


# Define a simple health check endpoint
@app.get("/health", tags=["meta"])
async def health() -> dict:
    """Health check endpoint to verify that the API is running."""
    return {"status": "ok"}
