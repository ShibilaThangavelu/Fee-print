"""Point every test at a throwaway database so the real feeprint.db is never touched."""

import os
import tempfile

os.environ["FEEPRINT_DB"] = os.path.join(tempfile.mkdtemp(), "feeprint-test.db")


import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def signed_in_client():
    """A client that has registered and is holding the session cookie."""
    import main

    c = TestClient(main.app)
    r = c.post("/api/auth/signup", json={"name": "Test", "email": "t@example.com", "password": "password123"})
    if r.status_code != 201:
        r = c.post("/api/auth/signin", json={"email": "t@example.com", "password": "password123"})
    assert r.status_code in (200, 201)
    return c
