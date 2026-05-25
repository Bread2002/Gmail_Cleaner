# Copyright (c) 2026, Rye Stahle-Smith; All rights reserved.
# Gmail Cleaner
# Last Updated: May 24th, 2026
# Description: Defines Pydantic models for user settings and settings updates, including validation rules and default values.
#              These models are used for storing user preferences and handling settings update requests in the application.

# Import necessary libraries and modules
from pydantic import BaseModel, Field
from typing import Optional


# Define a Pydantic model for user settings with validation rules and default values
class UserSettings(BaseModel):
    consecutive_unread_threshold: int = Field(
        default=20,
        ge=1,
        le=500,
        description="Number of consecutive unread emails before a sender is flagged",
    )
    max_senders: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of flagged senders to find per scan",
    )
    max_messages_per_sender: int = Field(
        default=100,
        ge=20,
        le=1000,
        description="Maximum messages to inspect per sender when checking consecutive unread",
    )
    dry_run_by_default: bool = Field(
        default=False, description="When true, actions only preview what would be done"
    )


# Define a Pydantic model for updating user settings, allowing partial updates with optional fields
class SettingsPatch(BaseModel):
    consecutive_unread_threshold: Optional[int] = Field(default=None, ge=1, le=500)
    max_senders: Optional[int] = Field(default=None, ge=1, le=100)
    max_messages_per_sender: Optional[int] = Field(default=None, ge=20, le=1000)
    dry_run_by_default: Optional[bool] = None
