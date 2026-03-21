import json
from unittest.mock import patch, MagicMock
from tripletex_api import TripletexClient


def test_client_uses_basic_auth():
    """Client authenticates with username '0' and session token as password."""
    client = TripletexClient("https://example.com/v2", "test-token-123")
    assert client.auth == ("0", "test-token-123")


def test_client_get():
    """GET request includes auth and params."""
    client = TripletexClient("https://example.com/v2", "token")
    with patch("tripletex_api.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"values": [{"id": 1}]}
        mock_get.return_value = mock_response

        result = client.get("/employee", params={"fields": "id,firstName"})

        mock_get.assert_called_once_with(
            "https://example.com/v2/employee",
            auth=("0", "token"),
            params={"fields": "id,firstName"},
            timeout=30,
        )
        assert result["status_code"] == 200
        assert result["body"]["values"] == [{"id": 1}]


def test_client_post():
    """POST request includes auth and JSON body."""
    client = TripletexClient("https://example.com/v2", "token")
    with patch("tripletex_api.requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"value": {"id": 42}}
        mock_post.return_value = mock_response

        result = client.post("/employee", body={"firstName": "Ola"})

        mock_post.assert_called_once_with(
            "https://example.com/v2/employee",
            auth=("0", "token"),
            json={"firstName": "Ola"},
            params=None,
            timeout=30,
        )
        assert result["status_code"] == 201
        assert result["body"]["value"]["id"] == 42


def test_client_put():
    """PUT request includes auth and JSON body."""
    client = TripletexClient("https://example.com/v2", "token")
    with patch("tripletex_api.requests.put") as mock_put:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"value": {"id": 42}}
        mock_put.return_value = mock_response

        result = client.put("/employee/42", body={"firstName": "Kari"})

        mock_put.assert_called_once_with(
            "https://example.com/v2/employee/42",
            auth=("0", "token"),
            json={"firstName": "Kari"},
            params=None,
            timeout=30,
        )
        assert result["status_code"] == 200


def test_client_delete():
    """DELETE request uses ID in URL path."""
    client = TripletexClient("https://example.com/v2", "token")
    with patch("tripletex_api.requests.delete") as mock_delete:
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_response.json.return_value = {}
        mock_delete.return_value = mock_response

        result = client.delete("/travelExpense/99")

        mock_delete.assert_called_once_with(
            "https://example.com/v2/travelExpense/99",
            auth=("0", "token"),
            params=None,
            timeout=30,
        )
        assert result["status_code"] == 204


def test_client_handles_error_response():
    """Client returns error details without raising."""
    client = TripletexClient("https://example.com/v2", "token")
    with patch("tripletex_api.requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 422
        mock_response.json.return_value = {
            "status": 422,
            "message": "email is required",
        }
        mock_post.return_value = mock_response

        result = client.post("/employee", body={"firstName": "Ola"})

        assert result["status_code"] == 422
        assert result["success"] is False
        assert "email is required" in result["error"]
