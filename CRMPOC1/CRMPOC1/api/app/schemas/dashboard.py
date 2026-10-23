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


class ServiceSummary(BaseModel):
    new_requests: int
    unassigned: int
    assigned: int
    pending_observation: int
    pending_approval: int
    approved: int
    in_progress: int
    payment_pending: int
    completed: int
    closed: int
