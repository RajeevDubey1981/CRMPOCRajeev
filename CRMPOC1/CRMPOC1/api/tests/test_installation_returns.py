import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import os
os.environ.setdefault("MYSQL_DATABASE_URL", "sqlite://")
import unittest
from datetime import date
from unittest.mock import patch
from fastapi import BackgroundTasks, HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base
from app.models.user import User
from app.models.order import Order, OrderItem
from app.models.installation import InstallationRequest, InstallationStatusLog
from app.routers.installation_returns import request_return, decide, queue, ReturnIn, DecisionIn, PENDING, RETURNED

class InstallationReturnsTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.eng = User(name="Engineer",email="engineer@test.invalid",password_hash="unused",role="engineer")
        self.admin = User(name="Manager",email="manager@test.invalid",password_hash="unused",role="service_manager")
        self.db.add_all([self.eng,self.admin]);self.db.flush()
        order = Order(order_no="TEST-RETURN", order_date=date.today(),customer_email="customer@test.invalid")
        self.db.add(order);self.db.flush()
        self.rows=[]
        for i in range(10):
            item=OrderItem(order_id=order.id,item_code="AC",serial_no=f"A{i}",serial_no_2=f"B{i}",installation_status="Submitted")
            self.db.add(item);self.db.flush()
            row=InstallationRequest(order_id=order.id,order_item_id=item.id,customer_name="Customer",contact_number="000",source="vendor",status="Assigned",assigned_engineer=self.eng.id,serial_no=item.serial_no,serial_no_2=item.serial_no_2)
            self.db.add(row);self.rows.append(row)
        self.db.commit()
        self.sync=patch("app.services.pending_action_sync.sync_installation_pending_actions");self.sync.start()
    def tearDown(self):
        self.sync.stop();self.db.close();self.engine.dispose()
    def submit(self, rows):
        return request_return(ReturnIn(installation_ids=[r.id for r in rows],reason="Not physically at this location"),self.db,self.eng)
    def test_partial_return_preserves_other_seven_and_pairs(self):
        self.submit(self.rows[:3])
        self.assertEqual([r.status for r in self.rows], [PENDING]*3+["Assigned"]*7)
        for row in self.rows[:3]:
            tasks=BackgroundTasks()
            decide(row.id,DecisionIn(decision="approve",remark="Confirmed unavailable"),tasks,self.db,self.admin)
            self.assertEqual(len(tasks.tasks),1)
            item=self.db.get(OrderItem,row.order_item_id)
            self.assertEqual(item.installation_status,"Not Requested")
            self.assertEqual((item.serial_no,item.serial_no_2),(row.serial_no,row.serial_no_2))
        self.assertEqual([r.status for r in self.rows[3:]],["Assigned"]*7)
        self.assertEqual(len(self.db.scalars(select(InstallationRequest)).all()),10)
    def test_rejection_restores_workflow_without_email_or_unblock(self):
        row=self.rows[0];self.submit([row]);tasks=BackgroundTasks()
        decide(row.id,DecisionIn(decision="reject",remark="Check the storeroom"),tasks,self.db,self.admin)
        self.assertEqual(row.status,"Assigned")
        self.assertEqual(self.db.get(OrderItem,row.order_item_id).installation_status,"Submitted")
        self.assertEqual(tasks.tasks,[])
    def test_duplicate_and_unauthorized_decision_are_rejected(self):
        row=self.rows[0];self.submit([row])
        with self.assertRaises(HTTPException):self.submit([row])
        with self.assertRaises(HTTPException):decide(row.id,DecisionIn(decision="approve",remark="bad actor"),BackgroundTasks(),self.db,self.eng)
    def test_single_serial_return_closes_request_and_releases_immediately(self):
        row=self.rows[0]
        row.serial_no_2=None
        self.db.get(OrderItem,row.order_item_id).serial_no_2=None
        self.db.commit()
        self.submit([row])
        tasks=BackgroundTasks()
        decide(row.id,DecisionIn(decision="approve",remark="Approved"),tasks,self.db,self.admin)
        self.assertEqual(row.status,RETURNED)
        self.assertEqual(self.db.get(OrderItem,row.order_item_id).installation_status,"Not Requested")
        self.assertEqual(row.serial_no,"A0")
        self.assertEqual(len(tasks.tasks),1)
        with self.assertRaises(HTTPException):
            decide(row.id,DecisionIn(decision="verify-location",remark="Removed step"),BackgroundTasks(),self.db,self.admin)

    def test_http_guard_and_own_engineer_scope(self):
        from fastapi.testclient import TestClient
        from app.main import app
        from app.database import get_db
        from app.deps import get_current_user
        def database():
            yield self.db
        app.dependency_overrides[get_db] = database
        app.dependency_overrides[get_current_user] = lambda: self.eng
        # The guard is checked through the real route, before completion can mutate the row.
        try:
            with patch("app.services.pending_action_sync.sync_installation_pending_actions"):
                client = TestClient(app)
                row=self.rows[0]
                response=client.post("/api/installation-returns",json={"installation_ids":[row.id],"reason":"Missing at location"})
                self.assertEqual(response.status_code,200,response.text)
                response=client.put(f"/api/installations/{row.id}/status",data={"new_status":"Completed"})
                self.assertEqual(response.status_code,409,response.text)
        finally:
            app.dependency_overrides.clear()

    def test_approved_return_cannot_be_reopened(self):
        row=self.rows[0];self.submit([row])
        decide(row.id,DecisionIn(decision="approve",remark="Approved"),BackgroundTasks(),self.db,self.admin)
        with self.assertRaises(HTTPException):self.submit([row])
        self.assertEqual(self.db.get(OrderItem,row.order_item_id).installation_status,"Not Requested")

    def test_different_engineer_cannot_return_assigned_rows(self):
        other=User(id=999,name="Other engineer",email="other@test.invalid",password_hash="unused",role="engineer")
        with self.assertRaises(HTTPException):
            request_return(ReturnIn(installation_ids=[self.rows[0].id],reason="Not available"),self.db,other)
        self.assertEqual(self.rows[0].status,"Assigned")

    def test_mismatched_order_pair_blocks_approval(self):
        row=self.rows[0];self.submit([row])
        self.db.get(OrderItem,row.order_item_id).serial_no_2="WRONG"
        self.db.commit()
        with self.assertRaises(HTTPException):
            decide(row.id,DecisionIn(decision="approve",remark="Approve"),BackgroundTasks(),self.db,self.admin)
        self.assertEqual(row.status,PENDING)

    def test_history_is_scoped_to_specific_installation(self):
        self.submit(self.rows[:2])
        result=queue(installation_id=self.rows[0].id,db=self.db,user=self.eng)
        self.assertEqual([r["id"] for r in result],[self.rows[0].id])
        unrelated=queue(installation_id=self.rows[2].id,db=self.db,user=self.eng)
        self.assertEqual(unrelated,[])

    def test_vendor_returns_one_pair_then_resubmits_without_affecting_other_rows(self):
        from app.models.vendor import Vendor
        from app.models.item_master import ItemMaster
        from app.routers.orders import _hydrate_items, _consignee_locked_item_ids, submit_serials_for_assignment, BulkSerialSubmitRequest
        from app.models.role import Role, Permission
        role=Role(name="vendor")
        self.db.add(role);self.db.flush()
        self.db.add(Permission(role_id=role.id,module="orders",can_view=True))
        vendor=Vendor(vendor_code="TEST-RETURN-VENDOR",name_of_firm="Vendor",email="vendor@test.invalid",is_active=True)
        user=User(name="Vendor",email="vendor@test.invalid",password_hash="unused",role="vendor")
        master=ItemMaster(item_code="AC",item_name="Split AC",serial_count=2)
        self.db.add_all([vendor,user,master]);self.db.flush()
        row=self.rows[0];order=self.db.get(Order,row.order_id)
        order.vendor_id=vendor.id;order.status="Delivered";order.oem_bill_no="TEST-BILL"
        for entry in self.rows:self.db.get(OrderItem,entry.order_item_id).item_id=master.id
        self.db.commit()
        item_id=row.order_item_id
        self.submit([row])
        self.assertIn(item_id,_consignee_locked_item_ids(self.db,order.id))
        decide(row.id,DecisionIn(decision="approve",remark="One pair absent"),BackgroundTasks(),self.db,self.admin)
        hydrated={r.id:r for r in _hydrate_items(self.db,order)}
        self.assertEqual(hydrated[item_id].returned_installation_id,row.id)
        self.assertIsNotNone(hydrated[item_id].return_reason)
        self.assertNotIn(item_id,_consignee_locked_item_ids(self.db,order.id))
        for other in self.rows[1:]:
            self.assertEqual(other.status,"Assigned")
            self.assertIsNone(hydrated[other.order_item_id].returned_installation_id)
            self.assertEqual(hydrated[other.order_item_id].installation_status,"Submitted")
        payload=BulkSerialSubmitRequest(order_id=order.id,order_item_ids=[item_id],selected_serials=[f"{item_id}-serial1",f"{item_id}-serial2"])
        result=submit_serials_for_assignment(order.id,payload,self.db,user)
        self.assertEqual(result["count"],1)
        self.assertEqual(result["submitted_order_item_ids"],[item_id])
        self.assertEqual(self.db.get(InstallationRequest,row.id).status,RETURNED)
        self.assertEqual(len(self.db.scalars(select(InstallationRequest)).all()),11)
        self.assertEqual(len(self.db.scalars(select(OrderItem)).all()),10)
        self.assertEqual((self.db.get(OrderItem,item_id).serial_no,self.db.get(OrderItem,item_id).serial_no_2),("A0","B0"))
        hydrated={r.id:r for r in _hydrate_items(self.db,order)}
        self.assertIsNone(hydrated[item_id].returned_installation_id)
        again=submit_serials_for_assignment(order.id,payload,self.db,user)
        self.assertEqual(again["count"],0)
