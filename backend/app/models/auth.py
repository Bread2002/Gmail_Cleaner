# Copyright (c) 2026, Rye Stahle-Smith; All rights reserved.
# Gmail Cleaner
# Last Updated: May 24th, 2026
# Description: Defines Pydantic models for authentication-related structures such as login responses, callback requests and responses, and user information.
#              These models are used for data validation and serialization in the authentication flow of the application.

# Import necessary libraries and modules
from pydantic import BaseModel
from datetime import datetime


# Define a Pydantic models for representing the response when a user initiates the login process
class LoginResponse(BaseModel):
    auth_url: str


# Define a Pydantic model for representing the request payload when Google redirects back to our callback endpoint after authentication
class CallbackRequest(BaseModel):
    code: str
    state: str


# Define a Pydantic model for representing the response from our callback endpoint after processing the authentication response from Google
class CallbackResponse(BaseModel):
    session_token: str
    user_email: str
    expires_at: datetime


# Define a Pydantic model for representing the response when fetching information about the currently authenticated user
class MeResponse(BaseModel):
    email: str
    authenticated: bool
