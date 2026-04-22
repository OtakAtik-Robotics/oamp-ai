"""
test_api_client.py — Production readiness tests for ServerClient.

Covers:
  1. UID sanitization / injection prevention
  2. Payload validation (missing fields, bad expressions)
  3. Simulated timeout / 503 / malformed response
  4. Offline buffer write + count
  5. Graceful degradation (no crash on any failure mode)
"""

import json
import os
import sqlite3
import tempfile
import time
import threading
from unittest.mock import patch, MagicMock

import pytest

# Ensure src importable
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.api_client import (
    ServerClient,
    _sanitize_uid,
    _validate_session_data,
    _validate_expressions,
    _VALID_BUFFER_TABLES,
)


# ── Helpers ────────────────────────────────────────────────────────────

def _make_client(tmp_path, **kw):
    """Create ServerClient with temp DB, sync thread stopped immediately."""
    db_path = str(tmp_path / "test_buffer.db")
    kw.setdefault("timeout", 0.5)
    with patch("src.api_client._BUFFER_DB", db_path):
        client = ServerClient(base_url="http://127.0.0.1:1", **kw)
    # Stop sync thread and wait for it
    client._stop_sync.set()
    client._sync_thread.join(timeout=2.0)
    return client


def _good_game_data():
    return {
        "mode": "normal",
        "level_reached": 3,
        "total_time": 15.5,
        "cognitive_age": 8,
        "visuo_spatial_fit": 0.75,
        "dexterity_score": 80.0,
    }


def _good_expressions():
    return [
        {"level": 1, "dominant_emotion": "happy", "timestamp": "2026-01-01T00:00:00+00:00"},
        {"level": 2, "dominant_emotion": "neutral", "timestamp": "2026-01-01T00:01:00+00:00"},
    ]


# ── 1. UID sanitization ───────────────────────────────────────────────

class TestSanitizeUID:
    def test_valid_alphanumeric(self):
        assert _sanitize_uid("ABC123") == "ABC123"

    def test_valid_with_dashes(self):
        assert _sanitize_uid("RFID-ABC_123:456") == "RFID-ABC_123:456"

    def test_reject_path_traversal(self):
        assert _sanitize_uid("../../../etc/passwd") is None

    def test_reject_sql_injection(self):
        assert _sanitize_uid("'; DROP TABLE--") is None

    def test_reject_xss(self):
        assert _sanitize_uid("<script>alert(1)</script>") is None

    def test_reject_empty(self):
        assert _sanitize_uid("") is None
        assert _sanitize_uid("   ") is None

    def test_strip_whitespace(self):
        assert _sanitize_uid("  ABC123  ") == "ABC123"

    def test_truncate_long(self):
        long_uid = "A" * 100
        result = _sanitize_uid(long_uid)
        assert result is not None
        assert len(result) == 64

    def test_reject_special_chars(self):
        for bad in ["uid&1", "uid|2", "uid`3", 'uid"4', "uid'5", "uid;6", "uid\n7"]:
            assert _sanitize_uid(bad) is None, f"Should reject: {bad!r}"


# ── 2. Payload validation ────────────────────────────────────────────

class TestValidateSessionData:
    def test_valid(self):
        missing = _validate_session_data({
            "participant_id": 1,
            "mode": "normal",
            "level_reached": 3,
            "total_time": 15.0,
        })
        assert missing == []

    def test_missing_mode(self):
        missing = _validate_session_data({
            "participant_id": 1,
            "level_reached": 3,
            "total_time": 15.0,
        })
        assert "mode" in missing

    def test_missing_participant_id(self):
        missing = _validate_session_data({
            "mode": "normal",
            "level_reached": 3,
            "total_time": 15.0,
        })
        assert "participant_id" in missing

    def test_missing_all_required(self):
        missing = _validate_session_data({})
        assert len(missing) == 4


class TestValidateExpressions:
    def test_valid(self):
        issues = _validate_expressions(_good_expressions())
        assert issues == []

    def test_missing_timestamp(self):
        exprs = [{"level": 1, "dominant_emotion": "happy"}]
        issues = _validate_expressions(exprs)
        assert any("timestamp" in i for i in issues)

    def test_missing_dominant_emotion(self):
        exprs = [{"level": 1, "timestamp": "2026-01-01T00:00:00Z"}]
        issues = _validate_expressions(exprs)
        assert any("dominant_emotion" in i for i in issues)

    def test_not_dict(self):
        exprs = ["not a dict"]
        issues = _validate_expressions(exprs)
        assert any("not a dict" in i for i in issues)

    def test_empty_list_valid(self):
        issues = _validate_expressions([])
        assert issues == []


# ── 3. Simulated server failures ─────────────────────────────────────

class TestServerFailures:
    def test_connection_refused(self, tmp_path):
        """Server not running → no crash, returns None."""
        client = _make_client(tmp_path)
        result = client.authenticate("ABC123")
        assert result is None
        assert not client.is_online
        client.stop()

    def test_timeout_non_routable(self, tmp_path):
        """Non-routable IP → timeout, no crash."""
        client = _make_client(tmp_path, timeout=0.01)
        client.base_url = "http://10.255.255.1:1/api/v1"
        result = client._get("/test")
        assert result is None
        client.stop()

    def test_503_retry_exhausted(self, tmp_path):
        """503 response → retries 3x, returns None."""
        import requests as req
        client = _make_client(tmp_path)
        mock_resp = MagicMock()
        mock_resp.status_code = 503
        # On 3rd attempt raise_for_status is called, which raises HTTPError
        mock_resp.raise_for_status.side_effect = req.HTTPError("503")
        mock_resp.json.return_value = {}

        call_count = 0

        def counting_request(*a, **kw):
            nonlocal call_count
            call_count += 1
            return mock_resp

        with patch.object(client._session, "request", side_effect=counting_request):
            with patch("src.api_client.time.sleep"):
                result = client._request("GET", "/test")
        # 3rd attempt raises HTTPError, caught by _get → returns None
        assert result is None
        assert call_count == 3
        client.stop()

    def test_malformed_json_response(self, tmp_path):
        """200 with non-JSON body → returns None, no crash."""
        client = _make_client(tmp_path)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.side_effect = ValueError("Not JSON")

        with patch.object(client._session, "request", return_value=mock_resp):
            result = client._request("GET", "/test")
        assert result is None
        client.stop()

    def test_404_returns_none(self, tmp_path):
        """404 → returns None, server still marked online."""
        import requests as req
        client = _make_client(tmp_path)
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.raise_for_status.side_effect = req.HTTPError("404")

        with patch.object(client._session, "request", return_value=mock_resp):
            result = client._get("/robot/auth/MISSING")
        assert result is None
        assert client.is_online
        client.stop()

    def test_auth_response_data_not_dict(self, tmp_path):
        """auth returns data as list → None, no crash."""
        client = _make_client(tmp_path)
        with patch.object(
            client, "_get",
            return_value={"status": "success", "data": [1, 2, 3]},
        ):
            result = client.authenticate("ABC123")
        assert result is None
        client.stop()


# ── 4. Offline buffer ─────────────────────────────────────────────────

class TestOfflineBuffer:
    def test_buffer_write(self, tmp_path):
        """Failed submission → payload stored in SQLite."""
        client = _make_client(tmp_path)
        payload = {"session": {"participant_id": 1, "mode": "normal"}}
        client._buffer("pending_sessions", payload)

        with client._db_lock:
            rows = client._db.execute(
                "SELECT payload FROM pending_sessions"
            ).fetchall()
        assert len(rows) == 1
        assert json.loads(rows[0][0]) == payload
        client.stop()

    def test_buffer_rejects_invalid_table(self, tmp_path):
        """_buffer rejects unknown table name."""
        client = _make_client(tmp_path)
        client._buffer("evil_table", {"bad": True})
        # Should not crash, table shouldn't exist
        with pytest.raises(sqlite3.OperationalError):
            with client._db_lock:
                client._db.execute("SELECT * FROM evil_table")
        client.stop()

    def test_buffer_face_logs(self, tmp_path):
        """Face logs buffered on offline."""
        client = _make_client(tmp_path)
        client._online = False

        logs = [{"level": 1, "dominant_emotion": "happy", "timestamp": "t"}]
        payload = {"session_id": 1, "logs": logs}
        client._buffer("pending_face_logs", payload)

        with client._db_lock:
            rows = client._db.execute(
                "SELECT payload FROM pending_face_logs"
            ).fetchall()
        assert len(rows) == 1
        client.stop()


# ── 5. Build payload validation integration ───────────────────────────

class TestBuildPayload:
    def test_valid_payload(self, tmp_path):
        client = _make_client(tmp_path)
        payload = client.build_session_payload(
            participant_id=1,
            game_data=_good_game_data(),
            expressions=_good_expressions(),
        )
        assert payload is not None
        assert payload["session"]["participant_id"] == 1
        assert len(payload["expressions"]) == 2
        client.stop()

    def test_missing_game_fields(self, tmp_path):
        client = _make_client(tmp_path)
        payload = client.build_session_payload(
            participant_id=1,
            game_data={"mode": "normal"},  # missing level_reached, total_time
        )
        assert payload is None
        client.stop()

    def test_bad_expressions(self, tmp_path):
        client = _make_client(tmp_path)
        payload = client.build_session_payload(
            participant_id=1,
            game_data=_good_game_data(),
            expressions=[{"bad_key": "val"}],  # missing required keys
        )
        assert payload is None
        client.stop()

    def test_invalid_session_id_rejected(self, tmp_path):
        client = _make_client(tmp_path)
        # Negative session_id — should log error, no crash
        client.submit_face_logs(-1, [{"level": 1, "dominant_emotion": "happy", "timestamp": "t"}])
        # String session_id
        client.submit_face_logs("abc", [{"level": 1, "dominant_emotion": "happy", "timestamp": "t"}])
        # Wait for background threads
        time.sleep(0.3)
        client.stop()


# ── 6. Graceful end-to-end ───────────────────────────────────────────

class TestGracefulDegradation:
    def test_full_offline_flow(self, tmp_path):
        """Complete game flow with server down → no crash, data buffered."""
        client = _make_client(tmp_path)

        # Auth fails
        child = client.authenticate("ABC123")
        assert child is None

        # Build payload manually
        payload = client.build_session_payload(
            participant_id=999,
            game_data=_good_game_data(),
            expressions=_good_expressions(),
        )
        assert payload is not None

        # Submit fails, buffers
        sid = client.submit_game_session(payload)
        assert sid is None

        # Verify buffered
        with client._db_lock:
            rows = client._db.execute(
                "SELECT payload FROM pending_sessions"
            ).fetchall()
        assert len(rows) == 1

        client.stop()

    def test_auth_with_injection_uid(self, tmp_path):
        """Injection UID rejected before any HTTP call."""
        client = _make_client(tmp_path)
        client._get = MagicMock(side_effect=AssertionError("Should not reach HTTP"))

        result = client.authenticate("'; DROP TABLE participants;--")
        assert result is None
        client._get.assert_not_called()
        client.stop()

    def test_health_check_offline(self, tmp_path):
        client = _make_client(tmp_path)
        assert client.health_check() is False
        client.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
