"""
Azure Functions entry point for the Multi-Provider LLM API.

This module defines all HTTP-triggered Azure Functions directly using
the native azure.functions FunctionApp. There is no Flask dependency;
each endpoint is registered as an individual Azure Function.

Endpoints:
    GET  /api/models          - List all available models from configuration.
    POST /api/chat            - Generate text response from a text prompt.
    POST /api/chat/vision     - Generate text response from text + image prompt.
    GET  /api/ping            - Health check endpoint.
    POST /api/users           - Add a new user.
    DELETE /api/users/{username} - Delete a user by username.
    PUT  /api/users/{username}  - Update a user's password and/or admin flag.
    POST /api/users/validate  - Validate user credentials.
"""

import json
import logging
from datetime import datetime, timezone

import azure.functions as func
from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError

from services.config_loader import get_all_models, get_model_by_id
from services.provider_factory import get_provider
from services import user_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


# ---------------------------------------------------------------------------
# Helper to build JSON responses
# ---------------------------------------------------------------------------
def _json_response(body: dict, status_code: int = 200) -> func.HttpResponse:
    """Return an HttpResponse with JSON content type."""
    return func.HttpResponse(
        body=json.dumps(body),
        status_code=status_code,
        mimetype="application/json",
    )


# ---------------------------------------------------------------------------
# Endpoint 1: List available models
# ---------------------------------------------------------------------------
@app.route(route="models", methods=["GET"])
def list_models(req: func.HttpRequest) -> func.HttpResponse:
    """Return a list of all available models from the configuration file."""
    try:
        models = get_all_models()
        return _json_response({"models": models, "count": len(models)})
    except Exception as e:
        logger.exception("Error retrieving model list.")
        return _json_response({"error": str(e)}, 500)


# ---------------------------------------------------------------------------
# Endpoint 2: Text chat completion
# ---------------------------------------------------------------------------
@app.route(route="chat", methods=["POST"])
def chat(req: func.HttpRequest) -> func.HttpResponse:
    """Generate a text response for a given prompt and model."""
    try:
        data = req.get_json()
    except ValueError:
        return _json_response({"error": "Request body must be valid JSON."}, 400)

    prompt = data.get("prompt")
    model_id = data.get("modelId")

    if not prompt:
        return _json_response({"error": "Field 'prompt' is required."}, 400)
    if not model_id:
        return _json_response({"error": "Field 'modelId' is required."}, 400)

    model_config = get_model_by_id(model_id)
    if not model_config:
        return _json_response({"error": f"Model '{model_id}' not found."}, 404)

    try:
        provider = get_provider(model_config["providerName"])
        response_text = provider.generate_text(
            prompt=prompt,
            model_name=model_config["modelName"],
            temperature=model_config.get("temperature", 0.7),
        )
        return _json_response({
            "response": response_text,
            "modelId": model_id,
            "providerName": model_config["providerName"],
        })
    except ValueError as ve:
        logger.error("Configuration error: %s", ve)
        return _json_response({"error": str(ve)}, 400)
    except Exception as e:
        logger.exception("Error during text generation with model '%s'.", model_id)
        return _json_response({"error": f"Generation failed: {str(e)}"}, 500)


# ---------------------------------------------------------------------------
# Endpoint 3: Vision chat completion (text + image)
# ---------------------------------------------------------------------------
@app.route(route="chat/vision", methods=["POST"])
def chat_vision(req: func.HttpRequest) -> func.HttpResponse:
    """Generate a text response for a text prompt combined with an image."""
    try:
        data = req.get_json()
    except ValueError:
        return _json_response({"error": "Request body must be valid JSON."}, 400)

    prompt = data.get("prompt")
    image_content = data.get("imageContent")
    model_id = data.get("modelId")
    image_media_type = data.get("imageMediaType", "image/png")

    if not prompt:
        return _json_response({"error": "Field 'prompt' is required."}, 400)
    if not image_content:
        return _json_response({"error": "Field 'imageContent' is required."}, 400)
    if not model_id:
        return _json_response({"error": "Field 'modelId' is required."}, 400)

    model_config = get_model_by_id(model_id)
    if not model_config:
        return _json_response({"error": f"Model '{model_id}' not found."}, 404)

    if not model_config.get("supportsVision", False):
        return _json_response(
            {"error": f"Model '{model_id}' does not support vision/image input."},
            400,
        )

    try:
        provider = get_provider(model_config["providerName"])
        response_text = provider.generate_with_image(
            prompt=prompt,
            image_content=image_content,
            model_name=model_config["modelName"],
            temperature=model_config.get("temperature", 0.7),
            image_media_type=image_media_type,
        )
        return _json_response({
            "response": response_text,
            "modelId": model_id,
            "providerName": model_config["providerName"],
        })
    except ValueError as ve:
        logger.error("Validation error: %s", ve)
        return _json_response({"error": str(ve)}, 400)
    except Exception as e:
        logger.exception("Error during vision generation with model '%s'.", model_id)
        return _json_response({"error": f"Generation failed: {str(e)}"}, 500)


# ---------------------------------------------------------------------------
# Endpoint 4: Ping / Health check
# ---------------------------------------------------------------------------
@app.route(route="ping", methods=["GET"])
def ping(req: func.HttpRequest) -> func.HttpResponse:
    """Health check endpoint to verify the function is running."""
    return _json_response({
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "Multi-Provider LLM API",
    })


# ---------------------------------------------------------------------------
# Endpoint 5: Add a new user
# ---------------------------------------------------------------------------
@app.route(route="users", methods=["POST"])
def add_user(req: func.HttpRequest) -> func.HttpResponse:
    """
    Create a new user in Azure Table Storage.

    Request Body (JSON):
        - username (str, required): Unique username.
        - password (str, required): Base64-encoded (btoa) password.
        - isAdmin (bool, required): Whether the user is an admin.

    Response:
        201: The created user object.
        400: Missing required fields.
        409: User already exists.
        500: Internal error.
    """
    try:
        data = req.get_json()
    except ValueError:
        return _json_response({"error": "Request body must be valid JSON."}, 400)

    username = data.get("username")
    password = data.get("password")
    is_admin = data.get("isAdmin")

    if not username:
        return _json_response({"error": "Field 'username' is required."}, 400)
    if not password:
        return _json_response({"error": "Field 'password' is required."}, 400)
    if is_admin is None:
        return _json_response({"error": "Field 'isAdmin' is required."}, 400)

    try:
        user = user_service.add_user(username, password, bool(is_admin))
        return _json_response({"user": user}, 201)
    except ResourceExistsError:
        return _json_response(
            {"error": f"User '{username}' already exists."}, 409
        )
    except ValueError as ve:
        logger.error("Configuration error: %s", ve)
        return _json_response({"error": str(ve)}, 500)
    except Exception as e:
        logger.exception("Error adding user '%s'.", username)
        return _json_response({"error": f"Failed to add user: {str(e)}"}, 500)


# ---------------------------------------------------------------------------
# Endpoint 6: Delete a user
# ---------------------------------------------------------------------------
@app.route(route="users/{username}", methods=["DELETE"])
def delete_user(req: func.HttpRequest) -> func.HttpResponse:
    """
    Delete a user from Azure Table Storage.

    Route Parameters:
        - username (str): The username to delete.

    Response:
        200: Confirmation message.
        404: User not found.
        500: Internal error.
    """
    username = req.route_params.get("username")
    if not username:
        return _json_response({"error": "Username is required in the URL."}, 400)

    try:
        user_service.delete_user(username)
        return _json_response({"message": f"User '{username}' deleted successfully."})
    except ResourceNotFoundError:
        return _json_response({"error": f"User '{username}' not found."}, 404)
    except ValueError as ve:
        logger.error("Configuration error: %s", ve)
        return _json_response({"error": str(ve)}, 500)
    except Exception as e:
        logger.exception("Error deleting user '%s'.", username)
        return _json_response({"error": f"Failed to delete user: {str(e)}"}, 500)


# ---------------------------------------------------------------------------
# Endpoint 7: Update a user
# ---------------------------------------------------------------------------
@app.route(route="users/{username}", methods=["PUT"])
def update_user(req: func.HttpRequest) -> func.HttpResponse:
    """
    Update a user's password and/or admin flag.

    Route Parameters:
        - username (str): The username to update.

    Request Body (JSON):
        - password (str, optional): New base64-encoded (btoa) password.
        - isAdmin (bool, optional): New admin flag value.

    Response:
        200: The updated user object.
        400: No updatable fields provided.
        404: User not found.
        500: Internal error.
    """
    username = req.route_params.get("username")
    if not username:
        return _json_response({"error": "Username is required in the URL."}, 400)

    try:
        data = req.get_json()
    except ValueError:
        return _json_response({"error": "Request body must be valid JSON."}, 400)

    password = data.get("password")
    is_admin = data.get("isAdmin")

    if password is None and is_admin is None:
        return _json_response(
            {"error": "At least one of 'password' or 'isAdmin' must be provided."},
            400,
        )

    is_admin_val = bool(is_admin) if is_admin is not None else None

    try:
        user = user_service.update_user(username, password=password, is_admin=is_admin_val)
        return _json_response({"user": user})
    except ResourceNotFoundError:
        return _json_response({"error": f"User '{username}' not found."}, 404)
    except ValueError as ve:
        logger.error("Configuration error: %s", ve)
        return _json_response({"error": str(ve)}, 500)
    except Exception as e:
        logger.exception("Error updating user '%s'.", username)
        return _json_response({"error": f"Failed to update user: {str(e)}"}, 500)


# ---------------------------------------------------------------------------
# Endpoint 8: Validate user credentials
# ---------------------------------------------------------------------------
@app.route(route="users/validate", methods=["POST"])
def validate_user(req: func.HttpRequest) -> func.HttpResponse:
    """
    Validate a user's credentials and return the user object if valid.

    Request Body (JSON):
        - username (str, required): The username to validate.
        - password (str, required): The base64-encoded (btoa) password.

    Response:
        200: The validated user object.
        400: Missing required fields.
        401: Invalid credentials.
        500: Internal error.
    """
    try:
        data = req.get_json()
    except ValueError:
        return _json_response({"error": "Request body must be valid JSON."}, 400)

    username = data.get("username")
    password = data.get("password")

    if not username:
        return _json_response({"error": "Field 'username' is required."}, 400)
    if not password:
        return _json_response({"error": "Field 'password' is required."}, 400)

    try:
        user = user_service.validate_user(username, password)
        if user:
            return _json_response({"user": user})
        return _json_response({"error": "Invalid username or password."}, 401)
    except ValueError as ve:
        logger.error("Configuration error: %s", ve)
        return _json_response({"error": str(ve)}, 500)
    except Exception as e:
        logger.exception("Error validating user '%s'.", username)
        return _json_response({"error": f"Validation failed: {str(e)}"}, 500)


logger.info("Multi-Provider LLM API Azure Function initialized.")
