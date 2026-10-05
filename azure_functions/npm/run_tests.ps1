# Test runner script for NPM Azure Function (PowerShell)

Write-Host "Setting up test environment..." -ForegroundColor Green

# Install test dependencies
Write-Host "Installing test dependencies..." -ForegroundColor Yellow
pip install pytest pytest-mock coverage

Write-Host "Running unit tests..." -ForegroundColor Green

# Run tests with coverage
Write-Host "Running pytest version..." -ForegroundColor Cyan
python -m pytest test_function_app_pytest.py -v --cov=function_app --cov-report=html --cov-report=term-missing

Write-Host "Running unittest version..." -ForegroundColor Cyan
python -m unittest test_function_app.py -v

Write-Host "Test execution completed!" -ForegroundColor Green
Write-Host "Coverage report available in htmlcov/index.html" -ForegroundColor Yellow
