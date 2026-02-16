"""
Configuration loader module.

Loads and provides access to the application configuration from the JSON
configuration file. Supports retrieving all models, a specific model by
its unique modelId, and user storage settings for Azure Table Storage.
"""

import json
import os
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Path to the configuration file (relative to the project root)
CONFIG_FILE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "models_config.json",
)

# In-memory caches
_models_cache: Optional[List[Dict]] = None
_full_config_cache: Optional[Dict] = None


def _load_full_config() -> Dict:
    """
    Load the entire configuration from the JSON file.

    Returns:
        The full configuration dictionary.

    Raises:
        FileNotFoundError: If the configuration file does not exist.
        json.JSONDecodeError: If the configuration file contains invalid JSON.
    """
    global _full_config_cache

    if _full_config_cache is not None:
        return _full_config_cache

    logger.info("Loading configuration from: %s", CONFIG_FILE_PATH)

    with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
        _full_config_cache = json.load(f)

    return _full_config_cache


def _load_models() -> List[Dict]:
    """
    Load the model configuration from the JSON file.

    Returns:
        A list of model configuration dictionaries.
    """
    global _models_cache

    if _models_cache is not None:
        return _models_cache

    config = _load_full_config()
    _models_cache = config.get("models", [])
    logger.info("Loaded %d model configurations.", len(_models_cache))
    return _models_cache


def get_all_models() -> List[Dict]:
    """
    Retrieve the full list of available models.

    Returns:
        A list of dictionaries, each containing model metadata such as
        modelId, modelName, providerName, temperature, supportsVision,
        and description.
    """
    return _load_models()


def get_model_by_id(model_id: str) -> Optional[Dict]:
    """
    Retrieve a specific model configuration by its modelId.

    Args:
        model_id: The unique identifier of the model to retrieve.

    Returns:
        The model configuration dictionary if found, otherwise None.
    """
    models = _load_models()
    for model in models:
        if model.get("modelId") == model_id:
            return model
    return None


def get_user_storage_config() -> Dict:
    """
    Retrieve the user storage configuration for Azure Table Storage.

    Returns:
        A dictionary with keys:
            - tableName (str): The Azure Table Storage table name.
            - partitionKey (str): The partition key used for user entities.
            - connectionStringEnvVar (str): The environment variable name
              that holds the Azure Storage connection string.
    """
    config = _load_full_config()
    return config.get("userStorage", {})


def reload_config() -> List[Dict]:
    """
    Force a reload of the configuration file.

    Clears all in-memory caches and reloads from disk. Useful if
    the configuration file has been updated at runtime.

    Returns:
        The freshly loaded list of model configurations.
    """
    global _models_cache, _full_config_cache
    _models_cache = None
    _full_config_cache = None
    logger.info("Configuration cache cleared. Reloading...")
    return _load_models()
