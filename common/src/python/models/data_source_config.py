"""DataSourceConfig model for data source configurations."""

from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field, validator


class DataSourceConfig(BaseModel):
    """Configuration for data sources - used by lambda infrastructure."""

    name: str = Field(description="Data source name", min_length=1, max_length=100)
    type: Literal["s3", "api", "database", "sqs"] = Field(description="Source type")
    connection_params: Dict[str, Any] = Field(
        description="Connection parameters", default_factory=dict
    )
    polling_interval: Optional[int] = Field(
        default=None, description="Polling interval in seconds", ge=1
    )
    output_format: Literal["parquet", "json", "csv"] = Field(
        default="parquet", description="Output format"
    )

    @validator("connection_params")
    def validate_connection_params(cls, v, values):
        """Validate connection parameters based on source type."""
        source_type = values.get("type")

        # Define required parameters for each source type
        required_params_map = {
            "s3": ["bucket_name"],
            "api": ["base_url"],
            "database": ["host", "database"],
            "sqs": ["queue_url"],
        }

        required_params = required_params_map.get(source_type, [])
        for param in required_params:
            if param not in v:
                raise ValueError(
                    f"{source_type.upper()} source requires '{param}' in "
                    "connection_params"
                )

        return v

    def get_connection_string(self) -> str:
        """Generate connection string based on source type."""
        if self.type == "s3":
            bucket = self.connection_params["bucket_name"]
            prefix = self.connection_params.get("prefix", "")
            return f"s3://{bucket}/{prefix}"

        elif self.type == "api":
            return self.connection_params["base_url"]

        elif self.type == "database":
            host = self.connection_params["host"]
            port = self.connection_params.get("port", 5432)
            database = self.connection_params["database"]
            return f"{host}:{port}/{database}"

        elif self.type == "sqs":
            return self.connection_params["queue_url"]

        return f"{self.type}://{self.name}"
