import logging
import re
import smtplib
from email.message import EmailMessage
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates" / "email"


def _substitute_template(content: str, context: dict) -> str:
    def replace(match: re.Match[str]) -> str:
        key = match.group(1).strip()
        value = context.get(key, "")
        return str(value) if value is not None else ""

    return re.sub(r"\{\{\s*(\w+)\s*\}\}", replace, content)


def _load_template(name: str) -> str:
    path = TEMPLATE_DIR / f"{name}.html"
    if not path.is_file():
        raise FileNotFoundError(f"Email template not found: {path}")
    return path.read_text(encoding="utf-8")


def _from_address() -> str:
    from_email = (settings.smtp_from or settings.smtp_user or "").strip()
    from_name = (settings.smtp_from_name or "").strip()
    if from_name and from_email:
        return f"{from_name} <{from_email}>"
    return from_email


def send_email(to: str, subject: str, html_body: str, text_body: str | None = None) -> bool:
    recipient = (to or "").strip()
    if not recipient:
        logger.warning("send_email skipped: empty recipient")
        return False

    if not settings.email_enabled:
        logger.info("email skipped (EMAIL_ENABLED=false): to=%s subject=%s", recipient, subject)
        return False

    smtp_user = (settings.smtp_user or "").strip()
    smtp_password = (settings.smtp_password or "").strip()
    smtp_from = (settings.smtp_from or smtp_user).strip()
    if not smtp_from:
        logger.error("email failed: SMTP_FROM (or SMTP_USER) must be set when EMAIL_ENABLED=true")
        return False
    if settings.smtp_use_auth and (not smtp_user or not smtp_password):
        logger.error("email failed: SMTP_USER and SMTP_PASSWORD required when SMTP_USE_AUTH=true")
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = _from_address()
    message["To"] = recipient
    if text_body:
        message.set_content(text_body)
        message.add_alternative(html_body, subtype="html")
    else:
        message.set_content(html_body, subtype="html")

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
            smtp.ehlo()
            if settings.smtp_use_tls:
                smtp.starttls()
                smtp.ehlo()
            if settings.smtp_use_auth:
                smtp.login(smtp_user, smtp_password)
            smtp.send_message(message)
        logger.info("email sent: to=%s subject=%s", recipient, subject)
        return True
    except Exception:
        logger.exception("email failed: to=%s subject=%s", recipient, subject)
        return False


def send_template_email(
    to: str,
    template: str,
    context: dict,
    subject: str | None = None,
) -> bool:
    html_body = _substitute_template(_load_template(template), context)
    resolved_subject = subject or context.get("subject") or "Notification from Indcool"
    text_body = context.get("text_body")
    return send_email(to, resolved_subject, html_body, text_body=text_body)


def send_partner_registration_invite_email(
    to: str,
    contact_person_name: str | None,
    firm_name: str | None,
    registration_no: str,
    registration_url: str,
) -> bool:
    recipient_name = (firm_name or contact_person_name or "Partner").strip() or "Partner"
    reference = (registration_no or "your registration").strip()
    subject = f"INDcool partner onboarding invite — {reference}"
    text_body = (
        f"Dear {recipient_name},\n\n"
        "Thank you for partnering with INDcool Electricals Pvt Ltd. We're glad to have you on board.\n\n"
        "To complete your onboarding, kindly upload your credentials and required documents using the link below:\n\n"
        f"Upload Link: {registration_url}\n\n"
        "Please ensure all details are submitted accurately to avoid any delays in processing.\n\n"
        "If you face any issues while uploading, feel free to reach out to us on +919213945441, 1800119515 "
        "Email: corpdesk@indcool.in\n\n"
        "Thanks & Regards,\n"
        "INDcool Onboarding Team"
    )
    return send_template_email(
        to=to,
        template="partner_registration_invite",
        context={
            "contact_person_name": recipient_name,
            "firm_name": recipient_name,
            "registration_no": reference,
            "registration_url": registration_url,
            "text_body": text_body,
        },
        subject=subject,
    )


def send_partner_agreement_invite_email(
    to: str,
    contact_person_name: str | None,
    firm_name: str | None,
    registration_no: str,
    agreement_no: str,
    agreement_url: str,
) -> bool:
    recipient_name = (firm_name or contact_person_name or "Partner").strip() or "Partner"
    reference = (registration_no or "your registration").strip()
    text_body = (
        f"Dear {recipient_name},\n\n"
        f"Congratulations - your partner onboarding application ({reference}) has been approved by "
        "INDcool Electricals Pvt Ltd.\n\n"
        "One final step remains. Please review and digitally sign the Authorised Service Partner "
        "Agreement using the secure link below:\n\n"
        f"Review & Sign Agreement: {agreement_url}\n\n"
        "You will be asked to read the agreement in full and confirm a one-time password (OTP) sent "
        "to this email address. Your acceptance is timestamped and legally valid under the "
        "Information Technology Act, 2000.\n\n"
        "Your partner account and vendor code will be issued once the agreement is signed.\n\n"
        f"Agreement Reference: {agreement_no}\n\n"
        "If you face any issues, feel free to reach out to us on +919213945441, 1800119515 "
        "Email: corpdesk@indcool.in\n\n"
        "Thanks & Regards,\n"
        "INDcool Onboarding Team"
    )
    return send_template_email(
        to=to,
        template="partner_agreement_invite",
        context={
            "contact_person_name": recipient_name,
            "firm_name": recipient_name,
            "registration_no": reference,
            "agreement_no": agreement_no,
            "agreement_url": agreement_url,
            "text_body": text_body,
        },
        subject=f"Sign your INDcool partner agreement — {agreement_no}",
    )


def send_partner_agreement_otp_email(
    to: str,
    otp: str,
    agreement_no: str,
    expiry_minutes: int,
) -> bool:
    text_body = (
        "You requested to digitally sign the INDcool Authorised Service Partner Agreement.\n\n"
        f"Your OTP is: {otp}\n"
        f"Valid for {expiry_minutes} minutes.\n\n"
        "Do not share this OTP with anyone.\n\n"
        f"Agreement Reference: {agreement_no}\n\n"
        "If you did not request this, ignore this email and no action will be taken."
    )
    return send_template_email(
        to=to,
        template="partner_agreement_otp",
        context={
            "otp": otp,
            "agreement_no": agreement_no,
            "expiry_minutes": expiry_minutes,
            "text_body": text_body,
        },
        subject=f"Your OTP for signing the INDcool partner agreement — {agreement_no}",
    )


def send_partner_agreement_signed_email(
    to: str,
    partner_name: str,
    agreement_no: str,
    agreement_version: str,
    signed_at: str,
    ip_address: str | None,
) -> bool:
    recipient_name = (partner_name or "Partner").strip() or "Partner"
    ip = (ip_address or "—").strip() or "—"
    text_body = (
        f"Dear {recipient_name},\n\n"
        "Your INDcool Authorised Service Partner Agreement has been digitally signed and is now "
        "legally binding. Keep this email as your digital signing certificate.\n\n"
        f"Agreement No: {agreement_no}\n"
        f"Version: {agreement_version}\n"
        f"Signed Email: {to}\n"
        f"Signed At: {signed_at}\n"
        f"IP Address: {ip}\n"
        "Verified Via: Email OTP\n"
        "Legal Basis: IT Act 2000, India\n\n"
        "Your partner account has been activated. A separate welcome email with your INDcool "
        "vendor code follows shortly."
    )
    return send_template_email(
        to=to,
        template="partner_agreement_signed",
        context={
            "partner_name": recipient_name,
            "agreement_no": agreement_no,
            "agreement_version": agreement_version,
            "email": to,
            "signed_at": signed_at,
            "ip_address": ip,
            "text_body": text_body,
        },
        subject=f"Agreement signed — {agreement_no}",
    )


def send_partner_rejection_email(
    to: str,
    contact_person_name: str | None,
    firm_name: str | None,
    registration_no: str,
    registration_url: str,
    reason: str | None = None,
) -> bool:
    recipient_name = (firm_name or contact_person_name or "Partner").strip() or "Partner"
    reference = (registration_no or "your registration").strip()
    reason = (reason or "").strip()
    reason_line = f"Reviewer note: {reason}" if reason else ""
    subject = f"INDcool partner onboarding — action needed on {reference}"
    text_body = (
        f"Dear {recipient_name},\n\n"
        f"Thank you for submitting your onboarding application ({reference}) with INDcool Electricals Pvt Ltd.\n\n"
        "After review, we were unable to approve your application in its current form and need you to revisit "
        "and resubmit it.\n\n"
        f"{reason_line + chr(10) + chr(10) if reason_line else ''}"
        "Please use the link below to review and correct your details, then resubmit:\n\n"
        f"Continue Onboarding: {registration_url}\n\n"
        "If you face any issues, feel free to reach out to us on +919213945441, 1800119515 "
        "Email: corpdesk@indcool.in\n\n"
        "Thanks & Regards,\n"
        "INDcool Onboarding Team"
    )
    reason_block = f"<p><strong>Reviewer note:</strong> {reason}</p>" if reason else ""
    return send_template_email(
        to=to,
        template="partner_registration_rejected",
        context={
            "contact_person_name": recipient_name,
            "firm_name": recipient_name,
            "registration_no": reference,
            "registration_url": registration_url,
            "reason_block": reason_block,
            "text_body": text_body,
        },
        subject=subject,
    )


def send_partner_approval_email(
    to: str,
    partner_name: str,
    vendor_code: str,
) -> bool:
    recipient_name = (partner_name or "Partner").strip() or "Partner"
    code = (vendor_code or "").strip()
    text_body = (
        f"Dear {recipient_name},\n\n"
        "Great news — your documents have been successfully verified, and we're delighted to "
        "officially welcome you as a partner with INDcool Electricals Pvt Ltd.\n\n"
        f"Your Vendor Code is: {code}\n\n"
        "Please keep this code handy, as it will be required for all future orders, communication, "
        "and transactions with us."
    )
    return send_template_email(
        to=to,
        template="partner_approval_welcome",
        context={
            "partner_name": recipient_name,
            "vendor_code": code,
            "text_body": text_body,
        },
        subject=f"Welcome to INDcool — Vendor Code {code}",
    )
HELPDESK_EMAIL = "support@indcool.in"
TOLL_FREE_NUMBER = "1800-11-9515"


def send_service_request_acknowledgment_email(
    to: str,
    request_no: str | None,
) -> bool:
    ticket_id = (request_no or "").strip() or "your request"
    from_name = (settings.smtp_from_name or "").strip() or "INDcool Service Team"
    subject = f"Service request acknowledged — Ticket ID: {ticket_id}"
    text_body = (
        "Dear Sir/Ma'am,\n\n"
        "Greetings from INDcool! Thanks for contacting us!\n\n"
        "This is a system-generated response acknowledging the receipt of your recent interaction with INDcool.\n\n"
        f"Your ticket has been generated with Ticket ID: {ticket_id}\n\n"
        "One of our service experts will reach out to you shortly regarding your query/complaint.\n\n"
        f"Please retain this Ticket ID for future communication. For assistance, you can reach out to our helpdesk at "
        f"{HELPDESK_EMAIL} or call us at our toll-free number: {TOLL_FREE_NUMBER}.\n\n"
        f"Thank you,\n{from_name}"
    )
    return send_template_email(
        to=to,
        template="service_request_acknowledged",
        context={
            "request_no": ticket_id,
            "helpdesk_email": HELPDESK_EMAIL,
            "toll_free_number": TOLL_FREE_NUMBER,
            "from_name": from_name,
            "text_body": text_body,
        },
        subject=subject,
    )


def send_service_happy_code_email(
    to: str,
    *,
    service_id: int,
    completion_code: str,
) -> bool:
    service_code = str(service_id)
    from_name = (settings.smtp_from_name or "").strip() or "INDcool Service Team"
    subject = f"INDcool Service Code {service_code} — Completion Code {completion_code}"
    text_body = (
        "Dear Sir/Ma'am,\n\n"
        "Greetings from INDcool!\n\n"
        f"INDcool Service Code is {service_code}. "
        f"Completion Code is {completion_code}.\n\n"
        "Our Service Engineer will report to you within the next 24-48 Hours.\n\n"
        "Please share the Completion Code with our engineer when they visit, so we can verify the visit.\n\n"
        f"TEAM INDcool\nToll-Free: {TOLL_FREE_NUMBER}\n\n"
        f"For assistance, contact {HELPDESK_EMAIL}.\n\n"
        f"Thank you,\n{from_name}"
    )
    return send_template_email(
        to=to,
        template="service_happy_code",
        context={
            "service_code": service_code,
            "completion_code": completion_code,
            "helpdesk_email": HELPDESK_EMAIL,
            "toll_free_number": TOLL_FREE_NUMBER,
            "from_name": from_name,
            "text_body": text_body,
        },
        subject=subject,
    )


DEFAULT_DOCUMENT_UPLOAD_REQUEST_ITEMS = [
    "Invoice of the product",
    "Warranty Certificate",
    "Serial number of the product",
    "Copy of Contract (if applicable)",
]

_DOCUMENT_TYPE_EMAIL_LABELS = {
    "Purchase Order": "Purchase Order",
    "Original Purchase Bill/Invoice": "Invoice of the product",
}


def _document_items_for_email(required_documents: list[str] | None = None) -> list[str]:
    if not required_documents:
        return list(DEFAULT_DOCUMENT_UPLOAD_REQUEST_ITEMS)
    mapped = [_DOCUMENT_TYPE_EMAIL_LABELS.get(doc, doc) for doc in required_documents if doc]
    return mapped or list(DEFAULT_DOCUMENT_UPLOAD_REQUEST_ITEMS)


def _documents_html(items: list[str]) -> str:
    return "".join(f"<li>{item}</li>" for item in items)


def send_document_upload_link_email(
    to: str,
    customer_name: str | None,
    ticket_id: str | None,
    upload_url: str,
    required_documents: list[str] | None = None,
) -> bool:
    ticket = (ticket_id or "").strip() or "your request"
    document_items = _document_items_for_email(required_documents)
    documents_html = _documents_html(document_items)
    from_name = (settings.smtp_from_name or "").strip() or "INDcool Service Team"
    subject = f"Document upload request — Ticket ID: {ticket}"
    document_lines = "\n".join(f"- {item}" for item in document_items)
    text_body = (
        "Dear Sir/Madam,\n\n"
        "Greetings from INDcool!\n\n"
        f"Your Ticket ID: {ticket}\n\n"
        "We kindly request you to share the following documents within 24 hours for warranty validation:\n\n"
        f"{document_lines}\n\n"
        "To upload the required documents, please click the link below:\n"
        f"Upload Documents: {upload_url}\n\n"
        "Please retain this Ticket ID for future communication.\n\n"
        f"Thank you,\n{from_name}"
    )
    return send_template_email(
        to=to,
        template="document_upload_link",
        context={
            "ticket_id": ticket,
            "upload_url": upload_url,
            "documents_html": documents_html,
            "from_name": from_name,
            "text_body": text_body,
        },
        subject=subject,
    )


def send_complaint_created_email(
    to: str,
    customer_name: str | None,
    comp_no: str | None,
    query_type: str | None,
    status: str | None,
    customer_mobile: str | None,
    problem_description: str | None,
) -> bool:
    display_name = (customer_name or "").strip() or "Customer"
    reference = (comp_no or "").strip() or "your request"
    type_label = (query_type or "").strip() or "General"
    status_label = (status or "").strip() or "Pending"
    mobile = (customer_mobile or "").strip() or "—"
    problem = (problem_description or "").strip()
    problem_summary = f"Problem reported: {problem}" if problem else "We have recorded your request."
    from_name = (settings.smtp_from_name or "").strip() or "Indcool Service Team"
    subject = f"Complaint registered — {reference}"
    text_body = (
        f"Hello {display_name},\n\n"
        f"Your request has been registered with Indcool.\n\n"
        f"Reference number: {reference}\n"
        f"Type: {type_label}\n"
        f"Status: {status_label}\n"
        f"Mobile: {mobile}\n\n"
        f"{problem_summary}\n\n"
        "Our team will review your request and contact you shortly.\n\n"
        f"Thank you,\n{from_name}"
    )
    return send_template_email(
        to=to,
        template="complaint_created",
        context={
            "customer_name": display_name,
            "comp_no": reference,
            "query_type": type_label,
            "status": status_label,
            "customer_mobile": mobile,
            "problem_summary": problem_summary,
            "from_name": from_name,
            "text_body": text_body,
        },
        subject=subject,
    )


def send_service_unit_assignment_email(
    to: str,
    engineer_name: str | None,
    request_no: str | None,
    order_no: str | None,
    customer_name: str | None,
    customer_address: str | None,
    problem_description: str | None,
    assigned_units: list[dict],
) -> bool:
    display_name = (engineer_name or "").strip() or "Engineer"
    request_label = (request_no or "").strip() or "service request"
    order_label = (order_no or "").strip() or "—"
    customer = (customer_name or "").strip() or "—"
    address = (customer_address or "").strip() or "—"
    problem = (problem_description or "").strip() or "—"
    quantity = len(assigned_units)

    rows_html = []
    for idx, unit in enumerate(assigned_units, start=1):
        labels = unit.get("serial_labels") or []
        values = unit.get("serial_values") or []
        serial_parts = []
        for label, value in zip(labels, values):
            serial_parts.append(f"{label}: {value or '—'}")
        if not serial_parts:
            serial_parts.append(f"Serial: {unit.get('serial_no') or '—'}")
        item_code = unit.get("item_code") or "—"
        item_name = unit.get("item_name") or "—"
        rows_html.append(
            f"<p><strong>Unit {idx}</strong> — {item_code} / {item_name}<br>"
            f"{'; '.join(serial_parts)}</p>"
        )
    units_html = "".join(rows_html) if rows_html else "<p>No unit details available.</p>"

    subject = f"Service assignment — {request_label} ({quantity} unit(s))"
    text_body = (
        f"Hello {display_name},\n\n"
        f"You have been assigned {quantity} unit(s) for service request {request_label}.\n"
        f"Order: {order_label}\nCustomer: {customer}\nAddress: {address}\n\n"
        f"Service details: {problem}\n\n"
        "Please log in to Indcool CRM to review your assigned units.\n\n"
        "Thank you,\nIndcool Service Team"
    )
    return send_template_email(
        to=to,
        template="service_unit_assignment",
        context={
            "engineer_name": display_name,
            "request_no": request_label,
            "order_no": order_label,
            "customer_name": customer,
            "customer_address": address,
            "quantity_assigned": quantity,
            "units_html": units_html,
            "problem_description": problem,
            "text_body": text_body,
        },
        subject=subject,
    )


def send_rubric_request_email(
    to: str,
    advisor_name: str | None,
    rubric_link: str | None,
    instructions: str | None,
) -> bool:
    display_name = (advisor_name or "").strip() or "Advisor"
    link = (rubric_link or "").strip()
    notes = (instructions or "").strip() or "Please complete the rubric using the link below."
    subject = "Rubric request from Indcool"
    text_body = f"Hello {display_name},\n\n{notes}\n"
    if link:
        text_body += f"\nLink: {link}\n"
    text_body += "\nThank you,\nIndcool Team"
    return send_template_email(
        to=to,
        template="rubric_request",
        context={
            "advisor_name": display_name,
            "rubric_link": link,
            "instructions": notes,
            "text_body": text_body,
        },
        subject=subject,
    )


def send_survey_email(
    to: str,
    advisor_name: str | None,
    survey_name: str | None,
    survey_link: str | None,
) -> bool:
    display_name = (advisor_name or "").strip() or "Advisor"
    survey_label = (survey_name or "").strip() or "Advisor Survey"
    link = (survey_link or "").strip()
    subject = f"Survey: {survey_label}"
    text_body = f"Hello {display_name},\n\nPlease complete the survey: {survey_label}\n"
    if link:
        text_body += f"\nLink: {link}\n"
    text_body += "\nThank you,\nIndcool Team"
    return send_template_email(
        to=to,
        template="survey_request",
        context={
            "advisor_name": display_name,
            "survey_name": survey_label,
            "survey_link": link,
            "text_body": text_body,
        },
        subject=subject,
    )
