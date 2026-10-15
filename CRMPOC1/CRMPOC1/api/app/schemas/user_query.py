from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator

CATEGORIES = ("General", "Order", "Service request", "Installation", "Complaint", "Payment", "Bid", "App or login", "Other")


def _text(value: str) -> str:
    return "\n".join(line.rstrip() for line in (value or "").strip().splitlines())


def _serial(value) -> str | None:
    value = " ".join(str(value or "").split())
    return value or None


def _query_date(value):
    if value in ("", None):
        return None
    parsed = value if isinstance(value, date) else date.fromisoformat(str(value)[:10])
    if not 2000 <= parsed.year <= 2100:
        raise ValueError("Choose a real date")
    return parsed


class QueryDetailsIn(BaseModel):
    """Serial number and date of a query, changed later."""

    serial_no: str | None = Field(None, max_length=100)
    query_date: date | None = None

    @field_validator("serial_no")
    @classmethod
    def _serial_no(cls, v):
        return _serial(v)

    @field_validator("query_date", mode="before")
    @classmethod
    def _query_date(cls, v):
        return _query_date(v)


class QueryCreate(BaseModel):
    subject: str = Field(min_length=1, max_length=200)
    category: str = "General"
    related_to: str | None = Field(None, max_length=200)
    serial_no: str | None = Field(None, max_length=100)
    query_date: date | None = None
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

    @field_validator("serial_no")
    @classmethod
    def _serial_no(cls, v):
        return _serial(v)

    @field_validator("query_date", mode="before")
    @classmethod
    def _query_date(cls, v):
        return _query_date(v)


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
    is_private: bool = False  # sent while someone was taken out of the conversation
    hidden_from: list[str] = []  # for the Admin team: who it was kept from


class QueryMemberOut(BaseModel):
    user_id: int
    name: str | None = None
    role: str | None = None
    kind: str = "member"  # owner | member | cc
    active: bool = True
    is_holder: bool = False
    joined_at: datetime
    left_at: datetime | None = None


class QueryEventOut(BaseModel):
    id: int
    kind: str
    text: str
    by_name: str | None = None
    at: datetime


class QueryPerson(BaseModel):
    id: int
    name: str
    role: str | None = None


class ForwardIn(BaseModel):
    to_user_id: int
    note: str = Field("", max_length=1000)


class MemberIn(BaseModel):
    user_id: int
    kind: str = "member"  # member | cc
    share_history: bool = True

    @field_validator("kind")
    @classmethod
    def _kind(cls, v):
        return v if v in ("member", "cc") else "member"


class PriorityIn(BaseModel):
    priority: str

    @field_validator("priority")
    @classmethod
    def _priority(cls, v):
        if v not in ("normal", "high", "urgent"):
            raise ValueError("Choose normal, high or urgent")
        return v


class QueryListItem(BaseModel):
    id: int
    subject: str
    category: str
    related_to: str | None = None
    serial_no: str | None = None
    query_date: date | None = None
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
    priority: str = "normal"
    holder_id: int | None = None
    holder_name: str | None = None
    holder_role: str | None = None
    hours_left: float | None = None  # before the 24 hour alarm, while it waits for an answer
    overdue: bool = False
    alarm_for_me: bool = False  # the alarm is ringing for the person looking
    member_count: int = 0


class QueryDetail(QueryListItem):
    messages: list[QueryMessageOut] = []
    members: list[QueryMemberOut] = []
    events: list[QueryEventOut] = []
    can_reply: bool = True
    can_close: bool = True
    can_reopen: bool = False
    can_forward: bool = False
    can_manage: bool = False  # add, CC or take people out
    can_set_priority: bool = False
    can_ring: bool = False
    can_see_history: bool = False
    can_edit_details: bool = False  # serial number and date: Admin, Sub Admin and the person who raised it
    alarm_count: int = 0
    private_now: bool = False  # someone is out, so new messages are private


class QuerySummary(BaseModel):
    open: int = 0  # staff: waiting for an answer; others: not yet closed
    answered: int = 0
    closed: int = 0
    unread: int = 0  # threads with something new for me
    staff: bool = False
    alarms: int = 0  # queries whose 24 hour alarm is ringing for me
