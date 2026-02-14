# Multi-Provider LLM API — Azure Function

A Python Azure Function that provides a unified REST API for interacting with multiple Large Language Model (LLM) providers. Built with **Flask** for API routing and the respective provider SDKs for backend communication.

## Supported Providers

| Provider | SDK | Models (examples) |
|---|---|---|
| **OpenAI** | `openai` | GPT-4o, GPT-4o Mini, GPT-4 Turbo |
| **Azure OpenAI** | `openai` (Azure mode) | GPT-4o, GPT-4o Mini (Azure deployments) |
| **Anthropic** | `anthropic` | Claude Sonnet 4, Claude 3.5 Haiku |
| **AWS Bedrock** | `boto3` | Claude (Anthropic) & Llama 3 (Meta) on Bedrock |

## Project Structure

```
├── function_app.py          # Azure Functions entry point (WSGI adapter)
├── flask_app.py             # Flask application with all API endpoints
├── models_config.json       # Model configuration (editable)
├── host.json                # Azure Functions host configuration
├── local.settings.json      # Local environment variables (git-ignored)
├── requirements.txt         # Python dependencies
├── .gitignore               # Git ignore rules
├── services/
│   ├── __init__.py          # Services package init
│   ├── base_provider.py     # Abstract base class for all providers
│   ├── openai_provider.py   # OpenAI API integration
│   ├── azure_openai_provider.py  # Azure OpenAI integration
│   ├── anthropic_provider.py     # Anthropic Claude integration
│   ├── bedrock_provider.py       # AWS Bedrock integration (Claude + Llama)
│   ├── provider_factory.py  # Factory to instantiate the correct provider
│   └── config_loader.py     # Configuration file loader and accessor
└── README.md
```

## API Endpoints

All endpoints are prefixed with `/api`.

### 1. List Models

```
GET /api/models
```

Returns all available models from the configuration file.

**Response (200):**
```json
{
  "models": [
    {
      "modelId": "openai-gpt4o",
      "modelName": "gpt-4o",
      "providerName": "OpenAI",
      "temperature": 0.7,
      "supportsVision": true,
      "description": "OpenAI GPT-4o - multimodal model with vision support"
    }
  ],
  "count": 11
}
```

### 2. Text Chat Completion

```
POST /api/chat
Content-Type: application/json
```

Sends a text prompt to the specified model and returns the response.

**Request Body:**
```json
{
  "prompt": "Explain quantum computing in simple terms.",
  "modelId": "openai-gpt4o"
}
```

**Response (200):**
```json
{
  "response": "Quantum computing uses quantum bits...",
  "modelId": "openai-gpt4o",
  "providerName": "OpenAI"
}
```

### 3. Vision Chat Completion (Text + Image)

```
POST /api/chat/vision
Content-Type: application/json
```

Sends a text prompt along with an image to a vision-capable model.

**Request Body:**
```json
{
  "prompt": "Describe what you see in this image.",
  "imageContent": "<base64-encoded-image-data-or-URL>",
  "modelId": "openai-gpt4o",
  "imageMediaType": "image/png"
}
```

- `imageContent`: Base64-encoded image data **or** an image URL (starting with `http`).
- `imageMediaType` (optional): MIME type of the image. Defaults to `image/png`. Supported: `image/png`, `image/jpeg`, `image/gif`, `image/webp`.

**Response (200):**
```json
{
  "response": "The image shows a landscape with mountains...",
  "modelId": "openai-gpt4o",
  "providerName": "OpenAI"
}
```

### 4. Ping / Health Check

```
GET /api/ping
```

Returns the health status of the function.

**Response (200):**
```json
{
  "status": "healthy",
  "timestamp": "2026-02-09T10:30:00+00:00",
  "service": "Multi-Provider LLM API"
}
```

## Configuration

### Models Configuration (`models_config.json`)

The available models are defined in `models_config.json`. Each entry has:

| Field | Type | Description |
|---|---|---|
| `modelId` | string | Unique identifier used in API requests |
| `modelName` | string | Provider-specific model name / deployment name |
| `providerName` | string | One of: `OpenAI`, `Azure OpenAI`, `Anthropic`, `AWS Bedrock` |
| `temperature` | float | Default sampling temperature for the model |
| `supportsVision` | bool | Whether the model accepts image input |
| `description` | string | Human-readable description |

To add a new model, simply add a new entry to the `models` array in the JSON file.

### Environment Variables

Set these in `local.settings.json` for local development, or in Azure Function Application Settings for production:

| Variable | Required For | Description |
|---|---|---|
| `OPENAI_API_KEY` | OpenAI | API key for OpenAI |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI | API key for Azure OpenAI resource |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI | Azure OpenAI resource endpoint URL |
| `AZURE_OPENAI_API_VERSION` | Azure OpenAI | API version (default: `2024-10-21`) |
| `ANTHROPIC_API_KEY` | Anthropic | API key for Anthropic |
| `AWS_ACCESS_KEY_ID` | AWS Bedrock | AWS access key ID |
| `AWS_SECRET_ACCESS_KEY` | AWS Bedrock | AWS secret access key |
| `AWS_REGION` | AWS Bedrock | AWS region (default: `us-east-1`) |

> **Note:** You only need to configure the environment variables for the providers you intend to use. If you only use OpenAI models, only `OPENAI_API_KEY` is required.

## Local Development

### Prerequisites

- Python 3.9+
- [Azure Functions Core Tools v4](https://learn.microsoft.com/en-us/azure/azure-functions/functions-run-local)

### Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment variables:**
   Copy and edit `local.settings.json` with your API keys.

3. **Run the function locally:**
   ```bash
   func start
   ```

4. **Test the endpoints:**
   ```bash
   # Health check
   curl http://localhost:7071/api/ping

   # List models
   curl http://localhost:7071/api/models

   # Text chat
   curl -X POST http://localhost:7071/api/chat \
     -H "Content-Type: application/json" \
     -d '{"prompt": "Hello, world!", "modelId": "openai-gpt4o"}'

   # Vision chat
   curl -X POST http://localhost:7071/api/chat/vision \
     -H "Content-Type: application/json" \
     -d '{"prompt": "Describe this image.", "imageContent": "<base64-data>", "modelId": "openai-gpt4o"}'
   ```

## Deployment

Deploy to Azure using the Azure Functions Core Tools or the Azure CLI:

```bash
func azure functionapp publish <YOUR_FUNCTION_APP_NAME>
```

Make sure to configure the required environment variables in your Azure Function App's Application Settings before making API calls.

## Architecture

```
Client Request
      │
      ▼
Azure Functions (function_app.py)
      │  WSGI Middleware
      ▼
Flask App (flask_app.py)
      │  Route matching
      ▼
Config Loader (config_loader.py)
      │  Model lookup by modelId
      ▼
Provider Factory (provider_factory.py)
      │  Instantiate correct provider
      ▼
Provider Service (e.g., openai_provider.py)
      │  Call external API
      ▼
LLM Provider API (OpenAI / Azure / Anthropic / Bedrock)
      │
      ▼
Response returned to client
```

## Error Handling

All endpoints return consistent JSON error responses:

```json
{
  "error": "Descriptive error message."
}
```

| HTTP Status | Meaning |
|---|---|
| 400 | Bad request (missing fields, unsupported model features) |
| 404 | Model ID not found in configuration |
| 500 | Internal server error (API call failure, configuration error) |
