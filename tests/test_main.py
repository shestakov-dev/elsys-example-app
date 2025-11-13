import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture(autouse=True)
def isolate_storage(tmp_path, monkeypatch):
    """Redirect the app STORAGE_DIR to a temporary directory and reset counters.

    This ensures tests run isolated and don't touch the real `storage/` folder.
    """
    storage = tmp_path / "storage"
    storage.mkdir()

    # Monkeypatch the STORAGE_DIR and reset files_stored_counter
    monkeypatch.setattr(main, "STORAGE_DIR", storage)
    monkeypatch.setattr(main, "files_stored_counter", 0)

    yield


@pytest.fixture
def client():
    return TestClient(main.app)


def test_root_contains_message_and_endpoints(client):
    r = client.get("/")
    assert r.status_code == 200
    data = r.json()
    assert "message" in data and "File Storage API" in data["message"]
    assert "endpoints" in data and isinstance(data["endpoints"], list)


def test_health_returns_status_and_timestamp(client):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "service" in data and "File Storage API" in data["service"]


def test_list_files_empty_initially(client):
    r = client.get("/files")
    assert r.status_code == 200
    data = r.json()
    assert data["files"] == []
    assert data["count"] == 0


def test_store_file_and_retrieve_it(client):
    # upload a file
    files = {"file": ("test.txt", b"hello world", "text/plain")}
    r = client.post("/files", files=files)
    assert r.status_code == 200
    data = r.json()
    assert data["filename"] == "test.txt"
    assert data["size"] == len(b"hello world")

    # listing should include the file
    r = client.get("/files")
    assert r.status_code == 200
    data = r.json()
    assert "test.txt" in data["files"]
    assert data["count"] == 1

    # retrieve the file
    r = client.get("/files/test.txt")
    assert r.status_code == 200
    assert r.content == b"hello world"


def test_metrics_reflects_stored_files(client):
    # no files initially
    r = client.get("/metrics")
    assert r.status_code == 200
    data = r.json()
    assert data["files_current"] == 0
    assert data["files_stored_total"] == 0

    # store a file
    files = {"file": ("a.bin", b"abc", "application/octet-stream")}
    r = client.post("/files", files=files)
    assert r.status_code == 200

    # metrics should update
    r = client.get("/metrics")
    assert r.status_code == 200
    data = r.json()
    assert data["files_current"] == 1
    assert data["files_stored_total"] == 1
    assert data["total_storage_bytes"] >= 3


def test_get_file_prevents_directory_traversal(client):
    # Attempt to fetch a file outside storage via traversal
    r = client.get("/files/../secret.txt")
    # App may return 400 (invalid filename) or 404 (not found) depending on
    # pathlib.resolve()/is_relative_to behavior in the environment. Both are
    # acceptable because they do not expose the file outside storage.
    assert r.status_code in (400, 404)
    data = r.json()
    assert ("Invalid filename" in str(data.get("detail", ""))) or (
        "not found" in str(data.get("detail", "")).lower()
    )
