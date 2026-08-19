# PR Reviewer Architecture — v1 vs v2

```mermaid
flowchart LR
    subgraph V1["v1 — custom script"]
        direction LR
        T1["pull_request event<br/>(every PR, automatic)"] --> R1["GitHub Actions runner<br/>bedrock_review.py"]
        R1 -->|"GET diff / POST comment<br/>(REST API)"| PR1["Pull Request"]
    end

    subgraph V2["v2 — praas-agent"]
        direction LR
        T2["praas-agent label applied<br/>(opt-in per PR)"] --> R2["GitHub Actions runner<br/>checkout base ref only"]
        SUB["IkkaLabs/praas-test<br/>private, different owner"] -->|"clone via SUBMODULE_PAT"| R2
        R2 -->|"docker build"| BUILD["praas-agent container"]
        BUILD -->|"GET diff / POST comment<br/>(REST API)"| PR2["Pull Request"]
    end

    subgraph AWS["Shared AWS substrate — unchanged"]
        direction LR
        OIDC["OIDC Provider<br/>token.actions.githubusercontent.com"] --> ROLE["IAM Role<br/>gha-bedrock-pr-review"]
        ROLE -->|"bedrock:InvokeModel"| BEDROCK["AWS Bedrock<br/>amazon.nova-pro-v1:0"]
    end

    R1 -->|"OIDC JWT → AssumeRoleWithWebIdentity"| OIDC
    BUILD -->|"OIDC JWT → AssumeRoleWithWebIdentity"| OIDC
```

Both versions authenticate to the *same* IAM role and call the *same* Bedrock model — nothing on the AWS side changed. What changed sits entirely on the GitHub side: v2 adds a cross-org clone (`SUBMODULE_PAT` against a private repo under a different owner) and a container build step before the OIDC hop, and trades the automatic every-PR trigger for a deliberate label.
