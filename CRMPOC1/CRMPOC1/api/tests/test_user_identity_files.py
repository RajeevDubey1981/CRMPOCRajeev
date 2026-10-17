from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("MYSQL_DATABASE_URL", "sqlite://")
os.environ.setdefault("UPLOAD_DIR", str(Path(tempfile.mkdtemp(prefix="indcool_user_files_")) / "uploads"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import User
from app.security import create_access_token, hash_password
from app.seed import seed_roles

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 200
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 200
PDF = b"%PDF-1.4\n" + b"0" * 200


class UserIdentityFileTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(engine)
        self.Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
        self.db = self.Session()
        seed_roles(self.db)

        def override():
            session = self.Session()
            try:
                yield session
            finally:
                session.close()

        app.dependency_overrides[get_db] = override
        self.client = TestClient(app)
        self.admin = self._user("admin@files.test", "admin")
        self.subadmin = self._user("sub@files.test", "sub_admin")
        self.engineer = self._user("engineer@files.test", "engineer")
        self.db.commit()

    def tearDown(self):
        app.dependency_overrides.clear()
        self.db.close()

    def _user(self, email, role):
        user = User(name=email.split("@")[0], email=email, password_hash=hash_password("password123"), role=role, is_active=True)
        self.db.add(user)
        self.db.flush()
        return user

    def _headers(self, user):
        return {"Authorization": f"Bearer {create_access_token(subject=str(user.id), extra_claims={'role': user.role})}"}

    def test_admin_creates_user_with_protected_files_and_replaces_profile(self):
        payload = {"name": "New User", "email": "new.files@example.com", "password": "password123", "role": "engineer", "is_active": True}
        response = self.client.post(
            "/api/users", data={"payload": json.dumps(payload)},
            files={"id_proof": ("identity.pdf", PDF, "application/pdf"), "profile_picture": ("photo.png", PNG, "image/png")},
            headers=self._headers(self.admin),
        )
        self.assertEqual(response.status_code, 201, response.text)
        out = response.json()
        self.assertTrue(out["has_id_proof"])
        self.assertTrue(out["has_profile_picture"])
        self.assertEqual(out["id_proof_filename"], "identity.pdf")
        self.assertEqual(self.client.get(f"/api/users/{out['id']}/id-proof", headers=self._headers(self.admin)).content, PDF)
        self.assertEqual(self.client.get(f"/api/users/{out['id']}/profile-picture", headers=self._headers(self.admin)).content, PNG)
        self.assertEqual(self.client.get(f"/api/users/{out['id']}/id-proof", headers=self._headers(self.engineer)).status_code, 403)

        updated = self.client.put(
            f"/api/users/{out['id']}", data={"payload": json.dumps({"phone": "9999999999"})},
            files={"profile_picture": ("replacement.jpg", JPEG, "image/jpeg")}, headers=self._headers(self.subadmin),
        )
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(updated.json()["profile_picture_filename"], "replacement.jpg")

    def test_rejects_unsupported_or_oversized_files(self):
        payload = {"name": "Bad File", "email": "bad.files@example.com", "password": "password123", "role": "engineer"}
        bad_type = self.client.post(
            "/api/users", data={"payload": json.dumps(payload)},
            files={"id_proof": ("identity.doc", b"not-doc", "application/msword")}, headers=self._headers(self.admin),
        )
        self.assertEqual(bad_type.status_code, 400, bad_type.text)
        too_large = self.client.post(
            "/api/users", data={"payload": json.dumps(payload)},
            files={"profile_picture": ("photo.png", b"\x89PNG\r\n\x1a\n" + b"0" * (2 * 1024 * 1024), "image/png")},
            headers=self._headers(self.admin),
        )
        self.assertEqual(too_large.status_code, 413, too_large.text)


if __name__ == "__main__":
    unittest.main()
