/**
 * Expo app configuration.
 *
 * Accessibility-first settings:
 * - TalkBack (Android) and VoiceOver (iOS) are primary interaction methods
 * - All interactive elements must have accessibilityLabel
 * - No reliance on color alone for conveying state
 * - Minimum touch target: 44x44dp
 */
import type { ExpoConfig } from "expo/config";

const config: ExpoConfig = {
  name: "Blind Assistant",
  slug: "blind-assistant",
  version: "0.1.0",
  orientation: "portrait",
  icon: "./assets/icon.png",
  userInterfaceStyle: "automatic", // Supports system dark/light mode
  splash: {
    image: "./assets/splash.png",
    resizeMode: "contain",
    backgroundColor: "#1a1a2e",
  },
  assetBundlePatterns: ["**/*"],
  ios: {
    supportsTablet: true,
    bundleIdentifier: "org.blindassistant.app",
    // VoiceOver accessibility hint for app selection
    infoPlist: {
      NSMicrophoneUsageDescription:
        "Blind Assistant needs microphone access to receive your voice commands.",
      NSSpeechRecognitionUsageDescription:
        "Blind Assistant uses speech recognition to understand your requests.",
    },
  },
  android: {
    package: "org.blindassistant.app",
    // TalkBack reads the app name from this label
    adaptiveIcon: {
      foregroundImage: "./assets/adaptive-icon.png",
      backgroundColor: "#1a1a2e",
    },
    permissions: [
      "android.permission.RECORD_AUDIO",
      "android.permission.INTERNET",
    ],
  },
  web: {
    // Expo Web shares the same React Native components via react-native-web
    favicon: "./assets/favicon.png",
    output: "single",
    bundler: "metro",
  },
  plugins: [
    [
      "expo-av",
      {
        microphonePermission:
          "Allow Blind Assistant to access your microphone for voice input.",
      },
    ],
  ],
  extra: {
    // Backend API URL — localhost for dev; will be configurable for production
    apiBaseUrl: process.env.EXPO_PUBLIC_API_BASE_URL ?? "http://localhost:8000",
  },
};

export default config;
