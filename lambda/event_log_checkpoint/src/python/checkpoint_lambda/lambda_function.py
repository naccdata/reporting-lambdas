from typing import Any
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger()

def lambda_handler(event: dict[str,Any], context: LambdaContext) -> dict[str, Any]:
    """Initial lambda handler"""
    return {}