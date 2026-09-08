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
import textwrap
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


def repo_lines() -> tuple[list[str], list[str]]:
    """Ausgabe fuer das Projekt-Panel, im Stil von `gh repo list/view`."""
    # Das Profil-Repo heisst wie der Benutzer und enthaelt nur dieses
    # README - es ist kein Projekt und gehoert nicht in die Liste.
    repos = [r for r in api(f"/users/{USER}/repos?per_page=100&sort=updated")
             if not r["fork"] and r["name"].lower() != USER.lower()]

    listing = [f"{'NAME':<22}{'LANG':<10}{'STARS':>6}  {'UPDATED':<10}"]
    for r in repos[:6]:
        listing.append(
            f"{r['name'][:21]:<22}{(r['language'] or '-')[:9]:<10}"
            f"{r['stargazers_count']:>6}  {r['updated_at'][:10]:<10}"
        )

    detail: list[str] = []
    if repos:
        top = max(repos, key=lambda r: (r["stargazers_count"], r["updated_at"]))
        detail.append(f"{USER}/{top['name']}")
        desc = (top.get("description") or "").replace("—", "-")
        # Breite 56: plus 2 Zeichen Einzug und " ..." bleibt die Zeile
        # unter den 64 Spalten des Panels.
        wrapped = textwrap.wrap(desc, width=56)
        # Lieber sichtbar kuerzen als mitten im Satz abschneiden.
        if len(wrapped) > 3:
            wrapped = wrapped[:3]
            wrapped[-1] = wrapped[-1].rstrip(" ,.;:") + " ..."
        for line in wrapped:
            detail.append(f"  {line}")
        topics = " ".join(top.get("topics") or [])
        if topics:
            for i, line in enumerate(textwrap.wrap(topics, width=52)[:2]):
                detail.append(f"  {'topics:' if i == 0 else '       '} {line}")
        detail.append(f"  homepage: github.com/{USER}/{top['name']}")
    return listing, detail


def main() -> None:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_stats = os.path.join(root, "assets", "stats.svg")
    out_repos = os.path.join(root, "assets", "payloads.svg")
    try:
        account, langs = collect()
        listing, detail = repo_lines()
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        if os.path.exists(out_stats) and os.path.exists(out_repos):
            print(f"GitHub-API nicht erreichbar ({exc}) - bestehende "
                  f"Dateien bleiben unveraendert.", file=sys.stderr)
            return
        print(f"GitHub-API nicht erreichbar ({exc}) und keine vorhandenen "
              f"Dateien - Abbruch.", file=sys.stderr)
        raise SystemExit(1)

    scenes = [
        (out_stats, Scene(
            name="stats",
            title="l4rp@github: ~/stats",
            cols=64,
            steps=[
                Step("gh api users/l4rp --jq .", account, pause=1.0),
                Step("cloc --by-lang .", langs, pause=1.2),
            ],
        )),
        (out_repos, Scene(
            name="payloads",
            title="l4rp@github: ~/payloads",
            cols=64,
            steps=[
                Step("gh repo list", listing, pause=1.2),
                Step("gh repo view --json name,description,topics",
                     detail, pause=1.4),
            ],
        )),
    ]
    os.makedirs(os.path.join(root, "assets"), exist_ok=True)
    for path, scene in scenes:
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(build(scene))
        print(f"{path}  ({os.path.getsize(path)} bytes)")


if __name__ == "__main__":
    main()
