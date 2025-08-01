# Makefile for Ultravox-Twilio Integration Service

.PHONY: help install dev test lint format clean build deploy check-env

# Default target
help:
	@echo "Available commands:"
	@echo "  install     - Install dependencies"
	@echo "  dev         - Start development server"
	@echo "  test        - Run tests"
	@echo "  test-cov    - Run tests with coverage"
	@echo "  lint        - Run linting checks"
	@echo "  format      - Format code"
	@echo "  check-env   - Validate development environment"
	@echo "  clean       - Clean up temporary files"
	@echo "  build       - Build Docker image"
	@echo "  deploy-dev  - Deploy in development mode"
	@echo "  deploy-prod - Deploy in production mode"

# Install dependencies
install:
	pip install -r requirements.txt
	pip install -r dev-requirements.txt

# Start development server
dev:
	python scripts/dev.py

# Run tests
test:
	pytest

# Run tests with coverage
test-cov:
	pytest --cov=app --cov-report=html --cov-report=term

# Run integration tests
test-integration:
	pytest tests/integration/

# Run linting
lint:
	flake8 app/ tests/
	mypy app/

# Format code
format:
	black app/ tests/
	isort app/ tests/

# Check development environment
check-env:
	python scripts/check-dev-env.py

# Validate configuration
validate-config:
	python scripts/validate-config.py

# Clean up temporary files
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf dist/
	rm -rf build/

# Build Docker image
build:
	docker-compose build

# Deploy in development mode
deploy-dev:
	./scripts/deploy.sh development

# Deploy in production mode
deploy-prod:
	./scripts/deploy.sh production

# Stop Docker services
stop:
	docker-compose down

# View logs
logs:
	docker-compose logs -f ultravox-twilio-service

# Setup development environment from scratch
setup: install check-env
	@echo "Development environment setup complete!"
	@echo "Run 'make dev' to start the development server"

# Run all quality checks
quality: format lint test
	@echo "All quality checks passed!"