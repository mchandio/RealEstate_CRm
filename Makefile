# Real Estate CRM Development Makefile
# =====================================

# Detect Python and pip - use venv if available, otherwise system
PYTHON := $(shell if [ -d .venv ]; then echo .venv/bin/python; else echo python3; endif)
PIP := $(shell if [ -d .venv ]; then echo .venv/bin/pip; else echo pip3; endif)

.PHONY: help setup test lint format clean install-dev

help:  ## Show this help message
	@echo "Real Estate CRM Development Commands"
	@echo "===================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup:  ## Set up development environment
	@echo "Setting up development environment..."
	python3 -m venv .venv
	@echo "Virtual environment created. Activate with:"
	@echo "  source .venv/bin/activate"
	@echo "Then run: make install-dev"

install-dev:  ## Install development dependencies
	@echo "Installing development dependencies..."
	@if [ ! -d ".venv" ]; then echo "Virtual environment not found. Run 'make setup' first."; exit 1; fi
	$(PIP) install -r requirements.txt
	$(PIP) install -r requirements-dev.txt
	@echo "Development dependencies installed!"

test:  ## Run tests with pytest
	@echo "Running tests..."
	$(PYTHON) -m pytest tests/ -v --tb=short

test-coverage:  ## Run tests with coverage report
	@echo "Running tests with coverage..."
	$(PYTHON) -m pytest tests/ -v --cov=backend --cov=crm_core --cov=CRM --cov-report=html

lint:  ## Run linting checks
	@echo "Running flake8..."
	@command -v flake8 >/dev/null 2>&1 || $(PIP) install -q flake8
	@flake8 backend/ crm_core/ CRM/ --max-line-length=100 --ignore=E501,W503
	@echo "Running black check..."
	@command -v black >/dev/null 2>&1 || $(PIP) install -q black
	@black --check backend/ crm_core/ CRM/
	@echo "Running isort check..."
	@command -v isort >/dev/null 2>&1 || $(PIP) install -q isort
	@isort --check-only backend/ crm_core/ CRM/

format:  ## Auto-format code
	@echo "Running black..."
	@command -v black >/dev/null 2>&1 || $(PIP) install -q black
	@black backend/ crm_core/ CRM/
	@echo "Running isort..."
	@command -v isort >/dev/null 2>&1 || $(PIP) install -q isort
	@isort backend/ crm_core/ CRM/

typecheck:  ## Run type checking
	@echo "Running mypy..."
	@command -v mypy >/dev/null 2>&1 || $(PIP) install -q mypy
	@mypy backend/ --ignore-missing-imports

clean:  ## Clean up generated files
	@echo "Cleaning up..."
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache htmlcov .mypy_cache

check-syntax:  ## Check syntax of all Python files
	@echo "Checking syntax..."
	@python3 -m py_compile backend/main.py && echo "✓ backend/main.py"
	@python3 -m py_compile backend/auth.py && echo "✓ backend/auth.py"
	@python3 -m py_compile crm_core/reports.py && echo "✓ crm_core/reports.py"
	@python3 -m py_compile crm_core/intelligence.py && echo "✓ crm_core/intelligence.py"
	@python3 -m py_compile CRM/app_window.py && echo "✓ CRM/app_window.py"
	@echo "All syntax checks passed!"

validate: check-syntax test  ## Run all validation checks
	@echo "All validation checks completed!"
