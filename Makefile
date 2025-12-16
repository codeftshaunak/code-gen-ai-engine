# Builder AI Engine - Makefile
# Convenient commands for development

.PHONY: help install run dev test clean docker-build docker-run format lint

help:
	@echo "Builder AI Engine - Available Commands"
	@echo "======================================"
	@echo "make install      - Install dependencies and setup environment"
	@echo "make run          - Run the server in production mode"
	@echo "make dev          - Run the server in development mode (auto-reload)"
	@echo "make test         - Run tests"
	@echo "make clean        - Clean up cache and temporary files"
	@echo "make docker-build - Build Docker image"
	@echo "make docker-run   - Run with Docker Compose"
	@echo "make format       - Format code with black"
	@echo "make lint         - Lint code with flake8"

install:
	@echo "Installing dependencies..."
	python3 -m venv venv
	. venv/bin/activate && pip install --upgrade pip
	. venv/bin/activate && pip install -r requirements.txt
	@if [ ! -f .env ]; then cp .env.example .env; fi
	@echo "✅ Installation complete! Edit .env file with your API keys."

run:
	@echo "Starting server in production mode..."
	python main.py

dev:
	@echo "Starting server in development mode..."
	uvicorn main:app --reload --port 3100

test:
	@echo "Running tests..."
	pytest -v

clean:
	@echo "Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cleanup complete!"

docker-build:
	@echo "Building Docker image..."
	docker build -t builder-ai-engine:latest .

docker-run:
	@echo "Starting with Docker Compose..."
	docker-compose up -d

docker-stop:
	@echo "Stopping Docker containers..."
	docker-compose down

docker-logs:
	@echo "Showing Docker logs..."
	docker-compose logs -f

format:
	@echo "Formatting code..."
	black app/ main.py

lint:
	@echo "Linting code..."
	flake8 app/ main.py --max-line-length=120
