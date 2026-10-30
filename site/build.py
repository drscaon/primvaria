"""Build the primvaria.com site into _site/: the page, and the generators' hero
images resized to one 16:9 format.

    python site/build.py                 # images from GitHub (what CI does)
    python site/build.py --local ..      # images from sibling clones, for a preview

Needs Pillow.
"""

from __future__ import annotations

import argparse
import io
import shutil
import urllib.request
from pathlib import Path

from PIL import Image

HERE = Path(__file__).parent
WIDTH, HEIGHT = 1200, 675

# (repository, image under docs/images, vertical anchor of the 16:9 crop: 0 top, 0.5 centre)
HEROES = {
    "granulaire": ("moisture_gallery.png", 0.0),
    "maillage": ("all_presets.jpg", 0.5),
    "filaire": ("hero.jpg", 0.5),
    "quincaillerie": ("variation.jpg", 0.5),
}


def fetch(repo: str, name: str, local: Path | None) -> Image.Image:
    if local is not None:
        return Image.open(local / repo / "docs" / "images" / name)
    url = f"https://raw.githubusercontent.com/drscaon/{repo}/main/docs/images/{name}"
    with urllib.request.urlopen(url, timeout=60) as r:
        return Image.open(io.BytesIO(r.read()))


def cover(im: Image.Image, anchor: float) -> Image.Image:
    """Scale to cover WIDTH x HEIGHT, then crop (horizontally centred)."""
    im = im.convert("RGB")
    s = max(WIDTH / im.width, HEIGHT / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x = (im.width - WIDTH) // 2
    y = round((im.height - HEIGHT) * anchor)
    return im.crop((x, y, x + WIDTH, y + HEIGHT))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--local", type=Path, default=None, help="folder holding clones of the four repositories")
    ap.add_argument("--out", type=Path, default=HERE.parent / "_site")
    args = ap.parse_args(argv)
    out = args.out
    shutil.rmtree(out, ignore_errors=True)
    (out / "img").mkdir(parents=True)
    for f in ("index.html", "favicon.svg", "social_preview.png", "logo.png", "robots.txt", "sitemap.xml"):
        shutil.copy(HERE / f, out / f)
    for repo, (name, anchor) in HEROES.items():
        cover(fetch(repo, name, args.local), anchor).save(
            out / "img" / f"{repo}.jpg", quality=84, optimize=True
        )
    print(f"site written to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
