"""
Tests for tools/registry.py — ToolRegistry

Verifies the self-expanding capability:
  - Loading tools from registry.yaml
  - Checking installed status
  - Installing tools (with user consent, from approved list only)
  - Refusing to install unapproved tools
  - Uninstalling tools and removing credentials
  - Audit log written on install
  - Dynamic class instantiation

All subprocess.create_subprocess_exec calls are mocked; no real pip runs.
All file I/O uses temp_dir fixture; no real ~/.blind-assistant writes.
"""

from __future__ import annotations

import json
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, call
import pytest

from blind_assistant.tools.registry import ToolRegistry, REGISTRY_PATH, AUDIT_LOG_PATH


# ─────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────


@pytest.fixture
def minimal_registry_yaml(tmp_path: Path) -> Path:
    """Write a minimal registry.yaml into a temp location and return its path."""
    content = """
tools:
  - name: browser
    package: playwright
    version: "1.40.0"
    description: "a web browser I can control"
    task_description: "navigate websites to complete tasks"
    class: "blind_assistant.tools.browser.BrowserTool"
  - name: stripe_payments
    package: stripe
    version: "7.3.0"
    description: "a payment processor"
    task_description: "process payments securely"
"""
    registry_file = tmp_path / "registry.yaml"
    registry_file.write_text(content)
    return registry_file


@pytest.fixture
def empty_registry_yaml(tmp_path: Path) -> Path:
    """Write a registry.yaml with no tools (empty list)."""
    content = "tools: []\n"
    registry_file = tmp_path / "registry.yaml"
    registry_file.write_text(content)
    return registry_file


@pytest.fixture
def registry_with_no_class(tmp_path: Path) -> Path:
    """Registry with a tool that has no class field (package-only install)."""
    content = """
tools:
  - name: http_client
    package: aiohttp
    version: "3.9.3"
    description: "an async HTTP client"
    task_description: "connect to web services"
"""
    registry_file = tmp_path / "registry.yaml"
    registry_file.write_text(content)
    return registry_file


@pytest.fixture
def mock_pip_success() -> MagicMock:
    """Mock asyncio.create_subprocess_exec to simulate a successful pip install."""
    proc = MagicMock()
    proc.returncode = 0
    proc.communicate = AsyncMock(return_value=(b"", b""))
    return proc


@pytest.fixture
def mock_pip_failure() -> MagicMock:
    """Mock asyncio.create_subprocess_exec to simulate a failed pip install."""
    proc = MagicMock()
    proc.returncode = 1
    proc.communicate = AsyncMock(return_value=(b"", b"error: package not found"))
    return proc


# ─────────────────────────────────────────────────────────────
# Load tests
# ─────────────────────────────────────────────────────────────


async def test_load_reads_tools_from_yaml(minimal_registry_yaml: Path) -> None:
    """load() populates _available from a valid registry.yaml."""
    registry = ToolRegistry()
    with patch("blind_assistant.tools.registry.REGISTRY_PATH", minimal_registry_yaml):
        await registry.load()

    assert "browser" in registry._available
    assert "stripe_payments" in registry._available
    assert registry._available["browser"]["package"] == "playwright"


async def test_load_empty_registry_has_no_available_tools(empty_registry_yaml: Path) -> None:
    """load() with an empty tools list results in an empty _available dict."""
    registry = ToolRegistry()
    with patch("blind_assistant.tools.registry.REGISTRY_PATH", empty_registry_yaml):
        await registry.load()

    assert registry._available == {}
    assert registry._loaded is True


async def test_load_missing_registry_file_logs_warning(tmp_path: Path) -> None:
    """load() with no registry.yaml sets _available to {} and _loaded to True."""
    nonexistent = tmp_path / "does_not_exist.yaml"
    registry = ToolRegistry()
    with patch("blind_assistant.tools.registry.REGISTRY_PATH", nonexistent):
        await registry.load()

    assert registry._available == {}
    assert registry._loaded is True


async def test_load_sets_loaded_flag(minimal_registry_yaml: Path) -> None:
    """_loaded is False before load() and True after."""
    registry = ToolRegistry()
    assert registry._loaded is False
    with patch("blind_assistant.tools.registry.REGISTRY_PATH", minimal_registry_yaml):
        await registry.load()
    assert registry._loaded is True


async def test_load_handles_null_tools_key(tmp_path: Path) -> None:
    """load() with tools: null does not raise — results in empty _available."""
    yaml_file = tmp_path / "registry.yaml"
    yaml_file.write_text("tools:\n")
    registry = ToolRegistry()
    with patch("blind_assistant.tools.registry.REGISTRY_PATH", yaml_file):
        await registry.load()

    assert registry._available == {}


# ─────────────────────────────────────────────────────────────
# is_installed / get_available_tool / get_installed_tool
# ─────────────────────────────────────────────────────────────


def test_is_installed_returns_false_for_uninstalled_tool() -> None:
    """is_installed returns False when the tool is not in _installed."""
    registry = ToolRegistry()
    assert registry.is_installed("browser") is False


def test_is_installed_returns_true_after_manual_insertion() -> None:
    """is_installed returns True when the tool has been added to _installed."""
    registry = ToolRegistry()
    registry._installed["browser"] = MagicMock()
    assert registry.is_installed("browser") is True


def test_get_available_tool_returns_none_for_unknown_tool() -> None:
    """get_available_tool returns None for a tool not in the registry."""
    registry = ToolRegistry()
    assert registry.get_available_tool("nonexistent") is None


def test_get_available_tool_returns_metadata_after_load() -> None:
    """get_available_tool returns the full tool metadata dict."""
    registry = ToolRegistry()
    registry._available = {
        "browser": {"name": "browser", "package": "playwright", "version": "1.40.0"}
    }
    result = registry.get_available_tool("browser")
    assert result is not None
    assert result["package"] == "playwright"


def test_get_installed_tool_returns_none_if_not_installed() -> None:
    """get_installed_tool returns None when the tool is not installed."""
    registry = ToolRegistry()
    assert registry.get_installed_tool("browser") is None


def test_get_installed_tool_returns_instance_when_installed() -> None:
    """get_installed_tool returns the tool instance after installation."""
    registry = ToolRegistry()
    fake_instance = MagicMock()
    registry._installed["browser"] = fake_instance
    assert registry.get_installed_tool("browser") is fake_instance


def test_list_installed_tools_returns_empty_when_none_installed() -> None:
    """list_installed_tools returns [] when no tools are installed."""
    registry = ToolRegistry()
    assert registry.list_installed_tools() == []


def test_list_installed_tools_returns_name_and_description() -> None:
    """list_installed_tools returns dicts with name and description."""
    registry = ToolRegistry()
    registry._available = {"browser": {"description": "a web browser"}}
    registry._installed = {"browser": MagicMock()}
    result = registry.list_installed_tools()
    assert len(result) == 1
    assert result[0]["name"] == "browser"
    assert result[0]["description"] == "a web browser"


def test_list_installed_tools_uses_empty_description_for_unknown_tool() -> None:
    """list_installed_tools uses empty string if tool not in _available."""
    registry = ToolRegistry()
    registry._available = {}
    registry._installed = {"mystery_tool": MagicMock()}
    result = registry.list_installed_tools()
    assert result[0]["description"] == ""


# ─────────────────────────────────────────────────────────────
# install_tool — happy path
# ─────────────────────────────────────────────────────────────


async def test_install_tool_refuses_unapproved_tool() -> None:
    """install_tool returns False and logs error for a tool not in _available."""
    registry = ToolRegistry()
    registry._available = {}  # empty — no tools approved

    result = await registry.install_tool("evil_package", {"package": "evil"})

    assert result is False


async def test_install_tool_runs_pip_with_correct_args(
    minimal_registry_yaml: Path, mock_pip_success: MagicMock, tmp_path: Path
) -> None:
    """install_tool calls pip install playwright==1.40.0 for the browser tool."""
    registry = ToolRegistry()
    registry._available = {
        "browser": {"package": "playwright", "version": "1.40.0"}
    }

    audit_log = tmp_path / "install_log.json"

    with patch("asyncio.create_subprocess_exec", return_value=mock_pip_success) as mock_exec, \
         patch("blind_assistant.tools.registry.AUDIT_LOG_PATH", audit_log):
        result = await registry.install_tool(
            "browser", registry._available["browser"]
        )

    assert result is True
    mock_exec.assert_called_once_with(
        "pip", "install", "--quiet", "playwright==1.40.0",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )


async def test_install_tool_without_version_uses_bare_package_name(
    mock_pip_success: MagicMock, tmp_path: Path
) -> None:
    """install_tool uses just the package name when version is not specified."""
    registry = ToolRegistry()
    registry._available = {
        "http_client": {"package": "aiohttp"}
    }

    audit_log = tmp_path / "install_log.json"

    with patch("asyncio.create_subprocess_exec", return_value=mock_pip_success) as mock_exec, \
         patch("blind_assistant.tools.registry.AUDIT_LOG_PATH", audit_log):
        await registry.install_tool("http_client", registry._available["http_client"])

    call_args = mock_exec.call_args[0]
    assert call_args[3] == "aiohttp"  # no ==version suffix


async def test_install_tool_returns_false_on_pip_failure(
    mock_pip_failure: MagicMock, tmp_path: Path
) -> None:
    """install_tool returns False when pip exits non-zero."""
    registry = ToolRegistry()
    registry._available = {
        "browser": {"package": "playwright", "version": "1.40.0"}
    }

    audit_log = tmp_path / "install_log.json"

    with patch("asyncio.create_subprocess_exec", return_value=mock_pip_failure), \
         patch("blind_assistant.tools.registry.AUDIT_LOG_PATH", audit_log):
        result = await registry.install_tool("browser", registry._available["browser"])

    assert result is False


async def test_install_tool_writes_audit_log(
    mock_pip_success: MagicMock, tmp_path: Path
) -> None:
    """install_tool writes an entry to the audit log with correct fields."""
    registry = ToolRegistry()
    tool_info = {
        "package": "playwright",
        "version": "1.40.0",
        "task_description": "navigate websites",
    }
    registry._available = {"browser": tool_info}
    audit_log = tmp_path / "install_log.json"

    with patch("asyncio.create_subprocess_exec", return_value=mock_pip_success), \
         patch("blind_assistant.tools.registry.AUDIT_LOG_PATH", audit_log):
        await registry.install_tool("browser", tool_info)

    assert audit_log.exists()
    entries = json.loads(audit_log.read_text())
    assert len(entries) == 1
    assert entries[0]["tool_name"] == "browser"
    assert entries[0]["package"] == "playwright==1.40.0"
    assert entries[0]["user_confirmed"] is True
    assert entries[0]["reason"] == "navigate websites"
    assert "timestamp" in entries[0]


async def test_install_tool_appends_to_existing_audit_log(
    mock_pip_success: MagicMock, tmp_path: Path
) -> None:
    """install_tool appends to an existing audit log (doesn't overwrite)."""
    audit_log = tmp_path / "install_log.json"
    # Pre-populate with one existing entry
    existing = [{"tool_name": "old_tool", "user_confirmed": True, "timestamp": "2026-01-01T00:00:00Z", "package": "old", "reason": ""}]
    audit_log.write_text(json.dumps(existing))

    registry = ToolRegistry()
    registry._available = {"browser": {"package": "playwright", "version": "1.40.0"}}

    with patch("asyncio.create_subprocess_exec", return_value=mock_pip_success), \
         patch("blind_assistant.tools.registry.AUDIT_LOG_PATH", audit_log):
        await registry.install_tool("browser", registry._available["browser"])

    entries = json.loads(audit_log.read_text())
    assert len(entries) == 2
    assert entries[0]["tool_name"] == "old_tool"
    assert entries[1]["tool_name"] == "browser"


async def test_install_tool_creates_audit_log_parent_dir(
    mock_pip_success: MagicMock, tmp_path: Path
) -> None:
    """install_tool creates parent directory for audit log if it doesn't exist."""
    audit_log = tmp_path / "subdir" / "deep" / "install_log.json"
    registry = ToolRegistry()
    registry._available = {"browser": {"package": "playwright", "version": "1.40.0"}}

    with patch("asyncio.create_subprocess_exec", return_value=mock_pip_success), \
         patch("blind_assistant.tools.registry.AUDIT_LOG_PATH", audit_log):
        await registry.install_tool("browser", registry._available["browser"])

    assert audit_log.exists()


# ─────────────────────────────────────────────────────────────
# install_tool — no class field (package-only)
# ─────────────────────────────────────────────────────────────


async def test_install_tool_succeeds_without_class_field(
    mock_pip_success: MagicMock, tmp_path: Path
) -> None:
    """install_tool returns True even when no class field is present in tool_info."""
    registry = ToolRegistry()
    registry._available = {"http_client": {"package": "aiohttp", "version": "3.9.3"}}
    audit_log = tmp_path / "install_log.json"

    with patch("asyncio.create_subprocess_exec", return_value=mock_pip_success), \
         patch("blind_assistant.tools.registry.AUDIT_LOG_PATH", audit_log):
        result = await registry.install_tool(
            "http_client", registry._available["http_client"]
        )

    assert result is True
    # No tool instance added since no class to instantiate
    assert "http_client" not in registry._installed


# ─────────────────────────────────────────────────────────────
# install_tool — exception handling
# ─────────────────────────────────────────────────────────────


async def test_install_tool_returns_false_on_subprocess_exception(
    tmp_path: Path,
) -> None:
    """install_tool returns False when create_subprocess_exec raises an exception."""
    registry = ToolRegistry()
    registry._available = {"browser": {"package": "playwright", "version": "1.40.0"}}
    audit_log = tmp_path / "install_log.json"

    with patch("asyncio.create_subprocess_exec", side_effect=OSError("no pip")), \
         patch("blind_assistant.tools.registry.AUDIT_LOG_PATH", audit_log):
        result = await registry.install_tool("browser", registry._available["browser"])

    assert result is False


async def test_install_tool_handles_corrupted_audit_log_gracefully(
    mock_pip_success: MagicMock, tmp_path: Path
) -> None:
    """install_tool starts fresh if existing audit log contains invalid JSON."""
    audit_log = tmp_path / "install_log.json"
    audit_log.write_text("NOT VALID JSON{{{")

    registry = ToolRegistry()
    registry._available = {"browser": {"package": "playwright", "version": "1.40.0"}}

    with patch("asyncio.create_subprocess_exec", return_value=mock_pip_success), \
         patch("blind_assistant.tools.registry.AUDIT_LOG_PATH", audit_log):
        result = await registry.install_tool("browser", registry._available["browser"])

    # Should succeed — corrupted log was reset
    assert result is True
    entries = json.loads(audit_log.read_text())
    assert len(entries) == 1


# ─────────────────────────────────────────────────────────────
# uninstall_tool
# ─────────────────────────────────────────────────────────────


async def test_uninstall_tool_returns_false_if_not_installed() -> None:
    """uninstall_tool returns False when tool is not in _installed."""
    registry = ToolRegistry()
    result = await registry.uninstall_tool("browser")
    assert result is False


async def test_uninstall_tool_removes_from_installed() -> None:
    """uninstall_tool removes the tool from _installed dict."""
    registry = ToolRegistry()
    registry._installed["browser"] = MagicMock()

    with patch("blind_assistant.security.credentials.delete_credential"):
        result = await registry.uninstall_tool("browser")

    assert result is True
    assert "browser" not in registry._installed


async def test_uninstall_tool_deletes_stored_credentials() -> None:
    """uninstall_tool calls delete_credential with the tool's credential key."""
    registry = ToolRegistry()
    registry._installed["stripe_payments"] = MagicMock()

    with patch("blind_assistant.security.credentials.delete_credential") as mock_delete:
        await registry.uninstall_tool("stripe_payments")

    mock_delete.assert_called_once_with("tool_stripe_payments_credentials")


async def test_uninstall_tool_handles_missing_credentials_gracefully() -> None:
    """uninstall_tool succeeds even if delete_credential raises (no stored creds)."""
    registry = ToolRegistry()
    registry._installed["browser"] = MagicMock()

    import keyring.errors
    with patch(
        "blind_assistant.security.credentials.delete_credential",
        side_effect=keyring.errors.PasswordDeleteError("not found"),
    ):
        # Should not raise — tool can be uninstalled even without stored credentials
        result = await registry.uninstall_tool("browser")

    assert result is True
    assert "browser" not in registry._installed


# ─────────────────────────────────────────────────────────────
# _instantiate_tool
# ─────────────────────────────────────────────────────────────


async def test_instantiate_tool_returns_none_for_bad_module_path() -> None:
    """_instantiate_tool returns None if the module path cannot be imported."""
    registry = ToolRegistry()
    result = await registry._instantiate_tool(
        "blind_assistant.tools.nonexistent_module.SomeClass"
    )
    assert result is None


async def test_instantiate_tool_returns_none_for_bad_class_name() -> None:
    """_instantiate_tool returns None if the class doesn't exist in the module."""
    registry = ToolRegistry()
    # The module exists but the class does not
    result = await registry._instantiate_tool(
        "blind_assistant.tools.registry.NonExistentClass"
    )
    assert result is None


async def test_instantiate_tool_returns_instance_when_class_exists() -> None:
    """_instantiate_tool returns an instance of the class when path is valid."""
    registry = ToolRegistry()
    # ToolRegistry itself is a valid class in a valid module
    result = await registry._instantiate_tool(
        "blind_assistant.tools.registry.ToolRegistry"
    )
    assert result is not None
    assert isinstance(result, ToolRegistry)


# ─────────────────────────────────────────────────────────────
# Security: unapproved tools MUST be blocked
# ─────────────────────────────────────────────────────────────


async def test_install_tool_refuses_tool_not_in_available_registry() -> None:
    """
    SECURITY: install_tool must refuse any tool not in _available.

    This is the core supply-chain security guard — no arbitrary pip packages
    can be installed. Per SECURITY_MODEL.md §5.
    """
    registry = ToolRegistry()
    registry._available = {"browser": {"package": "playwright"}}

    # Attempting to install a tool NOT in _available must fail
    result = await registry.install_tool(
        "malicious_package",
        {"package": "malicious_package", "version": "1.0.0"}
    )

    assert result is False


async def test_install_tool_cannot_install_if_available_is_empty() -> None:
    """SECURITY: with an empty registry no tool can ever be installed."""
    registry = ToolRegistry()
    # Don't call load() — _available stays empty

    result = await registry.install_tool("anything", {"package": "anything"})

    assert result is False


async def test_real_registry_yaml_loads_correctly() -> None:
    """
    Smoke test: the real tools/registry.yaml parses without errors.

    This catches syntax errors or structural changes to the registry file
    before they reach production.
    """
    registry = ToolRegistry()
    # Use the actual REGISTRY_PATH (the real file checked into the repo)
    await registry.load()

    # The real registry must have at least the browser and stripe_payments capabilities
    # (defined in tools/registry.yaml). If this fails, someone deleted an approved tool.
    assert len(registry._available) >= 2, (
        f"Real registry has only {len(registry._available)} tools. "
        "Did someone delete an approved tool from tools/registry.yaml?"
    )


async def test_real_registry_yaml_all_tools_have_required_fields() -> None:
    """Every tool in the real registry.yaml has name, package, and description."""
    registry = ToolRegistry()
    await registry.load()

    for name, tool in registry._available.items():
        assert "name" in tool, f"Tool {name!r} missing 'name' field"
        assert "package" in tool, f"Tool {name!r} missing 'package' field"
        assert "description" in tool, f"Tool {name!r} missing 'description' field"
