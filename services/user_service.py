"""
User service module for Azure Table Storage operations.

Provides CRUD operations for user entities stored in Azure Table Storage.
User entities consist of a username (used as RowKey), a base64-encoded
password (btoa format), and an isAdmin boolean flag.
"""

import logging
import os
from typing import Dict, Optional

from azure.data.tables import TableServiceClient, TableClient
from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError

from services.config_loader import get_user_storage_config

logger = logging.getLogger(__name__)

_table_client: Optional[TableClient] = None


def _get_table_client() -> TableClient:
    """
    Return a cached Azure Table Storage client.

    The connection string is read from the environment variable specified
    in the configuration file. The table is created if it does not exist.

    Returns:
        An authenticated TableClient instance.

    Raises:
        ValueError: If the connection string environment variable is not set.
    """
    global _table_client

    if _table_client is not None:
        return _table_client

    config = get_user_storage_config()
    table_name = config.get("tableName", "Users")
    conn_str_env = config.get("connectionStringEnvVar", "AZURE_STORAGE_CONNECTION_STRING")

    connection_string = os.environ.get(conn_str_env)
    if not connection_string:
        raise ValueError(
            f"Environment variable '{conn_str_env}' is not set. "
            "Please configure the Azure Storage connection string."
        )

    service_client = TableServiceClient.from_connection_string(connection_string)

    try:
        service_client.create_table(table_name)
        logger.info("Created table '%s'.", table_name)
    except ResourceExistsError:
        logger.info("Table '%s' already exists.", table_name)

    _table_client = service_client.get_table_client(table_name)
    return _table_client


def _get_partition_key() -> str:
    """Return the partition key used for all user entities."""
    config = get_user_storage_config()
    return config.get("partitionKey", "user")


def _entity_to_user(entity: Dict) -> Dict:
    """
    Convert an Azure Table entity to a clean user dictionary.

    Strips Azure-specific metadata fields (odata, Timestamp, etag) and
    returns only the application-relevant user fields.
    """
    return {
        "username": entity["RowKey"],
        "password": entity.get("password", ""),
        "isAdmin": entity.get("isAdmin", False),
    }


def add_user(username: str, password: str, is_admin: bool) -> Dict:
    """
    Add a new user to Azure Table Storage.

    The password is expected to already be base64-encoded (btoa format)
    by the caller/UI and is stored as-is.

    Args:
        username: Unique username for the new user.
        password: Base64-encoded (btoa) password.
        is_admin: Whether the user has admin privileges.

    Returns:
        A dictionary representing the created user.

    Raises:
        ResourceExistsError: If a user with the given username already exists.
    """
    client = _get_table_client()
    partition_key = _get_partition_key()

    entity = {
        "PartitionKey": partition_key,
        "RowKey": username,
        "password": password,
        "isAdmin": is_admin,
    }

    try:
        client.create_entity(entity)
        logger.info("User '%s' created successfully.", username)
        return _entity_to_user(entity)
    except ResourceExistsError:
        logger.warning("User '%s' already exists.", username)
        raise


def delete_user(username: str) -> None:
    """
    Delete a user from Azure Table Storage.

    Args:
        username: The username of the user to delete.

    Raises:
        ResourceNotFoundError: If the user does not exist.
    """
    client = _get_table_client()
    partition_key = _get_partition_key()

    try:
        client.delete_entity(partition_key=partition_key, row_key=username)
        logger.info("User '%s' deleted successfully.", username)
    except ResourceNotFoundError:
        logger.warning("User '%s' not found for deletion.", username)
        raise


def update_user(username: str, password: Optional[str] = None, is_admin: Optional[bool] = None) -> Dict:
    """
    Update an existing user's password and/or admin flag.

    The password is expected to already be base64-encoded (btoa format)
    by the caller/UI and is stored as-is.

    Args:
        username: The username of the user to update.
        password: New base64-encoded (btoa) password, or None to leave unchanged.
        is_admin: New admin flag value, or None to leave unchanged.

    Returns:
        A dictionary representing the updated user.

    Raises:
        ResourceNotFoundError: If the user does not exist.
    """
    client = _get_table_client()
    partition_key = _get_partition_key()

    try:
        existing = client.get_entity(partition_key=partition_key, row_key=username)
    except ResourceNotFoundError:
        logger.warning("User '%s' not found for update.", username)
        raise

    if password is not None:
        existing["password"] = password
    if is_admin is not None:
        existing["isAdmin"] = is_admin

    client.update_entity(existing, mode="replace")
    logger.info("User '%s' updated successfully.", username)
    return _entity_to_user(existing)


def validate_user(username: str, password: str) -> Optional[Dict]:
    """
    Validate a user's credentials.

    Compares the provided base64-encoded password against the stored
    password for the given username.

    Args:
        username: The username to validate.
        password: The base64-encoded (btoa) password to check.

    Returns:
        The full user object if credentials are valid, otherwise None.
    """
    client = _get_table_client()
    partition_key = _get_partition_key()

    try:
        entity = client.get_entity(partition_key=partition_key, row_key=username)
    except ResourceNotFoundError:
        logger.warning("Validation failed: user '%s' not found.", username)
        return None

    if entity.get("password") == password:
        logger.info("User '%s' validated successfully.", username)
        return _entity_to_user(entity)

    logger.warning("Validation failed: incorrect password for user '%s'.", username)
    return None
