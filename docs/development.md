# Development Guide

This guide covers setting up and running the Ultravox-Twilio Integration Service in development mode.

## Prerequisites

- Python 3.11 or higher
- pip (Python package installer)
- Git

## Quick Start

1. **Clone the repository and navigate to the project directory**

2. **Set up Python virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -r dev-requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your actual API keys and configuration
   ```

5. **Start the development server**
   ```bash
   python scripts/dev.py
   ```

The server will start at `http://localhost:8000` with hot reload enabled.

## Development Environment Setup

### Environment Configuration

The development environment uses `.env.development` for configuration. Key settings:

- `DEBUG=true` - Enables debug mode
- `LOG_LEVEL=DEBUG` - Verbose logging
- `LOG_FORMAT=console` - Human-readable logs
- `LOG_REQUEST_BODY=true` - Log request bodies for debugging
- `CORS_ORIGINS=*` - Allow all origins (development only)

### Hot Reload

The development server automatically reloads when you make changes to:
- Python files in the `app/` directory
- Test files in the `tests/` directory

### API Documentation

When running in development mode, interactive API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Development Workflow

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_call_service.py

# Run integration tests
pytest tests/integration/
```

### Code Quality

```bash
# Format code
black app/ tests/

# Sort imports
isort app/ tests/

# Lint code
flake8 app/ tests/

# Type checking
mypy app/
```

### Environment Validation

Check if your development environment is properly configured:

```bash
python scripts/check-dev-env.py
```

This script validates:
- Python version
- Required dependencies
- Environment variables
- API connectivity

## Development Scripts

### `scripts/dev.py`
Starts the development server with hot reload and development-optimized settings.

### `scripts/check-dev-env.py`
Validates the development environment setup.

### `scripts/validate-config.py`
Validates configuration files and environment variables.

## Debugging

### Logging

Development mode provides detailed logging:
- Request/response bodies are logged
- Debug-level messages are shown
- Console-friendly formatting

### Health Check

Monitor service health at: `http://localhost:8000/api/v1/health`

### Common Issues

1. **Port already in use**
   ```bash
   # Find process using port 8000
   lsof -i :8000
   # Kill the process
   kill -9 <PID>
   ```

2. **Missing environment variables**
   - Check `.env` file exists and contains required values
   - Run `python scripts/validate-config.py` to identify missing variables

3. **Import errors**
   - Ensure virtual environment is activated
   - Verify all dependencies are installed: `pip install -r requirements.txt -r dev-requirements.txt`

## Testing External Integrations

### Twilio Webhooks

For local development, use ngrok to expose your local server:

```bash
# Install ngrok (if not already installed)
# Then expose local server
ngrok http 8000
```

Use the ngrok URL in your Twilio webhook configuration.

### API Testing

Use the interactive docs or curl commands:

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Create agent (requires valid API keys)
curl -X POST http://localhost:8000/api/v1/agents \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Agent", "system_prompt": "You are a helpful assistant"}'
```

## Development Best Practices

1. **Always run tests before committing**
2. **Use type hints for new code**
3. **Follow the existing code style**
4. **Add tests for new functionality**
5. **Update documentation for API changes**
6. **Use meaningful commit messages**

## IDE Configuration

### VS Code

Recommended extensions:
- Python
- Pylance
- Black Formatter
- isort

Settings (`.vscode/settings.json`):
```json
{
    "python.defaultInterpreterPath": "./.venv/bin/python",
    "python.formatting.provider": "black",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "editor.formatOnSave": true
}
```

### PyCharm

1. Set Python interpreter to `.venv/bin/python`
2. Enable Black as code formatter
3. Configure flake8 as linter
4. Set up run configuration for `app.main:app`