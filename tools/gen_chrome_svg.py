#!/usr/bin/env python3
"""Erzeugt die Rahmen-Grafiken des README: Banner, Trenner, Fusszeile.

    python tools/gen_chrome_svg.py

Die Terminals kommen aus gen_terminal_svg.py; hier entsteht alles, was
kein Terminal ist. Hintergrund (Vignette + Punktraster) wird von dort
importiert, damit beide Sorten denselben Untergrund haben.

Der Schriftzug ist bewusst kein Text, sondern ein Pixelraster aus
<rect>-Elementen. ASCII-Grossbuchstaben haengen sonst davon ab, welche
Monospace-Schrift der Betrachter installiert hat - als Rechtecke sieht es
auf jedem Rechner identisch aus und bleibt bei jeder Groesse scharf.
"""

from __future__ import annotations

import os

from gen_terminal_svg import BG_DEFS, FONT_STACK, bg_rects

WIDTH = 753          # gleiche Breite wie die Terminal-Panels

# 5x5-Pixelschrift, nur fuer die Zeichen des Schriftzugs
GLYPHS = {
    "L": ("#....",
          "#....",
          "#....",
          "#....",
          "#####"),
    "4": ("#..#.",
          "#..#.",
          "#####",
          "...#.",
          "...#."),
    "R": ("####.",
          "#...#",
          "####.",
          "#..#.",
          "#...#"),
    "P": ("####.",
          "#...#",
          "####.",
          "#....",
          "#...."),
}


def wordmark(text: str, cell: float, x0: float, y0: float,
             gap_cols: int = 1) -> tuple[str, float, float]:
    """Schriftzug als Rechteckraster. Gibt (svg, breite, hoehe) zurueck."""
    parts: list[str] = []
    col = 0
    for ch in text:
        rows = GLYPHS[ch]
        for r, line in enumerate(rows):
            for c, px in enumerate(line):
                if px != "#":
                    continue
                x = x0 + (col + c) * cell
                y = y0 + r * cell
                parts.append(
                    f'<rect x="{x:.1f}" y="{y:.1f}" '
                    f'width="{cell - 2:.1f}" height="{cell - 2:.1f}" rx="1"/>'
                )
        col += len(rows[0]) + gap_cols
    total_cols = col - gap_cols
    return "".join(parts), total_cols * cell, 5 * cell


def build_hero() -> str:
    cell = 15.0
    _, mark_w, mark_h = wordmark("L4RP", cell, 0, 0)
    height = 214.0
    mark_x = (WIDTH - mark_w) / 2
    mark_y = 52.0
    marks, _, _ = wordmark("L4RP", cell, mark_x, mark_y)

    tagline = "arch linux tooling  //  python  //  opsec enabled"
    sub_y = mark_y + mark_h + 42
    # Vorschub = Schriftgroesse * 0.6 plus letter-spacing; ohne den Zuschlag
    # landet der Cursor mitten im Text statt dahinter.
    tag_adv = 14 * 0.6 + 2
    cursor_x = WIDTH / 2 + len(tagline) * tag_adv / 2 + 7

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH:.0f}" height="{height:.0f}"
     viewBox="0 0 {WIDTH:.0f} {height:.0f}" role="img"
     aria-label="L4RP - arch linux tooling, python, opsec enabled">
<title>L4RP</title>
<defs>
{BG_DEFS}
<linearGradient id="sweepg" x1="0" y1="0" x2="1" y2="0">
  <stop offset="0" stop-color="#ffffff" stop-opacity="0"/>
  <stop offset="0.5" stop-color="#ffffff" stop-opacity="0.5"/>
  <stop offset="1" stop-color="#ffffff" stop-opacity="0"/>
</linearGradient>
<clipPath id="heroclip">
  <rect width="{WIDTH:.0f}" height="{height:.0f}" rx="12"/>
</clipPath>
</defs>
<style>
  text{{font-family:{FONT_STACK}}}
  .mark rect{{fill:#f4f4f6}}
  .tag{{fill:#8e8e96;font-size:14px;letter-spacing:2px}}
  .rule{{stroke:#33333a}}
  .cur{{fill:#f4f4f6}}
  /* Der Schriftzug baut sich spaltenweise auf, danach faehrt einmal ein
     Lichtstreifen darueber. Beides laeuft genau einmal. */
  .mark{{clip-path:inset(0 100% 0 0);animation:reveal 1.5s steps(23) 0.3s 1 forwards}}
  @keyframes reveal{{to{{clip-path:inset(0 0 0 0)}}}}
  .tag{{opacity:0;animation:fade 0.6s linear 2.0s 1 forwards}}
  @keyframes fade{{to{{opacity:1}}}}
  .sweep{{opacity:0;animation:sweep 1.4s linear 2.1s 1 forwards}}
  @keyframes sweep{{
    0%{{opacity:0;transform:translateX(-240px)}}
    20%{{opacity:1}}
    80%{{opacity:1}}
    100%{{opacity:0;transform:translateX({WIDTH:.0f}px)}}
  }}
  .blink{{animation:bl 1.06s steps(1) infinite}}
  @keyframes bl{{0%,49%{{opacity:1}}50%,100%{{opacity:0}}}}
  @media (prefers-reduced-motion:reduce){{
    *{{animation:none!important}}
    .mark{{clip-path:none!important}}
    .tag{{opacity:1!important}}
    .sweep{{opacity:0!important}}
  }}
</style>
{bg_rects(WIDTH, height)}
<g clip-path="url(#heroclip)">
  <g class="mark">{marks}</g>
  <rect class="sweep" x="0" y="{mark_y - 8:.0f}" width="150"
        height="{mark_h + 16:.0f}" fill="url(#sweepg)"/>
</g>
<line class="rule" x1="60" y1="{sub_y - 22:.0f}" x2="{WIDTH - 60:.0f}"
      y2="{sub_y - 22:.0f}"/>
<text class="tag" x="{WIDTH / 2:.0f}" y="{sub_y:.0f}" text-anchor="middle">{tagline}</text>
<rect class="cur blink" x="{cursor_x:.0f}" y="{sub_y - 11:.0f}" width="8" height="13"/>
</svg>
"""


def build_divider() -> str:
    """Duenner Trenner zwischen den Abschnitten.

    Ohne eigenen Hintergrund - der Trenner liegt direkt auf der Seite und
    muss deshalb sowohl auf GitHubs hellem als auch auf dem dunklen Theme
    funktionieren. Ein mittleres Grau tut das.
    """
    h = 26.0
    mid = h / 2
    label = "/ / /"
    gap = 46.0
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH:.0f}" height="{h:.0f}"
     viewBox="0 0 {WIDTH:.0f} {h:.0f}" role="img" aria-label="">
<title>Trenner</title>
<defs>
<linearGradient id="fadeL" x1="0" y1="0" x2="1" y2="0">
  <stop offset="0" stop-color="#6a6a72" stop-opacity="0"/>
  <stop offset="1" stop-color="#6a6a72" stop-opacity="0.9"/>
</linearGradient>
<linearGradient id="fadeR" x1="0" y1="0" x2="1" y2="0">
  <stop offset="0" stop-color="#6a6a72" stop-opacity="0.9"/>
  <stop offset="1" stop-color="#6a6a72" stop-opacity="0"/>
</linearGradient>
</defs>
<rect x="0" y="{mid - 0.5:.1f}" width="{WIDTH / 2 - gap:.1f}" height="1" fill="url(#fadeL)"/>
<rect x="{WIDTH / 2 + gap:.1f}" y="{mid - 0.5:.1f}" width="{WIDTH / 2 - gap:.1f}"
      height="1" fill="url(#fadeR)"/>
<text x="{WIDTH / 2:.0f}" y="{mid + 5:.0f}" text-anchor="middle"
      font-family="{FONT_STACK}" font-size="13" fill="#6a6a72"
      letter-spacing="2">{label}</text>
</svg>
"""


def build_footer() -> str:
    cell = 7.0
    _, mark_w, mark_h = wordmark("L4RP", cell, 0, 0)
    height = 132.0
    mark_x = (WIDTH - mark_w) / 2
    mark_y = 30.0
    marks, _, _ = wordmark("L4RP", cell, mark_x, mark_y)
    line1 = "user@github:~$ exit"
    line2 = "Connection to localhost closed."

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH:.0f}" height="{height:.0f}"
     viewBox="0 0 {WIDTH:.0f} {height:.0f}" role="img"
     aria-label="{line1} - {line2}">
<title>exit</title>
<defs>
{BG_DEFS}
</defs>
<style>
  text{{font-family:{FONT_STACK};font-size:14px}}
  .mark rect{{fill:#5c5c66}}
  .a{{fill:#a8a8a8}}
  .b{{fill:#6f6f6f}}
  .blink{{fill:#f2f2f2;animation:bl 1.06s steps(1) infinite}}
  @keyframes bl{{0%,49%{{opacity:1}}50%,100%{{opacity:0}}}}
  @media (prefers-reduced-motion:reduce){{*{{animation:none!important}}}}
</style>
{bg_rects(WIDTH, height)}
<g class="mark">{marks}</g>
<text class="a" x="{WIDTH / 2:.0f}" y="{mark_y + mark_h + 30:.0f}"
      text-anchor="middle">{line1}</text>
<text class="b" x="{WIDTH / 2:.0f}" y="{mark_y + mark_h + 52:.0f}"
      text-anchor="middle">{line2}</text>
<rect class="blink" x="{WIDTH / 2 + len(line1) * 4.2 + 6:.0f}"
      y="{mark_y + mark_h + 19:.0f}" width="8" height="14"/>
</svg>
"""


def main() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(os.path.dirname(here), "assets")
    os.makedirs(out_dir, exist_ok=True)
    for name, svg in (("hero", build_hero()),
                      ("divider", build_divider()),
                      ("footer", build_footer())):
        path = os.path.join(out_dir, f"{name}.svg")
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(svg)
        print(f"{path}  ({os.path.getsize(path)} bytes)")


if __name__ == "__main__":
    main()
