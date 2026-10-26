from types import SimpleNamespace
from unittest.mock import Mock

from app.routers.installations import _canonical_order_item_code
from app.routers.orders import _resolve_item_code


def test_order_item_uses_linked_item_master_code_instead_of_scientific_notation():
    db = Mock()
    db.get.return_value = SimpleNamespace(item_code="8908012210924")
    order_item = SimpleNamespace(item_id=109, item_code="8.90801E+12")

    assert _canonical_order_item_code(db, order_item) == "8908012210924"


def test_order_import_prefers_linked_item_master_code_over_csv_value():
    db = Mock()
    db.get.return_value = SimpleNamespace(item_code="8908012210924")

    assert _resolve_item_code(db, 109, "8.90801E+12") == "8908012210924"


def test_unlinked_order_item_preserves_original_text_code():
    db = Mock()
    order_item = SimpleNamespace(item_id=None, item_code="CUSTOM-ITEM-01")

    assert _canonical_order_item_code(db, order_item) == "CUSTOM-ITEM-01"
    assert _resolve_item_code(db, None, "CUSTOM-ITEM-01") == "CUSTOM-ITEM-01"
