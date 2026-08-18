"""Fetches a PR diff, sends it to Bedrock (Amazon Nova Pro via Converse), posts the review as a PR comment."""
import os
import sys

import boto3
import requests

MAX_DIFF_CHARS = 240_000
GITHUB_API = "https://api.github.com"


def load_env():
    required = ["GITHUB_TOKEN", "GITHUB_REPOSITORY", "PR_NUMBER"]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        sys.exit(f"Missing required env vars: {', '.join(missing)}")

    return {
        "token": os.environ["GITHUB_TOKEN"],
        "repo": os.environ["GITHUB_REPOSITORY"],
        "pr_number": os.environ["PR_NUMBER"],
        "aws_region": os.environ.get("AWS_REGION", "us-east-1"),
        "model_id": os.environ.get("BEDROCK_MODEL_ID", "amazon.nova-pro-v1:0"),
    }


def fetch_diff(env):
    url = f"{GITHUB_API}/repos/{env['repo']}/pulls/{env['pr_number']}"
    headers = {
        "Authorization": f"Bearer {env['token']}",
        "Accept": "application/vnd.github.v3.diff",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        sys.exit(f"Failed to fetch PR diff: {e}")
    return resp.text


def truncate_diff(diff):
    if len(diff) <= MAX_DIFF_CHARS:
        return diff
    return diff[:MAX_DIFF_CHARS] + "\n\n[diff truncated at 240k chars]"


def build_prompt(diff):
    return f"""You are a senior DevOps engineer reviewing a pull request diff.

Review the diff below and produce a human-readable markdown report with these sections:
- Summary
- Security
- Performance
- Best Practices

If the diff is trivial or has no issues in a section, say so briefly rather than inventing problems.

Diff:
```
{diff}
```
"""


def review(env, prompt):
    client = boto3.client("bedrock-runtime", region_name=env["aws_region"])
    try:
        resp = client.converse(
            modelId=env["model_id"],
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": 1024, "temperature": 0.2},
        )
    except Exception as e:
        sys.exit(f"Bedrock converse call failed: {e}")
    return resp["output"]["message"]["content"][0]["text"]


def post_comment(env, body):
    url = f"{GITHUB_API}/repos/{env['repo']}/issues/{env['pr_number']}/comments"
    headers = {
        "Authorization": f"Bearer {env['token']}",
        "Accept": "application/vnd.github+json",
    }
    try:
        resp = requests.post(url, headers=headers, json={"body": body}, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        sys.exit(f"Failed to post PR comment: {e}")


def main():
    env = load_env()
    diff = truncate_diff(fetch_diff(env))
    prompt = build_prompt(diff)
    review_text = review(env, prompt)
    body = f"## 🤖 AI PR Review (Amazon Nova Pro)\n\n{review_text}"
    post_comment(env, body)


if __name__ == "__main__":
    main()
