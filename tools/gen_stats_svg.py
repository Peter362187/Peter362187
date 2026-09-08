#!/usr/bin/env python3
"""Erzeugt assets/stats.svg aus echten GitHub-Daten.

    python tools/gen_stats_svg.py

Warum nicht github-readme-stats o. ae.?
    Solche Dienste sind eine externe Abhaengigkeit, die jederzeit
    ausfallen kann - beim Bau dieses Profils war der bekannteste davon
    nicht erreichbar und haette ein kaputtes Bild im README hinterlassen.
    Hier werden die Zahlen einmal geholt und als statisches SVG abgelegt;
    der Workflow in .github/workflows/refresh-stats.yml haelt sie aktuell.

Ohne Netzwerk (oder bei API-Fehlern) bleibt eine vorhandene stats.svg
unveraendert stehen, statt sie durch Platzhalter zu ersetzen.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

from gen_terminal_svg import Scene, Step, build

USER = "Peter362187"
API = "https://api.github.com"


def api(path: str):
    req = urllib.request.Request(
        f"{API}{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"{USER}-profile-readme",
        },
    )
    # In Actions steht ein Token bereit -> hoeheres Rate-Limit.
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=20) as fh:
        return json.load(fh)


def human(n: int) -> str:
    return f"{n:,}".replace(",", " ")


def collect() -> tuple[list[str], list[str]]:
    user = api(f"/users/{USER}")
    repos = [r for r in api(f"/users/{USER}/repos?per_page=100&sort=updated")
             if not r["fork"]]

    stars = sum(r["stargazers_count"] for r in repos)
    forks = sum(r["forks_count"] for r in repos)

    totals: dict[str, int] = {}
    for r in repos:
        try:
            for lang, size in api(f"/repos/{USER}/{r['name']}/languages").items():
                totals[lang] = totals.get(lang, 0) + size
        except urllib.error.HTTPError:
            continue

    grand = sum(totals.values()) or 1
    ranked = sorted(totals.items(), key=lambda kv: -kv[1])[:5]

    account = [
        f"user        : {USER}",
        f"member since: {user['created_at'][:10]}",
        f"repos       : {user['public_repos']}   followers: {user['followers']}",
        f"stars       : {stars}   forks: {forks}",
    ]

    langs = []
    for name, size in ranked:
        share = size / grand * 100
        bar = "#" * max(1, round(share / 5)) + "." * (20 - max(1, round(share / 5)))
        langs.append(f"{name[:10]:<10} [{bar}] {share:5.1f}%  {human(size)} B")
    return account, langs


def main() -> None:
    out = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "assets", "stats.svg")
    try:
        account, langs = collect()
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        if os.path.exists(out):
            print(f"GitHub-API nicht erreichbar ({exc}) - bestehende "
                  f"stats.svg bleibt unveraendert.", file=sys.stderr)
            return
        print(f"GitHub-API nicht erreichbar ({exc}) und keine vorhandene "
              f"stats.svg - Abbruch.", file=sys.stderr)
        raise SystemExit(1)

    scene = Scene(
        name="stats",
        title=f"l4rp@github: ~/stats",
        cols=64,
        steps=[
            Step("gh api users/l4rp --jq .", account, pause=1.0),
            Step("cloc --by-lang .", langs, pause=1.2),
        ],
    )
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(build(scene))
    print(f"{out}  ({os.path.getsize(out)} bytes)")


if __name__ == "__main__":
    main()
