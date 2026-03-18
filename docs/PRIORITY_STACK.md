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

## Current Stack (Phase 5 COMPLETE — Community Launch Ready)

**Phase 4 COMPLETE (Cycle 36)**: 0 axe violations (CI run 23231203014); 36 Chromium + 36 Firefox E2E all pass; iOS/Android sign-off done; Windows/macOS CLI+web sign-off done (ISSUE-043).
**Phase 5 COMPLETE (Cycle 38)**: Dorothy language simplification done (136 JS tests); GRANT_NARRATIVE.md created; 13 Dorothy E2E scenario tests passing; ISSUE-045 resolved.
**Phase 5 gate PASSED**: Dorothy scenario tests (setup → food ordering → Second Brain note → general questions) all green; no jargon; no dead ends.
**Community launch prep COMPLETE (Cycle 39)**: CONTRIBUTING.md expanded with blind contributor welcome, braille display callout, Dorothy persona explanation, JS test instructions, good-first-issue guide, commit format; 5 GitHub good-first-issues created (#92-#96); CHANGELOG v0.5.0 complete.
**CI hardening COMPLETE (Cycle 40)**: lint fix (issue #97/#98); WebKit E2E CI (issue #92); Dorothy E2E CI job (issue #96); 842 Python tests + 7 new WebKit tests.
**Jordan DeafBlind scenario COMPLETE (Cycle 41)**: 16 Jordan tests; braille formatter fix; shared accessibility helpers; NVDA/braille README; issues #93/#94/#95 closed; 858 tests total.
**Marcus power user scenario COMPLETE (Cycle 42)**: 31 Marcus tests; brief mode pipeline verified; financial disclosure survives brief mode; DRY web_app_available fixture; CI renamed to persona gate; 919 tests total.
**Telegram integration COMPLETE (Cycle 43)**: --telegram CLI flag; api_server_enabled forced; 6 new tests in test_main.py (9 total); ruff CI fix; 925 tests total.
**Node.js 24 migration COMPLETE (Cycle 44)**: checkout/setup-node/upload-artifact v4→v5 across all 5 workflow files; ISSUE-050 resolved; June 2026 deadline met.
**Device simulation CI COMPLETE (Cycle 45)**: Playwright screenshot tests (7 tests); named device-sim-screenshots/{browser}/ artifact in CI; Netlify deploy skips gracefully without secrets; Marcus test hang fixed (wait_for_confirmation mock missing).

| Priority | Item | Source | Added |
|----------|------|---------|-------|
| P4 | Netlify staging activation: configure NETLIFY_AUTH_TOKEN + NETLIFY_SITE_ID secrets so community members can test https://staging.blind-assistant.org with real NVDA+Chrome, TalkBack+Chrome, VoiceOver+Safari | cycle 45 review | 2026-03-18 |
| P4 | pytest-timeout: add pytest-timeout package + asyncio_timeout config so tests that block for DEFAULT_TIMEOUT (60s) fail fast instead of silently hanging in CI | cycle 45 review | 2026-03-18 |
| P5 | Education site deployment: deploy clients/education/ to learn.blind-assistant.org; document as a community touchpoint for blind contributors who prefer reading course material to browsing GitHub | cycle 45 creative | 2026-03-18 |

## Completed Items (Cycle 45 additions)

| Item | Completed | Cycle # |
|------|-----------|---------|
| Device simulation CI (P3): Playwright screenshot tests (7 tests in test_device_simulation_screenshots.py); named screenshots for initial load, app-ready, setup wizard, main screen, mobile 375x812, tablet 768x1024 across Chromium/Firefox/WebKit; separate device-sim-screenshots CI artifact; Netlify staging workflow skips gracefully without secrets; Marcus wait_for_confirmation hang fixed | 2026-03-18 | 45 |
| Marcus test hang fix: test_financial_disclosure_present_in_brief_mode and test_food_order_updates_have_no_jargon_for_marcus — added wait_for_confirmation mock alongside wait_for_response; 31 Marcus tests now run in 0.10s (was hanging 60s+ per test) | 2026-03-18 | 45 |

## Completed Items (Cycle 44 additions)

| Item | Completed | Cycle # |
|------|-----------|---------|
| Node.js 24 migration (P4): bumped actions/checkout, actions/setup-node, actions/upload-artifact from v4→v5 in all 5 workflow files; ISSUE-050 resolved; YAML validated | 2026-03-18 | 44 |

## Completed Items (Cycle 43 additions)

| Item | Completed | Cycle # |
|------|-----------|---------|
| Telegram integration (P3): --telegram flag in main.py; forces api_server_enabled=True; 6 new tests in test_main.py (test_start_services_starts_telegram_when_enabled, starts_both_telegram_and_api, does_not_start_telegram_when_disabled, main_telegram_flag_sets_telegram_enabled, main_telegram_flag_forces_api_server_enabled, main_no_telegram_flag_leaves_telegram_disabled) | 2026-03-18 | 43 |
| CI fix (P0): ruff format violation in test_marcus_scenario.py; GitHub issue #99 closed | 2026-03-18 | 43 |
| P4 Consolidate FORBIDDEN_JARGON: confirmed already resolved in Cycle 41 (no duplicate list in test_dorothy_scenario.py); item closed as done | 2026-03-18 | 43 |

## Completed Items (Cycle 42 additions)

| Item | Completed | Cycle # |
|------|-----------|---------|
| Marcus (power user) scenario tests: 31 tests in tests/accessibility/test_marcus_scenario.py — preamble trimming (6 preambles parametrized), brief mode in _format_response(), Second Brain jargon-free, financial disclosure survives brief mode, no dependency patterns | 2026-03-18 | 42 |
| DRY web_app_available fixture: extracted from 4 web E2E test files to tests/e2e/platforms/web/conftest.py; http.client import removed from 4 files | 2026-03-18 | 42 |
| CI dorothy-e2e job renamed to "Persona scenario gate (Dorothy, Jordan, Marcus)"; step description updated; artifact renamed | 2026-03-18 | 42 |

## Completed Items (Cycle 41 additions)

| Item | Completed | Cycle # |
|------|-----------|---------|
| ISSUE-093 RESOLVED: Jordan (DeafBlind) scenario tests — 16 tests in tests/accessibility/test_jordan_scenario.py; braille formatting, Second Brain text-only, food ordering text disclosure | 2026-03-18 | 41 |
| ISSUE-094 RESOLVED: Shared accessibility helpers extracted to tests/accessibility/helpers.py; assert_no_jargon (word-boundary), assert_no_visual_only_language, assert_braille_friendly, assert_financial_disclosure_present | 2026-03-18 | 41 |
| ISSUE-095 RESOLVED: Windows NVDA + VoiceOver on macOS + braille display README sections added | 2026-03-18 | 41 |
| _format_for_braille() fixed: word-wrap at 40 chars enforced (was sentence-split only, left 46+ char lines) | 2026-03-18 | 41 |
| Visual-only language fixed in orchestrator.py: "look at" → non-visual equivalents (2 strings) | 2026-03-18 | 41 |
| dorothy-e2e CI job expanded: now runs Jordan tests too (29 persona gate tests total) | 2026-03-18 | 41 |

## Completed Items (Cycle 40 additions)

| Item | Completed | Cycle # |
|------|-----------|---------|
| ISSUE-046 RESOLVED: ruff format lint failure (test_dorothy_scenario.py) fixed; CI unblocked (issues #97, #98 closed) | 2026-03-18 | 40 |
| WebKit E2E CI (issue #92 RESOLVED): webkit added to e2e-web CI job (install + --browser webkit run); test_main_screen_webkit.py with 7 VoiceOver+Safari tests | 2026-03-18 | 40 |
| Dorothy E2E CI job (issue #96 RESOLVED): dedicated 'dorothy-e2e' job in ci.yml runs 13 Dorothy/Alex scenario tests on every push; included in notify-failure gate | 2026-03-18 | 40 |

## Completed Items (Cycle 39 additions)

| Item | Completed | Cycle # |
|------|-----------|---------|
| Community launch prep COMPLETE: CONTRIBUTING.md expanded with blind contributor welcome section, braille display user callout, Dorothy persona explanation, JS/React Native test instructions, good-first-issue guide, commit message format; 5 GitHub good-first-issues created (issues #92-#96) covering WebKit E2E, deafblind user stories, food ordering accessibility assertion, Windows NVDA README, Dorothy E2E CI job | 2026-03-18 | 39 |
| CHANGELOG.md: v0.5.0 entry created for Phase 5 (Cycles 37-39) with all additions and fixes documented | 2026-03-18 | 39 |

## Completed Items (Cycle 38 additions)

| Item | Completed | Cycle # |
|------|-----------|---------|
| ISSUE-045 RESOLVED: 2 missed jargon strings in handleConfirmToken fixed (empty: "API token" → "connection code"; too-short: "API tokens" → "Connection codes"); 2 new regression tests; 136 JS tests total | 2026-03-18 | 38 |
| Full Dorothy scenario test — 13 E2E tests in tests/e2e/core/test_dorothy_scenario.py covering Dorothy (elder) + Alex (newly-blind): food ordering with risk disclosure, Second Brain save/query, general questions, installer language, financial disclosure plain-language | 2026-03-18 | 38 |
| Phase 5 COMPLETE — both gate criteria met: (1) Dorothy scenario tests pass (13 E2E tests); (2) GRANT_NARRATIVE.md exists | 2026-03-18 | 38 |

## Completed Items (Cycle 37 additions)

| Item | Completed | Cycle # |
|------|-----------|---------|
| Dorothy test — language simplification: "API token" → "connection code", "backend server" → "your computer", "passphrase" → "secret phrase" in SetupWizardScreen + installer; welcome screen "ask to repeat" affordance; actionable error messages; 6 new Dorothy test assertions; 134 JS tests | 2026-03-18 | 37 |
| GRANT_NARRATIVE.md created: problem statement (7M blind Americans), impact metrics (812+134 tests, 0 WCAG violations), 3 fundable milestones, budget narrative, sustainability plan | 2026-03-18 | 37 |
| ROADMAP.md updated: Phase 3 ✅ COMPLETE, Phase 4 ✅ COMPLETE (all deliverables listed), Phase 5 🔄 IN PROGRESS with test count table | 2026-03-18 | 37 |
| CHANGELOG.md updated: Phase 5 section added; Phase 4 reclassified as [v0.4.0] | 2026-03-18 | 37 |

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
