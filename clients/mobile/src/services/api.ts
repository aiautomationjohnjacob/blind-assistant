/**
 * Blind Assistant API Client
 *
 * Thin HTTP client that connects this React Native app to the Python backend.
 * All intelligence lives on the backend — this client sends user input and
 * receives text/voice responses.
 *
 * Per the backend API contract (src/blind_assistant/interfaces/api_server.py):
 *   POST /query      — send user message, receive text + optional spoken text
 *   POST /transcribe — send base64 audio bytes; receive Whisper transcription
 *   POST /remember   — add voice note to Second Brain
 *   POST /describe   — request screen description (desktop only)
 *   POST /task       — execute a real-world agentic task
 *   GET  /profile    — fetch user preferences
 *   GET  /health     — liveness check (no auth required)
 */

// ─────────────────────────────────────────────────────────────
// Types — mirror backend pydantic models
// ─────────────────────────────────────────────────────────────

export interface QueryRequest {
  message: string;
  session_id?: string;
  speech_rate?: number;
  verbosity?: "brief" | "standard" | "detailed";
  braille_mode?: boolean;
}

export interface QueryResponse {
  text: string;
  spoken_text: string | null;
  follow_up_prompt: string | null;
  session_id: string;
}

export interface TranscribeRequest {
  /** Base64-encoded audio bytes (WAV, M4A, OGG — any format Whisper supports). */
  audio_base64: string;
  /** Optional BCP-47 language tag (e.g. "en", "es"). Auto-detected if omitted. */
  language?: string;
  session_id?: string;
}

export interface TranscribeResponse {
  /** Transcribed text — empty string if no speech detected. */
  text: string;
  /** Language Whisper detected (e.g. "en"). Null if detection failed. */
  language: string | null;
  session_id: string;
}

export interface RememberRequest {
  content: string;
  session_id?: string;
}

export interface RememberResponse {
  text: string;
  note_id: string | null;
}

export interface HealthResponse {
  status: string;
  version: string;
}

export interface ProfileResponse {
  user_id: string;
  verbosity: string;
  speech_rate: number;
  output_mode: string;
  braille_mode: boolean;
}

// ─────────────────────────────────────────────────────────────
// Client
// ─────────────────────────────────────────────────────────────

export class BlindAssistantAPIError extends Error {
  /** HTTP status code, or 0 for network errors. */
  constructor(
    public readonly statusCode: number,
    message: string
  ) {
    super(message);
    this.name = "BlindAssistantAPIError";
  }
}

export class BlindAssistantAPIClient {
  /**
   * HTTP client for the Blind Assistant REST backend.
   *
   * During development the backend runs at localhost:8000.
   * In production this URL will be loaded from app.config.ts extra.apiBaseUrl.
   */

  private readonly baseUrl: string;
  private readonly bearerToken: string | null;

  constructor(baseUrl: string, bearerToken: string | null = null) {
    this.baseUrl = baseUrl.replace(/\/$/, ""); // strip trailing slash
    this.bearerToken = bearerToken;
  }

  // ─────────────────────────────────────────────────────────
  // Private helpers
  // ─────────────────────────────────────────────────────────

  private buildHeaders(includeAuth = true): HeadersInit {
    /** Build common HTTP headers, including optional Bearer token. */
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      Accept: "application/json",
    };
    if (includeAuth && this.bearerToken) {
      headers["Authorization"] = `Bearer ${this.bearerToken}`;
    }
    return headers;
  }

  private async request<T>(
    method: "GET" | "POST",
    path: string,
    body?: unknown,
    includeAuth = true
  ): Promise<T> {
    /**
     * Execute an HTTP request and return the parsed JSON response.
     * Throws BlindAssistantAPIError on non-2xx status or network failure.
     */
    const url = `${this.baseUrl}${path}`;
    const options: RequestInit = {
      method,
      headers: this.buildHeaders(includeAuth),
    };
    if (body !== undefined) {
      options.body = JSON.stringify(body);
    }

    let response: Response;
    try {
      response = await fetch(url, options);
    } catch (err) {
      throw new BlindAssistantAPIError(
        0,
        `Network error connecting to backend at ${this.baseUrl}: ${String(err)}`
      );
    }

    if (!response.ok) {
      let detail = response.statusText;
      try {
        const errorBody = (await response.json()) as { detail?: string };
        if (errorBody.detail) detail = errorBody.detail;
      } catch {
        // JSON parse failed — use statusText
      }
      throw new BlindAssistantAPIError(
        response.status,
        `Backend error ${response.status}: ${detail}`
      );
    }

    return response.json() as Promise<T>;
  }

  // ─────────────────────────────────────────────────────────
  // Public API methods
  // ─────────────────────────────────────────────────────────

  /** Check if the backend is alive. No authentication required. */
  async health(): Promise<HealthResponse> {
    return this.request<HealthResponse>("GET", "/health", undefined, false);
  }

  /**
   * Send a user message and receive an AI response.
   * This is the primary method for all user interactions.
   */
  async query(req: QueryRequest): Promise<QueryResponse> {
    return this.request<QueryResponse>("POST", "/query", {
      session_id: "default",
      speech_rate: 1.0,
      verbosity: "standard",
      braille_mode: false,
      ...req,
    });
  }

  /**
   * Transcribe audio to text using the backend's Whisper STT.
   *
   * Usage: record audio with expo-av, base64-encode the raw bytes, call this method.
   * Returns the transcribed text which can then be passed to query().
   *
   * Privacy: Whisper runs locally on the backend server — speech never leaves the machine.
   */
  async transcribe(req: TranscribeRequest): Promise<TranscribeResponse> {
    return this.request<TranscribeResponse>("POST", "/transcribe", {
      session_id: "default",
      ...req,
    });
  }

  /**
   * Store a voice note in the user's Second Brain vault.
   * Used when user says "remember this" or "add a note".
   */
  async remember(req: RememberRequest): Promise<RememberResponse> {
    return this.request<RememberResponse>("POST", "/remember", {
      session_id: "default",
      ...req,
    });
  }

  /** Retrieve the user's current preferences from the backend. */
  async getProfile(): Promise<ProfileResponse> {
    return this.request<ProfileResponse>("GET", "/profile");
  }
}

// ─────────────────────────────────────────────────────────────
// Singleton client (configured from app.config.ts)
// ─────────────────────────────────────────────────────────────

let _apiClient: BlindAssistantAPIClient | null = null;

/** Get or create the singleton API client. Call configureAPIClient() first. */
export function getAPIClient(): BlindAssistantAPIClient {
  if (!_apiClient) {
    throw new Error(
      "API client not configured. Call configureAPIClient() during app startup."
    );
  }
  return _apiClient;
}

/** Configure the API client. Call once during app startup. */
export function configureAPIClient(
  baseUrl: string,
  bearerToken: string | null = null
): void {
  _apiClient = new BlindAssistantAPIClient(baseUrl, bearerToken);
}

/** Reset the API client (used in tests). */
export function resetAPIClient(): void {
  _apiClient = null;
}
