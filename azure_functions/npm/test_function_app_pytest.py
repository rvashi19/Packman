"""
Pytest-based unit tests for NPM package download ingestion Azure Function.
"""

import pytest
from unittest.mock import Mock, patch, call
import json
import io
from datetime import datetime, timedelta
import azure.functions as func
import requests

# Import the function under test
import function_app


class TestIngestData:
    """Test cases for the Ingest_data Azure Function using pytest."""

    @pytest.fixture
    def mock_timer(self):
        """Create a mock timer request."""
        timer = Mock(spec=func.TimerRequest)
        timer.past_due = False
        return timer

    @pytest.fixture
    def sample_packages(self):
        """Sample test data for packages."""
        return [
            {"PackageName": "lodash", "ClientName": "TestClient1"},
            {"PackageName": "react", "ClientName": "TestClient2"},
            {"PackageName": "express", "ClientName": "TestClient1"}
        ]

    @pytest.fixture
    def expected_date(self):
        """Expected date string for yesterday."""
        yesterday = datetime.utcnow().date() - timedelta(days=1)
        return yesterday.isoformat()

    @patch('function_app.ingest_client')
    @patch('function_app.query_client')
    @patch('requests.get')
    @patch('time.sleep')
    @patch('logging.info')
    @patch('logging.warning')
    @patch('logging.error')
    def test_successful_ingestion(self, mock_log_error, mock_log_warning, mock_log_info, 
                                 mock_sleep, mock_requests_get, mock_query_client, 
                                 mock_ingest_client, mock_timer, sample_packages, expected_date):
        """Test successful data ingestion scenario."""
        # Setup mocks
        mock_result = Mock()
        mock_result.primary_results = [sample_packages]
        mock_query_client.execute.return_value = mock_result
        
        # Mock successful API responses
        mock_responses = []
        for i, package in enumerate(sample_packages):
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"downloads": 1000 + i * 100}
            mock_responses.append(mock_response)
        
        mock_requests_get.side_effect = mock_responses
        
        # Execute the function
        function_app.Ingest_data(mock_timer)
        
        # Verify query execution
        mock_query_client.execute.assert_called_once_with(
            function_app.DATABASE, 
            "npm | project PackageName, ClientName | distinct PackageName, ClientName"
        )
        
        # Verify API calls
        expected_calls = []
        for package in sample_packages:
            expected_url = f"https://api.npmjs.org/downloads/point/{expected_date}:{expected_date}/{package['PackageName']}"
            expected_calls.append(call(expected_url))
        
        mock_requests_get.assert_has_calls(expected_calls)
        
        # Verify ingestion was called
        mock_ingest_client.ingest_from_stream.assert_called_once()
        
        # Verify logging
        mock_log_info.assert_any_call("Daily NPM download ingestion started")
        mock_log_info.assert_any_call(f"Retrieved {len(sample_packages)} unique packages with clients")
        mock_log_info.assert_any_call(f"Ingested {len(sample_packages)} records into PackMan table")

    @patch('function_app.ingest_client')
    @patch('function_app.query_client')
    @patch('requests.get')
    @patch('time.sleep')
    @patch('logging.info')
    @patch('logging.warning')
    def test_package_not_found_404(self, mock_log_warning, mock_log_info, mock_sleep, 
                                  mock_requests_get, mock_query_client, mock_ingest_client,
                                  mock_timer, sample_packages):
        """Test handling of 404 responses for packages not found."""
        # Setup mocks
        mock_result = Mock()
        mock_result.primary_results = [sample_packages[:1]]  # Only one package
        mock_query_client.execute.return_value = mock_result
        
        # Mock 404 response
        mock_response = Mock()
        mock_response.status_code = 404
        mock_requests_get.return_value = mock_response
        
        # Execute the function
        function_app.Ingest_data(mock_timer)
        
        # Verify 404 warning was logged
        mock_log_warning.assert_called_with(f"Package not found: {sample_packages[0]['PackageName']}")
        
        # Verify ingestion still happens with 0 downloads
        mock_ingest_client.ingest_from_stream.assert_called_once()

    @patch('function_app.ingest_client')
    @patch('function_app.query_client')
    @patch('requests.get')
    @patch('time.sleep')
    @patch('logging.info')
    @patch('logging.error')
    def test_api_request_exception(self, mock_log_error, mock_log_info, mock_sleep,
                                  mock_requests_get, mock_query_client, mock_ingest_client,
                                  mock_timer, sample_packages):
        """Test handling of API request exceptions."""
        # Setup mocks
        mock_result = Mock()
        mock_result.primary_results = [sample_packages[:1]]  # Only one package
        mock_query_client.execute.return_value = mock_result
        
        # Mock request exception
        mock_requests_get.side_effect = requests.RequestException("Connection error")
        
        # Execute the function
        function_app.Ingest_data(mock_timer)
        
        # Verify error was logged
        mock_log_error.assert_any_call(f"Error fetching data for {sample_packages[0]['PackageName']}: Connection error")

    @patch('function_app.query_client')
    @patch('logging.info')
    @patch('logging.error')
    def test_query_execution_failure(self, mock_log_error, mock_log_info, mock_query_client, mock_timer):
        """Test handling of query execution failure."""
        # Setup mock to raise exception
        mock_query_client.execute.side_effect = Exception("Database connection failed")
        
        # Execute the function
        function_app.Ingest_data(mock_timer)
        
        # Verify error was logged
        mock_log_error.assert_called_with("Function failed: Database connection failed")

    @patch('function_app.ingest_client')
    @patch('function_app.query_client')
    @patch('requests.get')
    @patch('time.sleep')
    @patch('logging.info')
    @patch('logging.warning')
    def test_no_packages_retrieved(self, mock_log_warning, mock_log_info, mock_sleep,
                                  mock_requests_get, mock_query_client, mock_ingest_client, mock_timer):
        """Test scenario where no packages are retrieved from the database."""
        # Setup mocks with empty result
        mock_result = Mock()
        mock_result.primary_results = [[]]  # Empty list
        mock_query_client.execute.return_value = mock_result
        
        # Execute the function
        function_app.Ingest_data(mock_timer)
        
        # Verify appropriate logging
        mock_log_info.assert_any_call("Retrieved 0 unique packages with clients")
        mock_log_warning.assert_called_with("No data to ingest today")
        
        # Verify no API calls were made
        mock_requests_get.assert_not_called()
        
        # Verify no ingestion was attempted
        mock_ingest_client.ingest_from_stream.assert_not_called()

    @patch('logging.info')
    def test_timer_past_due(self, mock_log_info, sample_packages):
        """Test logging when timer is past due."""
        # Setup timer as past due
        mock_timer = Mock(spec=func.TimerRequest)
        mock_timer.past_due = True
        
        with patch('function_app.query_client') as mock_query_client:
            mock_result = Mock()
            mock_result.primary_results = [[]]
            mock_query_client.execute.return_value = mock_result
            
            # Execute the function
            function_app.Ingest_data(mock_timer)
            
            # Verify past due message was logged
            mock_log_info.assert_any_call("The timer is past due!")

    @patch('function_app.ingest_client')
    @patch('function_app.query_client')
    @patch('requests.get')
    @patch('time.sleep')
    @patch('logging.info')
    def test_data_format_validation(self, mock_log_info, mock_sleep, mock_requests_get,
                                   mock_query_client, mock_ingest_client, mock_timer, 
                                   sample_packages, expected_date):
        """Test that ingested data has the correct format."""
        # Setup mocks
        mock_result = Mock()
        mock_result.primary_results = [sample_packages[:1]]
        mock_query_client.execute.return_value = mock_result
        
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"downloads": 1500}
        mock_requests_get.return_value = mock_response
        
        # Execute the function
        function_app.Ingest_data(mock_timer)
        
        # Capture the ingested data
        call_args = mock_ingest_client.ingest_from_stream.call_args
        ingested_stream = call_args[0][0]
        ingested_data = ingested_stream.getvalue().decode('utf-8')
        
        # Parse and validate the JSON data
        record = json.loads(ingested_data)
        
        # Verify record structure
        expected_record = {
            "PackageName": sample_packages[0]["PackageName"],
            "Version": "cumulative",
            "Date": expected_date,
            "Downloads": 1500,
            "PackageManager": "npm",
            "ClientName": sample_packages[0]["ClientName"]
        }
        
        assert record == expected_record

    @patch('function_app.ingest_client')
    @patch('function_app.query_client')
    @patch('requests.get')
    @patch('time.sleep')
    def test_rate_limiting_sleep(self, mock_sleep, mock_requests_get, mock_query_client, 
                               mock_ingest_client, mock_timer, sample_packages):
        """Test that rate limiting sleep is called between API requests."""
        # Setup mocks
        mock_result = Mock()
        mock_result.primary_results = [sample_packages]
        mock_query_client.execute.return_value = mock_result
        
        # Mock successful API responses
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"downloads": 1000}
        mock_requests_get.return_value = mock_response
        
        # Execute the function
        function_app.Ingest_data(mock_timer)
        
        # Verify sleep was called for each package (rate limiting)
        assert mock_sleep.call_count == len(sample_packages)
        mock_sleep.assert_has_calls([call(2)] * len(sample_packages))

    @pytest.mark.parametrize("status_code,downloads,expected_downloads", [
        (200, 1500, 1500),
        (200, 0, 0),
        (404, None, 0),
    ])
    @patch('function_app.ingest_client')
    @patch('function_app.query_client')
    @patch('requests.get')
    @patch('time.sleep')
    def test_various_api_responses(self, mock_sleep, mock_requests_get, mock_query_client,
                                  mock_ingest_client, mock_timer, sample_packages,
                                  status_code, downloads, expected_downloads):
        """Test handling of various API response scenarios."""
        # Setup mocks
        mock_result = Mock()
        mock_result.primary_results = [sample_packages[:1]]
        mock_query_client.execute.return_value = mock_result
        
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = status_code
        if status_code == 200:
            mock_response.json.return_value = {"downloads": downloads}
        mock_requests_get.return_value = mock_response
        
        # Execute the function
        function_app.Ingest_data(mock_timer)
        
        # Verify ingestion was called
        if status_code != 500:  # Assuming 500 would cause an exception
            mock_ingest_client.ingest_from_stream.assert_called_once()
            
            # Verify the data content
            call_args = mock_ingest_client.ingest_from_stream.call_args
            ingested_stream = call_args[0][0]
            ingested_data = ingested_stream.getvalue().decode('utf-8')
            record = json.loads(ingested_data)
            
            assert record["Downloads"] == expected_downloads
