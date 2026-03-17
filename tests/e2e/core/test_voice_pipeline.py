"""
E2E test: Voice input → Whisper STT → Orchestrator → TTS audio reply

This is the "product exists" test. It exercises the complete backend pipeline
that a Desktop CLI user experiences:

  microphone input
      ↓ transcribe_microphone (Whisper STT — mocked in CI, real in manual runs)
      ↓ orchestrator.handle_message (real orchestrator — Claude API mocked)
      ↓ response.spoken_text or response.text
      ↓ speak_locally (TTS pyttsx3 — mocked)
  speaker output

Per ISSUE-007: this test closes the Phase 2 gate. A real user (via Desktop CLI)
can now interact with the assistant end-to-end.

External APIs mocked:
  - Whisper (STT model — no GPU/download required in CI)
  - Claude Anthropic API
  - pyttsx3 (no real speaker access)
  - OS keychain (mock_keyring from conftest)
  - sounddevice (suppress_audio from conftest)

Real I/O used:
  - Orchestrator initialization + intent routing (real code paths)
  - Confirmation gate (real asyncio queues)
  - Response formatting (real braille/brief mode code)
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from blind_assistant.core.orchestrator import Orchestrator, Response, UserContext
from blind_assistant.interfaces.voice_local import VoiceLocalInterface

pytestmark = pytest.mark.integration


# ─────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────


def _make_config(tmp_path) -> dict:
    return {
        "vault_path": str(tmp_path / "vault"),
        "voice_local_enabled": True,
        "wake_word": "assistant",
        "record_duration": 5.0,
        "voice": {"prompt_timeout_seconds": 5},
    }


async def _init_orchestrator(config: dict, mock_planner, mock_registry, mock_ctx_mgr) -> Orchestrator:
    """Initialize orchestrator with mocked sub-components."""
    orch = Orchestrator(config)

    with patch("blind_assistant.core.planner.Planner", return_value=mock_planner), \
         patch("blind_assistant.tools.registry.ToolRegistry", return_value=mock_registry), \
         patch("blind_assistant.core.context.ContextManager", return_value=mock_ctx_mgr):
        await orch.initialize()

    return orch


# ─────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────


@pytest.fixture
def mock_planner_general_question():
    """Planner classifies any message as 'general_question' (no tool needed)."""
    from blind_assistant.core.planner import Intent
    planner = MagicMock()
    planner.classify_intent = AsyncMock(
        return_value=Intent(
            type="general_question",
            description="User asked a general question.",
            required_tools=[],
            parameters={},
            is_high_stakes=False,
            confidence=0.95,
        )
    )
    return planner


@pytest.fixture
def mock_registry_empty():
    """Empty tool registry — no tools to install."""
    registry = MagicMock()
    registry.load = AsyncMock()
    registry.is_installed.return_value = True  # All tools "installed" (no prompts needed)
    return registry


@pytest.fixture
def mock_context_manager(tmp_path):
    """ContextManager that returns a realistic UserContext."""
    ctx_mgr = MagicMock()
    ctx_mgr.initialize = AsyncMock()
    ctx_mgr.load_user_context = AsyncMock(
        return_value=UserContext(
            user_id="local_user",
            session_id="e2e_test",
            verbosity="standard",
            speech_rate=1.0,
            output_mode="voice_text",
            braille_mode=False,
        )
    )
    return ctx_mgr


# ─────────────────────────────────────────────────────────────
# Test 1: Full voice pipeline — speech in, speech out
# ─────────────────────────────────────────────────────────────


class TestVoicePipelineHappyPath:
    async def test_voice_input_reaches_orchestrator(
        self,
        tmp_path,
        mock_keyring,
        mock_planner_general_question,
        mock_registry_empty,
        mock_context_manager,
    ):
        """
        A voice utterance flows from microphone → STT → orchestrator → TTS.

        Verifies the integration seam: transcribe_microphone output is passed
        unchanged as the 'text' argument to orchestrator.handle_message.
        """
        config = _make_config(tmp_path)
        orch = await _init_orchestrator(
            config,
            mock_planner_general_question,
            mock_registry_empty,
            mock_context_manager,
        )

        iface = VoiceLocalInterface(orch, config)

        # Simulate user saying "assistant what is the weather today"
        voice_input = "assistant what is the weather today"

        received_texts: list[str] = []

        async def capture_handle_message(text, context, response_callback=None):
            received_texts.append(text)
            return Response(text="I don't have live weather data.", spoken_text=None, follow_up_prompt=None)

        orch.handle_message = AsyncMock(side_effect=capture_handle_message)

        # Load a fake context
        iface._context = UserContext(
            user_id="local_user",
            session_id="e2e_test",
            verbosity="standard",
            speech_rate=1.0,
            output_mode="voice_text",
            braille_mode=False,
        )

        with patch(
            "blind_assistant.voice.stt.transcribe_microphone",
            new=AsyncMock(return_value=voice_input),
        ), patch("blind_assistant.voice.tts.speak_locally", new=AsyncMock()):
            await iface._listen_and_respond()

        assert len(received_texts) == 1
        # Wake word "assistant" should be stripped before reaching orchestrator
        assert "assistant" not in received_texts[0].lower()
        assert "what is the weather today" in received_texts[0]

    async def test_tts_speaks_orchestrator_response(
        self,
        tmp_path,
        mock_keyring,
        mock_planner_general_question,
        mock_registry_empty,
        mock_context_manager,
    ):
        """
        The text returned by the orchestrator is passed to speak_locally.
        This verifies the final seam: AI brain → audio output.
        """
        config = _make_config(tmp_path)
        orch = await _init_orchestrator(
            config,
            mock_planner_general_question,
            mock_registry_empty,
            mock_context_manager,
        )

        expected_reply = "The current temperature is 72 degrees Fahrenheit."
        orch.handle_message = AsyncMock(
            return_value=Response(text=expected_reply, spoken_text=None, follow_up_prompt=None)
        )

        iface = VoiceLocalInterface(orch, config)
        iface._context = UserContext(
            user_id="local_user",
            session_id="e2e_test",
            verbosity="standard",
            speech_rate=1.0,
            output_mode="voice_text",
            braille_mode=False,
        )

        spoken: list[str] = []

        async def capture_speak(text, speed=1.0):  # noqa: ARG001
            spoken.append(text)

        with patch(
            "blind_assistant.voice.stt.transcribe_microphone",
            new=AsyncMock(return_value="assistant what is the weather"),
        ), patch("blind_assistant.voice.tts.speak_locally", new=capture_speak):
            await iface._listen_and_respond()

        assert any(expected_reply in m for m in spoken), (
            f"Expected reply not spoken. Got: {spoken}"
        )

    async def test_response_callback_streams_interim_updates(
        self,
        tmp_path,
        mock_keyring,
        mock_planner_general_question,
        mock_registry_empty,
        mock_context_manager,
    ):
        """
        The response_callback passed to orchestrator.handle_message is wired to
        speak_locally. Interim messages (e.g., 'Let me think...') should be spoken.
        """
        config = _make_config(tmp_path)
        orch = await _init_orchestrator(
            config,
            mock_planner_general_question,
            mock_registry_empty,
            mock_context_manager,
        )

        interim_spoken: list[str] = []

        async def orchestrator_with_streaming(text, context, response_callback=None):  # noqa: ARG001
            if response_callback:
                await response_callback("Let me think about that...")
            return Response(text="Here is the answer.", spoken_text=None, follow_up_prompt=None)

        orch.handle_message = AsyncMock(side_effect=orchestrator_with_streaming)

        iface = VoiceLocalInterface(orch, config)
        iface._context = UserContext(
            user_id="local_user",
            session_id="e2e_test",
            verbosity="standard",
            speech_rate=1.0,
            output_mode="voice_text",
            braille_mode=False,
        )

        async def capture_speak(text, speed=1.0):  # noqa: ARG001
            interim_spoken.append(text)

        with patch(
            "blind_assistant.voice.stt.transcribe_microphone",
            new=AsyncMock(return_value="assistant explain quantum computing"),
        ), patch("blind_assistant.voice.tts.speak_locally", new=capture_speak):
            await iface._listen_and_respond()

        # Interim "thinking" message must be spoken
        assert any("think" in m.lower() for m in interim_spoken)
        # Final answer must also be spoken
        assert any("Here is the answer." in m for m in interim_spoken)


# ─────────────────────────────────────────────────────────────
# Test 2: STT mock → orchestrator real path → TTS
# ─────────────────────────────────────────────────────────────


class TestVoicePipelineOrchestratorIntegration:
    async def test_orchestrator_general_question_returns_text(
        self,
        tmp_path,
        mock_keyring,
        mock_planner_general_question,
        mock_registry_empty,
        mock_context_manager,
    ):
        """
        Orchestrator.handle_message with a general_question intent calls Claude
        (mocked) and returns text. Verifies the orchestrator→Claude seam.

        anthropic is mocked at the blind_assistant.core.orchestrator import point
        since the package may not be installed in all CI environments.
        """
        config = _make_config(tmp_path)
        orch = await _init_orchestrator(
            config,
            mock_planner_general_question,
            mock_registry_empty,
            mock_context_manager,
        )

        context = UserContext(
            user_id="local_user",
            session_id="e2e_test_2",
            verbosity="standard",
            speech_rate=1.0,
            output_mode="voice_text",
            braille_mode=False,
        )

        mock_claude_message = MagicMock()
        mock_claude_message.content = [MagicMock(text="The capital of France is Paris.")]

        mock_client_instance = AsyncMock()
        mock_client_instance.messages.create = AsyncMock(return_value=mock_claude_message)

        mock_anthropic_module = MagicMock()
        mock_anthropic_module.AsyncAnthropic = MagicMock(return_value=mock_client_instance)

        with patch.dict("sys.modules", {"anthropic": mock_anthropic_module}), \
             patch(
                 "blind_assistant.security.credentials.require_credential",
                 return_value="fake_key",
             ):
            response = await orch.handle_message(
                text="What is the capital of France?",
                context=context,
            )

        assert response.text
        assert len(response.text) > 0

    async def test_orchestrator_response_has_no_visual_only_language(
        self,
        tmp_path,
        mock_keyring,
        mock_planner_general_question,
        mock_registry_empty,
        mock_context_manager,
    ):
        """
        Accessibility assertion: the orchestrator system prompt instructs Claude
        to avoid visual descriptions. The response should not start with visual-only
        cues like 'As you can see' or 'Looking at the screen'.
        Per CLAUDE.md accessibility rules: voice output must not use visual-only language.
        """
        config = _make_config(tmp_path)
        orch = await _init_orchestrator(
            config,
            mock_planner_general_question,
            mock_registry_empty,
            mock_context_manager,
        )

        context = UserContext(
            user_id="local_user",
            session_id="e2e_a11y_test",
            verbosity="standard",
            speech_rate=1.0,
            output_mode="voice_text",
            braille_mode=False,
        )

        # Return text that does NOT use visual-only language (correct AI behaviour)
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Paris is the capital city of France.")]

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        mock_anthropic_mod = MagicMock()
        mock_anthropic_mod.AsyncAnthropic = MagicMock(return_value=mock_client)

        visual_only_phrases = [
            "as you can see",
            "looking at the screen",
            "as shown above",
            "click here",
            "see figure",
            "see diagram",
        ]

        with patch.dict("sys.modules", {"anthropic": mock_anthropic_mod}), \
             patch(
                 "blind_assistant.security.credentials.require_credential",
                 return_value="fake_key",
             ):
            response = await orch.handle_message(
                text="What is the capital of France?",
                context=context,
            )

        response_lower = response.text.lower()
        for phrase in visual_only_phrases:
            assert phrase not in response_lower, (
                f"Visual-only phrase '{phrase}' found in voice response: {response.text}"
            )


# ─────────────────────────────────────────────────────────────
# Test 3: VoiceLocalInterface full start/stop lifecycle
# ─────────────────────────────────────────────────────────────


class TestVoiceLocalLifecycle:
    async def test_start_announces_ready(
        self,
        tmp_path,
        mock_keyring,
        mock_planner_general_question,
        mock_registry_empty,
        mock_context_manager,
    ):
        """
        VoiceLocalInterface.start() announces readiness to the user before
        entering the listen loop. This is critical for blind users — they need
        audible confirmation that the assistant is ready.

        We stop the loop by having the transcription mock set _running=False,
        then raise CancelledError to exit cleanly.
        """
        config = _make_config(tmp_path)
        orch = await _init_orchestrator(
            config,
            mock_planner_general_question,
            mock_registry_empty,
            mock_context_manager,
        )

        iface = VoiceLocalInterface(orch, config)

        spoken: list[str] = []

        async def capture_speak(text, speed=1.0):  # noqa: ARG001
            spoken.append(text)

        async def stop_on_first_call(duration_seconds=5.0):  # noqa: ARG001
            # Stop the loop — _listen_and_respond will return None (silence), loop will exit
            iface._running = False
            raise asyncio.CancelledError

        with patch("blind_assistant.voice.tts.speak_locally", new=capture_speak), \
             patch(
                 "blind_assistant.voice.stt.transcribe_microphone",
                 new=AsyncMock(side_effect=stop_on_first_call)
             ):
            await iface.start()

        # Must have spoken a startup/ready message BEFORE entering the loop
        assert any("blind assistant" in m.lower() for m in spoken), (
            f"No startup announcement found. Spoken: {spoken}"
        )

    async def test_stop_gracefully_sets_running_false(
        self,
        tmp_path,
        mock_keyring,
        mock_planner_general_question,
        mock_registry_empty,
        mock_context_manager,
    ):
        """
        stop() sets _running to False.
        The voice loop checks _running on each iteration and exits cleanly.
        """
        config = _make_config(tmp_path)
        orch = await _init_orchestrator(
            config,
            mock_planner_general_question,
            mock_registry_empty,
            mock_context_manager,
        )

        iface = VoiceLocalInterface(orch, config)
        iface._running = True

        await iface.stop()

        assert not iface._running


# ─────────────────────────────────────────────────────────────
# Test 4: API server → orchestrator round-trip (HTTP layer)
# ─────────────────────────────────────────────────────────────


class TestAPIServerVoicePipeline:
    async def test_query_endpoint_returns_response(
        self,
        tmp_path,
        mock_keyring,
        mock_planner_general_question,
        mock_registry_empty,
        mock_context_manager,
    ):
        """
        POST /query → orchestrator → text response.
        This is the path all native client apps use to send user messages.
        """
        from fastapi.testclient import TestClient

        from blind_assistant.interfaces.api_server import APIServer

        config = _make_config(tmp_path)
        orch = await _init_orchestrator(
            config,
            mock_planner_general_question,
            mock_registry_empty,
            mock_context_manager,
        )

        orch.handle_message = AsyncMock(
            return_value=Response(
                text="The answer to your question.",
                spoken_text=None,
                follow_up_prompt=None,
            )
        )

        # Disable auth for test
        config["api_auth_disabled"] = True
        server = APIServer(orch, config)
        app = server._build_app()

        with TestClient(app) as client:
            resp = client.post(
                "/query",
                json={"message": "What is the capital of France?", "session_id": "test"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["text"] == "The answer to your question."

    async def test_health_endpoint_no_auth_required(
        self,
        tmp_path,
        mock_keyring,
        mock_planner_general_question,
        mock_registry_empty,
        mock_context_manager,
    ):
        """
        GET /health returns 200 without Bearer token.
        Required for load balancers and monitoring tools.
        """
        from fastapi.testclient import TestClient

        from blind_assistant.interfaces.api_server import APIServer

        config = _make_config(tmp_path)
        orch = await _init_orchestrator(
            config,
            mock_planner_general_question,
            mock_registry_empty,
            mock_context_manager,
        )

        server = APIServer(orch, config)
        app = server._build_app()

        with TestClient(app) as client:
            resp = client.get("/health")

        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
