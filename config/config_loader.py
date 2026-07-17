"""
Config Loader
Loads YAML configuration files for Stockei.
"""

from typing import Any, Dict
import logging
import os

import yaml

logger = logging.getLogger(__name__)

CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))


def load_config(path: str) -> Dict[str, Any]:
    """
    Load a YAML configuration file.

    Args:
        path: Path to the YAML file.

    Returns:
        Parsed configuration dict (empty dict for empty files).
    """
    with open(path, "r", encoding="utf-8") as fh:
        config: Dict[str, Any] = yaml.safe_load(fh) or {}
    logger.info("Loaded config from '%s'", path)
    return config


def load_stockei_config() -> Dict[str, Any]:
    """
    Load the main Stockei product configuration.

    Returns:
        Parsed stockei_config.yaml dict.
    """
    return load_config(os.path.join(CONFIG_DIR, "stockei_config.yaml"))


def load_agents_config() -> Dict[str, Any]:
    """
    Load the agents configuration.

    Returns:
        Parsed agents_config.yaml dict.
    """
    return load_config(os.path.join(CONFIG_DIR, "agents_config.yaml"))
