#!/usr/bin/env python3
"""
Bulk Flag Approval Workflow for LaunchDarkly

Phases:
  1. List input — read flag keys from file
  2. Create approval requests — one per flag (turn ON in target environment)
  3. [Human pause] — wait for CAB/approvals
  4. Apply approval requests — apply each approved request

Usage:
  python approvalRequest.py --input flags.txt --project default --env production
  python approvalRequest.py --input flags.txt --project default --env production --dry-run

Environment:
  LD_API_TOKEN — LaunchDarkly API token (required unless --dry-run)
"""

import argparse
import json
import os
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None


BASE_URL = "https://app.launchdarkly.com/api/v2"


def load_flag_keys(input_path: str) -> list[str]:
    """Load flag keys from file (one per line, skip empty and # comments)."""
    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    keys = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        keys.append(line)
    return keys


def create_approval_request(
    api_token: str,
    project_key: str,
    environment_key: str,
    flag_key: str,
    description: str | None = None,
    notify_member_ids: list[str] | None = None,
) -> dict:
    """Create an approval request to turn a flag ON in the given environment."""
    resource_id = f"proj/{project_key}:env/{environment_key}:flag/{flag_key}"
    desc = description or f"Enable flag {flag_key} in {environment_key}"
    payload = {
        "resourceId": resource_id,
        "description": desc,
        "instructions": [
            {"kind": "turnFlagOn", "environmentKey": environment_key}
        ],
    }
    if notify_member_ids:
        payload["notifyMemberIds"] = notify_member_ids

    resp = requests.post(
        f"{BASE_URL}/approval-requests",
        headers={
            "Authorization": api_token,
            "Content-Type": "application/json",
        },
        json=payload,
    )
    resp.raise_for_status()
    return resp.json()


def apply_approval_request(api_token: str, approval_request_id: str) -> dict:
    """Apply an approved approval request."""
    resp = requests.post(
        f"{BASE_URL}/approval-requests/{approval_request_id}/apply",
        headers={
            "Authorization": api_token,
            "Content-Type": "application/json",
        },
        json={},
    )
    resp.raise_for_status()
    return resp.json() if resp.content else {}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bulk create and apply LaunchDarkly flag approval requests (turn ON)."
    )
    parser.add_argument(
        "--input",
        "-i",
        required=True,
        help="Path to file with flag keys (one per line)",
    )
    parser.add_argument(
        "--project",
        "-p",
        required=True,
        help="LaunchDarkly project key",
    )
    parser.add_argument(
        "--env",
        "-e",
        required=True,
        help="Target environment key (e.g. production)",
    )
    parser.add_argument(
        "--api-token",
        help="LaunchDarkly API token (default: LD_API_TOKEN env var)",
        default=os.environ.get("LD_API_TOKEN"),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log actions without calling the API",
    )
    parser.add_argument(
        "--notify",
        nargs="*",
        default=[],
        help="Member IDs to notify (optional)",
    )
    args = parser.parse_args()

    if requests is None:
        print("Error: 'requests' package required. Install with: pip install requests", file=sys.stderr)
        return 1

    # Phase 1: Load flag keys
    try:
        flag_keys = load_flag_keys(args.input)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if not flag_keys:
        print("Error: No flag keys found in input file.", file=sys.stderr)
        return 1

    print(f"Loaded {len(flag_keys)} flag(s): {', '.join(flag_keys)}")
    print()

    if not args.api_token and not args.dry_run:
        print("Error: LD_API_TOKEN env var or --api-token required.", file=sys.stderr)
        return 1

    api_token = args.api_token or ""

    # Phase 2: Create approval requests
    print("--- Phase 2: Creating approval requests ---")
    approval_requests: list[dict] = []

    for flag_key in flag_keys:
        if args.dry_run:
            print(f"  [DRY-RUN] Would create approval request for: {flag_key}")
            approval_requests.append({
                "flagKey": flag_key,
                "_id": f"dry-run-{flag_key}",
                "_dryRun": True,
            })
            continue

        try:
            result = create_approval_request(
                api_token=api_token,
                project_key=args.project,
                environment_key=args.env,
                flag_key=flag_key,
                notify_member_ids=args.notify or None,
            )
            approval_id = result.get("_id", "?")
            print(f"  Created: {flag_key} -> approval request {approval_id}")
            approval_requests.append({
                "flagKey": flag_key,
                "_id": approval_id,
                **result,
            })
        except requests.exceptions.RequestException as e:
            if hasattr(e, "response") and e.response is not None:
                try:
                    err = e.response.json()
                    msg = err.get("message", err.get("error", str(e)))
                except Exception:
                    msg = str(e)
            else:
                msg = str(e)
            print(f"  [ERROR] {flag_key}: {msg}", file=sys.stderr)
            return 1

    print()
    print(f"Created {len(approval_requests)} approval request(s).")
    print()

    # Human-in-the-loop pause
    print("--- Pause: Waiting for approvals ---")
    if args.dry_run:
        print("  [DRY-RUN] Skipping pause.")
    else:
        input("  Approve the requests in LaunchDarkly, then press Enter to apply them (or Ctrl+C to exit)... ")
    print()

    # Phase 3: Apply approval requests
    print("--- Phase 3: Applying approval requests ---")
    applied = 0
    failed = 0

    for ar in approval_requests:
        approval_id = ar["_id"]
        flag_key = ar.get("flagKey", "?")

        if ar.get("_dryRun"):
            print(f"  [DRY-RUN] Would apply: {flag_key} ({approval_id})")
            applied += 1
            continue

        try:
            apply_approval_request(api_token, approval_id)
            print(f"  Applied: {flag_key} ({approval_id})")
            applied += 1
        except requests.exceptions.RequestException as e:
            if hasattr(e, "response") and e.response is not None:
                try:
                    err = e.response.json()
                    msg = err.get("message", err.get("error", str(e)))
                except Exception:
                    msg = str(e)
            else:
                msg = str(e)
            print(f"  [ERROR] {flag_key}: {msg}", file=sys.stderr)
            failed += 1

    print()
    print(f"Done. Applied: {applied}, Failed: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
