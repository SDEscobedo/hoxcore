"""
Registry Operation for HoxCore Registry Path Management.

This module provides the shared registry management operation implementation
that ensures behavioral consistency between the CLI commands and MCP tools.
It handles:

- Registry path validation
- Getting the current registry path from configuration
- Setting the registry path in configuration
- Listing known registries
- Auto-discovery of registries in the current directory tree
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from hxc.core.config import Config
from hxc.utils.helpers import get_project_root


class RegistryOperationError(Exception):
    """Base exception for registry operation errors"""

    pass


class InvalidRegistryPathError(RegistryOperationError):
    """Raised when a path is not a valid HoxCore registry"""

    def __init__(self, path: str, missing_components: List[str]):
        self.path = path
        self.missing_components = missing_components
        super().__init__(
            f"Invalid registry path '{path}'. Missing: {', '.join(missing_components)}"
        )


class RegistryNotFoundError(RegistryOperationError):
    """Raised when no registry path is configured or discoverable"""

    pass


class RegistryOperation:
    """
    Shared registry management operation for CLI and MCP interfaces.

    This class provides the core registry path management logic including:
    - Path validation (checking for required structure)
    - Getting the current registry path from configuration
    - Setting the registry path in configuration
    - Listing known registries
    - Auto-discovery of registries
    """

    # Configuration key for storing registry path
    CONFIG_KEY = "registry_path"

    # Required folders for a valid registry
    REQUIRED_FOLDERS = ["programs", "projects", "missions", "actions"]

    # Required files for a valid registry
    REQUIRED_FILES = ["config.yml"]

    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the registry operation.

        Args:
            config: Optional Config instance (creates new one if not provided)
        """
        self.config = config or Config()

    @staticmethod
    def validate_registry_path(path: Union[str, Path]) -> Dict[str, Any]:
        """
        Validate if a path is a valid HoxCore registry.

        A valid registry must:
        - Exist and be a directory
        - Contain config.yml
        - Contain all entity folders: programs, projects, missions, actions

        Args:
            path: Path to validate

        Returns:
            Dictionary containing:
            - valid: bool - Whether the path is a valid registry
            - path: str - The validated path (resolved to absolute)
            - missing: list - Missing required components (empty if valid)
        """
        path = Path(path)

        # Check if path exists and is a directory
        if not path.exists():
            return {
                "valid": False,
                "path": str(path),
                "missing": ["path does not exist"],
            }

        if not path.is_dir():
            return {
                "valid": False,
                "path": str(path),
                "missing": ["path is not a directory"],
            }

        # Resolve to absolute path
        resolved_path = path.resolve()

        # Check for required components
        missing: List[str] = []

        # Check required files
        for required_file in RegistryOperation.REQUIRED_FILES:
            file_path = resolved_path / required_file
            if not file_path.exists():
                missing.append(required_file)

        # Check required folders
        for required_folder in RegistryOperation.REQUIRED_FOLDERS:
            folder_path = resolved_path / required_folder
            if not folder_path.exists():
                missing.append(f"{required_folder}/")

        return {
            "valid": len(missing) == 0,
            "path": str(resolved_path),
            "missing": missing,
        }

    def get_registry_path(self, include_discovery: bool = True) -> Dict[str, Any]:
        """
        Get the current registry path from configuration.

        Args:
            include_discovery: Whether to attempt auto-discovery if not configured

        Returns:
            Dictionary containing:
            - success: bool
            - path: str or None - The registry path
            - is_valid: bool - Whether the path passes validation
            - source: str - Where the path came from ('config', 'discovered', 'none')
            - discovered_path: str or None - Auto-discovered path if different from configured
        """
        # Try to get from config
        configured_path = self.config.get(self.CONFIG_KEY)

        if configured_path:
            # Validate the configured path
            validation = self.validate_registry_path(configured_path)

            if validation["valid"]:
                return {
                    "success": True,
                    "path": configured_path,
                    "is_valid": True,
                    "source": "config",
                    "discovered_path": None,
                }
            else:
                # Configured path is invalid
                discovered = None
                if include_discovery:
                    discovered = get_project_root()

                return {
                    "success": False,
                    "path": configured_path,
                    "is_valid": False,
                    "source": "config",
                    "discovered_path": discovered,
                    "validation_errors": validation["missing"],
                }

        # No configured path - try discovery
        if include_discovery:
            discovered_path = get_project_root()

            if discovered_path:
                validation = self.validate_registry_path(discovered_path)

                return {
                    "success": True,
                    "path": discovered_path,
                    "is_valid": validation["valid"],
                    "source": "discovered",
                    "discovered_path": discovered_path,
                }

        # No path found
        return {
            "success": False,
            "path": None,
            "is_valid": False,
            "source": "none",
            "discovered_path": None,
        }

    def set_registry_path(self, path: str, validate: bool = True) -> Dict[str, Any]:
        """
        Set the registry path in configuration.

        Args:
            path: Path to set as the registry
            validate: Whether to validate the path before setting

        Returns:
            Dictionary containing:
            - success: bool
            - path: str - The new path (resolved to absolute)
            - previous_path: str or None - The previous registry path
            - is_valid: bool - Whether the new path is valid (if validated)

        Raises:
            InvalidRegistryPathError: If validate=True and path is invalid
        """
        # Get previous path
        previous_path = self.config.get(self.CONFIG_KEY)

        # Resolve the path
        resolved_path = Path(path).resolve()

        # Validate if requested
        is_valid = True
        if validate:
            validation = self.validate_registry_path(resolved_path)

            if not validation["valid"]:
                raise InvalidRegistryPathError(
                    str(resolved_path), validation["missing"]
                )

            is_valid = validation["valid"]

        # Set the path in config
        self.config.set(self.CONFIG_KEY, str(resolved_path))

        return {
            "success": True,
            "path": str(resolved_path),
            "previous_path": previous_path,
            "is_valid": is_valid,
        }

    def list_registries(self) -> Dict[str, Any]:
        """
        List all known registries.

        Currently supports only a single configured registry.
        Future versions may support multiple named registries.

        Returns:
            Dictionary containing:
            - success: bool
            - registries: list of registry objects with path, is_current, is_valid
            - count: int - Number of registries
        """
        registries: List[Dict[str, Any]] = []

        # Get configured registry
        configured_path = self.config.get(self.CONFIG_KEY)

        if configured_path:
            validation = self.validate_registry_path(configured_path)

            registries.append(
                {
                    "path": configured_path,
                    "is_current": True,
                    "is_valid": validation["valid"],
                    "name": "default",
                    "source": "config",
                }
            )

        # Also check for discovered registry if different from configured
        discovered_path = get_project_root()

        if discovered_path and discovered_path != configured_path:
            validation = self.validate_registry_path(discovered_path)

            registries.append(
                {
                    "path": discovered_path,
                    "is_current": configured_path is None,
                    "is_valid": validation["valid"],
                    "name": "discovered",
                    "source": "discovered",
                }
            )

        return {
            "success": True,
            "registries": registries,
            "count": len(registries),
        }

    def discover_registry(self) -> Dict[str, Any]:
        """
        Attempt to discover a registry in the current directory tree.

        Walks up from the current directory looking for a valid registry.

        Returns:
            Dictionary containing:
            - success: bool
            - path: str or None - Discovered registry path
            - is_valid: bool - Whether the discovered path is valid
        """
        discovered_path = get_project_root()

        if discovered_path:
            validation = self.validate_registry_path(discovered_path)

            return {
                "success": True,
                "path": discovered_path,
                "is_valid": validation["valid"],
            }

        return {
            "success": False,
            "path": None,
            "is_valid": False,
        }

    def clear_registry_path(self) -> Dict[str, Any]:
        """
        Clear the configured registry path.

        Returns:
            Dictionary containing:
            - success: bool
            - previous_path: str or None - The cleared path
        """
        previous_path = self.config.get(self.CONFIG_KEY)

        # Load full config, remove key, and save
        config_data = self.config.load()
        if self.CONFIG_KEY in config_data:
            del config_data[self.CONFIG_KEY]
            self.config.save(config_data)

        return {
            "success": True,
            "previous_path": previous_path,
        }
