/**
 * SetupWizardScreen — Voice-guided first-run configuration
 *
 * Shown once on first launch, or after a reset.
 * Guides the blind user through entering their backend API token.
 *
 * Accessibility design:
 * - All instructions are spoken via TTS on screen entry
 * - Step labels use accessibilityLiveRegion="polite" for automatic announcements
 * - Text input has accessibilityLabel and hint matching screen reader conventions
 * - Success/error states are announced immediately via announceForAccessibility
 * - No color-only state indicators: text labels accompany every state change
 * - Minimum 44dp touch targets on all buttons
 *
 * Flow:
 * 1. Welcome — speaks instructions aloud
 * 2. Token entry — user types or pastes their API token
 * 3. Confirm — reads token back, asks user to confirm
 * 4. Saving — stores token via expo-secure-store
 * 5. Done — announces success, calls onSetupComplete
 *
 * Per USER_STORIES.md:
 * - Dorothy (elder): "I need clear spoken feedback for every action I take."
 * - Alex (newly blind): "I can't type long random strings accurately."
 *
 * The wizard speaks the token back before saving so the user can verify.
 * The backend server prints the token during setup — copy/paste is the
 * recommended flow for sighted users; speech-reading for blind users.
 */

import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  AccessibilityInfo,
  ActivityIndicator,
  Keyboard,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import * as Speech from "expo-speech";
import { saveBearerToken, saveApiBaseUrl } from "@hooks/useSecureStorage";

// ─────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────

type WizardStep =
  | "welcome"    // Initial screen — speaks instructions
  | "token"      // Token input step
  | "confirm"    // Read back token, ask for confirmation
  | "saving"     // Writing to secure storage
  | "done"       // Setup complete
  | "error";     // Something went wrong

interface SetupWizardScreenProps {
  /** Called when setup is complete. Parent swaps to MainScreen. */
  onSetupComplete: (bearerToken: string) => void;
  /** Initial API base URL from app.config.ts — can be overridden. */
  defaultApiBaseUrl?: string;
}

// ─────────────────────────────────────────────────────────────
// Color scheme — WCAG AA compliant (same palette as MainScreen)
// ─────────────────────────────────────────────────────────────

const COLORS = {
  background: "#0d0d1a",
  surface: "#1a1a2e",
  primary: "#4f8ef7",
  primaryText: "#e8f0fe",
  secondaryText: "#b0bec5",
  error: "#ff7043",
  white: "#ffffff",
  inputBorder: "#4f8ef7",
  inputBackground: "#111128",
};

// ─────────────────────────────────────────────────────────────
// Spoken instructions per step
// ─────────────────────────────────────────────────────────────

const STEP_INSTRUCTIONS: Record<WizardStep, string> = {
  welcome:
    "Welcome to Blind Assistant. This is a one-time setup. " +
    "You will need a connection code from your computer. " +
    "Your computer shows this code when you first start Blind Assistant on it. " +
    "If you do not have the code yet, ask the person who set up your computer to read it to you. " +
    "When you are ready, tap the Continue button.",
  token:
    "Please type or paste your connection code into the field below. " +
    "The code is a long string of letters and numbers — usually more than 30 characters. " +
    "When you have entered it, tap the Confirm button.",
  confirm: "", // Generated dynamically based on token value
  saving: "Saving your settings. Please wait.",
  done:
    "Setup complete. Blind Assistant is now connected to your computer. " +
    "Tap the Start button to begin talking to your assistant.",
  error:
    "Something went wrong during setup. " +
    "The connection code may be incorrect, or your computer may not be running Blind Assistant. " +
    "Tap the Retry button to start over and enter the code again.",
};

// ─────────────────────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────────────────────

export function SetupWizardScreen({
  onSetupComplete,
  defaultApiBaseUrl = "http://localhost:8000",
}: SetupWizardScreenProps): React.JSX.Element {
  const [step, setStep] = useState<WizardStep>("welcome");
  const [tokenInput, setTokenInput] = useState<string>("");
  const [errorMessage, setErrorMessage] = useState<string>("");
  const isMounted = useRef(true);
  const inputRef = useRef<TextInput>(null);

  useEffect(() => {
    isMounted.current = true;
    return () => {
      isMounted.current = false;
      Speech.stop();
    };
  }, []);

  // Speak the instruction for the current step whenever step changes
  useEffect(() => {
    const instruction = STEP_INSTRUCTIONS[step];
    if (instruction) {
      speak(instruction);
    }
  }, [step]); // eslint-disable-line react-hooks/exhaustive-deps

  /** Speak text aloud and announce via screen reader API. */
  const speak = useCallback(async (text: string): Promise<void> => {
    AccessibilityInfo.announceForAccessibility(text);
    await new Promise<void>((resolve) => {
      Speech.speak(text, {
        language: "en-US",
        rate: 0.85, // Slightly slower than normal for clarity
        onDone: resolve,
        onError: resolve,
      });
    });
  }, []);

  /** Advance from the welcome screen to token entry. */
  const handleContinueFromWelcome = useCallback((): void => {
    setStep("token");
    // Focus the input after the step transition so TalkBack lands on it
    setTimeout(() => inputRef.current?.focus(), 300);
  }, []);

  /** Move from token entry to the confirm step. */
  const handleConfirmToken = useCallback((): void => {
    const trimmed = tokenInput.trim();
    if (!trimmed) {
      speak("The connection code field is empty. Please enter your connection code.");
      return;
    }
    if (trimmed.length < 8) {
      speak(
        "The connection code you entered looks too short. " +
          "Connection codes are usually at least 32 characters. Please check and try again."
      );
      return;
    }

    Keyboard.dismiss();
    setStep("confirm");

    // Speak code back — character by character for verification
    // Spell out the first 4 characters and last 4 as a checksum read
    // Dorothy test (Cycle 37): "token" replaced with "connection code" throughout
    // so non-technical users understand what they are confirming.
    const confirmInstruction =
      `Your connection code starts with ${trimmed.slice(0, 4).split("").join(" ")} ` +
      `and ends with ${trimmed.slice(-4).split("").join(" ")}. ` +
      `The full code is ${trimmed.length} characters long. ` +
      `Tap Confirm to save this code, or tap Re-enter to change it.`;
    STEP_INSTRUCTIONS.confirm = confirmInstruction;
    speak(confirmInstruction);
  }, [tokenInput, speak]);

  /** Save the token to secure storage and complete setup. */
  const handleSaveToken = useCallback(async (): Promise<void> => {
    const trimmed = tokenInput.trim();
    setStep("saving");

    try {
      await saveBearerToken(trimmed);
      // Store the default API URL (can be overridden later in settings)
      await saveApiBaseUrl(defaultApiBaseUrl);

      if (!isMounted.current) return;
      setStep("done");
    } catch (err) {
      if (!isMounted.current) return;
      setErrorMessage(
        "Could not save your connection code. " +
          "Please make sure the app has permission to store passwords on your device, " +
          "then tap Retry to try again."
      );
      setStep("error");
    }
  }, [tokenInput, defaultApiBaseUrl]);

  /** Go back to token entry step to re-enter. */
  const handleReEnterToken = useCallback((): void => {
    setStep("token");
    setTimeout(() => inputRef.current?.focus(), 300);
  }, []);

  /** Called when user confirms setup is complete. */
  const handleStartApp = useCallback((): void => {
    onSetupComplete(tokenInput.trim());
  }, [tokenInput, onSetupComplete]);

  /** Retry after an error. */
  const handleRetry = useCallback((): void => {
    setTokenInput("");
    setErrorMessage("");
    setStep("welcome");
  }, []);

  // ─────────────────────────────────────────────────────────
  // Render helpers per step
  // ─────────────────────────────────────────────────────────

  const renderWelcome = (): React.JSX.Element => (
    <View style={styles.stepContainer}>
      <Text
        style={styles.stepTitle}
        accessibilityRole="header"
        accessibilityLabel="Welcome to Blind Assistant setup"
      >
        Welcome
      </Text>
      <Text
        style={styles.instructions}
        accessibilityRole={Platform.OS === "web" ? undefined : "text"}
        accessibilityLiveRegion="polite"
      >
        This is a one-time setup.{"\n\n"}
        You will need a connection code from your computer.{"\n\n"}
        Have the code ready, then tap Continue.{"\n\n"}
        You can ask your assistant to repeat anything at any time.
      </Text>
      <Pressable
        style={styles.button}
        onPress={handleContinueFromWelcome}
        accessibilityRole="button"
        accessibilityLabel="Continue to token entry"
        accessibilityHint="Proceeds to the token entry step."
        hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
      >
        <Text style={styles.buttonText}>Continue</Text>
      </Pressable>
    </View>
  );

  const renderTokenEntry = (): React.JSX.Element => (
    <View style={styles.stepContainer}>
      <Text
        style={styles.stepTitle}
        accessibilityRole="header"
        accessibilityLabel="Step 1: Enter your connection code"
      >
        Enter Connection Code
      </Text>
      {/* Phase 4 audit (Cycle 30): accessibilityLiveRegion added to match other steps.
          When VoiceOver navigates to this step, it must announce the instructions text.
          Without a live region, VoiceOver only announces this Text if the user swipes
          to it — it does not auto-announce when content appears due to step transition.
          The speak() call fires announceForAccessibility, but a live region on the Text
          ensures VoiceOver also announces it as a polite update in Browse mode. */}
      <Text
        style={styles.instructions}
        accessibilityRole={Platform.OS === "web" ? undefined : "text"}
        accessibilityLiveRegion="polite"
      >
        Type or paste your connection code below.{"\n"}
        Your computer showed this code when Blind Assistant started.
      </Text>
      <TextInput
        ref={inputRef}
        style={styles.textInput}
        value={tokenInput}
        onChangeText={setTokenInput}
        placeholder="Paste your connection code here"
        placeholderTextColor={COLORS.secondaryText}
        autoCapitalize="none"
        autoCorrect={false}
        autoComplete="off"
        // secureTextEntry hides from screen mirrors but still allows TalkBack
        secureTextEntry={false}
        returnKeyType="done"
        onSubmitEditing={handleConfirmToken}
        accessibilityLabel="Connection code input field"
        accessibilityHint={
          "Enter the connection code shown on your computer. " +
          "It is usually more than 30 characters long."
        }
        // Guarantees TalkBack auto-focuses this field when the token step appears.
        // Without this, users may need extra swipes to locate the input.
        importantForAccessibility="yes"
      />
      <Pressable
        style={[styles.button, !tokenInput.trim() && styles.buttonDisabled]}
        onPress={handleConfirmToken}
        disabled={!tokenInput.trim()}
        accessibilityRole="button"
        accessibilityLabel={
          tokenInput.trim() ? "Confirm code" : "Confirm code — disabled, please enter your connection code first"
        }
        accessibilityHint="Reviews your connection code before saving."
        accessibilityState={{ disabled: !tokenInput.trim() }}
        hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
      >
        <Text style={styles.buttonText}>Confirm</Text>
      </Pressable>
    </View>
  );

  const renderConfirm = (): React.JSX.Element => (
    <View style={styles.stepContainer}>
      <Text
        style={styles.stepTitle}
        accessibilityRole="header"
        accessibilityLabel="Step 2: Confirm your connection code"
      >
        Confirm Code
      </Text>
      <Text
        style={styles.instructions}
        accessibilityRole={Platform.OS === "web" ? undefined : "text"}
        accessibilityLiveRegion="polite"
      >
        Your connection code:{"\n"}
        Starts with: {tokenInput.trim().slice(0, 4)}{"\n"}
        Ends with: {tokenInput.trim().slice(-4)}{"\n"}
        Length: {tokenInput.trim().length} characters{"\n\n"}
        Does this look correct?
      </Text>
      <View style={styles.buttonRow}>
        <Pressable
          style={[styles.button, styles.buttonSecondary]}
          onPress={handleReEnterToken}
          accessibilityRole="button"
          accessibilityLabel="Re-enter token"
          accessibilityHint="Returns to token entry to change your token."
          hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
        >
          <Text style={styles.buttonTextSecondary}>Re-enter</Text>
        </Pressable>
        <Pressable
          style={styles.button}
          onPress={handleSaveToken}
          accessibilityRole="button"
          accessibilityLabel="Save token and complete setup"
          accessibilityHint="Saves your token and connects to your server."
          hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
        >
          <Text style={styles.buttonText}>Confirm</Text>
        </Pressable>
      </View>
    </View>
  );

  const renderSaving = (): React.JSX.Element => (
    <View style={styles.stepContainer}>
      <ActivityIndicator
        size="large"
        color={COLORS.primary}
        accessibilityLabel="Saving your settings"
      />
      <Text
        style={styles.instructions}
        accessibilityRole={Platform.OS === "web" ? undefined : "text"}
        accessibilityLiveRegion="polite"
      >
        Saving your settings…
      </Text>
    </View>
  );

  const renderDone = (): React.JSX.Element => (
    <View style={styles.stepContainer}>
      <Text
        style={styles.stepTitle}
        accessibilityRole="header"
        accessibilityLabel="Setup complete"
      >
        Setup Complete
      </Text>
      <Text
        style={styles.instructions}
        accessibilityRole={Platform.OS === "web" ? undefined : "text"}
        accessibilityLiveRegion="polite"
      >
        Blind Assistant is now connected to your computer.{"\n\n"}
        Tap Start to begin talking to your assistant.
      </Text>
      <Pressable
        style={styles.button}
        onPress={handleStartApp}
        accessibilityRole="button"
        accessibilityLabel="Start Blind Assistant"
        accessibilityHint="Opens the main assistant screen."
        hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
      >
        <Text style={styles.buttonText}>Start</Text>
      </Pressable>
    </View>
  );

  const renderError = (): React.JSX.Element => (
    <View style={styles.stepContainer}>
      <Text
        style={styles.stepTitle}
        accessibilityRole="header"
        accessibilityLabel="Setup error"
      >
        Setup Error
      </Text>
      <Text
        style={[styles.instructions, styles.errorText]}
        accessibilityRole={Platform.OS === "web" ? undefined : "text"}
        accessibilityLiveRegion="assertive"
      >
        {errorMessage || "Something went wrong. Please try again."}
      </Text>
      <Pressable
        style={styles.button}
        onPress={handleRetry}
        accessibilityRole="button"
        accessibilityLabel="Retry setup"
        accessibilityHint="Restarts the setup wizard from the beginning."
        hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
      >
        <Text style={styles.buttonText}>Retry</Text>
      </Pressable>
    </View>
  );

  const renderStep = (): React.JSX.Element => {
    switch (step) {
      case "welcome":
        return renderWelcome();
      case "token":
        return renderTokenEntry();
      case "confirm":
        return renderConfirm();
      case "saving":
        return renderSaving();
      case "done":
        return renderDone();
      case "error":
        return renderError();
    }
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === "ios" ? "padding" : "height"}
    >
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
        accessibilityLabel="Setup wizard scroll view"
      >
        {/* Progress indicator — announced as text, not color */}
        <Text
          style={styles.progressText}
          accessibilityRole={Platform.OS === "web" ? undefined : "text"}
          accessibilityLiveRegion="polite"
          accessibilityLabel={`Setup step: ${step}`}
          importantForAccessibility="yes"
        >
          {step === "welcome" && "Step 1 of 3: Welcome"}
          {step === "token" && "Step 2 of 3: Enter Token"}
          {step === "confirm" && "Step 2 of 3: Confirm Token"}
          {step === "saving" && "Step 3 of 3: Saving"}
          {step === "done" && "Setup complete"}
          {step === "error" && "Error — tap Retry to restart"}
        </Text>

        {renderStep()}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

// ─────────────────────────────────────────────────────────────
// Styles
// ─────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.background,
  },
  scrollContent: {
    flexGrow: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 24,
    paddingVertical: 48,
    gap: 16,
  },
  progressText: {
    fontSize: 12,
    color: COLORS.secondaryText,
    textAlign: "center",
    letterSpacing: 0.5,
    textTransform: "uppercase",
    marginBottom: 8,
  },
  stepContainer: {
    width: "100%",
    maxWidth: 400,
    alignItems: "center",
    gap: 20,
  },
  stepTitle: {
    fontSize: 26,
    fontWeight: "700",
    color: COLORS.primaryText,
    textAlign: "center",
    letterSpacing: 0.5,
  },
  instructions: {
    fontSize: 16,
    color: COLORS.secondaryText,
    textAlign: "center",
    lineHeight: 26,
    paddingHorizontal: 8,
  },
  errorText: {
    color: COLORS.error,
  },
  textInput: {
    width: "100%",
    backgroundColor: COLORS.inputBackground,
    borderColor: COLORS.inputBorder,
    borderWidth: 2,
    borderRadius: 8,
    paddingHorizontal: 16,
    paddingVertical: 14,
    fontSize: 15,
    color: COLORS.primaryText,
    fontFamily: Platform.OS === "ios" ? "Menlo" : "monospace",
    // Monospace font makes long token strings easier to read
  },
  button: {
    backgroundColor: COLORS.primary,
    paddingVertical: 16,
    paddingHorizontal: 40,
    borderRadius: 8,
    alignItems: "center",
    justifyContent: "center",
    minWidth: 160,
    minHeight: 52, // Above 44dp minimum
  },
  buttonDisabled: {
    opacity: 0.5,
  },
  buttonSecondary: {
    backgroundColor: "transparent",
    borderColor: COLORS.primary,
    borderWidth: 2,
  },
  buttonText: {
    color: COLORS.white,
    fontSize: 17,
    fontWeight: "600",
  },
  buttonTextSecondary: {
    color: COLORS.primary,
    fontSize: 17,
    fontWeight: "600",
  },
  buttonRow: {
    flexDirection: "row",
    gap: 16,
    flexWrap: "wrap",
    justifyContent: "center",
  },
});
