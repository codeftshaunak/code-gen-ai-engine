# Contributing to Builder AI Engine

First off, thank you for considering contributing to Builder AI Engine! 🎉

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [How to Contribute](#how-to-contribute)
- [Development Setup](#development-setup)
- [Coding Standards](#coding-standards)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)

---

## Code of Conduct

This project adheres to a Code of Conduct that all contributors are expected to follow. Please be respectful and constructive in all interactions.

---

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally
3. **Create a branch** for your changes
4. **Make your changes** and test thoroughly
5. **Submit a pull request**

---

## How to Contribute

### Reporting Bugs

- Use the GitHub Issues tracker
- Include detailed steps to reproduce
- Provide environment details (Python version, OS, etc.)
- Include error messages and logs

### Suggesting Features

- Use GitHub Issues with the "enhancement" label
- Describe the problem it solves
- Provide use cases and examples
- Consider implementation approach

### Improving Documentation

- Fix typos or clarify explanations
- Add examples and use cases
- Update outdated information
- Improve code comments

### Contributing Code

- Fix bugs
- Implement new features
- Optimize performance
- Add tests

---

## Development Setup

```bash
# Clone your fork
git clone https://github.com/yourusername/builder-ai-engine.git
cd builder-ai-engine

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Dev dependencies

# Setup pre-commit hooks
pre-commit install

# Copy environment file
cp .env.example .env
# Edit .env with your API keys

# Run tests
pytest

# Start development server
make dev
```

---

## Coding Standards

### Python Style

- Follow **PEP 8** style guide
- Use **type hints** for all functions
- Maximum line length: **120 characters**
- Use **black** for code formatting
- Use **isort** for import sorting

### Code Quality

```bash
# Format code
black app/ tests/
isort app/ tests/

# Lint
flake8 app/ tests/

# Type checking
mypy app/

# Security scan
bandit -r app/
```

### Naming Conventions

- **Classes**: `PascalCase` (e.g., `AIProviderManager`)
- **Functions**: `snake_case` (e.g., `generate_code_stream`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `MAX_TOKENS`)
- **Private methods**: `_leading_underscore` (e.g., `_parse_model`)

### Documentation

- All public functions must have docstrings
- Use Google-style docstrings
- Include parameter types and return types
- Provide examples for complex functions

Example:
```python
async def generate_code_stream(
    prompt: str,
    model: str,
    temperature: float = 0.7
) -> AsyncIterator[str]:
    """
    Generate code from AI model with streaming.

    Args:
        prompt: User's code generation request
        model: AI model identifier (e.g., "anthropic/claude-3-5-sonnet")
        temperature: Model temperature for randomness (0.0-1.0)

    Yields:
        Streaming chunks of generated code

    Raises:
        ValueError: If model is invalid
        HTTPException: If API call fails

    Example:
        >>> async for chunk in generate_code_stream("Create a button", "gpt-4"):
        ...     print(chunk)
    """
    ...
```

---

## Testing

### Writing Tests

- Write tests for all new features
- Maintain or improve code coverage
- Use `pytest` for testing
- Mock external API calls

### Test Structure

```python
import pytest
from app.core.ai_provider import AIProviderManager

@pytest.mark.asyncio
async def test_generate_code_stream():
    """Test code generation streaming"""
    provider = AIProviderManager()

    chunks = []
    async for chunk in provider.generate_code_stream("test prompt"):
        chunks.append(chunk)

    assert len(chunks) > 0
    assert isinstance(chunks[0], str)
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_ai_provider.py

# Run with verbose output
pytest -v

# Run only fast tests
pytest -m "not slow"
```

---

## Commit Guidelines

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **style**: Code style changes (formatting)
- **refactor**: Code refactoring
- **test**: Adding or updating tests
- **chore**: Maintenance tasks

### Examples

```
feat(api): add WebSocket support for streaming

Implement WebSocket endpoint for bidirectional streaming
communication. This improves performance for long-running
generation tasks.

Closes #123
```

```
fix(sandbox): handle timeout errors gracefully

Add proper error handling for sandbox timeout scenarios.
Previously, timeouts would crash the application.

Fixes #456
```

---

## Pull Request Process

### Before Submitting

1. **Test your changes** thoroughly
2. **Update documentation** if needed
3. **Add tests** for new features
4. **Run linters** and formatters
5. **Update CHANGELOG.md** if applicable

### PR Checklist

- [ ] Code follows project style guidelines
- [ ] All tests pass
- [ ] New tests added for new features
- [ ] Documentation updated
- [ ] Commit messages follow guidelines
- [ ] No merge conflicts
- [ ] Branch is up to date with main

### PR Description Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
How was this tested?

## Screenshots (if applicable)
Add screenshots here

## Checklist
- [ ] Tests pass
- [ ] Documentation updated
- [ ] Code formatted
```

### Review Process

1. Maintainers will review your PR
2. Address any feedback or requested changes
3. Once approved, your PR will be merged
4. Your contribution will be acknowledged in releases

---

## Development Workflow

```bash
# Create feature branch
git checkout -b feature/amazing-feature

# Make changes and commit
git add .
git commit -m "feat: add amazing feature"

# Push to your fork
git push origin feature/amazing-feature

# Create Pull Request on GitHub

# After review, squash and merge
```

---

## Project Structure

When adding new features, follow the existing structure:

```
app/
├── api/
│   ├── endpoints/     # Add new endpoints here
│   └── routes.py      # Register new routers here
├── core/              # Core business logic
├── models/            # Pydantic models
├── utils/             # Utility functions
└── config/            # Configuration
```

---

## Getting Help

- **GitHub Discussions**: Ask questions and discuss ideas
- **GitHub Issues**: Report bugs and request features
- **Documentation**: Check the full docs first
- **Code Comments**: Read inline documentation

---

## Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Mentioned in release notes
- Acknowledged in the README

---

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing! 🚀
