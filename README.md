![Python](https://img.shields.io/badge/Python-3.9+-blue?logo=python)
![Terraform](https://img.shields.io/badge/Terraform-IaC-purple?logo=terraform)
![CI/CD Ready](https://img.shields.io/badge/CI%2FCD-Gate_Ready-brightgreen)
![Multi-LLM](https://img.shields.io/badge/LLM-Local_%7C_OpenAI_%7C_Anthropic-orange)
![License](https://img.shields.io/badge/License-MIT-green)

# AI IaC Security Reviewer

AI-powered security review for **Terraform, Bicep, and CloudFormation** that catches misconfigurations before they reach the cloud. Integrates directly into CI/CD pipelines and blocks deployments with critical or high findings.

Supports three LLM backends: **local** (LM Studio — zero data exfiltration), **OpenAI**, and **Anthropic Claude**.

## The Problem

IaC moves fast. Security reviews don't. By the time a human auditor reviews a Terraform PR, the misconfiguration is often already deployed — open security groups, public S3 buckets, unencrypted databases, overpermissioned IAM roles.

This tool puts an AI security architect in your CI/CD pipeline. Every `terraform plan` gets reviewed before `terraform apply`.

## What It Catches

| Category | Examples |
|---|---|
| Network exposure | Open security groups (0.0.0.0/0 on SSH, RDP, DB ports) |
| Storage | Public S3 buckets, missing encryption at rest |
| Identity | AdministratorAccess, wildcard IAM policies, missing MFA |
| Secrets | Hardcoded passwords, API keys in user_data or env vars |
| Compute | IMDSv2 not enforced, public IPs on prod instances |
| Audit | Missing CloudTrail, VPC Flow Logs, Diagnostic Settings |
| Data | Unencrypted RDS, publicly accessible databases, no backups |
| Governance | Missing deletion protection, resource locks, no versioning |

## Quick Start

```bash
git clone https://github.com/jmragsdale/ai-iac-security-reviewer.git
cd ai-iac-security-reviewer
pip install -r requirements.txt

# Run against the sample insecure Terraform file
python reviewer.py samples/insecure.tf
```

## LLM Providers

### Local (default) — no API key, no data exfiltration
```bash
# Requires LM Studio running with a model loaded
python reviewer.py main.tf
python reviewer.py main.tf --provider local
```

### OpenAI
```bash
export OPENAI_API_KEY=sk-...
python reviewer.py main.tf --provider openai
```

### Anthropic Claude
```bash
export ANTHROPIC_API_KEY=sk-ant-...
python reviewer.py main.tf --provider anthropic
```

## CI/CD Integration

### GitHub Actions
```yaml
- name: AI Security Review
  run: |
    pip install requests
    python reviewer.py ${{ github.workspace }}/*.tf --fail-on HIGH
  # Exit code 1 blocks the workflow if HIGH or CRITICAL findings exist
```

### GitLab CI
```yaml
iac-security-review:
  script:
    - pip install requests
    - python reviewer.py *.tf --fail-on HIGH --json-out security-report.json
  artifacts:
    paths:
      - security-report.json
```

### Pre-commit hook
```bash
# .git/hooks/pre-commit
python /path/to/reviewer.py $(git diff --cached --name-only | grep '\.tf$')
```

## Example Output

```
════════════════════════════════════════════════════════════════
  IaC SECURITY REVIEW  ·  insecure.tf
════════════════════════════════════════════════════════════════
  Overall Risk: CRITICAL
  Findings:  4 CRITICAL  3 HIGH  2 MEDIUM  1 LOW

  Multiple critical misconfigurations detected including public S3 bucket,
  SSH/RDP open to the internet, administrator-level IAM role, and hardcoded
  credentials. This configuration would fail PCI-DSS, SOC2, and CIS Benchmark audits.

────────────────────────────────────────────────────────────────
  FINDING-001  CRITICAL  —  S3 Bucket Publicly Readable
  Resource:  aws_s3_bucket.data
  Location:  acl = "public-read"

  The S3 bucket is configured with public-read ACL, allowing any internet
  user to list and download all objects. This is a leading cause of data breaches.

  Attack scenario: An attacker queries s3.amazonaws.com/my-company-data-bucket
  to enumerate and exfiltrate all stored objects with no authentication.

  Fix: Remove acl = "public-read". Add aws_s3_bucket_public_access_block
  with all four block settings set to true.
  Compliance: CIS 2.1.2, NIST SC-28, PCI-DSS Req 10.3
...
```

## JSON Output (for SIEM/ticketing)

```bash
python reviewer.py main.tf --json-out findings.json
```

```json
{
  "summary": {
    "risk_level": "CRITICAL",
    "total_findings": 10,
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
    "overview": "Multiple critical misconfigurations..."
  },
  "findings": [
    {
      "id": "FINDING-001",
      "severity": "CRITICAL",
      "title": "S3 Bucket Publicly Readable",
      "resource": "aws_s3_bucket.data",
      "remediation": "...",
      "compliance": ["CIS 2.1.2", "NIST SC-28", "PCI-DSS Req 10.3"]
    }
  ]
}
```

## Multi-LLM Comparison

This tool was evaluated across multiple LLM backends for security review quality:

| Provider | Finding Coverage | False Positives | Remediation Quality |
|---|---|---|---|
| Claude 3.5 Sonnet | ⭐⭐⭐⭐⭐ | Very Low | Excellent |
| GPT-4o | ⭐⭐⭐⭐⭐ | Low | Excellent |
| Gemini 1.5 Pro | ⭐⭐⭐⭐ | Low | Very Good |
| Mistral 7B (local) | ⭐⭐⭐⭐ | Medium | Good |
| Llama 3 8B (local) | ⭐⭐⭐⭐ | Low | Good |

Cloud models produce richer compliance mapping. Local models are suitable for
teams where infrastructure code cannot be sent to external APIs.

## Architecture

```
reviewer.py  (CLI)
    │
    ├── src/providers.py    ← LLM backend abstraction
    │     ├── LocalProvider      (LM Studio, localhost)
    │     ├── OpenAIProvider     (gpt-4o)
    │     └── AnthropicProvider  (claude-3-5-sonnet)
    │
    ├── src/prompts.py      ← Security-expert system prompt + JSON schema
    │
    └── src/report.py       ← Parse JSON, render human output, exit codes
```

## Related Projects

- [local-llm-security-copilot](https://github.com/jmragsdale/local-llm-security-copilot) — Local LLM for log analysis, CVE explanation, config review
- [iac-policy-pipeline](https://github.com/jmragsdale/iac-policy-pipeline) — OPA policy enforcement (deterministic rules, complements AI review)

## Author

**Jermaine Ragsdale** · CISSP · AWS Solutions Architect  
[jmragsdale.com](https://jmragsdale.com) · [LinkedIn](https://linkedin.com/in/jermaine-ragsdale-cissp) · [GitHub](https://github.com/jmragsdale)
