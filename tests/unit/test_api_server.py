"""
Unit tests for the REST API server (interfaces/api_server.py).

Tests cover:
- Health endpoint (no auth required)
- Bearer token authentication (missing, malformed, wrong token, valid)
- /query endpoint: happy path, auth failure, orchestrator error
- /remember endpoint: note storage
- /describe endpoint: screen description
- /task endpoint: agentic task execution
- /profile endpoint: user preferences
- APIServer._get_context: per-request overrides
- Global error handler: internal exceptions become 500 with safe message

All external I/O is mocked:
- OS keychain (mock_keyring fixture from conftest.py)
- Orchestrator (MagicMock — no real Claude API calls)
- uvicorn (not started in unit tests; we test via FastAPI TestClient)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from blind_assistant.interfaces.api_server import APIServer
from blind_assistant.core.orchestrator import Response, UserContext


# ─────────────────────────────────────────────────────────────
# Helpers / fixtures
# ─────────────────────────────────────────────────────────────


def _make_orchestrator(response_text: str = "Here is your answer.") -> MagicMock:
    """Create a mock orchestrator that returns a canned response."""
    orc = MagicMock()
    orc.handle_message = AsyncMock(
        return_value=Response(
            text=response_text,
            spoken_text=None,
            follow_up_prompt=None,
            requires_confirmation=False,
            confirmation_action=None,
        )
    )
    orc.context_manager = MagicMock()
    orc.context_manager.load_user_context = AsyncMock(
        return_value=UserContext(
            user_id="local_user",
            session_id="default",
            verbosity="standard",
            speech_rate=1.0,
            output_mode="voice_text",
            braille_mode=False,
        )
    )
    return orc


class _PatchedClient:
    """
    Helper that keeps the keyring patch active for the lifetime of all requests.

    The API server imports get_credential lazily inside _authenticate(), so we must
    patch at the credentials module level and keep the patch alive during requests.
    """

    def __init__(self, app, token_in_keychain: str | None) -> None:
        self._token = token_in_keychain
        self._patcher = patch(
            "blind_assistant.security.credentials.get_credential",
            return_value=token_in_keychain,
        )
        self._patcher.start()
        self._client = TestClient(app, raise_server_exceptions=False)

    def __del__(self) -> None:
        try:
            self._patcher.stop()
        except RuntimeError:
            pass  # Already stopped

    # Proxy HTTP verbs to the inner TestClient
    def get(self, *args, **kwargs):
        return self._client.get(*args, **kwargs)

    def post(self, *args, **kwargs):
        return self._client.post(*args, **kwargs)


def _make_server(
    orchestrator=None,
    token_in_keychain: str | None = "test-token-123",
    auth_disabled: bool = False,
) -> tuple[APIServer, _PatchedClient]:
    """
    Build an APIServer and return a patched TestClient for it.

    The keyring mock stays active for all requests made through the returned client.
    """
    if orchestrator is None:
        orchestrator = _make_orchestrator()

    config = {"debug": True, "api_auth_disabled": auth_disabled}
    server = APIServer(orchestrator, config)
    app = server._build_app()

    return server, _PatchedClient(app, token_in_keychain)


# ─────────────────────────────────────────────────────────────
# Health endpoint (no auth)
# ─────────────────────────────────────────────────────────────


def test_health_returns_ok_without_auth():
    """GET /health requires no Authorization header and returns 200."""
    _, client = _make_server()
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_health_returns_version():
    """GET /health includes version field."""
    _, client = _make_server()
    resp = client.get("/health")
    assert "version" in resp.json()


# ─────────────────────────────────────────────────────────────
# Authentication
# ─────────────────────────────────────────────────────────────


def test_query_missing_auth_returns_401():
    """POST /query without Authorization header returns 401."""
    _, client = _make_server()
    resp = client.post("/query", json={"message": "hello"})
    assert resp.status_code == 401


def test_query_malformed_auth_returns_401():
    """POST /query with malformed Authorization returns 401."""
    _, client = _make_server()
    resp = client.post(
        "/query",
        json={"message": "hello"},
        headers={"Authorization": "NotBearer xyz"},
    )
    assert resp.status_code == 401


def test_query_wrong_token_returns_401():
    """POST /query with wrong token returns 401."""
    _, client = _make_server(token_in_keychain="correct-token")
    resp = client.post(
        "/query",
        json={"message": "hello"},
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert resp.status_code == 401


def test_query_no_token_configured_returns_401():
    """POST /query when no token is stored in keychain returns 401."""
    _, client = _make_server(token_in_keychain=None)
    resp = client.post(
        "/query",
        json={"message": "hello"},
        headers={"Authorization": "Bearer anything"},
    )
    assert resp.status_code == 401


def test_query_auth_disabled_dev_mode_allows_any_token():
    """With api_auth_disabled=True, any Bearer token is accepted (dev only)."""
    _, client = _make_server(token_in_keychain=None, auth_disabled=True)
    resp = client.post(
        "/query",
        json={"message": "hello"},
        headers={"Authorization": "Bearer dev-token"},
    )
    assert resp.status_code == 200


def test_query_valid_token_returns_200():
    """POST /query with correct Bearer token returns 200."""
    _, client = _make_server(token_in_keychain="test-token-123")
    resp = client.post(
        "/query",
        json={"message": "hello"},
        headers={"Authorization": "Bearer test-token-123"},
    )
    assert resp.status_code == 200


# ─────────────────────────────────────────────────────────────
# /query endpoint
# ─────────────────────────────────────────────────────────────


VALID_HEADERS = {"Authorization": "Bearer test-token-123"}


def test_query_returns_text_response():
    """POST /query returns the orchestrator's response text."""
    orc = _make_orchestrator("Here is your answer.")
    _, client = _make_server(orchestrator=orc)
    resp = client.post("/query", json={"message": "What time is it?"}, headers=VALID_HEADERS)
    assert resp.status_code == 200
    assert resp.json()["text"] == "Here is your answer."


def test_query_returns_session_id():
    """POST /query echoes the session_id from the request."""
    _, client = _make_server()
    resp = client.post(
        "/query",
        json={"message": "hello", "session_id": "my-session-abc"},
        headers=VALID_HEADERS,
    )
    assert resp.json()["session_id"] == "my-session-abc"


def test_query_passes_message_to_orchestrator():
    """POST /query calls orchestrator.handle_message with the user's message."""
    orc = _make_orchestrator()
    _, client = _make_server(orchestrator=orc)
    client.post("/query", json={"message": "Order me pizza"}, headers=VALID_HEADERS)
    call_args = orc.handle_message.call_args
    assert call_args.kwargs["text"] == "Order me pizza"


def test_query_applies_speech_rate_override():
    """POST /query applies speech_rate from request body to user context."""
    orc = _make_orchestrator()
    _, client = _make_server(orchestrator=orc)
    client.post(
        "/query",
        json={"message": "hello", "speech_rate": 0.75},
        headers=VALID_HEADERS,
    )
    # The context passed to handle_message should have speech_rate=0.75
    call_args = orc.handle_message.call_args
    assert call_args.kwargs["context"].speech_rate == 0.75


def test_query_applies_braille_mode_override():
    """POST /query with braille_mode=true sets context.braille_mode."""
    orc = _make_orchestrator()
    _, client = _make_server(orchestrator=orc)
    client.post(
        "/query",
        json={"message": "hello", "braille_mode": True},
        headers=VALID_HEADERS,
    )
    call_args = orc.handle_message.call_args
    assert call_args.kwargs["context"].braille_mode is True


def test_query_orchestrator_exception_returns_500():
    """POST /query returns 500 if the orchestrator raises an unexpected exception."""
    orc = MagicMock()
    orc.handle_message = AsyncMock(side_effect=RuntimeError("unexpected crash"))
    orc.context_manager = MagicMock()
    orc.context_manager.load_user_context = AsyncMock(
        return_value=UserContext(user_id="u", session_id="s")
    )
    _, client = _make_server(orchestrator=orc)
    resp = client.post("/query", json={"message": "hello"}, headers=VALID_HEADERS)
    assert resp.status_code == 500
    # Error message must not expose internal details
    assert "unexpected crash" not in resp.json().get("detail", "")


def test_query_500_message_is_safe():
    """Global error handler returns a user-friendly message, not a stack trace."""
    orc = MagicMock()
    orc.handle_message = AsyncMock(side_effect=ValueError("internal secret"))
    orc.context_manager = MagicMock()
    orc.context_manager.load_user_context = AsyncMock(
        return_value=UserContext(user_id="u", session_id="s")
    )
    _, client = _make_server(orchestrator=orc)
    resp = client.post("/query", json={"message": "hello"}, headers=VALID_HEADERS)
    body = resp.json()
    assert "internal secret" not in str(body)
    assert "detail" in body


# ─────────────────────────────────────────────────────────────
# /remember endpoint
# ─────────────────────────────────────────────────────────────


def test_remember_routes_to_orchestrator_with_remember_prefix():
    """POST /remember prepends 'Remember:' to route through the add_note handler."""
    orc = _make_orchestrator("Note saved.")
    _, client = _make_server(orchestrator=orc)
    client.post(
        "/remember",
        json={"content": "Buy milk on Thursday"},
        headers=VALID_HEADERS,
    )
    call_text = orc.handle_message.call_args.kwargs["text"]
    assert call_text.startswith("Remember:")
    assert "Buy milk on Thursday" in call_text


def test_remember_returns_confirmation_text():
    """POST /remember returns the orchestrator's confirmation text."""
    orc = _make_orchestrator("Note saved.")
    _, client = _make_server(orchestrator=orc)
    resp = client.post(
        "/remember",
        json={"content": "Buy milk on Thursday"},
        headers=VALID_HEADERS,
    )
    assert resp.json()["text"] == "Note saved."


# ─────────────────────────────────────────────────────────────
# /describe endpoint
# ─────────────────────────────────────────────────────────────


def test_describe_sends_screen_query_to_orchestrator():
    """POST /describe routes to the screen description handler via orchestrator."""
    orc = _make_orchestrator("The screen shows a browser with Google.com open.")
    _, client = _make_server(orchestrator=orc)
    client.post("/describe", json={}, headers=VALID_HEADERS)
    call_text = orc.handle_message.call_args.kwargs["text"]
    assert "screen" in call_text.lower()


def test_describe_returns_description_text():
    """POST /describe returns the screen description."""
    orc = _make_orchestrator("The screen shows a browser with Google.com open.")
    _, client = _make_server(orchestrator=orc)
    resp = client.post("/describe", json={}, headers=VALID_HEADERS)
    assert "browser" in resp.json()["text"].lower()


# ─────────────────────────────────────────────────────────────
# /task endpoint
# ─────────────────────────────────────────────────────────────


def test_task_routes_task_description_to_orchestrator():
    """POST /task sends the task description to the orchestrator."""
    orc = _make_orchestrator("I've started the food order.")
    _, client = _make_server(orchestrator=orc)
    client.post(
        "/task",
        json={"task_description": "Order me a pizza from DoorDash"},
        headers=VALID_HEADERS,
    )
    assert "pizza" in orc.handle_message.call_args.kwargs["text"].lower()


def test_task_completed_true_when_no_confirmation_required():
    """POST /task returns completed=True when no confirmation is needed."""
    orc = _make_orchestrator("Done.")
    _, client = _make_server(orchestrator=orc)
    resp = client.post(
        "/task",
        json={"task_description": "Play some music"},
        headers=VALID_HEADERS,
    )
    assert resp.json()["completed"] is True


def test_task_completed_false_when_confirmation_required():
    """POST /task returns completed=False when the response requires confirmation."""
    orc = MagicMock()
    orc.handle_message = AsyncMock(
        return_value=Response(
            text="Ready to order. Confirm?",
            requires_confirmation=True,
            confirmation_action="Shall I place the order for $18.50?",
        )
    )
    orc.context_manager = MagicMock()
    orc.context_manager.load_user_context = AsyncMock(
        return_value=UserContext(user_id="u", session_id="s")
    )
    _, client = _make_server(orchestrator=orc)
    resp = client.post(
        "/task",
        json={"task_description": "Order pizza"},
        headers=VALID_HEADERS,
    )
    data = resp.json()
    assert data["completed"] is False
    assert data["requires_confirmation"] is True
    assert "18.50" in data["confirmation_prompt"]


# ─────────────────────────────────────────────────────────────
# /profile endpoint
# ─────────────────────────────────────────────────────────────


def test_profile_returns_user_preferences():
    """GET /profile returns user_id, verbosity, speech_rate, output_mode, braille_mode."""
    _, client = _make_server()
    resp = client.get("/profile", headers=VALID_HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert "user_id" in data
    assert "verbosity" in data
    assert "speech_rate" in data
    assert "output_mode" in data
    assert "braille_mode" in data


def test_profile_requires_auth():
    """GET /profile returns 401 without an Authorization header."""
    _, client = _make_server()
    resp = client.get("/profile")
    assert resp.status_code == 401


# ─────────────────────────────────────────────────────────────
# APIServer construction
# ─────────────────────────────────────────────────────────────


def test_api_server_default_port():
    """APIServer defaults to port 8000 when not specified in config."""
    orc = _make_orchestrator()
    server = APIServer(orc, config={})
    assert server._port == 8000


def test_api_server_custom_port():
    """APIServer uses the port from config."""
    orc = _make_orchestrator()
    server = APIServer(orc, config={"api_server_port": 9000})
    assert server._port == 9000


def test_api_server_builds_app_without_docs_in_production():
    """In production (debug=False) the /docs route is disabled."""
    orc = _make_orchestrator()
    server = APIServer(orc, config={"debug": False})
    app = server._build_app()
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/docs")
    assert resp.status_code == 404


def test_api_server_enables_docs_in_debug_mode():
    """In debug mode the /docs route is available."""
    orc = _make_orchestrator()
    server = APIServer(orc, config={"debug": True})
    app = server._build_app()
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/docs")
    assert resp.status_code == 200
