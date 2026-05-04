"""Configuration loader for TSEDA.

This module handles loading and accessing configuration values from the
tseda_config.yaml file. The configuration is loaded once at startup and
provides a singleton interface for accessing configuration throughout the
application.
"""

import os
from pathlib import Path
from typing import Any, Optional
import yaml


class ConfigurationManager:
    """Singleton configuration manager for TSEDA."""

    _instance: Optional["ConfigurationManager"] = None
    _config: dict[str, Any] = {}
    _loaded: bool = False

    def __new__(cls) -> "ConfigurationManager":
        """Ensure only one instance exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def load_config(cls) -> dict[str, Any]:
        """Load configuration from YAML file.

        Returns:
            Configuration dictionary.

        Raises:
            FileNotFoundError: If config file is not found.
            yaml.YAMLError: If YAML parsing fails.
        """
        if cls._loaded and cls._config:
            return cls._config

        # Locate config file relative to this module
        config_dir = Path(__file__).parent
        config_file = config_dir / "tseda_config.yaml"

        if not config_file.exists():
            raise FileNotFoundError(
                f"Configuration file not found at {config_file}. "
                "Please ensure tseda_config.yaml exists in {config_dir}."
            )

        try:
            with open(config_file, "r", encoding="utf-8") as f:
                cls._config = yaml.safe_load(f) or {}
            cls._loaded = True
            return cls._config
        except yaml.YAMLError as e:
            raise yaml.YAMLError(
                f"Failed to parse configuration file {config_file}: {e}"
            )

    @classmethod
    def get(cls, key_path: str, default: Any = None) -> Any:
        """Get configuration value by dot-separated path.

        Args:
            key_path: Dot-separated path to config value (e.g., "file_upload.max_file_lines").
            default: Default value if key is not found.

        Returns:
            Configuration value or default if not found.

        Example:
            >>> max_lines = ConfigurationManager.get("file_upload.max_file_lines")
            >>> dw_low = ConfigurationManager.get("noise_validation.dw_low", 1.5)
        """
        if not cls._config:
            cls.load_config()

        keys = key_path.split(".")
        value = cls._config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    @classmethod
    def get_section(cls, section: str) -> dict[str, Any]:
        """Get entire configuration section.

        Args:
            section: Top-level section name (e.g., "file_upload", "grouping_heuristic").

        Returns:
            Dictionary containing the section, or empty dict if not found.

        Example:
            >>> window_config = ConfigurationManager.get_section("window_selection")
        """
        if not cls._config:
            cls.load_config()

        return cls._config.get(section, {})

    @classmethod
    def reload(cls) -> dict[str, Any]:
        """Force reload of configuration from file.

        Returns:
            Reloaded configuration dictionary.
        """
        cls._config = {}
        cls._loaded = False
        return cls.load_config()

    @classmethod
    def reset(cls) -> None:
        """Reset configuration (for testing)."""
        cls._config = {}
        cls._loaded = False


def get_config(key_path: str, default: Any = None) -> Any:
    """Convenience function to get configuration value.

    Args:
        key_path: Dot-separated path to config value.
        default: Default value if key is not found.

    Returns:
        Configuration value or default.

    Example:
        >>> max_lines = get_config("file_upload.max_file_lines")
    """
    return ConfigurationManager.get(key_path, default)


def get_config_section(section: str) -> dict[str, Any]:
    """Convenience function to get entire configuration section.

    Args:
        section: Top-level section name.

    Returns:
        Dictionary containing the section.

    Example:
        >>> window_cfg = get_config_section("window_selection")
    """
    return ConfigurationManager.get_section(section)
