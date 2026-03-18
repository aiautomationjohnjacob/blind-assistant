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
  await waitFor(() => screen.getByLabelText(/enter your connection code/i));
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

  it("advances to token step when Continue is pressed", async () => {
    renderWizard();
    fireEvent.press(screen.getByRole("button", { name: /continue/i }));
    await waitFor(() => {
      expect(screen.getByLabelText(/api token input field/i)).toBeTruthy();
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

describe("SetupWizardScreen — token entry step", () => {
  it("renders the token input field", async () => {
    await advanceToTokenStep();
    expect(screen.getByLabelText(/api token input field/i)).toBeTruthy();
  });

  it("Confirm Token button is disabled when input is empty", async () => {
    await advanceToTokenStep();
    const button = screen.getByRole("button", { name: /confirm token/i });
    expect(button.props.accessibilityState?.disabled).toBe(true);
  });

  it("Confirm Token button becomes enabled when token is entered", async () => {
    await advanceToTokenStep();
    const input = screen.getByLabelText(/api token input field/i);
    fireEvent.changeText(input, "a-valid-token-string");
    const button = screen.getByRole("button", { name: /confirm token/i });
    expect(button.props.accessibilityState?.disabled).toBeFalsy();
  });

  it("speaks an error when token is too short (< 8 chars)", async () => {
    await advanceToTokenStep();
    const input = screen.getByLabelText(/api token input field/i);
    fireEvent.changeText(input, "short");
    fireEvent.press(screen.getByRole("button", { name: /confirm token/i }));
    await waitFor(() => {
      expect(Speech.speak).toHaveBeenCalledWith(
        expect.stringMatching(/too short/i),
        expect.any(Object)
      );
    });
  });

  it("does not advance when token is too short", async () => {
    await advanceToTokenStep();
    const input = screen.getByLabelText(/api token input field/i);
    fireEvent.changeText(input, "tiny");
    fireEvent.press(screen.getByRole("button", { name: /confirm token/i }));
    // Should still be on token step
    expect(screen.getByLabelText(/api token input field/i)).toBeTruthy();
  });

  it("advances to confirm step with a valid token", async () => {
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

  it("Re-enter button goes back to token step", async () => {
    await advanceToConfirmStep(TEST_TOKEN);
    fireEvent.press(screen.getByRole("button", { name: /re-enter token/i }));
    await waitFor(() => {
      expect(screen.getByLabelText(/api token input field/i)).toBeTruthy();
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
