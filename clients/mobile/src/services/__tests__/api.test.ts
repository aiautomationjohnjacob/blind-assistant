/**
 * Unit tests for the BlindAssistantAPIClient
 *
 * Verifies that the HTTP client:
 * 1. Sends the correct payload to /query, /remember, etc.
 * 2. Includes the Authorization header when a token is configured
 * 3. Handles HTTP errors (401, 500) with a typed BlindAssistantAPIError
 * 4. Handles network failures with a typed error (status code 0)
 * 5. Singleton helpers (getAPIClient / configureAPIClient / resetAPIClient)
 *    behave correctly across tests
 *
 * All tests mock globalThis.fetch — no real HTTP calls are made.
 */

import {
  BlindAssistantAPIClient,
  BlindAssistantAPIError,
  configureAPIClient,
  getAPIClient,
  resetAPIClient,
} from "../api";

// ─────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────

/** Build a mock Response-like object for the fetch mock. */
function mockFetchResponse(
  body: unknown,
  status = 200,
  ok = true
): Response {
  return {
    ok,
    status,
    statusText: ok ? "OK" : "Error",
    json: jest.fn().mockResolvedValue(body),
    headers: new Headers({ "content-type": "application/json" }),
  } as unknown as Response;
}

const BASE_URL = "http://localhost:8000";
const TOKEN = "test-bearer-token";

// ─────────────────────────────────────────────────────────────
// Tests: BlindAssistantAPIClient
// ─────────────────────────────────────────────────────────────

describe("BlindAssistantAPIClient", () => {
  let client: BlindAssistantAPIClient;
  let fetchMock: jest.SpyInstance;

  beforeEach(() => {
    client = new BlindAssistantAPIClient(BASE_URL, TOKEN);
    fetchMock = jest
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(mockFetchResponse({ status: "ok", version: "0.1.0" }));
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  // ──────── health ────────

  describe("health()", () => {
    it("sends GET /health without Authorization header", async () => {
      await client.health();

      expect(fetchMock).toHaveBeenCalledWith(
        `${BASE_URL}/health`,
        expect.objectContaining({
          method: "GET",
          headers: expect.not.objectContaining({
            Authorization: expect.any(String),
          }),
        })
      );
    });

    it("returns status 'ok' on success", async () => {
      fetchMock.mockResolvedValue(
        mockFetchResponse({ status: "ok", version: "0.1.0" })
      );
      const result = await client.health();
      expect(result.status).toBe("ok");
    });
  });

  // ──────── query ────────

  describe("query()", () => {
    it("sends POST /query with message and session_id", async () => {
      fetchMock.mockResolvedValue(
        mockFetchResponse({
          text: "Hello!",
          spoken_text: null,
          follow_up_prompt: null,
          session_id: "s1",
        })
      );

      await client.query({ message: "Hi", session_id: "s1" });

      expect(fetchMock).toHaveBeenCalledWith(
        `${BASE_URL}/query`,
        expect.objectContaining({ method: "POST" })
      );

      const call = fetchMock.mock.calls[0]!;
      const body = JSON.parse(call[1].body as string) as Record<string, unknown>;
      expect(body.message).toBe("Hi");
      expect(body.session_id).toBe("s1");
    });

    it("includes Authorization Bearer header when token is set", async () => {
      fetchMock.mockResolvedValue(
        mockFetchResponse({
          text: "ok",
          spoken_text: null,
          follow_up_prompt: null,
          session_id: "s1",
        })
      );

      await client.query({ message: "test" });

      const call = fetchMock.mock.calls[0]!;
      const headers = call[1].headers as Record<string, string>;
      expect(headers["Authorization"]).toBe(`Bearer ${TOKEN}`);
    });

    it("uses spoken_text if provided in response", async () => {
      fetchMock.mockResolvedValue(
        mockFetchResponse({
          text: "Long text.",
          spoken_text: "Short.",
          follow_up_prompt: null,
          session_id: "s1",
        })
      );

      const result = await client.query({ message: "test" });
      expect(result.spoken_text).toBe("Short.");
      expect(result.text).toBe("Long text.");
    });

    it("applies default speech_rate 1.0 when not specified", async () => {
      fetchMock.mockResolvedValue(
        mockFetchResponse({
          text: "ok",
          spoken_text: null,
          follow_up_prompt: null,
          session_id: "default",
        })
      );

      await client.query({ message: "test" });

      const body = JSON.parse(
        fetchMock.mock.calls[0]![1].body as string
      ) as Record<string, unknown>;
      expect(body.speech_rate).toBe(1.0);
    });

    it("throws BlindAssistantAPIError on 401 response", async () => {
      fetchMock.mockResolvedValue(
        mockFetchResponse({ detail: "Invalid API token." }, 401, false)
      );

      await expect(client.query({ message: "test" })).rejects.toThrow(
        BlindAssistantAPIError
      );
      await expect(client.query({ message: "test" })).rejects.toMatchObject({
        statusCode: 401,
      });
    });

    it("throws BlindAssistantAPIError with statusCode 0 on network failure", async () => {
      fetchMock.mockRejectedValue(new TypeError("Network request failed"));

      await expect(client.query({ message: "test" })).rejects.toThrow(
        BlindAssistantAPIError
      );
      await expect(client.query({ message: "test" })).rejects.toMatchObject({
        statusCode: 0,
      });
    });
  });

  // ──────── remember ────────

  describe("remember()", () => {
    it("sends POST /remember with content", async () => {
      fetchMock.mockResolvedValue(
        mockFetchResponse({ text: "Note saved.", note_id: "note_123" })
      );

      await client.remember({ content: "Meeting notes" });

      const call = fetchMock.mock.calls[0]!;
      const body = JSON.parse(call[1].body as string) as Record<string, unknown>;
      expect(body.content).toBe("Meeting notes");
    });

    it("returns note_id from server response", async () => {
      fetchMock.mockResolvedValue(
        mockFetchResponse({ text: "Saved.", note_id: "abc123" })
      );

      const result = await client.remember({ content: "test" });
      expect(result.note_id).toBe("abc123");
    });
  });

  // ──────── Base URL trailing slash handling ────────

  describe("URL normalization", () => {
    it("strips trailing slash from baseUrl", async () => {
      const clientWithSlash = new BlindAssistantAPIClient(
        "http://localhost:8000/",
        TOKEN
      );
      fetchMock.mockResolvedValue(
        mockFetchResponse({ status: "ok", version: "0.1.0" })
      );

      await clientWithSlash.health();

      expect(fetchMock.mock.calls[0]![0]).toBe("http://localhost:8000/health");
    });
  });
});

// ─────────────────────────────────────────────────────────────
// Tests: Singleton helpers
// ─────────────────────────────────────────────────────────────

describe("API client singleton", () => {
  afterEach(() => {
    resetAPIClient();
  });

  it("getAPIClient throws before configureAPIClient is called", () => {
    expect(() => getAPIClient()).toThrow(
      /not configured/i
    );
  });

  it("getAPIClient returns client after configureAPIClient", () => {
    configureAPIClient(BASE_URL, TOKEN);
    const c = getAPIClient();
    expect(c).toBeInstanceOf(BlindAssistantAPIClient);
  });

  it("resetAPIClient causes getAPIClient to throw again", () => {
    configureAPIClient(BASE_URL, TOKEN);
    resetAPIClient();
    expect(() => getAPIClient()).toThrow(/not configured/i);
  });

  it("configureAPIClient without token creates client with null token", () => {
    configureAPIClient(BASE_URL);
    const c = getAPIClient();
    // The client should exist; health() (no-auth) should work
    expect(c).toBeInstanceOf(BlindAssistantAPIClient);
  });
});

// ─────────────────────────────────────────────────────────────
// Tests: BlindAssistantAPIError
// ─────────────────────────────────────────────────────────────

describe("BlindAssistantAPIError", () => {
  it("stores statusCode and message", () => {
    const err = new BlindAssistantAPIError(401, "Unauthorized");
    expect(err.statusCode).toBe(401);
    expect(err.message).toBe("Unauthorized");
    expect(err.name).toBe("BlindAssistantAPIError");
  });

  it("is instanceof Error", () => {
    const err = new BlindAssistantAPIError(500, "Internal Server Error");
    expect(err).toBeInstanceOf(Error);
  });
});
