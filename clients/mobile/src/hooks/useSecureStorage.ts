/**
 * useSecureStorage — thin wrapper around expo-secure-store
 *
 * Provides async read/write/delete for sensitive values (bearer token,
 * API base URL). Uses expo-secure-store which encrypts values using the
 * device's secure enclave (iOS Keychain / Android Keystore).
 *
 * SECURITY: values stored here are never logged, never sent to analytics,
 * and never included in crash reports.
 */

import * as SecureStore from "expo-secure-store";

/** Storage key for the API bearer token. */
export const SECURE_KEY_BEARER_TOKEN = "blind_assistant_bearer_token";

/** Storage key for the custom API base URL (overrides the default). */
export const SECURE_KEY_API_BASE_URL = "blind_assistant_api_base_url";

export interface SecureStorageResult {
  /** Store a string value under the given key. Rejects on failure. */
  setItem: (key: string, value: string) => Promise<void>;
  /** Read a string value. Returns null if key does not exist. */
  getItem: (key: string) => Promise<string | null>;
  /** Delete a stored value. No-op if the key does not exist. */
  removeItem: (key: string) => Promise<void>;
}

/**
 * Returns secure storage operations backed by expo-secure-store.
 *
 * This is a plain-function hook (no React state) — safe to call outside
 * components and inside async event handlers.
 */
export function useSecureStorage(): SecureStorageResult {
  const setItem = async (key: string, value: string): Promise<void> => {
    // expo-secure-store encrypts the value before persisting
    await SecureStore.setItemAsync(key, value);
  };

  const getItem = async (key: string): Promise<string | null> => {
    return SecureStore.getItemAsync(key);
  };

  const removeItem = async (key: string): Promise<void> => {
    await SecureStore.deleteItemAsync(key);
  };

  return { setItem, getItem, removeItem };
}

/**
 * Read the stored bearer token.
 * Returns null if no token has been saved yet (first-run case).
 */
export async function loadBearerToken(): Promise<string | null> {
  return SecureStore.getItemAsync(SECURE_KEY_BEARER_TOKEN);
}

/**
 * Persist the bearer token in secure storage.
 * Called at the end of the setup wizard after the user confirms their token.
 */
export async function saveBearerToken(token: string): Promise<void> {
  await SecureStore.setItemAsync(SECURE_KEY_BEARER_TOKEN, token);
}

/**
 * Delete the stored bearer token (e.g. on sign-out or reset).
 * After this call, the next app launch will show the setup wizard again.
 */
export async function clearBearerToken(): Promise<void> {
  await SecureStore.deleteItemAsync(SECURE_KEY_BEARER_TOKEN);
}

/**
 * Read the custom API base URL if the user has configured one.
 * Returns null if the user has not set one (default from app.config.ts is used).
 */
export async function loadApiBaseUrl(): Promise<string | null> {
  return SecureStore.getItemAsync(SECURE_KEY_API_BASE_URL);
}

/**
 * Persist a custom API base URL (for users pointing at a self-hosted backend).
 */
export async function saveApiBaseUrl(url: string): Promise<void> {
  await SecureStore.setItemAsync(SECURE_KEY_API_BASE_URL, url);
}
