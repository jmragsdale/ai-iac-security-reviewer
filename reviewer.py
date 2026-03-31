#!/usr/bin/env python3
"""
AI IaC Security Reviewer
--------------------------
AI-powered security review for Terraform, Bicep, and CloudFormation.
Supports local LLM (LM Studio), OpenAI, and Anthropic as backends.
CI/CD friendly — exits non-zero when critical or high findings are detected.

Usage:
  python reviewer.py samples/insecure.tf
  python reviewer.py main.tf --provider openai
  python reviewer.py main.tf --provider anthropic --json-out report.json
  python reviewer.py *.tf --fail-on MEDIUM
"""

import argparse
import sys
from pathlib import Path

from src.providers import get_provider
from src.prompts import SYSTEM_PROMPT, build_review_prompt
from src.report import parse_llm_response, print_report, save_json

BANNER = """
╔══════════════════════════════════════════════════════════════╗
║   AI IaC SECURITY REVIEWER  ·  v1.0                         ║
║   Terraform · Bicep · CloudFormation  ·  CI/CD Ready        ║
╚══════════════════════════════════════════════════════════════╝
"""

SEVERITY_ORDER = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}


def review_file(filepath: Path, provider, json_out: str = None) -> int:
    """Review a single IaC file. Returns exit code."""
    print(f"\n[*] Reviewing: {filepath.name}")
    code = filepath.read_text(encoding="utf-8")

    raw = provider.chat(SYSTEM_PROMPT, build_review_prompt(code, filepath.name))

    try:
        data = parse_llm_response(raw)
    except Exception as e:
        print(f"[ERROR] Failed to parse LLM response as JSON: {e}")
        print("[RAW RESPONSE]\n", raw)
        return 1

    exit_code = print_report(data, filepath.name)

    if json_out:
        out_path = json_out if len(sys.argv) > 1 else f"{filepath.stem}-security-report.json"
        save_json(data, out_path)

    return exit_code


def main():
    print(BANNER)

    parser = argparse.ArgumentParser(
        description="AI-powered security review for Infrastructure-as-Code files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python reviewer.py samples/insecure.tf
  python reviewer.py main.tf --provider local
  python reviewer.py main.tf --provider openai
  python reviewer.py main.tf --provider anthropic --json-out findings.json
  python reviewer.py *.tf --fail-on MEDIUM

Providers:
  local      LM Studio (default) — no API key, no data leaves machine
  openai     OpenAI API          — requires OPENAI_API_KEY env var
  anthropic  Anthropic Claude    — requires ANTHROPIC_API_KEY env var

CI/CD:
  Exit code 0 = no findings at or above --fail-on threshold
  Exit code 1 = findings found (blocks the pipeline)
        """,
    )
    parser.add_argument("files", nargs="+", metavar="FILE",
                        help="IaC file(s) to review (.tf, .bicep, .yaml, .json)")
    parser.add_argument("--provider", "-p", default="local",
                        choices=["local", "openai", "anthropic"],
                        help="LLM provider (default: local via LM Studio)")
    parser.add_argument("--model", help="Override model ID")
    parser.add_argument("--url", default="http://localhost:1234/v1",
                        help="LM Studio API URL (local provider only)")
    parser.add_argument("--fail-on", default="HIGH", metavar="SEVERITY",
                        choices=["CRITICAL", "HIGH", "MEDIUM", "LOW"],
                        help="Exit non-zero if any finding >= this severity (default: HIGH)")
    parser.add_argument("--json-out", metavar="FILE",
                        help="Save findings as JSON (useful for SIEM/ticketing integration)")

    args = parser.parse_args()

    # Initialise provider
    try:
        provider_kwargs = {}
        if args.provider == "local":
            provider_kwargs = {"base_url": args.url}
        if args.model:
            provider_kwargs["model"] = args.model
        provider = get_provider(args.provider, **provider_kwargs)
    except RuntimeError as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)

    # Resolve file list
    files = []
    for pattern in args.files:
        p = Path(pattern)
        if p.is_file():
            files.append(p)
        else:
            # Glob expansion (e.g. *.tf)
            files.extend(Path(".").glob(pattern))

    if not files:
        print("[ERROR] No files matched. Check file paths.")
        sys.exit(1)

    fail_threshold = SEVERITY_ORDER.get(args.fail_on, 3)
    overall_exit = 0

    for f in files:
        code = review_file(f, provider, args.json_out)
        if code != 0:
            overall_exit = 1

    if overall_exit == 1:
        print(f"[!] Pipeline gate: findings at or above {args.fail_on} detected.")
    else:
        print(f"[+] No findings at or above {args.fail_on} threshold. Pipeline clear.")

    sys.exit(overall_exit)


if __name__ == "__main__":
    main()
