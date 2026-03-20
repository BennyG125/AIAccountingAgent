import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)


class TripletexClient:
    """Thin wrapper around the Tripletex v2 REST API."""

    def __init__(self, base_url: str, session_token: str):
        self.base_url = base_url.rstrip("/")
        self.session_token = session_token
        self.auth = ("0", session_token)

    def get(self, endpoint: str, params: dict | None = None) -> dict:
        url = f"{self.base_url}{endpoint}"
        logger.info(f"GET {url} params={params}")
        resp = requests.get(url, auth=self.auth, params=params, timeout=30)
        return self._parse_response(resp)

    def post(self, endpoint: str, body: dict | None = None) -> dict:
        url = f"{self.base_url}{endpoint}"
        logger.info(f"POST {url}")
        resp = requests.post(url, auth=self.auth, json=body, timeout=30)
        return self._parse_response(resp)

    def put(self, endpoint: str, body: dict | None = None, params: dict | None = None) -> dict:
        url = f"{self.base_url}{endpoint}"
        logger.info(f"PUT {url} params={params}")
        resp = requests.put(url, auth=self.auth, json=body, params=params, timeout=30)
        return self._parse_response(resp)

    def delete(self, endpoint: str) -> dict:
        url = f"{self.base_url}{endpoint}"
        logger.info(f"DELETE {url}")
        resp = requests.delete(url, auth=self.auth, timeout=30)
        return self._parse_response(resp)

    def _parse_response(self, resp: requests.Response) -> dict:
        try:
            body = resp.json()
        except Exception:
            body = {}

        success = 200 <= resp.status_code < 300
        result = {
            "status_code": resp.status_code,
            "success": success,
            "body": body,
        }

        if not success:
            error_msg = body.get("message", str(body))
            result["error"] = error_msg
            logger.warning(f"API error {resp.status_code}: {error_msg}")

        return result
