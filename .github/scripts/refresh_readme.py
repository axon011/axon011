#!/usr/bin/env python3
"""Rewrite the auto-generated block in README.md from live GitHub API data.

Replaces everything between <!--AUTO:START--> and <!--AUTO:END--> with a short
"recently shipped" table. Uses GITHUB_TOKEN, so no third-party widget service
sits between a recruiter and the profile rendering.
"""

import os
import re
import sys
import json
import urllib.request
from datetime import datetime, timezone

USER = os.environ.get("GITHUB_REPOSITORY_OWNER", "axon011")
TOKEN = os.environ.get("GITHUB_TOKEN")
README = "README.md"
START, END = "<!--AUTO:START-->", "<!--AUTO:END-->"
SHOW = 5

# Repos that are scaffolding rather than portfolio work.
SKIP = {USER, f"{USER}.github.io", "skills-introduction-to-github"}


def api(path):
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {TOKEN}",
            "User-Agent": f"{USER}-profile-refresh",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def humanize(iso):
    then = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    days = (datetime.now(timezone.utc) - then).days
    if days <= 0:
        return "today"
    if days == 1:
        return "yesterday"
    if days < 30:
        return f"{days}d ago"
    if days < 365:
        return f"{days // 30}mo ago"
    return f"{days // 365}y ago"


def main():
    if not TOKEN:
        sys.exit("GITHUB_TOKEN is not set")

    repos = [
        r
        for r in api(f"/users/{USER}/repos?sort=pushed&per_page=100&type=owner")
        if not r["private"] and not r["fork"] and not r["archived"]
        and r["name"] not in SKIP
    ][:SHOW]

    rows = ["| Repo | What changed | Language | Last push |", "|---|---|---|---|"]
    for r in repos:
        # Split on sentence ends only — a bare "." also matches "Qwen2-0.5B".
        desc = re.split(r"(?<=[a-z])\. ", r["description"] or "—")[0].strip()
        desc = desc.rstrip(".").replace("|", "\\|")
        if len(desc) > 72:
            desc = desc[:71].rstrip() + "…"
        rows.append(
            f"| [`{r['name']}`]({r['html_url']}) | {desc} "
            f"| {r['language'] or '—'} | {humanize(r['pushed_at'])} |"
        )

    stamp = datetime.now(timezone.utc).strftime("%d %b %Y")
    block = "\n".join(rows) + f"\n\n<sub>Refreshed automatically · {stamp}</sub>"

    text = open(README, encoding="utf-8").read()
    new = re.sub(
        rf"{re.escape(START)}.*?{re.escape(END)}",
        f"{START}\n{block}\n{END}",
        text,
        flags=re.S,
    )
    if new == text:
        print("no change")
        return
    open(README, "w", encoding="utf-8").write(new)
    print(f"updated {len(repos)} rows")


if __name__ == "__main__":
    main()
