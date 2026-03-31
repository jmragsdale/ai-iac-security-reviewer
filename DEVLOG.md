# DEVLOG — AI IaC Security Reviewer

## v1.0 — Initial Release

**Motivation:** At Cisco and Truist, manual security review of Terraform PRs was a
bottleneck — 80+ teams submitting infrastructure changes, one security architecture
team reviewing. Most misconfigurations got through because reviewers were looking at
diffs, not the full security posture of each resource. Wanted to build a tool that
puts a security architect's eye on every IaC file automatically.

**Why AI over static analysis:** Tools like tfsec and checkov are excellent for
known-pattern detection but miss contextual risks — e.g., an IAM policy that looks
fine in isolation but is dangerous given the resource it's attached to. LLMs reason
about intent and context, not just rule matching. The ideal pipeline uses both:
static tools for speed and determinism, AI for depth and explanation.

**Provider abstraction:** Tested Claude 3.5 Sonnet, GPT-4o, Gemini 1.5 Pro, and
local Mistral/Llama models. Cloud models produced richer compliance mapping and
better attack scenario descriptions. Local models (7-8B) performed well on
structured findings but occasionally missed cross-resource context. Built the
provider abstraction so teams can choose based on their data sensitivity requirements.

**JSON output schema:** Iterated on the output format several times. Early versions
returned free-text, which was readable but not machine-parseable. Switched to
enforcing a strict JSON schema in the system prompt so output can be piped into
SIEM platforms, Jira, or ServiceNow ticketing workflows.

**CI/CD gate logic:** Exit code 1 on HIGH+ findings was the key design decision for
pipeline integration. Teams can tune `--fail-on` to their risk appetite — some
orgs block only CRITICAL in early rollout, then tighten to HIGH once developers
trust the tool.

**Complementary to OPA:** This tool is intentionally complementary to the
[iac-policy-pipeline](https://github.com/jmragsdale/iac-policy-pipeline) project.
OPA enforces deterministic, auditable rules (great for compliance). AI review catches
contextual and novel issues OPA policies haven't been written for yet. Run both.

**Next iteration ideas:**
- Azure Bicep and CloudFormation parser support
- Diff mode — only review changed resources in a PR
- Auto-generate OPA policies from AI findings
- VS Code extension for real-time feedback while writing IaC
