/**
 * App entry point (Expo Router v3 style)
 *
 * This configures the API client with the backend URL, then renders the main screen.
 *
 * Backend URL:
 * - Development: localhost:8000 (set EXPO_PUBLIC_API_BASE_URL to override)
 * - Production: will be set via environment variable pointing to cloud deployment
 *
 * No authentication token is set here — the app will need a token setup flow
 * (Voice-guided setup wizard) to configure the bearer token. For development,
 * the backend can run with api_auth_disabled=true in config.yaml.
 */
import React, { useEffect } from "react";
import Constants from "expo-constants";
import { configureAPIClient } from "@services/api";
import { MainScreen } from "@screens/MainScreen";

// Extract API base URL from Expo config (set in app.config.ts extra.apiBaseUrl)
const API_BASE_URL: string =
  (Constants.expoConfig?.extra?.apiBaseUrl as string | undefined) ??
  "http://localhost:8000";

// TODO: Load bearer token from secure storage (expo-secure-store) after setup wizard
const BEARER_TOKEN: string | null = null;

export default function App(): React.JSX.Element {
  useEffect(() => {
    // Configure the singleton API client once at startup
    configureAPIClient(API_BASE_URL, BEARER_TOKEN);
  }, []);

  return <MainScreen />;
}
