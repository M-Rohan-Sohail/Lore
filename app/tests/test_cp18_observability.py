import pytest
import os
import sqlite3
import datetime
import uuid
import json
import logging
from unittest.mock import patch

from app.jobs.backups import perform_backup
from app.config import settings

@pytest.fixture
def mock_backup_env(tmp_path):
    old_db = settings.DATABASE_URL
    old_storage = settings.BACKUP_STORAGE_PATH
    
    # Setup test DB
    test_db_path = tmp_path / "test_backup.db"
    conn = sqlite3.connect(test_db_path)
    conn.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY, value TEXT)")
    conn.execute("INSERT INTO test_table (value) VALUES ('hello backup')")
    conn.commit()
    conn.close()
    
    settings.DATABASE_URL = f"sqlite+aiosqlite:///{test_db_path}"
    settings.BACKUP_STORAGE_PATH = str(tmp_path / "backups")
    settings.BACKUP_PASSPHRASE = "test_passphrase"
    
    yield test_db_path, settings.BACKUP_STORAGE_PATH
    
    settings.DATABASE_URL = old_db
    settings.BACKUP_STORAGE_PATH = old_storage

def test_backup_job_and_restore(mock_backup_env):
    db_path, storage_path = mock_backup_env
    
    # 1. Run Backup Job
    result = perform_backup()
    assert result is True
    
    # 2. Verify Backup Exists and is Encrypted
    files = os.listdir(storage_path)
    assert len(files) == 1
    gpg_file = files[0]
    assert gpg_file.endswith(".gpg")
    
    # 3. Restore Drill (Decrypt)
    gpg_path = os.path.join(storage_path, gpg_file)
    restored_db_path = os.path.join(storage_path, "restored.db")
    
    import subprocess
    subprocess.run([
        "gpg", "--decrypt", "--batch", "--yes", "--passphrase", "test_passphrase",
        "-o", restored_db_path, gpg_path
    ], check=True)
    
    # 4. Smoke Test the Restored DB
    assert os.path.exists(restored_db_path)
    conn = sqlite3.connect(restored_db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM test_table")
    row = cursor.fetchone()
    assert row[0] == "hello backup"
    conn.close()

from fastapi.testclient import TestClient
from app.main import app

def test_observability_structured_logging(caplog):
    caplog.set_level(logging.INFO, logger="http")
    
    client = TestClient(app)
    # We want to use a specific request ID
    req_id = str(uuid.uuid4())
    res = client.get("/health", headers={"X-Request-ID": req_id})
    assert res.status_code == 200
    
    # Check that caplog captured the request with JSON properties
    # Since we are using standard caplog, it intercepts the LogRecord
    found = False
    for record in caplog.records:
        if getattr(record, "request_id", None) == req_id:
            assert hasattr(record, "latency_ms")
            assert record.path == "/health"
            found = True
            break
            
    assert found, "Structured log with request_id not found"

@patch("app.core.analytics.posthog")
@pytest.mark.asyncio
async def test_posthog_telemetry_called(mock_posthog):
    from app.core.analytics import track_sign_up
    
    uid = uuid.uuid4()
    await track_sign_up(uid, "test_provider")
    
    if mock_posthog is not None:
        mock_posthog.capture.assert_called_once_with(
            str(uid), "sign_up", properties={"provider": "test_provider"}
        )
