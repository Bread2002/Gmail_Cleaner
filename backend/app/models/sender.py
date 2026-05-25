# Copyright (c) 2026, Rye Stahle-Smith; All rights reserved.
# Gmail Cleaner
# Last Updated: May 24th, 2026
# Description: Defines Pydantic models for representing flagged senders, scan requests, scan results, and actions like trashing or blocking senders.
#              These models are used for data validation and serialization in the application's API endpoints and services.

# Import necessary libraries and modules
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from enum import Enum


# Define an enumeration model for scan status to represent the different states of a scan process
class ScanStatus(str, Enum):
    pending = "pending"
    running = "running"
    complete = "complete"
    error = "error"


# Define a Pydantic model for representing a flagged sender
class FlaggedSender(BaseModel):
    id: str  # UUID assigned server-side
    email: str
    display_name: Optional[str] = None
    message_count: int  # Total messages from sender
    consecutive_unread_count: int  # Total consecutive unread messages from sender
    snippet: Optional[str] = None  # First-message snippet
    subject: Optional[str] = None  # First-message subject
    first_message_date: Optional[datetime] = None


# Define a Pydantic model for representing a scan request
class ScanRequest(BaseModel):
    dry_run: bool = False
    consecutive_unread_threshold: int = 20
    max_senders: int = 10
    max_messages_per_sender: int = 100


# Define a Pydantic model for representing the response when a scan is started, including the scan ID
class ScanStartResponse(BaseModel):
    scan_id: str


# Define a Pydantic model for representing the results of a scan
class ScanResult(BaseModel):
    scan_id: str
    status: ScanStatus
    dry_run: bool
    senders: List[FlaggedSender] = []
    error: Optional[str] = None


# Define a Pydantic model for representing the response when previewing actions for a sender
class PreviewResponse(BaseModel):
    sender_id: str
    email: str
    subject: Optional[str] = None
    snippet: Optional[str] = None
    date: Optional[datetime] = None


# Define a Pydantic model for representing a request to trash emails from a sender
class TrashRequest(BaseModel):
    dry_run: bool = False


# Define a Pydantic model for representing the response when starting to trash emails from a sender
class TrashStartResponse(BaseModel):
    job_id: str
    sender: str
    estimated_count: int


# Define a Pydantic model for representing the response when starting to block a sender
class BlockResponse(BaseModel):
    filter_id: Optional[str]
    sender: str


# Define a Pydantic model for representing a request when bulk trashing senders
class BulkTrashRequest(BaseModel):
    sender_ids: List[str]
    dry_run: bool = False


# Define a Pydantic model for representing the response when bulk trashing senders
class BulkTrashResponse(BaseModel):
    jobs: List[dict]


# Define a Pydantic model for representing a request when bulk blocking senders
class BulkBlockRequest(BaseModel):
    sender_ids: List[str]


# Define a Pydantic model for representing the response when bulk blocking senders
class BulkBlockResponse(BaseModel):
    blocked: List[str]
    failed: List[str]


# Define a Pydantic model for representing a request when bulk skipping senders
class BulkSkipRequest(BaseModel):
    sender_ids: List[str]


# Define a Pydantic model for representing the response when bulk skipping senders
class BulkSkipResponse(BaseModel):
    skipped: List[str]
    failed: List[str]
