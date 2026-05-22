from pydantic import BaseModel
from datetime import datetime


class LoginResponse(BaseModel):
    auth_url: str


class CallbackRequest(BaseModel):
    code: str
    state: str


class CallbackResponse(BaseModel):
    session_token: str
    user_email: str
    expires_at: datetime


class MeResponse(BaseModel):
    email: str
    authenticated: bool
