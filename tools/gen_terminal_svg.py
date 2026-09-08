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

FONT_SIZE = 15.0
CHAR_W = FONT_SIZE * 0.6          # Monospace-Vorschub; per textLength erzwungen
LINE_H = 24.0
PAD_X = 26.0
TITLEBAR_H = 34.0
PAD_TOP = TITLEBAR_H + 22.0
PAD_BOTTOM = 20.0

FONT_STACK = ("ui-monospace,'DejaVu Sans Mono','Liberation Mono',"
              "'Courier New',monospace")

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
        f'<rect x="{18 + k * 15}" y="14" width="7" height="7" '
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
  .ttl{{fill:#7a7a7a;font-size:12px;letter-spacing:1px}}
  .blink{{fill:#f2f2f2;animation:bl 1.06s steps(1) infinite}}
  @keyframes bl{{0%,49%{{opacity:1}}50%,100%{{opacity:0}}}}
  @media (prefers-reduced-motion:reduce){{
    *{{animation:none!important}}
    g,text{{opacity:1!important}}
    .cur{{opacity:0!important}}
  }}
"""

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}"
     viewBox="0 0 {width} {height}" role="img"
     aria-label="{title} - animiertes Terminal">
<title>{title}</title>
<defs>
<pattern id="scan" width="1" height="3" patternUnits="userSpaceOnUse">
  <rect width="1" height="1" fill="#ffffff" opacity="0.045"/>
</pattern>
{chr(10).join(defs)}
</defs>
<style>{static_css}{chr(10).join('  ' + c for c in css)}
</style>
<rect width="{width}" height="{height}" rx="7" fill="#000000"/>
<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="7"
      fill="none" stroke="#303030"/>
<rect x="1" y="{TITLEBAR_H}" width="{width - 2}" height="{height - TITLEBAR_H - 1}"
      fill="url(#scan)"/>
<line x1="1" y1="{TITLEBAR_H}" x2="{width - 1}" y2="{TITLEBAR_H}" stroke="#262626"/>
{dots}
<text class="ttl" x="{title_x}" y="{22}" text-anchor="middle">{title}</text>
{chr(10).join(body)}
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
            Step("neofetch --stdout", [
                "os      : Arch Linux x86_64  (btw)",
                "shell   : bash 5.2.37",
                "lang    : Python, Shell, Batch",
                "editor  : whichever opens first",
                "wm      : i3 + too many keybinds",
                "uptime  : 9999 days, 4 mins",
            ], pause=1.3),
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
        name="build",
        cols=64,
        title="l4rp@github: ~/easy-arch-linux",
        steps=[
            Step("./build-iso.sh --profile desktop", [
                "[*] resolving packages ................ ok",
                "[*] building squashfs ................. ok",
                "[################################] 100%",
                "iso ready -> easy-arch-2026.09-x86_64.iso",
            ], pause=1.2),
            Step("git push origin main", [
                "Enumerating objects: 42, done.",
                "To github.com:Peter362187/Easy-Arch-Linux.git",
                "   c0ffee1..deadbee  main -> main",
            ], pause=1.2),
        ],
    ),
    Scene(
        name="panic",
        cols=64,
        title="l4rp@github: ~/panic",
        steps=[
            # Erster Step ohne Ausgabe - vim startet einfach und danach
            # landen die Editor-Kommandos in der Shell.
            Step("vim config.yaml", [], pause=0.8),
            Step(":q", ["bash: :q: command not found"], pause=0.5),
            Step(":wq", ["bash: :wq: command not found"], pause=0.5),
            Step("pkill vim", ["[1]+  Terminated  vim config.yaml"], pause=1.0),
            Step("git commit -m \"fix\"", [
                " 47 files changed, 3 insertions(+), 2891 deletions(-)",
            ], pause=1.0),
            Step("git push --force origin main", [
                "remote: your teammates have been notified",
            ], pause=1.2),
        ],
    ),
    Scene(
        name="lonely",
        cols=64,
        title="l4rp@github: ~/lonely",
        steps=[
            # ASCII-Block belegt Spalte 0-18, die Infospalte beginnt bei 19.
            Step("neofetch girlfriend", [
                "   ________        girlfriend: not found",
                "  /        \\       status : 404",
                " |   404    |      uptime : n/a",
                "  \\________/       disk   : 0 B used",
                "                   hint   : apt install shower",
            ], pause=1.3),
            Step("sudo apt install girlfriend", [
                "E: Unable to locate package girlfriend",
                "E: Did you mean 'gnome-shell-extension-clock'?",
            ], pause=1.2),
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
