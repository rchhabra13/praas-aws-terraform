# Implementation Plan — AI PR Reviewer (Bedrock + Terraform + GitHub Actions)

> Execution plan for a coding agent. Self-contained: do not assume prior conversation context.
> **SCOPE LIMIT (hard):** Write files ONLY. Do **not** run `terraform init/plan/apply`, `git init/add/commit/push`, `gh` commands, or create any GitHub repo or AWS resource. The human runs those manually later. Local read-only validation (`terraform fmt`, `terraform validate -backend=false`, `python -m py_compile`) is allowed.

## Goal
Recreate the tutorial's system: when a PR opens, GitHub Actions sends the PR diff to AWS Bedrock (Amazon Nova Pro), which returns a security/performance/best-practice review, posted back as a single PR comment. Infra is provisioned by Terraform (GitHub repo + AWS OIDC/IAM + remote-state backend resources).

## Confirmed decisions (do not re-ask)
- **Model:** Amazon Nova Pro — `amazon.nova-pro-v1:0`, called via the **Bedrock Converse API** (`bedrock-runtime.converse`), NOT raw `invoke_model` (the video hit body-format breakage with raw invoke).
- **Region:** `us-east-1` everywhere.
- **Repo:** Terraform declares a private GitHub repo `praas-aws-terraform` via the `integrations/github` provider. Provider token comes from env `GITHUB_TOKEN` (already set on the human's machine) — never hardcode it.
- **Diff cap:** 240,000 chars, truncate if longer.
- **Comment style:** one formatted markdown comment via GitHub issues/comments API.
- **Diff source:** fetch via GitHub REST API with `Accept: application/vnd.github.v3.diff` — do NOT use local `git diff`/checkout (avoids the "no merge base" shallow-clone bug from the video). No `actions/checkout` step needed.
- **IAM scope:** Bedrock policy scoped to the specific Nova Pro model ARN, not `*`.

## Target file tree
```
.gitignore
IMPLEMENTATION_PLAN.md            # this file (already exists)
README.md                         # project documentation (write this)
github/
  providers.tf                    # integrations/github provider, token from GITHUB_TOKEN env
  main.tf                         # github_repository "praas-aws-terraform", private
infra/
  providers.tf                    # terraform >=1.6.0; aws provider ~>5.0; region var
  variables.tf                    # region, bedrock_model_id, repo_full_name, state_bucket_name
  backend.tf                      # S3 bucket (+versioning +AES256 +public-access-block) + DynamoDB lock table
  oidc.tf                         # OIDC provider + IAM role (trust) + role policy (bedrock + logs)
  outputs.tf                      # output role ARN
.github/workflows/
  ai-pr-review.yml                # on: pull_request; OIDC creds; run python script
scripts/
  bedrock_review.py               # fetch diff -> Bedrock converse -> post PR comment
  requirements.txt                # boto3, requests
```

---

## Step-by-step

### 1. `.gitignore`
Ignore: `.terraform/`, `.terraform.lock.hcl`, `*.tfstate`, `*.tfstate.*`, `*.tfvars`, `crash.log`, `__pycache__/`, `*.pyc`, `.env`.

### 2. `github/providers.tf`
- `terraform.required_providers` → `github = { source = "integrations/github", version = "~> 6.0" }`.
- `provider "github" {}` — leave empty; it reads `GITHUB_TOKEN` (and `GITHUB_OWNER` if set) from env automatically. Do not put a token in code.

### 3. `github/main.tf`
- `resource "github_repository" "this"` with `name = "praas-aws-terraform"`, `description`, `visibility = "private"`, `auto_init = true`.

### 4. `infra/providers.tf`
- `terraform { required_version = ">= 1.6.0"; required_providers { aws = { source = "hashicorp/aws", version = "~> 5.0" } } }`.
- `provider "aws" { region = var.region }`.

### 5. `infra/variables.tf`
- `region` — string, default `"us-east-1"`.
- `bedrock_model_id` — string, default `"amazon.nova-pro-v1:0"`.
- `repo_full_name` — string, no default (e.g. `"owner/praas-aws-terraform"`); used to scope OIDC trust. Add a comment telling the human to set this.
- `state_bucket_name` — string, no default; S3 bucket names are globally unique, human must supply.

### 6. `infra/backend.tf`
Declared (habit / future use), not wired as an actual `backend` block yet:
- `aws_s3_bucket "state"` (`bucket = var.state_bucket_name`).
- `aws_s3_bucket_versioning "state"` → `status = "Enabled"`.
- `aws_s3_bucket_server_side_encryption_configuration "state"` → `sse_algorithm = "AES256"`.
- `aws_s3_bucket_public_access_block "state"` → all four flags `true`.
- `aws_dynamodb_table "locks"` → `name = "terraform-locks"`, `billing_mode = "PAY_PER_REQUEST"`, hash key `LockID` (type `S`).

### 7. `infra/oidc.tf`
- `data "aws_caller_identity" "current" {}` (for account id in ARNs if needed).
- `aws_iam_openid_connect_provider "github"`:
  - `url = "https://token.actions.githubusercontent.com"`
  - `client_id_list = ["sts.amazonaws.com"]`
  - `thumbprint_list` — use `["6938fd4d98bab03faadb97b34396831e3780aea1"]` (GitHub's well-known root thumbprint; add a comment noting AWS now validates OIDC against its trust store so this is largely legacy but still required by the resource).
- `aws_iam_role "gha_bedrock"`:
  - `assume_role_policy` — `sts:AssumeRoleWithWebIdentity`, principal = the OIDC provider ARN, conditions:
    - `StringEquals` on `token.actions.githubusercontent.com:aud` = `"sts.amazonaws.com"`.
    - `StringLike` on `token.actions.githubusercontent.com:sub` = `"repo:${var.repo_full_name}:*"`.
  - Build with `data "aws_iam_policy_document"` for readability.
- `aws_iam_role_policy "bedrock"` attached to that role:
  - Statement 1: `bedrock:InvokeModel` (+ `bedrock:InvokeModelWithResponseStream`) on resource `arn:aws:bedrock:${var.region}::foundation-model/${var.bedrock_model_id}`.
  - Statement 2: `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents` on `arn:aws:logs:*:*:*`.

### 8. `infra/outputs.tf`
- `output "gha_role_arn"` = `aws_iam_role.gha_bedrock.arn`, with a description telling the human to store it as the GitHub Actions secret `AWS_ROLE_ARN`.

### 9. `scripts/requirements.txt`
```
boto3>=1.34
requests>=2.31
```

### 10. `scripts/bedrock_review.py`
Structure (keep it lean; wrap only the 3 external calls in try/except — the two GitHub HTTP calls and the Bedrock call):
1. Read env: `GITHUB_TOKEN`, `GITHUB_REPOSITORY` (`owner/repo`), `PR_NUMBER`, `AWS_REGION` (default `us-east-1`), `BEDROCK_MODEL_ID` (default `amazon.nova-pro-v1:0`). Exit non-zero with a clear message if a required one is missing.
2. `fetch_diff()` — `GET https://api.github.com/repos/{repo}/pulls/{pr}` with headers `Authorization: Bearer <token>`, `Accept: application/vnd.github.v3.diff`. Return `resp.text`. Raise on non-200.
3. Truncate to `MAX_DIFF_CHARS = 240_000`; if truncated, append a note line so the model knows.
4. `build_prompt(diff)` — instruct the model to act as a senior DevOps reviewer and return a **human-readable markdown report** with sections: Summary, Security, Performance, Best Practices, and an overall risk note. Ask it not to invent issues if the diff is trivial.
5. `review(prompt)` — `boto3.client("bedrock-runtime", region_name=AWS_REGION).converse(modelId=..., messages=[{"role":"user","content":[{"text": prompt}]}], inferenceConfig={"maxTokens":1024,"temperature":0.2})`. Extract `resp["output"]["message"]["content"][0]["text"]`.
6. `post_comment(body)` — `POST https://api.github.com/repos/{repo}/issues/{pr}/comments` with bearer token + `Accept: application/vnd.github+json`, json `{"body": body}`. Raise on non-201.
7. `main()` wires them; prefix the posted comment with a heading like `## 🤖 AI PR Review (Amazon Nova Pro)`.
- Use `if __name__ == "__main__": main()`. No AI-attribution text beyond the functional heading above (that heading is the bot's own label, fine to keep).

### 11. `.github/workflows/ai-pr-review.yml`
- `name: AI PR Review`
- `on: pull_request:` (types default: opened, synchronize, reopened).
- Top-level `permissions:` → `id-token: write`, `contents: read`, `pull-requests: write`.
- One job `review`, `runs-on: ubuntu-latest`. **No checkout step.**
- Steps:
  1. `aws-actions/configure-aws-credentials@v4` with `role-to-assume: ${{ secrets.AWS_ROLE_ARN }}`, `aws-region: us-east-1`.
  2. `actions/setup-python@v5` with `python-version: '3.12'`.
  3. `run: pip install -r scripts/requirements.txt` — note: this needs the repo files, and there is no checkout. Resolve this by adding a minimal `actions/checkout@v4` step **without** `fetch-depth` (default depth is fine because we do NOT run `git diff` — we only need the script/requirements files on disk). Put checkout first. (This is the one place a checkout is needed — for the script files, not for the diff. Add a comment in the YAML explaining why depth doesn't matter here.)
  4. `run: python scripts/bedrock_review.py` with `env:` → `GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}`, `GITHUB_REPOSITORY: ${{ github.repository }}`, `PR_NUMBER: ${{ github.event.pull_request.number }}`, `AWS_REGION: us-east-1`, `BEDROCK_MODEL_ID: amazon.nova-pro-v1:0`.

### 12. `README.md` (documentation deliverable)
Write a clear README covering:
- **What it does** — one-paragraph overview + a simple flow line: `PR opened → GitHub Actions → Bedrock (Nova Pro) → review comment on PR`.
- **Architecture** — the three pieces (Terraform infra, GitHub Actions workflow, Python script) and how OIDC removes the need for stored AWS keys (only `AWS_ROLE_ARN` secret is stored).
- **Prerequisites** — Terraform ≥1.6, AWS account with Bedrock access to Nova Pro in us-east-1, a GitHub PAT in `GITHUB_TOKEN`, AWS creds configured locally.
- **Setup (manual steps the human runs)** — numbered:
  1. `cd github && terraform init && terraform apply` (creates the repo).
  2. `cd infra`, set `repo_full_name` and `state_bucket_name` (via `terraform.tfvars` or `-var`), `terraform init && terraform apply`.
  3. Copy `gha_role_arn` output → add as GitHub repo secret `AWS_ROLE_ARN`.
  4. Push this code to the repo; open a test PR; watch the Action post a review.
- **Repo layout** — the file tree above with one-line descriptions.
- **Configuration** — the Terraform variables and the workflow env vars, in a small table.
- **Cost / cleanup note** — resources are billable; `terraform destroy` to tear down.
- **Design notes** — why Converse API over raw invoke, why API-diff over `git diff`, why scoped IAM. Keep it brief.
- Do **not** include any AI-authorship/attribution lines in the README.

---

## Verification (read-only, allowed)
1. `terraform fmt -recursive` then `terraform validate` in each of `github/` and `infra/` using `terraform init -backend=false` (no state, no provider auth needed for validate on aws/github with recent versions — if validate requires provider download, that's fine; it does not create resources).
2. `python -m py_compile scripts/bedrock_review.py`.
3. Manually re-read `ai-pr-review.yml` to confirm permissions block and secret/env wiring.
4. Confirm no secret/token/ARN literals are committed anywhere.

## Definition of done
All files above exist and pass verification. Nothing provisioned, nothing pushed. Hand back to the human with the manual setup steps from the README.
