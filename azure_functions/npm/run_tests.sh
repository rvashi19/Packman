#!/bin/bash

# Test runner script for NPM Azure Function

echo "Setting up test environment..."

# Install test dependencies
echo "Installing test dependencies..."
pip install pytest pytest-mock coverage

echo "Running unit tests..."

# Run tests with coverage
python -m pytest test_function_app_pytest.py -v --cov=function_app --cov-report=html --cov-report=term-missing

echo "Running unittest version..."
python -m unittest test_function_app.py -v

echo "Test execution completed!"
echo "Coverage report available in htmlcov/index.html"
