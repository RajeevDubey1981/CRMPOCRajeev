from __future__ import annotations

import tempfile
import unittest
from datetime import date, timedelta
from unittest.mock import patch

import test_queries as _q

from app.config import settings
from app.models import PartnerRegistration
from app.models.partner_agreement import PartnerAgreement
from sqlalchemy import select

PDF = b"%PDF-1.4\n1 0 obj\n<< >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF\n"


class HardCopyTests(unittest.TestCase):
    # the same database and users as the Queries tests
    setUp = _q.QueriesTests.setUp
    tearDown = _q.QueriesTests.tearDown
    _user = _q.QueriesTests._user
    h = _q.QueriesTests.h

    def make(self, with_agreement=True, signed=True, status="Onboarding Approved"):
        with self.Session() as s:
            r = PartnerRegistration(registration_no="PR-HC-1", access_token="tok-hc-1", partner_type="Distributor", business_type="Partnership", name="Shree Cool", mobile="9928077777",
                                    email="shree@t.com", form_status="Submitted", onboarding_status=status, state="Rajasthan", city="Jaipur")
            s.add(r)
            s.flush()
            if with_agreement:
                from datetime import datetime, timezone

                s.add(PartnerAgreement(registration_id=r.id, agreement_no="AGR-HC-1", access_token="agr-tok-1", email="shree@t.com", signed_at=datetime.now(timezone.utc) if signed else None))
            s.commit()
            return r.id

    def upload(self, rid, who, name="signed.pdf", data=PDF, ctype="application/pdf", **form):
        return self.client.post(f"/api/partner-registrations/{rid}/agreement/hard-copy", files={"file": (name, data, ctype)}, data=form, headers=self.h(who))

    def test_admin_and_sub_admin_upload_the_hard_copy_and_it_is_shared_with_the_partner_documents(self):
        with patch.object(settings, "upload_dir", tempfile.mkdtemp(prefix="indcool_hc_") + "/uploads"):
            rid = self.make()
            self.assertEqual(self.upload(rid, self.eng).status_code, 403, "only the Admin team")
            self.assertEqual(self.upload(rid, self.tech).status_code, 403)
            r = self.upload(rid, self.sub, received_on=date.today().isoformat(), note="Came by courier, 3 pages")
            self.assertEqual(r.status_code, 200, r.text)
            d = r.json()
            self.assertTrue(d["hard_copy_received"] and d["hard_copy_shared"])
            self.assertEqual((d["hard_copy_name"], d["hard_copy_note"], d["hard_copy_by_name"]), ("signed.pdf", "Came by courier, 3 pages", "sub"))
            self.assertTrue(d["hard_copy_url"].startswith("/uploads/partners/"))
            self.assertIn("shown in the partner's documents", d["hard_copy_events"][0]["text"])
            # the registration (the partner's documents) now carries it
            full = self.client.get(f"/api/partner-registrations/{rid}", headers=self.h(self.admin)).json()
            self.assertEqual(full["agreement_hard_copy_path"], d["hard_copy_url"])
            # the public form shows it to the partner too, read only
            public = self.client.get("/api/partner-registrations/public/tok-hc-1")
            if public.status_code == 200:
                self.assertEqual(public.json()["data"]["agreement_hard_copy_path"], d["hard_copy_url"])
            # the list says which partners have signed and have their paper
            row = self.client.get("/api/partner-registrations", headers=self.h(self.admin)).json()["items"][0]
            self.assertEqual((row["agreement_issued"], row["agreement_signed"], row["hard_copy_received"]), (True, True, True))

    def test_keep_it_private_replace_and_remove_are_all_kept_in_the_history(self):
        with patch.object(settings, "upload_dir", tempfile.mkdtemp(prefix="indcool_hc_") + "/uploads"):
            rid = self.make()
            r = self.upload(rid, self.admin, share="false")
            self.assertFalse(r.json()["hard_copy_shared"])
            full = self.client.get(f"/api/partner-registrations/{rid}", headers=self.h(self.admin)).json()
            self.assertIsNone(full["agreement_hard_copy_path"], "not in the partner's documents")
            # show it
            shown = self.client.patch(f"/api/partner-registrations/{rid}/agreement/hard-copy?share=true", headers=self.h(self.admin)).json()
            self.assertTrue(shown["hard_copy_shared"])
            self.assertIsNotNone(self.client.get(f"/api/partner-registrations/{rid}", headers=self.h(self.admin)).json()["agreement_hard_copy_path"])
            # replace
            again = self.upload(rid, self.sub, name="signed2.pdf").json()
            self.assertEqual(again["hard_copy_name"], "signed2.pdf")
            # remove
            gone = self.client.delete(f"/api/partner-registrations/{rid}/agreement/hard-copy", headers=self.h(self.sub)).json()
            self.assertFalse(gone["hard_copy_received"])
            self.assertIsNone(self.client.get(f"/api/partner-registrations/{rid}", headers=self.h(self.admin)).json()["agreement_hard_copy_path"])
            texts = [e["text"] for e in gone["hard_copy_events"]]
            self.assertEqual(len(texts), 4, "uploaded, shown, replaced, removed")
            self.assertTrue(any("replaced" in t for t in texts) and any("removed" in t for t in texts) and any("hidden" in t or "shown" in t for t in texts))
            self.assertEqual(self.client.delete(f"/api/partner-registrations/{rid}/agreement/hard-copy", headers=self.h(self.eng)).status_code, 403)

    def test_the_rules_for_the_file_the_date_and_a_missing_agreement(self):
        with patch.object(settings, "upload_dir", tempfile.mkdtemp(prefix="indcool_hc_") + "/uploads"):
            rid = self.make(with_agreement=False, status="Registration Submitted")
            self.assertIsNone(self.client.get(f"/api/partner-registrations/{rid}/agreement", headers=self.h(self.admin)).json(), "no agreement before the approval")
            first = self.upload(rid, self.admin)
            self.assertEqual(first.status_code, 200, "the paper can arrive before the approval")
            self.assertFalse(first.json()["signing_started"], "the signing link has not gone out yet")
            row = self.client.get("/api/partner-registrations", headers=self.h(self.admin)).json()["items"][0]
            self.assertEqual((row["agreement_issued"], row["hard_copy_received"]), (False, True))
            self.assertEqual(self.client.delete(f"/api/partner-registrations/{rid}/agreement/hard-copy", headers=self.h(self.admin)).status_code, 200)
            self.assertEqual(self.client.patch(f"/api/partner-registrations/{rid + 99}/agreement/hard-copy?share=true", headers=self.h(self.admin)).status_code, 404)
            self.assertEqual(self.upload(rid, self.admin, name="x.exe", data=b"MZ", ctype="application/octet-stream").status_code, 400)
            future = (date.today() + timedelta(days=3)).isoformat()
            self.assertEqual(self.upload(rid, self.admin, received_on=future).status_code, 400)
            ok = self.upload(rid, self.admin, name="scan.jpg", data=b"\xff\xd8\xff\xe0" + b"0" * 200 + b"\xff\xd9", ctype="image/jpeg")
            self.assertEqual(ok.status_code, 200, ok.text)
            self.assertEqual(self.client.patch(f"/api/partner-registrations/{rid}/agreement/hard-copy?share=false", headers=self.h(self.sub)).status_code, 200)
            with self.Session() as s:
                ag = s.scalar(select(PartnerAgreement).where(PartnerAgreement.registration_id == rid))
                self.assertFalse(ag.signed_at, "this agreement was never signed digitally: the paper copy can still be kept")


if __name__ == "__main__":
    unittest.main()
