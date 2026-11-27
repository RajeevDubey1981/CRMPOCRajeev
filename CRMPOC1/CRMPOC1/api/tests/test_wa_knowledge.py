from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("MYSQL_DATABASE_URL", "sqlite://")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import wa_knowledge as k


class KnowledgeLookupTests(unittest.TestCase):
    def test_the_catalogue_is_split_into_products(self):
        head, products = k.load()
        self.assertGreaterEqual(len(products), 100)
        self.assertIn("1800 119 515", head)
        self.assertNotIn("Product page:", head)  # the general part holds no product blocks

    def test_a_model_code_finds_exactly_that_product(self):
        out = k.for_query("what is the ISEER of IDCACSBF18K5HE")
        self.assertIn("Product code: IDCACSBF18K5HE", out)
        self.assertLessEqual(out.count("Product page:"), k.MAX_PRODUCTS)

    def test_size_and_star_words_find_matching_ac_listings(self):
        out = k.for_query("price of 1.5 ton 5 star inverter split ac")
        self.assertIn("1.5 Ton", out)
        self.assertIn("5 Star", out)

    def test_a_freezer_question_finds_freezers_not_fans(self):
        out = k.for_query("deep freezer 300 L")
        self.assertIn("reezer", out[len(k.load()[0]):])

    def test_nothing_matching_sends_only_the_general_text(self):
        out = k.for_query("asdf qwer")
        self.assertEqual(out, k.load()[0])

    def test_the_total_stays_well_inside_the_models_memory(self):
        for q in ("1.5 ton 5 star inverter split ac", "water cooler 80 litre", "geyser", "inverter"):
            self.assertLess(len(k.for_query(q)), 24000, q)


class ExtraKnowledgeTests(unittest.TestCase):
    def test_an_error_code_finds_its_own_block_first(self):
        out = k.for_query("my AC shows E6 error")
        extra = out[len(k.load()[0]):]
        self.assertIn("### Split AC error code E6", extra.split("###")[1] and extra)
        self.assertLess(extra.index("error code E6"), extra.index("error code E8") if "error code E8" in extra else 10**9)

    def test_every_error_code_in_the_manual_is_present(self):
        text = k.EXTRA_FILE.read_text(encoding="utf-8")
        for code in ("EE", "E1", "E2", "E3", "E4", "E0", "E6", "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "E8",
                     "P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9", "PC", "PH", "L1", "L2", "L3", "L4"):
            self.assertIn(f"### Split AC error code {code}:", text, code)

    def test_manual_troubleshooting_is_found_by_the_customers_words(self):
        out = k.for_query("my AC is not starting")
        self.assertIn("Split AC problem: AC unit is not starting", out)
        out = k.for_query("the remote is not working")
        self.assertIn("Remote controller not working", out)

    def test_room_questions_reach_the_model_guide(self):
        out = k.for_query("which AC for a small bedroom")
        self.assertIn("best-for rooms", out)

    def test_the_safety_rules_for_error_codes_are_always_sent(self):
        head = k.load()[0]
        self.assertIn("Never tell a customer to open the indoor or outdoor unit", head)

    def test_rate_card_content_never_reaches_the_assistant(self):
        text = (k.KNOWLEDGE_FILE.read_text(encoding="utf-8") + k.EXTRA_FILE.read_text(encoding="utf-8")).lower()
        for word in ("rate card", "franchise rate", "asc rate"):
            self.assertNotIn(word, text.replace("the rate card documents are intentionally not included", "").replace("the rate card documents are deliberately not used", ""), word)


if __name__ == "__main__":
    unittest.main()


class OffersTests(unittest.TestCase):
    def test_questions_about_offers_reach_the_offers_entries(self):
        from app.services import wa_knowledge as k

        for q in ("any offer on AC", "EMI available?", "what is the free electricity scheme", "CSD canteen price"):
            _, blocks = k.select_blocks(q)
            self.assertTrue(blocks and blocks[0].startswith("[Offers and schemes]"), q)
