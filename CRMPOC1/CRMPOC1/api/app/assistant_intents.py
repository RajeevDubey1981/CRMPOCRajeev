"""Keyword-matched guide content for the INDcool Assistant (api/app/routers/assistant.py).

Pure Python string matching -- no external AI API, no cost. Each intent is matched against the
user's message by keyword overlap; the best-scoring intent's text/steps/link are returned.
Lookup intents (kind="lookup") are handled specially in the router -- they run a real query against
the CRM's own data (order search, ledger balance) instead of returning fixed text.
"""

GUIDE_INTENTS = [
    {
        "id": "find_leads",
        "keywords": ["lead", "leads", "find lead", "sales lead"],
        "text": "Here's how to find a lead:",
        "steps": [
            "Go to Sales → Leads in the left sidebar.",
            "Use the search bar at the top — search by phone, name, or lead source.",
            "Filter by Status (New / Contacted / Converted / Lost) or by date range if there are many results.",
            "Click a lead row to open its full detail — contact history, assigned salesperson, and next follow-up date.",
            "To take it, use \"Assign to me\" in the top-right of that lead's page.",
        ],
        "link": "/sales/leads",
        "link_label": "Open Sales → Leads",
    },
    {
        "id": "process_return",
        "keywords": ["process return", "return order", "process a return", "returned order"],
        "text": "Processing a return:",
        "steps": [
            "Sales/Service must first confirm Material Receipt on the order — Accounts can't process a return before this.",
            "Go to Accounts dashboard → Returns & Cancellations panel.",
            "Enter Qty Returned — the amount auto-calculates from the bill's per-unit price (Bill Amount ÷ Bill Qty). Leave it blank to type an amount manually instead, e.g. for a partial-box return.",
            "Submit — it goes through Accounts → Audit → Admin before it posts to the vendor's ledger.",
        ],
        "link": "/ledger/accounts-dashboard",
        "link_label": "Open Accounts Dashboard",
    },
    {
        "id": "add_courier",
        "keywords": ["add courier", "new courier", "create courier", "courier master"],
        "text": "Adding a courier:",
        "steps": [
            "Go to Courier Masters in the sidebar.",
            "Click \"+ Add Courier\", fill in the name and contact details.",
            "Pick a Type: Parcel (needs a saved rate card, e.g. Delhivery) or Truck/LTL (no rate card — just a reference number and amount each time, for Wheels Eye/Porter/self-truck).",
            "Save, then open the courier's own Rate Card tab if it's a Parcel courier to fill in the zone matrix.",
        ],
        "link": "/couriers",
        "link_label": "Open Courier Masters",
    },
    {
        "id": "material_receipt",
        "keywords": ["material receipt", "confirm receipt", "goods received", "received back"],
        "text": "Confirming material receipt:",
        "steps": [
            "On an order that's Returned or Cancelled, open it from Order List.",
            "Click \"Confirm Material Receipt\" once the goods are physically back in hand.",
            "This unlocks the order for Accounts to process the return — nothing is debited to the vendor before this step.",
        ],
        "link": "/orders",
        "link_label": "Open Order List",
    },
    {
        "id": "freight_calculator",
        "keywords": ["freight", "calculate freight", "shipping cost", "courier rate", "oda"],
        "text": "Using the freight calculator:",
        "steps": [
            "Open the order, click Edit Order, pick the Courier.",
            "Click \"Calculate\" next to Freight Amount.",
            "Enter weight (or L×W×H), tick ODA if the destination pincode is Outside Delivery Area, then Calculate.",
            "Click \"Use this amount\" to fill it into Freight Amount — saving credits the courier's ledger automatically.",
            "If ODA, treat that number as an estimate — correct it once the courier confirms the actual ODA charge at delivery.",
        ],
        "link": None,
        "link_label": None,
    },
    {
        "id": "bill_qty",
        "keywords": ["bill qty", "bill line", "oem bill", "per unit price"],
        "text": "OEM Bill Qty and Bill Line No, in Edit Order:",
        "steps": [
            "Bill Line No — which line of a multi-line OEM bill this order is, for reference.",
            "Qty — how many units this Bill Amount covers; the per-unit price is auto-divided and shown under the field.",
            "That per-unit price is what auto-calculates a partial-return credit later.",
        ],
        "link": None,
        "link_label": None,
    },
]


LOOKUP_INTENTS = [
    {"id": "find_order", "keywords": ["order", "find order", "where is", "order status"]},
    {"id": "courier_ledger", "keywords": ["courier balance", "courier ledger", "transporter balance"]},
    {"id": "vendor_ledger", "keywords": ["vendor balance", "vendor ledger"]},
]
