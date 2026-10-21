"""The Parts database itself: it is a genuinely separate database (no FK into the CRM), the schema round-trips,
and the approval-chain rules behave as documented."""
from __future__ import annotations

from decimal import Decimal

from app.parts.models import ItemRequest, ItemRequestEvent, ItemRequestPhoto, PartWarrantySwap, SparePart, SparePartFitment
from app.parts.rules import needs_second_approval, next_stage_on_approve, required_photos, stage_label
from tests.parts_base import PartsTestBase


class PartsDbTests(PartsTestBase):
    def test_catalogue_round_trips(self):
        part = SparePart(part_code="SP-CMP-1501", part_name="Inverter compressor 1.5 T", part_ean="8909000100011", price=Decimal("6800.00"))
        self.pdb.add(part)
        self.pdb.commit()
        self.pdb.refresh(part)
        self.pdb.add(SparePartFitment(spare_part_id=part.id, crm_item_code="8901234500011", crm_item_name_cache="Split AC 1.5 T"))
        self.pdb.commit()

        fetched = self.pdb.query(SparePart).filter_by(part_code="SP-CMP-1501").one()
        self.assertEqual(fetched.part_name, "Inverter compressor 1.5 T")
        self.assertTrue(fetched.engineer_visible)  # default
        fitments = self.pdb.query(SparePartFitment).filter_by(spare_part_id=fetched.id).all()
        self.assertEqual(len(fitments), 1)
        self.assertEqual(fitments[0].crm_item_code, "8901234500011")

    def test_item_request_timeline_and_photos(self):
        req = ItemRequest(
            request_no="PRQ-00001", kind="part", crm_service_request_id=42, crm_service_request_no="SRV_1790673711021",
            crm_item_code="8901234500011", description="Inverter compressor 1.5 T x 1", amount=Decimal("6800.00"),
            stage="svm", crm_raised_by_user_id=self.eng.id, crm_raised_by_name=self.eng.name, crm_raised_by_role="engineer",
        )
        self.pdb.add(req)
        self.pdb.commit()
        self.pdb.refresh(req)
        for label in ("Wide shot", "Close-up of damage", "Part's label-code", "With the unit-box"):
            self.pdb.add(ItemRequestPhoto(item_request_id=req.id, file_path=f"/uploads/parts/{label}.jpg", label=label))
        self.pdb.add(ItemRequestEvent(item_request_id=req.id, kind="raised", text="Request raised from Service", crm_by_user_id=self.eng.id, crm_by_name=self.eng.name))
        self.pdb.commit()

        photos = self.pdb.query(ItemRequestPhoto).filter_by(item_request_id=req.id).all()
        events = self.pdb.query(ItemRequestEvent).filter_by(item_request_id=req.id).order_by(ItemRequestEvent.id).all()
        self.assertEqual(len(photos), 4)
        self.assertEqual(events[0].kind, "raised")

    def test_warranty_swap_round_trips(self):
        swap = PartWarrantySwap(crm_service_request_id=42, crm_item_code="8901234500011", old_serial_no="OLD123", new_serial_no="NEW456", mode="fresh")
        self.pdb.add(swap)
        self.pdb.commit()
        fetched = self.pdb.query(PartWarrantySwap).filter_by(new_serial_no="NEW456").one()
        self.assertEqual(fetched.mode, "fresh")

    def test_approval_chain_thresholds(self):
        self.assertFalse(needs_second_approval("part", 800))
        self.assertTrue(needs_second_approval("part", 1500))
        self.assertTrue(needs_second_approval("expense", 50))  # expenses always need both
        self.assertTrue(needs_second_approval("unit", 500))  # whole-unit always needs both, regardless of value

        self.assertEqual(next_stage_on_approve("part", 800, "svm"), "done")  # under threshold: one approval closes it
        self.assertEqual(next_stage_on_approve("part", 1500, "svm"), "sub")
        self.assertEqual(next_stage_on_approve("part", 1500, "sub"), "done")
        self.assertEqual(next_stage_on_approve("unit", 38500, "svm"), "sub")

        self.assertEqual(required_photos("part"), 4)
        self.assertEqual(required_photos("unit"), 5)
        self.assertEqual(required_photos("expense"), 0)

        self.assertIn("Service Manager", stage_label("part", 1500, "svm"))
        self.assertIn("Admin", stage_label("part", 1500, "svm"))  # "(then Admin)" hint when a second approval is coming
        self.assertEqual(stage_label("part", 800, "done"), "Approved")
        self.assertEqual(stage_label("part", 800, "rejected"), "Not approved")

    def test_no_foreign_key_into_the_crm_database(self):
        """Parts tables only ever reference the CRM by a plain integer/string column (crm_*), never a ForeignKey."""
        from app.parts.db import PartsBase

        crm_table_names = set()
        from app.database import Base as CrmBase

        crm_table_names = set(CrmBase.metadata.tables.keys())
        for table in PartsBase.metadata.tables.values():
            for fk in table.foreign_keys:
                self.assertNotIn(fk.column.table.name, crm_table_names, f"{table.name} must not have a real FK into the CRM database")
