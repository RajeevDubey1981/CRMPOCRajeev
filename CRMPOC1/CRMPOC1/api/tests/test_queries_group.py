from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

import test_queries as _q

from app.models.pending_action import UserPendingAction
from app.models.user_query import UserQuery
from app.services import queries_service as qs
from sqlalchemy import select


class GroupQueryTests(unittest.TestCase):
    # the same database, users and helpers as the Queries tests
    setUp = _q.QueriesTests.setUp
    tearDown = _q.QueriesTests.tearDown
    _user = _q.QueriesTests._user
    h = _q.QueriesTests.h
    raise_query = _q.QueriesTests.raise_query

    def post(self, url, body, who):
        return self.client.post(url, json=body, headers=self.h(who))

    def get(self, url, who):
        return self.client.get(url, headers=self.h(who))

    def put(self, url, body, who):
        return self.client.put(url, json=body, headers=self.h(who))

    def delete(self, url, who):
        return self.client.delete(url, headers=self.h(who))

    def thread(self, qid, who):
        r = self.get(f"/api/queries/{qid}", who)
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def cards(self, user, action_type=None, active=True):
        with self.Session() as s:
            rows = list(s.scalars(select(UserPendingAction).where(UserPendingAction.recipient_user_id == user.id, UserPendingAction.module == "queries")))
            return [r for r in rows if (not action_type or r.action_type == action_type) and (r.is_active or not active)]

    # ---------------- forward ----------------
    def test_a_query_is_forwarded_to_a_role_and_the_history_keeps_every_step(self):
        q = self.raise_query(self.eng)
        self.assertEqual(self.post(f"/api/queries/{q['id']}/forward", {"to_user_id": self.tech.id}, self.eng).status_code, 403, "the one who asked cannot forward")
        self.assertEqual(self.get(f"/api/queries/{q['id']}", self.tech).status_code, 404, "not in it yet")
        r = self.post(f"/api/queries/{q['id']}/forward", {"to_user_id": self.tech.id, "note": "please check the stock"}, self.sub)
        self.assertEqual(r.status_code, 200, r.text)
        d = r.json()
        self.assertEqual((d["holder_id"], d["status"]), (self.tech.id, "Open"))
        self.assertIn("please check the stock", [e["text"] for e in d["events"] if e["kind"] == "forward"][0])
        mine = self.thread(q["id"], self.tech)
        self.assertEqual(len(mine["messages"]), 1, "the forwarded person reads what was said")
        self.assertTrue(mine["can_forward"] and mine["can_see_history"])
        self.assertEqual(len(self.cards(self.tech, "query_forward")), 1, "a card on their dashboard")
        self.assertEqual(self.get("/api/queries/summary", self.tech).json()["open"], 1)
        self.assertEqual(len(self.get("/api/queries", self.eng).json()), 1, "the one who asked still sees it")
        # their answer closes the card and marks it answered
        a = self.post(f"/api/queries/{q['id']}/messages", {"body": "Stock is on its way"}, self.tech).json()
        self.assertEqual(a["status"], "Answered")
        self.assertEqual(self.cards(self.tech, "query_forward"), [])
        # the person who asked cannot see the history, the holder and the Admin team can
        self.assertEqual(self.thread(q["id"], self.eng)["events"], [])
        self.assertGreaterEqual(len(self.thread(q["id"], self.admin)["events"]), 3)

    def test_the_holder_can_forward_it_on_and_a_stranger_cannot(self):
        q = self.raise_query(self.eng)
        self.post(f"/api/queries/{q['id']}/forward", {"to_user_id": self.tech.id}, self.admin)
        self.assertEqual(self.post(f"/api/queries/{q['id']}/forward", {"to_user_id": self.vendor.id}, self.eng2).status_code, 404)
        self.assertEqual(self.post(f"/api/queries/{q['id']}/forward", {"to_user_id": self.tech.id}, self.tech).status_code, 400, "it is with them already")
        r = self.post(f"/api/queries/{q['id']}/forward", {"to_user_id": self.vendor.id}, self.tech)
        self.assertEqual((r.status_code, r.json()["holder_id"]), (200, self.vendor.id))
        people = self.get("/api/queries/people", self.admin).json()
        self.assertIn(self.tech.id, [p["id"] for p in people])
        self.assertEqual(self.get("/api/queries/people", self.eng2).status_code, 403)

    # ---------------- CC and group ----------------
    def test_cc_and_members_join_the_conversation_and_are_told(self):
        q = self.raise_query(self.eng)
        self.assertEqual(self.post(f"/api/queries/{q['id']}/members", {"user_id": self.vendor.id, "kind": "cc"}, self.eng).status_code, 403)
        r = self.post(f"/api/queries/{q['id']}/members", {"user_id": self.vendor.id, "kind": "cc"}, self.sub)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(self.post(f"/api/queries/{q['id']}/members", {"user_id": self.vendor.id}, self.sub).status_code, 409)
        self.assertEqual(self.post(f"/api/queries/{q['id']}/members", {"user_id": self.admin.id}, self.sub).status_code, 400, "the Admin team sees everything anyway")
        self.post(f"/api/queries/{q['id']}/members", {"user_id": self.tech.id}, self.sub)
        self.assertEqual(len(self.cards(self.vendor, "query_cc")), 1)
        d = self.thread(q["id"], self.vendor)
        self.assertEqual(len(d["messages"]), 1)
        self.assertEqual(self.cards(self.vendor, "query_cc"), [], "seen, so the card is gone")
        self.assertEqual({m["name"]: m["kind"] for m in d["members"]}, {"eng": "owner", "v": "cc", "tech": "member"})
        # a CC reply is a comment: it does not make the query wait for an answer again
        self.post(f"/api/queries/{q['id']}/messages", {"body": "Answer"}, self.sub)
        after = self.post(f"/api/queries/{q['id']}/messages", {"body": "Just so you know"}, self.vendor).json()
        self.assertEqual(after["status"], "Answered")
        self.assertEqual(len(self.thread(q["id"], self.tech)["messages"]), 3, "everybody in it reads all three")

    # ---------------- taking someone out for a private talk ----------------
    def test_someone_taken_out_cannot_read_the_private_talk_and_comes_back_without_it(self):
        q = self.raise_query(self.eng)
        qid = q["id"]
        self.post(f"/api/queries/{qid}/members", {"user_id": self.vendor.id}, self.sub)
        self.post(f"/api/queries/{qid}/members", {"user_id": self.tech.id}, self.sub)
        self.post(f"/api/queries/{qid}/messages", {"body": "Shared one"}, self.sub)
        # the vendor is taken out
        out = self.delete(f"/api/queries/{qid}/members/{self.vendor.id}", self.sub)
        self.assertEqual(out.status_code, 200, out.text)
        self.assertTrue(out.json()["private_now"])
        self.assertEqual(self.get(f"/api/queries/{qid}", self.vendor).status_code, 404, "it is gone from their list")
        self.assertEqual(self.get("/api/queries", self.vendor).json(), [])
        pvt = self.post(f"/api/queries/{qid}/messages", {"body": "Private: decide the price among us"}, self.tech)
        self.assertEqual(pvt.status_code, 200, pvt.text)
        self.assertTrue(pvt.json()["messages"][-1]["is_private"])
        # the others read it; the Admin team reads it and sees who it was kept from
        self.assertEqual(len(self.thread(qid, self.eng)["messages"]), 3)
        staff_view = self.thread(qid, self.admin)["messages"][-1]
        self.assertEqual((staff_view["is_private"], staff_view["hidden_from"]), (True, ["v"]))
        # the vendor is added back: the shared messages are there, the private one is not
        self.post(f"/api/queries/{qid}/members", {"user_id": self.vendor.id}, self.sub)
        self.post(f"/api/queries/{qid}/messages", {"body": "Shared again"}, self.sub)
        back = self.thread(qid, self.vendor)
        self.assertEqual([m["body"] for m in back["messages"]], ["My payment is pending since last week", "Shared one", "Shared again"])
        self.assertFalse(back["private_now"], "nobody is out any more")
        self.assertEqual(self.thread(qid, self.eng)["members"][0]["kind"], "owner")
        kinds = [e["kind"] for e in self.thread(qid, self.admin)["events"]]
        self.assertIn("removed", kinds)
        self.assertEqual(kinds.count("member"), 3, "added twice, and added back")

    def test_the_holder_and_the_owner_rules_for_taking_out(self):
        q = self.raise_query(self.eng)
        qid = q["id"]
        self.post(f"/api/queries/{qid}/forward", {"to_user_id": self.tech.id}, self.sub)
        self.assertEqual(self.delete(f"/api/queries/{qid}/members/{self.tech.id}", self.sub).status_code, 400, "forward it before taking the holder out")
        self.assertEqual(self.delete(f"/api/queries/{qid}/members/{self.tech.id}", self.tech).status_code, 400, "not oneself")
        self.assertEqual(self.delete(f"/api/queries/{qid}/members/{self.eng.id}", self.eng).status_code, 403)
        self.assertEqual(self.delete(f"/api/queries/{qid}/members/{self.eng.id}", self.tech).status_code, 200, "the holder may take the one who asked out")
        self.assertEqual(self.get("/api/queries", self.eng).json(), [])
        self.assertEqual(self.delete(f"/api/queries/{qid}/members/{self.eng.id}", self.tech).status_code, 404, "already out")

    # ---------------- priority ----------------
    def test_only_admin_and_sub_admin_set_the_priority(self):
        q = self.raise_query(self.eng)
        self.assertEqual(self.put(f"/api/queries/{q['id']}/priority", {"priority": "urgent"}, self.eng).status_code, 403)
        self.assertEqual(self.put(f"/api/queries/{q['id']}/priority", {"priority": "loud"}, self.sub).status_code, 422)
        self.assertEqual(self.put(f"/api/queries/{q['id']}/priority", {"priority": "urgent"}, self.sub).json()["priority"], "urgent")
        low = self.raise_query(self.eng2, subject="Other")
        rows = self.get("/api/queries", self.admin).json()
        self.assertEqual(rows[0]["id"], q["id"], "urgent comes first")
        self.assertEqual(self.get("/api/queries", self.eng).json()[0]["priority"], "urgent", "the asker sees the tag")
        self.assertIn("Priority set to Urgent", [e["text"] for e in self.thread(q["id"], self.admin)["events"] if e["kind"] == "priority"][0])
        self.assertEqual(low["status"], "Open")

    # ---------------- the 24 hour alarm ----------------
    def age(self, qid, hours):
        with self.Session() as s:
            row = s.get(UserQuery, qid)
            row.awaiting_since = datetime.now(timezone.utc) - timedelta(hours=hours)
            row.last_alarm_at = None
            s.commit()

    def test_after_24_hours_without_an_answer_the_alarm_rings_for_the_person_who_has_to_answer(self):
        q = self.raise_query(self.eng)
        qid = q["id"]
        self.assertEqual(self.get("/api/queries/summary", self.sub).json()["alarms"], 0)
        self.assertLess(self.get("/api/queries", self.sub).json()[0]["hours_left"], 24.01)
        self.age(qid, 25)
        with self.Session() as s:
            self.assertEqual(qs.sweep_overdue(s), 1)
            self.assertEqual(qs.sweep_overdue(s), 0, "it does not ring twice for the same wait")
        row = self.get("/api/queries", self.sub).json()[0]
        self.assertEqual((row["overdue"], row["alarm_for_me"]), (True, True))
        self.assertFalse(self.get("/api/queries", self.eng).json()[0]["alarm_for_me"], "the one who asked is not rung")
        self.assertEqual(self.get("/api/queries/summary", self.sub).json()["alarms"], 1)
        card = self.cards(self.admin, "query_overdue")[0]
        self.assertTrue(card.message.startswith("HIGH PRIORITY - "))
        self.assertIsNotNone(card.due_at, "an alarm stays on the dashboard until it is answered")
        # only the Admin team rings it again
        self.assertEqual(self.post(f"/api/queries/{qid}/ring", {}, self.eng).status_code, 403)
        again = self.post(f"/api/queries/{qid}/ring", {}, self.sub)
        self.assertEqual(again.json()["alarm_count"], 2)
        # an answer silences it
        self.post(f"/api/queries/{qid}/messages", {"body": "Sorry for the wait"}, self.sub)
        self.assertEqual(self.cards(self.admin, "query_overdue"), [])
        self.assertEqual(self.get("/api/queries/summary", self.sub).json()["alarms"], 0)

    def test_a_forwarded_query_starts_a_new_24_hours_for_the_new_holder(self):
        q = self.raise_query(self.eng)
        qid = q["id"]
        self.age(qid, 30)
        self.post(f"/api/queries/{qid}/forward", {"to_user_id": self.tech.id}, self.sub)
        row = self.get("/api/queries", self.tech).json()[0]
        self.assertFalse(row["overdue"], "the clock started again when it was forwarded")
        self.age(qid, 26)
        with self.Session() as s:
            qs.sweep_overdue(s)
        self.assertTrue(self.get("/api/queries", self.tech).json()[0]["alarm_for_me"])
        self.assertFalse(self.get("/api/queries", self.sub).json()[0]["alarm_for_me"], "now it is the holder who is rung")
        self.assertEqual(len(self.cards(self.tech, "query_overdue")), 1)
        self.assertEqual(self.cards(self.sub, "query_overdue"), [])
        # solving it ends the clock
        self.post(f"/api/queries/{qid}/close", {}, self.tech)
        self.assertEqual(self.cards(self.tech, "query_overdue"), [])
        self.assertIsNone(self.get("/api/queries", self.tech).json()[0]["hours_left"])


if __name__ == "__main__":
    unittest.main()
