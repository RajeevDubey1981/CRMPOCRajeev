from datetime import date, datetime

from pydantic import BaseModel


class EmailSendLogOut(BaseModel):
    id: int
    to_email: str
    from_email: str | None
    subject: str
    template: str | None
    status: str
    skip_reason: str | None
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class EmailSendLogListResponse(BaseModel):
    items: list[EmailSendLogOut]
    total: int
    page: int
    per_page: int


class EmailSendLogSummary(BaseModel):
    sent: int
    failed: int
    skipped: int
    total_attempts: int
    date_from: date | None = None
    date_to: date | None = None
