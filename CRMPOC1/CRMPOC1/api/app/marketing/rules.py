"""The ticks inside Marketing, and what each kind of person starts with."""

from __future__ import annotations

# (group, [(key, label, locked to Admin and Sub Admin)])
TICK_GROUPS = (
    ("Marketing", (
        ("view", "View Marketing and its reports", False),
    )),
    ("Audiences", (
        ("aud_own", "Build audiences from my own leads", False),
        ("aud_all", "Build audiences from all CRM customers and Sales leads", False),
        ("upload", "Upload prospect lists (GeM dealers, export)", False),
    )),
    ("Campaigns", (
        ("draft", "Write drafts and templates", False),
        ("submit", "Send a campaign for approval", False),
        ("approve", "Approve and release campaigns", False),
        ("cost", "See what campaigns cost", False),
    )),
    ("Consent", (
        ("consent_edit", "Edit the opt-in and STOP list", False),
    )),
    ("Channels and settings", (
        ("connect", "Connect or disconnect a platform (logins and keys)", True),
        ("settings", "Change rates, senders and limits", True),
        ("give_ticks", "Give Marketing ticks to others", True),
    )),
)
ALL_TICKS = tuple(k for _g, items in TICK_GROUPS for k, _l, _x in items)
LOCKED_TICKS = frozenset(k for _g, items in TICK_GROUPS for k, _l, locked in items if locked)

# the kinds of person: team = Sales Team, mgr = Sales Manager, oth = anyone else given the tick, mkt = the Marketing role
KINDS_ORDER = ("mkt", "mgr", "team", "oth")
KINDS = {"team": "Sales Team", "mgr": "Sales Manager", "oth": "Others with the tick", "mkt": "Marketing role"}

_TEAM = frozenset({"view", "aud_own", "draft", "submit"})
TICK_DEFAULTS = {
    "team": _TEAM,
    "oth": _TEAM,
    "mgr": frozenset({"view", "aud_own", "aud_all", "upload", "draft", "submit", "approve", "cost"}),
    "mkt": frozenset({"view", "aud_own", "aud_all", "upload", "draft", "submit", "approve", "cost", "consent_edit"}),
}

SETTING_DEFAULTS = {
    "rate_whatsapp": "0.90",   # rupees per promotional WhatsApp message, to be set from the real bill
    "rate_sms": "0.20",        # rupees per promotional SMS
    "monthly_cap": "2",        # promotions per person per month
    "daily_limit": "500",      # messages sent in a day
}
