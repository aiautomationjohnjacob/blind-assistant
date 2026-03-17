/**
 * App.tsx — Metro/AppEntry.js shim for Expo 51 without expo-router.
 *
 * Expo's default entry point (node_modules/expo/AppEntry.js) looks for `App.tsx`
 * in the project root. Our app logic lives in `app/index.tsx` using the Expo
 * file-based layout convention (without the expo-router package). This shim
 * bridges the two: Metro resolves AppEntry.js → App.tsx → app/index.tsx.
 *
 * Do NOT add business logic here. All app logic belongs in app/index.tsx.
 */
export { default } from "./app/index";
