/**
 * Tests for useAudioRecorder hook
 *
 * Covers:
 * - Initial state (idle, not recording)
 * - startRecording requests permission, configures audio, starts recording
 * - startRecording throws when permission denied
 * - stopRecording returns base64 audio string
 * - stopRecording returns null when no recording is active
 * - stopRecording returns null when recording URI is null
 * - Error state set when recording fails to start
 * - Audio mode is restored to playback after stop
 *
 * All expo-av calls are mocked — no real audio hardware required.
 */

import { renderHook, act } from "@testing-library/react-native";
import { useAudioRecorder } from "../useAudioRecorder";
import { Audio } from "expo-av";

// ─────────────────────────────────────────────────────────────
// Mocks
// ─────────────────────────────────────────────────────────────

// Mock expo-av Audio module
const mockStartAsync = jest.fn().mockResolvedValue(undefined);
const mockStopAndUnloadAsync = jest.fn().mockResolvedValue(undefined);
const mockPrepareToRecordAsync = jest.fn().mockResolvedValue(undefined);
const mockGetURI = jest.fn().mockReturnValue("file:///tmp/recording.m4a");

jest.mock("expo-av", () => ({
  Audio: {
    // Recording class — each new instance uses the mocks above
    Recording: jest.fn().mockImplementation(() => ({
      prepareToRecordAsync: mockPrepareToRecordAsync,
      startAsync: mockStartAsync,
      stopAndUnloadAsync: mockStopAndUnloadAsync,
      getURI: mockGetURI,
    })),
    RecordingOptionsPresets: {
      HIGH_QUALITY: {
        android: { sampleRate: 44100, numberOfChannels: 2, bitRate: 128000 },
        ios: { sampleRate: 44100, numberOfChannels: 2, bitRate: 128000 },
      },
    },
    requestPermissionsAsync: jest.fn().mockResolvedValue({ status: "granted" }),
    setAudioModeAsync: jest.fn().mockResolvedValue(undefined),
  },
}));

// Mock fetch + FileReader for base64 reading
const mockBlob = { size: 100 };
const mockReadAsDataURL = jest.fn();
const MockFileReader = jest.fn().mockImplementation(() => ({
  readAsDataURL: mockReadAsDataURL,
  result: "data:audio/m4a;base64,SGVsbG8gV29ybGQ=",
  onloadend: null as (() => void) | null,
  onerror: null,
  // Simulate async read by calling onloadend when readAsDataURL is called
}));

beforeAll(() => {
  // Assign MockFileReader to global FileReader
  (global as unknown as { FileReader: typeof MockFileReader }).FileReader = MockFileReader;
});

// Override mockReadAsDataURL to trigger onloadend after a tick
mockReadAsDataURL.mockImplementation(function (this: { onloadend: (() => void) | null }) {
  // "this" is the MockFileReader instance — call onloadend asynchronously
  const instance = this;
  Promise.resolve().then(() => {
    if (instance.onloadend) instance.onloadend();
  });
});

global.fetch = jest.fn().mockResolvedValue({
  blob: jest.fn().mockResolvedValue(mockBlob),
});

// ─────────────────────────────────────────────────────────────
// Setup
// ─────────────────────────────────────────────────────────────

beforeEach(() => {
  jest.clearAllMocks();
  // Restore default mock implementations
  (Audio.requestPermissionsAsync as jest.Mock).mockResolvedValue({ status: "granted" });
  (Audio.setAudioModeAsync as jest.Mock).mockResolvedValue(undefined);
  mockPrepareToRecordAsync.mockResolvedValue(undefined);
  mockStartAsync.mockResolvedValue(undefined);
  mockStopAndUnloadAsync.mockResolvedValue(undefined);
  mockGetURI.mockReturnValue("file:///tmp/recording.m4a");
  mockReadAsDataURL.mockImplementation(function (this: { onloadend: (() => void) | null }) {
    const instance = this;
    Promise.resolve().then(() => {
      if (instance.onloadend) instance.onloadend();
    });
  });
});

// ─────────────────────────────────────────────────────────────
// Tests
// ─────────────────────────────────────────────────────────────

describe("useAudioRecorder — initial state", () => {
  it("starts in idle state with isRecording=false", () => {
    const { result } = renderHook(() => useAudioRecorder());
    expect(result.current.isRecording).toBe(false);
    expect(result.current.recorderState).toBe("idle");
  });

  it("has null lastError on mount", () => {
    const { result } = renderHook(() => useAudioRecorder());
    expect(result.current.lastError).toBeNull();
  });

  it("exposes startRecording and stopRecording functions", () => {
    const { result } = renderHook(() => useAudioRecorder());
    expect(typeof result.current.startRecording).toBe("function");
    expect(typeof result.current.stopRecording).toBe("function");
  });
});

describe("useAudioRecorder — startRecording", () => {
  it("requests microphone permission on start", async () => {
    const { result } = renderHook(() => useAudioRecorder());
    await act(async () => {
      await result.current.startRecording();
    });
    expect(Audio.requestPermissionsAsync).toHaveBeenCalledTimes(1);
  });

  it("sets isRecording=true after startRecording", async () => {
    const { result } = renderHook(() => useAudioRecorder());
    await act(async () => {
      await result.current.startRecording();
    });
    expect(result.current.isRecording).toBe(true);
    expect(result.current.recorderState).toBe("recording");
  });

  it("configures audio mode for iOS recording", async () => {
    const { result } = renderHook(() => useAudioRecorder());
    await act(async () => {
      await result.current.startRecording();
    });
    expect(Audio.setAudioModeAsync).toHaveBeenCalledWith(
      expect.objectContaining({ allowsRecordingIOS: true })
    );
  });

  it("calls prepareToRecordAsync and startAsync", async () => {
    const { result } = renderHook(() => useAudioRecorder());
    await act(async () => {
      await result.current.startRecording();
    });
    expect(mockPrepareToRecordAsync).toHaveBeenCalledTimes(1);
    expect(mockStartAsync).toHaveBeenCalledTimes(1);
  });

  it("sets error state and throws when permission denied", async () => {
    (Audio.requestPermissionsAsync as jest.Mock).mockResolvedValueOnce({
      status: "denied",
    });
    const { result } = renderHook(() => useAudioRecorder());
    await act(async () => {
      await expect(result.current.startRecording()).rejects.toThrow(/permission/i);
    });
    expect(result.current.recorderState).toBe("error");
    expect(result.current.lastError).toMatch(/permission/i);
  });

  it("sets error state and throws when recording hardware fails", async () => {
    mockPrepareToRecordAsync.mockRejectedValueOnce(new Error("No microphone"));
    const { result } = renderHook(() => useAudioRecorder());
    await act(async () => {
      await expect(result.current.startRecording()).rejects.toThrow(/could not start recording/i);
    });
    expect(result.current.recorderState).toBe("error");
    expect(result.current.lastError).toMatch(/could not start recording/i);
  });

  it("clears lastError on a new startRecording attempt", async () => {
    // First call fails to set an error
    mockPrepareToRecordAsync.mockRejectedValueOnce(new Error("Hardware error"));
    const { result } = renderHook(() => useAudioRecorder());
    await act(async () => {
      try {
        await result.current.startRecording();
      } catch {
        // expected failure
      }
    });
    expect(result.current.lastError).not.toBeNull();

    // Second call succeeds — lastError should be cleared
    mockPrepareToRecordAsync.mockResolvedValue(undefined);
    await act(async () => {
      await result.current.startRecording();
    });
    expect(result.current.lastError).toBeNull();
  });
});

describe("useAudioRecorder — stopRecording", () => {
  it("returns null when called without a prior startRecording", async () => {
    const { result } = renderHook(() => useAudioRecorder());
    let audio: string | null = "not-null";
    await act(async () => {
      audio = await result.current.stopRecording();
    });
    expect(audio).toBeNull();
    expect(result.current.recorderState).toBe("idle");
  });

  it("returns base64 audio string after a successful recording", async () => {
    const { result } = renderHook(() => useAudioRecorder());
    await act(async () => {
      await result.current.startRecording();
    });
    let audio: string | null = null;
    await act(async () => {
      audio = await result.current.stopRecording();
    });
    // Should have called stopAndUnloadAsync and returned a base64 string
    expect(mockStopAndUnloadAsync).toHaveBeenCalledTimes(1);
    expect(typeof audio).toBe("string");
    expect(audio).not.toBe("");
  });

  it("restores audio mode to playback after stop", async () => {
    const { result } = renderHook(() => useAudioRecorder());
    await act(async () => {
      await result.current.startRecording();
    });
    await act(async () => {
      await result.current.stopRecording();
    });
    // Should be called twice: once for recording mode, once to restore playback
    expect(Audio.setAudioModeAsync).toHaveBeenCalledTimes(2);
    const secondCall = (Audio.setAudioModeAsync as jest.Mock).mock.calls[1][0];
    expect(secondCall.allowsRecordingIOS).toBe(false);
  });

  it("returns null when recording URI is null", async () => {
    mockGetURI.mockReturnValueOnce(null);
    const { result } = renderHook(() => useAudioRecorder());
    await act(async () => {
      await result.current.startRecording();
    });
    let audio: string | null = "not-null";
    await act(async () => {
      audio = await result.current.stopRecording();
    });
    expect(audio).toBeNull();
    expect(result.current.recorderState).toBe("idle");
  });

  it("sets error state and returns null when stopAndUnloadAsync fails", async () => {
    mockStopAndUnloadAsync.mockRejectedValueOnce(new Error("Hardware failure"));
    const { result } = renderHook(() => useAudioRecorder());
    await act(async () => {
      await result.current.startRecording();
    });
    let audio: string | null = "not-null";
    await act(async () => {
      audio = await result.current.stopRecording();
    });
    expect(audio).toBeNull();
    expect(result.current.recorderState).toBe("error");
    expect(result.current.lastError).toMatch(/failed to stop recording/i);
  });

  it("returns to idle state after successful stop", async () => {
    const { result } = renderHook(() => useAudioRecorder());
    await act(async () => {
      await result.current.startRecording();
    });
    await act(async () => {
      await result.current.stopRecording();
    });
    expect(result.current.isRecording).toBe(false);
    expect(result.current.recorderState).toBe("idle");
  });
});
