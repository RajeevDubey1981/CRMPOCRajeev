from datetime import datetime
from pydantic import BaseModel, Field


class InstallationCreate(BaseModel):
    customer_name: str
    contact_number: str
    customer_email: str | None = None
    address: str | None = None
    order_item_id: int | None = None
    order_id: int | None = None
    product_name: str | None = None
    request_date: datetime | None = None
    source: str | None = None


class InstallationStatusUpdate(BaseModel):
    customer_name: str | None = None
    contact_number: str | None = None
    address: str | None = None
    product_name: str | None = None
    installation_date: datetime | None = None
    work_report: str | None = None
    status: str | None = None


class AdminInstallationPaymentUpdate(BaseModel):
    payment_amount_requested: float | None = None
    payment_amount_paid: float | None = None
    payment_type_requested: str | None = None
    payment_type_paid: str | None = None


class InstallationBulkUpdateRequest(BaseModel):
    installation_ids: list[int]
    new_status: str
    installation_date: datetime | None = None
    work_report: str | None = None
    payment_amount: float | None = None
    payment_type: str | None = None


class InstallationListItem(BaseModel):
    id: int
    source: str = "vendor"
    order_item_id: int | None = None
    item_code: str | None = None
    customer_name: str
    contact_number: str
    product_name: str | None
    order_no: str | None = None
    vendor_name: str | None = None
    serial_no: str | None = None
    serial_no_2: str | None = None
    status: str
    request_date: datetime
    installation_date: datetime | None
    assigned_engineer: int | None = None
    assigned_engineer_name: str | None
    settlement_approved_by_name: str | None
    payment_amount_requested: float | None = None
    payment_type_requested: str | None = None
    payment_qr_code_path: str | None = None
    payment_qr_code_filename: str | None = None
    payment_proof_file_path: str | None = None
    complaint_id: int | None = None
    complaint_no: str | None = None


class InstallationListResponse(BaseModel):
    items: list[InstallationListItem]
    total: int
    page: int
    per_page: int


class InstallationPaymentHistoryItem(BaseModel):
    id: int
    order_no: str | None = None
    item_code: str | None = None
    customer_name: str
    assigned_engineer_name: str | None = None
    payment_amount_requested: float | None = None
    payment_amount_paid: float | None = None
    payment_type_requested: str | None = None
    payment_type_paid: str | None = None
    payment_recorded_at: datetime | None = None
    payment_recorded_by_name: str | None = None
    installation_date: datetime | None = None
    status: str


class InstallationPaymentHistoryRequestItem(BaseModel):
    id: int
    source_type: str = "installation"
    order_no: str | None = None
    item_code: str | None = None
    customer_name: str
    installation_date: datetime | None = None
    requested_amount: float | None = None
    paid_amount: float | None = None
    status: str


class InstallationPaymentHistoryGroupItem(BaseModel):
    id: int
    payment_type: str
    total_amount: float
    request_count: int
    recorded_at: datetime
    recorded_by_name: str | None = None
    engineer_name: str | None = None
    requests: list[InstallationPaymentHistoryRequestItem]


class InstallationPaymentHistoryResponse(BaseModel):
    items: list[InstallationPaymentHistoryGroupItem]
    total: int
    page: int
    per_page: int


class InstallationEngineerAssignmentOption(BaseModel):
    id: int
    name: str
    email: str
    pending_requests: int = 0
    rating: float = 0.0
    completed_requests: int = 0


class InstallationCompletionProofOut(BaseModel):
    slot: int
    serial_no: str | None = None
    file_path: str | None = None


class InstallationOut(BaseModel):
    id: int
    source: str = "vendor"
    customer_name: str
    contact_number: str
    customer_email: str | None = None
    address: str | None
    order_id: int | None = None
    order_item_id: int | None
    item_code: str | None = None
    product_name: str | None
    order_no: str | None = None
    vendor_name: str | None = None
    serial_no: str | None = None
    serial_no_2: str | None = None
    request_date: datetime
    assigned_engineer: int | None
    assigned_engineer_name: str | None
    status: str
    installation_date: datetime | None
    work_report: str | None
    work_report_file_path: str | None
    work_report_file_path_2: str | None = None
    item_serial_count: int = 1
    completion_proofs: list[InstallationCompletionProofOut] = Field(default_factory=list)
    settlement_approved_by: int | None
    settlement_approved_by_name: str | None
    payment_amount_requested: float | None = None
    payment_type_requested: str | None = None
    payment_qr_code_path: str | None = None
    payment_qr_code_filename: str | None = None
    payment_proof_file_path: str | None = None
    payment_requested_at: datetime | None = None
    payment_amount_paid: float | None = None
    payment_type_paid: str | None = None
    payment_recorded_at: datetime | None = None
    payment_recorded_by: int | None = None
    payment_recorded_by_name: str | None = None
    complaint_id: int | None = None
    complaint_no: str | None = None
    document_upload_url: str | None = None
    document_request_sent_at: datetime | None = None
    order_verified_at: datetime | None = None
    engineer_entered_serial_no: str | None = None
    engineer_entered_serial_no_2: str | None = None
    serial_verified_at: datetime | None = None
    admin_billing_type: str | None = None
    admin_approval_remark: str | None = None
    admin_approved_at: datetime | None = None
    engineer_site_remarks: str | None = None
    engineer_serials_submitted_at: datetime | None = None
    parent_installation_id: int | None = None
    created_at: datetime
    updated_at: datetime


class InstallationDocumentOut(BaseModel):
    id: int
    document_type: str
    file_path: str
    uploaded_by_type: str
    uploaded_by_customer_name: str | None = None
    status: str
    uploaded_at: datetime
    review_remarks: str | None = None


class InstallationHistoryEntry(BaseModel):
    id: int
    action: str
    old_status: str | None
    new_status: str | None
    performed_by_name: str | None = None
    performed_role: str | None = None
    remarks: str | None = None
    metadata_json: str | None = None
    created_at: datetime


class InstallationOrderSearchResult(BaseModel):
    order_id: int
    order_no: str | None = None
    customer_name: str | None = None
    customer_mobile: str | None = None
    customer_email: str | None = None
    customer_address: str | None = None


class InstallationVerifyOrderRequest(BaseModel):
    order_id: int


class InstallationEngineerSerialRequest(BaseModel):
    serial_no: str
    serial_no_2: str | None = None


class InstallationEngineerSerialLine(BaseModel):
    serial_no: str
    serial_no_2: str | None = None
    observation: str | None = None
    unit_status: str | None = None


class InstallationEngineerSerialSubmitRequest(BaseModel):
    status: str | None = None
    site_remarks: str | None = None
    serials: list[InstallationEngineerSerialLine]


class InstallationEngineerSerialOut(BaseModel):
    id: int
    line_no: int
    serial_no: str
    serial_no_2: str | None = None
    observation: str | None = None
    unit_status: str | None = None
    verification_status: str
    admin_remark: str | None = None
    verified_at: datetime | None = None
    submitted_at: datetime | None = None


class InstallationEngineerSerialVerifyLine(BaseModel):
    serial_id: int
    decision: str
    admin_remark: str | None = None
    associate_serial_with_order: bool = False


class InstallationEngineerSerialFinalizeRequest(BaseModel):
    lines: list[InstallationEngineerSerialVerifyLine]
    billing_type: str | None = "Free"
    payment_amount: float | None = None
    overall_remark: str | None = None


class InstallationVerifySerialRequest(BaseModel):
    decision: str  # approve | reject | override
    serial_no: str | None = None
    serial_no_2: str | None = None
    billing_type: str | None = None  # Free | Paid
    payment_amount: float | None = None
    remark: str | None = None
    associate_serial_with_order: bool = False


class InstallationPublicDocumentContext(BaseModel):
    module: str = "installation"
    installation_request_id: int
    request_no: str
    customer_name: str
    customer_email: str | None = None
    model_details: str | None = None
    order_no: str | None = None
    serial_no: str | None = None
    serial_no_locked: bool = False
    problem_description: str | None = None
    required_documents: list[str]
    status: str


class InstallationAssignPair(BaseModel):
    installation_id: int | None = None
    order_item_id: int | None = None
    engineer_id: int


class BulkAssignRequest(BaseModel):
    assignments: list[InstallationAssignPair]


class BulkCancelRequest(BaseModel):
    installation_ids: list[int]
