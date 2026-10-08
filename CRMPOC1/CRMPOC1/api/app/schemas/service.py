from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

SERVICE_STATUSES = (
    "New",
    "Service Team Review",
    "Admin Review Document",
    "Assigned",
    "Engineer Visit",
    "Serial Verification Review",
    "Serial Verified",
    "Pending Service Approval",
    "Approved for Service",
    "Service In Progress",
    "Service Completed",
    "Completion Pending Approval",
    "Waiting for Part",
    "Customer Not Available",
    "Payment Requested",
    "Payment Completed",
    "Closed",
    "Rejected",
    "Cancelled",
)
SERVICE_TYPES = ("Free Service", "Warranty Service", "Paid Service")
WARRANTY_STATUSES = ("IN WARRANTY", "OUT OF WARRANTY")


class ServiceCreate(BaseModel):
    request_date: date | None = None
    query_type: str = "Service"
    customer_name: str = Field(min_length=1, max_length=255)
    customer_mobile: str = Field(min_length=10, max_length=20)
    customer_email: EmailStr | None = None
    customer_address: str | None = None
    model_details: str | None = Field(default=None, max_length=255)
    problem_description: str | None = None
    additional_remarks: str | None = None
    send_request_number: bool = True

    @field_validator("customer_mobile")
    @classmethod
    def _digits_only(cls, v: str) -> str:
        digits = "".join(ch for ch in v if ch.isdigit())
        if len(digits) < 10:
            raise ValueError("Customer mobile must contain at least 10 digits")
        return digits


class ServiceUpdate(BaseModel):
    customer_name: str | None = None
    customer_mobile: str | None = None
    customer_email: EmailStr | None = None
    customer_address: str | None = None
    model_details: str | None = None
    problem_description: str | None = None
    additional_remarks: str | None = None


class ServiceIdentifyCustomer(BaseModel):
    order_id: int | None = None
    order_item_id: int | None = None
    customer_name: str | None = None
    customer_mobile: str | None = None
    customer_email: str | None = None
    customer_address: str | None = None


class ServiceDeskUserAssignIn(BaseModel):
    service_user_id: int
    remarks: str | None = None


class ServiceDeskReturnIn(BaseModel):
    remarks: str | None = None


class ServiceAssignmentIn(BaseModel):
    assignee_type: Literal["engineer", "vendor"]
    assignee_id: int
    remarks: str | None = None


class ServiceVerifyOrderIn(BaseModel):
    order_id: int | None = None
    order_no: str | None = Field(default=None, min_length=1, max_length=100)
    serial_no: str | None = Field(default=None, min_length=1, max_length=100)


class ServiceAssignUnitsIn(BaseModel):
    unit_ids: list[int] = Field(min_length=1)
    engineer_id: int
    remarks: str | None = None
    billing_type: Literal["Free", "Paid"] | None = "Free"


class ServiceAssignUnitsByQuantityIn(BaseModel):
    item_code: str = Field(min_length=1, max_length=100)
    quantity: int = Field(gt=0)
    engineer_id: int
    remarks: str | None = None
    billing_type: Literal["Free", "Paid"] | None = "Free"


class ServiceAddUnitBySerialIn(BaseModel):
    serial_no: str = Field(min_length=1, max_length=100)
    engineer_id: int | None = None
    billing_type: Literal["Free", "Paid"] | None = "Free"
    remarks: str | None = None


class ServiceUnitBillingIn(BaseModel):
    unit_id: int | None = None
    billing_type: Literal["Free", "Paid"]


class ServiceOrderItemSummary(BaseModel):
    id: int
    item_code: str
    item_name: str | None
    ordered_quantity: int
    installed_quantity: int = 0
    pending_installation_quantity: int = 0
    serial_count: int
    serial_labels: list[str] = []
    units_count: int
    serials_available_count: int
    assigned_count: int
    unassigned_count: int


class ServiceRequestUnitOut(BaseModel):
    id: int
    service_request_item_id: int
    order_item_id: int | None
    item_code: str
    item_name: str | None
    serial_count: int
    serial_labels: list[str] = []
    serial_values: list[str | None] = []
    serial_no: str | None
    serial_no_2: str | None
    assigned_engineer_id: int | None
    assigned_engineer_name: str | None = None
    assigned_at: datetime | None
    serial_verified_at: datetime | None = None
    warranty_status: str | None = None
    part_warranty_status: str | None = None
    free_service_count: int | None = None
    paid_service_count: int | None = None
    admin_billing_type: str | None = None
    service_type: str | None = None
    observation_id: int | None = None
    problem_found: str | None = None
    observation_text: str | None = None
    recommended_action: str | None = None
    parts_required: list[str] = []
    estimated_service_charge: float | None = None
    estimated_parts_charge: float | None = None
    observation_remarks: str | None = None
    observation_submitted_at: datetime | None = None
    unit_status: str = "Assigned"
    serial_not_in_order: bool = False
    return_remarks: str | None = None
    approval_id: int | None = None
    approval_decision: str | None = None
    completion_id: int | None = None
    work_performed: str | None = None
    final_amount: float | None = None
    completion_proof_path: str | None = None
    completed_at: datetime | None = None
    engineer_completion_code: str | None = None
    payment_request_id: int | None = None
    payment_status: str | None = None
    payment_type: str | None = None
    total_requested_amount: float | None = None
    approved_amount: float | None = None
    payment_qr_code_path: str | None = None
    payment_proof_file_path: str | None = None
    payment_approval_status: str | None = None
    payment_approval_stage: str | None = None
    payment_approval_stage_label: str | None = None
    payment_approval_step: int | None = None
    payment_approval_total_steps: int | None = None
    payment_next_approver_role: str | None = None


class ServiceSerialVerifyIn(BaseModel):
    serial_no: str | None = Field(default=None, max_length=100)
    serial_no_2: str | None = Field(default=None, max_length=100)
    unit_id: int | None = None


class ServiceSerialMismatchReturnIn(BaseModel):
    unit_id: int
    scanned_serial_no: str = Field(min_length=1, max_length=100)
    remarks: str | None = Field(default=None, max_length=500)


class ServiceSerialReviewIn(BaseModel):
    unit_id: int
    decision: str
    remarks: str | None = None
    serial_no: str | None = Field(default=None, max_length=100)
    serial_no_2: str | None = Field(default=None, max_length=100)
    associate_serial_with_order: bool = False
    billing_type: Literal["Free", "Paid"] | None = None


class ServiceBulkSerialVerifyIn(BaseModel):
    unit_ids: list[int] | None = None


class ServiceObservationIn(BaseModel):
    unit_id: int | None = None
    problem_found: str | None = None
    observation: str | None = None
    recommended_action: str | None = None
    parts_required: list[str] = []
    estimated_service_charge: float | None = None
    estimated_parts_charge: float | None = None
    remarks: str | None = None


class ServiceBulkObservationsIn(BaseModel):
    observations: list[ServiceObservationIn] = Field(min_length=1)


class ServiceObservationCancelIn(BaseModel):
    unit_id: int | None = None


class EngineerAssignedUnitGroup(BaseModel):
    service_request_id: int
    request_no: str
    order_no: str | None
    customer_name: str
    customer_address: str | None
    problem_description: str | None
    status: str
    item_code: str
    item_name: str | None
    serial_count: int
    serial_labels: list[str] = []
    assigned_quantity: int
    units: list[dict]


class ServiceApprovalIn(BaseModel):
    decision: Literal["Approve", "Reject"]
    remarks: str | None = None
    unit_id: int | None = None


class ServiceBulkApprovalIn(BaseModel):
    decision: Literal["Approve", "Reject"]
    remarks: str | None = None
    unit_ids: list[int] | None = None


class ServiceCompletionIn(BaseModel):
    unit_id: int | None = None
    work_performed: str | None = None
    parts_replaced: list[str] = []
    service_notes: str | None = None
    service_date: date | None = None
    old_part_serial_no: str | None = None
    new_part_serial_no: str | None = None
    final_amount: float | None = None
    completion_remarks: str | None = None
    engineer_completion_code: str | None = None
    completion_status: str = "Service Completed"


class ServicePaymentRequestIn(BaseModel):
    unit_id: int | None = None
    customer_charge_amount: float | None = None
    settlement_service_amount: float | None = None
    settlement_parts_amount: float | None = None
    total_requested_amount: float | None = None
    payment_type: str | None = None
    payment_qr_code_path: str | None = None
    remarks: str | None = None


class ServiceDocumentReviewIn(BaseModel):
    status: Literal["Reviewed", "Rejected"]
    remarks: str | None = None


class ServiceDocumentLinkOut(BaseModel):
    service_request_id: int
    upload_url: str
    customer_email: str | None
    document_request_sent_at: datetime | None
    status: str


class ServicePublicDocumentContext(BaseModel):
    service_request_id: int
    request_no: str
    customer_name: str
    customer_email: str | None
    model_details: str | None
    order_no: str | None = None
    serial_no: str | None = None
    serial_no_locked: bool = False
    problem_description: str | None
    required_documents: list[str] = []
    status: str


class ServiceHistoryEntry(BaseModel):
    id: int
    action: str
    old_status: str | None
    new_status: str | None
    performed_by: int | None
    performed_by_name: str | None = None
    performed_role: str | None = None
    remarks: str | None = None
    metadata: dict | None = None
    created_at: datetime


class ServiceDocumentOut(BaseModel):
    id: int
    document_type: str
    file_path: str
    uploaded_by_type: str
    uploaded_by_user_id: int | None
    uploaded_by_customer_name: str | None
    status: str
    reviewed_by: int | None
    reviewed_by_name: str | None = None
    reviewed_at: datetime | None
    review_remarks: str | None
    uploaded_at: datetime


class ServiceObservationOut(BaseModel):
    id: int
    service_request_unit_id: int | None = None
    submitted_by_user_id: int | None
    submitted_by_name: str | None = None
    serial_no: str | None
    warranty_status: str | None
    service_type: str | None
    problem_found: str | None
    observation: str | None
    recommended_action: str | None
    parts_required: list[str] = []
    estimated_service_charge: float | None
    estimated_parts_charge: float | None
    remarks: str | None
    submitted_at: datetime


class ServiceApprovalOut(BaseModel):
    id: int
    observation_id: int | None
    decision: str
    remarks: str | None
    approved_by: int | None
    approved_by_name: str | None = None
    approved_at: datetime


class ServiceCompletionOut(BaseModel):
    id: int
    performed_by_type: str
    performed_by_user_id: int | None
    performed_by_name: str | None = None
    performed_by_vendor_id: int | None
    performed_by_vendor_name: str | None = None
    work_performed: str | None
    parts_replaced: list[str] = []
    service_notes: str | None
    service_date: date | None
    old_part_serial_no: str | None = None
    new_part_serial_no: str | None = None
    customer_acknowledgement_path: str | None
    final_amount: float | None
    completion_remarks: str | None
    engineer_completion_code: str | None = None
    completed_at: datetime


class ServicePaymentRequestOut(BaseModel):
    id: int
    requested_by_type: str
    requested_by_user_id: int | None
    requested_by_name: str | None = None
    requested_by_vendor_id: int | None
    requested_by_vendor_name: str | None = None
    service_type: str | None
    customer_charge_amount: float | None
    settlement_service_amount: float | None
    settlement_parts_amount: float | None
    total_requested_amount: float | None
    payment_type: str | None
    payment_qr_code_path: str | None = None
    payment_proof_file_path: str | None = None
    approved_amount: float | None = None
    remarks: str | None
    status: str
    approval_status: str | None = None
    approval_stage: str | None = None
    approval_stage_label: str | None = None
    approval_step: int | None = None
    approval_total_steps: int | None = None
    next_approver_role: str | None = None
    processed_at: datetime | None
    processed_by_user_id: int | None = None
    processed_by_name: str | None = None
    payment_transaction_id: int | None = None
    created_at: datetime


class ServicePaymentCompleteIn(BaseModel):
    approved_amount: float
    payment_type: str | None = None
    remarks: str | None = None
    unit_id: int | None = None
    decision: Literal["Approved", "Rejected"] = "Approved"


class AdminServicePaymentUpdate(BaseModel):
    approved_amount: float | None = None
    total_requested_amount: float | None = None
    customer_charge_amount: float | None = None
    settlement_service_amount: float | None = None
    settlement_parts_amount: float | None = None
    payment_type: str | None = None
    remarks: str | None = None


class ServiceNotificationOut(BaseModel):
    id: int
    service_request_id: int
    title: str
    message: str
    notification_type: str
    is_read: bool
    created_at: datetime


class ServiceAssignmentOut(BaseModel):
    id: int
    assignee_type: str
    assignee_user_id: int | None
    assignee_user_name: str | None = None
    assignee_vendor_id: int | None
    assignee_vendor_name: str | None = None
    assigned_by: int | None
    assigned_by_name: str | None = None
    assigned_at: datetime
    remarks: str | None
    is_active: bool


class PaymentApprovalLogOut(BaseModel):
    id: int
    module: str
    entity_id: int
    service_payment_request_id: int | None = None
    stage_key: str
    stage_label: str
    stage_level: int
    total_stages: int
    decision: str
    approved_by_user_id: int | None = None
    approved_by_name: str | None = None
    approver_role: str | None = None
    remarks: str | None = None
    created_at: datetime


class ServiceOut(BaseModel):
    id: int
    request_no: str
    request_date: date
    query_type: str
    customer_name: str
    customer_mobile: str
    customer_email: str | None
    customer_address: str | None
    model_details: str | None
    problem_description: str | None
    additional_remarks: str | None
    status: str
    status_date: datetime | None
    source: str
    created_by: int | None
    created_by_name: str | None = None
    complaint_id: int | None = None
    complaint_no: str | None = None
    order_id: int | None
    order_item_id: int | None
    order_no: str | None = None
    serial_no: str | None
    pcb_warranty_date: date | None = None
    component_warranty_date: date | None = None
    machine_warranty_date: date | None = None
    service_type: str | None
    warranty_status: str | None
    assigned_engineer_id: int | None
    assigned_engineer_name: str | None = None
    assigned_service_user_id: int | None = None
    assigned_service_user_name: str | None = None
    assigned_vendor_id: int | None
    assigned_vendor_name: str | None = None
    requires_documents: bool
    ask_for_documents: bool
    document_request_sent_at: datetime | None
    document_access_token: str | None
    upload_url: str | None = None
    customer_identified_at: datetime | None
    approved_at: datetime | None
    completed_at: datetime | None
    closed_at: datetime | None
    completion_code: str | None = None
    created_at: datetime
    updated_at: datetime
    documents: list[ServiceDocumentOut] = []
    assignments: list[ServiceAssignmentOut] = []
    observations: list[ServiceObservationOut] = []
    approvals: list[ServiceApprovalOut] = []
    completions: list[ServiceCompletionOut] = []
    payment_requests: list[ServicePaymentRequestOut] = []
    payment_approval_history: list[PaymentApprovalLogOut] = []
    order_items: list[ServiceOrderItemSummary] = []
    units: list[ServiceRequestUnitOut] = []
    required_document_types: list[str] = []
    customer_documents_approved: bool = False
    email_bounced: bool = False
    email_bounce_reason: str | None = None


class ServiceListItem(BaseModel):
    id: int
    request_no: str
    request_date: date
    customer_name: str
    customer_mobile: str
    order_no: str | None = None
    serial_no: str | None = None
    status: str
    service_type: str | None = None
    warranty_status: str | None = None
    assigned_engineer_name: str | None = None
    assigned_service_user_name: str | None = None
    assigned_vendor_name: str | None = None
    requires_documents: bool
    document_count: int = 0
    complaint_id: int | None = None
    complaint_no: str | None = None
    created_at: datetime
    email_bounced: bool = False
    email_bounce_reason: str | None = None


class ServiceListResponse(BaseModel):
    items: list[ServiceListItem]
    total: int
    page: int
    per_page: int


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
    unread_notifications: int = 0
