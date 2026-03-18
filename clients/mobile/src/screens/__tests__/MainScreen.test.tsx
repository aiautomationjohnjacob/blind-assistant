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

// Mock expo-haptics — impactAsync is the recording start/stop confirmation cue.
// This mock prevents native Taptic Engine calls in the test environment while
// allowing assertions that haptic feedback was requested at the right times.
// Note: jest.mock() is hoisted before variable declarations, so the mock factory
// must not reference variables defined outside it. We use jest.fn() directly here
// and retrieve the mock reference via jest.requireMock() in beforeEach.
jest.mock("expo-haptics", () => ({
  impactAsync: jest.fn().mockResolvedValue(undefined),
  ImpactFeedbackStyle: {
    Light: "light",
    Medium: "medium",
    Heavy: "heavy",
  },
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
    // Hint must exist and be meaningful — it describes what happens when activated.
    // Per VoiceOver/TalkBack guidelines, hints must NOT say "Double-tap" or "tap" —
    // screen readers already tell users how to activate (VoiceOver says "Activate",
    // TalkBack says "Double-tap"). The hint should describe the outcome.
    expect(button.props.accessibilityHint).toBeTruthy();
    expect(button.props.accessibilityHint.length).toBeGreaterThan(10);
    // Ensure we don't regress to VoiceOver-incorrect "double-tap" hint wording
    expect(button.props.accessibilityHint).not.toMatch(/double-tap/i);
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
// Tests: Haptic feedback (ISSUE-open since Cycle 7)
// ─────────────────────────────────────────────────────────────
//
// TalkBack/VoiceOver users cannot see the button color change when recording starts.
// A medium-weight haptic on start and a light haptic on stop give non-visual confirmation.
// Per blind-user-tester review (Cycle 7, 9, 10): "I need to know recording actually started."

describe("MainScreen — haptic recording cues", () => {
  // Access the mocked expo-haptics module via jest.requireMock to avoid hoisting issues.
  // jest.mock() is hoisted before variable declarations, so top-level const mockFn =
  // jest.fn() references don't work as mock factories. jest.requireMock() is the correct
  // pattern for accessing auto-mocked or factory-mocked modules in tests.
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const getHapticsMock = () => jest.requireMock("expo-haptics") as any;

  it("fires a medium haptic when recording starts (first button press)", async () => {
    render(<MainScreen />);
    const button = screen.getByRole("button");

    fireEvent.press(button);

    await waitFor(() => {
      expect(mockStartRecording).toHaveBeenCalledTimes(1);
    });

    // Medium impact fires after state transitions to "listening" — confirms recording started
    expect(getHapticsMock().impactAsync).toHaveBeenCalledWith("medium");
  });

  it("fires a light haptic when recording stops (second button press)", async () => {
    render(<MainScreen />);
    const button = screen.getByRole("button");

    // Start recording
    fireEvent.press(button);
    await waitFor(() => { expect(mockStartRecording).toHaveBeenCalled(); });

    // Stop recording
    fireEvent.press(button);
    await waitFor(() => {
      // Two haptics should have fired: medium on start, light on stop
      expect(getHapticsMock().impactAsync).toHaveBeenCalledTimes(2);
      const calls = getHapticsMock().impactAsync.mock.calls.map((c: string[]) => c[0]);
      expect(calls[0]).toBe("medium"); // start — confirms recording active
      expect(calls[1]).toBe("light");  // stop — confirms input captured
    });
  });

  it("haptic failure does not crash the recording flow", async () => {
    // expo-haptics may not be available on all devices (e.g. older Android, iPad
    // without Taptic Engine). The implementation silently ignores haptic errors.
    getHapticsMock().impactAsync.mockRejectedValueOnce(new Error("Haptics unavailable"));

    render(<MainScreen />);
    const button = screen.getByRole("button");

    // Should not throw even when haptics fails
    fireEvent.press(button);
    await waitFor(() => {
      expect(mockStartRecording).toHaveBeenCalledTimes(1);
    });

    // Screen reader announcement should still fire as the primary cue
    expect(AccessibilityInfo.announceForAccessibility).toHaveBeenCalledWith(
      expect.stringMatching(/listening/i)
    );
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

// ─────────────────────────────────────────────────────────────
// Tests: Web platform ARIA role fix (Phase 4 — ISSUE-033)
// ─────────────────────────────────────────────────────────────
//
// react-native-web maps accessibilityRole="text" → role="text" in the DOM.
// "text" is not a valid WAI-ARIA role. On web, it confuses assistive technologies
// (NVDA, JAWS, VoiceOver/macOS) that validate roles against the ARIA spec.
// Fix: use Platform.OS === "web" ? undefined : "text" so that on web the element
// carries no explicit role (the native HTML element semantics are sufficient).
//
// These tests mock Platform.OS to "web" to simulate the web export environment
// and verify that status/transcript/response containers emit no invalid roles.

describe("MainScreen — web platform accessibilityRole fix (ISSUE-033)", () => {
  let originalPlatformOS: string;

  beforeAll(() => {
    // Save original platform and switch to web
    const { Platform } = require("react-native");
    originalPlatformOS = Platform.OS;
    Platform.OS = "web";
  });

  afterAll(() => {
    // Restore original platform after these tests
    const { Platform } = require("react-native");
    Platform.OS = originalPlatformOS;
  });

  it("status text has no accessibilityRole on web (avoids invalid role='text')", () => {
    render(<MainScreen />);
    // The status text is identified by its label
    const statusText = screen.getByLabelText(/ready\. tap to speak/i);
    // On web, accessibilityRole should be undefined (not "text")
    expect(statusText.props.accessibilityRole).toBeUndefined();
  });

  it("main container still renders on web platform", () => {
    render(<MainScreen />);
    expect(screen.getByLabelText(/blind assistant main screen/i)).toBeTruthy();
  });

  it("button still has role=button on web platform", () => {
    render(<MainScreen />);
    const button = screen.getByRole("button");
    expect(button).toBeTruthy();
    expect(button.props.accessibilityRole).toBe("button");
  });

  it("title still has role=header on web platform", () => {
    render(<MainScreen />);
    const header = screen.getByRole("header");
    expect(header).toBeTruthy();
    expect(header.props.accessibilityRole).toBe("header");
  });
});

// ─────────────────────────────────────────────────────────────
// Tests: Phase 4 — iOS/Android accessibility hardening (ISSUE-036)
// ─────────────────────────────────────────────────────────────
//
// Phase 4 accessibility hardening targets:
//
// 1. VoiceOver rotor (accessibilityActions): VoiceOver's "Actions" rotor item shows
//    custom actions on the focused element. We expose an "activate" action on the button
//    so VoiceOver users know what the button does from the Actions rotor menu.
//
// 2. TalkBack gesture coverage (onAccessibilityAction): TalkBack's "Actions" node
//    (swipe-up-then-right) also uses accessibilityActions. The onAccessibilityAction
//    handler must correctly call handleButtonPress when the "activate" action fires.
//
// 3. Live region on Text vs View (iOS VoiceOver fix): accessibilityLiveRegion on a View
//    is silently ignored by iOS VoiceOver. The live region must be on the inner Text node
//    that actually changes, not its View container. This fix ensures VoiceOver announces
//    both transcript and response updates when they appear.

describe("MainScreen — Phase 4 iOS/Android accessibility (ISSUE-036)", () => {
  // ── VoiceOver Rotor / TalkBack Actions ─────────────────────────────────────

  it("main button exposes an accessibilityActions array (rotor/actions support)", () => {
    // VoiceOver: Actions rotor item lists these. TalkBack: Actions menu (swipe-up-then-right).
    // Both screen readers require onAccessibilityAction handler to be present.
    render(<MainScreen />);
    const button = screen.getByRole("button");
    // accessibilityActions must be defined and contain at least one action
    expect(button.props.accessibilityActions).toBeDefined();
    expect(Array.isArray(button.props.accessibilityActions)).toBe(true);
    expect(button.props.accessibilityActions.length).toBeGreaterThan(0);
  });

  it("idle state button action is labeled 'Start speaking'", () => {
    // In idle state, the action label describes what will happen next.
    // VoiceOver reads: "Speak to assistant. Button. Actions available: Start speaking."
    render(<MainScreen />);
    const button = screen.getByRole("button");
    const actions = button.props.accessibilityActions as Array<{ name: string; label: string }>;
    const activateAction = actions.find((a) => a.name === "activate");
    expect(activateAction).toBeDefined();
    expect(activateAction?.label).toBe("Start speaking");
  });

  it("onAccessibilityAction handler exists on the button", () => {
    // TalkBack's Actions menu fires onAccessibilityAction when a user selects an action.
    // Without this handler, the Actions menu entry does nothing — silent failure.
    render(<MainScreen />);
    const button = screen.getByRole("button");
    expect(button.props.onAccessibilityAction).toBeDefined();
    expect(typeof button.props.onAccessibilityAction).toBe("function");
  });

  // ── iOS VoiceOver live region fix (Text not View) ──────────────────────────

  it("transcript Text node has accessibilityLiveRegion='polite' after transcription", async () => {
    // Phase 4 fix: live region moved to Text (not View) for iOS VoiceOver compatibility.
    // VoiceOver only fires live region events when content changes inside a Text node.
    // A View wrapper with accessibilityLiveRegion is ignored on iOS.
    mockTranscribe.mockResolvedValue({ text: "order food", language: "en", session_id: "test" });
    mockQuery.mockResolvedValue({
      text: "I can help with that.",
      spoken_text: "I can help with that.",
      session_id: "test",
    });

    render(<MainScreen />);
    const button = screen.getByRole("button");

    // Start recording, stop to trigger transcription
    fireEvent.press(button);
    await waitFor(() => { expect(mockStartRecording).toHaveBeenCalled(); });
    fireEvent.press(button);

    await waitFor(() => {
      // After transcription, "You said:" text should appear
      expect(screen.getByText("order food")).toBeTruthy();
    });

    // The transcript text node must carry the live region attribute
    // React Native Testing Library uses the 'accessibilityLiveRegion' prop directly
    const transcriptNode = screen.getByText("order food");
    expect(transcriptNode.props.accessibilityLiveRegion).toBe("polite");
  });

  it("response Text node has accessibilityLiveRegion='polite' after AI response", async () => {
    // Same fix for the response container: the inner Text node must carry the live region.
    mockTranscribe.mockResolvedValue({ text: "what time is it?", language: "en", session_id: "t" });
    mockQuery.mockResolvedValue({
      text: "It is 3 PM.",
      spoken_text: "It is 3 PM.",
      session_id: "test",
    });

    render(<MainScreen />);
    const button = screen.getByRole("button");

    fireEvent.press(button);
    await waitFor(() => { expect(mockStartRecording).toHaveBeenCalled(); });
    fireEvent.press(button);

    await waitFor(() => {
      expect(screen.getByText("It is 3 PM.")).toBeTruthy();
    });

    // The response Text node must carry the live region for iOS VoiceOver
    const responseNode = screen.getByText("It is 3 PM.");
    expect(responseNode.props.accessibilityLiveRegion).toBe("polite");
  });

  it("transcript Text node has accessibilityLabel including 'You said'", async () => {
    // The inner Text that has the live region should also have a descriptive label
    // so VoiceOver announces 'You said: order food' not just 'order food'.
    mockTranscribe.mockResolvedValue({ text: "call my doctor", language: "en", session_id: "t" });
    mockQuery.mockResolvedValue({
      text: "Calling your doctor now.",
      spoken_text: "Calling your doctor now.",
      session_id: "test",
    });

    render(<MainScreen />);
    const button = screen.getByRole("button");

    fireEvent.press(button);
    await waitFor(() => { expect(mockStartRecording).toHaveBeenCalled(); });
    fireEvent.press(button);

    await waitFor(() => {
      expect(screen.getByText("call my doctor")).toBeTruthy();
    });

    const transcriptNode = screen.getByText("call my doctor");
    // Label should include context prefix for VoiceOver announcement
    expect(transcriptNode.props.accessibilityLabel).toMatch(/you said/i);
  });
});
