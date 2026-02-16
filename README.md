# Multi-Provider LLM API — Azure Function

A Python Azure Function that provides a unified REST API for interacting with multiple Large Language Model (LLM) providers and user management. Built natively on the **Azure Functions** Python v2 programming model with **Azure Table Storage** for user data persistence.

## Supported Providers

| Provider | SDK | Models (examples) |
|---|---|---|
| **OpenAI** | `openai` | GPT-4o, GPT-4o Mini, GPT-4 Turbo |
| **Azure OpenAI** | `openai` (Azure mode) | GPT-4o, GPT-4o Mini (Azure deployments) |
| **Anthropic** | `anthropic` | Claude Sonnet 4, Claude 3.5 Haiku |
| **AWS Bedrock** | `boto3` | Claude (Anthropic) & Llama 3 (Meta) on Bedrock |

## Project Structure

```
├── function_app.py              # Azure Functions entry point (all HTTP triggers)
├── models_config.json           # Model + user storage configuration (editable)
├── host.json                    # Azure Functions host configuration
├── local.settings.json          # Local environment variables (git-ignored)
├── requirements.txt             # Python dependencies
├── .gitignore                   # Git ignore rules
├── services/
│   ├── __init__.py              # Services package init
│   ├── base_provider.py         # Abstract base class for all providers
│   ├── openai_provider.py       # OpenAI API integration
│   ├── azure_openai_provider.py # Azure OpenAI integration
│   ├── anthropic_provider.py    # Anthropic Claude integration
│   ├── bedrock_provider.py      # AWS Bedrock integration (Claude + Llama)
│   ├── provider_factory.py      # Factory to instantiate the correct provider
│   ├── config_loader.py         # Configuration file loader and accessor
│   └── user_service.py          # User CRUD operations via Azure Table Storage
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

### 5. Add New User

```
POST /api/users
Content-Type: application/json
```

Creates a new user in Azure Table Storage. The password should be sent already base64-encoded (btoa format) from the UI.

**Request Body:**
```json
{
  "username": "johndoe",
  "password": "cGFzc3dvcmQxMjM=",
  "isAdmin": false
}
```

**Response (201):**
```json
{
  "user": {
    "username": "johndoe",
    "password": "cGFzc3dvcmQxMjM=",
    "isAdmin": false
  }
}
```

**Error (409):**
```json
{
  "error": "User 'johndoe' already exists."
}
```

### 6. Delete User

```
DELETE /api/users/{username}
```

Deletes a user by username.

**Response (200):**
```json
{
  "message": "User 'johndoe' deleted successfully."
}
```

**Error (404):**
```json
{
  "error": "User 'johndoe' not found."
}
```

### 7. Update User

```
PUT /api/users/{username}
Content-Type: application/json
```

Updates a user's password and/or admin flag. At least one field must be provided. The password should be sent already base64-encoded (btoa format) from the UI.

**Request Body:**
```json
{
  "password": "bmV3cGFzc3dvcmQ=",
  "isAdmin": true
}
```

**Response (200):**
```json
{
  "user": {
    "username": "johndoe",
    "password": "bmV3cGFzc3dvcmQ=",
    "isAdmin": true
  }
}
```

**Error (404):**
```json
{
  "error": "User 'johndoe' not found."
}
```

### 8. Validate User

```
POST /api/users/validate
Content-Type: application/json
```

Validates a user's credentials. Takes a username and a base64-encoded (btoa) password, and returns the full user object if the credentials are valid.

**Request Body:**
```json
{
  "username": "johndoe",
  "password": "cGFzc3dvcmQxMjM="
}
```

**Response (200):**
```json
{
  "user": {
    "username": "johndoe",
    "password": "cGFzc3dvcmQxMjM=",
    "isAdmin": false
  }
}
```

**Error (401):**
```json
{
  "error": "Invalid username or password."
}
```

## Configuration

### Models Configuration (`models_config.json`)

The configuration file contains two sections: model definitions and user storage settings.

#### Models

Each model entry has:

| Field | Type | Description |
|---|---|---|
| `modelId` | string | Unique identifier used in API requests |
| `modelName` | string | Provider-specific model name / deployment name |
| `providerName` | string | One of: `OpenAI`, `Azure OpenAI`, `Anthropic`, `AWS Bedrock` |
| `temperature` | float | Default sampling temperature for the model |
| `supportsVision` | bool | Whether the model accepts image input |
| `description` | string | Human-readable description |

To add a new model, simply add a new entry to the `models` array in the JSON file.

#### User Storage

The `userStorage` section configures Azure Table Storage for user management:

| Field | Type | Description |
|---|---|---|
| `tableName` | string | Name of the Azure Table Storage table (default: `Users`) |
| `partitionKey` | string | Partition key used for all user entities (default: `user`) |
| `connectionStringEnvVar` | string | Environment variable name that holds the Azure Storage connection string |

### Environment Variables

Set these in `local.settings.json` for local development, or in Azure Function Application Settings for production:

| Variable | Required For | Description |
|---|---|---|
| `AZURE_STORAGE_CONNECTION_STRING` | User Management | Connection string for Azure Table Storage |
| `OPENAI_API_KEY` | OpenAI | API key for OpenAI |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI | API key for Azure OpenAI resource |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI | Azure OpenAI resource endpoint URL |
| `AZURE_OPENAI_API_VERSION` | Azure OpenAI | API version (default: `2024-10-21`) |
| `ANTHROPIC_API_KEY` | Anthropic | API key for Anthropic |
| `AWS_ACCESS_KEY_ID` | AWS Bedrock | AWS access key ID |
| `AWS_SECRET_ACCESS_KEY` | AWS Bedrock | AWS secret access key |
| `AWS_REGION` | AWS Bedrock | AWS region (default: `us-east-1`) |

> **Note:** You only need to configure the environment variables for the providers and features you intend to use. `AZURE_STORAGE_CONNECTION_STRING` is required for all user management endpoints.

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
   Copy and edit `local.settings.json` with your API keys and Azure Storage connection string.

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

   # Add a user
   curl -X POST http://localhost:7071/api/users \
     -H "Content-Type: application/json" \
     -d '{"username": "johndoe", "password": "cGFzc3dvcmQxMjM=", "isAdmin": false}'

   # Validate a user
   curl -X POST http://localhost:7071/api/users/validate \
     -H "Content-Type: application/json" \
     -d '{"username": "johndoe", "password": "cGFzc3dvcmQxMjM="}'

   # Update a user
   curl -X PUT http://localhost:7071/api/users/johndoe \
     -H "Content-Type: application/json" \
     -d '{"isAdmin": true}'

   # Delete a user
   curl -X DELETE http://localhost:7071/api/users/johndoe
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
      │  Native HTTP Triggers
      ├──────────────────────────────────┐
      │                                  │
      ▼                                  ▼
LLM Endpoints                    User Endpoints
(models, chat, chat/vision)      (add, delete, update, validate)
      │                                  │
      ▼                                  ▼
Config Loader                    User Service
(config_loader.py)               (user_service.py)
      │                                  │
      ▼                                  ▼
Provider Factory                 Azure Table Storage
(provider_factory.py)
      │
      ▼
Provider Service
(e.g., openai_provider.py)
      │
      ▼
LLM Provider API
(OpenAI / Azure / Anthropic / Bedrock)
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
| 401 | Invalid credentials (user validation failed) |
| 404 | Resource not found (model ID or username) |
| 409 | Conflict (user already exists) |
| 500 | Internal server error (API call failure, configuration error) |
