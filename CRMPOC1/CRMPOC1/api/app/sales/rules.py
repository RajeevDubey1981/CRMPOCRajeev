"""The fixed lists and the explainable rules of the Sales module: lead types, heat, priority, disposal reasons and
the access ticks. Nothing here touches a database."""

from __future__ import annotations

import re
from datetime import date

LEAD_TYPES = {
    "gem": "GeM",
    "csd": "CSD",
    "retail": "Retail",
    "spare": "Spare parts",
    "dealer": "Dealer",
    "tender": "State tender",
    "corp": "Corporate / project",
    "export": "Export",
}
STATUSES = {
    "new": "New", "con": "Contacted", "int": "Interested", "quo": "Quote sent", "neg": "Negotiation",
    "won": "Won", "dis": "Disposed", "rev": "Waiting for manager",
}
CLOSED_STATUSES = frozenset({"won", "dis", "rev"})
HEATS = ("hot", "warm", "cold")
PRIORITIES = ("urgent", "high", "normal", "low")
PRIORITY_ORDER = {"urgent": 0, "high": 1, "normal": 2, "low": 3}
HEAT_ORDER = {"hot": 0, "warm": 1, "cold": 2}

# key, label, needs the manager to approve
DISPOSALS = {
    "won": ("Won: order confirmed", False),
    "lost_price": ("Lost: price too high", True),
    "lost_brand": ("Lost: chose another brand", True),
    "lost_cancel": ("Lost: project cancelled or no budget", True),
    "noint": ("Not interested", False),
    "wrong": ("Wrong number", True),
    "dup": ("Duplicate lead", True),
    "fake": ("Invalid or fake enquiry", True),
    "unreach": ("Not reachable after 5 attempts", True),
    # set only by the CRM, for a partner registration lead
    "pr_won": ("Won: partner approved in the CRM", False),
    "pr_can": ("Not interested: registration cancelled in the CRM", False),
}
CRM_ONLY_DISPOSALS = frozenset({"pr_won", "pr_can"})
GOOD_DISPOSALS = frozenset({"won", "pr_won"})

# ---- heat: Hot (ready to buy), Warm (interested), Cold (only enquiring) ----
HEAT_RULES = (
    ("quote", "Asked for a quote or price", 3),
    ("time15", "Needs it within 15 days", 3),
    ("soon", "Bid or tender closes within 7 days", 3),
    ("budget", "Budget is confirmed", 2),
    ("boss", "Spoke to the decision maker", 2),
    ("time45", "Needs it within 45 days", 1),
    ("noans", "No answer on the last calls", -2),
    ("stale", "No contact for 7 days or more", -2),
)
MARKETPLACE_SOURCES = frozenset({"Alibaba.com", "TradeWheel", "TradeKey", "WaystoCap", "Afrindex"})


def suggest_heat(answers: dict) -> tuple[str, list[str], int]:
    score, why = 0, []
    for key, label, points in HEAT_RULES:
        if answers.get(key):
            score += points
            why.append(label)
    level = "hot" if score >= 7 else "warm" if score >= 3 else "cold"
    return level, why, score


def heat_from_text(text: str) -> dict:
    t = text or ""
    return {
        "quote": bool(re.search(r"rate|price|quot|list", t, re.I)),
        "time15": bool(re.search(r"urgent|this week|immediately", t, re.I)),
        "budget": bool(re.search(r"budget", t, re.I)),
    }


def suggest_priority(
    *, value_lakh: float | None, closes_on: date | None, lead_type: str, heat: str, follow_up_late: bool,
    source: str | None = None, today: date | None = None,
) -> tuple[str, list[str], int]:
    today = today or date.today()
    score, why = 0, []

    def add(n: int, text: str):
        nonlocal score
        score += n
        why.append(text)

    v = float(value_lakh or 0)
    if v >= 25:
        add(3, "Deal worth ₹25 lakh or more")
    elif v >= 10:
        add(2, "Deal worth ₹10 lakh or more")
    elif v >= 5:
        add(1, "Deal worth ₹5 lakh or more")
    if closes_on is not None:
        days = (closes_on - today).days
        if days <= 2:
            add(4, "Closes within 2 days")
        elif days <= 7:
            add(2, "Closes within 7 days")
    if lead_type in ("gem", "tender"):
        add(1, "Government bid or tender")
    if lead_type == "export" and source in MARKETPLACE_SOURCES:
        add(1, "Marketplace buyer is asking many suppliers")
    if heat == "hot":
        add(1, "Hot lead")
    if follow_up_late:
        add(1, "Follow-up is overdue")
    level = "urgent" if score >= 6 else "high" if score >= 3 else "normal" if score >= 1 else "low"
    return level, why, score


def detect_lead_type(text: str, channel: str = "") -> str:
    t = text or ""
    if channel == "partner":
        return "dealer"
    if channel in {"alibaba", "tradewheel", "tradekey", "tenders", "waystocap", "afrindex"} or re.search(
        r"nepal|kenya|ghana|sri lanka|colombo|kathmandu|nairobi|mombasa|accra|\bfob\b|\bcif\b|\bdap\b|\bexport", t, re.I
    ):
        return "export"
    if re.search(r"csd|canteen|cantt|depot", t, re.I):
        return "csd"
    if re.search(r"tender", t, re.I):
        return "tender"
    if re.search(r"\bgem\b|\bbid\b", t, re.I):
        return "gem"
    if re.search(r"spare|compressor|pcb", t, re.I):
        return "spare"
    if re.search(r"hotel|project|hospital|college|company", t, re.I):
        return "corp"
    return "retail"


# ---- the access ticks ----
# (group, [(key, label, locked to Admin and Sub Admin)])
TICK_GROUPS = (
    ("Leads", (
        ("see_all", "See all leads, not only my own", False),
        ("add_lead", "Add a lead by hand", False),
        ("upload", "Upload leads from Excel or CSV", False),
        ("give", "Give or move a lead to a team member", False),
        ("autogive", "Auto-give new leads by area", False),
        ("types_edit", "Choose which lead types each member handles", False),
    )),
    ("Rating and priority", (
        ("rate", "Mark a lead Hot, Warm or Cold", False),
        ("flag", "Flag a lead High, with a reason", False),
        ("setpri", "Set Urgent, High, Normal or Low", False),
        ("rules", "Change the rating and priority rules", False),
    )),
    ("Closing a lead", (
        ("dispose", "Dispose: Won, Not interested", False),
        ("dispose_lost", "Dispose: lost, wrong number, duplicate, invalid (waits for approval)", False),
        ("approve_disp", "Approve or reopen a disposal", False),
        ("delete", "Delete a lead", False),
    )),
    ("Partner registration leads", (
        ("pr_view", "See the required papers and CRM status of a partner lead", False),
        ("pr_remind", "Remind the partner about missing papers", False),
        ("pr_cancel_req", "Ask the partner admin to cancel a registration", False),
    )),
    ("Quotations", (
        ("make_quote", "Make a quotation", False),
        ("send_quote", "Send an approved quotation to the customer", False),
        ("approve_quote", "Approve, return or reject a quotation", False),
        ("approve_high", "Approve a discount above the limit", True),
        ("override", "Override a decision on a quotation", True),
    )),
    ("Sources", (
        ("connect", "Connect or disconnect a source (logins and keys)", False),
        ("form_fill", "Change what a connected form fills in, its default type and owner", False),
        ("reglog", "See the registered-first log", False),
    )),
    ("Export", (
        ("exp_desk", "See the Export desk", False),
        ("exp_search", "Search the export market and make leads from it", False),
        ("fx", "Set the daily dollar rate for export quotations", False),
    )),
    ("People", (
        ("own_profile", "Edit my own profile (pin code, state, district)", False),
        ("others_profile", "Edit another person's profile", False),
        ("targets", "Set monthly targets", False),
    )),
    ("Dashboards", (
        ("my_dash", "My own dashboard", False),
        ("team_dash", "Team dashboard and leaderboard", False),
        ("co_dash", "Company-wide view and discount report", False),
    )),
)
ALL_TICKS = tuple(k for _g, items in TICK_GROUPS for k, _l, _x in items)
LOCKED_TICKS = frozenset(k for _g, items in TICK_GROUPS for k, _l, locked in items if locked)

TICK_DEFAULTS = {
    "team": frozenset({
        "add_lead", "rate", "flag", "dispose", "dispose_lost", "make_quote", "send_quote", "own_profile", "my_dash",
        "pr_view", "pr_remind", "pr_cancel_req",
    }),
    "mgr": frozenset({
        "see_all", "add_lead", "upload", "give", "autogive", "types_edit", "rate", "flag", "setpri", "dispose",
        "dispose_lost", "approve_disp", "make_quote", "send_quote", "approve_quote", "form_fill", "reglog",
        "exp_desk", "exp_search", "own_profile", "others_profile", "targets", "my_dash", "team_dash",
        "pr_view", "pr_remind", "pr_cancel_req",
    }),
}

# ---- partner registration papers (the CRM's own rules) ----
INCORPORATION_BUSINESS_TYPES = frozenset({"Private Limited", "Public Limited", "LLP", "Partnership"})

# ---- quotation terms by lead type ----
QUOTE_TERMS = {
    "gem": ("As per the GeM bid terms (payment after delivery and acceptance)", "As per the bid delivery schedule", "As per the bid, 1 year comprehensive"),
    "csd": ("As per CSD norms, after supply to the depot", "Supply to the depot named in the indent", "1 year comprehensive, 5 years on the compressor"),
    "retail": ("50% advance with the order, balance before dispatch", "Within 15 days of the advance", "1 year comprehensive, 5 years on the compressor"),
    "spare": ("100% advance", "Within 3 days of payment, ex-warehouse", "6 months on the part"),
    "dealer": ("As per the dealer agreement (credit limit)", "Within 10 days of the order", "1 year comprehensive, 5 years on the compressor"),
    "tender": ("As per the tender conditions", "As per the tender schedule", "As per the tender"),
    "corp": ("30% advance, 60% on delivery, 10% after installation", "As per the project plan", "1 year comprehensive, 5 years on the compressor"),
    "export": ("30% advance by bank transfer, 70% against a copy of the Bill of Lading (or an irrevocable letter of credit at sight)", "Within 35 days of the advance, price basis as named on the lead", "1 year comprehensive; spare parts supplied from India"),
}

QUOTE_STATUSES = {
    "draft": "Draft", "wait": "Waiting for the Sales Manager", "wadm": "Waiting for Admin or Sub Admin (high discount)",
    "ret": "Returned for changes", "appr": "Approved", "rej": "Rejected", "sent": "Sent to the customer",
    "acc": "Accepted by the customer", "cust_rej": "Declined by the customer", "cancel": "Cancelled by Admin",
}


def default_gst_for_hsn(hsn: str | None) -> int:
    h = (hsn or "").strip()
    if h.startswith("8415"):
        return 28
    return 18
