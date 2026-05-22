from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from enum import Enum


class ScanStatus(str, Enum):
    pending = "pending"
    running = "running"
    complete = "complete"
    error = "error"


class FlaggedSender(BaseModel):
    id: str  # UUID assigned server-side
    email: str
    display_name: Optional[str] = None
    message_count: int  # total messages from sender
    consecutive_unread_count: int  # how many consecutive unread found
    snippet: Optional[str] = None  # first-message snippet
    subject: Optional[str] = None  # first-message subject
    first_message_date: Optional[datetime] = None


class ScanRequest(BaseModel):
    dry_run: bool = False
    consecutive_unread_threshold: int = 20
    max_senders: int = 10
    max_messages_per_sender: int = 100


class ScanStartResponse(BaseModel):
    scan_id: str


class ScanResult(BaseModel):
    scan_id: str
    status: ScanStatus
    dry_run: bool
    senders: List[FlaggedSender] = []
    error: Optional[str] = None


class PreviewResponse(BaseModel):
    sender_id: str
    email: str
    subject: Optional[str] = None
    snippet: Optional[str] = None
    date: Optional[datetime] = None


class TrashRequest(BaseModel):
    dry_run: bool = False


class TrashStartResponse(BaseModel):
    job_id: str
    sender: str
    estimated_count: int


class BlockResponse(BaseModel):
    filter_id: Optional[str]
    sender: str


class BulkTrashRequest(BaseModel):
    sender_ids: List[str]
    dry_run: bool = False


class BulkTrashResponse(BaseModel):
    jobs: List[dict]  # [{sender_id, job_id}]


class BulkBlockRequest(BaseModel):
    sender_ids: List[str]


class BulkBlockResponse(BaseModel):
    blocked: List[str]
    failed: List[str]


class BulkSkipRequest(BaseModel):
    sender_ids: List[str]


class BulkSkipResponse(BaseModel):
    skipped: List[str]
    failed: List[str]
