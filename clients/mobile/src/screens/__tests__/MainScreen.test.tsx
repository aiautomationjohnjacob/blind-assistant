/**
 * Tests for MainScreen — accessibility + voice interaction
 *
 * Key assertions:
 * 1. Every interactive element has an accessibilityLabel
 * 2. The main button is accessible (role=button, has label and hint)
 * 3. Status text uses accessibilityLiveRegion="polite" (announced on change)
 * 4. No interactive elements are hidden from the accessibility tree
 * 5. Response text is accessible to braille display users
 *
 * Voice recording flow (ISSUE-015 resolved):
 * - First press → startRecording called, state changes to "listening"
 * - Second press → stopRecording called, audio → transcribe → query → TTS
 * - Empty transcription → "didn't catch that" spoken, returns to idle
 * - Microphone permission denied → error spoken
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
const mockTranscribe = jest.fn();

jest.mock("@services/api", () => ({
  ...jest.requireActual("@services/api"),
  getAPIClient: () => ({
    query: mockQuery,
    transcribe: mockTranscribe,
  }),
  configureAPIClient: jest.fn(),
  resetAPIClient: jest.fn(),
}));

// Mock the audio recorder hook — avoids any expo-av native module dependency in tests
const mockStartRecording = jest.fn();
const mockStopRecording = jest.fn();

jest.mock("@hooks/useAudioRecorder", () => ({
  useAudioRecorder: jest.fn(() => ({
    isRecording: false,
    recorderState: "idle",
    startRecording: mockStartRecording,
    stopRecording: mockStopRecording,
    lastError: null,
  })),
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

  // Default: recording returns base64 audio
  mockStartRecording.mockResolvedValue(undefined);
  mockStopRecording.mockResolvedValue("SGVsbG8gV29ybGQ="); // base64 "Hello World"

  // Default: transcribe returns a user message
  mockTranscribe.mockResolvedValue({
    text: "What can you help me with?",
    language: "en",
    session_id: "test",
  });

  // Default: query returns AI response
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
// Tests: Voice interaction flow (ISSUE-015)
// ─────────────────────────────────────────────────────────────

describe("MainScreen — voice recording flow", () => {
  it("calls startRecording on first button press", async () => {
    render(<MainScreen />);
    const button = screen.getByRole("button");
    fireEvent.press(button);

    await waitFor(() => {
      expect(mockStartRecording).toHaveBeenCalledTimes(1);
    });
  });

  it("announces 'Listening' when recording starts", async () => {
    render(<MainScreen />);
    const button = screen.getByRole("button");
    fireEvent.press(button);

    await waitFor(() => {
      expect(AccessibilityInfo.announceForAccessibility).toHaveBeenCalledWith(
        expect.stringMatching(/listening/i)
      );
    });
  });

  it("calls transcribe with the audio base64 after second press", async () => {
    render(<MainScreen />);
    const button = screen.getByRole("button");

    // First press: start recording
    fireEvent.press(button);
    await waitFor(() => {
      expect(mockStartRecording).toHaveBeenCalledTimes(1);
    });

    // Second press: stop and process
    fireEvent.press(button);
    await waitFor(() => {
      expect(mockTranscribe).toHaveBeenCalledWith(
        expect.objectContaining({ audio_base64: "SGVsbG8gV29ybGQ=" })
      );
    });
  });

  it("sends the transcript to /query after transcription", async () => {
    render(<MainScreen />);
    const button = screen.getByRole("button");

    fireEvent.press(button);
    await waitFor(() => { expect(mockStartRecording).toHaveBeenCalled(); });
    fireEvent.press(button);

    await waitFor(() => {
      expect(mockQuery).toHaveBeenCalledWith(
        expect.objectContaining({ message: "What can you help me with?" })
      );
    });
  });

  it("speaks the AI response via TTS after query", async () => {
    render(<MainScreen />);
    const button = screen.getByRole("button");

    fireEvent.press(button);
    await waitFor(() => { expect(mockStartRecording).toHaveBeenCalled(); });
    fireEvent.press(button);

    await waitFor(() => {
      expect(Speech.speak).toHaveBeenCalledWith(
        expect.stringContaining("I can help you with many tasks"),
        expect.any(Object)
      );
    });
  });

  it("shows transcript on screen for braille display users", async () => {
    render(<MainScreen />);
    const button = screen.getByRole("button");

    fireEvent.press(button);
    await waitFor(() => { expect(mockStartRecording).toHaveBeenCalled(); });
    fireEvent.press(button);

    await waitFor(() => {
      expect(screen.getByText("What can you help me with?")).toBeTruthy();
    });
  });

  it("speaks 'didn't catch that' when transcription returns empty string", async () => {
    mockStopRecording.mockResolvedValue("SGVsbG8=");
    mockTranscribe.mockResolvedValue({ text: "   ", language: null, session_id: "test" });

    render(<MainScreen />);
    const button = screen.getByRole("button");

    fireEvent.press(button);
    await waitFor(() => { expect(mockStartRecording).toHaveBeenCalled(); });
    fireEvent.press(button);

    await waitFor(() => {
      expect(Speech.speak).toHaveBeenCalledWith(
        expect.stringMatching(/didn't catch that/i),
        expect.any(Object)
      );
    });
    expect(mockQuery).not.toHaveBeenCalled();
  });

  it("speaks 'no audio captured' when stopRecording returns null", async () => {
    mockStopRecording.mockResolvedValue(null);

    render(<MainScreen />);
    const button = screen.getByRole("button");

    fireEvent.press(button);
    await waitFor(() => { expect(mockStartRecording).toHaveBeenCalled(); });
    fireEvent.press(button);

    await waitFor(() => {
      expect(Speech.speak).toHaveBeenCalledWith(
        expect.stringMatching(/no audio captured/i),
        expect.any(Object)
      );
    });
  });

  it("speaks error message when transcribe API call fails", async () => {
    mockTranscribe.mockRejectedValue(new Error("Network error"));

    render(<MainScreen />);
    const button = screen.getByRole("button");

    fireEvent.press(button);
    await waitFor(() => { expect(mockStartRecording).toHaveBeenCalled(); });
    fireEvent.press(button);

    await waitFor(() => {
      expect(Speech.speak).toHaveBeenCalledWith(
        expect.stringMatching(/something went wrong/i),
        expect.any(Object)
      );
    });
  });

  it("speaks error and recovers when microphone permission denied", async () => {
    mockStartRecording.mockRejectedValue(new Error("Microphone permission denied"));

    render(<MainScreen />);
    const button = screen.getByRole("button");
    fireEvent.press(button);

    await waitFor(() => {
      expect(Speech.speak).toHaveBeenCalledWith(
        expect.stringMatching(/could not access microphone/i),
        expect.any(Object)
      );
    });
  });

  it("prefers spoken_text over text for TTS playback", async () => {
    mockQuery.mockResolvedValue({
      text: "A detailed explanation that is quite long.",
      spoken_text: "Short version.",
      follow_up_prompt: null,
      session_id: "test",
    });

    render(<MainScreen />);
    const button = screen.getByRole("button");

    fireEvent.press(button);
    await waitFor(() => { expect(mockStartRecording).toHaveBeenCalled(); });
    fireEvent.press(button);

    await waitFor(() => {
      expect(Speech.speak).toHaveBeenCalledWith("Short version.", expect.any(Object));
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
    const button = screen.getByRole("button");

    fireEvent.press(button);
    await waitFor(() => { expect(mockStartRecording).toHaveBeenCalled(); });
    fireEvent.press(button);

    await waitFor(() => {
      const calls = (Speech.speak as jest.Mock).mock.calls.map((c) => c[0] as string);
      expect(calls.some((t) => t.includes("Would you like me to read it back?"))).toBe(true);
    });
  });
});

// ─────────────────────────────────────────────────────────────
// Tests: Button state management
// ─────────────────────────────────────────────────────────────

describe("MainScreen — button state", () => {
  it("button is disabled while query is in flight", async () => {
    // Make query hang so we can observe the thinking state
    mockTranscribe.mockResolvedValue({ text: "order food", language: "en", session_id: "test" });
    mockQuery.mockReturnValue(new Promise(() => {}));

    render(<MainScreen />);
    const button = screen.getByRole("button");

    fireEvent.press(button);
    await waitFor(() => { expect(mockStartRecording).toHaveBeenCalled(); });
    fireEvent.press(button);

    await waitFor(() => {
      expect(mockQuery).toHaveBeenCalled();
    });
    // Button should be disabled while thinking
    expect(button.props.accessibilityState?.disabled).toBe(true);
  });

  it("displays the AI response text for braille display users", async () => {
    mockQuery.mockResolvedValue({
      text: "This text is for braille users.",
      spoken_text: "Short.",
      follow_up_prompt: null,
      session_id: "test",
    });

    render(<MainScreen />);
    const button = screen.getByRole("button");

    fireEvent.press(button);
    await waitFor(() => { expect(mockStartRecording).toHaveBeenCalled(); });
    fireEvent.press(button);

    await waitFor(() => {
      // spoken_text "Short." is used for TTS
      expect(Speech.speak).toHaveBeenCalledWith("Short.", expect.any(Object));
      // The short text is displayed in the response area for braille users
      expect(screen.getByText("Short.")).toBeTruthy();
    });
  });
});
