"""Unit tests for REDCap Report Processing lambda reporting processor."""

import csv
import io
from typing import Any, Dict, List
from unittest.mock import patch

from redcap_report_processor_lambda.reporting_processor import process_data
from testing.moto_fixtures import moto_server, s3_client, setup_s3_environment


class MockREDCapProject:
    """Mock REDCap project for testing."""

    def __init__(
        self,
        records: List[Dict[str, Any]],
        pid: int = 0,
        title: str = "Dummy REDCap Report",
    ) -> None:
        self.__records = records
        self.__pid = pid
        self.__title = title

    @property
    def pid(self) -> int:
        return self.__pid

    @property
    def title(self) -> str:
        return self.__title

    def export_records(self, exp_format: str = "csv") -> str:
        """Turn records into CSV string."""
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=self.__records[0].keys())
        writer.writeheader()
        writer.writerows(self.__records)

        return output.getvalue()


class TestReportingProccessor:
    """Test cases for main data processing logic."""

    def test_process_redcap_report(
        self, valid_input, s3_client, setup_s3_environment
    ) -> None:
        """Test processing of scheduled events."""
        s3_client.create_bucket(Bucket=valid_input.output_prefix)

        records = [
            {"ptid": "1234", "dummy": "dummy"},
            {"ptid": "4567", "dummy": "dummy2"},
        ]
        redcap_project = MockREDCapProject(records=records)

        with patch(
            "redcap_report_processor_lambda.reporting_processor.get_redcap_project"
        ) as mock_process:
            mock_process.return_value = redcap_project
            response = process_data(valid_input)

            assert response.num_records == 2
            assert response.output_location.startswith(
                "s3://dummy-bucket/sandbox/testing/0/"
            )
            assert response.output_location.endswith("/0.parquet")
