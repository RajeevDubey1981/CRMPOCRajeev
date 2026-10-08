from datetime import datetime

from pydantic import BaseModel, Field, field_validator

CATEGORIES = ("General", "Order", "Service request", "Installation", "Complaint", "Payment", "Bid", "App or login", "Other")


def _text(value: str) -> str:
    return "\n".join(line.rstrip() for line in (value or "").strip().splitlines())


class QueryCreate(BaseModel):
    subject: str = Field(min_length=1, max_length=200)
    category: str = "General"
    related_to: str | None = Field(None, max_length=200)
    message: str = Field(min_length=1, max_length=4000)
    to_user_id: int | None = None  # only an Admin / Sub Admin can write to someone first

    @field_validator("subject")
    @classmethod
    def _subject(cls, v):
        v = " ".join(v.split())
        if not v:
            raise ValueError("Write a subject")
        return v

    @field_validator("message")
    @classmethod
    def _message(cls, v):
        v = _text(v)
        if not v:
            raise ValueError("Write your message")
        return v

    @field_validator("category")
    @classmethod
    def _category(cls, v):
        return v if v in CATEGORIES else "General"

    @field_validator("related_to")
    @classmethod
    def _related(cls, v):
        v = " ".join((v or "").split())
        return v or None


class QueryReply(BaseModel):
    body: str = Field(min_length=1, max_length=4000)

    @field_validator("body")
    @classmethod
    def _body(cls, v):
        v = _text(v)
        if not v:
            raise ValueError("Write your message")
        return v


class QueryMessageOut(BaseModel):
    id: int
    sender_id: int
    sender_name: str | None = None
    sender_role: str | None = None
    from_staff: bool = False
    mine: bool = False
    body: str
    created_at: datetime


class QueryListItem(BaseModel):
    id: int
    subject: str
    category: str
    related_to: str | None = None
    status: str
    owner_id: int
    owner_name: str | None = None
    owner_role: str | None = None
    created_at: datetime
    last_message_at: datetime
    last_message_preview: str = ""
    last_sender_name: str | None = None
    message_count: int = 0
    unread_count: int = 0


class QueryDetail(QueryListItem):
    messages: list[QueryMessageOut] = []
    can_reply: bool = True
    can_close: bool = True
    can_reopen: bool = False


class QuerySummary(BaseModel):
    open: int = 0  # staff: waiting for an answer; others: not yet closed
    answered: int = 0
    closed: int = 0
    unread: int = 0  # threads with something new for me
    staff: bool = False
