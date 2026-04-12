import logging
import threading
from typing import Optional
import requests
import os
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("api_client")

class ServerClient:
    """
    HTTP client for the OAMP Go backend server.

    Reads BASE_URL from .env (BACKEND_API_URL).
    Default: http://localhost:8080/api/v1

    Typical usage flow:
        client = ServerClient()

        # 1. Robot taps RFID -> authenticate child
        child = client.authenticate("RFID-ABC123")
        if not child:
            # unknown card, skip
            return

        # 2. Calibrate robot height using child["height"]
        robot.set_height(child["height"])

        # 3. Child plays the game...
        # ...collect game data, expressions, datasets during play...

        # 4. Build and submit session payload
        payload = client.build_session_payload(
            participant_id=child["id"],
            game_data={
                "mode": "normal",
                "level_reached": 5,
                "total_time": 23.4,
                "cognitive_age": 10,
                "visuo_spatial_fit": 0.87,
                "dexterity_score": 92.5,
            },
            expressions=face_expression_list,
            datasets=dataset_capture_list,
        )
        session_id = client.submit_game_session(payload)

        # 5. Optionally send additional face logs in background
        if session_id:
            client.submit_face_logs(session_id, extra_face_logs)
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 3.0,
    ):
        self.base_url = (
            base_url
            or os.getenv("BACKEND_API_URL", "http://localhost:8080/api/v1")
        ).rstrip("/")
        self.timeout = timeout
        self._session = requests.Session()
        self._online = False
        logger.info("ServerClient initialized — server: %s", self.base_url)

    def _get(self, path: str) -> Optional[dict]:
        try:
            r = self._session.get(
                f"{self.base_url}{path}",
                timeout=self.timeout,
            )
            self._online = True
            r.raise_for_status()
            return r.json()
        except requests.Timeout:
            logger.error("GET %s timed out", path)
        except requests.ConnectionError:
            self._online = False
            logger.error("Server unreachable: GET %s", path)
        except requests.RequestException as e:
            logger.error("GET %s error: %s", path, e)
        return None

    def _post(self, path: str, data: dict) -> Optional[dict]:
        try:
            r = self._session.post(
                f"{self.base_url}{path}",
                json=data,
                timeout=self.timeout,
            )
            self._online = True
            r.raise_for_status()
            return r.json()
        except requests.Timeout:
            logger.error("POST %s timed out", path)
        except requests.ConnectionError:
            self._online = False
            logger.error("Server unreachable: POST %s", path)
        except requests.RequestException as e:
            logger.error("POST %s error: %s", path, e)
        return None

    @property
    def is_online(self) -> bool:
        return self._online

    def authenticate(self, uid: str) -> Optional[dict]:
        """
        GET /api/v1/robot/auth/{uid}
        Returns participant dict (includes 'id', 'name', 'height', etc.)
        """

        body = self._get(f"/robot/auth/{uid}")
        if body and body.get("status") == "success" and body.get("data"):
            data = body["data"]
            logger.info(
                "Authenticated: %s (id=%s, height=%.1f cm)",
                data.get("name"),
                data.get("id"),
                data.get("height", 0),
            )
            return data

        logger.warning("Authentication failed for UID %s", uid)
        return None
    def build_session_payload(
        self,
        participant_id: int,
        game_data: dict,
        expressions: list = None,
        datasets: list = None,
    ) -> dict:
        """
        Build the full payload dict for submit_game_session().

        Args:
            participant_id: from authenticate()["id"]
            game_data:      dict with keys like mode, level_reached,
                            total_time, cognitive_age, visuo_spatial_fit,
                            dexterity_score
            expressions:    list of {level, dominant_emotion, timestamp}
            datasets:       list of {camera_source, image_path}

        Returns:
            Ready-to-send payload dict.
        """

        return {
            "session": {
                "participant_id": participant_id,
                **game_data,
            },
            "expressions": expressions or [],
            "datasets": datasets or [],
        }
    def submit_game_session(self, data: dict) -> Optional[int]:
        """
        POST /api/v1/robot/sessions

        Accepts the payload from build_session_payload().
        Returns session_id (int) from the server, or None on failure.
        """
        body = self._post("/robot/sessions", data)
        if body and body.get("status") == "success" and body.get("data"):
            session_id = body["data"].get("session_id")
            logger.info("Session submitted — id=%s", session_id)
            return session_id

        logger.error("submit_game_session failed")
        return None

    def submit_face_logs(self, session_id: int, logs: list) -> None:
        """
        POST /api/v1/robot/logs/face

        Sends batch face expression logs recorded during gameplay.
        Runs in a background daemon thread so it never blocks the
        main game loop or UI.

        Args:
            session_id: ID of the game session (from submit_game_session).
            logs:       List of dicts with keys: level, dominant_emotion, timestamp.
        """
        if not logs:
            return

        def _send():
            body = self._post("/robot/logs/face", {
                "session_id": session_id,
                "logs": logs,
            })
            if body and body.get("status") == "success":
                count = body.get("data", {}).get("count", "?")
                logger.info(
                    "Face logs sent — session %d, count=%s",
                    session_id,
                    count,
                )
            else:
                logger.error("submit_face_logs failed for session %d", session_id)

        thread = threading.Thread(target=_send, daemon=True)
        thread.start()
