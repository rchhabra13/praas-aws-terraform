output "gha_role_arn" {
  description = "IAM role ARN for GitHub Actions to assume via OIDC. Store this as the AWS_ROLE_ARN repo secret."
  value       = aws_iam_role.gha_bedrock.arn
}
