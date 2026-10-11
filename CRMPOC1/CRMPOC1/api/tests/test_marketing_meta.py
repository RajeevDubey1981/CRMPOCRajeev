"""Marketing: the Meta connection (log in, ad accounts, campaigns), read only. Meta itself is never called: its answers are faked."""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("MYSQL_DATABASE_URL", "sqlite://")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.config import settings
from app.marketing import meta, secrets_box
from app.marketing.models import MkChannel
from app.security import create_access_token
import test_marketing as _base


class MetaTests(unittest.TestCase):
    # the same two databases, users and helpers as the Marketing tests
    setUp = _base.MarketingTests.setUp
    tearDown = _base.MarketingTests.tearDown
    _user = _base.MarketingTests._user
    h = _base.MarketingTests.h
    get = _base.MarketingTests.get
    put = _base.MarketingTests.put

    def configure(self):
        self._old = (settings.meta_app_id, settings.meta_app_secret)
        settings.meta_app_id, settings.meta_app_secret = "123456", "shhh-secret"
        self.addCleanup(lambda: setattr(settings, "meta_app_id", self._old[0]) or setattr(settings, "meta_app_secret", self._old[1]))

    def state(self, user, purpose="meta_connect"):
        return create_access_token(subject=str(user.id), extra_claims={"purpose": purpose})

    def callback(self, user, **kw):
        state = kw.pop("state", self.state(user))
        return self.client.get("/api/marketing/meta/callback", params={"code": "abc", "state": state, **kw}, follow_redirects=False)

    def connect_as_admin(self):
        self.configure()
        with patch.object(meta, "exchange_code", return_value={"access_token": "LONG-TOKEN-1", "expires_in": 5_000_000}), \
                patch.object(meta, "me", return_value={"id": "77", "name": "Rajeev Dubey"}), \
                patch.object(meta, "ad_accounts", return_value=[{"account_id": "111", "name": "INDcool Ads", "currency": "INR"}, {"account_id": "222", "name": "Old Account", "currency": "INR"}]):
            r = self.callback(self.admin)
        self.assertEqual(r.status_code, 307)
        return r

    def test_not_set_up_until_the_app_id_and_secret_are_on_the_server(self):
        st = self.get("/api/marketing/meta/status", self.admin).json()
        self.assertEqual((st["configured"], st["connected"]), (False, False))
        r = self.get("/api/marketing/meta/connect", self.admin)
        self.assertEqual(r.status_code, 409)
        self.assertIn("not set up", r.json()["detail"])

    def test_the_login_address_asks_only_for_reading_ads_and_only_admin_can_start_it(self):
        self.configure()
        url = self.get("/api/marketing/meta/connect", self.admin).json()["url"]
        self.assertTrue(url.startswith("https://www.facebook.com/"))
        self.assertIn("client_id=123456", url)
        self.assertIn("scope=ads_read%2Cbusiness_management", url)
        self.assertNotIn("ads_management", url)
        self.assertNotIn("shhh-secret", url)
        self.assertEqual(self.get("/api/marketing/meta/connect", self.mktm).status_code, 403, "connecting is locked to Admin and Sub Admin")

    def test_the_login_is_saved_encrypted_and_never_shown(self):
        r = self.connect_as_admin()
        self.assertIn("meta=connected", r.headers["location"])
        st = self.get("/api/marketing/meta/status", self.admin).json()
        self.assertEqual((st["connected"], st["name"], st["scopes"]), (True, "Rajeev Dubey", ["ads_read", "business_management"]))
        self.assertGreater(st["days_left"], 50)
        self.assertNotIn("LONG-TOKEN-1", str(st))
        with self.Mk() as mdb:
            ch = mdb.scalar(select(MkChannel))
            self.assertNotIn("LONG-TOKEN-1", ch.token_enc)
            self.assertEqual(secrets_box.unseal(ch.token_enc), {"access_token": "LONG-TOKEN-1"})

    def test_a_wrong_or_stolen_state_is_refused(self):
        self.configure()
        for kw in ({"state": "garbage"}, {"state": self.state(self.admin, "something_else")}):
            r = self.callback(self.admin, **kw)
            self.assertIn("meta=failed", r.headers["location"])
        self.assertIn("meta=cancelled", self.client.get("/api/marketing/meta/callback", params={"error": "access_denied"}, follow_redirects=False).headers["location"])
        with self.Mk() as mdb:
            self.assertIsNone(mdb.scalar(select(MkChannel)))

    def test_ad_accounts_and_campaigns_need_the_cost_tick_and_a_switched_on_account(self):
        self.connect_as_admin()
        with patch.object(meta, "ad_accounts", return_value=[{"account_id": "111", "name": "INDcool Ads", "currency": "INR", "amount_spent": "1200"}, {"account_id": "222", "name": "Old Account", "currency": "INR"}]):
            self.assertEqual(self.get("/api/marketing/meta/ad-accounts", self.mkt).status_code, 403, "a Marketing user does not see money")
            self.assertEqual(self.get("/api/marketing/meta/ad-accounts", self.mktm).status_code, 200)
            rows = self.get("/api/marketing/meta/ad-accounts", self.mktm).json()
        self.assertEqual({r["id"]: r["in_use"] for r in rows}, {"111": False, "222": False})
        fake = [{"id": "c1", "name": "Dubai push", "status": "ACTIVE", "last_30_days": {"spend": "500", "leads": 9}}]
        with patch.object(meta, "campaigns", return_value=fake):
            self.assertEqual(self.get("/api/marketing/meta/campaigns?account=111", self.mktm).status_code, 403, "not switched on yet")
            self.assertEqual(self.put("/api/marketing/meta/ad-accounts/111?in_use=true", {}, self.mktm).status_code, 403, "only Admin switches an account on")
            self.assertEqual(self.put("/api/marketing/meta/ad-accounts/111?in_use=true", {}, self.admin).status_code, 200)
            r = self.get("/api/marketing/meta/campaigns?account=act_111", self.mktm)
            self.assertEqual((r.status_code, r.json()[0]["name"]), (200, "Dubai push"))
            self.assertEqual(self.get("/api/marketing/meta/campaigns?account=222", self.mktm).status_code, 403)

    def test_disconnect_wipes_the_token(self):
        self.connect_as_admin()
        self.assertEqual(self.client.post("/api/marketing/meta/disconnect", headers=self.h(self.mktm)).status_code, 403)
        self.assertEqual(self.client.post("/api/marketing/meta/disconnect", headers=self.h(self.admin)).status_code, 200)
        self.assertFalse(self.get("/api/marketing/meta/status", self.admin).json()["connected"])
        with self.Mk() as mdb:
            ch = mdb.scalar(select(MkChannel))
            self.assertEqual((ch.status, ch.token_enc), ("removed", None))

    def test_meta_answers_are_checked_and_the_token_goes_in_a_header_with_a_proof(self):
        self.configure()

        class Fake:
            status_code = 200

            def json(self):
                return {"data": []}

        with patch.object(meta.requests, "get", return_value=Fake()) as g:
            meta.get("me/adaccounts", "TOKEN-X", {"fields": "name"})
        args, kwargs = g.call_args
        self.assertNotIn("TOKEN-X", args[0])
        self.assertNotIn("TOKEN-X", str(kwargs["params"]))
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer TOKEN-X")
        self.assertEqual(len(kwargs["params"]["appsecret_proof"]), 64)

        class Bad:
            status_code = 400

            def json(self):
                return {"error": {"message": "Invalid OAuth access token."}}

        with patch.object(meta.requests, "get", return_value=Bad()):
            with self.assertRaises(meta.MetaError) as ctx:
                meta.get("me", "TOKEN-X")
        self.assertNotIn("TOKEN-X", str(ctx.exception))

    def test_ad_accounts_are_also_found_through_the_businesses_of_the_person(self):
        self.configure()

        def fake_get(path, token, params=None):
            if path == "me/adaccounts":
                return {"data": [{"account_id": "111", "name": "Personal"}]}
            if path == "me/businesses":
                return {"data": [{"id": "900", "name": "Indcool"}]}
            if path == "900/owned_ad_accounts":
                return {"data": [{"account_id": "222", "name": "Business account"}, {"account_id": "111", "name": "Personal"}]}
            if path == "900/client_ad_accounts":
                raise meta.MetaError("not allowed")
            return {"data": []}

        with patch.object(meta, "get", side_effect=fake_get):
            got = meta.ad_accounts("T")
        self.assertEqual(sorted(a["account_id"] for a in got), ["111", "222"], "found once each, from both ways of asking")

    def test_the_diagnosis_shows_permissions_chosen_accounts_and_businesses_without_a_token(self):
        self.connect_as_admin()

        def fake_get(path, token, params=None):
            if path == "me/permissions":
                return {"data": [{"permission": "ads_read", "status": "granted"}, {"permission": "business_management", "status": "declined"}]}
            if path == "me/adaccounts":
                return {"data": [{"account_id": "111"}]}
            if path == "me/businesses":
                return {"data": [{"id": "900", "name": "Indcool"}]}
            if path == "900/owned_ad_accounts":
                return {"data": []}
            raise meta.MetaError("not allowed")

        class Fake:
            status_code = 200

            def json(self):
                return {"data": {"app_id": "123456", "is_valid": True, "granular_scopes": [{"scope": "ads_read", "target_ids": ["111"]}]}}

        with patch.object(meta, "get", side_effect=fake_get), patch.object(meta.requests, "get", return_value=Fake()):
            self.assertEqual(self.get("/api/marketing/meta/diagnose", self.mktm).status_code, 403, "only Admin")
            r = self.get("/api/marketing/meta/diagnose", self.admin)
        self.assertEqual(r.status_code, 200, r.text)
        d = r.json()
        self.assertEqual(d["direct_accounts"], 1)
        self.assertEqual(d["granular"], [{"scope": "ads_read", "target_ids": ["111"]}])
        self.assertEqual(d["businesses"][0]["name"], "Indcool")
        self.assertIn({"name": "business_management", "status": "declined"}, d["permissions"])
        self.assertNotIn("LONG-TOKEN-1", r.text)

    def test_a_system_user_token_connects_without_expiry_and_is_never_shown(self):
        self.configure()
        accounts = [{"account_id": "2629", "name": "Indcool Ads", "currency": "INR"}]
        tok = "SYSTEM-TOKEN-ABCDEFGHIJKLMNOP"
        with patch.object(meta, "me", return_value={"id": "9", "name": "INDcool CRM"}), patch.object(meta, "ad_accounts", return_value=accounts):
            self.assertEqual(self.client.post("/api/marketing/meta/system-token", json={"token": tok}, headers=self.h(self.mktm)).status_code, 403, "only Admin")
            self.assertEqual(self.client.post("/api/marketing/meta/system-token", json={"token": "short"}, headers=self.h(self.admin)).status_code, 422)
            r = self.client.post("/api/marketing/meta/system-token", json={"token": tok}, headers=self.h(self.admin))
        self.assertEqual((r.status_code, r.json()["ad_accounts"]), (200, 1), r.text)
        self.assertNotIn(tok, r.text)
        st = self.get("/api/marketing/meta/status", self.admin)
        self.assertTrue(st.json()["connected"])
        self.assertIsNone(st.json()["days_left"])
        self.assertNotIn(tok, st.text)
        with self.Mk() as mdb:
            ch = mdb.scalar(select(MkChannel))
            self.assertNotIn(tok, str(ch.token_enc))
        with patch.object(meta, "me", side_effect=meta.MetaError("bad")), patch.object(meta, "ad_accounts", return_value=[]):
            self.assertEqual(self.client.post("/api/marketing/meta/system-token", json={"token": tok}, headers=self.h(self.admin)).status_code, 400)


if __name__ == "__main__":
    unittest.main()
