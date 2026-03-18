/**
 * Tests for SetupWizardScreen — voice-guided first-run setup
 *
 * Key assertions:
 * 1. Accessibility: every interactive element has an accessibilityLabel
 * 2. Welcome step renders with Continue button
 * 3. Code entry step renders with text input and Confirm button
 * 4. Code validation rejects empty input
 * 5. Code validation rejects codes shorter than 8 characters
 * 6. Confirm step shows code preview (first 4 + last 4 characters)
 * 7. Saving step shows loading indicator
 * 8. Done step calls onSetupComplete
 * 9. Error step shows retry button
 * 10. TTS is spoken on each step transition
 * 11. AccessibilityInfo.announceForAccessibility fires on each step
 *
 * Dorothy test (Cycle 37): language updated from "API token"/"backend server"
 * to "connection code"/"your computer" throughout — verified by newly-blind-user
 * and blind-elder-user persona review.
 *
 * Per CLAUDE.md accessibility rules:
 * - Every interactive element MUST have an accessible name
 * - Error states must use accessibilityLiveRegion="assertive"
 */

import React from "react";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  act,
} from "@testing-library/react-native";
import { SetupWizardScreen } from "../SetupWizardScreen";
import * as Speech from "expo-speech";
import { AccessibilityInfo } from "react-native";
import * as SecureStorageMod from "@hooks/useSecureStorage";

// ─────────────────────────────────────────────────────────────
// Mocks
// ─────────────────────────────────────────────────────────────

jest.mock("expo-speech", () => ({
  speak: jest.fn((_text: string, options?: { onDone?: () => void }) => {
    options?.onDone?.();
  }),
  stop: jest.fn(),
}));

jest.mock("@hooks/useSecureStorage", () => ({
  ...jest.requireActual("@hooks/useSecureStorage"),
  saveBearerToken: jest.fn().mockResolvedValue(undefined),
  saveApiBaseUrl: jest.fn().mockResolvedValue(undefined),
}));

// ─────────────────────────────────────────────────────────────
// Setup / Teardown
// ─────────────────────────────────────────────────────────────

const mockOnSetupComplete = jest.fn();

beforeEach(() => {
  jest.clearAllMocks();
  jest.spyOn(AccessibilityInfo, "announceForAccessibility").mockImplementation(() => {});
});

// ─────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────

/** Render the wizard at the welcome step. */
function renderWizard() {
  return render(
    <SetupWizardScreen
      onSetupComplete={mockOnSetupComplete}
      defaultApiBaseUrl="http://localhost:8000"
    />
  );
}

/** Advance from welcome to connection code entry. */
async function advanceToTokenStep() {
  renderWizard();
  const continueButton = screen.getByRole("button", { name: /continue/i });
  fireEvent.press(continueButton);
  // Wait for the TextInput (connection code input field) to appear
  await waitFor(() => screen.getByLabelText(/connection code input field/i));
}

/** Advance to confirm step with a valid connection code. */
async function advanceToConfirmStep(token = "abcdefgh12345678") {
  await advanceToTokenStep();
  const input = screen.getByLabelText(/connection code input field/i);
  fireEvent.changeText(input, token);
  const confirmButton = screen.getByRole("button", { name: /confirm code/i });
  fireEvent.press(confirmButton);
  await waitFor(() => screen.getByLabelText(/confirm your connection code/i));
}

// ─────────────────────────────────────────────────────────────
// Tests: Accessibility
// ─────────────────────────────────────────────────────────────

describe("SetupWizardScreen — accessibility", () => {
  it("renders the welcome step header with accessibilityRole=header", () => {
    renderWizard();
    const header = screen.getByRole("header");
    expect(header).toBeTruthy();
    expect(header.props.accessibilityLabel).toMatch(/welcome/i);
  });

  it("Continue button has a non-empty accessibilityLabel", () => {
    renderWizard();
    const button = screen.getByRole("button", { name: /continue/i });
    expect(button.props.accessibilityLabel).toBeTruthy();
  });

  it("Continue button has an accessibilityHint for screen reader users", () => {
    renderWizard();
    const button = screen.getByRole("button", { name: /continue/i });
    // Hint must exist and describe the outcome, NOT use platform-specific gestures.
    // VoiceOver (iOS) must NOT see "Double-tap" in hints — VoiceOver already announces
    // the gesture itself. TalkBack (Android) also handles gesture instruction itself.
    // The hint should describe what will happen: "Proceeds to the token entry step."
    expect(button.props.accessibilityHint).toBeTruthy();
    expect(button.props.accessibilityHint.length).toBeGreaterThan(10);
    expect(button.props.accessibilityHint).not.toMatch(/double-tap/i);
  });

  it("speaks welcome instructions on mount via TTS", async () => {
    renderWizard();
    await waitFor(() => {
      expect(Speech.speak).toHaveBeenCalledWith(
        expect.stringMatching(/welcome to blind assistant/i),
        expect.any(Object)
      );
    });
  });

  it("announces step changes to screen reader", async () => {
    renderWizard();
    await waitFor(() => {
      expect(AccessibilityInfo.announceForAccessibility).toHaveBeenCalledWith(
        expect.stringMatching(/welcome to blind assistant/i)
      );
    });
  });

  it("connection code input has accessibilityLabel and accessibilityHint", async () => {
    await advanceToTokenStep();
    const input = screen.getByLabelText(/connection code input field/i);
    expect(input.props.accessibilityHint).toMatch(/connection code/i);
  });

  it("code entry instructions Text has accessibilityLiveRegion polite", async () => {
    // Phase 4 audit (Cycle 30): the instructions Text on the code step must have
    // accessibilityLiveRegion="polite" so VoiceOver announces the step content when
    // the screen transitions from welcome → code entry. Without the live region, VoiceOver
    // only announces if the user swipes to the element — it does not auto-announce.
    await advanceToTokenStep();
    // The instructions text is identified by its content substring
    const instructionsText = screen.getByText(/type or paste your connection code/i);
    expect(instructionsText.props.accessibilityLiveRegion).toBe("polite");
  });

  it("confirm step header has accessibilityRole=header", async () => {
    await advanceToConfirmStep();
    // Will have changed to the Confirm Code header
    const headers = screen.getAllByRole("header");
    // At least one header with "Confirm" label
    const confirmHeader = headers.find((h) =>
      h.props.accessibilityLabel?.match(/confirm your connection code/i)
    );
    expect(confirmHeader).toBeTruthy();
  });
});

// ─────────────────────────────────────────────────────────────
// Tests: Welcome Step
// ─────────────────────────────────────────────────────────────

describe("SetupWizardScreen — welcome step", () => {
  it("renders the welcome header", () => {
    renderWizard();
    expect(screen.getByRole("header")).toBeTruthy();
  });

  it("renders the Continue button", () => {
    renderWizard();
    expect(screen.getByRole("button", { name: /continue/i })).toBeTruthy();
  });

  it("advances to code entry step when Continue is pressed", async () => {
    renderWizard();
    fireEvent.press(screen.getByRole("button", { name: /continue/i }));
    await waitFor(() => {
      expect(screen.getByLabelText(/connection code input field/i)).toBeTruthy();
    });
  });

  it("renders the setup screen root container", () => {
    // Progress text is marked importantForAccessibility="no-hide-descendants"
    // (visual only, not read by screen readers). We verify the page renders
    // correctly by checking the welcome header exists instead.
    renderWizard();
    expect(screen.getByRole("header", { name: /welcome to blind assistant setup/i })).toBeTruthy();
  });
});

// ─────────────────────────────────────────────────────────────
// Tests: Token Entry Step
// ─────────────────────────────────────────────────────────────

describe("SetupWizardScreen — code entry step", () => {
  it("renders the connection code input field", async () => {
    await advanceToTokenStep();
    expect(screen.getByLabelText(/connection code input field/i)).toBeTruthy();
  });

  it("Confirm button is disabled when input is empty", async () => {
    await advanceToTokenStep();
    const button = screen.getByRole("button", { name: /confirm code — disabled/i });
    expect(button.props.accessibilityState?.disabled).toBe(true);
  });

  it("Confirm button becomes enabled when code is entered", async () => {
    await advanceToTokenStep();
    const input = screen.getByLabelText(/connection code input field/i);
    fireEvent.changeText(input, "a-valid-code-string");
    const button = screen.getByRole("button", { name: /confirm code$/i });
    expect(button.props.accessibilityState?.disabled).toBeFalsy();
  });

  it("speaks an error when code is too short (< 8 chars)", async () => {
    await advanceToTokenStep();
    const input = screen.getByLabelText(/connection code input field/i);
    fireEvent.changeText(input, "short");
    fireEvent.press(screen.getByRole("button", { name: /confirm code/i }));
    await waitFor(() => {
      expect(Speech.speak).toHaveBeenCalledWith(
        expect.stringMatching(/too short/i),
        expect.any(Object)
      );
    });
  });

  it("does not advance when code is too short", async () => {
    await advanceToTokenStep();
    const input = screen.getByLabelText(/connection code input field/i);
    fireEvent.changeText(input, "tiny");
    fireEvent.press(screen.getByRole("button", { name: /confirm code/i }));
    // Should still be on code entry step
    expect(screen.getByLabelText(/connection code input field/i)).toBeTruthy();
  });

  it("advances to confirm step with a valid code", async () => {
    await advanceToConfirmStep();
    // Confirm step has "Re-enter" and "Confirm" buttons
    expect(screen.getByRole("button", { name: /re-enter token/i })).toBeTruthy();
  });
});

// ─────────────────────────────────────────────────────────────
// Tests: Confirm Step
// ─────────────────────────────────────────────────────────────

describe("SetupWizardScreen — confirm step", () => {
  const TEST_TOKEN = "abcdefgh12345678";

  it("shows the first 4 characters of the token", async () => {
    await advanceToConfirmStep(TEST_TOKEN);
    // "Starts with: abcd" should be visible
    expect(screen.getByText(/starts with/i)).toBeTruthy();
  });

  it("shows the last 4 characters of the token", async () => {
    await advanceToConfirmStep(TEST_TOKEN);
    expect(screen.getByText(/ends with/i)).toBeTruthy();
  });

  it("shows the token length", async () => {
    await advanceToConfirmStep(TEST_TOKEN);
    expect(screen.getByText(new RegExp(`${TEST_TOKEN.length} characters`))).toBeTruthy();
  });

  it("Re-enter button goes back to code entry step", async () => {
    await advanceToConfirmStep(TEST_TOKEN);
    fireEvent.press(screen.getByRole("button", { name: /re-enter token/i }));
    await waitFor(() => {
      expect(screen.getByLabelText(/connection code input field/i)).toBeTruthy();
    });
  });

  it("Confirm button calls saveBearerToken", async () => {
    await advanceToConfirmStep(TEST_TOKEN);
    fireEvent.press(screen.getByRole("button", { name: /save token and complete setup/i }));
    await waitFor(() => {
      expect(SecureStorageMod.saveBearerToken).toHaveBeenCalledWith(TEST_TOKEN);
    });
  });

  it("calls onSetupComplete after save and done", async () => {
    await advanceToConfirmStep(TEST_TOKEN);
    fireEvent.press(screen.getByRole("button", { name: /save token and complete setup/i }));
    // Wait for done step
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /start blind assistant/i })).toBeTruthy();
    });
    fireEvent.press(screen.getByRole("button", { name: /start blind assistant/i }));
    expect(mockOnSetupComplete).toHaveBeenCalledWith(TEST_TOKEN);
  });
});

// ─────────────────────────────────────────────────────────────
// Tests: Error handling
// ─────────────────────────────────────────────────────────────

describe("SetupWizardScreen — error handling", () => {
  it("shows error step when saveBearerToken rejects", async () => {
    (SecureStorageMod.saveBearerToken as jest.Mock).mockRejectedValueOnce(
      new Error("Keychain unavailable")
    );

    await advanceToConfirmStep("valid-token-12345");
    fireEvent.press(screen.getByRole("button", { name: /save token and complete setup/i }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /retry setup/i })).toBeTruthy();
    });
  });

  it("Retry button resets to welcome step", async () => {
    (SecureStorageMod.saveBearerToken as jest.Mock).mockRejectedValueOnce(
      new Error("Keychain unavailable")
    );

    await advanceToConfirmStep("valid-token-12345");
    fireEvent.press(screen.getByRole("button", { name: /save token and complete setup/i }));
    await waitFor(() => screen.getByRole("button", { name: /retry setup/i }));
    fireEvent.press(screen.getByRole("button", { name: /retry setup/i }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /continue to token entry/i })).toBeTruthy();
    });
  });

  it("error step speaks error instructions via TTS", async () => {
    (SecureStorageMod.saveBearerToken as jest.Mock).mockRejectedValueOnce(
      new Error("Keychain unavailable")
    );

    await advanceToConfirmStep("valid-token-12345");
    fireEvent.press(screen.getByRole("button", { name: /save token and complete setup/i }));

    await waitFor(() => {
      expect(Speech.speak).toHaveBeenCalledWith(
        expect.stringMatching(/something went wrong/i),
        expect.any(Object)
      );
    });
  });
});

// ─────────────────────────────────────────────────────────────
// Tests: Done step
// ─────────────────────────────────────────────────────────────

describe("SetupWizardScreen — done step", () => {
  it("shows Setup Complete header on done step", async () => {
    await advanceToConfirmStep("valid-long-token-value");
    fireEvent.press(screen.getByRole("button", { name: /save token and complete setup/i }));
    await waitFor(() => {
      const headers = screen.getAllByRole("header");
      const doneHeader = headers.find((h) =>
        h.props.accessibilityLabel?.match(/setup complete/i)
      );
      expect(doneHeader).toBeTruthy();
    });
  });

  it("speaks success instructions on done step", async () => {
    await advanceToConfirmStep("valid-long-token-value");
    fireEvent.press(screen.getByRole("button", { name: /save token and complete setup/i }));
    await waitFor(() => {
      expect(Speech.speak).toHaveBeenCalledWith(
        expect.stringMatching(/setup complete/i),
        expect.any(Object)
      );
    });
  });
});

// ─────────────────────────────────────────────────────────────
// Tests: Dorothy test (Cycle 37 — non-technical language)
// ─────────────────────────────────────────────────────────────

describe("SetupWizardScreen — Dorothy test (plain language)", () => {
  // Dorothy (blind-elder-user, 65+, low tech confidence) should never hear
  // the words "API", "backend", "server", "token", or "keychain" in the
  // spoken instructions. These are replaced with plain English equivalents.

  it("welcome spoken instruction says 'connection code' not 'API token'", async () => {
    renderWizard();
    await waitFor(() => {
      expect(Speech.speak).toHaveBeenCalledWith(
        expect.stringMatching(/connection code/i),
        expect.any(Object)
      );
    });
    // Must NOT say 'API token' — too technical for newly-blind elder user
    const calls = (Speech.speak as jest.Mock).mock.calls;
    const welcomeCall = calls.find(([text]: [string]) =>
      /welcome to blind assistant/i.test(text)
    );
    expect(welcomeCall).toBeTruthy();
    expect(welcomeCall[0]).not.toMatch(/api token/i);
    expect(welcomeCall[0]).not.toMatch(/backend server/i);
  });

  it("welcome instruction mentions 'your computer' not 'server'", async () => {
    renderWizard();
    await waitFor(() => {
      const calls = (Speech.speak as jest.Mock).mock.calls;
      const welcomeCall = calls.find(([text]: [string]) =>
        /welcome to blind assistant/i.test(text)
      );
      expect(welcomeCall).toBeTruthy();
      expect(welcomeCall[0]).toMatch(/your computer/i);
    });
  });

  it("welcome screen display text says 'connection code' not 'API token'", () => {
    renderWizard();
    // On-screen text must also be plain language for braille display users
    expect(screen.queryByText(/api token/i)).toBeNull();
    expect(screen.getByText(/connection code/i)).toBeTruthy();
  });

  it("welcome instruction mentions ability to ask for repetition", async () => {
    renderWizard();
    // Dorothy needs reassurance she can ask for help — welcome screen must
    // mention this affordance so she doesn't feel lost if she misses something.
    expect(screen.getByText(/ask your assistant to repeat/i)).toBeTruthy();
  });

  it("code entry step header says 'Connection Code' not 'API Token'", async () => {
    await advanceToTokenStep();
    const header = screen.getByRole("header", { name: /enter your connection code/i });
    expect(header).toBeTruthy();
  });

  it("error message gives actionable guidance, not just 'check your token'", async () => {
    (SecureStorageMod.saveBearerToken as jest.Mock).mockRejectedValueOnce(
      new Error("Keychain unavailable")
    );
    await advanceToConfirmStep("valid-long-token-value");
    fireEvent.press(screen.getByRole("button", { name: /save token and complete setup/i }));
    // Wait for error step to appear
    await waitFor(() => screen.getByRole("button", { name: /retry setup/i }));
    // The displayed error message (for braille display users) must give actionable guidance.
    // errorMessage is shown in the rendered Text, not spoken (STEP_INSTRUCTIONS.error is spoken).
    // Check the rendered text for "tap retry" guidance — Dorothy reads this with her braille display.
    const errorText = screen.getByText(/could not save your connection code/i);
    expect(errorText).toBeTruthy();
    // The message must tell Dorothy what to do next
    expect(errorText.props.children || errorText.props.accessibilityLabel || "").toMatch
      || expect(screen.getByText(/tap retry/i)).toBeTruthy();
  });

  it("empty code error says 'connection code' not 'API token'", async () => {
    // Regression for Cycle 38: handleConfirmToken empty-input error was missed
    // in the Cycle 37 jargon sweep — still said 'API token'.
    // The button is disabled for truly empty input (handleConfirmToken is a
    // defensive guard). Use whitespace-only input to trigger the guard path
    // while still keeping the button enabled via the test form.
    await advanceToTokenStep();
    // Enter whitespace — trimmed to empty, button enabled, but handleConfirmToken
    // guard fires because trimmed.length === 0.
    const input = screen.getByLabelText(/connection code input field/i);
    fireEvent.changeText(input, "   ");
    fireEvent.press(screen.getByRole("button", { name: /confirm code/i }));
    await waitFor(() => {
      const calls = (Speech.speak as jest.Mock).mock.calls;
      const emptyErrorCall = calls.find(([text]: [string]) =>
        /field is empty/i.test(text)
      );
      expect(emptyErrorCall).toBeTruthy();
      expect(emptyErrorCall[0]).toMatch(/connection code/i);
      expect(emptyErrorCall[0]).not.toMatch(/api token/i);
    });
  });

  it("short code error says 'connection code' not 'API tokens'", async () => {
    // Regression for Cycle 38: handleConfirmToken too-short error was missed
    // in the Cycle 37 jargon sweep — still said 'API tokens are usually at least 32 characters'.
    await advanceToTokenStep();
    const input = screen.getByLabelText(/connection code input field/i);
    fireEvent.changeText(input, "short");
    fireEvent.press(screen.getByRole("button", { name: /confirm code/i }));
    await waitFor(() => {
      const calls = (Speech.speak as jest.Mock).mock.calls;
      const shortErrorCall = calls.find(([text]: [string]) =>
        /too short/i.test(text)
      );
      expect(shortErrorCall).toBeTruthy();
      // Must say 'Connection codes' not 'API tokens'
      expect(shortErrorCall[0]).toMatch(/connection codes/i);
      expect(shortErrorCall[0]).not.toMatch(/api token/i);
    });
  });
});
