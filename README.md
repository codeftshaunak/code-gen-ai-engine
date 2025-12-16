# Builder AI Engine - Pure Python Edition

A powerful AI-powered code generation engine built with **FastAPI** and Python. This is a complete reimplementation of the Next.js-based AI engine with the 5 core APIs needed for production use.

## Features

- **AI Code Generation**: Stream code generation from multiple AI providers (Anthropic, OpenAI, Google, Groq, OpenRouter)
- **Code Application**: Apply AI-generated code to sandboxed environments with real-time progress
- **Package Management**: Automatic npm package detection and installation
- **Conversation State**: Track conversation history and project evolution
- **Multi-Project Support**: Isolated state management for concurrent projects
- **Sandbox Providers**: Support for E2B Code Interpreter and Vercel Sandboxes
- **Auto Swagger Documentation**: Built-in OpenAPI/Swagger UI

## Architecture

```
python-ai-engine/
├── main.py                          # FastAPI application entry point
├── app/
│   ├── api/
│   │   ├── routes.py                # Main router
│   │   └── endpoints/               # API endpoint implementations
│   │       ├── generate_ai_code.py  # /api/generate-ai-code-stream
│   │       ├── apply_ai_code.py     # /api/apply-ai-code-stream
│   │       ├── install_packages.py  # /api/install-packages
│   │       ├── detect_packages.py   # /api/detect-and-install-packages
│   │       └── conversation.py      # /api/conversation-state
│   ├── core/
│   │   ├── app_state_manager.py     # Multi-project state management
│   │   ├── ai_provider.py           # AI model provider manager
│   │   └── sandbox_provider.py      # Sandbox abstraction layer
│   ├── models/
│   │   ├── conversation.py          # Conversation state models
│   │   └── api_models.py            # Request/response models
│   ├── config/
│   │   └── settings.py              # Centralized configuration
│   └── utils/
│       ├── code_parser.py           # Code parsing utilities
│       └── project_utils.py         # Project validation helpers
├── requirements.txt                 # Python dependencies
├── .env.example                     # Environment variables template
└── README.md                        # This file
```

## Core APIs

### 1. Generate AI Code Stream
**Endpoint**: `POST /api/generate-ai-code-stream`

Stream code generation from AI models with real-time updates.

**Request**:
```json
{
  "prompt": "Create a React login form",
  "model": "anthropic/claude-3-5-sonnet-20241022",
  "context": {
    "currentFiles": {},
    "conversationContext": {}
  },
  "is_edit": false
}
```

**Headers**: `X-Project-Id: your-project-id`

**Response**: Server-Sent Events stream

### 2. Apply AI Code Stream
**Endpoint**: `POST /api/apply-ai-code-stream`

Apply AI-generated code to sandbox with automatic package installation.

**Request**:
```json
{
  "response": "<file path=\"src/App.jsx\">...</file><package>react-router-dom</package>",
  "is_edit": false,
  "packages": ["additional-package"],
  "sandbox_id": "sandbox-123"
}
```

**Headers**: `X-Project-Id: your-project-id`

**Response**: Server-Sent Events stream

### 3. Install Packages
**Endpoint**: `POST /api/install-packages`

Install npm packages with automatic Vite server restart.

**Request**:
```json
{
  "packages": ["react-router-dom", "axios", "@mui/material"],
  "sandbox_id": "sandbox-123"
}
```

**Headers**: `X-Project-Id: your-project-id`

**Response**: Server-Sent Events stream

### 4. Detect and Install Packages
**Endpoint**: `POST /api/detect-and-install-packages`

Auto-detect packages from import statements.

**Request**:
```json
{
  "files": {
    "src/App.jsx": "import React from 'react';\nimport { BrowserRouter } from 'react-router-dom';"
  }
}
```

**Headers**: `X-Project-Id: your-project-id`

**Response**:
```json
{
  "success": true,
  "packages_installed": ["react-router-dom"],
  "packages_already_installed": ["react"],
  "message": "Detected 2 packages. 1 needs installation."
}
```

### 5. Conversation State
**Endpoint**: `GET/POST/DELETE /api/conversation-state`

Manage conversation history and context.

**GET** - Retrieve current state
**POST** - Update state (actions: `reset`, `clear-old`, `update`)
**DELETE** - Clear all conversation data

**Headers**: `X-Project-Id: your-project-id`

## Installation & Setup

### Prerequisites

- Python 3.10 or higher
- pip or poetry
- Node.js and npm (for sandbox operations)
- API keys for AI providers (Anthropic, OpenAI, etc.)
- Sandbox provider credentials (E2B or Vercel)

### Step 1: Clone and Navigate

```bash
cd python-ai-engine
```

### Step 2: Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your API keys:

```env
# Required
SANDBOX_PROVIDER=e2b
E2B_API_KEY=your_e2b_api_key
ANTHROPIC_API_KEY=your_anthropic_key

# Optional
OPENAI_API_KEY=your_openai_key
GEMINI_API_KEY=your_gemini_key
```

### Step 5: Run the Server

```bash
# Development mode (auto-reload)
python main.py

# OR with uvicorn directly
uvicorn main:app --reload --port 3100
```

Server will start at: `http://localhost:3100`

## API Documentation

Once the server is running, access the auto-generated documentation:

- **Swagger UI**: http://localhost:3100/api/docs
- **ReDoc**: http://localhost:3100/api/redoc
- **OpenAPI JSON**: http://localhost:3100/api/openapi.json

## Usage Examples

### Example 1: Generate and Apply Code

```python
import requests
import json

# Step 1: Generate code
headers = {"X-Project-Id": "my-project-123"}
generate_request = {
    "prompt": "Create a React counter component with increment and decrement buttons",
    "model": "anthropic/claude-3-5-sonnet-20241022"
}

response = requests.post(
    "http://localhost:3100/api/generate-ai-code-stream",
    headers=headers,
    json=generate_request,
    stream=True
)

# Process SSE stream
for line in response.iter_lines():
    if line:
        data = json.loads(line.decode('utf-8').replace('data: ', ''))
        print(data)

# Step 2: Apply generated code
apply_request = {
    "response": generated_code,
    "is_edit": False,
    "packages": []
}

response = requests.post(
    "http://localhost:3100/api/apply-ai-code-stream",
    headers=headers,
    json=apply_request,
    stream=True
)
```

### Example 2: Manage Conversation

```python
# Get conversation state
response = requests.get(
    "http://localhost:3100/api/conversation-state",
    headers={"X-Project-Id": "my-project-123"}
)
conversation = response.json()

# Update conversation
update_request = {
    "action": "update",
    "data": {
        "currentTopic": "Building user authentication",
        "userPreferences": {
            "editStyle": "targeted"
        }
    }
}

response = requests.post(
    "http://localhost:3100/api/conversation-state",
    headers={"X-Project-Id": "my-project-123"},
    json=update_request
)
```

## Configuration

### AI Models

Supported providers and models:

| Provider | Model Examples |
|----------|---------------|
| Anthropic | `anthropic/claude-3-5-sonnet-20241022`, `anthropic/claude-3-opus-20240229` |
| OpenAI | `openai/gpt-4-turbo`, `openai/gpt-4o` |
| Google | `google/gemini-1.5-pro`, `google/gemini-1.5-flash` |
| Groq | `groq/llama-3.1-70b`, `groq/mixtral-8x7b` |
| OpenRouter | `openrouter/anthropic/claude-3.5-sonnet` |

### Sandbox Providers

#### E2B (Recommended)
- Fast startup time
- Full Node.js environment
- Persistent file system
- Command execution

#### Vercel
- Serverless sandbox
- OIDC or PAT authentication
- Integrated with Vercel projects

## Multi-Project Support

Each request requires an `X-Project-Id` header. Projects are isolated:

- Separate sandbox instances
- Independent conversation history
- Isolated file caches
- Project-specific state

```bash
# Project A
curl -H "X-Project-Id: project-a" http://localhost:3100/api/conversation-state

# Project B (completely isolated)
curl -H "X-Project-Id: project-b" http://localhost:3100/api/conversation-state
```

## Development

### Running Tests

```bash
pytest
```

### Code Quality

```bash
# Format code
black .

# Lint
flake8 .

# Type checking
mypy .
```

## Differences from Next.js Version

| Feature | Next.js Version | Python Version |
|---------|----------------|----------------|
| Framework | Next.js 15 + React | FastAPI |
| Language | TypeScript | Python 3.10+ |
| API Routes | 35+ endpoints | 5 core endpoints |
| Streaming | SSE via Response | SSE via StreamingResponse |
| State Management | In-memory | In-memory (AppStateManager) |
| Documentation | Manual | Auto-generated Swagger |
| Deployment | Vercel, Node.js | Any Python host |

## Production Deployment

### Using Docker

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "3100"]
```

### Environment Variables

Set all required environment variables in your deployment platform:
- API keys (ANTHROPIC_API_KEY, etc.)
- Sandbox credentials (E2B_API_KEY or VERCEL_TOKEN)
- Configuration (PORT, DEBUG, etc.)

### Health Checks

- `/health` - Basic health check
- `/` - Root endpoint with version info

## Troubleshooting

### Issue: "No sandbox found"

**Solution**: Create a sandbox first using the appropriate sandbox provider API.

### Issue: "Missing X-Project-Id header"

**Solution**: Include `X-Project-Id` header in all requests.

### Issue: Package installation fails

**Solution**:
1. Check sandbox is running
2. Verify npm is available in sandbox
3. Try with `USE_LEGACY_PEER_DEPS=True`

### Issue: AI generation not working

**Solution**: Verify API keys in `.env` file and check provider status.

## Contributing

This is a production-ready Python implementation. Contributions welcome for:
- Additional AI providers
- New sandbox providers
- Performance optimizations
- Tests and documentation

## License

[Your License Here]

## Support

For issues and questions, please open an issue in the repository.

---

**Built with FastAPI, Python, and AI** 🚀
