#!/usr/bin/env python3
"""Erzeugt die animierten Terminal-SVGs fuer das Profil-README.

Aufruf (aus dem Repo-Wurzelverzeichnis):

    python tools/gen_terminal_svg.py

Schreibt die Dateien nach assets/. Keine Abhaengigkeiten ausser der
Standardbibliothek.

Warum SVG und nicht HTML/JS?
    GitHub entfernt aus Markdown-Dateien <script> und <style> sowie
    style-Attribute. Eine SVG-Datei, die per <img> eingebunden wird, ist
    dagegen ein eigenes Dokument - die darin enthaltenen CSS-Keyframes
    laufen normal. Das ist der einzige Weg zu echten Animationen in einem
    GitHub-Profil ohne externen Dienst.

Timing
    Die Szene ist eine Zeitachse der Laenge T. Jedes Element bekommt
    Keyframes in Prozent von T, damit alles synchron bleibt. Die
    Animation laeuft genau einmal und haelt danach den Endzustand
    (forwards) - eine Endlosschleife wuerde die Terminals regelmaessig
    wieder leeren und dauerhaft CPU kosten. Getippt wird ueber eine Clip-Maske, die per
    steps(n) zeichenweise nach rechts wandert - das ist billiger als ein
    Neu-Rendern des Textes pro Zeichen.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

# --- Geometrie -------------------------------------------------------------

FONT_SIZE = 17.0
CHAR_W = FONT_SIZE * 0.6          # Monospace-Vorschub; per textLength erzwungen
LINE_H = FONT_SIZE * 1.45         # aus der Schriftgroesse abgeleitet, damit
                                  # eine Aenderung oben alles mitzieht.
                                  # 1.45 haelt das Zellverhaeltnis nahe an
                                  # einem echten Terminal (~2.1) - bei mehr
                                  # zerfaellt ASCII-Kunst in Einzelstriche.
PAD_X = 30.0
TITLEBAR_H = 36.0
PAD_TOP = TITLEBAR_H + 24.0
PAD_BOTTOM = 22.0
MARGIN = 20.0                     # Rand um das Fenster, damit der Hintergrund
                                  # (Punktraster + Vignette) sichtbar wird

FONT_STACK = ("ui-monospace,'DejaVu Sans Mono','Liberation Mono',"
              "'Courier New',monospace")

# Gemeinsame Hintergrund-Bausteine; gen_chrome_svg.py importiert sie, damit
# Terminals, Banner und Trenner denselben Untergrund haben.
BG_DEFS = """<pattern id="grid" width="19" height="19" patternUnits="userSpaceOnUse">
  <circle cx="1" cy="1" r="1" fill="#ffffff" opacity="0.07"/>
</pattern>
<radialGradient id="vig" cx="50%" cy="34%" r="78%">
  <stop offset="0%" stop-color="#1b1b21"/>
  <stop offset="100%" stop-color="#050506"/>
</radialGradient>
<filter id="shadow" x="-12%" y="-12%" width="124%" height="124%">
  <feDropShadow dx="0" dy="5" stdDeviation="10"
                flood-color="#000000" flood-opacity="0.85"/>
</filter>"""


def bg_rects(ow: float, oh: float, rx: int = 12) -> str:
    """Vignette plus Punktraster als Untergrund einer Grafik."""
    return (f'<rect width="{ow:.0f}" height="{oh:.0f}" rx="{rx}" fill="url(#vig)"/>\n'
            f'<rect width="{ow:.0f}" height="{oh:.0f}" rx="{rx}" fill="url(#grid)"/>')

# --- Zeiten (Sekunden) -----------------------------------------------------

TYPE_PER_CHAR = 0.055
ENTER_PAUSE = 0.35
OUT_STAGGER = 0.11
LEAD_IN = 0.7
TAIL_HOLD = 1.0

PROMPT = "user@github:~$ "


@dataclass
class Step:
    """Ein Kommando samt Ausgabe."""
    cmd: str
    out: list[str] = field(default_factory=list)
    pause: float = 0.9
    prompt: str = PROMPT


@dataclass
class Scene:
    name: str
    title: str
    steps: list[Step]
    cols: int | None = None       # None -> aus dem laengsten Text ableiten
    trailing_prompt: bool = True


def esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;"))


def pct(t: float, total: float) -> str:
    """Zeitpunkt in Prozent der Gesamtschleife, auf 3 Stellen gerundet."""
    return f"{max(0.0, min(100.0, t / total * 100.0)):.3f}"


def build(scene: Scene) -> str:
    # ---- Zeitachse ------------------------------------------------------
    t = LEAD_IN
    plan = []                      # (step, t_start, t_typed, [(line, t_show)])
    for st in scene.steps:
        t_start = t
        t_typed = t_start + len(st.cmd) * TYPE_PER_CHAR
        t = t_typed + ENTER_PAUSE
        outs = []
        for line in st.out:
            outs.append((line, t))
            t += OUT_STAGGER
        t += st.pause
        plan.append((st, t_start, t_typed, outs))

    t_end = t
    total = t_end + TAIL_HOLD

    # ---- Layout ---------------------------------------------------------
    rows = 0
    widest = 0
    for st, _, _, outs in plan:
        widest = max(widest, len(st.prompt) + len(st.cmd) + 1)
        rows += 1
        for line, _ in outs:
            widest = max(widest, len(line))
            rows += 1
    if scene.trailing_prompt:
        rows += 1
        widest = max(widest, len(PROMPT) + 1)

    cols = scene.cols or widest
    width = round(PAD_X * 2 + cols * CHAR_W)
    height = round(PAD_TOP + rows * LINE_H + PAD_BOTTOM)

    css: list[str] = []
    body: list[str] = []
    defs: list[str] = []

    row = 0
    for i, (st, t_start, t_typed, outs) in enumerate(plan):
        y = PAD_TOP + row * LINE_H
        row += 1

        px = PAD_X
        cx = px + len(st.prompt) * CHAR_W
        cw = len(st.cmd) * CHAR_W

        # Die Gruppe erscheint, sobald das Kommando an der Reihe ist.
        a = pct(t_start, total)
        css.append(
            f"@keyframes ap{i}{{0%,{a}%{{opacity:0}}"
            f"{pct(t_start + 0.001, total)}%,100%{{opacity:1}}}}"
        )
        css.append(f".ap{i}{{opacity:0;animation:ap{i} {total:.2f}s linear 1 forwards}}")

        # Tippen: Clip-Rechteck faehrt zeichenweise nach rechts.
        n = max(1, len(st.cmd))
        css.append(
            f"@keyframes tp{i}{{0%,{a}%{{transform:translateX(-{cw:.1f}px)}}"
            f"{pct(t_typed, total)}%,100%{{transform:translateX(0)}}}}"
        )
        css.append(
            f".tp{i}{{animation:tp{i} {total:.2f}s steps({n}) 1 forwards}}"
        )
        defs.append(
            f'<clipPath id="clip{i}">'
            f'<rect class="tp{i}" x="{cx:.1f}" y="{y - FONT_SIZE:.1f}" '
            f'width="{cw:.1f}" height="{LINE_H:.1f}"/></clipPath>'
        )

        # Cursor: waehrend des Tippens sichtbar, wandert mit.
        css.append(
            f"@keyframes cw{i}{{0%,{a}%{{opacity:0}}"
            f"{pct(t_start + 0.001, total)}%,{pct(t_typed + ENTER_PAUSE, total)}%"
            f"{{opacity:1}}{pct(t_typed + ENTER_PAUSE + 0.001, total)}%,100%"
            f"{{opacity:0}}}}"
        )
        css.append(f".cw{i}{{opacity:0;animation:cw{i} {total:.2f}s linear 1 forwards}}")
        css.append(
            f"@keyframes cm{i}{{0%,{a}%{{transform:translateX(0)}}"
            f"{pct(t_typed, total)}%,100%{{transform:translateX({cw:.1f}px)}}}}"
        )
        css.append(f".cm{i}{{animation:cm{i} {total:.2f}s steps({n}) 1 forwards}}")

        body.append(f'<g class="ap{i}">')
        body.append(
            f'<text class="dim" x="{px:.1f}" y="{y:.1f}" '
            f'textLength="{len(st.prompt) * CHAR_W:.1f}" lengthAdjust="spacing">'
            f'{esc(st.prompt)}</text>'
        )
        body.append(
            f'<g clip-path="url(#clip{i})">'
            f'<text class="cmd" x="{cx:.1f}" y="{y:.1f}" '
            f'textLength="{cw:.1f}" lengthAdjust="spacing">{esc(st.cmd)}</text></g>'
        )
        body.append(
            f'<g class="cw{i} cur"><g class="cm{i}">'
            f'<rect class="blink" x="{cx:.1f}" y="{y - FONT_SIZE + 2:.1f}" '
            f'width="{CHAR_W:.1f}" height="{FONT_SIZE:.1f}"/></g></g>'
        )
        body.append("</g>")

        for j, (line, t_show) in enumerate(outs):
            oy = PAD_TOP + row * LINE_H
            row += 1
            cls = f"o{i}_{j}"
            css.append(
                f"@keyframes {cls}{{0%,{pct(t_show, total)}%{{opacity:0}}"
                f"{pct(t_show + 0.001, total)}%,100%{{opacity:1}}}}"
            )
            css.append(
                f".{cls}{{opacity:0;animation:{cls} {total:.2f}s linear 1 forwards}}"
            )
            body.append(
                f'<text class="out {cls}" x="{PAD_X:.1f}" y="{oy:.1f}" '
                f'textLength="{max(1, len(line)) * CHAR_W:.1f}" '
                f'lengthAdjust="spacing">{esc(line) or " "}</text>'
            )

    if scene.trailing_prompt:
        y = PAD_TOP + row * LINE_H
        a = pct(t_end, total)
        css.append(
            f"@keyframes fin{{0%,{a}%{{opacity:0}}"
            f"{pct(t_end + 0.001, total)}%,100%{{opacity:1}}}}"
        )
        css.append(f".fin{{opacity:0;animation:fin {total:.2f}s linear 1 forwards}}")
        body.append('<g class="fin">')
        body.append(
            f'<text class="dim" x="{PAD_X:.1f}" y="{y:.1f}" '
            f'textLength="{len(PROMPT) * CHAR_W:.1f}" lengthAdjust="spacing">'
            f'{esc(PROMPT)}</text>'
        )
        body.append(
            f'<rect class="blink" x="{PAD_X + len(PROMPT) * CHAR_W:.1f}" '
            f'y="{y - FONT_SIZE + 2:.1f}" width="{CHAR_W:.1f}" '
            f'height="{FONT_SIZE:.1f}"/>'
        )
        body.append("</g>")

    # ---- Rahmen ---------------------------------------------------------
    dots = "".join(
        f'<rect x="{20 + k * 16}" y="15" width="7" height="7" '
        f'fill="none" stroke="#4a4a4a" stroke-width="1"/>'
        for k in range(3)
    )
    title = esc(scene.title)
    title_x = width / 2

    static_css = f"""
  text{{font-family:{FONT_STACK};font-size:{FONT_SIZE}px;
    dominant-baseline:auto;white-space:pre}}
  .cmd{{fill:#f2f2f2}}
  .out{{fill:#a8a8a8}}
  .dim{{fill:#6f6f6f}}
  .ttl{{fill:#7a7a7a;font-size:13px;letter-spacing:1px}}
  .blink{{fill:#f2f2f2;animation:bl 1.06s steps(1) infinite}}
  @keyframes bl{{0%,49%{{opacity:1}}50%,100%{{opacity:0}}}}
  @media (prefers-reduced-motion:reduce){{
    *{{animation:none!important}}
    g,text{{opacity:1!important}}
    .cur{{opacity:0!important}}
  }}
"""

    # Aussenmasse inklusive Rand; das Fenster selbst wird hineinverschoben.
    ow = round(width + 2 * MARGIN)
    oh = round(height + 2 * MARGIN)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{ow}" height="{oh}"
     viewBox="0 0 {ow} {oh}" role="img"
     aria-label="{title} - animiertes Terminal">
<title>{title}</title>
<defs>
<pattern id="scan" width="1" height="3" patternUnits="userSpaceOnUse">
  <rect width="1" height="1" fill="#ffffff" opacity="0.045"/>
</pattern>
{BG_DEFS}
<clipPath id="win">
  <rect width="{width}" height="{height}" rx="8"/>
</clipPath>
{chr(10).join(defs)}
</defs>
<style>{static_css}{chr(10).join('  ' + c for c in css)}
</style>
{bg_rects(ow, oh)}
<g transform="translate({MARGIN:.0f},{MARGIN:.0f})">
  <rect width="{width}" height="{height}" rx="8" fill="#000000" filter="url(#shadow)"/>
  <g clip-path="url(#win)">
    <rect width="{width}" height="{TITLEBAR_H}" fill="#0e0e12"/>
    <rect y="{TITLEBAR_H}" width="{width}" height="{height - TITLEBAR_H}"
          fill="url(#scan)"/>
  </g>
  <line x1="1" y1="{TITLEBAR_H}" x2="{width - 1}" y2="{TITLEBAR_H}" stroke="#2b2b32"/>
  {dots}
  <text class="ttl" x="{title_x}" y="{23}" text-anchor="middle">{title}</text>
{chr(10).join(body)}
  <rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="8"
        fill="none" stroke="#33333a"/>
</g>
</svg>
"""


SCENES = [
    Scene(
        name="header",
        cols=64,
        title="l4rp@github: ~",
        steps=[
            Step("whoami", ["L4RP"]),
            Step("sudo install opsec", [
                "[sudo] password for l4rp: ********",
                "Reading package lists... done",
                "Unpacking opsec (4.0.1) ...",
                "OPSEC installed successfully.",
            ], pause=1.0),
            Step("./status.sh", [
                "SYSTEM STATUS : ONLINE",
                "OPSEC         : ENABLED",
                "GIT           : CLEAN",
                "SHELL         : /bin/bash",
                "LOCATION      : localhost",
            ], pause=1.4),
        ],
    ),
    Scene(
        name="stack",
        cols=64,
        title="l4rp@github: ~/stack",
        steps=[
            # Arch-Logo als ASCII, Infospalte ab Spalte 20.
            # Raw-Strings, sonst liest Python "\ " als ungueltige
            # Escape-Sequenz (heute nur eine Warnung, kuenftig ein Fehler).
            Step("neofetch", [
                r"       /\           l4rp@localhost",
                r"      /  \          ---------------------------",
                r"     /\   \         os     : Arch Linux x86_64",
                r"    /      \        kernel : 6.11.5-arch1-1",
                r"   /   ,,   \       shell  : bash 5.2.37",
                r"  /   |  |  -\      lang   : Python, Shell, Batch",
                r" /_-''    ''-_\     wm     : i3 + too many keybinds",
                r"                    uptime : 9999 days, 4 mins",
            ], pause=1.4),
            Step("grep -ri \"L4RP\" /etc/", [
                "/etc/hostname:L4RP",
                "/etc/motd:welcome back, L4RP",
                "/etc/shadow:permission denied (nice try)",
            ], pause=1.2),
        ],
    ),
    Scene(
        name="services",
        cols=64,
        title="l4rp@github: ~/systemd",
        steps=[
            Step("systemctl status motivation", [
                "* motivation.service - Motivation Daemon",
                "     Active: active (running) since Mon 04:12:07",
                "     Memory: 2.1G (mostly coffee)",
            ], pause=1.1),
            Step("systemctl status hypergamie", [
                "* hypergamie.service - Hypergamie Daemon",
                "     Loaded: loaded (/etc/systemd/system/hypergamie.service)",
                "     Active: active (running) since forever",
                "     Status: \"mask failed: unit is load-bearing\"",
            ], pause=1.2),
            Step("sudo rm -rf /doubt", [
                "rm: cannot remove '/doubt': Device or resource busy",
            ], pause=1.1),
        ],
    ),
    Scene(
        name="lonely",
        cols=64,
        title="l4rp@github: ~/lonely",
        steps=[
            Step("find / -name girlfriend 2>/dev/null", [
                "find: no matches in 4 filesystems",
                "  reason : hypergamie.service holds all open references",
                "  retry  : not scheduled",
            ], pause=1.3),
            # "Note: selecting X instead of Y" ist echte apt-Ausgabe - dadurch
            # wirkt die Paketvertauschung wie ein Systemverhalten, nicht wie
            # ein hingeschriebener Witz.
            Step("sudo apt install being-funny", [
                "Note: selecting 'looksmaxxing' instead of 'being-funny'",
                "Setting up jawline (2.0) ... done",
                "Setting up filler (1.5ml) ... done",
                "Setting up height-booster (5cm) ... done",
                "Personality: unchanged. 0 upgraded, 3 newly installed.",
            ], pause=1.2),
        ],
    ),
    Scene(
        name="review",
        cols=64,
        title="l4rp@github: ~/easy-arch-linux",
        steps=[
            # Aufbau einer echten abgelehnten Push-Ausgabe: erst der
            # Upload, dann die Meldungen des Hooks mit "remote:"-Praefix,
            # dann die Ref-Zeile und der Fehler. Genau in der Reihenfolge
            # kennt man das von Git.
            Step("git push origin main", [
                "Enumerating objects: 47, done.",
                "Writing objects: 100% (31/31), 4.21 KiB, done.",
                "remote: error: pre-receive hook declined",
                "remote:",
                "remote:   verdict ......... the code is ass",
                "remote:   suggestion ...... start over",
                "remote:",
                "To github.com:Peter362187/Easy-Arch-Linux.git",
                " ! [remote rejected] main -> main (hook declined)",
                "error: failed to push some refs",
            ], pause=1.5),
            Step("git push --force origin main", [
                "remote: error: no.",
            ], pause=1.3),
        ],
    ),
    Scene(
        name="wsl",
        cols=64,
        # Zeigt, dass das Projekt auch unter Windows laeuft - und ist
        # gleichzeitig der Witz, Arch aus einer PowerShell heraus zu starten.
        title="PS C:\\Users\\l4rp",
        steps=[
            Step("wsl --list --verbose", [
                "  NAME            STATE           VERSION",
                "* Arch            Running         2",
                "  Ubuntu          Stopped         2",
                "  docker-desktop  Stopped         2",
            ], prompt="PS C:\\Users\\l4rp> ", pause=1.2),
            Step("wsl -d Arch", [], prompt="PS C:\\Users\\l4rp> ", pause=0.7),
            Step("head -1 /etc/os-release", ["NAME=\"Arch Linux\""], pause=1.0),
            Step("echo \"windows was just the bootloader\"", [
                "windows was just the bootloader",
            ], pause=1.3),
        ],
    ),
]


def main() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(os.path.dirname(here), "assets")
    os.makedirs(out_dir, exist_ok=True)
    for scene in SCENES:
        path = os.path.join(out_dir, f"{scene.name}.svg")
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(build(scene))
        print(f"{path}  ({os.path.getsize(path)} bytes)")


if __name__ == "__main__":
    main()
