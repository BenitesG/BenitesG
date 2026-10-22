#!/usr/bin/env python3
"""
Regenerates the "Recent repositories" block of the profile README.

WHY ONLY THIS BLOCK: the API returns name, description, language and topics.
It does not return the reason a project is worth reading. The featured
projects stay hand-written above; what gets automated is the part that is
mechanical - the list, and keeping it in the right order.

The script rewrites only what sits between the markers. Everything outside
them is untouched, so editing the README by hand never fights the workflow.
"""

import json
import os
import re
import sys
import urllib.request

USER = os.environ.get("GH_USER", "BenitesG")
README = os.environ.get("README_PATH", "README.md")
MAX_REPOS = int(os.environ.get("MAX_REPOS", "6"))

START = "<!--START_SECTION:repos-->"
END = "<!--END_SECTION:repos-->"

# Repositories that must never show up in the list: the profile repository
# itself (it is the README, not a project) and anything explicitly excluded.
SKIP = {USER.lower(), f"{USER.lower()}.github.io"}


def fetch_repos():
    url = f"https://api.github.com/users/{USER}/repos?per_page=100&sort=updated"
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{USER}-profile-readme",
    })
    # GITHUB_TOKEN raises the rate limit from 60/h to 5000/h. The workflow
    # provides it; running locally without one still works.
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def pick(repos):
    out = []
    for r in repos:
        if r.get("fork") or r.get("archived") or r.get("private"):
            continue
        if r["name"].lower() in SKIP:
            continue
        out.append(r)
    return out[:MAX_REPOS]


def render(repos):
    if not repos:
        return "_Nothing public yet._"
    lines = ["| Repository | What it is | Stack |", "|---|---|---|"]
    for r in repos:
        name = r["name"]
        link = f"[{name}]({r['html_url']})"
        desc = (r.get("description") or "—").replace("|", "\\|")
        if len(desc) > 110:
            desc = desc[:107].rstrip() + "..."
        topics = r.get("topics") or []
        stack = ", ".join(topics[:4]) if topics else (r.get("language") or "—")
        lines.append(f"| {link} | {desc} | {stack} |")
    return "\n".join(lines)


def main():
    with open(README, encoding="utf-8") as f:
        text = f.read()

    if START not in text or END not in text:
        print(f"markers not found in {README}", file=sys.stderr)
        return 1

    block = render(pick(fetch_repos()))
    new = re.sub(
        re.escape(START) + r".*?" + re.escape(END),
        f"{START}\n{block}\n{END}",
        text,
        flags=re.S,
    )

    if new == text:
        print("no changes")
        return 0

    with open(README, "w", encoding="utf-8", newline="\n") as f:
        f.write(new)
    print("README updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
