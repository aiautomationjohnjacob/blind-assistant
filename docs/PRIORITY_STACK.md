# Priority Stack — Ranked Backlog

> Maintained by the orchestrator. Updated every cycle.
> The orchestrator ALWAYS works from the top of this stack.
> Items are added by gap detection, persona feedback, security audits, and user stories.
> Items are removed when completed and committed.

## How Priority is Determined

1. **P0 — BLOCKING**: Security vulnerabilities, broken builds, data loss risk
2. **P1 — SHOWSTOPPER**: A blind user persona cannot complete a core task
3. **P2 — PHASE GATE**: Required deliverable for current phase to complete
4. **P3 — KNOWN GAP**: Detected gap not yet addressed (see OPEN_ISSUES.md)
5. **P4 — IMPROVEMENT**: Enhancement that improves the product meaningfully
6. **P5 — CREATIVE**: New idea or integration opportunity worth exploring

## Current Stack (Phase 5 — Polish & Community Ready)

**Phase 4 COMPLETE (Cycle 36)**: 0 axe violations (CI run 23231203014); 36 Chromium + 36 Firefox E2E all pass; iOS/Android sign-off done; Windows/macOS CLI+web sign-off done (ISSUE-043).
**Phase 5 goal**: Dorothy persona test — newly-blind elder user completes setup and uses app without sighted help; grant-writer produces GRANT_NARRATIVE.md.

| Priority | Item | Source | Added |
|----------|------|---------|-------|
| P2 | Dorothy test: newly-blind-user + blind-elder-user persona review of setup wizard and main screen — identify simplicity gaps, confusing language, missing affordances | Phase 5 gate | 2026-03-18 |
| P2 | Simplicity audit of voice strings — review installer + voice responses for jargon-free, patient language appropriate for non-technical newly-blind users | Phase 5 gate | 2026-03-18 |
| P2 | ROADMAP.md + CHANGELOG.md update — mark Phase 4 complete; add Phase 5 milestones with Dorothy test as gate; update test counts (812 Python, 128 JS, 36+36 E2E) | documentation | 2026-03-18 |
| P2 | Grant narrative: grant-writer produces GRANT_NARRATIVE.md (Phase 5 completion criterion per CLAUDE.md) | Phase 5 gate | 2026-03-18 |
| P3 | Community launch prep: open-source-steward reviews CONTRIBUTING.md, identifies good-first-issues, ensures blind contributors feel welcomed | community | 2026-03-18 |
| P3 | VoiceOver+Safari CI: add WebKit E2E tests — Playwright WebKit is not real Safari + VoiceOver, but provides closer coverage than Chromium alone | accessibility | 2026-03-18 |
| P3 | Device simulation CI: Android emulator (AVD) + Playwright for web E2E in CI | device-simulator agent | 2026-03-17 |
| P3 | Telegram integration: secondary/super-user channel only; voice-guided Telegram setup for power users who want remote access; NOT required for primary blind user experience | cloud-architect | 2026-03-17 |

## Completed Items (Cycle 36 additions)

| Item | Completed | Cycle # |
|------|-----------|---------|
| ISSUE-039 RESOLVED: 0 axe violations confirmed — root cause was axe auditing blank loading spinner; CI run 23231203014: 36 Chromium + 36 Firefox E2E + 4 axe-core ALL PASS | 2026-03-18 | 36 |
| Phase 4 completion assessment: all criteria met — zero critical axe violations ✓, iOS/Android ✓, Windows/macOS CLI+web sign-off ✓ (ISSUE-043), security/ethics sign-off ✓ | 2026-03-18 | 36 |
| Windows/macOS accessibility sign-off (ISSUE-043): installer NVDA-safe; web WCAG 2.1 AA confirmed; native GUI deferred | 2026-03-18 | 36 |
| Closed 6 stale GitHub CI failure issues (86, 87, 88, 89, 90, 91) | 2026-03-18 | 36 |
| PHASE 4 COMPLETE — WCAG 2.1 AA on web confirmed; all platform sign-offs done | 2026-03-18 | 36 |

## Completed Items (Cycle 35 additions)

| Item | Completed | Cycle # |
|------|-----------|---------|
| ISSUE-041: react-dom@19.2.4 → 18.2.0 pinned; ALL 33 Chromium web E2E PASS (CI run 23230759864) | 2026-03-18 | 35 |
| ISSUE-042: Firefox browser binary added to e2e-web CI job install step | 2026-03-18 | 35 |
| _wait_for_app_ready() timeout increased to 30s; conftest.py add_init_script() diagnostic added | 2026-03-18 | 35 |

## Completed Items (Cycle 33 additions)

| Item | Completed | Cycle # |
|------|-----------|---------|
| ISSUE-040: MainScreen.tsx aria-live regions always rendered (WCAG 4.1.3 fix); hiddenLiveRegion style; 128 JS tests pass | 2026-03-18 | 33 |
| _wait_for_app_ready() timeout 5s→15s in test_main_screen_chromium.py, test_food_ordering_web.py, test_wcag_axe_audit.py; expected to fix 8 CI test failures | 2026-03-18 | 33 |

## Completed Items (Cycle 32 additions)

| Item | Completed | Cycle # |
|------|-----------|---------|
| Check axe-core CI gate results (Cycle 31 push): 0 critical, 0 serious, 1 unidentified moderate; ISSUE-039 logged | 2026-03-18 | 32 |
| Fix 10 web E2E test failures: Python `or`→`||` bug, React hydration race, setup wizard vs main screen mismatch; _wait_for_app_ready() added | 2026-03-18 | 32 |
| Add _wait_for_app_ready() to axe-core audit tests (test_wcag_axe_audit.py) | 2026-03-18 | 32 |
| ISSUE-038 resolved: web E2E hydration race documented and fixed | 2026-03-18 | 32 |
| Closed stale GitHub CI issues 84 and 85 | 2026-03-18 | 32 |

## Completed Items (Cycle 31 additions)

| Item | Completed | Cycle # |
|------|-----------|---------|
| Verify skip link in expo export: confirmed `dist/index.html` includes skip link + main landmark from `public/index.html` template | 2026-03-17 | 31 |
| ISSUE-037: tabindex="-1" added to #main-content in public/index.html; skip link now actually routes keyboard focus (not just scroll); dist rebuilt | 2026-03-17 | 31 |
| 5 new TestFocusManagement E2E tests: skip link focus routing, voice button reachability, invisible focus, aria-live coverage (Cycle 31) | 2026-03-17 | 31 |
| 1 new TestPageStructure test: test_skip_link_target_has_tabindex_minus_one (Cycle 31) | 2026-03-17 | 31 |
| test_can_reach_main_button_by_tab corrected — fixed assertion for skip link Tab order (Cycle 31) | 2026-03-17 | 31 |

## Completed Items (Cycle 30 additions)

| Item | Completed | Cycle # |
|------|-----------|---------|
| Skip link + main landmark: `clients/mobile/public/index.html` custom Expo template; skip-to-main-content link first focusable element (WCAG 2.4.1); `<div role="main">` wraps React root | 2026-03-17 | 30 |
| SetupWizardScreen token step live region: `accessibilityLiveRegion="polite"` added to instructions Text; 1 new JS test; 128 JS total | 2026-03-17 | 30 |
| Web structure E2E tests: 5 new tests in TestPageStructure — skip link first focusable, target exists, main landmark, heading structure, heading labels | 2026-03-17 | 30 |
| Documentation steward (Cycle 30): CHANGELOG Phase 4 section (Cycles 28-30); README Telegram demoted to optional; test counts updated | 2026-03-17 | 30 |

## Completed Items (Cycle 29 additions)

| Item | Completed | Cycle # |
|------|-----------|---------|
| ISSUE-034: All 26 web E2E tests converted from async to sync playwright API; CI pipefail fixed; ISSUE-034 resolved | 2026-03-18 | 29 |
| ISSUE-035: axe-core bundled locally (axe.min.js, 555KB); CDN dependency eliminated; _inject_axe() uses add_script_tag(path=...); ISSUE-035 resolved | 2026-03-18 | 29 |
| ISSUE-036: VoiceOver live region moved from View to Text in MainScreen.tsx (transcript+response); accessibilityActions added to Pressable button; +6 JS tests; 127 JS total | 2026-03-18 | 29 |

## Completed Items (Cycle 28 additions)

| Item | Completed | Cycle # |
|------|-----------|---------|
| ISSUE-033: `accessibilityRole="text"` → Platform.OS guard across 10 occurrences in MainScreen.tsx (3) + SetupWizardScreen.tsx (7); 4 new JS tests; 121 JS total | 2026-03-18 | 28 |
| Phase 4 axe-core WCAG CI gate: `a11y-audit` job in ci.yml + test_wcag_axe_audit.py (4 tests: critical WCAG, contrast, naming, ARIA role validity) | 2026-03-18 | 28 |
| Stale GitHub CI issues 80-83 closed | 2026-03-18 | 28 |

## Completed Items (Cycle 27 additions)

| Item | Completed | Cycle # |
|------|-----------|---------|
| ISSUE-032: test_main.py ruff violations fixed (I001, SIM105/SIM117/S110); CI lint passing | 2026-03-18 | 27 |
| SECURITY_MODEL.md §10: VALID_EXTRA_PREFS 422 documented as intentional information disclosure | 2026-03-18 | 27 |
| Voice clear preferences: `clear_preferences` intent + ConfirmationGate handler + APIServer dispatch; 14 new tests; 812 Python unit tests total | 2026-03-18 | 27 |
| Phase 3 → Phase 4 transition: CYCLE_STATE.md updated; Phase 3 complete | 2026-03-18 | 27 |

## Completed Items (Cycle 26 additions)

| Item | Completed | Cycle # |
|------|-----------|---------|
| ISSUE-031: DELETE /profile/preferences endpoint; confirm=true required; MCPMemoryClient.clear_user_data() exposed; 204 No Content; graceful degradation; CORS updated; 8 new unit tests | 2026-03-18 | 26 |
| Phase 3 completion assessment: Android TalkBack CI ✓, iOS VoiceOver CI ✓, Web E2E CI ✓ — device screenshot artifacts deferred to release CI (expected) | 2026-03-18 | 26 |
| 798 Python unit tests total (+8 from Cycle 26); ruff clean; mypy 0 errors | 2026-03-18 | 26 |

## Completed Items (Cycle 25 additions)

| Item | Completed | Cycle # |
|------|-----------|---------|
| ISSUE-030: VALID_EXTRA_PREFS frozenset in api_server.py; PUT /profile returns 422 on unknown extra keys; all-or-nothing validation; audit log at WARNING; 8 new tests | 2026-03-18 | 25 |
| MCPMemoryClient wired into main.py start_services() production API server startup; graceful degradation if constructor raises; 3 new tests in test_main.py | 2026-03-18 | 25 |
| Android TalkBack CI v0.3.2 verified: run 23223747818 PASSED | 2026-03-18 | 25 |
| 790 Python unit tests total (+11 from Cycle 25); ruff clean; mypy 0 errors | 2026-03-18 | 25 |

## Completed Items (Cycle 24 additions)

| Item | Completed | Cycle # |
|------|-----------|---------|
| MCPMemoryClient wired into GET/PUT /profile in api_server.py: 14 new tests; ProfileUpdateRequest added; preferences persist across server restarts | 2026-03-18 | 24 |
| Education site tests fixed: moved to src/__tests__/, 41 new Jest tests, coverage 82.7%, npm ci in CI, NavLink aria-current corrected | 2026-03-18 | 24 |
| CI failure fixed: test_record_with_vad_sync now uses patch.dict(sys.modules, {'webrtcvad': None}); 779 Python unit tests | 2026-03-18 | 24 |

## Completed Items (Cycle 23 additions)

| Item | Completed | Cycle # |
|------|-----------|---------|
| MCP memory server: MCPMemoryClient in mcp_memory.py; context.py TODO resolved; 33 new tests; 765 Python unit tests | 2026-03-18 | 23 |
| Education website scaffold: clients/education/ React site; AudioPlayer; CourseCard; 5 pages; WCAG 2.1 AA; 39 Jest tests; test-education CI | 2026-03-18 | 23 |
| Android TalkBack CI backslash bug fixed: e2e-android.yml script field now single-line pytest; v0.3.2 tag pushed | 2026-03-18 | 23 |

## Completed Items (Cycle 21 additions)

| Item | Completed | Cycle # |
|------|-----------|---------|
| ROADMAP.md rewritten: Phases 1+2 checked off, Phase 3 current state with 16 items completed, Phase 4+5 milestones defined, tech stack table added | 2026-03-17 | 21 |
| CONTRIBUTING.md: added ROADMAP.md link alongside FEATURE_PRIORITY.md under "Find something to work on" | 2026-03-17 | 21 |
| v0.3.0 release tag pushed: triggers e2e-android (AVD) + ios-e2e.yml (macOS Simulator) CI workflows | 2026-03-17 | 21 |

## Completed Items (Cycle 22 additions)

| Item | Completed | Cycle # |
|------|-----------|---------|
| iOS VoiceOver CI verified: run 23222358997, 6 PASSED, 2 SKIPPED (backend not reachable — expected) | 2026-03-18 | 22 |
| Android TalkBack CI structural bug fixed: e2e-android.yml created (was unreachable in ci.yml) | 2026-03-18 | 22 |
| Voice Activity Detection (ISSUE-002): transcribe_microphone_with_vad() + _record_with_vad_sync(); webrtcvad-wheels; +12 tests | 2026-03-18 | 22 |
| PIL/Playwright screenshot fallback (ISSUE-003): _capture_with_pil() + _capture_with_playwright() in ScreenObserver; +9 tests | 2026-03-18 | 22 |
| 732 Python unit tests total (+19 from Cycle 22); ruff clean; mypy 0 errors | 2026-03-18 | 22 |

## Completed Items (Cycle 20 additions)

| Item | Completed | Cycle # |
|------|-----------|---------|
| Unit tests for ADB/simctl helpers: 72 new tests covering _parse_content_descriptions, _parse_bounds, _has_visual_only_language, _has_double_tap_hint — device-free, 0.08s | 2026-03-17 | 20 |
| Documentation-steward run: CHANGELOG.md updated through Cycle 19; CONTRIBUTING.md setup steps corrected; 8 missing docstrings added | 2026-03-17 | 20 |

## Completed Items (Cycle 19 additions)

| Item | Completed | Cycle # |
|------|-----------|---------|
| Android TalkBack E2E test infrastructure: ADBClient wrapper + 8 tests (conftest.py + test_food_ordering_talkback.py) | 2026-03-17 | 19 |
| iOS VoiceOver E2E test infrastructure: SimctlClient wrapper + 9 tests (conftest.py + test_food_ordering_voiceover.py) | 2026-03-17 | 19 |
| CI path bug fixed: e2e-android job now uses tests/e2e/platforms/android/ (was tests/e2e/android/) | 2026-03-17 | 19 |
| ios-e2e.yml: macOS GitHub Actions workflow for iOS VoiceOver tests on release tags | 2026-03-17 | 19 |
| pyproject.toml: android + ios pytest marks registered | 2026-03-17 | 19 |
| ISSUE-029: Netlify operator setup docs added to README.md | 2026-03-17 | 19 |

## Completed Items (Cycle 18 additions)

| Item | Completed | Cycle # |
|------|-----------|---------|
| netlify.toml + deploy-staging.yml: web app auto-deploys to Netlify on push to main | 2026-03-17 | 18 |
| 11 new food ordering web E2E accessibility tests (keyboard nav, aria-live, focus management) | 2026-03-17 | 18 |
| WEB_APP_URL env var override in web E2E tests (enables staging URL testing) | 2026-03-17 | 18 |
| CSP fixed: no localhost in production CSP; connect-src restricted to api.blind-assistant.org | 2026-03-17 | 18 |

## Completed Items

| Item | Completed | Cycle # |
|------|-----------|---------|
| Agent network setup (20 agents) | 2026-03-17 | 0 |
| GitHub repo + MCP integration | 2026-03-17 | 0 |
| Autonomous loop infrastructure | 2026-03-17 | 0 |
| Product brief with synthesis vision | 2026-03-17 | 0 |
| docs/GAP_ANALYSIS.md | 2026-03-17 | 1 |
| docs/INTEGRATION_MAP.md | 2026-03-17 | 1 |
| docs/SECURITY_MODEL.md | 2026-03-17 | 1 |
| docs/ETHICS_REQUIREMENTS.md | 2026-03-17 | 1 |
| docs/ARCHITECTURE.md | 2026-03-17 | 1 |
| docs/USER_STORIES.md (21 stories, 5 personas) | 2026-03-17 | 1 |
| docs/FEATURE_PRIORITY.md | 2026-03-17 | 1 |
| src/ project scaffold (Python, 29 source files) | 2026-03-17 | 1 |
| requirements.txt (pinned dependencies) | 2026-03-17 | 1 |
| config.yaml (non-secret configuration) | 2026-03-17 | 1 |
| README.md (screen-reader-friendly, voice setup guide) | 2026-03-17 | 1 |
| .gitignore (credential and vault exclusions) | 2026-03-17 | 1 |
| tools/registry.yaml (curated tool registry) | 2026-03-17 | 1 |
| installer/install.py (voice-guided installer skeleton) | 2026-03-17 | 1 |
| Phase 1: Discovery & Architecture — COMPLETE | 2026-03-17 | 1 |
| voice_local.py (local voice interface) | 2026-03-17 | 2 |
| second_brain/query.py (voice query layer over vault) | 2026-03-17 | 2 |
| Orchestrator real intent routing (screen/note/query/general) | 2026-03-17 | 2 |
| Vault microsecond filename uniqueness fix | 2026-03-17 | 2 |
| 244 unit tests (encryption, vault, orchestrator, security) | 2026-03-17 | 2 |
| conftest.py suppress_audio ImportError fix | 2026-03-17 | 2 |
| Voice local interface stub (microphone + speaker) | 2026-03-17 | 2 |
| Unit tests: security/credentials, disclosure, encryption, vault | 2026-03-17 | 2 |
| pyproject.toml pythonpath fix (no manual PYTHONPATH needed) | 2026-03-17 | 3 |
| ISSUE-001 fix: _get_vault passphrase prompt recovery (10 tests) | 2026-03-17 | 3 |
| TTS unit tests: synthesize_speech, ElevenLabs, pyttsx3, speak_locally (14 tests) | 2026-03-17 | 3 |
| STT unit tests: transcribe_audio, singleton model, transcribe_microphone (11 tests) | 2026-03-17 | 3 |
| Total test count: 279 (was 244) | 2026-03-17 | 3 |
| ARCH DECISION (ISSUE-009): React Native + Expo for all client apps | 2026-03-17 | 4 |
| REST API server (ISSUE-008): FastAPI /query /remember /describe /task /profile /health | 2026-03-17 | 4 |
| ISSUE-005: UserContext.clear_sensitive() added (4 tests) | 2026-03-17 | 4 |
| ISSUE-006: configurable passphrase timeout from config.yaml (3 tests) | 2026-03-17 | 4 |
| Telegram de-emphasis: main.py default + telegram_bot.py docstring corrected | 2026-03-17 | 4 |
| Total test count: 314 (was 279) | 2026-03-17 | 4 |
| ISSUE-007: Voice E2E demo — 9 E2E tests, pipeline proven end-to-end | 2026-03-17 | 5 |
| Wake-word-only bug fix in voice_local.py ("assistant" alone now prompts "Yes?") | 2026-03-17 | 5 |
| 25 unit tests for VoiceLocalInterface (test_voice_local.py) | 2026-03-17 | 5 |
| React Native Expo skeleton: clients/mobile/ with MainScreen.tsx + API client | 2026-03-17 | 5 |
| 32 JS tests for API client + MainScreen accessibility (jest-expo) | 2026-03-17 | 5 |
| Multi-platform E2E test stubs (Web/Android/iOS/Desktop) per ISSUE-010 | 2026-03-17 | 5 |
| Total test count: 348 Python passed + 21 skipped; 32 JS tests (requires npm install) | 2026-03-17 | 5 |
| ISSUE-014: JS CI job ('test-js') added to ci.yml; 77 JS tests now in CI (was 32) | 2026-03-17 | 6 |
| ISSUE-013: SetupWizardScreen + useSecureStorage + app/index.tsx rewrite; 63 new JS tests | 2026-03-17 | 6 |
| ISSUE-012: Dead code wake_word_found removed from voice_local.py | 2026-03-17 | 6 |
| ISSUE-011: RateLimitMiddleware added to api_server.py; 8 new Python tests; configurable | 2026-03-17 | 6 |
| Total test count: 356 Python (347 unit + 9 E2E, 21 skipped); 77 JS tests in CI | 2026-03-17 | 6 |
| ISSUE-015: Real voice recording in MainScreen — useAudioRecorder hook + 2-press flow | 2026-03-17 | 7 |
| Backend POST /transcribe endpoint (base64 audio → Whisper STT); 7 Python tests | 2026-03-17 | 7 |
| JS API client: transcribe() method + TranscribeRequest/Response types; 7 tests | 2026-03-17 | 7 |
| ISSUE-016: importantForAccessibility="yes" added to SetupWizardScreen TextInput | 2026-03-17 | 7 |
| ISSUE-017: URL scheme validation in saveApiBaseUrl() with error message; 7 tests | 2026-03-17 | 7 |
| Total test count: 363 Python (354 unit + 9 E2E, 21 skipped); 114 JS tests | 2026-03-17 | 7 |
| Tool registry + installer (Cycle 8): 36 registry tests, 23 planner tests, ISSUE-018 /transcribe 413 limit | 2026-03-17 | 8 |
| Total test count Cycle 8: 426 Python (417 unit + 9 E2E, 21 skipped); 114 JS tests | 2026-03-17 | 8 |
| BrowserTool (Playwright wrapper): 24 unit tests; _handle_order_food: 12 unit tests; 8 E2E food ordering tests | 2026-03-17 | 9 |
| order_food/order_groceries wired to real handler (not stub); risk disclosure + 2-step confirmation in place | 2026-03-17 | 9 |
| Total test count Cycle 9: 470 Python (453 unit + 17 E2E, 21 skipped); 114 JS tests | 2026-03-17 | 9 |
| CI: 45 ruff errors resolved; pip-audit openai-whisper setuptools fix; CI green | 2026-03-17 | 10 |
| Food ordering checkout loop: 11-step conversational flow; 5 Claude helpers; 12 new unit tests; 4 E2E updated | 2026-03-17 | 10 |
| ConfirmationGate.wait_for_response() added (5 tests) | 2026-03-17 | 10 |
| Documentation: README.md updated (Telegram demoted), CHANGELOG.md created | 2026-03-17 | 10 |
| **PHASE 2 COMPLETE** — food ordering by voice end-to-end milestone reached | 2026-03-17 | 10 |
| Total test count Cycle 10: 482 Python (465 unit + 17 E2E, 21 skipped); 114 JS tests | 2026-03-17 | 10 |
| a11y: VoiceOver hint fix (7 "Double-tap" → outcome-first accessibilityHints) | 2026-03-17 | 11 |
| a11y: haptic recording cue (Medium on start, Light on stop) + 3 new tests | 2026-03-17 | 11 |
| a11y: importantForAccessibility="no-hide-descendants" → "yes" on SetupWizardScreen progress Text | 2026-03-17 | 11 |
| ISSUE-004: ResponseCallback type alias + 9 annotated method signatures in orchestrator.py | 2026-03-17 | 11 |
| Cross-platform accessibility audit (code-level): VoiceOver/TalkBack issues found + fixed | 2026-03-17 | 11 |
| Total test count Cycle 11: 465 Python (unchanged); 117 JS tests (was 114, +3 haptic tests) | 2026-03-17 | 11 |
| ISSUE-021: 11 real Playwright integration tests in tests/integration/test_browser_tool_real.py; CI job 'integration-browser' added | 2026-03-17 | 12 |
| ISSUE-020: "Double-tap to activate" platform hint removed from MainScreen.tsx; Platform import + platformHint style removed | 2026-03-17 | 12 |
| Total test count Cycle 12: 482 Python (unchanged); 117 JS (unchanged); +11 integration tests (skip locally) | 2026-03-17 | 12 |
| ISSUE-022: 56 mypy type errors fixed across 7 src/ files (from __future__ annotations + assert narrowing + bytes casts) | 2026-03-17 | 13 |
| CI: openai-whisper setuptools build fix applied to test + integration-browser jobs (was already in security-audit) | 2026-03-17 | 13 |
| Total test count Cycle 13: 482 Python (unchanged); 117 JS (unchanged); mypy reports 0 errors in 32 source files | 2026-03-17 | 13 |
| CI fully green (Cycle 14): 11 CVEs patched (cryptography→46, Pillow→12.1.1, starlette→0.49.1, fastapi→0.135.1); pip-audit switched to installed-env mode; 5 new mypy errors from updated stubs fixed; Playwright libasound2 workaround | 2026-03-17 | 14 |
| Total test count Cycle 14: 482 Python (unchanged); 117 JS (unchanged); ALL 7 CI jobs green on run 23218631525 | 2026-03-17 | 14 |
| ISSUE-023: Batch-closed 79 stale GitHub CI-failure issues (d593482) | 2026-03-17 | 14 |
| project-inspector gap scan (Cycle 15): 5 new issues found (ISSUE-024 through ISSUE-028) | 2026-03-17 | 15 |
| ISSUE-024: App.tsx shim added — Expo web export now works (npx expo export --platform web) | 2026-03-17 | 15 |
| ISSUE-025: CI e2e-web job rebuilt — builds Expo bundle, serves dist/, runs Playwright tests | 2026-03-17 | 15 |
| ISSUE-026: test_food_ordering.py E2E test fixed — context_manager mocked in test helper | 2026-03-17 | 15 |
| ISSUE-027: e2e + web pytest markers registered in pyproject.toml | 2026-03-17 | 15 |
| 11 web E2E accessibility tests written (WCAG 2.1 AA: keyboard nav, ARIA, lang, title, focus) | 2026-03-17 | 15 |
| Total test count Cycle 15: 482 Python (unchanged); 117 JS (unchanged); 11 web E2E tests (skip locally, run in CI) | 2026-03-17 | 15 |
| ISSUE-028: 118 new unit tests — test_telegram_bot.py (24), test_query.py (49), test_redaction.py (27), test_screen_observer.py (18) | 2026-03-17 | 16 |
| Ruff format CI blocker fixed (Cycle 15 web E2E files: conftest.py + test_main_screen_chromium.py) | 2026-03-17 | 16 |
| Total test count Cycle 16: 583 Python unit tests (was 465 Python + was counting separately); ruff lint+format clean | 2026-03-17 | 16 |
| Voice installer refactored: Telegram demoted to optional Step 5; _setup_native_app() added as Step 1 (TalkBack/VoiceOver); server address discovery (socket IP); 58 new installer tests | 2026-03-17 | 17 |
| Web E2E CI confirmed green: CI run 23219936377 all 7 jobs green including e2e-web (Playwright Chromium + Firefox accessibility tests) | 2026-03-17 | 17 |
| Total test count Cycle 17: 641 Python unit tests (+58 installer); ruff clean | 2026-03-17 | 17 |
