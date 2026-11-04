"""Keyword-matched guide content for the INDcool Assistant (api/app/routers/assistant.py).

Pure Python string matching -- no external AI API, no cost. Each intent is matched against the
user's message by keyword overlap; the best-scoring intent's text/steps/link are returned.
Lookup intents (kind="lookup") are handled specially in the router -- they run a real query against
the CRM's own data (order search, ledger balance) instead of returning fixed text.

Every route/step below was checked against the actual pages in ui/src (App.jsx, SalesRoutes.jsx,
Sidebar.jsx) rather than guessed, so a guide never points somewhere that doesn't exist.
"""

GUIDE_INTENTS = [
    # --- Sales ---
    {
        "id": "find_leads",
        "keywords": ["lead", "leads", "sales lead", "my leads", "how to find"],
        "text": "Here's how to find a lead:",
        "steps": [
            "Go to Sales → My leads in the left sidebar.",
            "Use the search bar — search by name, phone, item, place, or a lead reference (SL-...).",
            "Filter by Open/All, lead type, Hot/Warm/Cold, priority, or Registered date.",
            "Click a lead row to open its full detail — contact history, wants, source, and follow-up date.",
            "To take it, use \"Assign to me\" on that lead's own page.",
        ],
        "link": "/sales/leads",
        "link_label": "Open Sales → My leads",
    },
    {
        "id": "add_lead",
        "keywords": ["add lead", "new lead", "create lead", "upload leads", "bulk lead"],
        "text": "Adding a lead:",
        "steps": [
            "Go to Sales → My leads.",
            "Click \"+ Add lead\" for one at a time, or \"Upload Excel or CSV\" to bring in many at once.",
            "\"Bring in the last 30 days\" pulls in recent enquiries already registered elsewhere in the CRM (GeM, call-centre desk, etc.) as leads.",
        ],
        "link": "/sales/leads",
        "link_label": "Open Sales → My leads",
    },
    {
        "id": "make_quotation",
        "keywords": ["quotation", "quote", "make a quotation", "create quote"],
        "text": "Making a quotation:",
        "steps": [
            "Open the lead from Sales → My leads.",
            "Log a call against it (or open an existing call log) — the \"Make a quotation\" button appears there once the call is marked as wanting a quote.",
            "Click it — it creates the quotation and opens it straight away for you to fill in items and pricing.",
            "All quotations on that lead are also listed on the lead's own page, with status and total.",
        ],
        "link": "/sales/quotations",
        "link_label": "Open Sales → Quotations",
    },
    {
        "id": "sales_dashboard",
        "keywords": ["sales dashboard", "my day", "sales calendar", "sales team"],
        "text": "Other Sales views:",
        "steps": [
            "My day — today's follow-ups and calls, in order.",
            "Calendar — all your scheduled follow-ups by date.",
            "Dashboard — your numbers (or the team's/company's, if you have that access).",
            "Team — see teammates, their targets, and profiles (if you have that access).",
        ],
        "link": "/sales",
        "link_label": "Open Sales",
    },

    # --- Orders / Couriers / Returns ---
    {
        "id": "process_return",
        "keywords": ["process return", "return order", "process a return", "returned order"],
        "text": "Processing a return:",
        "steps": [
            "Sales/Service must first confirm Material Receipt on the order — Accounts can't process a return before this.",
            "Go to Accounts (the Ledger page) → Dashboard tab → Returns & Cancellations panel.",
            "Enter Qty Returned — the amount auto-calculates from the bill's per-unit price (Bill Amount ÷ Bill Qty). Leave it blank to type an amount manually instead, e.g. for a partial-box return.",
            "Submit — it goes through Accounts → Audit → Admin before it posts to the vendor's ledger.",
        ],
        "link": "/ledger",
        "link_label": "Open Accounts",
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
        "id": "deactivate_courier",
        "keywords": ["deactivate courier", "disable courier", "delete courier"],
        "text": "Deactivate vs Delete a courier:",
        "steps": [
            "Deactivate works anytime, even with active orders — it just hides the courier from the dropdown for new orders. Existing orders keep working normally.",
            "Delete is blocked until every order on that courier is Delivered.",
            "Both buttons are on the courier's own detail page.",
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
    {
        "id": "add_order",
        "keywords": ["add order", "new order", "create order", "raise order"],
        "text": "Creating an order:",
        "steps": [
            "Go to Order List, click \"+ New Order\".",
            "Fill in customer details, item lines, and upload the Order Document (required).",
            "Vendors creating their own order can't set OEM Bill details, Courier, or LRN — those are filled in later by Admin/Incool once the order ships.",
        ],
        "link": "/orders/new",
        "link_label": "Open New Order",
    },

    # --- Queries / Complaints / Partner Registrations ---
    {
        "id": "raise_query",
        "keywords": ["raise query", "ask admin", "query"],
        "text": "Raising a query:",
        "steps": [
            "Go to Queries in the sidebar, or use \"+ Raise query\" on the Dashboard.",
            "Describe what you're stuck on — an order, a job, a payment, or the app itself.",
            "The Admin team answers it in the same Queries thread; you'll see it under \"My queries\".",
        ],
        "link": "/queries",
        "link_label": "Open Queries",
    },
    {
        "id": "complaint",
        "keywords": ["complaint", "register complaint", "service complaint"],
        "text": "Registering a complaint:",
        "steps": [
            "Go to Complaints in the sidebar, click \"+ New Complaint\".",
            "Pick the type (Service/Installation/Sales/Others), enter customer and serial details.",
            "It then flows into the normal assignment/approval chain for that type.",
        ],
        "link": "/complaints",
        "link_label": "Open Complaints",
    },
    {
        "id": "partner_registration",
        "keywords": ["partner registration", "vendor registration", "new vendor", "onboard vendor"],
        "text": "Partner (vendor) registration:",
        "steps": [
            "Go to Partner Registrations in the sidebar.",
            "A submitted registration shows here for review — approving it creates the Vendor record and (if applicable) sends the partner agreement to sign.",
        ],
        "link": "/partner-registrations",
        "link_label": "Open Partner Registrations",
    },

    # --- Installations / Service ---
    {
        "id": "assign_installation",
        "keywords": ["assign installation", "assign engineer", "installation request"],
        "text": "Installation Requests:",
        "steps": [
            "Go to Installation Requests in the sidebar.",
            "Unassigned requests show their serial/customer details — use the assignment panel to pick an engineer.",
            "The assigned engineer then sees it in their own queue and updates status as they work it (Assigned → In Progress → Completed).",
        ],
        "link": "/installations",
        "link_label": "Open Installation Requests",
    },
    {
        "id": "payment_queue",
        "keywords": ["payment queue", "ready to pay", "approve payment"],
        "text": "Payment Queue:",
        "steps": [
            "Go to Payment Queue in the sidebar — it lists installation/service payments waiting at your stage of the approval chain.",
            "Approving moves it to the next stage (e.g. Sub Admin → Accounts → Audit → Admin); rejecting sends it back with your note.",
        ],
        "link": "/installations/payment-queue",
        "link_label": "Open Payment Queue",
    },

    # --- Bids ---
    {
        "id": "bids",
        "keywords": ["bid", "bids", "tender", "gem bid"],
        "text": "Bids:",
        "steps": [
            "Go to Bids in the sidebar.",
            "Admin/manager side: create a bid, allocate it to vendors, and review vendor requests to participate.",
            "Vendor side: see open bids and submit a request to participate from Bids → Request.",
        ],
        "link": "/bids",
        "link_label": "Open Bids",
    },

    # --- Serials / Claims / Items ---
    {
        "id": "serial_history",
        "keywords": ["serial history", "find serial", "serial number", "track serial"],
        "text": "Finding a serial's history:",
        "steps": [
            "Use the \"Search serial number...\" box at the top of any page — fastest way in.",
            "Or go to Serial History in the sidebar and search there.",
            "It shows the full life of that unit: order, installation, service history, and any complaint/claim against it.",
        ],
        "link": "/serials/history",
        "link_label": "Open Serial History",
    },
    {
        "id": "claims",
        "keywords": ["claim", "claims", "warranty claim"],
        "text": "Claims:",
        "steps": [
            "Go to Claims in the sidebar.",
            "Click \"+ New Claim\", enter the serial and the issue — it links to that unit's full history automatically.",
        ],
        "link": "/claims",
        "link_label": "Open Claims",
    },
    {
        "id": "item_master",
        "keywords": ["item master", "add item", "product master"],
        "text": "Item Masters:",
        "steps": [
            "Go to Item Masters in the sidebar to see every product/item code set up in the system.",
            "Click \"+ New Item\" to add one — item code, name, and warranty/service defaults.",
        ],
        "link": "/items",
        "link_label": "Open Item Masters",
    },

    # --- Accounts / Ledger ---
    {
        "id": "accounts_dashboard",
        "keywords": ["accounts dashboard", "due vs paid", "overdue vendors", "ledger"],
        "text": "Accounts:",
        "steps": [
            "Go to Accounts in the sidebar (this is the Ledger page).",
            "The Dashboard tab shows total due, paid this month, overdue parties, and the Returns queue.",
            "Other tabs: Vendors, Engineers, Couriers — search any party and open its own ledger for full history.",
        ],
        "link": "/ledger",
        "link_label": "Open Accounts",
    },
]


LOOKUP_INTENTS = [
    {"id": "find_order", "keywords": ["order", "find order", "where is", "order status"]},
    {"id": "courier_ledger", "keywords": ["courier balance", "courier ledger", "transporter balance"]},
    {"id": "vendor_ledger", "keywords": ["vendor balance", "vendor ledger"]},
    {"id": "find_lead", "keywords": ["find lead", "lead status", "lead phone", "lead detail"]},
    {"id": "find_serial", "keywords": ["serial", "find serial", "serial number", "track serial", "serial status"]},
    {"id": "find_complaint", "keywords": ["complaint status", "find complaint", "track complaint", "complaint number"]},
    {"id": "find_installation", "keywords": ["installation status", "find installation", "track installation"]},
]
