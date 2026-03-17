/**
 * useAudioRecorder — expo-av microphone recording hook
 *
 * Provides a clean interface for recording voice audio on Android (TalkBack) and
 * iOS (VoiceOver). Returns the raw audio bytes as a base64 string for POSTing to the
 * backend's /transcribe endpoint.
 *
 * Design decisions:
 * - Uses expo-av Audio.Recording (highest-quality format available per platform)
 * - iOS: records in AAC (M4A) — natively supported by Whisper via ffmpeg
 * - Android: records in AMR_NB fallback → MP4/AAC when available
 * - Requests microphone permission on first call (prompts the user once)
 * - Returns base64 string so the audio can be JSON-serialised and sent to the backend
 *
 * Accessibility:
 * - startRecording() and stopRecording() are async — call from button press handlers
 * - isRecording state drives button label and color changes in MainScreen
 * - Error messages are human-readable and suitable for TTS announcement
 *
 * Per USER_STORIES.md (Sarah, NVDA user / Marcus, power user):
 *   "Press button, speak, hear response" — this hook makes that real.
 */

import { useCallback, useRef, useState } from "react";
import { Audio, type AVPlaybackStatus } from "expo-av";

// ─────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────

export type RecorderState = "idle" | "recording" | "processing" | "error";

export interface AudioRecorderResult {
  /** True while the microphone is active and capturing. */
  isRecording: boolean;
  /** Current state of the recorder lifecycle. */
  recorderState: RecorderState;
  /**
   * Start microphone recording. Requests permission if needed.
   * Resolves immediately once recording has started.
   * Rejects with a user-readable error if permission denied or hardware unavailable.
   */
  startRecording: () => Promise<void>;
  /**
   * Stop recording and return the audio as a base64 string.
   * Returns null if no audio was captured (e.g. recording was cancelled).
   * The base64 string can be sent directly to the backend /transcribe endpoint.
   */
  stopRecording: () => Promise<string | null>;
  /** Human-readable error message from the last failed operation, or null. */
  lastError: string | null;
}

// ─────────────────────────────────────────────────────────────
// Recording preset — high quality, Whisper-compatible
// ─────────────────────────────────────────────────────────────

/**
 * Recording options optimised for speech recognition.
 *
 * Uses HIGH_QUALITY preset as the base, which maps to:
 * - iOS: kAudioFormatMPEG4AAC at 44100 Hz stereo → Whisper handles this natively
 * - Android: MPEG_4 at 44100 Hz → Whisper handles this via ffmpeg
 *
 * We override to 16000 Hz mono (Whisper's native sample rate) to reduce file size
 * and improve accuracy. Smaller files also mean less base64 payload to the backend.
 */
const SPEECH_RECORDING_OPTIONS: Audio.RecordingOptions = {
  ...Audio.RecordingOptionsPresets.HIGH_QUALITY,
  android: {
    ...Audio.RecordingOptionsPresets.HIGH_QUALITY.android,
    sampleRate: 16000,
    numberOfChannels: 1,
    bitRate: 32000,
  },
  ios: {
    ...Audio.RecordingOptionsPresets.HIGH_QUALITY.ios,
    sampleRate: 16000,
    numberOfChannels: 1,
    bitRate: 32000,
    // linearPCMBitDepth, linearPCMIsBigEndian, linearPCMIsFloat are inherited
  },
};

// ─────────────────────────────────────────────────────────────
// Hook
// ─────────────────────────────────────────────────────────────

/**
 * Hook for recording voice audio and returning it as base64 for STT transcription.
 *
 * Typical usage in a press-to-talk button:
 *   const { isRecording, startRecording, stopRecording } = useAudioRecorder();
 *
 *   onPressIn: async () => await startRecording()
 *   onPressOut: async () => {
 *     const audio = await stopRecording();
 *     if (audio) { const transcript = await api.transcribe({ audio_base64: audio }); }
 *   }
 */
export function useAudioRecorder(): AudioRecorderResult {
  const [recorderState, setRecorderState] = useState<RecorderState>("idle");
  const [lastError, setLastError] = useState<string | null>(null);
  const recordingRef = useRef<Audio.Recording | null>(null);

  /** Request microphone permission. Returns true if granted, false otherwise. */
  const requestPermission = useCallback(async (): Promise<boolean> => {
    const { status } = await Audio.requestPermissionsAsync();
    return status === "granted";
  }, []);

  const startRecording = useCallback(async (): Promise<void> => {
    // Clear previous error before each new attempt
    setLastError(null);
    setRecorderState("recording");

    const granted = await requestPermission();
    if (!granted) {
      const msg =
        "Microphone permission denied. Please enable microphone access in your device settings.";
      setLastError(msg);
      setRecorderState("error");
      throw new Error(msg);
    }

    // Configure audio session for recording — iOS requires this before recording
    await Audio.setAudioModeAsync({
      allowsRecordingIOS: true,
      // Keep the speaker active so the user can still hear TTS feedback during recording
      playsInSilentModeIOS: true,
    });

    const recording = new Audio.Recording();
    try {
      await recording.prepareToRecordAsync(SPEECH_RECORDING_OPTIONS);
      await recording.startAsync();
      recordingRef.current = recording;
    } catch (err) {
      const msg = `Could not start recording: ${String(err)}`;
      setLastError(msg);
      setRecorderState("error");
      // Clean up any partially initialised recording
      try {
        await recording.stopAndUnloadAsync();
      } catch {
        // Ignore cleanup errors
      }
      throw new Error(msg);
    }
  }, [requestPermission]);

  const stopRecording = useCallback(async (): Promise<string | null> => {
    const recording = recordingRef.current;
    if (!recording) {
      // No active recording — called stop without start
      setRecorderState("idle");
      return null;
    }

    setRecorderState("processing");

    try {
      await recording.stopAndUnloadAsync();
      recordingRef.current = null;

      // Restore audio session to playback mode after recording ends
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: false,
        playsInSilentModeIOS: true,
      });

      const uri = recording.getURI();
      if (!uri) {
        setRecorderState("idle");
        return null;
      }

      // Read the audio file and base64-encode it for the backend
      const base64Audio = await readFileAsBase64(uri);
      setRecorderState("idle");
      return base64Audio;
    } catch (err) {
      const msg = `Failed to stop recording: ${String(err)}`;
      setLastError(msg);
      setRecorderState("error");
      recordingRef.current = null;
      return null;
    }
  }, []);

  return {
    isRecording: recorderState === "recording",
    recorderState,
    startRecording,
    stopRecording,
    lastError,
  };
}

// ─────────────────────────────────────────────────────────────
// File reading helper
// ─────────────────────────────────────────────────────────────

/**
 * Read a local file URI and return its contents as a base64 string.
 *
 * Uses the fetch() API with a file:// URI which is supported in Expo's
 * managed workflow on both Android and iOS. This avoids adding expo-file-system
 * as a new dependency for a single use case.
 */
async function readFileAsBase64(uri: string): Promise<string> {
  // Fetch the file using the file:// URI scheme — works in Expo's JS runtime
  const response = await fetch(uri);
  const blob = await response.blob();

  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => {
      const result = reader.result as string;
      // reader.result format: "data:<mime>;base64,<data>"
      // We only want the base64 data portion after the comma
      const base64 = result.split(",")[1];
      if (base64) {
        resolve(base64);
      } else {
        reject(new Error("FileReader produced empty base64 result"));
      }
    };
    reader.onerror = () => reject(reader.error ?? new Error("FileReader error"));
    reader.readAsDataURL(blob);
  });
}
