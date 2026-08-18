terraform {
  required_version = ">= 1.6.0"

  required_providers {
    github = {
      source  = "integrations/github"
      version = "~> 6.0"
    }
  }
}

# Reads token from GITHUB_TOKEN env var (and owner from GITHUB_OWNER if set).
# Do not hardcode a token here.
provider "github" {}
