/**
 * App entry point (Expo Router v3 style)
 *
 * On first launch (no token in secure storage):
 *   Shows SetupWizardScreen so the user can configure their backend token.
 *
 * On returning launch (token found in secure storage):
 *   Configures the API client immediately and shows MainScreen.
 *
 * Backend URL:
 * - Development: localhost:8000 (set EXPO_PUBLIC_API_BASE_URL in app.config.ts)
 * - Production: stored in secure storage after setup wizard completes
 *
 * Security: the bearer token is NEVER stored in JS constants, .env files,
 * or AsyncStorage — only in the device's encrypted keychain via expo-secure-store.
 */
import React, { useEffect, useState } from "react";
import Constants from "expo-constants";
import { ActivityIndicator, StyleSheet, View } from "react-native";
import { configureAPIClient } from "@services/api";
import { MainScreen } from "@screens/MainScreen";
import { SetupWizardScreen } from "@screens/SetupWizardScreen";
import {
  loadBearerToken,
  loadApiBaseUrl,
} from "@hooks/useSecureStorage";

// ─────────────────────────────────────────────────────────────
// App states
// ─────────────────────────────────────────────────────────────

type AppState =
  | "loading"   // Checking secure storage — show spinner
  | "setup"     // No token found — show wizard
  | "ready";    // Token loaded — show main screen

// Fallback API base URL from Expo config (set in app.config.ts extra.apiBaseUrl)
const DEFAULT_API_BASE_URL: string =
  (Constants.expoConfig?.extra?.apiBaseUrl as string | undefined) ??
  "http://localhost:8000";

// ─────────────────────────────────────────────────────────────
// Root component
// ─────────────────────────────────────────────────────────────

export default function App(): React.JSX.Element {
  const [appState, setAppState] = useState<AppState>("loading");

  useEffect(() => {
    // On mount, check if a bearer token is stored from a previous session.
    // This is the ONLY place we load from secure storage at startup.
    checkStoredCredentials();
  }, []);

  /**
   * Load stored credentials from the device keychain.
   * If a token exists, configure the API client and go straight to main screen.
   * If not, show the setup wizard.
   */
  const checkStoredCredentials = async (): Promise<void> => {
    try {
      const [storedToken, storedApiUrl] = await Promise.all([
        loadBearerToken(),
        loadApiBaseUrl(),
      ]);

      if (storedToken) {
        // Credentials exist — configure and go directly to the main screen
        const apiBaseUrl = storedApiUrl ?? DEFAULT_API_BASE_URL;
        configureAPIClient(apiBaseUrl, storedToken);
        setAppState("ready");
      } else {
        // No token — first run or after reset
        setAppState("setup");
      }
    } catch {
      // If secure storage read fails (e.g. device has no secure enclave support),
      // fall back to the setup wizard so the user can still configure the app.
      setAppState("setup");
    }
  };

  /**
   * Called by SetupWizardScreen when the user completes setup.
   * At this point the token is already persisted in secure storage
   * by the wizard; we just configure the API client and go to main screen.
   */
  const handleSetupComplete = (bearerToken: string): void => {
    configureAPIClient(DEFAULT_API_BASE_URL, bearerToken);
    setAppState("ready");
  };

  // ─────────────────────────────────────────────────────────
  // Render
  // ─────────────────────────────────────────────────────────

  if (appState === "loading") {
    return (
      <View
        style={styles.loadingContainer}
        accessibilityLabel="Loading Blind Assistant"
      >
        <ActivityIndicator
          size="large"
          color="#4f8ef7"
          accessibilityLabel="Loading"
        />
      </View>
    );
  }

  if (appState === "setup") {
    return (
      <SetupWizardScreen
        onSetupComplete={handleSetupComplete}
        defaultApiBaseUrl={DEFAULT_API_BASE_URL}
      />
    );
  }

  // appState === "ready"
  return <MainScreen />;
}

const styles = StyleSheet.create({
  loadingContainer: {
    flex: 1,
    backgroundColor: "#0d0d1a",
    alignItems: "center",
    justifyContent: "center",
  },
});
