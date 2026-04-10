import json
import sqlite3
import threading
import time
import uuid
import logging
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass

logger = logging.getLogger("api_client")

try:
    import requests
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False
    logger.warning("requests tidak terinstall. Jalankan: pip install requests")


@dataclass
class SessionResult:
    session_id: str
    child_id: str
    robot_id: str
    waktu_solve: float
    skor: int
    jumlah_percobaan: int
    status: str = "completed"      # completed | skipped
    hand_logs: Optional[list] = None


class ServerClient:
    """
    Client HTTP ke server Go.

    Args:
        base_url:       e.g. "http://192.168.1.100:8080"
        robot_id:       UUID robot ini (didapat saat register ke server)
        db_path:        Path file SQLite lokal untuk buffer offline
        sync_interval:  Detik antar upaya sync data offline (default 15)
        timeout:        HTTP request timeout detik (default 3)
    """

    def __init__(
        self,
        base_url: str,
        robot_id: str,
        db_path: str = "local_buffer.db",
        sync_interval: int = 15,
        timeout: int = 3,
    ):
        self.base_url = base_url.rstrip("/")
        self.robot_id = robot_id
        self.timeout = timeout
        self._online = False

        # Setup SQLite buffer
        self._db_path = Path(db_path)
        self._init_local_db()

        # Background sync thread
        self._sync_interval = sync_interval
        self._sync_thread = threading.Thread(
            target=self._sync_worker,
            daemon=True,
            name="OfflineSync",
        )
        self._sync_thread.start()
        logger.info(f"ServerClient initialized. Server: {self.base_url}")

    def _init_local_db(self):
        """Buat tabel buffer kalau belum ada."""
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS session_buffer (
                    id          TEXT PRIMARY KEY,
                    payload     TEXT NOT NULL,
                    created_at  REAL NOT NULL,
                    synced      INTEGER NOT NULL DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS heartbeat_buffer (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    payload     TEXT NOT NULL,
                    created_at  REAL NOT NULL,
                    synced      INTEGER NOT NULL DEFAULT 0
                )
            """)
            conn.commit()

    def _buffer_session(self, result: SessionResult):
        payload = {
            "session_id":       result.session_id,
            "waktu_solve":      result.waktu_solve,
            "skor":             result.skor,
            "jumlah_percobaan": result.jumlah_percobaan,
            "status":           result.status,
        }
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO session_buffer (id, payload, created_at, synced) VALUES (?,?,?,0)",
                (result.session_id, json.dumps(payload), time.time()),
            )
            conn.commit()
        logger.info(f"📦 Buffered session {result.session_id} ke SQLite")

    def _get_unsynced_sessions(self) -> List[dict]:
        with sqlite3.connect(self._db_path) as conn:
            rows = conn.execute(
                "SELECT id, payload FROM session_buffer WHERE synced=0 ORDER BY created_at"
            ).fetchall()
        return [{"id": r[0], "payload": json.loads(r[1])} for r in rows]

    def _mark_synced(self, session_id: str):
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "UPDATE session_buffer SET synced=1 WHERE id=?",
                (session_id,),
            )
            conn.commit()

    def _post(self, path: str, data: dict) -> Optional[dict]:
        if not _HAS_REQUESTS:
            return None
        try:
            r = requests.post(
                f"{self.base_url}{path}",
                json=data,
                timeout=self.timeout,
            )
            self._online = True
            r.raise_for_status()
            return r.json()
        except requests.exceptions.ConnectionError:
            self._online = False
            logger.warning(f"⚠️  Server tidak terjangkau: {self.base_url}{path}")
            return None
        except Exception as e:
            logger.error(f"HTTP error {path}: {e}")
            return None

    def _get(self, path: str) -> Optional[dict]:
        if not _HAS_REQUESTS:
            return None
        try:
            r = requests.get(f"{self.base_url}{path}", timeout=self.timeout)
            self._online = True
            r.raise_for_status()
            return r.json()
        except requests.exceptions.ConnectionError:
            self._online = False
            return None
        except Exception as e:
            logger.error(f"HTTP GET error {path}: {e}")
            return None

    def get_child_by_rfid(self, rfid_tag: str) -> Optional[dict]:
        result = self._get(f"/child/rfid/{rfid_tag}")
        if result and result.get("success"):
            return result.get("data")
        return None

    def get_child_by_qr(self, qr_code: str) -> Optional[dict]:
        result = self._get(f"/child/qr/{qr_code}")
        if result and result.get("success"):
            return result.get("data")
        return None

    def get_child_by_nomor(self, nomor: str) -> Optional[dict]:
        result = self._get(f"/child/nomor/{nomor}")
        if result and result.get("success"):
            return result.get("data")
        return None

    def start_session(self, child_id: str, level: int, variant: str) -> Optional[str]:
        result = self._post("/session/start", {
            "child_id": child_id,
            "robot_id": self.robot_id,
            "level":    level,
            "variant":  variant,
        })
        if result and result.get("success"):
            return result["data"]["session_id"]

        local_id = str(uuid.uuid4())
        logger.info(f"📦 Session dimulai offline, ID lokal: {local_id}")
        return local_id

    def end_session(self, result: SessionResult) -> bool:
        payload = {
            "session_id":       result.session_id,
            "waktu_solve":      result.waktu_solve,
            "skor":             result.skor,
            "jumlah_percobaan": result.jumlah_percobaan,
            "status":           result.status,
        }
        response = self._post("/session/end", payload)
        if response and response.get("success"):
            logger.info(f"✅ Session {result.session_id} tersimpan ke server")

            if result.hand_logs:
                self._post("/session/hand-logs", {
                    "session_id": result.session_id,
                    "logs":       result.hand_logs,
                })
            return True

        self._buffer_session(result)
        return False

    def send_heartbeat(self, status: str, baterai_persen: int = 100):
        self._post("/robot/heartbeat", {
            "robot_id":       self.robot_id,
            "status":         status,
            "baterai_persen": baterai_persen,
        })

    @property
    def is_online(self) -> bool:
        return self._online


    def _sync_worker(self):
        while True:
            time.sleep(self._sync_interval)
            try:
                self._do_sync()
            except Exception as e:
                logger.error(f"Sync error: {e}")

    def _do_sync(self):
        pending = self._get_unsynced_sessions()
        if not pending:
            return

        logger.info(f"🔄 Syncing {len(pending)} sesi offline...")
        payloads = [row["payload"] for row in pending]

        response = self._post("/session/sync-buffer", payloads)
        if not response:
            return

        for row in pending:
            self._mark_synced(row["id"])

        synced = response.get("data", {}).get("synced", 0)
        logger.info(f"✅ Sync selesai: {synced}/{len(pending)} berhasil")