"""Builds assets/profile-card.svg: a coloured ASCII portrait + a neofetch-style
info panel, drawn as ONE animated SVG so it looks identical everywhere.

Runs daily in GitHub Actions (stats refresh) and locally.
    python generate.py            # fetch live stats
    python generate.py --offline  # use the fallback numbers
"""

import hashlib
import html
import json
import os
import sys

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

USERNAME = os.environ.get("GH_USERNAME", "vedantdev37")
NOTE = "SYNT{fit_1f_wh5g_kzy_8194oo}"  # :)
PHOTO = "profile.jpg"
OUT = os.path.join("assets", "profile-card.svg")
CACHE = os.path.join("assets", "portrait.json")  # portrait only changes when the photo does

# ---- portrait settings -------------------------------------------------------
COLS = 84                      # characters per ASCII row
FONT = 8.2                     # px (portrait)
PANEL_FONT = 12.5              # px (info panel)
CW = FONT * 0.6                # monospace advance width (fixed with textLength)
LH = FONT * 1.18               # line height
RAMP = " .,:;i1tfLCG08@"       # sparse -> dense; brighter pixels get denser chars
PCW = PANEL_FONT * 0.6         # panel advance width
PLH = PANEL_FONT * 1.65        # panel line height

# ---- colours (GitHub dark palette) -------------------------------------------
BG, BORDER, DIM = "#0d1117", "#30363d", "#6e7681"
TEXT, KEY, OK, ACCENT = "#c9d1d9", "#ffa657", "#3fb950", "#79c0ff"

# ---- what the panel says (edit freely) ---------------------------------------
WHOAMI = "Aspiring SecDev · InfoSec tinkerer"
INFO = [  # (key, value)
    ("Location", "Bangalore, India"),
    ("Stack", "Python · Bash · C"),
    ("Tools", "Linux · Git · Docker"),
    ("Interests", "InfoSec · CTFs · Automation"),
    ("", "Reverse Engineering"),
]
FALLBACK_STATS = {"Repos": 7, "Stars": 0, "Followers": 6, "Following": 3}


def fetch_stats():
    if "--offline" in sys.argv:
        return FALLBACK_STATS
    import requests

    headers = {"Accept": "application/vnd.github+json"}
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    try:
        user = requests.get(f"https://api.github.com/users/{USERNAME}", headers=headers, timeout=30).json()
        repos = requests.get(f"https://api.github.com/users/{USERNAME}/repos?per_page=100",
                             headers=headers, timeout=30).json()
        return {
            "Repos": user["public_repos"],
            "Stars": sum(r.get("stargazers_count", 0) for r in repos),
            "Followers": user["followers"],
            "Following": user["following"],
        }
    except Exception as exc:  # never break the daily run over a network hiccup
        print(f"stats fetch failed ({exc}); using fallback numbers")
        return FALLBACK_STATS


def cutout(path):
    """Remove the background (transparent PNG). Falls back to the raw photo."""
    img = Image.open(path).convert("RGB")
    try:
        from rembg import new_session, remove
        return remove(img, session=new_session("u2net_human_seg")).convert("RGBA")
    except Exception as exc:
        print(f"background removal unavailable ({exc}); using raw photo")
        return img.convert("RGBA")


def portrait_cells(img):
    """Returns rows of (char, hex colour) — None for empty background."""
    # crop to the person, then cut the lower part (keep head + shoulders)
    box = img.getchannel("A").point(lambda a: 255 if a > 128 else 0).getbbox() or (0, 0, *img.size)
    l, t, r, b = box
    img = img.crop((l, t, r, t + round((b - t) * 0.86)))
    rows = round(img.height / img.width * COLS * CW / LH)  # keep the face's real proportions
    small = img.resize((COLS, rows), Image.LANCZOS)
    alpha = small.getchannel("A")
    rgb = small.convert("RGB")

    # Local contrast (CLAHE) on the full-res photo, so eyes/brows/lips stand out
    # before shrinking; then stretch contrast on the subject only.
    import cv2
    import numpy as np
    full = np.array(ImageOps.grayscale(img.convert("RGB")))
    full = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8)).apply(full)
    gray = Image.fromarray(full).resize((COLS, rows), Image.LANCZOS)
    gray = ImageOps.autocontrast(gray, cutoff=2, mask=alpha.point(lambda a: 255 if a > 128 else 0))
    gray = gray.filter(ImageFilter.UnsharpMask(radius=1, percent=90, threshold=2))
    vivid = ImageEnhance.Color(rgb).enhance(1.25)

    out = []
    for y in range(rows):
        row = []
        for x in range(COLS):
            if alpha.getpixel((x, y)) < 128:
                row.append(None)
                continue
            g = (gray.getpixel((x, y)) / 255) ** 1.35  # spread the bright skin tones
            # high floor: dark hair still gets solid letters, colour carries the shading
            ch = RAMP[round(4 + g * (len(RAMP) - 5))]
            r, gg, b = vivid.getpixel((x, y))
            lift = 0.42  # lift dark colours (hair) so they read on the dark card
            r, gg, b = (round(c + (255 - c) * lift * (1 - g)) for c in (r, gg, b))
            row.append((ch, f"#{r // 16 * 17:02x}{gg // 16 * 17:02x}{b // 16 * 17:02x}"))  # 4-bit colour = smaller file
        out.append(row)
    return out


def esc(s):
    return html.escape(s, quote=False)


def ascii_rows_svg(cells, x0, y0):
    """One <text> per row; each same-colour run is pinned to its exact column,
    so spacing never depends on the viewer's font (SVG would collapse spaces)."""
    parts = []
    for i, row in enumerate(cells):
        spans, start, run, run_col = [], 0, "", None
        for x, cell in enumerate(row + [None]):
            col = cell[1] if cell else None
            if run and col != run_col:
                spans.append(
                    f'<tspan x="{x0 + start * CW:.1f}" fill="{run_col}" textLength="{len(run) * CW:.1f}">{esc(run)}</tspan>'
                )
                run = ""
            if cell:
                if not run:
                    start = x
                run += cell[0]
            run_col = col
        if spans:
            y = y0 + (i + 1) * LH
            parts.append(f'<text class="a" y="{y:.1f}" style="animation-delay:{i * 0.03:.2f}s">{"".join(spans)}</text>')
    return "\n".join(parts)


def panel_svg(stats, x0, y0, width_chars, start_delay):
    """Neofetch-style panel. Every line is pinned to an exact width with textLength."""
    lines = []  # list of [(text, colour)]
    title = f"{USERNAME}@github"
    lines.append([(title, OK)])
    lines.append([("─" * len(title), DIM)])
    lines.append([("$ ", OK), ("whoami", TEXT)])
    lines.append([(WHOAMI, ACCENT)])
    lines.append([])
    for key, val in INFO:
        label = f"{key}:" if key else ""
        lines.append([(label.ljust(11), KEY), (val, TEXT)])
    lines.append([])
    lines.append([("$ ", OK), ("gh api /users/" + USERNAME, TEXT)])
    for key, val in stats.items():
        dots = "." * (width_chars - len(key) - len(str(val)) - 2)
        lines.append([(key + " ", KEY), (dots, DIM), (" " + str(val), TEXT)])
    lines.append([])
    lines.append([("$ ", OK), ("sudo rm -rf ~/doubts", TEXT)])
    lines.append([("done. nothing left to fear.", DIM)])
    lines.append([])
    lines.append([("$ ", OK)])

    out = []
    for i, segs in enumerate(lines):
        if not segs:
            continue
        y = y0 + (i + 1) * (PLH)
        n = sum(len(t) for t, _ in segs)
        body = "".join(f'<tspan fill="{c}">{esc(t)}</tspan>' for t, c in segs)
        out.append(
            f'<text class="t" x="{x0}" y="{y:.1f}" textLength="{n * PCW:.1f}" lengthAdjust="spacing" '
            f'style="animation-delay:{start_delay + i * 0.12:.2f}s">{body}</text>'
        )
    last_y = y0 + len(lines) * (PLH)
    cursor = (f'<rect class="cur" x="{x0 + 2 * PCW + 2:.1f}" y="{last_y - PANEL_FONT * 0.85:.1f}" '
              f'width="{PCW:.1f}" height="{PANEL_FONT * 1.05:.1f}" fill="{OK}" '
              f'style="animation-delay:{start_delay + len(lines) * 0.12:.2f}s"/>')
    return "\n".join(out) + "\n" + cursor, last_y


def main():
    stats = fetch_stats()

    # Re-run the slow background removal only when the photo (or COLS) changes
    with open(PHOTO, "rb") as f:
        key = hashlib.sha1(f.read()).hexdigest() + f"-{COLS}"
    cached = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
    if cached.get("key") == key:
        cells = [[tuple(c) if c else None for c in row] for row in cached["cells"]]
    else:
        cells = portrait_cells(cutout(PHOTO))
        os.makedirs("assets", exist_ok=True)
        with open(CACHE, "w") as f:
            json.dump({"key": key, "cells": cells}, f, separators=(",", ":"))

    pad = 28
    art_w, art_h = COLS * CW, len(cells) * LH
    panel_x = pad + art_w + 40
    W = round(panel_x + 37 * PCW + pad)
    H = round(max(art_h, 20 * PLH) + pad * 2 + 30)

    art = ascii_rows_svg(cells, pad, pad + 22)
    reveal_end = len(cells) * 0.03
    panel, _ = panel_svg(stats, panel_x, pad + 22, 34, reveal_end * 0.5)

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{USERNAME}: ASCII portrait and profile info">
<!-- note to self: {NOTE} -->
<style>
text {{ font-family: "JetBrains Mono","Fira Code","SF Mono",Consolas,"DejaVu Sans Mono",monospace; white-space: pre; }}
.a {{ font-size: {FONT}px; opacity: 0; animation: in .25s ease-out forwards; }}
.t {{ font-size: {PANEL_FONT:.1f}px; opacity: 0; animation: in .2s steps(1) forwards; }}
.cur {{ opacity: 0; animation: blink 1s steps(1) infinite; }}
@keyframes in {{ to {{ opacity: 1; }} }}
@keyframes blink {{ 0% {{ opacity: 1; }} 50% {{ opacity: 0; }} }}
@media (prefers-reduced-motion: reduce) {{ .a, .t {{ animation: none; opacity: 1; }} }}
</style>
<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="12" fill="{BG}" stroke="{BORDER}"/>
<circle cx="22" cy="18" r="5" fill="#ff5f57"/><circle cx="38" cy="18" r="5" fill="#febc2e"/><circle cx="54" cy="18" r="5" fill="#28c840"/>
<defs><linearGradient id="fade" x1="0" y1="0" x2="0" y2="1"><stop offset="0.8" stop-color="#fff"/><stop offset="1" stop-color="#000"/></linearGradient>
<mask id="m"><rect x="0" y="{pad + 22}" width="{panel_x - 24:.1f}" height="{art_h:.1f}" fill="url(#fade)"/></mask></defs>
<line x1="{panel_x - 20:.1f}" y1="{pad + 18}" x2="{panel_x - 20:.1f}" y2="{H - pad}" stroke="{BORDER}"/>
<g mask="url(#m)">
{art}
</g>
{panel}
</svg>
'''
    os.makedirs("assets", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"wrote {OUT}: {W}x{H}, {len(svg) // 1024} KB, stats {stats}")


if __name__ == "__main__":
    main()
