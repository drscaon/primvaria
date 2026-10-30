"""Draw the Primvaria logo: the mark (nine primitives, no two alike, the centre
one in teal) and the wordmark in Familjen Grotesk Bold, as outlines, in light
and dark versions, plus the website's favicon. The social preview: make_social_preview.py.

Development tool:

    python scripts/make_logo.py            # writes docs/images/ and site/favicon.svg

Needs fontTools; cairosvg (with the cairo library) for the PNGs. The font
(SIL Open Font License) is fetched from the Google Fonts repository.
"""

from __future__ import annotations

import io
import sys
import urllib.request
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

ROOT = Path(__file__).resolve().parents[1]
FONT_URL = (
    "https://raw.githubusercontent.com/google/fonts/main/ofl/familjengrotesk/FamiljenGrotesk%5Bwght%5D.ttf"
)
WORD = "Primvaria"
TRACKING = -0.02  # em, as on the website

LIGHT = {"ink": "#16191D", "teal": "#0F6E74"}
DARK = {"ink": "#E8EAED", "teal": "#4CC1C4"}

# the mark, on a 64-unit grid: eight primitives in ink, the centre one in teal
SHAPES = [
    (4, 4, 16, 16, 2, -6),
    (24, 4, 16, 16, 8, 0),
    (46, 6, 13, 13, 4, 8),
    (5, 25, 14, 14, 6, 0),
    (44, 24, 16, 16, 0, -4),
    (6, 46, 12, 12, 6, 0),
    (24, 44, 16, 16, 3, -10),
    (44.5, 44.5, 15, 15, 5, 0),
]
CENTRE = (24, 24, 16, 16, 4, 12)


def _rect(x, y, w, h, rx, rot, fill) -> str:
    t = f' transform="rotate({rot} {x + w / 2:g} {y + h / 2:g})"' if rot else ""
    return f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="{rx:g}" fill="{fill}"{t}/>'


def mark_body(c: dict) -> str:
    return "".join(_rect(*s, c["ink"]) for s in SHAPES) + _rect(*CENTRE, c["teal"])


def mark_svg(c: dict, size: int = 64, adaptive: bool = False) -> str:
    """The mark alone; `adaptive` switches to the dark colours under a dark colour scheme
    (a favicon on a dark tab bar, the site header in dark mode)."""
    body = mark_body(c)
    style = ""
    if adaptive:
        body = body.replace(f'fill="{c["ink"]}"', 'class="i" fill="' + c["ink"] + '"').replace(
            f'fill="{c["teal"]}"', 'class="t" fill="' + c["teal"] + '"'
        )
        style = (
            "<style>@media (prefers-color-scheme: dark){"
            f".i{{fill:{DARK['ink']}}}.t{{fill:{DARK['teal']}}}}}</style>"
        )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="{size}" height="{size}" '
        f'role="img" aria-label="Primvaria"><title>Primvaria</title>{style}{body}</svg>\n'
    )


def load_font() -> TTFont:
    with urllib.request.urlopen(FONT_URL, timeout=60) as r:
        font = TTFont(io.BytesIO(r.read()))
    return instantiateVariableFont(font, {"wght": 700})


def word_paths(font: TTFont, size: float):
    """SVG path data of the word at `size` px (baseline at y = 0, y down) and its bounds."""
    upm = font["head"].unitsPerEm
    s = size / upm
    cmap, gs, hmtx = font.getBestCmap(), font.getGlyphSet(), font["hmtx"]
    pen, bounds, x = SVGPathPen(gs), BoundsPen(gs), 0.0
    for ch in WORD:
        name = cmap[ord(ch)]
        t = (s, 0, 0, -s, x, 0)
        gs[name].draw(TransformPen(pen, t))
        gs[name].draw(TransformPen(bounds, t))
        x += hmtx[name][0] * s + TRACKING * size
    return pen.getCommands(), bounds.bounds


def logo_svg(font: TTFont, c: dict) -> str:
    mark, gap, pad = 120.0, 30.0, 24.0
    d, (x0, y0, x1, y1) = word_paths(font, 118.0)
    height = mark + 2 * pad
    tx = pad + mark + gap - x0
    ty = pad + mark / 2 - (y0 + y1) / 2  # the word's ink centred on the mark
    width = tx + x1 + pad
    k = mark / 64
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.0f} {height:.0f}" '
        f'width="{width:.0f}" height="{height:.0f}" role="img" aria-label="Primvaria">'
        "<title>Primvaria</title>"
        f'<g transform="translate({pad:g} {pad:g}) scale({k:g})">{mark_body(c)}</g>'
        f'<path fill="{c["teal"]}" transform="translate({tx:.2f} {ty:.2f})" d="{d}"/></svg>\n'
    )


def main() -> int:
    font = load_font()
    images = ROOT / "docs" / "images"
    images.mkdir(parents=True, exist_ok=True)
    files = {
        images / "logo.svg": logo_svg(font, LIGHT),
        images / "logo-dark.svg": logo_svg(font, DARK),
        images / "mark.svg": mark_svg(LIGHT),
        images / "mark-dark.svg": mark_svg(DARK),
        ROOT / "site" / "favicon.svg": mark_svg(LIGHT, 32, adaptive=True),
    }
    for path, text in files.items():
        path.write_text(text, encoding="utf-8")
        print(path.relative_to(ROOT))
    try:
        import cairosvg
    except (ImportError, OSError):
        print("cairosvg not available: PNGs not written", file=sys.stderr)
        return 0
    cairosvg.svg2png(url=str(images / "mark.svg"), write_to=str(images / "mark.png"), output_width=512)
    print("docs/images/mark.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
