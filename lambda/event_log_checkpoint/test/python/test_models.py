"""Unit tests for VisitEvent model.

This module contains unit tests and property-based tests for the
VisitEvent Pydantic model, testing validation, type conversion, null
preservation, and serialization.
"""

import json
from datetime import datetime

import pytest
from checkpoint_lambda.models import VisitEvent
from hypothesis import given
from hypothesis import strategies as st
from hypothesis.strategies import composite
from pydantic import ValidationError


class TestVisitEventValidation:
    """Unit tests for VisitEvent validation."""

    def test_valid_event_passes_validation(self):
        """Test that a valid event passes all validation checks."""
        valid_event_data = {
            "action": "submit",
            "study": "adrc",
            "pipeline_adcid": 123,
            "project_label": "test_project",
            "center_label": "test_center",
            "gear_name": "test_gear",
            "ptid": "ABC123",
            "visit_date": "2024-01-15",
            "visit_number": "01",
            "datatype": "form",
            "module": "UDS",
            "packet": "I",
            "timestamp": "2024-01-15T10:00:00Z",
        }

        event = VisitEvent(**valid_event_data)

        assert event.action == "submit"
        assert event.study == "adrc"
        assert event.pipeline_adcid == 123
        assert event.project_label == "test_project"
        assert event.center_label == "test_center"
        assert event.gear_name == "test_gear"
        assert event.ptid == "ABC123"
        assert event.visit_date == "2024-01-15"  # Now a string
        assert event.visit_number == "01"
        assert event.datatype == "form"
        assert event.module == "UDS"
        assert event.packet == "I"
        assert isinstance(event.timestamp, datetime)

    def test_valid_event_without_optional_fields(self):
        """Test that a valid event passes validation without optional
        fields."""
        valid_event_data = {
            "action": "submit",
            "study": "adrc",
            "pipeline_adcid": 123,
            "project_label": "test_project",
            "center_label": "test_center",
            "gear_name": "test_gear",
            "ptid": "ABC123",
            "visit_date": "2024-01-15",
            "datatype": "dicom",  # Non-form datatype
            "timestamp": "2024-01-15T10:00:00Z",
        }

        event = VisitEvent(**valid_event_data)

        assert event.visit_number is None
        assert event.module is None
        assert event.packet is None

    def test_invalid_action_fails_validation(self):
        """Test that invalid action values fail validation."""
        invalid_event_data = {
            "action": "invalid_action",
            "study": "adrc",
            "pipeline_adcid": 123,
            "project_label": "test_project",
            "center_label": "test_center",
            "gear_name": "test_gear",
            "ptid": "ABC123",
            "visit_date": "2024-01-15",
            "datatype": "form",
            "module": "UDS",
            "timestamp": "2024-01-15T10:00:00Z",
        }

        with pytest.raises(ValidationError) as exc_info:
            VisitEvent(**invalid_event_data)

        assert "action" in str(exc_info.value)

    def test_invalid_ptid_pattern_fails_validation(self):
        """Test that ptid values not matching pattern fail validation."""
        invalid_ptids = [
            "ABC 123",  # contains space (not printable non-whitespace)
            "ABC\t123",  # contains tab
            "ABC123TOOLONG",  # too long (>10 chars)
            "",  # empty
        ]

        base_data = {
            "action": "submit",
            "study": "adrc",
            "pipeline_adcid": 123,
            "project_label": "test_project",
            "center_label": "test_center",
            "gear_name": "test_gear",
            "visit_date": "2024-01-15",
            "datatype": "dicom",
            "timestamp": "2024-01-15T10:00:00Z",
        }

        for invalid_ptid in invalid_ptids:
            with pytest.raises(ValidationError) as exc_info:
                VisitEvent(**{**base_data, "ptid": invalid_ptid})
            assert "ptid" in str(exc_info.value)

    def test_valid_ptid_patterns_pass_validation(self):
        """Test that valid ptid values pass validation."""
        valid_ptids = [
            "ABC123",  # alphanumeric
            "A1B2C3",  # mixed
            "!@#$%",  # special characters (printable non-whitespace)
            "a",  # single character
            "1234567890",  # exactly 10 characters
        ]

        base_data = {
            "action": "submit",
            "study": "adrc",
            "pipeline_adcid": 123,
            "project_label": "test_project",
            "center_label": "test_center",
            "gear_name": "test_gear",
            "visit_date": "2024-01-15",
            "datatype": "dicom",
            "timestamp": "2024-01-15T10:00:00Z",
        }

        for valid_ptid in valid_ptids:
            event = VisitEvent(**{**base_data, "ptid": valid_ptid})
            assert event.ptid == valid_ptid

    def test_missing_required_fields_fail_validation(self):
        """Test that missing required fields fail validation."""
        required_fields = [
            "action",
            "pipeline_adcid",
            "project_label",
            "center_label",
            "gear_name",
            "ptid",
            "visit_date",
            "datatype",
            "timestamp",
        ]

        complete_data = {
            "action": "submit",
            "study": "adrc",
            "pipeline_adcid": 123,
            "project_label": "test_project",
            "center_label": "test_center",
            "gear_name": "test_gear",
            "ptid": "ABC123",
            "visit_date": "2024-01-15",
            "datatype": "dicom",
            "timestamp": "2024-01-15T10:00:00Z",
        }

        for field in required_fields:
            incomplete_data = complete_data.copy()
            del incomplete_data[field]

            with pytest.raises(ValidationError) as exc_info:
                VisitEvent(**incomplete_data)
            assert field in str(exc_info.value)

    def test_invalid_datatype_fails_validation(self):
        """Test that invalid datatype values fail validation."""
        base_data = {
            "action": "submit",
            "study": "adrc",
            "pipeline_adcid": 123,
            "project_label": "test_project",
            "center_label": "test_center",
            "gear_name": "test_gear",
            "ptid": "ABC123",
            "visit_date": "2024-01-15",
            "datatype": "invalid_datatype",  # Not in DatatypeNameType
            "timestamp": "2024-01-15T10:00:00Z",
        }

        with pytest.raises(ValidationError) as exc_info:
            VisitEvent(**base_data)
        assert "datatype" in str(exc_info.value)

    def test_valid_datatypes_pass_validation(self):
        """Test that all valid datatype values pass validation."""
        valid_datatypes = [
            "apoe",
            "biomarker",
            "dicom",
            "enrollment",
            "form",
            "genetic-availability",
            "gwas",
            "imputation",
            "scan-analysis",
        ]

        base_data = {
            "action": "submit",
            "study": "adrc",
            "pipeline_adcid": 123,
            "project_label": "test_project",
            "center_label": "test_center",
            "gear_name": "test_gear",
            "ptid": "ABC123",
            "visit_date": "2024-01-15",
            "timestamp": "2024-01-15T10:00:00Z",
        }

        for datatype in valid_datatypes:
            if datatype == "form":
                # Form datatype requires module
                event_data = {**base_data, "datatype": datatype, "module": "UDS"}
            else:
                event_data = {**base_data, "datatype": datatype}

            event = VisitEvent(**event_data)
            assert event.datatype == datatype

    def test_module_validation_for_form_datatype(self):
        """Test module validation logic for form datatype."""
        base_data = {
            "action": "submit",
            "study": "adrc",
            "pipeline_adcid": 123,
            "project_label": "test_project",
            "center_label": "test_center",
            "gear_name": "test_gear",
            "ptid": "ABC123",
            "visit_date": "2024-01-15",
            "datatype": "form",
            "timestamp": "2024-01-15T10:00:00Z",
        }

        # Form datatype without module should fail
        with pytest.raises(ValidationError) as exc_info:
            VisitEvent(**base_data)
        assert "Expected module name for form datatype" in str(exc_info.value)

        # Form datatype with valid module should pass
        valid_modules = ["UDS", "FTLD", "LBD", "MDS"]
        for module in valid_modules:
            event = VisitEvent(**{**base_data, "module": module})
            assert event.module == module

    def test_module_validation_for_non_form_datatype(self):
        """Test module validation logic for non-form datatypes."""
        base_data = {
            "action": "submit",
            "study": "adrc",
            "pipeline_adcid": 123,
            "project_label": "test_project",
            "center_label": "test_center",
            "gear_name": "test_gear",
            "ptid": "ABC123",
            "visit_date": "2024-01-15",
            "datatype": "dicom",  # Non-form datatype
            "timestamp": "2024-01-15T10:00:00Z",
        }

        # Non-form datatype with module should fail
        with pytest.raises(ValidationError) as exc_info:
            VisitEvent(**{**base_data, "module": "UDS"})
        assert "but has form module" in str(exc_info.value)

        # Non-form datatype without module should pass
        event = VisitEvent(**base_data)
        assert event.module is None

    def test_pipeline_adcid_type_conversion(self):
        """Test that pipeline_adcid is converted to integer."""
        base_data = {
            "action": "submit",
            "study": "adrc",
            "pipeline_adcid": "123",  # String that should convert to int
            "project_label": "test_project",
            "center_label": "test_center",
            "gear_name": "test_gear",
            "ptid": "ABC123",
            "visit_date": "2024-01-15",
            "datatype": "dicom",
            "timestamp": "2024-01-15T10:00:00Z",
        }

        event = VisitEvent(**base_data)
        assert isinstance(event.pipeline_adcid, int)
        assert event.pipeline_adcid == 123

    def test_null_preservation_in_optional_fields(self):
        """Test that null values in optional fields are preserved."""
        event_data = {
            "action": "submit",
            "study": "adrc",
            "pipeline_adcid": 123,
            "project_label": "test_project",
            "center_label": "test_center",
            "gear_name": "test_gear",
            "ptid": "ABC123",
            "visit_date": "2024-01-15",
            "datatype": "dicom",  # Non-form so module can be None
            "visit_number": None,  # Optional field with null
            "module": None,  # Optional field with null
            "packet": None,  # Optional field with null
            "timestamp": "2024-01-15T10:00:00Z",
        }

        event = VisitEvent(**event_data)
        assert event.visit_number is None
        assert event.module is None
        assert event.packet is None

    def test_visit_date_string_validation(self):
        """Test visit_date string pattern validation."""
        base_data = {
            "action": "submit",
            "study": "adrc",
            "pipeline_adcid": 123,
            "project_label": "test_project",
            "center_label": "test_center",
            "gear_name": "test_gear",
            "ptid": "ABC123",
            "datatype": "dicom",
            "timestamp": "2024-01-15T10:00:00Z",
        }

        # Valid date format should pass
        event = VisitEvent(**{**base_data, "visit_date": "2024-01-15"})
        assert event.visit_date == "2024-01-15"

        # Invalid date formats should fail (these don't match the YYYY-MM-DD pattern)
        invalid_dates = ["2024-1-15", "01/15/2024", "not-a-date", "2024/01/15"]

        for invalid_date in invalid_dates:
            with pytest.raises(ValidationError):
                VisitEvent(**{**base_data, "visit_date": invalid_date})

    def test_timestamp_parsing(self):
        """Test parsing of timestamp field."""
        event_data = {
            "action": "submit",
            "study": "adrc",
            "pipeline_adcid": 123,
            "project_label": "test_project",
            "center_label": "test_center",
            "gear_name": "test_gear",
            "ptid": "ABC123",
            "visit_date": "2024-01-15",
            "datatype": "dicom",
            "timestamp": "2024-01-15T10:30:45Z",  # ISO datetime string
        }

        event = VisitEvent(**event_data)

        # Check type and value (accounting for timezone)
        assert isinstance(event.timestamp, datetime)
        # Compare the datetime components, ignoring timezone for this test
        assert event.timestamp.year == 2024
        assert event.timestamp.month == 1
        assert event.timestamp.day == 15
        assert event.timestamp.hour == 10
        assert event.timestamp.minute == 30
        assert event.timestamp.second == 45

    def test_invalid_timestamp_formats_fail(self):
        """Test that invalid timestamp formats fail validation."""
        base_data = {
            "action": "submit",
            "study": "adrc",
            "pipeline_adcid": 123,
            "project_label": "test_project",
            "center_label": "test_center",
            "gear_name": "test_gear",
            "ptid": "ABC123",
            "visit_date": "2024-01-15",
            "datatype": "dicom",
        }

        invalid_timestamps = [
            "not-a-timestamp",
            "2024-13-45",  # Invalid month and day
            "15/01/2024",  # Wrong format (DD/MM/YYYY)
            "2024-01-15T25:00:00Z",  # Invalid hour (25)
            "January 15, 2024",  # Text format
        ]

        for invalid_timestamp in invalid_timestamps:
            with pytest.raises(ValidationError):
                VisitEvent(**{**base_data, "timestamp": invalid_timestamp})


class TestVisitEventSerialization:
    """Unit tests for VisitEvent serialization."""

    def test_serialization_round_trip(self):
        """Test that serializing and deserializing preserves data."""
        original_data = {
            "action": "pass-qc",
            "study": "adrc",
            "pipeline_adcid": 456,
            "project_label": "test_project",
            "center_label": "test_center",
            "gear_name": "test_gear",
            "ptid": "XYZ789",
            "visit_date": "2024-02-20",
            "visit_number": "02",
            "datatype": "form",
            "module": "FTLD",
            "packet": "F",
            "timestamp": "2024-02-20T14:30:00Z",
        }

        # Create event from data
        event = VisitEvent(**original_data)

        # Serialize to JSON
        json_data = event.model_dump_json()

        # Parse back from JSON
        parsed_data = json.loads(json_data)
        recreated_event = VisitEvent(**parsed_data)

        # Verify all fields match
        assert recreated_event.action == event.action
        assert recreated_event.study == event.study
        assert recreated_event.pipeline_adcid == event.pipeline_adcid
        assert recreated_event.project_label == event.project_label
        assert recreated_event.center_label == event.center_label
        assert recreated_event.gear_name == event.gear_name
        assert recreated_event.ptid == event.ptid
        assert recreated_event.visit_date == event.visit_date
        assert recreated_event.visit_number == event.visit_number
        assert recreated_event.datatype == event.datatype
        assert recreated_event.module == event.module
        assert recreated_event.packet == event.packet
        assert recreated_event.timestamp == event.timestamp


@composite
def valid_visit_event_data(draw):
    """Generate valid VisitEvent data for property testing."""
    datatype = draw(
        st.sampled_from(
            [
                "apoe",
                "biomarker",
                "dicom",
                "enrollment",
                "form",
                "genetic-availability",
                "gwas",
                "imputation",
                "scan-analysis",
            ]
        )
    )

    # Generate base data
    data = {
        "action": draw(st.sampled_from(["submit", "delete", "not-pass-qc", "pass-qc"])),
        "study": draw(
            st.text(
                min_size=1,
                max_size=20,
                alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
            )
        ),
        "pipeline_adcid": draw(st.integers(min_value=1, max_value=9999)),
        "project_label": draw(
            st.text(
                min_size=1,
                max_size=50,
                alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Pc")),
            )
        ),
        "center_label": draw(
            st.text(
                min_size=1,
                max_size=50,
                alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Pc")),
            )
        ),
        "gear_name": draw(
            st.text(
                min_size=1,
                max_size=50,
                alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Pc")),
            )
        ),
        "ptid": draw(
            st.text(
                min_size=1,
                max_size=10,
                alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*()_+-=",
            )
        ),
        "visit_date": draw(
            st.dates(
                min_value=datetime(2020, 1, 1).date(),
                max_value=datetime(2030, 12, 31).date(),
            )
        ).strftime("%Y-%m-%d"),
        "visit_number": draw(
            st.one_of(
                st.none(),
                st.text(
                    min_size=1,
                    max_size=10,
                    alphabet=st.characters(whitelist_categories=("Nd", "Lu", "Ll")),
                ),
            )
        ),
        "datatype": datatype,
        "packet": draw(
            st.one_of(
                st.none(),
                st.text(
                    min_size=1,
                    max_size=10,
                    alphabet=st.characters(whitelist_categories=("Lu", "Ll")),
                ),
            )
        ),
        "timestamp": draw(
            st.datetimes(
                min_value=datetime(2020, 1, 1), max_value=datetime(2030, 12, 31)
            )
        ).isoformat()
        + "Z",
    }

    # Handle module field based on datatype
    if datatype == "form":
        data["module"] = draw(st.sampled_from(["UDS", "FTLD", "LBD", "MDS"]))
    else:
        data["module"] = None

    return data


class TestVisitEventPropertyBased:
    """Property-based tests for VisitEvent model."""

    @given(valid_visit_event_data())
    def test_property_validation_enforcement(self, event_data):
        """Property 5: Validation enforcement For any valid event data, the
        VisitEvent model should successfully validate and create an instance
        with all constraints satisfied.

        Feature: event-log-scraper, Property 5: Validation enforcement
        Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8
        """
        # This should not raise any validation errors
        event = VisitEvent(**event_data)

        # Verify all constraints are satisfied
        assert event.action in ["submit", "delete", "not-pass-qc", "pass-qc"]
        assert len(event.study) >= 1
        assert isinstance(event.pipeline_adcid, int)
        assert len(event.project_label) >= 1
        assert len(event.center_label) >= 1
        assert len(event.gear_name) >= 1
        assert len(event.ptid) >= 1 and len(event.ptid) <= 10
        assert len(event.visit_date) == 10  # YYYY-MM-DD format
        assert event.datatype in [
            "apoe",
            "biomarker",
            "dicom",
            "enrollment",
            "form",
            "genetic-availability",
            "gwas",
            "imputation",
            "scan-analysis",
        ]
        assert isinstance(event.timestamp, datetime)

        # Verify module validation logic
        if event.datatype == "form":
            assert event.module is not None
            assert event.module in ["UDS", "FTLD", "LBD", "MDS"]
        else:
            assert event.module is None

    @given(st.integers(min_value=1, max_value=9999))
    def test_property_type_conversion_correctness(self, pipeline_adcid_value):
        """Property 6: Type conversion correctness For any valid pipeline_adcid
        value (as string or int), parsing should convert it to Python int type
        correctly.

        Feature: event-log-scraper, Property 6: Type conversion correctness
        Validates: Requirements 3.2
        """
        base_data = {
            "action": "submit",
            "study": "adrc",
            "project_label": "test_project",
            "center_label": "test_center",
            "gear_name": "test_gear",
            "ptid": "ABC123",
            "visit_date": "2024-01-15",
            "datatype": "dicom",
            "timestamp": "2024-01-15T10:00:00Z",
        }

        # Test with integer input
        event_int = VisitEvent(**{**base_data, "pipeline_adcid": pipeline_adcid_value})
        assert isinstance(event_int.pipeline_adcid, int)
        assert event_int.pipeline_adcid == pipeline_adcid_value

        # Test with string input
        event_str = VisitEvent(
            **{**base_data, "pipeline_adcid": str(pipeline_adcid_value)}
        )
        assert isinstance(event_str.pipeline_adcid, int)
        assert event_str.pipeline_adcid == pipeline_adcid_value

    @given(st.booleans(), st.booleans(), st.booleans())
    def test_property_null_preservation(
        self, visit_number_is_null, module_is_null, packet_is_null
    ):
        """Property 7: Null preservation For any event with null values in
        optional fields (visit_number, module, packet), parsing should preserve
        those null values in the VisitEvent object.

        Feature: event-log-scraper, Property 7: Null preservation
        Validates: Requirements 3.3
        """
        base_data = {
            "action": "submit",
            "study": "adrc",
            "pipeline_adcid": 123,
            "project_label": "test_project",
            "center_label": "test_center",
            "gear_name": "test_gear",
            "ptid": "ABC123",
            "visit_date": "2024-01-15",
            "datatype": "dicom",  # Non-form so module can be null
            "timestamp": "2024-01-15T10:00:00Z",
        }

        # Set optional fields based on the boolean flags
        if visit_number_is_null:
            base_data["visit_number"] = None
        else:
            base_data["visit_number"] = "01"

        if module_is_null:
            base_data["module"] = None
        else:
            # Can't set module for non-form datatype, so skip this test case
            if base_data["datatype"] != "form":
                base_data["module"] = None

        if packet_is_null:
            base_data["packet"] = None
        else:
            base_data["packet"] = "I"

        event = VisitEvent(**base_data)

        # Verify null preservation
        if visit_number_is_null:
            assert event.visit_number is None
        else:
            assert event.visit_number == "01"

        # Module is always None for non-form datatype
        assert event.module is None

        if packet_is_null:
            assert event.packet is None
        else:
            assert event.packet == "I"

    @given(valid_visit_event_data())
    def test_property_serialization_round_trip(self, event_data):
        """Property 8: Serialization round-trip For any valid VisitEvent
        object, serializing to JSON and then parsing back should produce an
        equivalent VisitEvent object with all fields matching.

        Feature: event-log-scraper, Property 8: Serialization round-trip
        Validates: Requirements 3.4
        """
        # Create original event
        original_event = VisitEvent(**event_data)

        # Serialize to JSON
        json_data = original_event.model_dump_json()

        # Parse back from JSON
        parsed_data = json.loads(json_data)
        recreated_event = VisitEvent(**parsed_data)

        # Verify all fields match (round-trip equivalence)
        assert recreated_event.action == original_event.action
        assert recreated_event.study == original_event.study
        assert recreated_event.pipeline_adcid == original_event.pipeline_adcid
        assert recreated_event.project_label == original_event.project_label
        assert recreated_event.center_label == original_event.center_label
        assert recreated_event.gear_name == original_event.gear_name
        assert recreated_event.ptid == original_event.ptid
        assert recreated_event.visit_date == original_event.visit_date
        assert recreated_event.visit_number == original_event.visit_number
        assert recreated_event.datatype == original_event.datatype
        assert recreated_event.module == original_event.module
        assert recreated_event.packet == original_event.packet
        assert recreated_event.timestamp == original_event.timestamp
