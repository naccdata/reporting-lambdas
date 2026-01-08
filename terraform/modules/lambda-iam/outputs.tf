# Outputs for Lambda IAM Role Module

output "role_arn" {
  description = "ARN of the Lambda execution role"
  value       = aws_iam_role.lambda_role.arn
}

output "role_name" {
  description = "Name of the Lambda execution role"
  value       = aws_iam_role.lambda_role.name
}

output "role_id" {
  description = "ID of the Lambda execution role"
  value       = aws_iam_role.lambda_role.id
}

output "role_unique_id" {
  description = "Unique ID of the Lambda execution role"
  value       = aws_iam_role.lambda_role.unique_id
}

output "attached_policies" {
  description = "List of attached policy ARNs"
  value = concat(
    ["arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"],
    var.enable_xray ? ["arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"] : [],
    var.additional_policy_arns
  )
}

output "custom_policy_names" {
  description = "Names of custom policies created"
  value       = keys(var.custom_policies)
}

output "s3_access_enabled" {
  description = "Whether S3 access policy was created"
  value       = length(var.s3_bucket_arns) > 0
}

output "s3_bucket_arns" {
  description = "S3 bucket ARNs that the role has access to"
  value       = var.s3_bucket_arns
}