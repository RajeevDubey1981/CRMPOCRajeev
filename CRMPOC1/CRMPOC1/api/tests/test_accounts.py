from __future__ import annotations

import os
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("MYSQL_DATABASE_URL", "sqlite://")
os.environ.setdefault("SITE_API_KEY", "k")
os.environ.setdefault("SARVAM_API_KEY", "k")
os.environ.setdefault("BOUNCE_CHECK_ENABLED", "false")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (registers every table)
from app.database import Base, get_db
from app.deps import get_current_user
from app.main import app as fastapi_app
from app.models.item_master import ItemMaster
from app.models.store import StoreLedger, StoreStock
from app.models.user import User
from app.seed import seed_roles

UP_GSTIN = "09ABCDE1234F1Z5"
HR_GSTIN = "06ABCDE1234F1Z5"


class AccountsTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False, future=True)
        db = self.Session()
        seed_roles(db)
        db.commit()
        self.users = {}
        for name, role in [
            ("keeper", "store_keeper"), ("manager", "store_manager"), ("boss", "admin"), ("accmgr", "accounts_manager"),
            ("accmgr2", "accounts_manager"), ("accexec", "accounts_executive"), ("buyer", "purchase_officer"),
            ("auditor", "auditor"), ("caller", "callcenter"),
        ]:
            u = User(name=name.title(), email=f"{name}@test.com", password_hash="x", role=role, is_active=True)
            db.add(u)
            self.users[name] = u
        self.ac = ItemMaster(item_code="AC15", item_name="Split AC 1.5T", serial_count=2, is_active=True, source="Make", hsn_code="8415", gst_rate=18)
        self.cmp = ItemMaster(item_code="CMP15", item_name="Compressor 1.5T", serial_count=1, is_active=True, source="Buy", hsn_code="8414", gst_rate=18)
        self.fan = ItemMaster(item_code="FAN01", item_name="Fan motor", serial_count=0, is_active=True, source="Buy", hsn_code="8501", gst_rate=18)
        db.add_all([self.ac, self.cmp, self.fan])
        db.commit()
        self.db = db
        self.current = "accexec"

        def _db():
            s = self.Session()
            try:
                yield s
            finally:
                s.close()

        fastapi_app.dependency_overrides[get_db] = _db
        fastapi_app.dependency_overrides[get_current_user] = lambda: self.users[self.current]
        self.c = TestClient(fastapi_app)

    def tearDown(self):
        fastapi_app.dependency_overrides.clear()
        self.db.close()
        self.engine.dispose()

    def as_(self, who):
        self.current = who

    # helpers ---------------------------------------------------------------
    def supplier(self, name="Cool Parts", gstin=UP_GSTIN, **kw):
        self.as_("accexec")
        body = {"name": name, "gstin": gstin, "payment_terms_days": 30, **kw}
        r = self.c.post("/api/accounts/suppliers", json=body)
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()

    def po_body(self, sup_id, lines=None, po_date="2026-10-04"):
        return {
            "supplier_id": sup_id,
            "po_date": po_date,
            "lines": lines if lines is not None else [{"item_id": self.cmp.id, "qty": 10, "rate": 4000}],
        }

    def approved_po(self, lines=None, sup=None):
        sup = sup or self.supplier()
        self.as_("accexec")
        po = self.c.post("/api/accounts/pos", json=self.po_body(sup["id"], lines)).json()
        self.assertEqual(self.c.post(f"/api/accounts/pos/{po['id']}/submit").status_code, 200)
        self.as_("accmgr")
        r = self.c.post(f"/api/accounts/pos/{po['id']}/approve")
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def receive(self, lines, ref="BILL/1", po_id=None):
        self.as_("keeper")
        body = {"source_type": "Purchase", "supplier_name": "Cool Parts", "reference_no": ref, "lines": lines}
        if po_id:
            body["po_id"] = po_id
        g = self.c.post("/api/store/grns", json=body)
        self.assertEqual(g.status_code, 201, g.text)
        gid = g.json()["id"]
        sub = self.c.post(f"/api/store/grns/{gid}/submit")
        if sub.status_code != 200:
            return sub
        self.as_("manager")
        return self.c.post(f"/api/store/grns/{gid}/approve")

    def spare_lines(self, serials, fans=0, cost=4000, fan_cost=500):
        out = [{"item_id": self.cmp.id, "stock_type": "Spare", "serial_no": s, "unit_cost": cost} for s in serials]
        if fans:
            out.append({"item_id": self.fan.id, "stock_type": "Spare", "qty": fans, "unit_cost": fan_cost})
        return out

    def make_bom(self, activate=True):
        self.as_("buyer")
        r = self.c.post(
            "/api/accounts/boms",
            json={
                "item_id": self.ac.id, "labour_cost": 500, "overhead_cost": 250,
                "lines": [{"component_item_id": self.cmp.id, "qty": 1}, {"component_item_id": self.fan.id, "qty": 2}],
            },
        )
        self.assertEqual(r.status_code, 201, r.text)
        bom = r.json()
        if activate:
            self.as_("accmgr")
            a = self.c.post(f"/api/accounts/boms/{bom['id']}/activate")
            self.assertEqual(a.status_code, 200, a.text)
            bom = a.json()
        return bom

    # suppliers -------------------------------------------------------------
    def test_supplier_gstin_rules(self):
        s = self.supplier()
        self.assertEqual(s["state"], "Uttar Pradesh")
        self.assertEqual(s["pan"], "ABCDE1234F")
        self.assertTrue(s["registered"])
        dup = self.c.post("/api/accounts/suppliers", json={"name": "Again", "gstin": UP_GSTIN})
        self.assertEqual(dup.status_code, 409)
        bad = self.c.post("/api/accounts/suppliers", json={"name": "Bad", "gstin": "NOTAGSTIN"})
        self.assertEqual(bad.status_code, 400)
        self.assertEqual(self.c.post("/api/accounts/suppliers", json={"name": "No state"}).status_code, 400)
        small = self.c.post("/api/accounts/suppliers", json={"name": "Small shop", "state": "Delhi", "is_msme": True, "msme_no": "UDYAM-1"})
        self.assertEqual(small.status_code, 201, small.text)
        self.assertFalse(small.json()["registered"])
        self.assertEqual(small.json()["state_code"], "07")

    # purchase orders -------------------------------------------------------
    def test_po_gst_split_by_state_and_numbering(self):
        up = self.supplier()
        hr = self.supplier("Delta Cooling", HR_GSTIN)
        self.as_("accexec")
        a = self.c.post("/api/accounts/pos", json=self.po_body(up["id"])).json()
        self.assertEqual(a["po_no"], "PO/26-27/0001")
        self.assertTrue(a["intra_state"])
        self.assertEqual((a["taxable_value"], a["cgst"], a["sgst"], a["igst"], a["total"]), ("40000.00", "3600.00", "3600.00", "0.00", "47200.00"))
        b = self.c.post("/api/accounts/pos", json=self.po_body(hr["id"])).json()
        self.assertEqual(b["po_no"], "PO/26-27/0002")
        self.assertFalse(b["intra_state"])
        self.assertEqual((b["cgst"], b["sgst"], b["igst"], b["total"]), ("0.00", "0.00", "7200.00", "47200.00"))
        old = self.c.post("/api/accounts/pos", json=self.po_body(up["id"], po_date="2026-03-31")).json()
        self.assertEqual(old["po_no"], "PO/25-26/0001")  # the financial year runs April to March

    def test_po_lifecycle_and_maker_checker(self):
        sup = self.supplier()
        self.as_("accmgr")
        po = self.c.post("/api/accounts/pos", json=self.po_body(sup["id"])).json()
        self.assertEqual(self.c.post(f"/api/accounts/pos/{po['id']}/submit").status_code, 200)
        own = self.c.post(f"/api/accounts/pos/{po['id']}/approve")
        self.assertEqual(own.status_code, 403)
        self.assertIn("someone else", own.json()["detail"])
        self.as_("accexec")
        self.assertEqual(self.c.post(f"/api/accounts/pos/{po['id']}/approve").status_code, 403)  # no approval right
        self.as_("accmgr2")
        sent_back = self.c.post(f"/api/accounts/pos/{po['id']}/reject", json={"reason": "Rate too high"}).json()
        self.assertEqual(sent_back["status"], "Draft")
        self.assertIn("Rate too high", sent_back["reject_reason"])
        self.as_("accmgr")
        lines = [{"item_id": self.cmp.id, "qty": 10, "rate": 3800}]
        fixed = self.c.put(f"/api/accounts/pos/{po['id']}", json=self.po_body(sup["id"], lines))
        self.assertEqual(fixed.status_code, 200, fixed.text)
        self.c.post(f"/api/accounts/pos/{po['id']}/submit")
        self.as_("accmgr2")
        ok = self.c.post(f"/api/accounts/pos/{po['id']}/approve").json()
        self.assertEqual(ok["status"], "Approved")
        self.as_("accmgr")
        self.assertEqual(self.c.put(f"/api/accounts/pos/{po['id']}", json=self.po_body(sup["id"])).status_code, 409)

    def test_po_needs_a_rate_and_lines_to_submit(self):
        sup = self.supplier()
        self.as_("accexec")
        empty = self.c.post("/api/accounts/pos", json=self.po_body(sup["id"], [])).json()
        self.assertEqual(self.c.post(f"/api/accounts/pos/{empty['id']}/submit").status_code, 400)
        free = self.c.post("/api/accounts/pos", json=self.po_body(sup["id"], [{"item_id": self.cmp.id, "qty": 1, "rate": 0}])).json()
        self.assertEqual(self.c.post(f"/api/accounts/pos/{free['id']}/submit").status_code, 400)

    def test_cancel_po(self):
        po = self.approved_po()
        self.as_("accexec")
        r = self.c.post(f"/api/accounts/pos/{po['id']}/cancel", json={"reason": "Wrong supplier"})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["status"], "Cancelled")

    def test_permissions(self):
        self.as_("keeper")
        self.assertEqual(self.c.get("/api/accounts/pos").status_code, 403)
        self.as_("caller")
        self.assertEqual(self.c.get("/api/accounts/suppliers").status_code, 403)
        self.as_("auditor")
        self.assertEqual(self.c.get("/api/accounts/pos").status_code, 200)
        self.assertEqual(self.c.post("/api/accounts/suppliers", json={"name": "X", "state": "Delhi"}).status_code, 403)
        self.as_("buyer")
        po = self.c.post("/api/accounts/pos", json=self.po_body(self.supplier()["id"]))
        self.assertEqual(po.status_code, 201)
        self.as_("accexec")
        self.assertEqual(self.c.post("/api/accounts/boms", json={"item_id": self.ac.id, "lines": []}).status_code, 403)

    # GRN against a PO -------------------------------------------------------
    def test_grn_against_po_tracks_what_is_outstanding(self):
        po = self.approved_po()
        r = self.receive(self.spare_lines(["CMP-1", "CMP-2", "CMP-3", "CMP-4"]), po_id=po["id"])
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["po_no"], po["po_no"])
        self.as_("accexec")
        got = self.c.get(f"/api/accounts/pos/{po['id']}").json()
        self.assertEqual(got["status"], "Part received")
        self.assertEqual((got["lines"][0]["received_qty"], got["lines"][0]["outstanding"]), (4, 6))
        over = self.receive(self.spare_lines([f"CMP-{n}" for n in range(10, 17)]), ref="B2", po_id=po["id"])
        self.assertEqual(over.status_code, 409)
        self.assertIn("outstanding", over.json()["detail"])
        rest = self.receive(self.spare_lines([f"CMP-{n}" for n in range(20, 26)]), ref="B3", po_id=po["id"])
        self.assertEqual(rest.status_code, 200, rest.text)
        self.as_("accexec")
        self.assertEqual(self.c.get(f"/api/accounts/pos/{po['id']}").json()["status"], "Received")
        self.assertEqual(self.c.post(f"/api/accounts/pos/{po['id']}/cancel", json={"reason": "x"}).status_code, 409)

    def test_stock_received_against_a_po_takes_the_po_rate_as_cost(self):
        po = self.approved_po()
        lines = [{"item_id": self.cmp.id, "stock_type": "Spare", "serial_no": "CMP-1"}]
        self.assertEqual(self.receive(lines, po_id=po["id"]).status_code, 200)
        db = self.Session()
        self.assertEqual(str(db.scalar(select(StoreStock.unit_cost).where(StoreStock.serial_no == "CMP-1"))), "4000.00")
        db.close()

    def test_grn_against_po_rejects_other_items_and_unapproved_pos(self):
        po = self.approved_po()
        wrong = self.receive([{"item_id": self.fan.id, "stock_type": "Spare", "qty": 2}], po_id=po["id"])
        self.assertEqual(wrong.status_code, 409)
        self.assertIn("not on", wrong.json()["detail"])
        sup = self.supplier("Other", HR_GSTIN)
        self.as_("accexec")
        draft = self.c.post("/api/accounts/pos", json=self.po_body(sup["id"])).json()
        self.as_("keeper")
        r = self.c.post("/api/store/grns", json={"source_type": "Purchase", "po_id": draft["id"], "lines": []})
        self.assertEqual(r.status_code, 409)
        self.as_("keeper")
        listing = self.c.get("/api/accounts/pos/open").json()
        self.assertEqual([p["po_no"] for p in listing], [po["po_no"]])

    # BOM ---------------------------------------------------------------------
    def test_bom_needs_make_source_and_activation_retires_the_old_version(self):
        self.as_("buyer")
        r = self.c.post("/api/accounts/boms", json={"item_id": self.cmp.id, "lines": []})
        self.assertEqual(r.status_code, 409)
        v1 = self.make_bom()
        self.assertEqual((v1["version"], v1["status"]), (1, "Active"))
        self.as_("buyer")
        v2 = self.c.post(f"/api/accounts/boms/{v1['id']}/copy").json()
        self.assertEqual((v2["version"], v2["status"]), (2, "Draft"))
        self.assertEqual(self.c.post(f"/api/accounts/boms/{v2['id']}/activate").status_code, 403)  # the buyer drafts, the manager activates
        self.as_("accmgr")
        self.c.post(f"/api/accounts/boms/{v2['id']}/activate")
        self.assertEqual(self.c.get(f"/api/accounts/boms/{v1['id']}").json()["status"], "Retired")
        self.assertEqual(self.c.put(f"/api/accounts/boms/{v1['id']}", json={"lines": []}).status_code, 409)

    def test_bom_line_rules(self):
        self.as_("buyer")
        dup = self.c.post("/api/accounts/boms", json={"item_id": self.ac.id, "lines": [{"component_item_id": self.fan.id, "qty": 1}, {"component_item_id": self.fan.id, "qty": 2}]})
        self.assertEqual(dup.status_code, 400)
        selfref = self.c.post("/api/accounts/boms", json={"item_id": self.ac.id, "lines": [{"component_item_id": self.ac.id, "qty": 1}]})
        self.assertEqual(selfref.status_code, 400)
        db = self.Session()
        db.get(ItemMaster, self.cmp.id).source = "Make"
        db.commit()
        db.close()
        first = self.c.post("/api/accounts/boms", json={"item_id": self.ac.id, "lines": [{"component_item_id": self.cmp.id, "qty": 1}]})
        self.assertEqual(first.status_code, 201, first.text)
        loop = self.c.post("/api/accounts/boms", json={"item_id": self.cmp.id, "lines": [{"component_item_id": self.ac.id, "qty": 1}]})
        self.assertEqual(loop.status_code, 400)
        self.assertIn("circle", loop.json()["detail"])

    def test_bom_costing_and_can_build(self):
        bom = self.make_bom()
        self.assertFalse(bom["cost_complete"])  # nothing on the shelf and no PO yet
        self.assertEqual(bom["can_build"], 0)
        self.receive(self.spare_lines(["CMP-1", "CMP-2", "CMP-3"], fans=10, cost=4000, fan_cost=500))
        self.as_("accmgr")
        got = self.c.get(f"/api/accounts/boms/{bom['id']}").json()
        self.assertTrue(got["cost_complete"])
        self.assertEqual(got["material_cost"], "5000.00")  # 4000 + 2 x 500
        self.assertEqual(got["unit_cost"], "5750.00")  # plus labour 500 and overhead 250
        self.assertEqual(got["can_build"], 3)  # three compressors, five motors' worth of fans

    # assembly ---------------------------------------------------------------
    def test_assembly_builds_units_and_keeps_the_passport(self):
        self.make_bom()
        self.receive(self.spare_lines(["CMP-1", "CMP-2"], fans=5, cost=4000, fan_cost=500))
        self.as_("buyer")
        asm = self.c.post("/api/accounts/assemblies", json={"item_id": self.ac.id, "qty": 2}).json()
        self.assertEqual(asm["status"], "Planned")
        self.assertEqual({n["item_name"]: (n["needed"], n["short"]) for n in asm["needs"]}, {"Compressor 1.5T": (2, 0), "Fan motor": (4, 0)})
        units = [{"serial_no": "idu-1", "serial_no_2": "odu-1"}, {"serial_no": "IDU-2", "serial_no_2": "ODU-2"}]
        self.as_("buyer")
        self.assertEqual(self.c.post(f"/api/accounts/assemblies/{asm['id']}/complete", json={"units": units}).status_code, 403)
        self.as_("keeper")
        self.assertEqual(self.c.post(f"/api/accounts/assemblies/{asm['id']}/complete", json={"units": units[:1]}).status_code, 400)
        dup = self.c.post(f"/api/accounts/assemblies/{asm['id']}/complete", json={"units": [units[0], units[0]]})
        self.assertEqual(dup.status_code, 400)
        r = self.c.post(f"/api/accounts/assemblies/{asm['id']}/complete", json={"units": units})
        self.assertEqual(r.status_code, 200, r.text)
        out = r.json()
        self.assertEqual(out["status"], "Completed")

        db = self.Session()
        fin = db.scalars(select(StoreStock).where(StoreStock.item_id == self.ac.id).order_by(StoreStock.id)).all()
        self.assertEqual([(s.serial_no, s.serial_no_2, s.status, str(s.unit_cost)) for s in fin], [("IDU-1", "ODU-1", "Available", "5750.00"), ("IDU-2", "ODU-2", "Available", "5750.00")])
        comps = db.scalars(select(StoreStock).where(StoreStock.item_id == self.cmp.id)).all()
        self.assertEqual({s.status for s in comps}, {"Issued"})
        fans = db.scalars(select(StoreStock).where(StoreStock.item_id == self.fan.id)).all()
        self.assertEqual(sorted((s.status, s.qty) for s in fans), [("Available", 1), ("Issued", 4)])
        asm_ledger = db.scalars(select(StoreLedger).where(StoreLedger.doc_type == "ASM")).all()
        self.assertEqual(sum(x.qty_in for x in asm_ledger), 2)
        self.assertEqual(sum(x.qty_out for x in asm_ledger), 6)
        db.close()

        passport = self.c.get("/api/accounts/passport/idu-1").json()
        self.assertEqual(passport["asm_no"], asm["asm_no"])
        self.assertEqual([p["component_serial"] for p in passport["parts"] if p["component_serial"]], ["CMP-1"])
        self.assertEqual(self.c.post(f"/api/accounts/assemblies/{asm['id']}/complete", json={"units": units}).status_code, 409)
        self.assertEqual(self.c.get("/api/accounts/passport/NOPE-1").status_code, 404)

    def test_assembly_refuses_when_components_are_short(self):
        self.make_bom()
        self.receive(self.spare_lines(["CMP-1"], fans=2))
        self.as_("buyer")
        asm = self.c.post("/api/accounts/assemblies", json={"item_id": self.ac.id, "qty": 2}).json()
        self.assertEqual({n["item_name"]: n["short"] for n in asm["needs"]}, {"Compressor 1.5T": 1, "Fan motor": 2})
        self.as_("keeper")
        r = self.c.post(f"/api/accounts/assemblies/{asm['id']}/complete", json={"units": [{"serial_no": "IDU-1", "serial_no_2": "ODU-1"}, {"serial_no": "IDU-2", "serial_no_2": "ODU-2"}]})
        self.assertEqual(r.status_code, 409)
        self.assertIn("short", r.json()["detail"])
        db = self.Session()
        self.assertEqual({s.status for s in db.scalars(select(StoreStock).where(StoreStock.item_id == self.cmp.id))}, {"Available"})  # nothing was taken
        db.close()

    def test_assembly_needs_an_active_bom_and_can_be_cancelled(self):
        self.as_("buyer")
        r = self.c.post("/api/accounts/assemblies", json={"item_id": self.ac.id, "qty": 1})
        self.assertEqual(r.status_code, 409)
        self.make_bom()
        self.as_("buyer")
        asm = self.c.post("/api/accounts/assemblies", json={"item_id": self.ac.id, "qty": 1}).json()
        self.as_("keeper")
        c = self.c.post(f"/api/accounts/assemblies/{asm['id']}/cancel")
        self.assertEqual(c.status_code, 200)
        self.assertEqual(c.json()["status"], "Cancelled")

    # item master ------------------------------------------------------------
    def test_item_master_carries_source_and_gst(self):
        self.as_("boss")
        r = self.c.post("/api/items", json={"item_code": "CMP20", "item_name": "Compressor 2T", "source": "Both", "item_type": "Component", "gst_rate": 18, "serial_count": 1})
        self.assertEqual(r.status_code, 201, r.text)
        self.assertEqual((r.json()["source"], r.json()["item_type"], r.json()["gst_rate"]), ("Both", "Component", 18.0))
        plain = self.c.post("/api/items", json={"item_code": "OLD1", "item_name": "Old style item"}).json()
        self.assertEqual(plain["source"], "Buy")
        self.assertEqual(self.c.put(f"/api/items/{plain['id']}", json={"source": "Make"}).json()["source"], "Make")


if __name__ == "__main__":
    unittest.main()
