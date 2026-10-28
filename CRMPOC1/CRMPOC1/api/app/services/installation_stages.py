"""The stages an installation request is shown in on every installation screen and dashboard. Each stage groups the
exact statuses, which stay available in the status filter."""

from __future__ import annotations

STAGES: list[tuple[str, str, tuple[str, ...]]] = [
    ("na", "Not assigned", ("Pending", "Document Requested", "Admin Review Document", "Order Verified", "Submitted", "Service Team Review")),
    ("as", "Assigned", ("Assigned",)),
    ("ip", "In progress", ("In Progress",)),
    ("vp", "Verification Pending", ("Serial Pending Verification",)),
    ("ap", "Approval Pending", ("Completion Pending Approval",)),
    ("in", "Installed", ("Installation Completed",)),
    ("pay", "Payment", ("Payment Pending", "Settlement Pending", "Settlement Approved")),
    ("done", "Completed", ("Completed",)),
    ("rr", "Returned or rejected", ("Returned", "Rejected")),
]

STAGE_STATUSES: dict[str, tuple[str, ...]] = {key: statuses for key, _label, statuses in STAGES}
STAGE_OF: dict[str, str] = {status: key for key, _label, statuses in STAGES for status in statuses}


def stage_counts(status_counts: dict[str, int]) -> dict[str, int]:
    """{status: how many} -> {stage: how many}, with every stage present."""
    out = {key: 0 for key, _label, _statuses in STAGES}
    for status, n in status_counts.items():
        key = STAGE_OF.get(status)
        if key:
            out[key] += int(n or 0)
    return out
