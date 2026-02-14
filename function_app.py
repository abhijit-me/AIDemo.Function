"""
Azure Functions entry point for the Multi-Provider LLM API.

This module creates an Azure Functions application that delegates all HTTP
requests to a Flask application via the WsgiMiddleware adapter. This allows
Flask to handle routing, request parsing, and response formatting while
Azure Functions manages hosting, scaling, and authentication.

The Flask app is imported from flask_app.py and mounted using the WSGI
middleware so that all routes defined in Flask are accessible as Azure
Function HTTP triggers.
"""

import logging

import azure.functions as func

from flask_app import app as flask_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Create the Azure Functions application and mount the Flask WSGI app.
# The auth_level is set to ANONYMOUS so that the endpoints are publicly
# accessible (adjust to FUNCTION or ADMIN for production use).
app = func.WsgiFunctionApp(
    app=flask_app.wsgi_app,
    http_auth_level=func.AuthLevel.ANONYMOUS,
)

logger.info("Multi-Provider LLM API Azure Function initialized.")
