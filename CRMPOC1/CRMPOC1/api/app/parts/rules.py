"""The fixed lists and the explainable rules of the Parts module: request kinds, the approval chain and its
thresholds, and the mandatory-photo rule. Nothing here touches a database."""

from __future__ import annotations

KINDS = {
    "part": "Spare part",
    "expense": "Expense",
    "ondemand": "On demand",
    "unit": "Whole unit",
}

# A request that needs its own photo proof, and how many. Everything else has no minimum.
REQUIRED_PHOTOS = {
    "part": 4,
    "unit": 5,
}

# Above this amount, a "part" or "ondemand" request also needs Admin/Sub Admin after the Service Manager.
# A "unit" (whole-unit replacement) always needs both, regardless of amount. "expense" always needs both.
PART_AUTO_APPROVE_LIMIT = 2500
UNIT_VALUE_THRESHOLD = 15000


def needs_second_approval(kind: str, amount) -> bool:
    if kind in ("unit", "expense"):
        return True
    if kind in ("part", "ondemand"):
        return amount is None or amount > PART_AUTO_APPROVE_LIMIT
    return False


def required_photos(kind: str) -> int:
    return REQUIRED_PHOTOS.get(kind, 0)


def effective_required_photos(req) -> int:
    """The photo count actually enforced for this request: its own override if one was set at creation
    (e.g. 0 for requests the system auto-raises from an engineer's observation), else the kind's default."""
    if req.required_photos_override is not None:
        return req.required_photos_override
    return required_photos(req.kind)


def next_stage_on_approve(kind: str, amount, current_stage: str) -> str:
    """svm -> sub (if a second approval is needed) or done; sub -> done."""
    if current_stage == "svm":
        return "sub" if needs_second_approval(kind, amount) else "done"
    if current_stage == "sub":
        return "done"
    return current_stage


def stage_label(kind: str, amount, stage: str) -> str:
    if stage == "done":
        return "Approved"
    if stage == "rejected":
        return "Not approved"
    if stage == "returned":
        return "Returned to Service Team"
    if stage == "sub":
        return "Approved by Service Manager, pending Admin"
    if stage == "svm":
        return f"Pending Service Manager{' (then Admin)' if needs_second_approval(kind, amount) else ''}"
    return stage
