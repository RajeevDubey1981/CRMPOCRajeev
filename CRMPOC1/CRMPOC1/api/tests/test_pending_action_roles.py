from __future__ import annotations

import unittest

import test_queries as _q

from app.services import pending_action_service as pas


class StaleCardTests(unittest.TestCase):
    # the same database and users as the Queries tests
    setUp = _q.QueriesTests.setUp
    tearDown = _q.QueriesTests.tearDown
    _user = _q.QueriesTests._user
    h = _q.QueriesTests.h

    def card(self, user, module, action_type, entity_id):
        with self.Session() as s:
            pas.upsert_pending_action(
                s, recipient_user_id=user.id, module=module, entity_id=entity_id, action_type=action_type, title=f"{module} {entity_id}", message="m",
                action_label="Open", href=f"/{module}/{entity_id}", entity_status="New",
            )
            s.commit()

    def test_a_card_for_work_the_role_is_not_asked_to_do_is_closed_when_the_list_opens(self):
        sales = self.sales = None
        with self.Session() as s:
            from app.models import User
            from app.security import hash_password

            u = User(name="sales1", email="sales1@t.com", password_hash=hash_password("pw123456"), role="sales", is_active=True)
            s.add(u)
            s.commit()
            s.refresh(u)
            sales = u
        # cards made when this person was on the service desk, kept after the role changed to Sales
        self.card(sales, "services", "assign_service", 1)
        self.card(sales, "installations", "approve_completion", 2)
        self.card(sales, "installations", "approve_payment", 3)
        self.card(sales, "sales", "sales_new_lead", 4)  # their own work stays
        r = self.client.get("/api/pending-actions", headers=self.h(sales))
        self.assertEqual(r.status_code, 200, r.text)
        mods = sorted((i["module"], i["action_type"]) for i in r.json()["items"])
        self.assertEqual(mods, [("sales", "sales_new_lead")])
        self.assertEqual(r.json()["total"], 1, "the number on the bell drops too")

    def test_the_people_who_do_the_work_keep_their_cards(self):
        self.card(self.tech, "services", "assign_service", 11)          # service manager
        self.card(self.sub, "installations", "approve_completion", 12)   # sub admin
        self.card(self.eng, "services", "complete_service", 13)          # engineer
        self.card(self.vendor, "orders", "fulfill_order", 14)            # vendor
        for who, count in ((self.tech, 1), (self.sub, 1), (self.eng, 1), (self.vendor, 1)):
            r = self.client.get("/api/pending-actions", headers=self.h(who))
            self.assertEqual(len(r.json()["items"]), count, who.role)


if __name__ == "__main__":
    unittest.main()
