/**
 * Tests for useSecureStorage — secure credential storage layer
 *
 * Verifies that:
 * 1. loadBearerToken returns null when no token is stored
 * 2. saveBearerToken persists the token
 * 3. loadBearerToken returns the stored token after save
 * 4. clearBearerToken removes the stored token
 * 5. loadApiBaseUrl and saveApiBaseUrl mirror the same pattern
 * 6. useSecureStorage hook returns the same set-get-remove interface
 *
 * expo-secure-store is mocked — no device keychain access in Jest.
 */

import {
  loadBearerToken,
  saveBearerToken,
  clearBearerToken,
  loadApiBaseUrl,
  saveApiBaseUrl,
  useSecureStorage,
  SECURE_KEY_BEARER_TOKEN,
  SECURE_KEY_API_BASE_URL,
} from "../useSecureStorage";

// ─────────────────────────────────────────────────────────────
// Mock expo-secure-store
// ─────────────────────────────────────────────────────────────

// Simulate a simple in-memory keychain for testing
const mockStore: Record<string, string> = {};

jest.mock("expo-secure-store", () => ({
  getItemAsync: jest.fn(async (key: string) => mockStore[key] ?? null),
  setItemAsync: jest.fn(async (key: string, value: string) => {
    mockStore[key] = value;
  }),
  deleteItemAsync: jest.fn(async (key: string) => {
    delete mockStore[key];
  }),
}));

import * as SecureStore from "expo-secure-store";

// ─────────────────────────────────────────────────────────────
// Setup / Teardown
// ─────────────────────────────────────────────────────────────

beforeEach(() => {
  // Clear in-memory store and mock call records between tests
  Object.keys(mockStore).forEach((k) => delete mockStore[k]);
  jest.clearAllMocks();
});

// ─────────────────────────────────────────────────────────────
// loadBearerToken
// ─────────────────────────────────────────────────────────────

describe("loadBearerToken", () => {
  it("returns null when no token has been stored", async () => {
    const result = await loadBearerToken();
    expect(result).toBeNull();
  });

  it("calls SecureStore.getItemAsync with the correct key", async () => {
    await loadBearerToken();
    expect(SecureStore.getItemAsync).toHaveBeenCalledWith(SECURE_KEY_BEARER_TOKEN);
  });

  it("returns the stored token after saveBearerToken", async () => {
    await saveBearerToken("test-token-abc123");
    const result = await loadBearerToken();
    expect(result).toBe("test-token-abc123");
  });
});

// ─────────────────────────────────────────────────────────────
// saveBearerToken
// ─────────────────────────────────────────────────────────────

describe("saveBearerToken", () => {
  it("calls SecureStore.setItemAsync with token key and value", async () => {
    await saveBearerToken("my-secret-token");
    expect(SecureStore.setItemAsync).toHaveBeenCalledWith(
      SECURE_KEY_BEARER_TOKEN,
      "my-secret-token"
    );
  });

  it("persists the exact token value without modification", async () => {
    const token = "abc123XYZ!@#$%";
    await saveBearerToken(token);
    const loaded = await loadBearerToken();
    expect(loaded).toBe(token);
  });

  it("overwrites an existing token with a new one", async () => {
    await saveBearerToken("first-token");
    await saveBearerToken("second-token");
    const result = await loadBearerToken();
    expect(result).toBe("second-token");
  });
});

// ─────────────────────────────────────────────────────────────
// clearBearerToken
// ─────────────────────────────────────────────────────────────

describe("clearBearerToken", () => {
  it("calls SecureStore.deleteItemAsync with the correct key", async () => {
    await clearBearerToken();
    expect(SecureStore.deleteItemAsync).toHaveBeenCalledWith(SECURE_KEY_BEARER_TOKEN);
  });

  it("causes loadBearerToken to return null after clearing", async () => {
    await saveBearerToken("token-to-clear");
    await clearBearerToken();
    const result = await loadBearerToken();
    expect(result).toBeNull();
  });

  it("is idempotent — no error if key does not exist", async () => {
    // Should not throw even if nothing was stored
    await expect(clearBearerToken()).resolves.toBeUndefined();
  });
});

// ─────────────────────────────────────────────────────────────
// loadApiBaseUrl / saveApiBaseUrl
// ─────────────────────────────────────────────────────────────

describe("loadApiBaseUrl", () => {
  it("returns null when no URL has been stored", async () => {
    const result = await loadApiBaseUrl();
    expect(result).toBeNull();
  });

  it("returns the stored URL after saveApiBaseUrl", async () => {
    await saveApiBaseUrl("http://localhost:8000");
    const result = await loadApiBaseUrl();
    expect(result).toBe("http://localhost:8000");
  });
});

describe("saveApiBaseUrl", () => {
  it("calls SecureStore.setItemAsync with the URL key", async () => {
    await saveApiBaseUrl("https://api.example.com");
    expect(SecureStore.setItemAsync).toHaveBeenCalledWith(
      SECURE_KEY_API_BASE_URL,
      "https://api.example.com"
    );
  });

  it("stores trailing-slash URLs as-is", async () => {
    await saveApiBaseUrl("http://localhost:8000/");
    const result = await loadApiBaseUrl();
    expect(result).toBe("http://localhost:8000/");
  });

  // ── URL scheme validation (ISSUE-017) ─────────────────────────

  it("accepts http:// URLs without throwing", async () => {
    await expect(saveApiBaseUrl("http://localhost:8000")).resolves.toBeUndefined();
  });

  it("accepts https:// URLs without throwing", async () => {
    await expect(saveApiBaseUrl("https://api.example.com")).resolves.toBeUndefined();
  });

  it("rejects file:// URLs and throws with readable message", async () => {
    await expect(saveApiBaseUrl("file:///etc/passwd")).rejects.toThrow(
      /must start with http:\/\/ or https:\/\//i
    );
  });

  it("rejects javascript: URLs and throws", async () => {
    await expect(saveApiBaseUrl("javascript:alert(1)")).rejects.toThrow(
      /must start with http:\/\/ or https:\/\//i
    );
  });

  it("rejects data: URLs and throws", async () => {
    await expect(saveApiBaseUrl("data:text/html,<script>")).rejects.toThrow(
      /must start with http:\/\/ or https:\/\//i
    );
  });

  it("rejects bare hostnames without scheme and throws", async () => {
    await expect(saveApiBaseUrl("localhost:8000")).rejects.toThrow(
      /must start with http:\/\/ or https:\/\//i
    );
  });

  it("does not call SecureStore when URL scheme is invalid", async () => {
    try {
      await saveApiBaseUrl("ftp://example.com");
    } catch {
      // expected
    }
    expect(SecureStore.setItemAsync).not.toHaveBeenCalled();
  });
});

// ─────────────────────────────────────────────────────────────
// useSecureStorage hook
// ─────────────────────────────────────────────────────────────

describe("useSecureStorage", () => {
  it("returns setItem, getItem, and removeItem functions", () => {
    const storage = useSecureStorage();
    expect(typeof storage.setItem).toBe("function");
    expect(typeof storage.getItem).toBe("function");
    expect(typeof storage.removeItem).toBe("function");
  });

  it("setItem stores a value retrievable by getItem", async () => {
    const storage = useSecureStorage();
    await storage.setItem("custom-key", "custom-value");
    const result = await storage.getItem("custom-key");
    expect(result).toBe("custom-value");
  });

  it("getItem returns null for non-existent key", async () => {
    const storage = useSecureStorage();
    const result = await storage.getItem("nonexistent-key-xyz");
    expect(result).toBeNull();
  });

  it("removeItem deletes a stored value", async () => {
    const storage = useSecureStorage();
    await storage.setItem("key-to-remove", "some-value");
    await storage.removeItem("key-to-remove");
    const result = await storage.getItem("key-to-remove");
    expect(result).toBeNull();
  });

  it("removeItem is idempotent — no error on missing key", async () => {
    const storage = useSecureStorage();
    await expect(storage.removeItem("missing-key")).resolves.toBeUndefined();
  });
});
