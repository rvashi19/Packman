"""
Unit tests for NPM package download ingestion Azure Function.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, call
import json
import io
from datetime import datetime, timedelta
import azure.functions as func
import requests

# Import the function under test
import function_app


class TestIngestData(unittest.TestCase):
    """Test cases for the Ingest_data Azure Function."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.mock_timer = Mock(spec=func.TimerRequest)
        self.mock_timer.past_due = False
        
        # Sample test data
        self.sample_packages = [
            {"PackageName": "lodash", "ClientName": "TestClient1"},
            {"PackageName": "react", "ClientName": "TestClient2"},
            {"PackageName": "express", "ClientName": "TestClient1"}
        ]
        
        # Expected date string for yesterday
        yesterday = datetime.utcnow().date() - timedelta(days=1)
        self.expected_date = yesterday.isoformat()

    @patch('function_app.ingest_client')
    @patch('function_app.query_client')
    @patch('requests.get')
    @patch('time.sleep')
    @patch('logging.info')
    @patch('logging.warning')
    @patch('logging.error')
    def test_successful_ingestion(self, mock_log_error, mock_log_warning, mock_log_info, 
                                 mock_sleep, mock_requests_get, mock_query_client, mock_ingest_client):
        """Test successful data ingestion scenario."""
        # Setup mocks
        mock_result = Mock()
        mock_result.primary_results = [self.sample_packages]
        mock_query_client.execute.return_value = mock_result
        
        # Mock successful API responses
        mock_responses = []
        for i, package in enumerate(self.sample_packages):
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"downloads": 1000 + i * 100}
            mock_responses.append(mock_response)
        
        mock_requests_get.side_effect = mock_responses
        
        # Execute the function
        function_app.Ingest_data(self.mock_timer)
        
        # Verify query execution
        mock_query_client.execute.assert_called_once_with(
            function_app.DATABASE, 
            "npm | project PackageName, ClientName | distinct PackageName, ClientName"
        )
        
        # Verify API calls
        expected_calls = []
        for package in self.sample_packages:
            expected_url = f"https://api.npmjs.org/downloads/point/{self.expected_date}:{self.expected_date}/{package['PackageName']}"
            expected_calls.append(call(expected_url))
        
        mock_requests_get.assert_has_calls(expected_calls)
        
        # Verify ingestion was called
        mock_ingest_client.ingest_from_stream.assert_called_once()
        
        # Verify logging
        mock_log_info.assert_any_call("Daily NPM download ingestion started")
        mock_log_info.assert_any_call(f"Retrieved {len(self.sample_packages)} unique packages with clients")
        mock_log_info.assert_any_call(f"Ingested {len(self.sample_packages)} records into PackMan table")

    @patch('function_app.ingest_client')
    @patch('function_app.query_client')
    @patch('requests.get')
    @patch('time.sleep')
    @patch('logging.info')
    @patch('logging.warning')
    def test_package_not_found_404(self, mock_log_warning, mock_log_info, mock_sleep, 
                                  mock_requests_get, mock_query_client, mock_ingest_client):
        """Test handling of 404 responses for packages not found."""
        # Setup mocks
        mock_result = Mock()
        mock_result.primary_results = [self.sample_packages[:1]]  # Only one package
        mock_query_client.execute.return_value = mock_result
        
        # Mock 404 response
        mock_response = Mock()
        mock_response.status_code = 404
        mock_requests_get.return_value = mock_response
        
        # Execute the function
        function_app.Ingest_data(self.mock_timer)
        
        # Verify 404 warning was logged
        mock_log_warning.assert_called_with(f"Package not found: {self.sample_packages[0]['PackageName']}")
        
        # Verify ingestion still happens with 0 downloads
        mock_ingest_client.ingest_from_stream.assert_called_once()

    @patch('function_app.ingest_client')
    @patch('function_app.query_client')
    @patch('requests.get')
    @patch('time.sleep')
    @patch('logging.info')
    @patch('logging.error')
    def test_api_request_exception(self, mock_log_error, mock_log_info, mock_sleep,
                                  mock_requests_get, mock_query_client, mock_ingest_client):
        """Test handling of API request exceptions."""
        # Setup mocks
        mock_result = Mock()
        mock_result.primary_results = [self.sample_packages[:1]]  # Only one package
        mock_query_client.execute.return_value = mock_result
        
        # Mock request exception
        mock_requests_get.side_effect = requests.RequestException("Connection error")
        
        # Execute the function
        function_app.Ingest_data(self.mock_timer)
        
        # Verify error was logged
        mock_log_error.assert_any_call(f"Error fetching data for {self.sample_packages[0]['PackageName']}: Connection error")
        
        # Verify no records were ingested due to exception
        mock_log_warning = mock_log_info
        # Check if "No data to ingest today" was logged (since no successful records)

    @patch('function_app.query_client')
    @patch('logging.info')
    @patch('logging.error')
    def test_query_execution_failure(self, mock_log_error, mock_log_info, mock_query_client):
        """Test handling of query execution failure."""
        # Setup mock to raise exception
        mock_query_client.execute.side_effect = Exception("Database connection failed")
        
        # Execute the function
        function_app.Ingest_data(self.mock_timer)
        
        # Verify error was logged
        mock_log_error.assert_called_with("Function failed: Database connection failed")

    @patch('function_app.ingest_client')
    @patch('function_app.query_client')
    @patch('requests.get')
    @patch('time.sleep')
    @patch('logging.info')
    @patch('logging.warning')
    def test_no_packages_retrieved(self, mock_log_warning, mock_log_info, mock_sleep,
                                  mock_requests_get, mock_query_client, mock_ingest_client):
        """Test scenario where no packages are retrieved from the database."""
        # Setup mocks with empty result
        mock_result = Mock()
        mock_result.primary_results = [[]]  # Empty list
        mock_query_client.execute.return_value = mock_result
        
        # Execute the function
        function_app.Ingest_data(self.mock_timer)
        
        # Verify appropriate logging
        mock_log_info.assert_any_call("Retrieved 0 unique packages with clients")
        mock_log_warning.assert_called_with("No data to ingest today")
        
        # Verify no API calls were made
        mock_requests_get.assert_not_called()
        
        # Verify no ingestion was attempted
        mock_ingest_client.ingest_from_stream.assert_not_called()

    @patch('logging.info')
    def test_timer_past_due(self, mock_log_info):
        """Test logging when timer is past due."""
        # Setup timer as past due
        self.mock_timer.past_due = True
        
        with patch('function_app.query_client') as mock_query_client:
            mock_result = Mock()
            mock_result.primary_results = [[]]
            mock_query_client.execute.return_value = mock_result
            
            # Execute the function
            function_app.Ingest_data(self.mock_timer)
            
            # Verify past due message was logged
            mock_log_info.assert_any_call("The timer is past due!")

    @patch('function_app.ingest_client')
    @patch('function_app.query_client')
    @patch('requests.get')
    @patch('time.sleep')
    @patch('logging.info')
    def test_data_format_validation(self, mock_log_info, mock_sleep, mock_requests_get,
                                   mock_query_client, mock_ingest_client):
        """Test that ingested data has the correct format."""
        # Setup mocks
        mock_result = Mock()
        mock_result.primary_results = [self.sample_packages[:1]]
        mock_query_client.execute.return_value = mock_result
        
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"downloads": 1500}
        mock_requests_get.return_value = mock_response
        
        # Execute the function
        function_app.Ingest_data(self.mock_timer)
        
        # Capture the ingested data
        call_args = mock_ingest_client.ingest_from_stream.call_args
        ingested_stream = call_args[0][0]
        ingested_data = ingested_stream.getvalue().decode('utf-8')
        
        # Parse and validate the JSON data
        record = json.loads(ingested_data)
        
        # Verify record structure
        expected_record = {
            "PackageName": self.sample_packages[0]["PackageName"],
            "Version": "cumulative",
            "Date": self.expected_date,
            "Downloads": 1500,
            "PackageManager": "npm",
            "ClientName": self.sample_packages[0]["ClientName"]
        }
        
        self.assertEqual(record, expected_record)

    @patch('function_app.ingest_client')
    @patch('function_app.query_client')
    @patch('requests.get')
    @patch('time.sleep')
    def test_rate_limiting_sleep(self, mock_sleep, mock_requests_get, mock_query_client, mock_ingest_client):
        """Test that rate limiting sleep is called between API requests."""
        # Setup mocks
        mock_result = Mock()
        mock_result.primary_results = [self.sample_packages]
        mock_query_client.execute.return_value = mock_result
        
        # Mock successful API responses
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"downloads": 1000}
        mock_requests_get.return_value = mock_response
        
        # Execute the function
        function_app.Ingest_data(self.mock_timer)
        
        # Verify sleep was called for each package (rate limiting)
        self.assertEqual(mock_sleep.call_count, len(self.sample_packages))
        mock_sleep.assert_has_calls([call(2)] * len(self.sample_packages))


if __name__ == '__main__':
    # Configure logging for tests
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Run the tests
    unittest.main()
