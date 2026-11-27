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


if __name__ == "__main__":
    unittest.main()
