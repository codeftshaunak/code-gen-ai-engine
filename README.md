# Python AI Engine

AI-powered code generation engine for React applications built with FastAPI and Python.

## Features

- 🚀 **Streaming Code Generation**: Real-time code streaming using Server-Sent Events (SSE)
- 🤖 **Access to All AI Models**: Uses OpenRouter for unified access to 200+ models including Anthropic Claude, OpenAI GPT, Google Gemini, Meta Llama, and more
- 🔄 **Automatic Retry Logic**: Handles transient failures with configurable retries
- 📝 **Context-Aware Generation**: Uses conversation history and existing files for better results
- ✨ **Best Practices**: Clean, maintainable Python code following industry standards
- 🔑 **Single API Key**: Only requires OPENROUTER_API_KEY for access to all models

## Project Structure

```
python-ai-engine/
├── main.py                          # FastAPI application entry point
├── app/
│   ├── api/
│   │   ├── routes.py                # Main router
│   │   └── endpoints/
│   │       └── generate_ai_code.py  # /api/generate-ai-code-stream
│   ├── core/
│   │   ├── ai_provider.py           # AI model provider manager
│   │   └── prompt_builder.py        # System prompt builder
│   ├── models/
│   │   └── api_models.py            # Request/response models
│   └── config/
│       └── settings.py              # Centralized configuration
├── requirements.txt                 # Python dependencies
├── .env.example                     # Environment variables template
└── README.md                        # This file
```

## Prerequisites

- Python 3.9 or higher
- pip (Python package manager)

## API Documentation

### POST `/api/generate-ai-code-stream`

Generates React code based on user prompt with real-time streaming.

**Request Body**:
```json
{
  "prompt": "Create a hero section with a dark background",
  "model": "anthropic/claude-3-5-sonnet-20241022",
  "context": {
    "sandboxId": "sb_123",
    "currentFiles": {
      "src/App.jsx": "..."
    },
    "conversationContext": {
      "scrapedWebsites": [],
      "currentProject": "my-app"
    }
  },
  "isEdit": false
}
```

**Response**: Server-Sent Events stream

Event types:
- `status`: Progress updates
- `stream`: Raw AI output chunks
- `complete`: Final code and metadata
- `error`: Error information

**Example using Python**:
```python
import requests
import json

url = "http://localhost:3100/api/generate-ai-code-stream"
data = {
    "prompt": "Create a hero section with dark background",
    "model": "anthropic/claude-3-5-sonnet-20241022"
}

response = requests.post(url, json=data, stream=True)

for line in response.iter_lines():
    if line.startswith(b'data: '):
        event = json.loads(line[6:])
        print(f"Event type: {event['type']}")
        if event['type'] == 'stream':
            print(event['text'], end='', flush=True)
        elif event['type'] == 'complete':
            print(f"\n\nGeneration complete! Files: {event['files']}")
```

**Example using JavaScript**:
```javascript
const eventSource = new EventSource('http://localhost:3100/api/generate-ai-code-stream', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    prompt: 'Create a hero section with dark background',
    model: 'anthropic/claude-3-5-sonnet-20241022'
  })
});

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Event:', data.type);

  if (data.type === 'stream') {
    process.stdout.write(data.text);
  } else if (data.type === 'complete') {
    console.log('\nGeneration complete!');
    eventSource.close();
  }
};
```

### GET `/health`

Health check endpoint.

**Response**:
```json
{
  "status": "healthy",
  "service": "Builder AI Engine",
  "version": "1.0.0"
}
```

## Installation

1. **Clone the repository** (if not already done)

2. **Navigate to the python-ai-engine directory**:
   ```bash
   cd python-ai-engine
   ```

3. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Configure environment variables**:
   ```bash
   cp .env.example .env
   ```

   Edit `.env` and add your OpenRouter API key:
   ```env
   OPENROUTER_API_KEY=sk-or-v1-...
   ```

   Get your OpenRouter API key at: https://openrouter.ai/keys

## Running the Server

### Development Mode

```bash
python main.py
```

Or using uvicorn directly:
```bash
uvicorn main:app --reload --port 3100
```

### Production Mode

```bash
uvicorn main:app --host 0.0.0.0 --port 3100 --workers 4
```

The server will start at `http://localhost:3100`

## Interactive API Documentation

Once the server is running in DEBUG mode, visit:
- Swagger UI: http://localhost:3100/docs
- ReDoc: http://localhost:3100/redoc

## Supported AI Models

This engine uses **OpenRouter** which provides unified access to 200+ AI models with a single API key.

### Popular Models Available:

**Anthropic Claude:**
- `anthropic/claude-3-5-sonnet-20241022` (recommended - best for code generation)
- `anthropic/claude-3-opus-20240229`
- `anthropic/claude-3-sonnet-20240229`
- `anthropic/claude-3-haiku-20240307`

**OpenAI GPT:**
- `openai/gpt-4-turbo`
- `openai/gpt-4`
- `openai/gpt-3.5-turbo`

**Google Gemini:**
- `google/gemini-pro-1.5`
- `google/gemini-flash-1.5`

**Meta Llama:**
- `meta-llama/llama-3.1-405b-instruct`
- `meta-llama/llama-3.1-70b-instruct`

**And 200+ more models...**

View all available models at: https://openrouter.ai/models

**Note:** You only need `OPENROUTER_API_KEY` - no other API keys required!

## Configuration

All configuration is done through environment variables in the `.env` file:

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_NAME` | Application name | Builder AI Engine |
| `VERSION` | Application version | 1.0.0 |
| `DEBUG` | Enable debug mode | True |
| `PORT` | Server port | 3100 |
| `CORS_ORIGINS` | Allowed CORS origins | * |
| `DEFAULT_AI_MODEL` | Default AI model | anthropic/claude-3-5-sonnet-20241022 |
| `DEFAULT_TEMPERATURE` | AI temperature | 0.7 |
| `MAX_TOKENS` | Maximum tokens to generate | 8192 |
| `MAX_RETRIES` | Maximum retry attempts | 2 |
| `RETRY_DELAY_SECONDS` | Delay between retries | 2 |

## Development

### Running Tests

```bash
pytest
```

### Code Style

This project follows Python best practices:
- PEP 8 style guide
- Type hints for better IDE support
- Comprehensive docstrings
- Async/await for I/O operations

## Error Handling

The API includes robust error handling:
- **400 Bad Request**: Invalid request parameters
- **500 Internal Server Error**: Server errors (includes details in debug mode)
- **Automatic Retries**: Retries on transient failures (rate limits, service unavailable)

Errors are streamed as SSE events:
```json
{
  "type": "error",
  "error": "Error message here"
}
```

## Logging

Logs are written to stdout with the following format:
```
2025-12-23 10:30:45 - app.core.ai_provider - INFO - Streaming code generation...
```

Set `DEBUG=True` in `.env` for verbose logging.

## Performance

- **Streaming**: Code is streamed in real-time as it's generated
- **Async I/O**: Non-blocking operations for better concurrency
- **Connection Pooling**: Reuses HTTP connections to AI providers
- **Keepalive**: Prevents connection timeouts during generation

## Security

- **API Keys**: Stored in environment variables, never committed to git
- **CORS**: Configurable allowed origins
- **Input Validation**: Pydantic models validate all inputs
- **Error Messages**: Sensitive details hidden in production mode

## Troubleshooting

### "OPENROUTER_API_KEY is required"
- Ensure you've set `OPENROUTER_API_KEY` in your `.env` file
- Get your API key from https://openrouter.ai/keys
- Check that the `.env` file is in the python-ai-engine directory

### "Service unavailable" errors
- The API automatically retries on transient failures
- If issues persist, check your API key limits and quotas

### Port already in use
- Change the `PORT` in `.env` to an available port
- Or kill the process using port 3100: `lsof -ti:3100 | xargs kill -9`

## Contributing

Contributions are welcome! Please follow the existing code style and include tests for new features.
