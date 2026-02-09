"""
Flask application module for the Multi-Provider LLM API.

Defines the REST API endpoints that are served by the Azure Function.
All routes are prefixed under /api to align with Azure Functions HTTP
trigger conventions.

Endpoints:
    GET  /api/models       - List all available models from configuration.
    POST /api/chat         - Generate text response from a text prompt.
    POST /api/chat/vision  - Generate text response from text + image prompt.
    GET  /api/ping         - Health check endpoint.
"""

import logging
from datetime import datetime, timezone

from flask import Flask, jsonify, request

from services.config_loader import get_all_models, get_model_by_id
from services.provider_factory import get_provider

logger = logging.getLogger(__name__)

app = Flask(__name__)


# ---------------------------------------------------------------------------
# Endpoint 1: List available models
# ---------------------------------------------------------------------------
@app.route("/api/models", methods=["GET"])
def list_models():
    """
    Return a list of all available models from the configuration file.

    Response:
        200: JSON array of model objects, each containing:
            - modelId (str): Unique identifier for the model.
            - modelName (str): Provider-specific model name.
            - providerName (str): Name of the LLM provider.
            - temperature (float): Default sampling temperature.
            - supportsVision (bool): Whether the model supports image input.
            - description (str): Human-readable description.
    """
    try:
        models = get_all_models()
        return jsonify({"models": models, "count": len(models)}), 200
    except Exception as e:
        logger.exception("Error retrieving model list.")
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# Endpoint 2: Text chat completion
# ---------------------------------------------------------------------------
@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Generate a text response for a given prompt and model.

    Request Body (JSON):
        - prompt (str, required): The text prompt to send to the model.
        - modelId (str, required): The ID of the model to use (from config).

    Response:
        200: JSON object with:
            - response (str): The generated text.
            - modelId (str): The model ID that was used.
            - providerName (str): The provider that handled the request.
        400: If required fields are missing.
        404: If the modelId is not found in configuration.
        500: If the provider call fails.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be valid JSON."}), 400

    prompt = data.get("prompt")
    model_id = data.get("modelId")

    # Validate required fields
    if not prompt:
        return jsonify({"error": "Field 'prompt' is required."}), 400
    if not model_id:
        return jsonify({"error": "Field 'modelId' is required."}), 400

    # Look up the model configuration
    model_config = get_model_by_id(model_id)
    if not model_config:
        return jsonify({"error": f"Model '{model_id}' not found."}), 404

    try:
        provider = get_provider(model_config["providerName"])
        response_text = provider.generate_text(
            prompt=prompt,
            model_name=model_config["modelName"],
            temperature=model_config.get("temperature", 0.7),
        )

        return jsonify({
            "response": response_text,
            "modelId": model_id,
            "providerName": model_config["providerName"],
        }), 200

    except ValueError as ve:
        logger.error("Configuration error: %s", ve)
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        logger.exception("Error during text generation with model '%s'.", model_id)
        return jsonify({"error": f"Generation failed: {str(e)}"}), 500


# ---------------------------------------------------------------------------
# Endpoint 3: Vision chat completion (text + image)
# ---------------------------------------------------------------------------
@app.route("/api/chat/vision", methods=["POST"])
def chat_vision():
    """
    Generate a text response for a given text prompt combined with an image.

    Request Body (JSON):
        - prompt (str, required): The text prompt to send to the model.
        - imageContent (str, required): Base64-encoded image data or image URL.
        - modelId (str, required): The ID of the model to use (from config).
        - imageMediaType (str, optional): MIME type of the image
          (e.g., 'image/png', 'image/jpeg'). Defaults to 'image/png'.

    Response:
        200: JSON object with:
            - response (str): The generated text.
            - modelId (str): The model ID that was used.
            - providerName (str): The provider that handled the request.
        400: If required fields are missing or the model does not support vision.
        404: If the modelId is not found in configuration.
        500: If the provider call fails.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be valid JSON."}), 400

    prompt = data.get("prompt")
    image_content = data.get("imageContent")
    model_id = data.get("modelId")
    image_media_type = data.get("imageMediaType", "image/png")

    # Validate required fields
    if not prompt:
        return jsonify({"error": "Field 'prompt' is required."}), 400
    if not image_content:
        return jsonify({"error": "Field 'imageContent' is required."}), 400
    if not model_id:
        return jsonify({"error": "Field 'modelId' is required."}), 400

    # Look up the model configuration
    model_config = get_model_by_id(model_id)
    if not model_config:
        return jsonify({"error": f"Model '{model_id}' not found."}), 404

    # Check if the model supports vision
    if not model_config.get("supportsVision", False):
        return jsonify({
            "error": f"Model '{model_id}' does not support vision/image input."
        }), 400

    try:
        provider = get_provider(model_config["providerName"])
        response_text = provider.generate_with_image(
            prompt=prompt,
            image_content=image_content,
            model_name=model_config["modelName"],
            temperature=model_config.get("temperature", 0.7),
            image_media_type=image_media_type,
        )

        return jsonify({
            "response": response_text,
            "modelId": model_id,
            "providerName": model_config["providerName"],
        }), 200

    except ValueError as ve:
        logger.error("Validation error: %s", ve)
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        logger.exception(
            "Error during vision generation with model '%s'.", model_id
        )
        return jsonify({"error": f"Generation failed: {str(e)}"}), 500


# ---------------------------------------------------------------------------
# Endpoint 4: Ping / Health check
# ---------------------------------------------------------------------------
@app.route("/api/ping", methods=["GET"])
def ping():
    """
    Health check endpoint to verify the function is running.

    Response:
        200: JSON object with:
            - status (str): 'healthy'
            - timestamp (str): Current UTC timestamp in ISO 8601 format.
            - service (str): Name of the service.
    """
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "Multi-Provider LLM API",
    }), 200
