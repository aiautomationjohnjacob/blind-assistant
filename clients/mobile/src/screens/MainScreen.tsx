/**
 * MainScreen — Primary voice interaction screen
 *
 * This is the entry point for blind users. It provides:
 * - A large press-to-talk button (44x44dp minimum touch target)
 * - Spoken status announcements via expo-speech
 * - TalkBack (Android) and VoiceOver (iOS) accessible labels on every element
 * - High-contrast color scheme (WCAG AA compliant)
 * - No color-only state indicators — all state is also conveyed via text
 *
 * Per USER_STORIES.md (Sarah, NVDA user):
 *   "I want to ask what's on my screen without picking up my phone."
 *
 * Per USER_STORIES.md (Dorothy, elder user):
 *   "I need clear spoken feedback for every action I take."
 */

import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  AccessibilityInfo,
  ActivityIndicator,
  Platform,
  Pressable,
  StatusBar,
  StyleSheet,
  Text,
  View,
} from "react-native";
import * as Speech from "expo-speech";
import { type QueryResponse, getAPIClient } from "@services/api";

// ─────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────

type AssistantState =
  | "idle"       // Ready to receive input
  | "listening"  // Recording voice input (future: microphone active)
  | "thinking"   // Request sent to backend, awaiting response
  | "speaking"   // Speaking the response aloud
  | "error";     // Something went wrong — error spoken, returning to idle

// ─────────────────────────────────────────────────────────────
// Color scheme — WCAG AA compliant
// All background/text pairs have ≥4.5:1 contrast ratio
// ─────────────────────────────────────────────────────────────

const COLORS = {
  background: "#0d0d1a",        // Near-black (dark mode default)
  surface: "#1a1a2e",           // Slightly lighter card surface
  primary: "#4f8ef7",           // Blue — 4.6:1 on #0d0d1a
  primaryText: "#e8f0fe",       // Very light blue text — 12:1 on #0d0d1a
  secondaryText: "#b0bec5",     // Gray text — 4.7:1 on #0d0d1a
  error: "#ff7043",             // Orange-red — distinct from state colors
  white: "#ffffff",
  recordingActive: "#ef5350",   // Red for recording state
  transparent: "transparent",
};

// ─────────────────────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────────────────────

export function MainScreen(): React.JSX.Element {
  const [state, setState] = useState<AssistantState>("idle");
  const [lastResponse, setLastResponse] = useState<string>("");
  const [sessionId] = useState<string>(() => `session_${Date.now()}`);
  const isMounted = useRef(true);

  useEffect(() => {
    isMounted.current = true;
    // Announce app readiness to screen reader users
    announceToScreenReader("Blind Assistant is ready. Tap the button to speak.");
    return () => {
      isMounted.current = false;
      Speech.stop();
    };
  }, []);

  /** Announce a message to the screen reader (TalkBack/VoiceOver). */
  const announceToScreenReader = useCallback((message: string): void => {
    AccessibilityInfo.announceForAccessibility(message);
  }, []);

  /** Speak text aloud and announce it to the screen reader. */
  const speak = useCallback(async (text: string): Promise<void> => {
    announceToScreenReader(text);
    await new Promise<void>((resolve) => {
      Speech.speak(text, {
        language: "en-US",
        rate: 0.9,
        onDone: resolve,
        onError: resolve,
      });
    });
  }, [announceToScreenReader]);

  /** Get the current state label for accessibility (TalkBack/VoiceOver reads this). */
  const getStateLabel = useCallback((): string => {
    switch (state) {
      case "idle":
        return "Ready. Tap to speak to the assistant.";
      case "listening":
        return "Listening. Speak your request now.";
      case "thinking":
        return "Processing your request. Please wait.";
      case "speaking":
        return "Assistant is speaking.";
      case "error":
        return "An error occurred. Tap to try again.";
    }
  }, [state]);

  /** The main button action — send a text query to the backend. */
  const handleButtonPress = useCallback(async (): Promise<void> => {
    if (state === "thinking" || state === "speaking") {
      // Ignore presses while busy; TalkBack will read the hint label
      return;
    }

    setState("thinking");
    announceToScreenReader("Sending your request.");

    try {
      const client = getAPIClient();
      const response: QueryResponse = await client.query({
        message: "Hello, what can you do for me?",
        session_id: sessionId,
        speech_rate: 1.0,
        verbosity: "standard",
      });

      if (!isMounted.current) return;

      // Use spoken_text (shorter) if provided, otherwise use full text
      const textToSpeak = response.spoken_text ?? response.text;
      setLastResponse(textToSpeak);

      setState("speaking");
      await speak(textToSpeak);

      if (!isMounted.current) return;

      // If the assistant has a follow-up question, speak it
      if (response.follow_up_prompt) {
        await speak(response.follow_up_prompt);
      }

      setState("idle");
    } catch (err) {
      if (!isMounted.current) return;
      setState("error");
      const errorMessage = "Something went wrong. Please try again.";
      setLastResponse(errorMessage);
      await speak(errorMessage);
      if (isMounted.current) setState("idle");
    }
  }, [state, sessionId, speak, announceToScreenReader]);

  const isButtonDisabled = state === "thinking" || state === "speaking";
  const buttonBgColor =
    state === "listening" ? COLORS.recordingActive : COLORS.primary;

  return (
    <View
      style={styles.container}
      accessibilityLabel="Blind Assistant main screen"
    >
      <StatusBar barStyle="light-content" backgroundColor={COLORS.background} />

      {/* App title — always visible, always accessible */}
      <Text
        style={styles.title}
        accessibilityRole="header"
        accessibilityLabel="Blind Assistant"
      >
        Blind Assistant
      </Text>

      {/* Status text — announced when it changes */}
      <Text
        style={styles.statusText}
        accessibilityRole="text"
        accessibilityLiveRegion="polite"
        accessibilityLabel={getStateLabel()}
      >
        {getStateLabel()}
      </Text>

      {/* Press-to-talk button — the primary interaction element */}
      <Pressable
        style={[
          styles.button,
          { backgroundColor: buttonBgColor },
          isButtonDisabled && styles.buttonDisabled,
        ]}
        onPress={handleButtonPress}
        disabled={isButtonDisabled}
        accessibilityRole="button"
        accessibilityLabel={
          isButtonDisabled ? "Assistant is busy, please wait." : "Speak to assistant"
        }
        accessibilityHint="Double-tap to send a voice request to the assistant."
        accessibilityState={{ disabled: isButtonDisabled }}
        // Minimum 44dp touch target (Android accessibility guideline)
        hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
      >
        {state === "thinking" ? (
          <ActivityIndicator
            size="large"
            color={COLORS.white}
            accessibilityLabel="Loading"
          />
        ) : (
          <Text
            style={styles.buttonText}
            accessibilityElementsHidden
            importantForAccessibility="no"
          >
            {state === "listening" ? "🎙" : "🎤"}
          </Text>
        )}
      </Pressable>

      {/* Last response — shown as text for braille display users */}
      {lastResponse ? (
        <View
          style={styles.responseContainer}
          accessibilityRole="text"
          accessibilityLabel={`Assistant replied: ${lastResponse}`}
          accessibilityLiveRegion="polite"
        >
          <Text style={styles.responseLabel} accessibilityElementsHidden importantForAccessibility="no">
            Assistant:
          </Text>
          <Text style={styles.responseText}>{lastResponse}</Text>
        </View>
      ) : null}

      {/* Platform-specific accessibility note (not read by screen readers) */}
      <Text
        style={styles.platformHint}
        accessibilityElementsHidden
        importantForAccessibility="no"
      >
        {Platform.OS === "ios"
          ? "VoiceOver: Swipe to navigate. Double-tap to activate."
          : "TalkBack: Explore by touch. Double-tap to activate."}
      </Text>
    </View>
  );
}

// ─────────────────────────────────────────────────────────────
// Styles
// ─────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.background,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 24,
    paddingVertical: 48,
    gap: 24,
  },
  title: {
    fontSize: 28,
    fontWeight: "700",
    color: COLORS.primaryText,
    textAlign: "center",
    letterSpacing: 0.5,
  },
  statusText: {
    fontSize: 16,
    color: COLORS.secondaryText,
    textAlign: "center",
    lineHeight: 24,
    paddingHorizontal: 16,
  },
  button: {
    width: 120,
    height: 120,
    borderRadius: 60,
    alignItems: "center",
    justifyContent: "center",
    // Shadow for depth without color-only state indication
    shadowColor: COLORS.white,
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.15,
    shadowRadius: 12,
    elevation: 8, // Android shadow
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  buttonText: {
    fontSize: 48,
  },
  responseContainer: {
    backgroundColor: COLORS.surface,
    borderRadius: 12,
    padding: 16,
    width: "100%",
    maxWidth: 380,
  },
  responseLabel: {
    fontSize: 12,
    color: COLORS.secondaryText,
    marginBottom: 4,
    fontWeight: "600",
    textTransform: "uppercase",
    letterSpacing: 1,
  },
  responseText: {
    fontSize: 16,
    color: COLORS.primaryText,
    lineHeight: 24,
  },
  platformHint: {
    fontSize: 12,
    color: COLORS.secondaryText,
    textAlign: "center",
    opacity: 0.5,
    paddingTop: 8,
  },
});
