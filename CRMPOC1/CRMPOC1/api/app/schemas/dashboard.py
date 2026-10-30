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
    payee_id: int | None = None  # User.id (Engineer) or Vendor.id -- what a pooled payment groups by
    payment_request_id: int | None = None  # ServicePaymentRequest.id -- unambiguous ref for a bulk pay (service only)
    requested_at: datetime | None = None
    amount: float
    days_waiting: int
    urgency: str  # "urgent" | "soon" | "ontime"
    href: str


class BulkPayResult(BaseModel):
    paid: int
    total_amount: float


class InstallationPaymentStageOut(BaseModel):
    stage_key: str
    stage_label: str
    count: int
    amount: float
    is_mine: bool = False


class PaymentQueueItem(BaseModel):
    module: str  # "installation" | "service"
    entity_id: int
    label: str
    customer_name: str | None = None
    engineer_name: str | None = None
    amount: float
    payment_type: str | None = None
    requested_at: datetime | None = None
    days_waiting: int
    urgency: str  # "urgent" | "soon" | "ontime"
    stage_key: str
    stage_label: str
    next_stage_label: str | None = None  # None only at the final (admin) stage
    last_action: str | None = None  # e.g. "Forwarded by Mohit SVM" -- None if nobody has acted yet
    href: str
    actionable: bool = True  # False for service rows with more than one unit -- open the record instead


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
