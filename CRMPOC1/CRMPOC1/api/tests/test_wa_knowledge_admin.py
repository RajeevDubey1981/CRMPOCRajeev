from __future__ import annotations

import io
import os
import sys
import unittest
import zipfile
from pathlib import Path

os.environ.setdefault("MYSQL_DATABASE_URL", "sqlite://")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import User
from app.models.whatsapp import WaKnowledge
from app.security import create_access_token, hash_password
from app.seed import seed_roles
from app.services import wa_knowledge as k


def make_docx(paragraphs: list[str]) -> bytes:
    body = "".join(f"<w:p><w:r><w:t>{p}</w:t></w:r></w:p>" for p in paragraphs)
    xml = f'<?xml version="1.0"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>{body}</w:body></w:document>'
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml", xml)
    return buf.getvalue()


class KnowledgeAdminTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(engine)
        self.Session = sessionmaker(bind=engine, expire_on_commit=False)
        self.db = self.Session()
        seed_roles(self.db)
        self.admin = User(name="Admin", email="a@x.com", password_hash=hash_password("x"), role="admin", is_active=True)
        self.eng = User(name="Eng", email="e@x.com", password_hash=hash_password("x"), role="engineer", is_active=True)
        self.db.add_all([self.admin, self.eng])
        self.db.commit()

        def override():
            s = self.Session()
            try:
                yield s
            finally:
                s.close()

        app.dependency_overrides[get_db] = override
        self.client = TestClient(app, raise_server_exceptions=False)
        k._CACHE.update({"sig": None, "head": "", "products": []})

    def tearDown(self):
        app.dependency_overrides.clear()
        self.db.close()

    def h(self, u):
        return {"Authorization": f"Bearer {create_access_token(subject=str(u.id), extra_claims={'role': u.role})}"}

    def count(self):
        self.db.expire_all()
        return self.db.scalar(select(func.count()).select_from(WaKnowledge))

    def test_only_an_administrator_can_use_it(self):
        self.assertEqual(self.client.get("/api/whatsapp/knowledge", headers=self.h(self.eng)).status_code, 403)
        self.assertEqual(self.client.post("/api/whatsapp/knowledge", json={"title": "x", "body": "y"}, headers=self.h(self.eng)).status_code, 403)
        self.assertEqual(self.client.get("/api/whatsapp/knowledge").status_code, 401)

    def test_until_someone_changes_something_the_builtin_files_are_used(self):
        r = self.client.get("/api/whatsapp/knowledge", headers=self.h(self.admin)).json()
        self.assertEqual((r["using"], r["items"]), ("builtin files", []))
        self.assertIn("1800 119 515", k.for_query("hello", self.db))

    def test_the_first_change_keeps_everything_from_the_files(self):
        r = self.client.post("/api/whatsapp/knowledge", json={"title": "Warranty IDCXYZ1", "category": "Test", "body": "IDCXYZ1 has a 9 year warranty."}, headers=self.h(self.admin))
        self.assertEqual(r.status_code, 200, r.text)
        self.assertGreater(self.count(), 100)  # the files were copied in first
        listing = self.client.get("/api/whatsapp/knowledge", headers=self.h(self.admin)).json()
        self.assertEqual(listing["using"], "database")
        self.assertIn("1800 119 515", k.for_query("hello", self.db))  # still has the general rules
        self.assertIn("IDCXYZ1 has a 9 year warranty", k.for_query("tell me about IDCXYZ1", self.db))

    def test_an_edit_applies_to_the_very_next_question(self):
        e = self.client.post("/api/whatsapp/knowledge", json={"title": "Item IDCQQQ9", "body": "Old text about IDCQQQ9."}, headers=self.h(self.admin)).json()
        self.assertIn("Old text", k.for_query("IDCQQQ9", self.db))
        self.client.put(f"/api/whatsapp/knowledge/{e['id']}", json={"body": "New text about IDCQQQ9."}, headers=self.h(self.admin))
        out = k.for_query("IDCQQQ9", self.db)
        self.assertIn("New text", out)
        self.assertNotIn("Old text", out)

    def test_switching_an_entry_off_or_deleting_it_removes_it(self):
        e = self.client.post("/api/whatsapp/knowledge", json={"title": "Item IDCWWW7", "body": "Secret-ish note about IDCWWW7."}, headers=self.h(self.admin)).json()
        self.client.put(f"/api/whatsapp/knowledge/{e['id']}", json={"active": False}, headers=self.h(self.admin))
        self.assertNotIn("Secret-ish note", k.for_query("IDCWWW7", self.db))
        self.client.put(f"/api/whatsapp/knowledge/{e['id']}", json={"active": True}, headers=self.h(self.admin))
        self.assertIn("Secret-ish note", k.for_query("IDCWWW7", self.db))
        self.assertEqual(self.client.delete(f"/api/whatsapp/knowledge/{e['id']}", headers=self.h(self.admin)).status_code, 200)
        self.assertNotIn("Secret-ish note", k.for_query("IDCWWW7", self.db))

    def test_a_general_rule_marked_always_send_goes_with_every_question(self):
        self.client.post("/api/whatsapp/knowledge", json={"title": "Support hours", "body": "We answer 10 am to 6 pm Monday to Friday.", "always_send": True}, headers=self.h(self.admin))
        self.assertIn("10 am to 6 pm", k.for_query("anything at all", self.db))

    def test_a_markdown_file_with_headings_becomes_one_entry_per_heading(self):
        md = b"## Offers\n### Festive offer IDCOFF1\nFlat discount on IDCOFF1.\n### Exchange offer IDCOFF2\nExchange bonus on IDCOFF2.\n"
        r = self.client.post("/api/whatsapp/knowledge-upload", files={"file": ("offers.md", md)}, data={"category": ""}, headers=self.h(self.admin))
        self.assertEqual((r.status_code, r.json().get("created")), (200, 2), r.text)
        self.assertIn("Flat discount", k.for_query("IDCOFF1", self.db))

    def test_a_word_file_is_read_and_split_into_parts(self):
        docx = make_docx([f"Line {i} about IDCDOC5 " + "x" * 120 for i in range(40)])
        r = self.client.post("/api/whatsapp/knowledge-upload", files={"file": ("guide.docx", docx)}, headers=self.h(self.admin))
        self.assertEqual(r.status_code, 200, r.text)
        self.assertGreater(r.json()["created"], 1)
        self.assertIn("IDCDOC5", k.for_query("IDCDOC5", self.db))

    def test_a_pdf_or_an_unknown_file_is_refused_with_a_clear_reason(self):
        r = self.client.post("/api/whatsapp/knowledge-upload", files={"file": ("x.pdf", b"%PDF-1.4")}, headers=self.h(self.admin))
        self.assertEqual(r.status_code, 422)
        self.assertIn("Word", r.json()["detail"])
        self.assertEqual(self.client.post("/api/whatsapp/knowledge-upload", files={"file": ("x.exe", b"MZ")}, headers=self.h(self.admin)).status_code, 422)
        self.assertEqual(self.count(), 0)  # a refused upload changes nothing

    def test_preview_shows_what_the_assistant_would_get(self):
        r = self.client.post("/api/whatsapp/knowledge-preview", json={"question": "my AC shows E6 error"}, headers=self.h(self.admin))
        self.assertEqual(r.status_code, 200, r.text)
        self.assertTrue(any("E6" in t for t in r.json()["matched"]))
        self.assertGreater(r.json()["general_chars"], 1000)

    def test_an_entry_needs_a_title_and_text(self):
        self.assertEqual(self.client.post("/api/whatsapp/knowledge", json={"title": "", "body": "x"}, headers=self.h(self.admin)).status_code, 422)
        self.assertEqual(self.client.post("/api/whatsapp/knowledge", json={"title": "x", "body": " "}, headers=self.h(self.admin)).status_code, 422)


if __name__ == "__main__":
    unittest.main()
