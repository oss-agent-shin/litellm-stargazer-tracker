#!/usr/bin/env python3
"""Sync stargazers from BerriAI/litellm-agent-platform that have a LinkedIn URL on their GitHub profile.

Run in GitHub Actions; uses GITHUB_TOKEN from the workflow.
"""
from __future__ import annotations

import csv
import json
import os
import re
import sys
import time
from pathlib import Path

import requests

REPO = "BerriAI/litellm-agent-platform"
ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "stargazers.csv"
SEEN_PATH = ROOT / "seen.json"
CSV_COLUMNS = ["login", "name", "linkedin_url", "profile_url", "starred_at", "source"]
LINKEDIN_RE = re.compile(
    r"https?://(?:[a-z]{2,3}\.)?linkedin\.com/(?:in|pub|company)/[A-Za-z0-9\-_%./]+",
    re.IGNORECASE,
)

GH_TOKEN = os.environ.get("GITHUB_TOKEN")
if not GH_TOKEN:
    print("GITHUB_TOKEN not set", file=sys.stderr)
    sys.exit(1)

SESSION = requests.Session()
SESSION.headers.update(
    {
        "Authorization": f"Bearer {GH_TOKEN}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "litellm-stargazer-tracker",
    }
)


def gh_get(url, accept="application/vnd.github+json", params=None):
    for attempt in range(5):
        r = SESSION.get(url, headers={"Accept": accept}, params=params or {})
        if r.status_code == 403 and (
            "rate limit" in r.text.lower() or r.headers.get("X-RateLimit-Remaining") == "0"
        ):
            reset = int(r.headers.get("X-RateLimit-Reset", "0"))
            wait = max(0, reset - int(time.time())) + 5
            print(f"Rate limited; sleeping {wait}s", file=sys.stderr)
            time.sleep(wait)
            continue
        if r.status_code >= 500:
            time.sleep(2 ** attempt)
            continue
        r.raise_for_status()
        return r
    r.raise_for_status()
    return r


def iter_stargazers():
    page = 1
    while True:
        r = gh_get(
            f"https://api.github.com/repos/{REPO}/stargazers",
            accept="application/vnd.github.star+json",
            params={"per_page": 100, "page": page},
        )
        items = r.json()
        if not items:
            return
        for it in items:
            user = it.get("user") or {}
            login = user.get("login")
            if login:
                yield {"login": login, "starred_at": it.get("starred_at")}
        if len(items) < 100:
            return
        page += 1


def extract_linkedin(text):
    if not text:
        return None
    m = LINKEDIN_RE.search(text)
    return m.group(0).rstrip("/.,);") if m else None


def profile_for(login):
    return gh_get(f"https://api.github.com/users/{login}").json()


def find_linkedin(login):
    """Return (linkedin_url, name, profile_url, source) or (None, name, profile_url, None)."""
    try:
        accts = gh_get(f"https://api.github.com/users/{login}/social_accounts").json()
    except requests.HTTPError:
        accts = []
    for acct in accts:
        if acct.get("provider") == "linkedin" and acct.get("url"):
            p = profile_for(login)
            return acct["url"], p.get("name"), p.get("html_url"), "social_accounts"

    p = profile_for(login)
    for field_name in ("blog", "bio"):
        url = extract_linkedin(p.get(field_name))
        if url:
            return url, p.get("name"), p.get("html_url"), field_name

    return None, p.get("name"), p.get("html_url"), None


def load_seen():
    if SEEN_PATH.exists():
        try:
            return json.loads(SEEN_PATH.read_text() or "{}")
        except json.JSONDecodeError:
            return {}
    return {}


def load_csv():
    if not CSV_PATH.exists():
        return []
    with CSV_PATH.open(newline="") as f:
        return list(csv.DictReader(f))


def write_csv(rows):
    rows = sorted(rows, key=lambda r: r.get("starred_at") or "", reverse=True)
    with CSV_PATH.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") or "" for k in CSV_COLUMNS})


def main():
    seen = load_seen()
    existing = {r["login"]: r for r in load_csv() if r.get("login")}

    checked = 0
    added = 0
    for star in iter_stargazers():
        login = star["login"]
        starred_at = star["starred_at"]

        if login in seen:
            if login in existing and starred_at:
                existing[login]["starred_at"] = starred_at
            continue

        checked += 1
        try:
            url, name, profile_url, source = find_linkedin(login)
        except requests.HTTPError as e:
            print(f"  ! {login}: HTTP {e.response.status_code}; skipping this run", file=sys.stderr)
            continue

        seen[login] = {"has_linkedin": bool(url), "checked_at": int(time.time())}

        if url:
            existing[login] = {
                "login": login,
                "name": name or "",
                "linkedin_url": url,
                "profile_url": profile_url or f"https://github.com/{login}",
                "starred_at": starred_at or "",
                "source": source or "",
            }
            added += 1
            print(f"  + {login} -> {url} ({source})")

    write_csv(list(existing.values()))
    SEEN_PATH.write_text(json.dumps(seen, indent=2, sort_keys=True) + "\n")

    print(f"\nDone. Checked {checked} new stargazers; {added} with LinkedIn; total tracked: {len(existing)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
