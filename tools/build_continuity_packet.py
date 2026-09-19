#!/usr/bin/env python3
"""Build a compact provider-independent MULTIVERSE recovery packet.

Dependency-free; uses only the Python standard library. It reads public GitHub
surfaces so it can be run outside ChatGPT by another AI/operator.

Usage:
  python tools/build_continuity_packet.py
  python tools/build_continuity_packet.py --out CONTINUITY_PACKET.md

An optional GITHUB_TOKEN may be supplied through the environment to improve
API rate limits. The token is never written to the generated packet.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.request

REPO = "fufufu1116/multiverse-research"
API = f"https://api.github.com/repos/{REPO}"
CONTROL_ISSUE = 394
IMPLEMENTATION_ISSUE = 596
DESIGN_PR = 595
ACTIVE_CANDIDATE_PR = 597


def get(path: str):
    req = urllib.request.Request(
        API + path,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "multiverse-continuity-packet/1.1",
        },
    )
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.load(response)


def short(value, n=160):
    value = " ".join(str(value or "").split())
    return value if len(value) <= n else value[: n - 1] + "…"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="CONTINUITY_PACKET.md")
    args = parser.parse_args()

    try:
        branch = get("/branches/main")
        control = get(f"/issues/{CONTROL_ISSUE}")
        implementation = get(f"/issues/{IMPLEMENTATION_ISSUE}")
        design = get(f"/pulls/{DESIGN_PR}")
        candidate = get(f"/pulls/{ACTIVE_CANDIDATE_PR}")
        commits = get("/commits?per_page=8")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"Fresh Read failed: {exc}", file=sys.stderr)
        return 2

    sha = branch["commit"]["sha"]
    generated = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")

    lines = [
        "# MULTIVERSE Compact Continuity Packet",
        "",
        "> BOOTSTRAP ONLY. This packet is not authority. Fresh Read canonical GitHub surfaces before consequential work.",
        "> If this packet conflicts with Fresh Read, the Fresh Read wins and this packet must be regenerated.",
        "",
        f"- Generated: `{generated}`",
        f"- Repository: `{REPO}`",
        "- Canonical branch: `main`",
        f"- Observed main SHA: `{sha}`",
        "- Runtime: `OFF`",
        "",
        "## Canonical pointers",
        f"- Control ledger: [#{CONTROL_ISSUE}]({control['html_url']}) — {short(control['title'])}",
        f"- Continuity implementation: [#{IMPLEMENTATION_ISSUE}]({implementation['html_url']}) — {short(implementation['title'])}",
        f"- Lightweight Protocol design: [PR #{DESIGN_PR}]({design['html_url']}) — {short(design['title'])}",
        f"- Active continuity candidate: [PR #{ACTIVE_CANDIDATE_PR}]({candidate['html_url']}) — {short(candidate['title'])}",
        "",
        "## Fresh control state",
        f"- Control issue state: `{control['state']}`; updated `{control.get('updated_at')}`",
        f"- Continuity issue state: `{implementation['state']}`; updated `{implementation.get('updated_at')}`",
        f"- Lightweight Protocol candidate: `{design['state']}` / draft=`{design.get('draft')}` / merged=`{design.get('merged')}`",
        f"- Active continuity candidate: `{candidate['state']}` / draft=`{candidate.get('draft')}` / merged=`{candidate.get('merged')}`",
        f"- Candidate base SHA: `{candidate.get('base_sha')}`",
        f"- Candidate head SHA: `{candidate.get('head_sha')}`",
        "",
        "## Recent canonical commits",
    ]
    for commit in commits[:8]:
        lines.append(f"- `{commit['sha'][:12]}` {short(commit['commit']['message'], 140)}")

    lines += [
        "",
        "## Current task",
        "- Maintain provider-independent continuity so ChatGPT limits/interruption do not become project-state loss.",
        "- Keep the durable state external, compact, Fresh-readable, and provider-neutral.",
        "- Current candidate work: continuity protocol, manifest, startup guide, packet generator, and provider-neutral adapter contract.",
        "",
        "## Resume procedure",
        "1. Fresh Read `main` and the canonical pointers above.",
        "2. Compare the observed main SHA with this packet; the packet is navigation, not authority.",
        "3. Inspect the active candidate and canonical issue state before deciding what remains uncommitted.",
        "4. Reconstruct the first uncommitted step from canonical evidence.",
        "5. Check Owner Gates and existing authority boundaries.",
        "6. Continue only within existing authority.",
        "7. Before any consequential one-shot/external effect, persist intent/checkpoint and verify downstream state after execution.",
        "",
        "## Side-effect safety",
        "- Provider statuses such as `SUCCESS`, `PUBLISHED`, `SENT`, or `DEPLOYED` are not by themselves downstream-effect proof.",
        "- If side-effect state is uncertain, classify it `UNVERIFIED`, Fresh Read, and do not blindly retry.",
        "- Never place credentials, tokens, private keys, cookies, or secrets in this packet.",
        "",
        "## Provider handoff",
        "Any compatible AI (including Gemini) may use this packet as a bootstrap. The replacement AI is an executor, not canonical authority. It must perform Fresh Read before action and may not infer authority from the packet.",
        "",
        "## Known boundary",
        "This protocol does not bypass ChatGPT free-tier or context limits. It makes those limits survivable by externalizing state and enabling deterministic handoff. Automatic provider switching requires separately authorized runtime/credential infrastructure and is not enabled here.",
        "",
    ]

    with open(args.out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(args.out)
    print(f"main_sha={sha}")
    print(f"generated={generated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
