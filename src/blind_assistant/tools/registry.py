"""
Tool Registry

Manages available and installed tools. Supports self-expanding capability:
the assistant discovers what's available, installs what's needed (with user consent),
and tracks what's been installed.

Per SECURITY_MODEL.md §5: only packages from the approved registry can be installed.
"""

import asyncio
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Path to the approved tool registry
REGISTRY_PATH = Path(__file__).parent.parent.parent.parent / "tools" / "registry.yaml"

# Installation audit log
AUDIT_LOG_PATH = Path.home() / ".blind-assistant" / "install_log.json"


class ToolRegistry:
    """
    Registry of available and installed tools.

    Available tools: defined in tools/registry.yaml (curated, audited)
    Installed tools: subset of available that have been set up on this device
    """

    def __init__(self) -> None:
        self._available: dict[str, dict] = {}  # name → tool metadata
        self._installed: dict[str, object] = {}  # name → tool instance
        self._loaded = False

    async def load(self) -> None:
        """Load the tool registry from disk."""
        if REGISTRY_PATH.exists():
            import yaml
            with open(REGISTRY_PATH) as f:
                data = yaml.safe_load(f)
                self._available = {
                    tool["name"]: tool
                    for tool in (data.get("tools") or [])
                }
            logger.info(f"Loaded {len(self._available)} available tools from registry")
        else:
            logger.warning(f"Tool registry not found at {REGISTRY_PATH}")
            self._available = {}

        self._loaded = True

    def is_installed(self, tool_name: str) -> bool:
        """Check if a tool is installed and ready to use."""
        return tool_name in self._installed

    def get_available_tool(self, tool_name: str) -> dict | None:
        """Get metadata for an available (but possibly not installed) tool."""
        return self._available.get(tool_name)

    def get_installed_tool(self, tool_name: str) -> object | None:
        """Get an installed tool instance."""
        return self._installed.get(tool_name)

    def list_installed_tools(self) -> list[dict]:
        """
        Return list of installed tool names and descriptions.
        Used for the "what tools have you installed?" transparency feature.
        """
        return [
            {
                "name": name,
                "description": self._available.get(name, {}).get("description", ""),
            }
            for name in self._installed
        ]

    async def install_tool(self, tool_name: str, tool_info: dict) -> bool:
        """
        Install a tool from the approved registry.

        Per SECURITY_MODEL.md §5:
        - Only approved registry tools can be installed
        - Installation is logged to audit log
        - User has already confirmed before this is called

        Returns: True if successful
        """
        if tool_name not in self._available:
            logger.error(
                f"Refused to install unapproved tool: {tool_name}. "
                "Only tools from the approved registry can be installed."
            )
            return False

        try:
            logger.info(f"Installing tool: {tool_name}")

            # Run pip install in subprocess (isolated)
            package = tool_info.get("package", tool_name)
            version = tool_info.get("version", "")
            install_target = f"{package}=={version}" if version else package

            proc = await asyncio.create_subprocess_exec(
                "pip", "install", "--quiet", install_target,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                logger.error(f"pip install failed for {tool_name}: {stderr.decode()}")
                return False

            # Log the installation
            await self._log_installation(tool_name, install_target, tool_info)

            # Initialize the tool
            tool_class_path = tool_info.get("class")
            if tool_class_path:
                tool_instance = await self._instantiate_tool(tool_class_path)
                if tool_instance:
                    self._installed[tool_name] = tool_instance

            logger.info(f"Tool installed: {tool_name}")
            return True

        except Exception as e:
            logger.error(f"Tool installation failed for {tool_name}: {e}", exc_info=True)
            return False

    async def uninstall_tool(self, tool_name: str) -> bool:
        """
        Uninstall a tool and remove its credentials.

        Used for: "uninstall [tool]" voice command.
        """
        if tool_name not in self._installed:
            return False

        # Remove from installed registry
        del self._installed[tool_name]

        # Remove stored credentials for this tool
        cred_key = f"tool_{tool_name}_credentials"
        from blind_assistant.security.credentials import delete_credential
        delete_credential(cred_key)

        logger.info(f"Tool uninstalled: {tool_name}")
        return True

    async def _log_installation(
        self, tool_name: str, package: str, tool_info: dict
    ) -> None:
        """Append installation to audit log."""
        import datetime

        AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

        # Load existing log
        log_entries = []
        if AUDIT_LOG_PATH.exists():
            with open(AUDIT_LOG_PATH) as f:
                try:
                    log_entries = json.load(f)
                except json.JSONDecodeError:
                    log_entries = []

        # Append new entry
        log_entries.append({
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "tool_name": tool_name,
            "package": package,
            "reason": tool_info.get("task_description", ""),
            "user_confirmed": True,  # always true — user confirmed before this is called
        })

        with open(AUDIT_LOG_PATH, "w") as f:
            json.dump(log_entries, f, indent=2)

    async def _instantiate_tool(self, class_path: str) -> object | None:
        """Dynamically instantiate a tool class by its module path."""
        try:
            module_path, class_name = class_path.rsplit(".", 1)
            import importlib
            module = importlib.import_module(module_path)
            cls = getattr(module, class_name)
            return cls()
        except Exception as e:
            logger.error(f"Failed to instantiate tool class {class_path}: {e}")
            return None
