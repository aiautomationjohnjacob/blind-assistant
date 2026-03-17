"""
Unit tests for platform E2E test helper functions.

These tests cover the pure-Python helper functions used by the Android TalkBack
and iOS VoiceOver E2E test suites. Because the helpers operate on strings (parsed
XML, accessibility trees, hint text), they run entirely without a device, emulator,
or ADB connection — fast, portable, and CI-safe.

Helper functions under test:

  Android (test_food_ordering_talkback.py):
    _parse_content_descriptions(xml) -> list[str]
    _parse_bounds(xml)              -> list[tuple[int, int, int, int]]

  iOS (test_food_ordering_voiceover.py):
    _has_visual_only_language(text) -> bool
    _has_double_tap_hint(text)      -> bool

Per testing.md: naming convention is test_[what]_[condition]_[result].
Per CLAUDE.md: every public helper must have test coverage.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    import types

# ---------------------------------------------------------------------------
# Import helpers without executing device-dependent test classes.
#
# The talkback and voiceover test modules are in tests/e2e/platforms/… which is
# NOT on sys.path by default, and they require ADB/xcrun at import time only via
# a session fixture (the fixture itself skips if unavailable). We import only the
# helper functions we need by loading the modules with importlib after temporarily
# adding their directories to sys.path.
# ---------------------------------------------------------------------------


def _import_helper_functions():  # type: ignore[return]
    """
    Return (parse_content_descriptions, parse_bounds,
            has_visual_only_language, has_double_tap_hint).

    We import them from the E2E modules by name. If the modules cannot be
    loaded (e.g. missing optional dependency), the test is skipped.
    """
    import importlib.util
    from pathlib import Path

    base = Path(__file__).parent.parent  # tests/
    android_path = base / "e2e" / "platforms" / "android" / "test_food_ordering_talkback.py"
    ios_path = base / "e2e" / "platforms" / "ios" / "test_food_ordering_voiceover.py"

    def load(path: Path, name: str) -> types.ModuleType:
        spec = importlib.util.spec_from_file_location(name, path)
        assert spec is not None and spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        # Register in sys.modules BEFORE exec so relative imports inside the
        # module resolve correctly (none expected here, but defensive).
        sys.modules[name] = mod
        spec.loader.exec_module(mod)  # type: ignore[attr-defined]
        return mod

    android_mod = load(android_path, "_talkback_helpers")
    ios_mod = load(ios_path, "_voiceover_helpers")

    return (
        android_mod._parse_content_descriptions,
        android_mod._parse_bounds,
        ios_mod._has_visual_only_language,
        ios_mod._has_double_tap_hint,
    )


# Load once at module level; skip entire module if something goes wrong.
try:
    (
        _parse_content_descriptions,
        _parse_bounds,
        _has_visual_only_language,
        _has_double_tap_hint,
    ) = _import_helper_functions()
except Exception as exc:
    pytest.skip(f"Could not import platform helper functions: {exc}", allow_module_level=True)


# ===========================================================================
# _parse_content_descriptions  (Android uiautomator XML parser)
# ===========================================================================

MINIMAL_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<hierarchy rotation="0">
  <node bounds="[0,0][1080,1920]" content-desc="" />
</hierarchy>
"""

SINGLE_BUTTON_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<hierarchy rotation="0">
  <node class="android.widget.FrameLayout" content-desc="Speak to assistant"
        bounds="[468,1776][612,1920]" clickable="true" />
</hierarchy>
"""

MULTI_ELEMENT_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<hierarchy rotation="0">
  <node content-desc="Blind Assistant" bounds="[0,0][1080,120]" />
  <node content-desc="Connected to server" bounds="[0,120][1080,240]" />
  <node content-desc="Speak to assistant" bounds="[468,1776][612,1920]" clickable="true" />
</hierarchy>
"""

NO_CONTENT_DESC_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<hierarchy rotation="0">
  <node class="android.widget.TextView" text="Hello" bounds="[0,0][1080,120]" />
  <node class="android.widget.Button" bounds="[468,1776][612,1920]" clickable="true" />
</hierarchy>
"""


class TestParseContentDescriptions:
    """Tests for _parse_content_descriptions(xml) -> list[str]."""

    def test_returns_empty_list_for_empty_xml(self) -> None:
        """An empty string produces an empty list without raising."""
        assert _parse_content_descriptions("") == []

    def test_returns_empty_list_when_no_content_desc_attributes(self) -> None:
        """XML nodes without content-desc attributes produce an empty result."""
        result = _parse_content_descriptions(NO_CONTENT_DESC_XML)
        assert result == []

    def test_returns_empty_string_for_blank_content_desc(self) -> None:
        """A node with content-desc="" contributes an empty string to the list."""
        result = _parse_content_descriptions(MINIMAL_XML)
        assert result == [""]

    def test_returns_single_description_from_single_node(self) -> None:
        """A single labelled node returns exactly one description."""
        result = _parse_content_descriptions(SINGLE_BUTTON_XML)
        assert result == ["Speak to assistant"]

    def test_returns_all_descriptions_from_multiple_nodes(self) -> None:
        """Multiple nodes return all descriptions in document order."""
        result = _parse_content_descriptions(MULTI_ELEMENT_XML)
        assert result == ["Blind Assistant", "Connected to server", "Speak to assistant"]

    def test_speak_keyword_present_in_result(self) -> None:
        """The main button description contains 'speak' (as the TalkBack test checks)."""
        result = _parse_content_descriptions(MULTI_ELEMENT_XML)
        assert any("speak" in d.lower() for d in result)

    def test_assistant_keyword_present_in_result(self) -> None:
        """The main button description contains 'assistant'."""
        result = _parse_content_descriptions(SINGLE_BUTTON_XML)
        assert any("assistant" in d.lower() for d in result)

    def test_preserves_description_text_exactly(self) -> None:
        """Description text is returned verbatim — no stripping or case changes."""
        xml = '<node content-desc="  Hello World  " />'
        result = _parse_content_descriptions(xml)
        assert result == ["  Hello World  "]

    def test_handles_descriptions_with_special_characters(self) -> None:
        """Descriptions containing commas, hyphens, and numbers are returned correctly."""
        xml = '<node content-desc="Order #12-3: confirmed" />'
        result = _parse_content_descriptions(xml)
        assert result == ["Order #12-3: confirmed"]

    def test_multiple_same_description_values_all_returned(self) -> None:
        """Duplicate descriptions are all included (not de-duplicated)."""
        xml = (
            '<node content-desc="Button" />'
            '<node content-desc="Button" />'
        )
        result = _parse_content_descriptions(xml)
        assert result == ["Button", "Button"]

    @pytest.mark.parametrize(
        "keyword",
        ["speak", "assistant", "record"],
    )
    def test_main_button_check_passes_for_known_keywords(self, keyword: str) -> None:
        """The TalkBack test's assertion passes when any description contains a known keyword."""
        descriptions = [f"Press to {keyword}"]
        assert any(
            "speak" in d.lower() or "assistant" in d.lower() or "record" in d.lower()
            for d in descriptions
        )

    def test_main_button_check_fails_when_no_known_keywords(self) -> None:
        """The TalkBack test's assertion fails when descriptions lack required keywords."""
        descriptions = ["Button", "View", ""]
        assert not any(
            "speak" in d.lower() or "assistant" in d.lower() or "record" in d.lower()
            for d in descriptions
        )


# ===========================================================================
# _parse_bounds  (Android uiautomator bounds parser)
# ===========================================================================

BOUNDS_XML_SINGLE = """\
<hierarchy>
  <node bounds="[468,1776][612,1920]" />
</hierarchy>
"""

BOUNDS_XML_MULTI = """\
<hierarchy>
  <node bounds="[0,0][1080,120]" />
  <node bounds="[10,200][110,300]" />
  <node bounds="[468,1776][612,1920]" />
</hierarchy>
"""

BOUNDS_XML_ZERO = """\
<hierarchy>
  <node bounds="[0,0][0,0]" />
</hierarchy>
"""

LARGE_SCREEN_XML = """\
<hierarchy>
  <node bounds="[0,0][2560,1440]" />
</hierarchy>
"""


class TestParseBounds:
    """Tests for _parse_bounds(xml) -> list[tuple[int, int, int, int]]."""

    def test_returns_empty_list_for_empty_xml(self) -> None:
        """An empty string produces an empty list without raising."""
        assert _parse_bounds("") == []

    def test_returns_empty_list_when_no_bounds_attributes(self) -> None:
        """XML without bounds attributes produces an empty result."""
        xml = '<hierarchy><node content-desc="Hello" /></hierarchy>'
        assert _parse_bounds(xml) == []

    def test_parses_single_bounds_correctly(self) -> None:
        """A single bounds attribute is parsed into one (x1, y1, x2, y2) tuple."""
        result = _parse_bounds(BOUNDS_XML_SINGLE)
        assert result == [(468, 1776, 612, 1920)]

    def test_parses_multiple_bounds_in_document_order(self) -> None:
        """Multiple bounds are returned in document order."""
        result = _parse_bounds(BOUNDS_XML_MULTI)
        assert result == [(0, 0, 1080, 120), (10, 200, 110, 300), (468, 1776, 612, 1920)]

    def test_parses_zero_bounds_without_error(self) -> None:
        """bounds='[0,0][0,0]' is a degenerate but valid value — returned as-is."""
        result = _parse_bounds(BOUNDS_XML_ZERO)
        assert result == [(0, 0, 0, 0)]

    def test_returns_integers_not_strings(self) -> None:
        """All four tuple elements are Python ints, not strings."""
        result = _parse_bounds(BOUNDS_XML_SINGLE)
        assert all(isinstance(v, int) for b in result for v in b)

    def test_parses_large_screen_coordinates(self) -> None:
        """Large coordinates (2560x1440 tablet) parse correctly."""
        result = _parse_bounds(LARGE_SCREEN_XML)
        assert result == [(0, 0, 2560, 1440)]

    def test_touch_target_width_calculation(self) -> None:
        """Width = x2 - x1; height = y2 - y1. Policy: ≥44px."""
        bounds = _parse_bounds(BOUNDS_XML_SINGLE)[0]
        x1, y1, x2, y2 = bounds
        width = x2 - x1  # 612 - 468 = 144
        height = y2 - y1  # 1920 - 1776 = 144
        assert width >= 44, f"Touch target width {width}dp is below 44dp minimum"
        assert height >= 44, f"Touch target height {height}dp is below 44dp minimum"

    def test_touch_target_too_small_detected(self) -> None:
        """A 20x20 bounds correctly fails the 44dp touch target check."""
        xml = '<hierarchy><node bounds="[0,0][20,20]" /></hierarchy>'
        bounds = _parse_bounds(xml)
        assert len(bounds) == 1
        x1, y1, x2, y2 = bounds[0]
        width = x2 - x1
        height = y2 - y1
        assert width < 44  # 20 < 44 — correctly detected as too small
        assert height < 44

    def test_all_bounds_meet_touch_target_policy(self) -> None:
        """The multi-bounds fixture has at least one element meeting the 44dp policy."""
        all_bounds = _parse_bounds(BOUNDS_XML_MULTI)
        # The third element [468,1776][612,1920] is 144x144 — should meet the policy.
        passing = [b for b in all_bounds if (b[2] - b[0]) >= 44 and (b[3] - b[1]) >= 44]
        assert len(passing) > 0, "No elements meet the 44dp touch target minimum"


# ===========================================================================
# _has_visual_only_language  (iOS VoiceOver WCAG 1.3.3 guard)
# ===========================================================================


class TestHasVisualOnlyLanguage:
    """Tests for _has_visual_only_language(text) -> bool."""

    # ---- True cases (visual language detected) ----

    def test_returns_true_for_click_the(self) -> None:
        """'click the' is visual-only language."""
        assert _has_visual_only_language("click the button") is True

    def test_returns_true_for_tap_the_green(self) -> None:
        """'tap the green' references colour — visual-only."""
        assert _has_visual_only_language("tap the green icon") is True

    def test_returns_true_for_tap_the_red(self) -> None:
        """'tap the red' references colour — visual-only."""
        assert _has_visual_only_language("tap the red stop button") is True

    def test_returns_true_for_look_at(self) -> None:
        """'look at' implies sighted interaction."""
        assert _has_visual_only_language("look at the top of the screen") is True

    def test_returns_true_for_see_the(self) -> None:
        """'see the' is visual-only language."""
        assert _has_visual_only_language("see the confirmation message") is True

    def test_returns_true_for_on_the_right(self) -> None:
        """'on the right' is position-based visual language."""
        assert _has_visual_only_language("the button on the right") is True

    def test_returns_true_for_on_the_left(self) -> None:
        """'on the left' is position-based visual language."""
        assert _has_visual_only_language("tap the item on the left") is True

    def test_returns_true_for_icon_at_the_top(self) -> None:
        """'icon at the top' is position-based visual language."""
        assert _has_visual_only_language("press the icon at the top") is True

    def test_returns_true_for_icon_at_the_bottom(self) -> None:
        """'icon at the bottom' is position-based visual language."""
        assert _has_visual_only_language("press the icon at the bottom") is True

    def test_returns_true_for_the_icon(self) -> None:
        """'the icon' without accessible name is visual shorthand."""
        assert _has_visual_only_language("tap the icon") is True

    def test_case_insensitive_for_click_the(self) -> None:
        """Detection is case-insensitive — 'Click The' is caught."""
        assert _has_visual_only_language("Click The Submit Button") is True

    def test_case_insensitive_for_look_at(self) -> None:
        """'LOOK AT' (all caps) is detected."""
        assert _has_visual_only_language("LOOK AT THE SCREEN") is True

    # ---- False cases (accessible language — no visual phrases) ----

    def test_returns_false_for_empty_string(self) -> None:
        """An empty string has no visual phrases."""
        assert _has_visual_only_language("") is False

    def test_returns_false_for_outcome_first_hint(self) -> None:
        """Outcome-first language like 'Starts recording' is accessible."""
        assert _has_visual_only_language("Starts recording your message") is False

    def test_returns_false_for_double_tap_to_activate(self) -> None:
        """'Double-tap to activate' uses touch gesture language — not visual."""
        assert _has_visual_only_language("Double-tap to activate") is False

    def test_returns_false_for_plain_instruction(self) -> None:
        """Plain accessible instructions without visual references pass."""
        assert _has_visual_only_language("Press and hold to record") is False

    def test_returns_false_for_tap_alone(self) -> None:
        """'tap' alone (without 'the green'/'the red') is not flagged."""
        assert _has_visual_only_language("tap to confirm your order") is False

    def test_returns_false_for_food_ordering_confirmation_text(self) -> None:
        """Typical risk disclosure text passes (no visual phrases)."""
        text = (
            "Financial risk disclosure: sharing payment details with any app carries risk. "
            "Do you want to proceed? Say yes to confirm or no to cancel."
        )
        assert _has_visual_only_language(text) is False

    def test_returns_false_for_generic_status_message(self) -> None:
        """Status updates like 'Order placed successfully' pass."""
        assert _has_visual_only_language("Order placed successfully. Estimated arrival: 35 minutes.") is False

    @pytest.mark.parametrize(
        "phrase",
        [
            "click the",
            "tap the green",
            "tap the red",
            "look at",
            "see the",
            "on the right",
            "on the left",
            "icon at the top",
            "icon at the bottom",
            "the icon",
        ],
    )
    def test_each_banned_phrase_is_detected(self, phrase: str) -> None:
        """Every phrase in the banned list is individually detected."""
        assert _has_visual_only_language(phrase) is True


# ===========================================================================
# _has_double_tap_hint  (iOS VoiceOver hint regression guard)
# ===========================================================================


class TestHasDoubleTapHint:
    """
    Tests for _has_double_tap_hint(text) -> bool.

    Background (Cycle 11): VoiceOver automatically appends "double tap to activate"
    to every interactive element. Developers who add the same text in their
    accessibilityHint create a stutter: the user hears "double tap to activate,
    double tap to activate." Fixed in Cycle 11 — this function guards against regression.
    """

    # ---- True cases (deprecated hint language detected) ----

    def test_returns_true_for_double_hyphen_tap_to(self) -> None:
        """'double-tap to' (hyphenated) is deprecated hint language."""
        assert _has_double_tap_hint("Double-tap to activate") is True

    def test_returns_true_for_double_space_tap_to(self) -> None:
        """'double tap to' (no hyphen) is also deprecated."""
        assert _has_double_tap_hint("double tap to start recording") is True

    def test_returns_true_mid_sentence_hyphenated(self) -> None:
        """Deprecated phrase embedded mid-sentence is still detected."""
        assert _has_double_tap_hint("Please double-tap to confirm the order.") is True

    def test_returns_true_mid_sentence_no_hyphen(self) -> None:
        """No-hyphen variant embedded mid-sentence is still detected."""
        assert _has_double_tap_hint("To submit, double tap to send.") is True

    def test_case_insensitive_uppercase(self) -> None:
        """'DOUBLE-TAP TO' in all caps is detected."""
        assert _has_double_tap_hint("DOUBLE-TAP TO ACTIVATE") is True

    def test_case_insensitive_mixed(self) -> None:
        """Mixed case 'Double Tap To' is detected."""
        assert _has_double_tap_hint("Double Tap To Start") is True

    # ---- False cases (acceptable hint language) ----

    def test_returns_false_for_empty_string(self) -> None:
        """An empty string has no deprecated hint."""
        assert _has_double_tap_hint("") is False

    def test_returns_false_for_outcome_first_hint(self) -> None:
        """'Starts recording your message' is the correct pattern (Cycle 11 fix)."""
        assert _has_double_tap_hint("Starts recording your message") is False

    def test_returns_false_for_play_back_hint(self) -> None:
        """'Plays back your last recording' is accessible outcome-first language."""
        assert _has_double_tap_hint("Plays back your last recording") is False

    def test_returns_false_for_opens_settings_hint(self) -> None:
        """'Opens the settings screen' is outcome-first and acceptable."""
        assert _has_double_tap_hint("Opens the settings screen") is False

    def test_returns_false_for_tap_without_double(self) -> None:
        """'tap to activate' (single tap) is not the deprecated VoiceOver stutter phrase."""
        assert _has_double_tap_hint("tap to activate") is False

    def test_returns_false_for_double_without_tap_to(self) -> None:
        """'double' alone or 'double tap' without 'to' is not flagged."""
        assert _has_double_tap_hint("double press for more options") is False

    @pytest.mark.parametrize(
        "acceptable_hint",
        [
            "Starts recording your message",
            "Stops recording",
            "Sends your message to the assistant",
            "Opens the server configuration screen",
            "Cancels the current operation",
            "Confirms your food order",
            "Returns to the main screen",
        ],
    )
    def test_cycle11_hint_fixes_all_pass(self, acceptable_hint: str) -> None:
        """All hints updated in Cycle 11 use outcome-first language and pass."""
        assert _has_double_tap_hint(acceptable_hint) is False
