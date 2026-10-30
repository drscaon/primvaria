"""Build the social preview (GitHub, link previews): docs/images/social_preview.png
(1280 × 640) and social_preview@2x.png, copied to site/ for the website's og:image.

The tiles come from the four generators' own renders (fetched from their
repositories, or from sibling clones with --local), laid out by
scripts/social/social.html and rendered with Playwright (Chromium).

    python scripts/make_social_preview.py [--local ..]

Needs Pillow, numpy, fontTools and Playwright (Node or Python). Fonts (SIL Open
Font License) are fetched from the Google Fonts repository.
"""

from __future__ import annotations

import argparse
import io
import shutil
import sys
import tempfile
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import make_logo  # noqa: E402

FONTS = {
    "fg.ttf": "familjengrotesk/FamiljenGrotesk%5Bwght%5D.ttf",
    "plex.ttf": "ibmplexsans/IBMPlexSans%5Bwdth%2Cwght%5D.ttf",
}
S = 2  # tiles at twice their size, for a sharp @2x render


def fetch(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read()


def source(repo: str, name: str, local: Path | None) -> Image.Image:
    if local is not None:
        return Image.open(local / repo / "docs" / "images" / name)
    url = f"https://raw.githubusercontent.com/drscaon/{repo}/main/docs/images/{name}"
    return Image.open(io.BytesIO(fetch(url)))


def cover(im: Image.Image, w: int, h: int, cx=0.5, cy=0.5) -> Image.Image:
    im = im.convert("RGB")
    s = max(w / im.width, h / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x, y = round((im.width - w) * cx), round((im.height - h) * cy)
    return im.crop((x, y, x + w, y + h))


def grains_tile(gallery: Image.Image) -> Image.Image:
    """Three grains (rounded gravel, crushed gravel, marble chips), dry to saturated,
    cut from Granulaire's moisture gallery."""
    g = gallery.convert("RGB")
    ink = np.abs(np.asarray(g, int) - 255).sum(2) > 30
    rows, runs, s = ink[:, 300:].any(1), [], None
    for y, v in enumerate(rows):
        if v and s is None:
            s = y
        if not v and s is not None:
            if y - s > 20:
                runs.append((s, y))
            s = None
    runs = runs[1:]  # the first band is the header
    cols = [(319, 403), (417, 497), (511, 590), (601, 683), (691, 776)]
    states = [0, 498, 996, 1494]
    pick = [(3, 3), (4, 4), (5, 0)]
    w, h = 229 * S, 228 * S
    tile = Image.new("RGB", (w, h), "white")
    cw, top, bottom = w / 4, 28 * S, 70 * S
    rh = (h - top - bottom) / 3
    for r, (row, k) in enumerate(pick):
        y0, y1 = runs[row]
        x0, x1 = cols[k]
        for i, o in enumerate(states):
            c = g.crop((x0 + o - 4, y0 - 6, x1 + o + 4, y1 + 6))
            c.thumbnail((int(cw * 0.8), int(rh * 0.94)), Image.LANCZOS)
            tile.paste(c, (int(cw * i + cw / 2 - c.width / 2), int(top + rh * r + rh / 2 - c.height / 2)))
    return tile


def plugs_tile(sheet: Image.Image) -> Image.Image:
    """Four plugs facing their receptacles (USB-C, HDMI, C13, XLR) from Filaire's sheet."""
    p = sheet.convert("RGB")
    w, h, gap = 229 * S, 228 * S, 4
    tile = Image.new("RGB", (w, h), (176, 142, 108))
    cw, ch = (w - gap) // 2, (h - gap) // 2
    for i, (r, c) in enumerate([(0, 0), (0, 2), (1, 2), (2, 2)]):
        cell = cover(p.crop((c * 640, r * 518, c * 640 + 640, r * 518 + 480)), cw, ch)
        tile.paste(cell, ((i % 2) * (cw + gap), (i // 2) * (ch + gap)))
    return tile


def render(page: Path, out: Path, scale: int) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        tab = browser.new_page(viewport={"width": 1280, "height": 640}, device_scale_factor=scale)
        tab.goto(page.as_uri())
        tab.evaluate("document.fonts.ready")
        tab.wait_for_timeout(300)
        tab.screenshot(path=str(out))
        browser.close()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--local", type=Path, default=None, help="folder holding clones of the four repositories")
    args = ap.parse_args(argv)
    images = ROOT / "docs" / "images"
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        shutil.copy(ROOT / "scripts" / "social" / "social.html", work / "social.html")
        (work / "fonts").mkdir()
        for name, path in FONTS.items():
            (work / "fonts" / name).write_bytes(
                fetch(f"https://raw.githubusercontent.com/google/fonts/main/ofl/{path}")
            )
        (work / "mark.svg").write_text(make_logo.mark_svg(make_logo.DARK), encoding="utf-8")
        cover(source("quincaillerie", "variation.jpg", args.local), 720 * S, 300 * S, 0.5, 0.62).save(
            work / "quin.jpg", quality=92
        )
        drape = source("maillage", "blender_drape.jpg", args.local).crop((600, 180, 1000, 760))
        cover(drape, 229 * S, 228 * S, 0.5, 0.45).save(work / "mail.jpg", quality=92)
        plugs_tile(source("filaire", "plugs.jpg", args.local)).save(work / "fil.jpg", quality=92)
        grains_tile(source("granulaire", "moisture_gallery.png", args.local)).save(work / "gran.png")
        render(work / "social.html", images / "social_preview.png", 1)
        render(work / "social.html", images / "social_preview@2x.png", 2)
    shutil.copy(images / "social_preview.png", ROOT / "site" / "social_preview.png")
    print("docs/images/social_preview.png, docs/images/social_preview@2x.png, site/social_preview.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
