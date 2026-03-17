"""
REST API Server — Primary Connection Point for All Client Apps

All five clients (Android, iOS, Desktop, Web, Education) connect to this server.
During development it runs on localhost:8000. In production it will be deployed
to a cloud host (Railway, Fly.io, etc.) — that migration is deferred.

Per founder directive 2026-03-17: all user data (vault, calendar, preferences)
lives on this server, NOT per-device. Clients are thin — they send user input
and play back audio; all intelligence runs here.

Authentication: simple Bearer token stored in OS keychain (API_SERVER_TOKEN).
In production this will be upgraded to JWT or session-based auth.

Endpoints:
  POST /query      — send a user message; receive a text response
  POST /transcribe — send base64 audio; receive transcribed text (Whisper STT)
  POST /remember   — add a voice note to the Second Brain
  POST /describe   — trigger a screen description (desktop only)
  POST /task       — execute a real-world task (order food, book travel, etc.)
  GET  /profile    — return the user's preferences and config
  GET  /health     — server health check; no auth required
"""

import base64
import logging
import time
from collections import defaultdict, deque

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Rate limiting middleware
# ─────────────────────────────────────────────────────────────


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Sliding-window rate limiter for the API server.

    Limits requests per IP address using a deque-based sliding window.
    Two limits are applied:
      - Authenticated endpoints: up to `auth_limit` requests per 60 seconds
      - /health (unauthenticated): up to `health_limit` requests per 60 seconds

    This middleware runs on the backend server before any route handler.
    On localhost during development the blind user is the only caller, so
    these limits only matter once the server is cloud-deployed.
    Values are configurable in config.yaml under `api_server.rate_limit_per_minute`.

    Per SECURITY_MODEL.md: rate limiting protects the Claude API budget and
    prevents a compromised client from degrading service quality for the user.
    """

    def __init__(
        self,
        app,
        auth_limit: int = 60,
        health_limit: int = 120,
        window_seconds: int = 60,
    ) -> None:
        super().__init__(app)
        self._auth_limit = auth_limit
        self._health_limit = health_limit
        self._window = window_seconds
        # {ip: deque of timestamps} — one deque per IP
        self._auth_windows: dict[str, deque[float]] = defaultdict(deque)
        self._health_windows: dict[str, deque[float]] = defaultdict(deque)

    def _is_rate_limited(self, windows: dict[str, deque[float]], ip: str, limit: int) -> bool:
        """Return True if the IP has exceeded the limit in the current window."""
        now = time.monotonic()
        window = windows[ip]
        # Remove timestamps outside the sliding window
        cutoff = now - self._window
        while window and window[0] < cutoff:
            window.popleft()
        if len(window) >= limit:
            return True
        window.append(now)
        return False

    async def dispatch(self, request: Request, call_next):
        """Check rate limit before passing the request to the route handler."""
        # Extract client IP — X-Forwarded-For for reverse-proxy setups
        forwarded_for = request.headers.get("X-Forwarded-For")
        client_ip = forwarded_for.split(",")[0].strip() if forwarded_for else (
            request.client.host if request.client else "unknown"
        )

        if request.url.path == "/health":
            if self._is_rate_limited(self._health_windows, client_ip, self._health_limit):
                logger.warning(f"Rate limit exceeded on /health from {client_ip}")
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded. Please slow down."},
                )
        else:
            if self._is_rate_limited(self._auth_windows, client_ip, self._auth_limit):
                logger.warning(f"Rate limit exceeded on {request.url.path} from {client_ip}")
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded. Please slow down."},
                )

        return await call_next(request)

# ─────────────────────────────────────────────────────────────
# Request / Response models
# ─────────────────────────────────────────────────────────────


class QueryRequest(BaseModel):
    """User sends a text (or pre-transcribed voice) message."""
    message: str
    session_id: str = "default"
    # Optional user preferences override (e.g. speed, verbosity)
    speech_rate: float = 1.0
    verbosity: str = "standard"
    braille_mode: bool = False


class QueryResponse(BaseModel):
    """Text response plus optional metadata for TTS."""
    text: str
    spoken_text: str | None = None       # Shorter spoken version if different from text
    follow_up_prompt: str | None = None  # Next question to ask the user, if any
    session_id: str = "default"


class RememberRequest(BaseModel):
    """Store a voice note in the user's Second Brain vault."""
    content: str       # Transcribed voice note content
    session_id: str = "default"


class RememberResponse(BaseModel):
    """Confirmation that the note was stored."""
    text: str          # Spoken confirmation (e.g. "Note saved")
    note_id: str | None = None


class DescribeRequest(BaseModel):
    """Request a description of the current desktop screen."""
    session_id: str = "default"
    region: dict | None = None    # Optional {x, y, width, height} for partial capture


class DescribeResponse(BaseModel):
    """Screen description as text."""
    text: str
    session_id: str = "default"


class TaskRequest(BaseModel):
    """Execute a high-stakes agentic task (food order, booking, etc.)."""
    task_description: str
    session_id: str = "default"


class TaskResponse(BaseModel):
    """Outcome of a task execution."""
    text: str                 # Summary of what happened
    completed: bool = False
    requires_confirmation: bool = False
    confirmation_prompt: str | None = None


class ProfileResponse(BaseModel):
    """User's current preferences and configuration."""
    user_id: str
    verbosity: str
    speech_rate: float
    output_mode: str
    braille_mode: bool


class TranscribeRequest(BaseModel):
    """Audio transcription request — base64-encoded audio bytes from the client microphone."""
    # Audio file as base64 string (WAV, M4A, OGG, or any format supported by Whisper/ffmpeg).
    # Maximum ~10 MB of audio (about 5 minutes of speech at 16kHz mono WAV).
    audio_base64: str
    # Optional BCP-47 language tag (e.g. "en", "es"). Auto-detected by Whisper if omitted.
    language: str | None = None
    session_id: str = "default"


class TranscribeResponse(BaseModel):
    """Transcribed text from the submitted audio clip."""
    text: str               # Transcribed speech — empty string if nothing detected
    language: str | None    # Language Whisper detected (e.g. "en", "es")
    session_id: str = "default"


class HealthResponse(BaseModel):
    """Server health — no auth required."""
    status: str = "ok"
    version: str = "0.1.0"


# ─────────────────────────────────────────────────────────────
# API Server class
# ─────────────────────────────────────────────────────────────


class APIServer:
    """
    FastAPI-based REST server that exposes the Blind Assistant backend to all clients.

    One orchestrator instance is shared across all requests — it manages per-session
    state internally via UserContext objects keyed by session_id.
    """

    def __init__(self, orchestrator, config: dict) -> None:
        self.orchestrator = orchestrator
        self.config = config
        self._app: FastAPI | None = None
        self._port = int(config.get("api_server_port", 8000))

    def _build_app(self) -> FastAPI:
        """Construct the FastAPI application with routes and middleware."""
        app = FastAPI(
            title="Blind Assistant API",
            description=(
                "REST API connecting all client apps (Android, iOS, Desktop, Web) "
                "to the Blind Assistant backend."
            ),
            version="0.1.0",
            # Disable auto-generated docs in production to avoid leaking API shape
            docs_url="/docs" if self.config.get("debug", False) else None,
            redoc_url=None,
        )

        # Rate limiting — configurable per config.yaml api_server.rate_limit_per_minute
        # Default: 60 req/min for authenticated endpoints, 120 for /health
        rate_cfg = self.config.get("api_server", {})
        auth_limit = int(rate_cfg.get("rate_limit_per_minute", 60))
        health_limit = int(rate_cfg.get("health_rate_limit_per_minute", auth_limit * 2))
        app.add_middleware(
            RateLimitMiddleware,
            auth_limit=auth_limit,
            health_limit=health_limit,
        )

        # CORS: allow all origins during development; restrict in production
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"] if self.config.get("debug", False) else ["http://localhost:*"],
            allow_credentials=True,
            allow_methods=["GET", "POST"],
            allow_headers=["Authorization", "Content-Type"],
        )

        # Register routes
        app.get("/health", response_model=HealthResponse)(self._health)
        app.post("/query", response_model=QueryResponse)(self._query)
        app.post("/transcribe", response_model=TranscribeResponse)(self._transcribe)
        app.post("/remember", response_model=RememberResponse)(self._remember)
        app.post("/describe", response_model=DescribeResponse)(self._describe)
        app.post("/task", response_model=TaskResponse)(self._task)
        app.get("/profile", response_model=ProfileResponse)(self._profile)

        # Global error handler: never expose internal details to clients
        @app.exception_handler(Exception)
        async def _global_error_handler(request: Request, exc: Exception) -> JSONResponse:
            logger.error(f"Unhandled error on {request.url.path}: {exc}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={"detail": "An internal error occurred. Please try again."},
            )

        return app

    # ─────────────────────────────────────────────────────────
    # Auth helper
    # ─────────────────────────────────────────────────────────

    async def _authenticate(self, request: Request) -> str:
        """
        Validate Bearer token from the Authorization header.

        Token is stored in OS keychain under API_SERVER_TOKEN key.
        Returns the user_id embedded in the token (for now, the token IS the user_id).
        Raises HTTP 401 if the token is missing or invalid.
        """
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or malformed Authorization header.")

        provided_token = auth_header.removeprefix("Bearer ").strip()

        from blind_assistant.security.credentials import API_SERVER_TOKEN, get_credential
        stored_token = get_credential(API_SERVER_TOKEN)

        if not stored_token:
            # No token configured yet — check if we're in dev/bypass mode
            if self.config.get("api_auth_disabled", False):
                logger.warning(
                    "API auth is disabled (api_auth_disabled=true in config). "
                    "This is only safe for local development."
                )
                return "dev_user"
            raise HTTPException(
                status_code=401,
                detail=(
                    "API server token not configured. "
                    "Run the setup wizard: python installer/install.py --setup"
                ),
            )

        if provided_token != stored_token:
            raise HTTPException(status_code=401, detail="Invalid API token.")

        # Token is valid — return a user_id (in future this would be decoded from JWT)
        return "local_user"

    # ─────────────────────────────────────────────────────────
    # Route handlers
    # ─────────────────────────────────────────────────────────

    async def _health(self) -> HealthResponse:
        """Health check — no auth required. Used by client apps to verify connectivity."""
        return HealthResponse(status="ok", version="0.1.0")

    async def _query(self, body: QueryRequest, request: Request) -> QueryResponse:
        """
        Send a user message (text or pre-transcribed voice) to the orchestrator.

        The client handles STT locally (using device microphone) then sends the
        transcript here. The server handles intent classification, tool routing,
        and response generation. The client handles TTS playback.
        """
        user_id = await self._authenticate(request)
        context = await self._get_context(user_id, body.session_id, body)

        # Collect interim response messages (progress updates)
        updates: list[str] = []

        async def collect_update(message: str) -> None:
            updates.append(message)
            logger.debug(f"Interim update: {message}")

        response = await self.orchestrator.handle_message(
            text=body.message,
            context=context,
            response_callback=collect_update,
        )

        return QueryResponse(
            text=response.text,
            spoken_text=response.spoken_text,
            follow_up_prompt=response.follow_up_prompt,
            session_id=body.session_id,
        )

    async def _transcribe(self, body: TranscribeRequest, request: Request) -> TranscribeResponse:
        """
        Transcribe base64-encoded audio using local Whisper STT.

        Clients record microphone audio (WAV/M4A/OGG), base64-encode it, and POST here.
        The server decodes the bytes, runs Whisper locally (never sent to external APIs),
        and returns the transcribed text. The client then passes the text to /query.

        Privacy: Whisper runs on the local machine. Speech never leaves the backend server.

        Body size limit: max 10 MB of decoded audio bytes (~5 min at 16kHz mono WAV;
        ~2.7 MB WAV = ~3.6 MB base64). Enforced here before decoding to prevent memory
        exhaustion from large uploads. Per ISSUE-018.
        """
        await self._authenticate(request)

        # Check base64 string length before decoding — base64 overhead is ~4/3 so
        # 14_000_000 base64 chars ≈ 10.5 MB decoded. Reject anything larger up front.
        MAX_AUDIO_B64_CHARS = 14_000_000  # ~10 MB decoded audio limit
        if len(body.audio_base64) > MAX_AUDIO_B64_CHARS:
            raise HTTPException(
                status_code=413,
                detail=(
                    f"Audio payload too large. "
                    f"Maximum is {MAX_AUDIO_B64_CHARS // 1_000_000} MB of audio "
                    f"(approximately 5 minutes at standard quality). "
                    "Please trim your recording and try again."
                ),
            )

        try:
            # Decode base64 audio bytes — invalid base64 raises ValueError
            audio_bytes = base64.b64decode(body.audio_base64)
        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid audio_base64: could not decode base64 data. {exc}",
            ) from exc

        if not audio_bytes:
            # Empty audio — return empty transcript without calling Whisper
            return TranscribeResponse(text="", language=None, session_id=body.session_id)

        from blind_assistant.voice.stt import transcribe_audio

        transcript = await transcribe_audio(audio_bytes, language=body.language)

        return TranscribeResponse(
            text=transcript or "",
            language=body.language,  # Whisper language detection not yet exposed; use hint
            session_id=body.session_id,
        )

    async def _remember(self, body: RememberRequest, request: Request) -> RememberResponse:
        """
        Add a note to the user's Second Brain vault.

        Intended for voice note capture: client records audio, transcribes it locally,
        sends the text here. The server handles encryption and storage.
        """
        user_id = await self._authenticate(request)
        context = await self._get_context(user_id, body.session_id)

        # Route through the orchestrator's add_note handler
        response = await self.orchestrator.handle_message(
            text=f"Remember: {body.content}",
            context=context,
        )

        return RememberResponse(text=response.text)

    async def _describe(self, body: DescribeRequest, request: Request) -> DescribeResponse:
        """
        Trigger a screen description.

        Only meaningful when the backend is running on the same machine as the display.
        For remote server deployments this will return a "no display available" message.
        """
        user_id = await self._authenticate(request)
        context = await self._get_context(user_id, body.session_id)

        response = await self.orchestrator.handle_message(
            text="What's on my screen?",
            context=context,
        )

        return DescribeResponse(text=response.text, session_id=body.session_id)

    async def _task(self, body: TaskRequest, request: Request) -> TaskResponse:
        """
        Execute a real-world agentic task (order food, book travel, etc.).

        High-stakes tasks require user confirmation which is handled conversationally.
        If a confirmation is needed, the response will set requires_confirmation=True
        and the client should display the confirmation_prompt and route the user's
        response back through /query.
        """
        user_id = await self._authenticate(request)
        context = await self._get_context(user_id, body.session_id)

        response = await self.orchestrator.handle_message(
            text=body.task_description,
            context=context,
        )

        return TaskResponse(
            text=response.text,
            completed=not response.requires_confirmation,
            requires_confirmation=response.requires_confirmation,
            confirmation_prompt=response.confirmation_action,
        )

    async def _profile(self, request: Request) -> ProfileResponse:
        """Return the user's current preferences and configuration."""
        user_id = await self._authenticate(request)
        context = await self._get_context(user_id, "profile")

        return ProfileResponse(
            user_id=context.user_id,
            verbosity=context.verbosity,
            speech_rate=context.speech_rate,
            output_mode=context.output_mode,
            braille_mode=context.braille_mode,
        )

    # ─────────────────────────────────────────────────────────
    # Context helper
    # ─────────────────────────────────────────────────────────

    async def _get_context(
        self,
        user_id: str,
        session_id: str,
        body: QueryRequest | None = None,
    ):
        """Load or create user context, applying any per-request preference overrides."""
        context = await self.orchestrator.context_manager.load_user_context(
            user_id=user_id,
            session_id=session_id,
        )
        # Apply per-request overrides from the request body
        if body is not None:
            context.speech_rate = body.speech_rate
            context.verbosity = body.verbosity
            context.braille_mode = body.braille_mode
        return context

    # ─────────────────────────────────────────────────────────
    # Server lifecycle
    # ─────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Start the uvicorn server. This method is async and runs until shutdown."""
        import uvicorn

        self._app = self._build_app()

        # Create a uvicorn Config + Server directly so we can run it in an asyncio task
        server_config = uvicorn.Config(
            app=self._app,
            host=self.config.get("api_server_host", "127.0.0.1"),
            port=self._port,
            log_level="info" if not self.config.get("debug", False) else "debug",
        )
        server = uvicorn.Server(config=server_config)
        logger.info(f"REST API server starting on http://127.0.0.1:{self._port}")
        await server.serve()
