python_sources()

python_aws_lambda_function(
    name="lambda",
    runtime="python3.12",
    handler="lambda_function.py:lambda_handler",
    include_requirements=False,
)

python_aws_lambda_layer(
    name="powertools",
    runtime="python3.12",
    dependencies=[
        "//:root#aws-lambda-powertools",
    ],
    include_sources=False,
)

python_aws_lambda_layer(
    name="data_processing",
    runtime="python3.12",
    dependencies=[
        "//:root#polars",
        "//:root#pydantic",
    ],
    include_sources=False,
)
