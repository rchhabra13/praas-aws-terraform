variable "region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "bedrock_model_id" {
  description = "Bedrock model ID used by the PR review script"
  type        = string
  default     = "amazon.nova-pro-v1:0"
}

variable "repo_full_name" {
  description = "GitHub repo as owner/repo, used to scope the OIDC trust policy. Set this before apply."
  type        = string
}
