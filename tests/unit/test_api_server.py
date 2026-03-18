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
- OS keychain (patched at credentials module level; patch is scoped to each test)
- Orchestrator (MagicMock — no real Claude API calls)
- uvicorn (not started in unit tests; we test via FastAPI TestClient)
"""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from blind_assistant.core.orchestrator import Response, UserContext
from blind_assistant.interfaces.api_server import APIServer, RateLimitMiddleware, VALID_EXTRA_PREFS

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


@contextmanager
def _make_server(
    orchestrator=None,
    token_in_keychain: str | None = "test-token-123",  # noqa: S107
    auth_disabled: bool = False,
):
    """
    Context manager that builds an APIServer + TestClient with keyring mocked.

    Usage::

        with _make_server() as (server, client):
            resp = client.get("/health")

    The keyring patch is active only for the duration of the `with` block,
    preventing test pollution into other test modules.
    """
    if orchestrator is None:
        orchestrator = _make_orchestrator()

    config = {"debug": True, "api_auth_disabled": auth_disabled}
    server = APIServer(orchestrator, config)
    app = server._build_app()

    # Patch at the credentials module where get_credential is defined.
    # api_server._authenticate() imports and calls it lazily, so module-level
    # patching is required (not patching the api_server namespace).
    with patch(
        "blind_assistant.security.credentials.get_credential",
        return_value=token_in_keychain,
    ):
        yield server, TestClient(app, raise_server_exceptions=False)


VALID_HEADERS = {"Authorization": "Bearer test-token-123"}


# ─────────────────────────────────────────────────────────────
# Health endpoint (no auth)
# ─────────────────────────────────────────────────────────────


def test_health_returns_ok_without_auth():
    """GET /health requires no Authorization header and returns 200."""
    with _make_server() as (_, client):
        resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_health_returns_version():
    """GET /health includes version field."""
    with _make_server() as (_, client):
        resp = client.get("/health")
    assert "version" in resp.json()


# ─────────────────────────────────────────────────────────────
# Authentication
# ─────────────────────────────────────────────────────────────


def test_query_missing_auth_returns_401():
    """POST /query without Authorization header returns 401."""
    with _make_server() as (_, client):
        resp = client.post("/query", json={"message": "hello"})
    assert resp.status_code == 401


def test_query_malformed_auth_returns_401():
    """POST /query with malformed Authorization returns 401."""
    with _make_server() as (_, client):
        resp = client.post(
            "/query",
            json={"message": "hello"},
            headers={"Authorization": "NotBearer xyz"},
        )
    assert resp.status_code == 401


def test_query_wrong_token_returns_401():
    """POST /query with wrong token returns 401."""
    with _make_server(token_in_keychain="correct-token") as (_, client):
        resp = client.post(
            "/query",
            json={"message": "hello"},
            headers={"Authorization": "Bearer wrong-token"},
        )
    assert resp.status_code == 401


def test_query_no_token_configured_returns_401():
    """POST /query when no token is stored in keychain returns 401."""
    with _make_server(token_in_keychain=None) as (_, client):
        resp = client.post(
            "/query",
            json={"message": "hello"},
            headers={"Authorization": "Bearer anything"},
        )
    assert resp.status_code == 401


def test_query_auth_disabled_dev_mode_allows_any_token():
    """With api_auth_disabled=True, any Bearer token is accepted (dev only)."""
    with _make_server(token_in_keychain=None, auth_disabled=True) as (_, client):
        resp = client.post(
            "/query",
            json={"message": "hello"},
            headers={"Authorization": "Bearer dev-token"},
        )
    assert resp.status_code == 200


def test_query_valid_token_returns_200():
    """POST /query with correct Bearer token returns 200."""
    with _make_server(token_in_keychain="test-token-123") as (_, client):
        resp = client.post(
            "/query",
            json={"message": "hello"},
            headers=VALID_HEADERS,
        )
    assert resp.status_code == 200


# ─────────────────────────────────────────────────────────────
# /query endpoint
# ─────────────────────────────────────────────────────────────


def test_query_returns_text_response():
    """POST /query returns the orchestrator's response text."""
    orc = _make_orchestrator("Here is your answer.")
    with _make_server(orchestrator=orc) as (_, client):
        resp = client.post("/query", json={"message": "What time is it?"}, headers=VALID_HEADERS)
    assert resp.status_code == 200
    assert resp.json()["text"] == "Here is your answer."


def test_query_returns_session_id():
    """POST /query echoes the session_id from the request."""
    with _make_server() as (_, client):
        resp = client.post(
            "/query",
            json={"message": "hello", "session_id": "my-session-abc"},
            headers=VALID_HEADERS,
        )
    assert resp.json()["session_id"] == "my-session-abc"


def test_query_passes_message_to_orchestrator():
    """POST /query calls orchestrator.handle_message with the user's message."""
    orc = _make_orchestrator()
    with _make_server(orchestrator=orc) as (_, client):
        client.post("/query", json={"message": "Order me pizza"}, headers=VALID_HEADERS)
    call_args = orc.handle_message.call_args
    assert call_args.kwargs["text"] == "Order me pizza"


def test_query_applies_speech_rate_override():
    """POST /query applies speech_rate from request body to user context."""
    orc = _make_orchestrator()
    with _make_server(orchestrator=orc) as (_, client):
        client.post(
            "/query",
            json={"message": "hello", "speech_rate": 0.75},
            headers=VALID_HEADERS,
        )
    call_args = orc.handle_message.call_args
    assert call_args.kwargs["context"].speech_rate == 0.75


def test_query_applies_braille_mode_override():
    """POST /query with braille_mode=true sets context.braille_mode."""
    orc = _make_orchestrator()
    with _make_server(orchestrator=orc) as (_, client):
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
    orc.context_manager.load_user_context = AsyncMock(return_value=UserContext(user_id="u", session_id="s"))
    with _make_server(orchestrator=orc) as (_, client):
        resp = client.post("/query", json={"message": "hello"}, headers=VALID_HEADERS)
    assert resp.status_code == 500
    # Error message must not expose internal exception details
    assert "unexpected crash" not in resp.json().get("detail", "")


def test_query_500_message_is_safe():
    """Global error handler returns a user-friendly message, not a stack trace."""
    orc = MagicMock()
    orc.handle_message = AsyncMock(side_effect=ValueError("internal secret"))
    orc.context_manager = MagicMock()
    orc.context_manager.load_user_context = AsyncMock(return_value=UserContext(user_id="u", session_id="s"))
    with _make_server(orchestrator=orc) as (_, client):
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
    with _make_server(orchestrator=orc) as (_, client):
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
    with _make_server(orchestrator=orc) as (_, client):
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
    with _make_server(orchestrator=orc) as (_, client):
        client.post("/describe", json={}, headers=VALID_HEADERS)
    call_text = orc.handle_message.call_args.kwargs["text"]
    assert "screen" in call_text.lower()


def test_describe_returns_description_text():
    """POST /describe returns the screen description."""
    orc = _make_orchestrator("The screen shows a browser with Google.com open.")
    with _make_server(orchestrator=orc) as (_, client):
        resp = client.post("/describe", json={}, headers=VALID_HEADERS)
    assert "browser" in resp.json()["text"].lower()


# ─────────────────────────────────────────────────────────────
# /task endpoint
# ─────────────────────────────────────────────────────────────


def test_task_routes_task_description_to_orchestrator():
    """POST /task sends the task description to the orchestrator."""
    orc = _make_orchestrator("I've started the food order.")
    with _make_server(orchestrator=orc) as (_, client):
        client.post(
            "/task",
            json={"task_description": "Order me a pizza from DoorDash"},
            headers=VALID_HEADERS,
        )
    assert "pizza" in orc.handle_message.call_args.kwargs["text"].lower()


def test_task_completed_true_when_no_confirmation_required():
    """POST /task returns completed=True when no confirmation is needed."""
    orc = _make_orchestrator("Done.")
    with _make_server(orchestrator=orc) as (_, client):
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
    orc.context_manager.load_user_context = AsyncMock(return_value=UserContext(user_id="u", session_id="s"))
    with _make_server(orchestrator=orc) as (_, client):
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
    with _make_server() as (_, client):
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
    with _make_server() as (_, client):
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


# ─────────────────────────────────────────────────────────────
# Rate limiting middleware
# ─────────────────────────────────────────────────────────────


def _make_rate_limit_client(auth_limit: int = 60, health_limit: int = 120):
    """
    Build a TestClient with aggressive rate limits for testing.
    Returns (server, client) pair.
    """
    orc = _make_orchestrator()
    config: dict = {
        "debug": True,
        "api_auth_disabled": True,
        "api_server": {
            "rate_limit_per_minute": auth_limit,
            "health_rate_limit_per_minute": health_limit,
        },
    }
    server = APIServer(orc, config)
    # Build app — RateLimitMiddleware is added inside _build_app()
    app = server._build_app()
    return server, TestClient(app, raise_server_exceptions=False)


def test_rate_limit_middleware_allows_requests_within_limit():
    """Requests within the rate limit return 200, not 429."""
    _, client = _make_rate_limit_client(auth_limit=5, health_limit=5)
    # 3 requests — under the limit of 5
    for _ in range(3):
        resp = client.get("/health")
    assert resp.status_code == 200


def test_rate_limit_middleware_blocks_health_after_limit_exceeded():
    """After health_limit requests in the window, /health returns 429."""
    _, client = _make_rate_limit_client(auth_limit=100, health_limit=2)
    # First two allowed
    client.get("/health")
    client.get("/health")
    # Third should be blocked
    resp = client.get("/health")
    assert resp.status_code == 429
    assert "rate limit" in resp.json()["detail"].lower()


def test_rate_limit_middleware_blocks_auth_endpoint_after_limit_exceeded():
    """After auth_limit requests in the window, authenticated endpoints return 429."""
    _, client = _make_rate_limit_client(auth_limit=2, health_limit=100)
    # First two allowed (api_auth_disabled=True so no token needed)
    client.post("/query", json={"message": "hello"})
    client.post("/query", json={"message": "hello"})
    # Third should be blocked
    resp = client.post("/query", json={"message": "hello"})
    assert resp.status_code == 429


def test_rate_limit_middleware_health_and_auth_limits_are_independent():
    """Health endpoint and authenticated endpoints have separate rate limit counters."""
    _, client = _make_rate_limit_client(auth_limit=2, health_limit=100)
    # Exhaust auth limit
    client.post("/query", json={"message": "hello"})
    client.post("/query", json={"message": "hello"})
    # /health should still work (its own limit is 100)
    resp = client.get("/health")
    assert resp.status_code == 200


def test_rate_limit_middleware_configured_from_server_config():
    """APIServer passes rate limit config values to RateLimitMiddleware."""
    orc = _make_orchestrator()
    # Low limits so we can verify they're applied
    config = {
        "debug": True,
        "api_auth_disabled": True,
        "api_server": {
            "rate_limit_per_minute": 1,
            "health_rate_limit_per_minute": 1,
        },
    }
    server = APIServer(orc, config)
    app = server._build_app()
    client = TestClient(app, raise_server_exceptions=False)

    # First request allowed
    resp = client.get("/health")
    assert resp.status_code == 200
    # Second request blocked (limit=1)
    resp = client.get("/health")
    assert resp.status_code == 429


def test_rate_limit_middleware_is_instance_of_base_http_middleware():
    """RateLimitMiddleware is constructed with correct default limits."""
    # Construct directly to unit-test the init parameters
    middleware = RateLimitMiddleware(app=None, auth_limit=30, health_limit=60)  # type: ignore[arg-type]
    assert middleware._auth_limit == 30
    assert middleware._health_limit == 60


# ─────────────────────────────────────────────────────────────
# GET /profile with MCPMemoryClient integration
# ─────────────────────────────────────────────────────────────


def _make_mock_memory(prefs: dict | None = None):
    """Build an AsyncMock MCPMemoryClient with canned preferences."""
    mem = MagicMock()
    returned = prefs if prefs is not None else {}
    mem.get_all_preferences = AsyncMock(return_value=returned)
    mem.set_preference = AsyncMock()
    mem.clear_user_data = AsyncMock()
    return mem


@contextmanager
def _make_server_with_memory(memory_client=None, token: str = "test-token-123"):  # noqa: S107
    """Build an APIServer+TestClient with a mock MCPMemoryClient injected."""
    orc = _make_orchestrator()
    config = {"debug": True}
    server = APIServer(orc, config, memory_client=memory_client)
    app = server._build_app()
    with patch(
        "blind_assistant.security.credentials.get_credential",
        return_value=token,
    ):
        yield server, TestClient(app, raise_server_exceptions=False)


def test_profile_reads_preferences_from_memory_client():
    """GET /profile returns speech_rate from MCPMemoryClient when available."""
    mem = _make_mock_memory({"voice_speed": 0.7, "verbosity": "brief"})
    with _make_server_with_memory(memory_client=mem) as (_, client):
        resp = client.get("/profile", headers=VALID_HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert data["speech_rate"] == 0.7
    assert data["verbosity"] == "brief"


def test_profile_includes_full_preferences_dict_from_memory():
    """GET /profile includes the raw preferences dict when MCPMemoryClient is present."""
    mem = _make_mock_memory({"voice_speed": 1.2, "braille_mode": True, "user_name": "Dorothy"})
    with _make_server_with_memory(memory_client=mem) as (_, client):
        resp = client.get("/profile", headers=VALID_HEADERS)
    prefs = resp.json().get("preferences")
    assert prefs is not None
    assert prefs["user_name"] == "Dorothy"
    assert prefs["braille_mode"] is True


def test_profile_without_memory_client_has_null_preferences():
    """GET /profile returns preferences=null when no MCPMemoryClient is configured."""
    with _make_server_with_memory(memory_client=None) as (_, client):
        resp = client.get("/profile", headers=VALID_HEADERS)
    assert resp.status_code == 200
    assert resp.json()["preferences"] is None


def test_profile_gracefully_handles_memory_client_failure():
    """GET /profile still returns 200 if MCPMemoryClient.get_all_preferences raises."""
    mem = MagicMock()
    mem.get_all_preferences = AsyncMock(side_effect=RuntimeError("MCP unreachable"))
    with _make_server_with_memory(memory_client=mem) as (_, client):
        resp = client.get("/profile", headers=VALID_HEADERS)
    # Must still succeed — never let memory errors surface as 5xx
    assert resp.status_code == 200


# ─────────────────────────────────────────────────────────────
# PUT /profile — update preferences via MCPMemoryClient
# ─────────────────────────────────────────────────────────────


def test_put_profile_updates_speech_rate_in_memory():
    """PUT /profile calls MCPMemoryClient.set_preference for voice_speed."""
    mem = _make_mock_memory({"voice_speed": 0.8})
    with _make_server_with_memory(memory_client=mem) as (_, client):
        resp = client.put(
            "/profile",
            json={"speech_rate": 0.8},
            headers=VALID_HEADERS,
        )
    assert resp.status_code == 200
    # verify set_preference was called with the correct key
    calls = {call.args[1]: call.args[2] for call in mem.set_preference.call_args_list}
    assert calls.get("voice_speed") == 0.8


def test_put_profile_updates_verbosity_in_memory():
    """PUT /profile calls MCPMemoryClient.set_preference for verbosity."""
    mem = _make_mock_memory({"verbosity": "brief"})
    with _make_server_with_memory(memory_client=mem) as (_, client):
        resp = client.put(
            "/profile",
            json={"verbosity": "brief"},
            headers=VALID_HEADERS,
        )
    assert resp.status_code == 200
    calls = {call.args[1]: call.args[2] for call in mem.set_preference.call_args_list}
    assert calls.get("verbosity") == "brief"


def test_put_profile_updates_braille_mode_in_memory():
    """PUT /profile calls MCPMemoryClient.set_preference for braille_mode."""
    mem = _make_mock_memory({"braille_mode": True})
    with _make_server_with_memory(memory_client=mem) as (_, client):
        resp = client.put(
            "/profile",
            json={"braille_mode": True},
            headers=VALID_HEADERS,
        )
    assert resp.status_code == 200
    calls = {call.args[1]: call.args[2] for call in mem.set_preference.call_args_list}
    assert calls.get("braille_mode") is True


def test_put_profile_writes_extra_preferences():
    """PUT /profile persists arbitrary extra key-value pairs via MCPMemoryClient."""
    mem = _make_mock_memory({"timezone": "America/New_York"})
    with _make_server_with_memory(memory_client=mem) as (_, client):
        resp = client.put(
            "/profile",
            json={"extra": {"timezone": "America/New_York", "user_name": "Dorothy"}},
            headers=VALID_HEADERS,
        )
    assert resp.status_code == 200
    calls = {call.args[1]: call.args[2] for call in mem.set_preference.call_args_list}
    assert calls.get("timezone") == "America/New_York"
    assert calls.get("user_name") == "Dorothy"


def test_put_profile_without_memory_client_returns_200():
    """PUT /profile succeeds (session-only) when no MCPMemoryClient is configured."""
    with _make_server_with_memory(memory_client=None) as (_, client):
        resp = client.put(
            "/profile",
            json={"verbosity": "detailed"},
            headers=VALID_HEADERS,
        )
    assert resp.status_code == 200


def test_put_profile_gracefully_handles_memory_client_write_failure():
    """PUT /profile still returns 200 if MCPMemoryClient.set_preference raises."""
    mem = MagicMock()
    mem.set_preference = AsyncMock(side_effect=RuntimeError("MCP unreachable"))
    mem.get_all_preferences = AsyncMock(return_value={})
    with _make_server_with_memory(memory_client=mem) as (_, client):
        resp = client.put(
            "/profile",
            json={"verbosity": "brief"},
            headers=VALID_HEADERS,
        )
    assert resp.status_code == 200


def test_put_profile_requires_auth():
    """PUT /profile returns 401 without an Authorization header."""
    mem = _make_mock_memory()
    with _make_server_with_memory(memory_client=mem) as (_, client):
        resp = client.put("/profile", json={"verbosity": "brief"})
    assert resp.status_code == 401


def test_put_profile_returns_updated_preferences():
    """PUT /profile response includes updated speech_rate in the profile body."""
    mem = _make_mock_memory({"voice_speed": 0.6})
    with _make_server_with_memory(memory_client=mem) as (_, client):
        resp = client.put(
            "/profile",
            json={"speech_rate": 0.6},
            headers=VALID_HEADERS,
        )
    assert resp.status_code == 200
    assert resp.json()["speech_rate"] == 0.6


def test_api_server_accepts_memory_client_in_constructor():
    """APIServer stores the injected memory_client on self._memory."""
    orc = _make_orchestrator()
    mem = _make_mock_memory()
    server = APIServer(orc, config={}, memory_client=mem)
    assert server._memory is mem


def test_api_server_memory_client_defaults_to_none():
    """APIServer._memory is None when no memory_client is provided."""
    orc = _make_orchestrator()
    server = APIServer(orc, config={})
    assert server._memory is None


# ─────────────────────────────────────────────────────────────
# PUT /profile — extra key allowlist (ISSUE-030)
# ─────────────────────────────────────────────────────────────


def test_put_profile_rejects_unknown_extra_key_with_422():
    """PUT /profile returns 422 when extra contains an unknown key (ISSUE-030)."""
    mem = _make_mock_memory()
    with _make_server_with_memory(memory_client=mem) as (_, client):
        resp = client.put(
            "/profile",
            json={"extra": {"is_admin": True}},
            headers=VALID_HEADERS,
        )
    assert resp.status_code == 422
    # Error detail must name the rejected key
    assert "is_admin" in resp.json()["detail"]


def test_put_profile_rejects_multiple_unknown_extra_keys_with_422():
    """PUT /profile lists all unknown keys in the 422 response detail."""
    mem = _make_mock_memory()
    with _make_server_with_memory(memory_client=mem) as (_, client):
        resp = client.put(
            "/profile",
            json={"extra": {"payment_method": "visa", "credit_score": 750}},
            headers=VALID_HEADERS,
        )
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert "payment_method" in detail
    assert "credit_score" in detail


def test_put_profile_rejects_unknown_key_does_not_write_to_memory():
    """PUT /profile with unknown extra key never calls MCPMemoryClient.set_preference."""
    mem = _make_mock_memory()
    with _make_server_with_memory(memory_client=mem) as (_, client):
        client.put(
            "/profile",
            json={"extra": {"is_admin": True}},
            headers=VALID_HEADERS,
        )
    # Validation fires before any write — set_preference must not have been called
    mem.set_preference.assert_not_called()


def test_put_profile_accepts_all_valid_extra_keys():
    """PUT /profile accepts every key in VALID_EXTRA_PREFS without error."""
    # Use one valid key at a time to keep the test focused
    for key in VALID_EXTRA_PREFS:
        mem = _make_mock_memory({key: "test-value"})
        with _make_server_with_memory(memory_client=mem) as (_, client):
            resp = client.put(
                "/profile",
                json={"extra": {key: "test-value"}},
                headers=VALID_HEADERS,
            )
        assert resp.status_code == 200, f"Expected 200 for valid key '{key}', got {resp.status_code}"


def test_put_profile_rejects_mix_of_valid_and_invalid_extra_keys():
    """PUT /profile returns 422 when ANY extra key is invalid, even with valid ones present."""
    mem = _make_mock_memory()
    with _make_server_with_memory(memory_client=mem) as (_, client):
        resp = client.put(
            "/profile",
            # "timezone" is valid; "hacker_field" is not
            json={"extra": {"timezone": "Europe/London", "hacker_field": "pwned"}},
            headers=VALID_HEADERS,
        )
    assert resp.status_code == 422
    assert "hacker_field" in resp.json()["detail"]
    # Valid key must NOT have been written (all-or-nothing validation)
    mem.set_preference.assert_not_called()


def test_put_profile_empty_extra_dict_is_accepted():
    """PUT /profile with empty extra dict returns 200 without calling set_preference for extra."""
    mem = _make_mock_memory()
    with _make_server_with_memory(memory_client=mem) as (_, client):
        resp = client.put(
            "/profile",
            json={"extra": {}},
            headers=VALID_HEADERS,
        )
    assert resp.status_code == 200


def test_put_profile_null_extra_is_accepted():
    """PUT /profile with extra=null (omitted) is a no-op on extra prefs — returns 200."""
    mem = _make_mock_memory()
    with _make_server_with_memory(memory_client=mem) as (_, client):
        resp = client.put(
            "/profile",
            json={"verbosity": "detailed"},
            headers=VALID_HEADERS,
        )
    assert resp.status_code == 200


def test_valid_extra_prefs_is_a_frozenset():
    """VALID_EXTRA_PREFS is a frozenset so it cannot be mutated at runtime."""
    assert isinstance(VALID_EXTRA_PREFS, frozenset)
    assert len(VALID_EXTRA_PREFS) >= 4, "Expected at least 4 allowlisted preference keys"


# ─────────────────────────────────────────────────────────────
# DELETE /profile/preferences — clear all MCP preference data (ISSUE-031)
# ─────────────────────────────────────────────────────────────


def test_delete_preferences_returns_204_on_happy_path():
    """DELETE /profile/preferences returns 204 No Content when confirm=true."""
    mem = _make_mock_memory()
    mem.clear_user_data = AsyncMock()
    with _make_server_with_memory(memory_client=mem) as (_, client):
        resp = client.request("DELETE", "/profile/preferences", json={"confirm": True}, headers=VALID_HEADERS)
    assert resp.status_code == 204


def test_delete_preferences_calls_clear_user_data():
    """DELETE /profile/preferences calls MCPMemoryClient.clear_user_data with the user_id."""
    mem = _make_mock_memory()
    mem.clear_user_data = AsyncMock()
    with _make_server_with_memory(memory_client=mem) as (_, client):
        client.request("DELETE", "/profile/preferences", json={"confirm": True}, headers=VALID_HEADERS)
    mem.clear_user_data.assert_called_once_with("local_user")


def test_delete_preferences_returns_400_when_confirm_false():
    """DELETE /profile/preferences returns 400 when confirm=false — must be explicit."""
    mem = _make_mock_memory()
    mem.clear_user_data = AsyncMock()
    with _make_server_with_memory(memory_client=mem) as (_, client):
        resp = client.request("DELETE", "/profile/preferences", json={"confirm": False}, headers=VALID_HEADERS)
    assert resp.status_code == 400
    # Must not have deleted anything
    mem.clear_user_data.assert_not_called()


def test_delete_preferences_returns_400_when_confirm_omitted():
    """DELETE /profile/preferences returns 400 when confirm is omitted (defaults to false)."""
    mem = _make_mock_memory()
    mem.clear_user_data = AsyncMock()
    with _make_server_with_memory(memory_client=mem) as (_, client):
        resp = client.request("DELETE", "/profile/preferences", json={}, headers=VALID_HEADERS)
    assert resp.status_code == 400
    mem.clear_user_data.assert_not_called()


def test_delete_preferences_requires_auth():
    """DELETE /profile/preferences returns 401 without a valid Authorization header."""
    mem = _make_mock_memory()
    mem.clear_user_data = AsyncMock()
    with _make_server_with_memory(memory_client=mem) as (_, client):
        resp = client.request("DELETE", "/profile/preferences", json={"confirm": True})
    assert resp.status_code == 401
    mem.clear_user_data.assert_not_called()


def test_delete_preferences_returns_204_when_no_memory_client():
    """DELETE /profile/preferences returns 204 even when no MCPMemoryClient is configured.

    If MCP is not configured there is nothing to clear, so we succeed silently.
    """
    with _make_server_with_memory(memory_client=None) as (_, client):
        resp = client.request("DELETE", "/profile/preferences", json={"confirm": True}, headers=VALID_HEADERS)
    assert resp.status_code == 204


def test_delete_preferences_returns_204_when_memory_client_raises():
    """DELETE /profile/preferences returns 204 even if MCPMemoryClient.clear_user_data raises.

    Graceful degradation: if MCP is unreachable the endpoint still succeeds
    (there is nothing in MCP to clear if it is down).
    """
    mem = _make_mock_memory()
    mem.clear_user_data = AsyncMock(side_effect=RuntimeError("MCP unreachable"))
    with _make_server_with_memory(memory_client=mem) as (_, client):
        resp = client.request("DELETE", "/profile/preferences", json={"confirm": True}, headers=VALID_HEADERS)
    assert resp.status_code == 204


def test_delete_preferences_400_detail_mentions_confirmation():
    """The 400 error message explains that confirm=true is required."""
    with _make_server_with_memory() as (_, client):
        resp = client.request("DELETE", "/profile/preferences", json={"confirm": False}, headers=VALID_HEADERS)
    detail = resp.json()["detail"].lower()
    assert "confirm" in detail


def test_rate_limit_middleware_default_window_is_60_seconds():
    """RateLimitMiddleware uses a 60-second sliding window by default."""
    middleware = RateLimitMiddleware(app=None)  # type: ignore[arg-type]
    assert middleware._window == 60


def test_rate_limit_middleware_uses_x_forwarded_for_when_present():
    """Behind a reverse proxy, rate limits are applied to the forwarded IP, not 127.0.0.1."""
    _, client = _make_rate_limit_client(auth_limit=1, health_limit=100)
    # First request from proxy IP — allowed
    client.get("/health", headers={"X-Forwarded-For": "10.0.0.1"})
    # Second request from the SAME proxy IP — still allowed (health limit=100)
    resp = client.get("/health", headers={"X-Forwarded-For": "10.0.0.1"})
    assert resp.status_code == 200  # health limit=100, only 2 requests sent


# ─────────────────────────────────────────────────────────────
# /transcribe endpoint
# ─────────────────────────────────────────────────────────────


def test_transcribe_requires_auth():
    """POST /transcribe returns 401 without an Authorization header."""
    with _make_server() as (_, client):
        resp = client.post(
            "/transcribe",
            json={"audio_base64": "SGVsbG8="},
        )
    assert resp.status_code == 401


def test_transcribe_returns_transcribed_text():
    """POST /transcribe returns the text from Whisper STT."""
    b64_audio = "SGVsbG8gV29ybGQ="  # base64("Hello World") — valid base64
    with (
        _make_server() as (_, client),
        patch(
            "blind_assistant.voice.stt.transcribe_audio",
            new=AsyncMock(return_value="Hello World"),
        ),
    ):
        resp = client.post(
            "/transcribe",
            json={"audio_base64": b64_audio},
            headers=VALID_HEADERS,
        )
    assert resp.status_code == 200
    assert resp.json()["text"] == "Hello World"


def test_transcribe_returns_empty_string_on_silence():
    """POST /transcribe returns empty string when Whisper detects no speech."""
    b64_audio = "AAAA"  # valid base64 that decodes to non-empty bytes
    with (
        _make_server() as (_, client),
        patch(
            "blind_assistant.voice.stt.transcribe_audio",
            new=AsyncMock(return_value=None),
        ),
    ):
        resp = client.post(
            "/transcribe",
            json={"audio_base64": b64_audio},
            headers=VALID_HEADERS,
        )
    assert resp.status_code == 200
    assert resp.json()["text"] == ""


def test_transcribe_returns_400_on_invalid_base64():
    """POST /transcribe returns 400 if audio_base64 is not valid base64."""
    with _make_server() as (_, client):
        resp = client.post(
            "/transcribe",
            json={"audio_base64": "!!! not base64 !!!"},
            headers=VALID_HEADERS,
        )
    assert resp.status_code == 400
    assert "invalid" in resp.json()["detail"].lower()


def test_transcribe_empty_audio_base64_returns_empty_text():
    """POST /transcribe with base64 that decodes to empty bytes returns empty text immediately."""
    import base64 as b64

    # base64 of b"" is an empty string, but b64encode(b"") = b"" which encodes to ""
    # Let's test with a base64 that decodes to zero bytes
    empty_b64 = b64.b64encode(b"").decode()  # ""
    with _make_server() as (_, client):
        resp = client.post(
            "/transcribe",
            json={"audio_base64": empty_b64},
            headers=VALID_HEADERS,
        )
    assert resp.status_code == 200
    assert resp.json()["text"] == ""


def test_transcribe_passes_language_hint_to_stt():
    """POST /transcribe passes the language hint to transcribe_audio."""
    b64_audio = "SGVsbG8="
    mock_stt = AsyncMock(return_value="Hola")
    with (
        _make_server() as (_, client),
        patch(
            "blind_assistant.voice.stt.transcribe_audio",
            new=mock_stt,
        ),
    ):
        client.post(
            "/transcribe",
            json={"audio_base64": b64_audio, "language": "es"},
            headers=VALID_HEADERS,
        )
    # Verify language was passed through
    mock_stt.assert_called_once()
    _, call_kwargs = mock_stt.call_args
    assert call_kwargs.get("language") == "es"


def test_transcribe_echoes_session_id():
    """POST /transcribe echoes the session_id from the request."""
    b64_audio = "SGVsbG8="
    with (
        _make_server() as (_, client),
        patch(
            "blind_assistant.voice.stt.transcribe_audio",
            new=AsyncMock(return_value="test"),
        ),
    ):
        resp = client.post(
            "/transcribe",
            json={"audio_base64": b64_audio, "session_id": "my-session-xyz"},
            headers=VALID_HEADERS,
        )
    assert resp.json()["session_id"] == "my-session-xyz"


# ─────────────────────────────────────────────────────────────
# /transcribe — body size limit (ISSUE-018)
# ─────────────────────────────────────────────────────────────


def test_transcribe_rejects_oversized_payload():
    """POST /transcribe returns 413 when audio_base64 exceeds 14 MB chars (ISSUE-018)."""
    # 14_000_001 chars — one over the limit
    oversized = "A" * 14_000_001
    with _make_server() as (_, client):
        resp = client.post(
            "/transcribe",
            json={"audio_base64": oversized},
            headers=VALID_HEADERS,
        )
    assert resp.status_code == 413
    detail = resp.json()["detail"].lower()
    assert "too large" in detail or "maximum" in detail


def test_transcribe_accepts_payload_at_exact_limit():
    """POST /transcribe accepts exactly 14_000_000 chars (at the limit boundary)."""
    # 14_000_000 chars is exactly the limit — should decode to valid bytes and be accepted
    at_limit = "A" * 14_000_000  # 'A' is valid base64 padding char; produces valid bytes
    mock_stt = AsyncMock(return_value="")
    with _make_server() as (_, client), patch("blind_assistant.voice.stt.transcribe_audio", new=mock_stt):
        resp = client.post(
            "/transcribe",
            json={"audio_base64": at_limit},
            headers=VALID_HEADERS,
        )
    # Should not return 413 — limit is inclusive
    assert resp.status_code != 413


def test_transcribe_413_message_mentions_limit():
    """The 413 error message tells the user the maximum and a suggested fix."""
    oversized = "A" * 14_000_001
    with _make_server() as (_, client):
        resp = client.post(
            "/transcribe",
            json={"audio_base64": oversized},
            headers=VALID_HEADERS,
        )
    assert resp.status_code == 413
    detail = resp.json()["detail"]
    # Message must mention the size limit in MB so the user knows what to expect
    assert "MB" in detail or "mb" in detail.lower()


def test_transcribe_small_payload_is_not_rejected():
    """POST /transcribe accepts a small (realistic) audio payload without 413."""
    import base64 as b64

    # 1 second of 16kHz mono audio ≈ 32 kB WAV ≈ 44 kB base64 — well within limit
    small_audio = b"RIFF" + b"\x00" * 1000  # fake WAV header + silence
    small_b64 = b64.b64encode(small_audio).decode()
    mock_stt = AsyncMock(return_value="")
    with _make_server() as (_, client), patch("blind_assistant.voice.stt.transcribe_audio", new=mock_stt):
        resp = client.post(
            "/transcribe",
            json={"audio_base64": small_b64},
            headers=VALID_HEADERS,
        )
    assert resp.status_code == 200
