"""Report formatting — converts JSON findings into human-readable output."""

import json
from typing import Optional

SEVERITY_COLORS = {
    "CRITICAL": "\033[91m",  # bright red
    "HIGH":     "\033[31m",  # red
    "MEDIUM":   "\033[33m",  # yellow
    "LOW":      "\033[36m",  # cyan
}
RESET = "\033[0m"
BOLD = "\033[1m"


def _color(text: str, severity: str) -> str:
    return f"{SEVERITY_COLORS.get(severity, '')}{text}{RESET}"


def parse_llm_response(raw: str) -> dict:
    """Extract and parse JSON from LLM response, tolerating minor formatting issues."""
    raw = raw.strip()
    # Strip markdown code fences if model included them despite instructions
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    return json.loads(raw)


def print_report(data: dict, filename: str) -> int:
    """Print a human-readable report. Returns exit code (1 if critical/high found)."""
    summary = data.get("summary", {})
    findings = data.get("findings", [])
    hardening = data.get("hardening", [])

    risk = summary.get("risk_level", "UNKNOWN")
    print(f"\n{'═' * 64}")
    print(f"  {BOLD}IaC SECURITY REVIEW  ·  {filename}{RESET}")
    print(f"{'═' * 64}")
    print(f"  Overall Risk: {_color(BOLD + risk + RESET, risk)}")
    print(f"  Findings:  "
          f"{_color(str(summary.get('critical', 0)) + ' CRITICAL', 'CRITICAL')}  "
          f"{_color(str(summary.get('high', 0)) + ' HIGH', 'HIGH')}  "
          f"{_color(str(summary.get('medium', 0)) + ' MEDIUM', 'MEDIUM')}  "
          f"{_color(str(summary.get('low', 0)) + ' LOW', 'LOW')}")
    print(f"\n  {summary.get('overview', '')}\n")

    if not findings:
        print("  No findings. Configuration looks clean.\n")
        return 0

    for f in findings:
        sev = f.get("severity", "LOW")
        print(f"{'─' * 64}")
        print(f"  {_color(f['id'] + '  ' + sev, sev)}  —  {BOLD}{f['title']}{RESET}")
        print(f"  Resource:  {f.get('resource', 'N/A')}")
        if f.get("line_hint"):
            print(f"  Location:  {f['line_hint']}")
        print(f"\n  {f.get('description', '')}")
        if f.get("attack_scenario"):
            print(f"\n  {BOLD}Attack scenario:{RESET} {f['attack_scenario']}")
        print(f"\n  {BOLD}Fix:{RESET} {f.get('remediation', 'See description')}")
        if f.get("compliance"):
            print(f"  {BOLD}Compliance:{RESET} {', '.join(f['compliance'])}")
        print()

    if hardening:
        print(f"{'─' * 64}")
        print(f"  {BOLD}HARDENING RECOMMENDATIONS{RESET}")
        for h in hardening:
            print(f"  •  {h}")
        print()

    print(f"{'═' * 64}\n")

    critical = summary.get("critical", 0)
    high = summary.get("high", 0)
    return 1 if (critical + high) > 0 else 0


def save_json(data: dict, path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"[+] JSON report saved: {path}")
