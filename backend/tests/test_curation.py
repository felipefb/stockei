"""Stockei - Testes da curadoria do dataset (double-check humano)."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_stockei.db")

import pytest
from fastapi.testclient import TestClient

import backend.app as app_module
from backend.app import _rate_state, app
from backend.database import Base, engine


@pytest.fixture()
def scraped_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(app_module, "_SCRAPED", tmp_path)
    manifest = {
        "aaa.jpg": {"url": "http://x/1.jpg", "query": "validade lata",
                    "sha1": "1", "status": "pending"},
        "bbb.jpg": {"url": "http://x/2.jpg", "query": "validade pote",
                    "sha1": "2", "status": "pending"},
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (tmp_path / "aaa.jpg").write_bytes(b"fake")
    (tmp_path / "bbb.jpg").write_bytes(b"fake")
    return tmp_path


@pytest.fixture(scope="module")
def client():
    _rate_state.clear()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="module")
def auth(client):
    client.post("/auth/register", json={
        "email": "cur@stockei.com", "password": "secret123", "name": "C"})
    token = client.post("/auth/login", json={
        "email": "cur@stockei.com", "password": "secret123"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_pending_lists_images(client, auth, scraped_dir):
    d = client.get("/dataset/pending", headers=auth).json()
    assert len(d["pending"]) == 2
    assert d["kept"] == 0


def test_keep_with_ground_truth(client, auth, scraped_dir):
    r = client.post("/dataset/curate", headers=auth,
                    json={"file": "aaa.jpg", "keep": True, "true_date": "2026-10-03"})
    assert r.status_code == 200
    manifest = json.loads((scraped_dir / "manifest.json").read_text())
    assert manifest["aaa.jpg"]["status"] == "kept"
    assert manifest["aaa.jpg"]["true_date"] == "2026-10-03"
    assert (scraped_dir / "aaa.jpg").exists()


def test_discard_removes_file(client, auth, scraped_dir):
    client.post("/dataset/curate", headers=auth,
                json={"file": "bbb.jpg", "keep": False})
    manifest = json.loads((scraped_dir / "manifest.json").read_text())
    assert manifest["bbb.jpg"]["status"] == "discarded"
    assert not (scraped_dir / "bbb.jpg").exists()


def test_invalid_ground_truth(client, auth, scraped_dir):
    r = client.post("/dataset/curate", headers=auth,
                    json={"file": "aaa.jpg", "keep": True, "true_date": "10/26"})
    assert r.status_code == 422


def test_unknown_file(client, auth, scraped_dir):
    r = client.post("/dataset/curate", headers=auth,
                    json={"file": "zzz.jpg", "keep": True})
    assert r.status_code == 404
