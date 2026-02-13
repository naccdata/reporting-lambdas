"""Unit tests for REDCap Report Processing lambda reporting processor."""

import csv
import io
from typing import Any, Dict, List
from unittest.mock import patch

from redcap_report_processor_lambda.reporting_processor import process_data


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

    def export_report(self, report_id: str, exp_format: str = "csv") -> str:
        """Turn records into CSV string."""
        return self.export_records(exp_format)


class TestReportingProcessor:
    """Test cases for main data processing logic."""

    def test_process_redcap_report(
        self, valid_input, s3_client, setup_s3_environment
    ) -> None:
        """Test processing of scheduled events."""
        s3_client.create_bucket(Bucket=valid_input.s3_bucket)

        records = "id,dummy\n1234,value\n4567,value2"

        with patch(
            "redcap_report_processor_lambda.reporting_processor.get_redcap_records"
        ) as mock_process:
            mock_process.return_value = records
            response = process_data(valid_input)

            assert response.num_records == 2
            assert response.output_location.startswith(  # type: ignore
                "s3://dummy-bucket/redcap/sandbox/testing/file.parquet"
            )
