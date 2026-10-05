import pytest
from unittest.mock import patch, MagicMock
from types import SimpleNamespace
from azure_functions.npm.function_app import Ingest_data

@pytest.fixture
def timer_request():
    return SimpleNamespace(past_due=False)

def test_successful_ingestion(timer_request):
    mock_kusto_result = MagicMock()
    mock_primary_result = MagicMock()
    mock_primary_result.__iter__.return_value = iter([
        {"PackageName": "express", "ClientName": "ClientX"},
    ])
    mock_kusto_result.primary_results = [mock_primary_result]

    def mock_requests_get(url, *args, **kwargs):
        class MockResponse:
            def __init__(self):
                self.status_code = 200
            def json(self):
                return {"downloads": 123}
            def raise_for_status(self): pass
        return MockResponse()

    with patch("azure_functions.npm.function_app.query_client", create=True) as mock_qc, \
         patch("azure_functions.npm.function_app.requests.get", side_effect=mock_requests_get), \
         patch("azure_functions.npm.function_app.ingest_client", create=True) as mock_ic:

        mock_qc.execute.return_value = mock_kusto_result
        mock_ic.ingest_from_stream = MagicMock()

        Ingest_data(timer_request)
        mock_ic.ingest_from_stream.assert_called_once()


def test_ingests_zero_when_api_returns_no_data(timer_request):
    # ADX returns 1 package-client pair
    mock_kusto_result = MagicMock()
    mock_primary_result = MagicMock()
    mock_primary_result.__iter__.return_value = iter([
        {"PackageName": "express", "ClientName": "ClientX"},
    ])
    mock_kusto_result.primary_results = [mock_primary_result]

    # API returns no 'downloads' key
    def mock_requests_get(url, *args, **kwargs):
        class MockResponse:
            status_code = 200
            def json(self): return {}  # missing 'downloads'
            def raise_for_status(self): pass
        return MockResponse()

    with patch("azure_functions.npm.function_app.query_client", create=True) as mock_qc, \
         patch("azure_functions.npm.function_app.requests.get", side_effect=mock_requests_get), \
         patch("azure_functions.npm.function_app.ingest_client", create=True) as mock_ic:

        mock_qc.execute.return_value = mock_kusto_result
        mock_ingest = MagicMock()
        mock_ic.ingest_from_stream = mock_ingest

        Ingest_data(timer_request)

        # ✅ Ingest still happens (with 0 downloads)
        mock_ingest.assert_called_once()
