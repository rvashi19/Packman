# Unit Tests for NPM Package Download Ingestion Azure Function

This directory contains comprehensive unit tests for the `Ingest_data` Azure Function that ingests NPM package download statistics.

## Test Files

- `test_function_app.py` - Standard unittest-based tests
- `test_function_app_pytest.py` - Pytest-based tests with fixtures and parametrized tests
- `pytest.ini` - Pytest configuration
- `run_tests.ps1` - PowerShell script to run tests (Windows)
- `run_tests.sh` - Bash script to run tests (Linux/macOS)

## Test Coverage

The tests cover the following scenarios:

### Happy Path
- ✅ Successful data ingestion with multiple packages
- ✅ Correct data format validation
- ✅ Proper API calls to NPM registry
- ✅ Rate limiting implementation (sleep between requests)

### Error Handling
- ✅ Package not found (404 responses)
- ✅ API request exceptions
- ✅ Database query failures
- ✅ No packages retrieved from database

### Edge Cases
- ✅ Timer past due logging
- ✅ Empty package list handling
- ✅ Various API response codes and data formats

## Running Tests

### Option 1: Using PowerShell (Windows)
```powershell
.\run_tests.ps1
```

### Option 2: Using Bash (Linux/macOS)
```bash
chmod +x run_tests.sh
./run_tests.sh
```

### Option 3: Manual execution

Install dependencies:
```bash
pip install pytest pytest-mock coverage
```

Run pytest version:
```bash
python -m pytest test_function_app_pytest.py -v --cov=function_app --cov-report=html --cov-report=term-missing
```

Run unittest version:
```bash
python -m unittest test_function_app.py -v
```

## Test Requirements

The tests require the following additional packages (added to `requirements.txt`):
- `pytest==8.0.2` - Testing framework
- `pytest-mock==3.12.0` - Mocking utilities for pytest
- `coverage==7.4.4` - Code coverage analysis

## Mocked Dependencies

The tests mock the following external dependencies:
- Azure Data Explorer (Kusto) client connections
- NPM API HTTP requests
- Azure Function timer requests
- Logging functionality
- Time sleep operations

## Coverage Report

After running tests, a coverage report will be generated in `htmlcov/index.html` showing:
- Line coverage percentage
- Missing lines
- Detailed coverage analysis

## Key Test Patterns

### Mocking External Services
```python
@patch('function_app.query_client')
@patch('requests.get')
def test_example(mock_requests, mock_query_client):
    # Test implementation
```

### Fixture Usage (pytest)
```python
@pytest.fixture
def sample_packages():
    return [{"PackageName": "lodash", "ClientName": "TestClient1"}]
```

### Parametrized Tests
```python
@pytest.mark.parametrize("status_code,downloads,expected", [
    (200, 1500, 1500),
    (404, None, 0),
])
def test_api_responses(status_code, downloads, expected):
    # Test implementation
```

## Best Practices Implemented

1. **Comprehensive Mocking** - All external dependencies are mocked
2. **Error Scenarios** - Tests cover both success and failure paths
3. **Data Validation** - Verifies correct data format and content
4. **Logging Verification** - Ensures proper logging behavior
5. **Coverage Analysis** - Aims for high test coverage
6. **Multiple Test Frameworks** - Provides both unittest and pytest versions
