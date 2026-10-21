#!/usr/bin/env python3
"""Generate bespoke animated radar charts in pastel blue aesthetic.

Usage:
    python scripts/generate_radar.py
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / ".github/assets"

THEMES = {
    "dark": {
        "grid":    "#1E2F4D",  # Subtle dark pastel border
        "spoke":   "#162032",  # Deep axis line
        "label":   "#BAE6FD",  # Soft pastel sky text
        "value":   "#7E97B8",  # Slate muted numbers
        "title":   "#89B4FA",  # Signature pastel blue title
        "fill":    "#89B4FA",  # Translucent pastel polygon
        "stroke":  "#89B4FA",  # Crisp pastel blue stroke
        "vertex":  "#BAE6FD",  # Cyan highlight dots
        "bg":      "none",
    },
    "light": {
        "grid":    "#BAE6FD",  # Pastel sky grid rings
        "spoke":   "#E0F2FE",  # Soft sky spoke lines
        "label":   "#0F172A",  # Deep slate readable labels
        "value":   "#0284C7",  # Vibrant ocean blue values
        "title":   "#0369A1",  # Deep ocean navy title
        "fill":    "#38BDF8",  # Sky blue translucent polygon
        "stroke":  "#2563EB",  # Royal sapphire stroke
        "vertex":  "#1D4ED8",  # Deep blue dots
        "bg":      "none",
    },
}

FONT = "ui-sans-serif,-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif"
LBL, VAL, TTL = 13, 11, 15  # Font sizes


def esc(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def ring(radius: float, n: int, start: float = -math.pi / 2) -> list[tuple[float, float]]:
    """Vertices of a regular n-gon centred on (0, 0), first one straight up."""
    return [
        (
            radius * math.cos(start + i * 2 * math.pi / n),
            radius * math.sin(start + i * 2 * math.pi / n),
        )
        for i in range(n)
    ]


def text_width(s: str, font_size: float) -> float:
    return len(s) * font_size * 0.62


def render(
    title: str,
    axes: list[tuple[str, float]],
    theme: str,
    size: int = 440,
    rings: int = 4,
    show_values: bool = False,
    animate: bool = True,
) -> str:
    c = THEMES[theme]
    n = len(axes)
    r = size / 2 - 8
    gap = 20

    vals = [max(0.0, min(100.0, v)) for _, v in axes]
    outer = ring(r, n)

    labels = []
    for i, (label, _) in enumerate(axes):
        ang = -math.pi / 2 + i * 2 * math.pi / n
        cosv, sinv = math.cos(ang), math.sin(ang)
        lx, ly = (r + gap) * cosv, (r + gap) * sinv
        anchor = "middle" if abs(cosv) < 0.25 else ("start" if cosv > 0 else "end")
        dy = 4 if abs(sinv) < 0.25 else (14 if sinv > 0 else -5)
        labels.append((lx, ly + dy, anchor, label, vals[i]))

    minx, maxx, miny, maxy = -r, r, -r, r
    for lx, ly, anchor, label, v in labels:
        w = max(
            text_width(label, LBL),
            text_width(f"{v:g}", VAL) if show_values else 0.0,
        )
        if anchor == "start":
            x0, x1 = lx, lx + w
        elif anchor == "end":
            x0, x1 = lx - w, lx
        else:
            x0, x1 = lx - w / 2, lx + w / 2
        y0 = ly - LBL
        y1 = ly + 4 + (VAL + 4 if show_values else 0)
        minx, maxx = min(minx, x0), max(maxx, x1)
        miny, maxy = min(miny, y0), max(maxy, y1)

    pad = 12
    title_h = TTL + 14 if title else 0
    W = round((maxx - minx) + 2 * pad)
    H = round((maxy - miny) + 2 * pad + title_h)
    ox, oy = -minx + pad, -miny + pad + title_h

    if title:
        need = round(text_width(title, TTL) + 2 * pad)
        if need > W:
            ox += (need - W) / 2
            W = need

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'width="{W}" height="{H}" role="img" '
        f'aria-label="{esc(title) or "radar chart"}" font-family="{FONT}">'
    ]
    if c["bg"] != "none":
        parts.append(f'<rect width="100%" height="100%" fill="{c["bg"]}"/>')

    if title:
        parts.append(
            f'<text x="{W / 2:.1f}" y="{pad + TTL:.0f}" text-anchor="middle" '
            f'font-size="{TTL}" font-weight="700" fill="{c["title"]}">'
            f"{esc(title)}</text>"
        )

    parts.append(f'<g transform="translate({ox:.1f},{oy:.1f})">')

    # Concentric rings
    for k in range(rings, 0, -1):
        d = " ".join(f"{x:.1f},{y:.1f}" for x, y in ring(r * k / rings, n))
        parts.append(
            f'<polygon points="{d}" fill="none" stroke="{c["grid"]}" '
            f'stroke-width="1" opacity="{0.35 + 0.5 * k / rings:.2f}"/>'
        )

    # Spokes
    for x, y in outer:
        parts.append(
            f'<line x1="0" y1="0" x2="{x:.1f}" y2="{y:.1f}" '
            f'stroke="{c["spoke"]}" stroke-width="1"/>'
        )

    # Data shape with scale animation
    shape = [(px * v / 100, py * v / 100) for (px, py), v in zip(outer, vals)]
    d = " ".join(f"{x:.1f},{y:.1f}" for x, y in shape)
    fill_op = "0.22" if theme == "dark" else "0.26"

    parts.append("<g>")
    if animate:
        parts.append(
            '<animateTransform attributeName="transform" type="scale" '
            'values="0.04;1" dur="1.1s" calcMode="spline" keyTimes="0;1" '
            'keySplines="0.22 1 0.36 1" fill="freeze"/>'
        )
    parts.append(
        f'<polygon points="{d}" fill="{c["fill"]}" fill-opacity="{fill_op}" '
        f'stroke="{c["stroke"]}" stroke-width="2.5" stroke-linejoin="round"/>'
    )
    for x, y in shape:
        parts.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.6" fill="{c["vertex"]}" '
            f'stroke="{c["stroke"]}" stroke-width="1.2"/>'
        )
    parts.append("</g>")

    # Axis labels & values
    for lx, ly, anchor, label, v in labels:
        parts.append(
            f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}" '
            f'font-size="{LBL}" font-weight="600" fill="{c["label"]}">'
            f"{esc(label)}</text>"
        )
        if show_values:
            parts.append(
                f'<text x="{lx:.1f}" y="{ly + VAL + 4:.1f}" text-anchor="{anchor}" '
                f'font-size="{VAL}" font-weight="500" fill="{c["value"]}">{v:g}</text>'
            )

    parts.append("</g></svg>")
    return "".join(parts)


def build_pair(json_path: Path, out_stem: Path, show_values: bool = False) -> None:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    title = data.get("title", "Radar")
    axes = [(a["label"], float(a["value"])) for a in data["axes"]]

    for theme in ("dark", "light"):
        svg = render(title, axes, theme=theme, show_values=show_values, animate=True)
        target = out_stem.parent / f"{out_stem.name}-{theme}.svg"
        target.write_text(svg, encoding="utf-8")
        print(f"Generated {target.name} ({len(svg.encode('utf-8')):,} bytes)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skills", type=Path, default=ASSETS / "skills.json")
    parser.add_argument("--langs", type=Path, default=ASSETS / "langmix.json")
    args = parser.parse_args()

    ASSETS.mkdir(parents=True, exist_ok=True)

    print("Generating skill radars...")
    build_pair(args.skills, ASSETS / "radar", show_values=False)

    print("Generating language radars...")
    build_pair(args.langs, ASSETS / "radar-langs", show_values=True)

    print("Radar generation complete!")


if __name__ == "__main__":
    main()
