from __future__ import annotations

import io
import json
import unittest
import zipfile
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from sales_base import SalesTestBase
from app.models import Complaint
from app.sales import importer, sources as S
from app.sales.models import SalesInbound, SalesInboxLog, SalesLead, SalesProspect, SalesSource
from app.sales.secrets_box import seal, unseal


class FakeResponse:
    def __init__(self, payload, status_code=200, text=None):
        self._payload = payload
        self.status_code = status_code
        self.text = text if text is not None else (json.dumps(payload) if not isinstance(payload, str) else payload)
        self.content = self.text.encode("utf-8")

    def json(self):
        if isinstance(self._payload, str):
            raise ValueError("not json")
        return self._payload


class Web:
    """Stands in for the internet: the test says what each address answers, and what was asked."""

    def __init__(self):
        self.answers = {}
        self.calls = []

    def __call__(self, method, url, params=None, headers=None, json_body=None, data=None):
        self.calls.append({"method": method, "url": url, "params": params, "headers": headers, "json": json_body})
        for prefix, answer in self.answers.items():
            if url.startswith(prefix):
                return answer(params) if callable(answer) else answer
        return FakeResponse({"error": "unexpected address " + url}, 404)


IM_RECORD = {
    "UNIQUE_QUERY_ID": "2026101012345", "QUERY_TYPE": "W", "QUERY_TIME": "2026-10-10 11:20:30", "SENDER_NAME": "Himalaya Cool Traders",
    "SENDER_MOBILE": "+977-9851022334", "SENDER_EMAIL": "buyer@himalaya.example", "SENDER_COMPANY": "Himalaya Cool Traders Pvt Ltd",
    "SENDER_CITY": "Kathmandu", "SENDER_STATE": "Bagmati", "SENDER_COUNTRY_ISO": "NP", "QUERY_PRODUCT_NAME": "Split AC 1.5 Ton",
    "QUERY_MESSAGE": "I need 200 split ACs, please send the price FOB.",
}


def make_xlsx(rows):
    """A small real .xlsx file, so that the reader is tested on the format and not on a mock."""
    strings, cells = [], []

    def col(i):
        s = ""
        i += 1
        while i:
            i, r = divmod(i - 1, 26)
            s = chr(65 + r) + s
        return s

    for r, row in enumerate(rows, start=1):
        cs = []
        for c, v in enumerate(row):
            if isinstance(v, (int, float)):
                cs.append(f'<c r="{col(c)}{r}"><v>{v}</v></c>')
            else:
                strings.append(str(v))
                cs.append(f'<c r="{col(c)}{r}" t="s"><v>{len(strings) - 1}</v></c>')
        cells.append(f'<row r="{r}">{"".join(cs)}</row>')
    sheet = f'<?xml version="1.0"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>{"".join(cells)}</sheetData></worksheet>'
    sst = '<?xml version="1.0"?><sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">' + "".join(f"<si><t>{s}</t></si>" for s in strings) + "</sst>"
    wb = '<?xml version="1.0"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Leads" sheetId="1" r:id="rId1"/></sheets></workbook>'
    rels = '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="x" Target="worksheets/sheet1.xml"/></Relationships>'
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("xl/workbook.xml", wb)
        z.writestr("xl/_rels/workbook.xml.rels", rels)
        z.writestr("xl/sharedStrings.xml", sst)
        z.writestr("xl/worksheets/sheet1.xml", sheet)
    return buf.getvalue()


class ConnectionBase(SalesTestBase):
    def setUp(self):
        super().setUp()
        self.web = Web()
        self._orig_http = S.http
        S.http = self.web

    def tearDown(self):
        S.http = self._orig_http
        super().tearDown()

    def add_source(self, kind="indiamart", who=None, **body):
        payload = {"kind": kind, "name": body.pop("name", "Test connection"), **body}
        r = self.post("/api/sales/sources", payload, who or self.admin)
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()

    def complaints(self):
        self.db.expire_all()
        return list(self.db.scalars(select(Complaint).order_by(Complaint.id)))


# =========================== lead types ===========================
class LeadTypeTests(ConnectionBase):
    def test_the_eight_built_in_types_are_there_and_admin_changes_the_list(self):
        types = self.get("/api/sales/types", self.karan).json()
        self.assertEqual([t["key"] for t in types][:3], ["gem", "csd", "retail"])
        self.assertEqual(len(types), 8)
        self.assertEqual(self.post("/api/sales/types", {"label": "Hotel chain", "color": "#aa3355"}, self.karan).status_code, 403)
        r = self.post("/api/sales/types", {"label": "Hotel chain", "color": "#AA3355"}, self.admin)
        self.assertEqual(r.status_code, 201, r.text)
        key = r.json()["key"]
        self.assertEqual((key, r.json()["color"], r.json()["builtin"]), ("hotel_chain", "#aa3355", False))
        self.assertEqual(self.post("/api/sales/types", {"label": "hotel chain"}, self.admin).status_code, 400)  # same name
        self.assertEqual(self.post("/api/sales/types", {"label": "Bad colour", "color": "red"}, self.admin).status_code, 400)
        # it can be chosen on a lead, handled by a person, and it is named on the lead
        lead = self.new_lead(name="Taj Group", phone="98000 77001", lead_type=key)
        self.assertEqual((lead["lead_type"], lead["lead_type_label"], lead["lead_type_color"]), (key, "Hotel chain", "#aa3355"))
        self.assertEqual(self.put(f"/api/sales/team/{self.amit.id}/profile", {"types_handled": f"retail,{key}"}, self.karan).status_code, 200)
        self.assertIn(key, [t["key"] for t in self.get("/api/sales/status", self.amit).json()["lead_types"]])

    def test_rename_switch_off_and_the_last_one_stays(self):
        r = self.client.patch("/api/sales/types/export", json={"label": "Export (abroad)", "color": "#112233"}, headers=self.h(self.admin))
        self.assertEqual((r.status_code, r.json()["label"]), (200, "Export (abroad)"))
        lead = self.new_lead(name="Old export", phone="98000 77002", lead_type="export")
        self.assertEqual(lead["lead_type_label"], "Export (abroad)")
        r = self.client.patch("/api/sales/types/export", json={"is_active": False}, headers=self.h(self.admin))
        self.assertFalse(r.json()["active"])
        self.assertNotIn("export", [t["key"] for t in self.get("/api/sales/status", self.karan).json()["lead_types"]])
        # a type that is off cannot be chosen, but a lead that has it keeps it
        self.assertEqual(self.post("/api/sales/leads", {"name": "x", "phone": "98000 77003", "lead_type": "export"}, self.karan).status_code, 400)
        self.assertEqual(self.get(f"/api/sales/leads/{lead['id']}", self.karan).json()["lead_type"], "export")
        # the words alone no longer make an Export lead while it is off
        again = self.new_lead(name="Words only", phone="98000 77004", item="price FOB Mombasa for Kenya")
        self.assertEqual(again["lead_type"], "retail")
        # not the last one
        for t in self.get("/api/sales/types", self.admin).json():
            if t["key"] not in ("retail", "export"):
                self.client.patch(f"/api/sales/types/{t['key']}", json={"is_active": False}, headers=self.h(self.admin))
        r = self.client.patch("/api/sales/types/retail", json={"is_active": False}, headers=self.h(self.admin))
        self.assertEqual(r.status_code, 400)


# =========================== connections ===========================
class SourceTests(ConnectionBase):
    def test_keys_are_stored_locked_and_never_sent_back(self):
        s = self.add_source("indiamart", secret={"crm_key": "SUPER-SECRET-KEY-123"}, config={"mode": "pull"})
        self.assertEqual(s["secret_set"], {"crm_key": True})
        self.assertNotIn("SUPER-SECRET-KEY-123", json.dumps(self.get("/api/sales/sources", self.admin).json()))
        self.sdb.expire_all()
        row = self.sdb.get(SalesSource, s["id"])
        self.assertNotIn("SUPER-SECRET-KEY-123", row.secret)
        self.assertEqual(unseal(row.secret), {"crm_key": "SUPER-SECRET-KEY-123"})
        # an empty key on edit keeps the old one
        r = self.client.patch(f"/api/sales/sources/{s['id']}", json={"name": "IndiaMART main", "secret": {"crm_key": ""}}, headers=self.h(self.admin))
        self.assertEqual(r.status_code, 200)
        self.sdb.expire_all()
        self.assertEqual(unseal(self.sdb.get(SalesSource, s["id"]).secret)["crm_key"], "SUPER-SECRET-KEY-123")

    def test_needs_the_connect_tick_and_the_right_details(self):
        self.assertEqual(self.get("/api/sales/sources", self.karan).status_code, 403)
        self.put("/api/sales/ticks/user/%d" % self.karan.id, {"ticks": {"connect": True}}, self.admin)
        self.assertEqual(self.get("/api/sales/sources", self.karan).status_code, 200)
        self.assertEqual(self.post("/api/sales/sources", {"kind": "indiamart", "name": "x"}, self.karan).status_code, 400)  # no key
        self.assertEqual(self.post("/api/sales/sources", {"kind": "meta", "config": {"form_ids": "1"}}, self.karan).status_code, 400)  # no token
        self.assertEqual(self.post("/api/sales/sources", {"kind": "nonsense"}, self.karan).status_code, 400)
        self.assertEqual(self.post("/api/sales/sources", {"kind": "api", "config": {"url": "ftp://x"}}, self.karan).status_code, 400)
        self.assertEqual(self.post("/api/sales/sources", {"kind": "mailbox", "config": {"host": "imap.x"}}, self.karan).status_code, 400)
        self.assertEqual(self.post("/api/sales/sources", {"kind": "webhook", "name": "Landing page"}, self.karan).status_code, 201)

    def test_indiamart_pull_registers_first_then_makes_the_lead(self):
        s = self.add_source("indiamart", secret={"crm_key": "KEY1"}, default_owner_user_id=self.amit.id)
        self.web.answers[S.IM_URL] = FakeResponse({"CODE": 200, "STATUS": "SUCCESS", "TOTAL_RECORDS": 1, "RESPONSE": [IM_RECORD]})
        test = self.post(f"/api/sales/sources/{s['id']}/test", {}, self.admin).json()
        self.assertEqual((test["ok"], test["count"]), (True, 1))
        self.assertEqual(self.complaints(), [])  # a test makes nothing
        call = self.web.calls[-1]
        self.assertEqual(call["params"]["glusr_crm_key"], "KEY1")
        r = self.post(f"/api/sales/sources/{s['id']}/run", {}, self.admin).json()
        self.assertEqual((r["ok"], r["new"]), (True, 1))
        c = self.complaints()[0]
        self.assertTrue(c.comp_no.startswith("IDC_"))
        self.assertEqual((c.query_type, c.source, c.status, c.send_sms), ("Sales", "indiamart", "Pending", False))
        self.assertEqual(c.customer_mobile, "+9779851022334")
        self.assertIn("200 split ACs", c.problem_description)
        lead = self.get("/api/sales/leads", self.karan).json()["items"][0]
        self.assertEqual((lead["source"], lead["crm_ref"], lead["country"], lead["lead_type"], lead["owner_name"]), ("Test connection", c.comp_no, "Nepal", "export", "Amit Verma"))
        # the same enquiry is not made twice, here or by the minute sync
        self.assertEqual(self.post(f"/api/sales/sources/{s['id']}/run", {}, self.admin).json()["skipped"], 1)
        self.sync()
        self.assertEqual(self.get("/api/sales/leads", self.karan).json()["total"], 1)
        self.assertEqual(len(self.complaints()), 1)
        log = self.get("/api/sales/inbox-log", self.karan).json()
        self.assertIn(c.comp_no, log[0]["result"])
        shown = self.get("/api/sales/sources", self.admin).json()["items"][0]
        self.assertEqual((shown["received_count"], shown["last_error"]), (1, None))

    def test_indiamart_errors_are_kept_for_the_admin_to_read(self):
        s = self.add_source("indiamart", secret={"crm_key": "BAD"})
        self.web.answers[S.IM_URL] = FakeResponse({"CODE": 401, "STATUS": "FAILURE", "MESSAGE": "Invalid key"})
        r = self.post(f"/api/sales/sources/{s['id']}/run", {}, self.admin).json()
        self.assertFalse(r["ok"])
        self.assertIn("Invalid key", self.get("/api/sales/sources", self.admin).json()["items"][0]["last_error"])
        self.web.answers[S.IM_URL] = FakeResponse("<html>down</html>", 503)
        self.assertFalse(self.post(f"/api/sales/sources/{s['id']}/run", {}, self.admin).json()["ok"])

    def test_an_enquiry_without_a_phone_is_logged_not_made_a_lead(self):
        s = self.add_source("indiamart", secret={"crm_key": "K"})
        rec = {**IM_RECORD, "SENDER_MOBILE": "", "UNIQUE_QUERY_ID": "NOPHONE1"}
        self.web.answers[S.IM_URL] = FakeResponse({"CODE": 200, "RESPONSE": [rec]})
        r = self.post(f"/api/sales/sources/{s['id']}/run", {}, self.admin).json()
        self.assertEqual((r["no_phone"], r["new"]), (1, 0))
        self.assertEqual(self.complaints(), [])
        self.assertIn("No phone number", self.get("/api/sales/inbox-log", self.karan).json()[0]["result"])
        self.assertEqual(self.post(f"/api/sales/sources/{s['id']}/run", {}, self.admin).json()["skipped"], 1)

    def test_same_buyer_from_two_connections_is_one_lead(self):
        a = self.add_source("indiamart", name="IndiaMART", secret={"crm_key": "K"})
        b = self.add_source("webhook", name="Landing page")
        self.web.answers[S.IM_URL] = FakeResponse({"CODE": 200, "RESPONSE": [IM_RECORD]})
        self.post(f"/api/sales/sources/{a['id']}/run", {}, self.admin)
        r = self.client.post(b["webhook_path"], json={"name": "Himalaya Cool", "mobile": "+977 9851022334", "message": "asking again"})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["again"], 1)
        self.assertEqual(self.get("/api/sales/leads", self.karan).json()["total"], 1)
        self.assertEqual(len(self.complaints()), 2)  # both were registered first

    def test_web_address_takes_posts_json_and_forms_and_checks_the_token(self):
        s = self.add_source("webhook", name="Landing page", default_lead_type="dealer")
        path = s["webhook_path"]
        self.assertEqual(self.client.post("/api/sales/in/not-a-real-token", json={"name": "x", "phone": "9800000000"}).status_code, 404)
        r = self.client.post(path, json={"full_name": "Gupta Electricals", "phone_number": "98111 22334", "message": "price for 20 ACs", "city": "Noida", "id": "L-1"})
        self.assertEqual((r.status_code, r.json()["new"]), (200, 1))
        r = self.client.post(path, data={"name": "Form Person", "mobile": "98111 55555", "message": "form post"})
        self.assertEqual((r.status_code, r.json()["new"]), (200, 1))
        r = self.client.post(path, json={"leads": [{"name": "A", "phone": "98100 00001"}, {"name": "B", "phone": "98100 00002"}]})
        self.assertEqual(r.json()["new"], 2)
        self.assertEqual({l["lead_type"] for l in self.get("/api/sales/leads", self.karan).json()["items"]}, {"dealer"})
        self.assertEqual(self.client.post(path, json={"id": "L-1", "name": "Gupta Electricals", "phone": "98111 22334"}).json()["skipped"], 1)
        # switched off, the address stops answering
        self.client.patch(f"/api/sales/sources/{s['id']}", json={"is_active": False}, headers=self.h(self.admin))
        self.assertEqual(self.client.post(path, json={"name": "x", "phone": "98100 00009"}).status_code, 404)

    def test_indiamart_push_format(self):
        s = self.add_source("indiamart", secret={"crm_key": "K"}, config={"mode": "push"})
        r = self.client.post(s["webhook_path"], json={"CODE": 200, "STATUS": "SUCCESS", "RESPONSE": IM_RECORD})
        self.assertEqual((r.status_code, r.json()["new"]), (200, 1))
        self.assertEqual(self.get("/api/sales/leads", self.karan).json()["items"][0]["country"], "Nepal")

    def test_meta_pull_and_webhook(self):
        s = self.add_source("meta", secret={"page_token": "PAGE-TOKEN"}, config={"form_ids": "111, 222"})
        self.assertTrue(s["verify_token_set"])
        lead_json = {"id": "9001", "created_time": "2026-10-10T05:00:00+0000", "form_id": "111", "campaign_name": "Diwali AC offer",
                     "field_data": [{"name": "full_name", "values": ["Pankaj Jain"]}, {"name": "phone_number", "values": ["+91 98270 11990"]},
                                    {"name": "city", "values": ["Indore"]}, {"name": "how_many_acs_do_you_need?", "values": ["3"]}]}
        self.web.answers[S.META_URL + "/111/leads"] = FakeResponse({"data": [lead_json]})
        self.web.answers[S.META_URL + "/222/leads"] = FakeResponse({"data": []})
        r = self.post(f"/api/sales/sources/{s['id']}/run", {}, self.admin).json()
        self.assertEqual((r["ok"], r["new"]), (True, 1), r)
        lead = self.get("/api/sales/leads", self.karan).json()["items"][0]
        self.assertEqual((lead["name"], lead["phone"], lead["district"]), ("Pankaj Jain", "9827011990", "Indore"))
        self.assertIn("how_many_acs_do_you_need?: 3", lead["message"])
        self.assertIn("Diwali AC offer", lead["message"])
        # the webhook: Meta checks it, then sends the lead number and Sales fetches the lead
        tok = unseal(self.sdb.get(SalesSource, s["id"]).secret)["verify_token"]
        self.assertEqual(self.client.get(s["webhook_path"], params={"hub.mode": "subscribe", "hub.verify_token": "wrong", "hub.challenge": "42"}).status_code, 403)
        ok = self.client.get(s["webhook_path"], params={"hub.mode": "subscribe", "hub.verify_token": tok, "hub.challenge": "42"})
        self.assertEqual((ok.status_code, ok.text), (200, "42"))
        second = {**lead_json, "id": "9002", "field_data": [{"name": "full_name", "values": ["Second Person"]}, {"name": "phone_number", "values": ["98270 22222"]}]}
        self.web.answers[S.META_URL + "/9002"] = FakeResponse(second)
        r = self.client.post(s["webhook_path"], json={"object": "page", "entry": [{"changes": [{"field": "leadgen", "value": {"leadgen_id": "9002", "form_id": "111"}}]}]})
        self.assertEqual((r.status_code, r.json()["new"]), (200, 1), r.text)
        self.assertEqual(self.web.calls[-1]["params"]["access_token"], "PAGE-TOKEN")

    def test_any_api_with_a_header_key_and_a_map_of_fields(self):
        s = self.add_source("api", name="Supplier portal", secret={"header_name": "X-Api-Key", "header_value": "abc123"},
                            config={"url": "https://api.example.com/inquiries", "list_path": "data.items", "mapping": {"external_id": "ref", "name": "buyer.company", "phone": "buyer.tel", "message": "text", "country": "buyer.country"}})
        self.web.answers["https://api.example.com/inquiries"] = FakeResponse({"data": {"items": [{"ref": "RFQ-1", "buyer": {"company": "Accra Home Appliances", "tel": "+233 24 411 7788", "country": "Ghana"}, "text": "80 deep freezers CIF Tema"}]}})
        r = self.post(f"/api/sales/sources/{s['id']}/run", {}, self.admin).json()
        self.assertEqual((r["ok"], r["new"]), (True, 1), r)
        self.assertEqual(self.web.calls[-1]["headers"], {"X-Api-Key": "abc123"})
        lead = self.get("/api/sales/leads", self.karan).json()["items"][0]
        self.assertEqual((lead["name"], lead["country"], lead["lead_type"], lead["phone"]), ("Accra Home Appliances", "Ghana", "export", "+233244117788"))
        self.web.answers["https://api.example.com/inquiries"] = FakeResponse({"oops": 1})
        self.assertIn("path to the list", self.post(f"/api/sales/sources/{s['id']}/run", {}, self.admin).json()["error"])

    def test_google_sheet_csv(self):
        s = self.add_source("sheet", name="Expo visitors", config={"csv_url": "https://docs.google.com/spreadsheets/d/e/abc/pub?output=csv"})
        csv_text = "Name,Mobile,City,Product,Message\nAnand Electricals,98100 77881,Jaipur,Water cooler,10 pieces\nNo Phone,,Delhi,Fan,x\n"
        self.web.answers["https://docs.google.com/"] = FakeResponse(csv_text)
        r = self.post(f"/api/sales/sources/{s['id']}/run", {}, self.admin).json()
        self.assertEqual((r["ok"], r["new"]), (True, 1), r)
        self.assertEqual(self.post(f"/api/sales/sources/{s['id']}/run", {}, self.admin).json()["skipped"], 1)

    def test_only_connections_that_are_due_run_by_themselves(self):
        s = self.add_source("indiamart", secret={"crm_key": "K"}, interval_minutes=30)
        self.web.answers[S.IM_URL] = FakeResponse({"CODE": 200, "RESPONSE": [IM_RECORD]})
        self.assertEqual(S.run_due_sources(self.db, self.sdb), 1)
        self.assertEqual(S.run_due_sources(self.db, self.sdb), 0)  # just ran
        src = self.sdb.get(SalesSource, s["id"])
        src.last_run_at = datetime.now(timezone.utc) - timedelta(minutes=31)
        self.sdb.commit()
        self.assertEqual(S.run_due_sources(self.db, self.sdb), 1)
        self.client.patch(f"/api/sales/sources/{s['id']}", json={"is_active": False}, headers=self.h(self.admin))
        self.sdb.expire_all()
        self.sdb.get(SalesSource, s["id"]).last_run_at = None
        self.sdb.commit()
        self.assertEqual(S.run_due_sources(self.db, self.sdb), 0)
        # IndiaMART allows one call every 5 minutes, so it never runs sooner than 6
        again = self.client.patch(f"/api/sales/sources/{s['id']}", json={"interval_minutes": 5}, headers=self.h(self.admin)).json()
        self.assertEqual(again["interval_minutes"], 6)

    def test_new_token_replaces_the_address(self):
        s = self.add_source("webhook", name="Tool")
        old = s["webhook_path"]
        new = self.post(f"/api/sales/sources/{s['id']}/new-token", {}, self.admin).json()["webhook_path"]
        self.assertNotEqual(old, new)
        self.assertEqual(self.client.post(old, json={"name": "x", "phone": "98100 00001"}).status_code, 404)
        self.assertEqual(self.client.post(new, json={"name": "x", "phone": "98100 00001"}).status_code, 200)

    def test_secrets_box(self):
        text = seal({"a": "1"})
        self.assertNotIn("1", text.replace("=", "")[:6])
        self.assertEqual(unseal(text), {"a": "1"})
        self.assertEqual(unseal("not a real token"), {})
        self.assertEqual(unseal(None), {})


class MailParserTests(unittest.TestCase):
    def test_a_marketplace_mail_with_labelled_lines(self):
        body = ("You have a new inquiry\n\nName: Kofi Mensah\nCompany: Tema Cool Imports Ltd\nCountry/Region: Ghana\n"
                "Product: Split Air Conditioner 1.5 Ton\nQuantity: 120 pieces\nTel: +233 30 320 4417\nEmail: kofi@temacool.example\n"
                "Message: Please quote CIF Tema, payment by LC.\n\nReply to this inquiry on the marketplace.")
        inc = S.parse_inquiry_mail("Inquiry about Split Air Conditioner", "Alibaba <noreply@notice.alibaba.com>", body, ["alibaba.com"])
        self.assertEqual((inc.name, inc.company, inc.country), ("Kofi Mensah", "Tema Cool Imports Ltd", "Ghana"))
        self.assertEqual((inc.phone, inc.email), ("+233 30 320 4417", "kofi@temacool.example"))
        self.assertIn("CIF Tema", inc.message)
        self.assertIn("Quantity: 120", inc.message)
        self.assertIn("Split Air Conditioner", inc.product)

    def test_a_mail_without_labels_still_gets_a_phone_and_an_address(self):
        body = "<p>Hello, I am Sunil from Colombo. I want 150 ACs. Call me on +94 77 310 4455 or write to sunil@lankacool.example</p>"
        inc = S.parse_inquiry_mail("Re: Inquiry for AC", "TradeWheel <info@tradewheel.com>", body, ["tradewheel.com"])
        self.assertEqual(inc.phone, "+94 77 310 4455")
        self.assertEqual(inc.email, "sunil@lankacool.example")
        self.assertIn("check the details", inc.message.lower())

    def test_a_mail_with_nothing_to_use_is_dropped(self):
        self.assertIsNone(S.parse_inquiry_mail("Newsletter", "x@x.com", "Hello", ["x.com"]))


# =========================== files and lists ===========================
class UploadTests(ConnectionBase):
    CSV = ("Name,Phone Number,City,State,Product,Remarks\n"
           "Meena Traders,99110 55667,Noida,Uttar Pradesh,Deep freezer 300 L x 15,wants price\n"
           "Vijay Enterprises,98230 44556,Pune,Maharashtra,Water cooler x 25,\n"
           ",,Delhi,Delhi,no name or phone,\n"
           "Meena Again,99110 55667,Noida,Uttar Pradesh,again,\n").encode("utf-8")

    def preview(self, name, data, who=None):
        return self.client.post("/api/sales/uploads/preview", files={"file": (name, data)}, headers=self.h(who or self.karan))

    def do_import(self, name, data, options, who=None):
        return self.client.post("/api/sales/uploads/import", files={"file": (name, data)}, data={"options": json.dumps(options)}, headers=self.h(who or self.karan))

    def test_csv_preview_guesses_the_columns(self):
        r = self.preview("leads.csv", self.CSV)
        self.assertEqual(r.status_code, 200, r.text)
        out = r.json()
        self.assertEqual((out["total"], out["mapping"]["name"], out["mapping"]["phone"], out["mapping"]["place"], out["mapping"]["item"]), (4, "Name", "Phone Number", "City", "Product"))
        self.assertEqual(self.preview("leads.xls", b"x").status_code, 400)
        self.assertEqual(self.preview("leads.csv", b"Name,Phone\n").status_code, 400)
        self.assertEqual(self.preview("leads.csv", self.CSV, self.amit).status_code, 403)  # no upload tick

    def test_import_makes_leads_skips_bad_rows_and_joins_the_same_phone(self):
        mapping = self.preview("leads.csv", self.CSV).json()["mapping"]
        r = self.do_import("leads.csv", self.CSV, {"mapping": mapping, "source_label": "Expo 2026", "lead_type": "retail"})
        self.assertEqual(r.status_code, 200, r.text)
        out = r.json()
        self.assertEqual((out["created"], out["again"], out["skipped"]), (2, 1, 1))
        self.assertIn("Row 4", out["errors"][0])
        items = self.get("/api/sales/leads", self.karan).json()["items"]
        self.assertEqual({l["source"] for l in items}, {"Expo 2026"})
        self.assertEqual({l["channel"] for l in items}, {"file"})
        self.assertEqual(len(self.complaints()), 0)  # a loaded list is not an enquiry: nothing is registered in the CRM
        self.assertEqual(self.do_import("leads.csv", self.CSV, {"mapping": mapping, "lead_type": "nonsense"}).status_code, 400)

    def test_real_xlsx_file(self):
        data = make_xlsx([["Name", "Mobile", "Country", "Product", "Value"], ["Lanka Cool Mart", "+94 77 310 4455", "Sri Lanka", "Split AC 1 Ton x 150", 30], ["Kenya Buyer", 254722114880, "Kenya", "Window AC", 12.5]])
        cols, rows = importer.read_table("x.xlsx", data)
        self.assertEqual(cols, ["Name", "Mobile", "Country", "Product", "Value"])
        self.assertEqual(rows[1]["Mobile"], "254722114880")
        pre = self.preview("x.xlsx", data).json()
        self.assertEqual((pre["total"], pre["mapping"]["country"], pre["mapping"]["phone"]), (2, "Country", "Mobile"))
        r = self.do_import("x.xlsx", data, {"mapping": pre["mapping"]}).json()
        self.assertEqual(r["created"], 2)
        lead = [l for l in self.get("/api/sales/leads", self.karan).json()["items"] if l["name"] == "Lanka Cool Mart"][0]
        self.assertEqual((lead["lead_type"], lead["country"], lead["value_lakh"]), ("export", "Sri Lanka", 30.0))

    def test_company_lists_for_the_export_market(self):
        csv_text = ("Company,Country,City,Type,Products,Phone,Email,Evidence\n"
                    "Himal Appliances Pvt Ltd,Nepal,Kathmandu,Importer,Air conditioners,+977 1 4228 774,info@himal.example,5 shipments in 12 months\n"
                    "Colombo Electro Mart,Sri Lanka,Colombo,Importer,Air conditioners; refrigerators,+94 11 2437 620,,Listed in the Rainbow Pages\n"
                    "Lanka Air Systems,Sri Lanka,Colombo,Distributor,Split ACs,,,7 shipments\n"
                    "No Country Ltd,,,Importer,ACs,+1 555 0100,,\n").encode()
        pre = self.preview("kompass.csv", csv_text).json()
        self.assertEqual(pre["mapping"]["company"], "Company")
        r = self.do_import("kompass.csv", csv_text, {"mode": "prospects", "mapping": pre["mapping"], "source_label": "Kompass export"}).json()
        self.assertEqual((r["added"], r["duplicates"]), (3, 0))
        self.assertEqual(self.do_import("kompass.csv", csv_text, {"mode": "prospects", "mapping": pre["mapping"]}).json()["duplicates"], 3)
        found = self.get("/api/sales/prospects", self.karan, params={"country": "sri lanka", "product": "refrigerator"}).json()
        self.assertEqual([p["company"] for p in found["items"]], ["Colombo Electro Mart"])
        facets = self.get("/api/sales/prospects/facets", self.karan).json()
        self.assertEqual(set(facets["countries"]), {"Nepal", "Sri Lanka"})
        everyone = self.get("/api/sales/prospects", self.karan).json()["items"]
        ids = [p["id"] for p in everyone]
        made = self.post("/api/sales/prospects/make-leads", {"ids": ids}, self.karan).json()
        self.assertEqual((made["made"], made["no_phone"]), (2, 1))  # the one without a phone number waits
        leads = self.get("/api/sales/leads", self.karan).json()["items"]
        self.assertTrue(all(l["lead_type"] == "export" and l["is_prospect"] and l["heat"] == "cold" for l in leads))
        self.assertEqual(self.post("/api/sales/prospects/make-leads", {"ids": ids}, self.karan).json()["made"], 0)  # not twice
        self.assertEqual(len(self.complaints()), 0)
        # a list loaded by mistake can be removed, except what became a lead
        batch = facets["batches"][0]["batch"]
        gone = self.client.delete(f"/api/sales/prospects/batch/{batch}", headers=self.h(self.karan)).json()
        self.assertEqual(gone["deleted"], 1)
        self.assertEqual(self.get("/api/sales/prospects", self.amit).status_code, 403)

    def test_a_team_member_with_no_upload_tick_cannot_import(self):
        mapping = self.preview("leads.csv", self.CSV).json()["mapping"]
        self.assertEqual(self.do_import("leads.csv", self.CSV, {"mapping": mapping}, self.amit).status_code, 403)


# =========================== the team list, and the database update ===========================
class TeamAndMigrationTests(ConnectionBase):
    def test_a_role_written_in_capitals_is_still_a_sales_person(self):
        self.amit.role = "SALES"
        self.db.commit()
        team = self.get("/api/sales/team", self.karan).json()
        self.assertIn("sales", {p["role"] for p in team})
        lead = self.new_lead(name="Capital", phone="98000 55001", state="Uttar Pradesh")
        self.assertIn(lead["owner_name"], ("Amit Verma", "Pooja Singh"))
        r = self.post(f"/api/sales/leads/{lead['id']}/give", {"owner_user_id": self.amit.id}, self.karan)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertIn("add_lead", self.get("/api/sales/status", self.amit).json()["ticks"])

    def test_the_database_update_adds_the_new_tables_and_the_eight_types(self):
        import tempfile
        from pathlib import Path
        from alembic import command
        from alembic.config import Config
        from sqlalchemy import create_engine, inspect, text
        from app.config import settings

        tmp = Path(tempfile.mkdtemp()) / "sales_mig.db"
        old = settings.sales_database_url
        settings.sales_database_url = f"sqlite:///{tmp.as_posix()}"
        try:
            cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic_sales.ini"))
            cfg.set_main_option("script_location", str(Path(__file__).resolve().parents[1] / "sales_alembic"))
            command.upgrade(cfg, "head")
            eng = create_engine(settings.sales_database_url)
            names = set(inspect(eng).get_table_names())
            for t in ("sales_lead_type", "sales_source", "sales_inbound", "sales_prospect", "sales_lead", "sales_quotation"):
                self.assertIn(t, names)
            with eng.connect() as c:
                self.assertEqual(c.execute(text("select count(*) from sales_lead_type where is_builtin=1")).scalar(), 8)
                self.assertEqual(c.execute(text("select version_num from sales_alembic_version")).scalar(), "0004_sales_profile_coverage")
            eng.dispose()
            command.downgrade(cfg, "0001_sales_initial")
            eng = create_engine(settings.sales_database_url)
            self.assertNotIn("sales_source", set(inspect(eng).get_table_names()))
            eng.dispose()
        finally:
            settings.sales_database_url = old


if __name__ == "__main__":
    unittest.main()
