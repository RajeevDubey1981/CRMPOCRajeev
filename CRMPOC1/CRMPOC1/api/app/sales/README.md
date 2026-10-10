# Sales module

The Sales part of the CRM keeps its data in its **own database** (`indcool_sales`). It is linked to the CRM database
only by reference numbers (a CRM user id, an enquiry number such as `IDC_...` or `PR-...`) and by calls made through
the application. There is no foreign key, no join and no shared table between the two databases.

## Switching it on

1. Create the database and a MySQL user that can use **only** that database:
   ```sql
   CREATE DATABASE indcool_sales CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   CREATE USER 'indcool_sales'@'localhost' IDENTIFIED BY '<a long random password>';
   GRANT ALL PRIVILEGES ON indcool_sales.* TO 'indcool_sales'@'localhost';
   ```
2. Add one line to `api/.env`:
   `SALES_DATABASE_URL=mysql+mysqlconnector://indcool_sales:<password>@localhost:3306/indcool_sales`
3. Deploy. `scripts/deploy.py` runs the CRM updates (`alembic/`, up to `0064_sales_menu`) and then the Sales updates
   (`alembic_sales.ini`, folder `sales_alembic/`). With `SALES_DATABASE_URL` empty, Sales stays switched off, the Sales
   menu is hidden and the CRM works exactly as before.

## How the two sides meet

| Link | Sales keeps | CRM side |
|---|---|---|
| Same login | `sales_profile.crm_user_id` | `users.id` |
| Enquiry to lead | `sales_lead.crm_ref` (`IDC_...`) | `complaints` (query type Sales) |
| Partner registration | `sales_lead.crm_ref` (`PR-...`) | `partner_registrations`, read each time, never copied |
| Item prices | a copy on each quotation line | `item_masters` |
| Closing | `sales_lead` status | the enquiry is closed with the same result (a partner registration is closed by the CRM, never by Sales) |
| Login popup | nothing | `user_pending_actions` (module `sales`) |

All reads and writes on the CRM side go through `crm_link.py`.

## Access

* The CRM role card has one module, `sales` (view): it shows the Sales menu. Admin and Sub Admin always have it.
* Inside Sales, ticks (`rules.py`: `TICK_GROUPS`) decide what a person may do. Built-in defaults for the roles
  `sales` (team) and `sales_manager` (mgr), then Admin's choice for a role, then Admin's choice for one person.
  `approve_high` and `override` are never ticked for anyone but Admin and Sub Admin.

## Good to know

* The first sync starts from "now": older enquiries become leads only when a manager presses
  "Bring in the last 30 days".
* A background thread checks the CRM every `SALES_SYNC_SECONDS` (default 60). Nothing is lost if either side is offline:
  Sales asks for everything newer than the last enquiry it saw.
* Quotation prices come from the item master `mrp`; GST per line defaults by HSN (8415 is 28%, others 18%) and can
  be changed on the line. Export quotations are in US dollars with no GST.
* Lead types are rows in `sales_lead_type` (the eight built-in ones are seeded). Admin adds, renames, recolours or switches
  them off (screen "Lead types"). A type is never deleted.

## Connections, upload and the export-market lists

* `sources.py` holds the connections: IndiaMART (pull with the CRM key, or push), Meta lead forms (pull, or webhook),
  a web address (webhook), any API (address, key header, path to the list, field map), a Google Sheet published as CSV, and
  a mailbox (IMAP) for marketplaces that only send an e-mail (Alibaba.com, TradeWheel ...). Each enquiry is **registered
  first in the CRM** as a Sales enquiry (`crm_link.register_enquiry`, an IDC_ number, no SMS or mail to the customer), and
  the lead is made from it. `sales_inbound` remembers what each connection already brought in.
* Keys and passwords are stored encrypted (`secrets_box.py`, key from `SALES_SECRET_KEY`, else `JWT_SECRET`) and are never sent
  to a browser. If that key changes, saved keys cannot be read and must be typed again.
* The connections are written from each company's published way of working and tested with sample answers only. They have not
  been run with real accounts: use "Test" on the Connections screen after saving one.
* `importer.py` reads .xlsx (no extra library) and .csv. A loaded lead list makes leads directly (not registered in the CRM
  complaints). A loaded company list (Kompass, import records, a chamber list) goes into `sales_prospect`, is searched on the
  Export desk, and becomes a cold lead only when someone presses "Make lead".

## Not built yet

* Direct connections to Alibaba.com's own seller API, JustDial, TradeIndia and other marketplaces that need an approved app:
  use the mailbox, the any-API or the web-address connection for them.
