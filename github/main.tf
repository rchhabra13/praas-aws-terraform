resource "github_repository" "this" {
  name        = "praas-aws-terraform"
  description = "AI PR reviewer: AWS Bedrock + Terraform + GitHub Actions"
  visibility  = "private"
  auto_init   = true
}
