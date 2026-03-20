# tests/test_main.py
"""Tests for /solve payload parsing and bank account pre-config."""

from unittest.mock import patch, MagicMock

_mock_genai = MagicMock()
with patch("google.genai.Client", return_value=_mock_genai):
    from main import app, _preconfigure_bank_account

from fastapi.testclient import TestClient

client = TestClient(app)

PAYLOAD_A = {
    "prompt": "Opprett ansatt Ola Nordmann",
    "files": [],
    "tripletex_credentials": {"base_url": "https://t.dev/v2", "session_token": "tok-a"},
}

PAYLOAD_B = {
    "task_prompt": "Create employee Ola Nordmann",
    "attached_files": [],
    "tripletex_base_url": "https://t.dev/v2",
    "session_token": "tok-b",
}


class TestPayloadParsing:
    @patch("main.run_agent", return_value={"status": "completed"})
    @patch("main.process_files", return_value=[])
    @patch("main._preconfigure_bank_account")
    def test_format_a(self, *_):
        assert client.post("/solve", json=PAYLOAD_A).status_code == 200

    @patch("main.run_agent", return_value={"status": "completed"})
    @patch("main.process_files", return_value=[])
    @patch("main._preconfigure_bank_account")
    def test_format_b(self, *_):
        assert client.post("/solve", json=PAYLOAD_B).status_code == 200


class TestBankPreconfig:
    def test_configures_when_empty(self):
        mock_cls = MagicMock()
        mock_cls.return_value.get.return_value = {
            "success": True, "status_code": 200,
            "body": {"values": [{"id": 99, "number": 1920, "bankAccountNumber": None}]},
        }
        mock_cls.return_value.put.return_value = {"success": True, "status_code": 200, "body": {}}
        with patch("main.TripletexClient", mock_cls):
            _preconfigure_bank_account("https://t.dev/v2", "tok")
        mock_cls.return_value.put.assert_called_once()

    def test_skips_when_set(self):
        mock_cls = MagicMock()
        mock_cls.return_value.get.return_value = {
            "success": True, "status_code": 200,
            "body": {"values": [{"id": 99, "number": 1920, "bankAccountNumber": "86010517941"}]},
        }
        with patch("main.TripletexClient", mock_cls):
            _preconfigure_bank_account("https://t.dev/v2", "tok")
        mock_cls.return_value.put.assert_not_called()
