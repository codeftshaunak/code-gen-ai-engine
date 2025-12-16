# Quick Start Guide

Get the Builder AI Engine running in under 5 minutes! 🚀

## Option 1: Automated Setup (Recommended)

```bash
# Run the setup script
./setup.sh

# Edit .env with your API keys
nano .env

# Run the server
source venv/bin/activate
python main.py
```

## Option 2: Manual Setup

```bash
# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Setup environment
cp .env.example .env
# Edit .env with your API keys

# 4. Run the server
python main.py
```

## Option 3: Using Make

```bash
# Install everything
make install

# Edit .env with your API keys
nano .env

# Run in development mode
make dev
```

## Option 4: Docker

```bash
# Copy and edit environment file
cp .env.example .env
# Edit .env with your API keys

# Build and run with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f
```

## Required API Keys

At minimum, you need:

1. **Sandbox Provider** (choose one):
   - E2B: `E2B_API_KEY` - Get from https://e2b.dev
   - Vercel: `VERCEL_TOKEN` - Get from Vercel dashboard

2. **AI Provider** (choose one or more):
   - Anthropic: `ANTHROPIC_API_KEY` - Get from https://console.anthropic.com
   - OpenAI: `OPENAI_API_KEY` - Get from https://platform.openai.com
   - Google: `GEMINI_API_KEY` - Get from https://makersuite.google.com
   - Groq: `GROQ_API_KEY` - Get from https://console.groq.com

## Test the API

Once running, test with:

```bash
# Health check
curl http://localhost:3100/health

# View Swagger docs
open http://localhost:3100/api/docs
```

## First API Call

```bash
# Set your project ID
PROJECT_ID="test-project-123"

# Generate code
curl -X POST http://localhost:3100/api/generate-ai-code-stream \
  -H "Content-Type: application/json" \
  -H "X-Project-Id: $PROJECT_ID" \
  -d '{
    "prompt": "Create a simple React counter component",
    "model": "anthropic/claude-3-5-sonnet-20241022"
  }'
```

## Common Issues

### "No module named 'fastapi'"
**Solution**: Activate virtual environment: `source venv/bin/activate`

### "Missing API key"
**Solution**: Edit `.env` file and add required API keys

### "Port 3100 already in use"
**Solution**: Change `PORT` in `.env` or kill the process using port 3100

## Next Steps

1. ✅ Read the [README.md](README.md) for full documentation
2. ✅ Explore the [Swagger UI](http://localhost:3100/api/docs)
3. ✅ Try the 5 core APIs
4. ✅ Integrate with your frontend

Happy coding! 🎉
