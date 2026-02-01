# REDCap Report Processor Lambda

This Lambda function exports a REDCap report, processes into Parquet format, and stores the results in S3.

## What This Lambda Does

The REDCap Report Processor Lambda:

1. Exports a REDCap report based on the input parameter path
2. Converts the report to Parquet format
3. Writes the results to S3, and may overwrite results

## Directory Structure

```
lambda/redcap_report_processor/
├── src/python/
│   └── redcap_report_processor_lambda/  # Lambda function source code
├── test/python/                         # Lambda function tests
│
├── main.tf                              # Terraform configuration
├── outputs.tf                           # Terraform outputs
├── README.md                            # This file - Lambda overview
├── terraform.tfvars.example             # Example Terraform variables
└── variables.tf                         # Terraform variables
```

## TODO
