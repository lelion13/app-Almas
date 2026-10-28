from datetime import datetime

from pydantic import BaseModel


class GbpStatusResponse(BaseModel):
    connected: bool
    google_account_email: str | None = None
    token_last4: str | None = None
    connected_at: datetime | None = None
    location_configured: bool


class GbpOAuthStartResponse(BaseModel):
    authorization_url: str
