from datetime import datetime

from pydantic import BaseModel


class ComplaintsSummary(BaseModel):
    pending: int
    resolved: int
    under_process: int
    rejected: int
    in_process: int


class InstallationSummary(BaseModel):
    total_pending: int
    gt7days: int
    gt15days: int
    gt30days: int
    stages: dict[str, int] = {}  # installation requests in each stage


class ComplaintChartPoint(BaseModel):
    month: str
    pending: int
    resolved: int
    under_process: int
    rejected: int
    in_process: int


class ComplaintChart(BaseModel):
    points: list[ComplaintChartPoint]


class OrdersSummary(BaseModel):
    total: int
    pending: int
    in_transit: int
    delivered: int


class ReadyToPayItem(BaseModel):
    module: str  # "installation" | "service"
    entity_id: int
    label: str
    payee_name: str | None = None
    payee_type: str | None = None  # "Engineer" | "Vendor"
    requested_at: datetime | None = None
    amount: float
    days_waiting: int
    urgency: str  # "urgent" | "soon" | "ontime"
    href: str


class InstallationPaymentStageOut(BaseModel):
    stage_key: str
    stage_label: str
    count: int
    amount: float
    is_mine: bool = False


class ServiceSummary(BaseModel):
    new_requests: int
    unassigned: int
    assigned: int
    pending_observation: int
    pending_approval: int
    completion_pending_approval: int = 0
    approved: int
    in_progress: int
    payment_pending: int
    completed: int
    closed: int
