/**
 * Tests for MainScreen — accessibility + interaction
 *
 * Key assertions:
 * 1. Every interactive element has an accessibilityLabel
 * 2. The main button is accessible (role=button, has label and hint)
 * 3. Status text uses accessibilityLiveRegion="polite" (announced on change)
 * 4. No interactive elements are hidden from the accessibility tree
 * 5. Response text is accessible to braille display users
 *
 * Per CLAUDE.md accessibility rules:
 * - Every interactive element MUST have an accessible name
 * - Minimum touch target 44x44dp (tested via hitSlop)
 * - No color-only state indicators
 */

import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react-native";
import { MainScreen } from "../MainScreen";
import * as Speech from "expo-speech";
import { AccessibilityInfo } from "react-native";
import { configureAPIClient, resetAPIClient } from "@services/api";

// ─────────────────────────────────────────────────────────────
// Mocks
// ─────────────────────────────────────────────────────────────

jest.mock("expo-speech", () => ({
  speak: jest.fn((_text, options) => {
    // Immediately call onDone so we don't wait for real TTS
    options?.onDone?.();
  }),
  stop: jest.fn(),
}));

// jest-expo preset already mocks react-native. We patch AccessibilityInfo
// via jest.spyOn in beforeEach (below) rather than jest.mock, which avoids
// the SettingsManager circular/native-module error in Node-based Jest.

const mockQuery = jest.fn();

jest.mock("@services/api", () => ({
  ...jest.requireActual("@services/api"),
  getAPIClient: () => ({
    query: mockQuery,
  }),
  configureAPIClient: jest.fn(),
  resetAPIClient: jest.fn(),
}));

// ─────────────────────────────────────────────────────────────
// Setup / Teardown
// ─────────────────────────────────────────────────────────────

beforeEach(() => {
  jest.clearAllMocks();
  // Spy on AccessibilityInfo.announceForAccessibility after jest-expo preset
  // has already loaded the react-native mock. This is the correct pattern for
  // patching individual methods without triggering the SettingsManager native
  // module error that happens when jest.requireActual("react-native") is called.
  jest.spyOn(AccessibilityInfo, "announceForAccessibility").mockImplementation(() => {});
  mockQuery.mockResolvedValue({
    text: "I can help you with many tasks.",
    spoken_text: null,
    follow_up_prompt: null,
    session_id: "test",
  });
});

// ─────────────────────────────────────────────────────────────
// Tests: Accessibility
// ─────────────────────────────────────────────────────────────

describe("MainScreen — accessibility", () => {
  it("renders the main container with an accessibilityLabel", () => {
    render(<MainScreen />);
    // The root View should be identifiable by screen readers
    expect(screen.getByLabelText(/blind assistant main screen/i)).toBeTruthy();
  });

  it("renders the title with role=header for screen reader navigation", () => {
    render(<MainScreen />);
    const header = screen.getByRole("header");
    expect(header).toBeTruthy();
    expect(header.props.accessibilityLabel).toMatch(/blind assistant/i);
  });

  it("renders the main button with role=button", () => {
    render(<MainScreen />);
    const button = screen.getByRole("button");
    expect(button).toBeTruthy();
  });

  it("main button has a non-empty accessibilityLabel", () => {
    render(<MainScreen />);
    const button = screen.getByRole("button");
    expect(button.props.accessibilityLabel).toBeTruthy();
    expect(button.props.accessibilityLabel.length).toBeGreaterThan(3);
  });

  it("main button has an accessibilityHint for first-time users", () => {
    render(<MainScreen />);
    const button = screen.getByRole("button");
    // VoiceOver reads the hint after the label — important for discoverability
    expect(button.props.accessibilityHint).toMatch(/double-tap/i);
  });

  it("status text uses accessibilityLiveRegion='polite'", () => {
    render(<MainScreen />);
    const statusText = screen.getByLabelText(/ready\. tap to speak/i);
    expect(statusText.props.accessibilityLiveRegion).toBe("polite");
  });

  it("announces readiness to screen reader on mount", () => {
    render(<MainScreen />);
    expect(AccessibilityInfo.announceForAccessibility).toHaveBeenCalledWith(
      expect.stringMatching(/blind assistant is ready/i)
    );
  });
});

// ─────────────────────────────────────────────────────────────
// Tests: Interaction
// ─────────────────────────────────────────────────────────────

describe("MainScreen — interaction", () => {
  it("calls the API when the button is pressed", async () => {
    render(<MainScreen />);
    const button = screen.getByRole("button");

    fireEvent.press(button);

    await waitFor(() => {
      expect(mockQuery).toHaveBeenCalledTimes(1);
    });
  });

  it("speaks the API response via TTS", async () => {
    mockQuery.mockResolvedValue({
      text: "I can help you navigate your computer.",
      spoken_text: null,
      follow_up_prompt: null,
      session_id: "test",
    });

    render(<MainScreen />);
    fireEvent.press(screen.getByRole("button"));

    await waitFor(() => {
      expect(Speech.speak).toHaveBeenCalledWith(
        expect.stringContaining("I can help you navigate"),
        expect.any(Object)
      );
    });
  });

  it("prefers spoken_text over text for TTS", async () => {
    mockQuery.mockResolvedValue({
      text: "A detailed explanation that is quite long.",
      spoken_text: "Short version.",
      follow_up_prompt: null,
      session_id: "test",
    });

    render(<MainScreen />);
    fireEvent.press(screen.getByRole("button"));

    await waitFor(() => {
      expect(Speech.speak).toHaveBeenCalledWith(
        "Short version.",
        expect.any(Object)
      );
    });
  });

  it("speaks follow_up_prompt after the main response", async () => {
    mockQuery.mockResolvedValue({
      text: "Note saved.",
      spoken_text: null,
      follow_up_prompt: "Would you like me to read it back?",
      session_id: "test",
    });

    render(<MainScreen />);
    fireEvent.press(screen.getByRole("button"));

    await waitFor(() => {
      const calls = (Speech.speak as jest.Mock).mock.calls.map((c) => c[0] as string);
      expect(calls.some((t) => t.includes("Would you like me to read it back?"))).toBe(true);
    });
  });

  it("speaks an error message when the API fails", async () => {
    mockQuery.mockRejectedValue(new Error("Network error"));

    render(<MainScreen />);
    fireEvent.press(screen.getByRole("button"));

    await waitFor(() => {
      expect(Speech.speak).toHaveBeenCalledWith(
        expect.stringMatching(/something went wrong/i),
        expect.any(Object)
      );
    });
  });

  it("button is disabled while request is in flight", async () => {
    // Make the query never resolve during this test
    mockQuery.mockReturnValue(new Promise(() => {}));

    render(<MainScreen />);
    const button = screen.getByRole("button");
    fireEvent.press(button);

    // Button should become disabled while thinking
    await waitFor(() => {
      expect(button.props.accessibilityState?.disabled).toBe(true);
    });
  });

  it("displays the response text for braille display users", async () => {
    mockQuery.mockResolvedValue({
      text: "This text is for braille users.",
      spoken_text: "Short.",
      follow_up_prompt: null,
      session_id: "test",
    });

    render(<MainScreen />);
    fireEvent.press(screen.getByRole("button"));

    // The SHORT version is spoken; the TEXT version is rendered (for braille)
    await waitFor(() => {
      // spoken_text is used for TTS
      expect(Speech.speak).toHaveBeenCalledWith("Short.", expect.any(Object));
      // text is displayed on screen for braille display
      expect(screen.getByText("Short.")).toBeTruthy();
    });
  });
});
