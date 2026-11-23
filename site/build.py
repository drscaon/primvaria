"""Build the primvaria.com site into _site/.

One page per subject instead of one long page:

    /                     home: the idea, the four generators, the first command
    /engines/             the engine matrix
    /contract/, /mission/ docs/contract.md and MISSION.md of this repository
    /<generator>/         the generator's README
    /<generator>/<page>/  each page of the generator's docs/ folder that its README links to

The home and the engine matrix are written by hand (site/pages/). Everything else is rendered
from the Markdown files of the five repositories, so the site says what the repositories say.

    python site/build.py                 # the generators' files from GitHub (what CI does)
    python site/build.py --local ..      # from sibling clones, for a preview

    python -m http.server -d _site       # then open http://localhost:8000

Needs Pillow and Markdown. The build fails if a link inside the site leads nowhere.
"""

from __future__ import annotations

import argparse
import html
import io
import json
import os
import posixpath
import re
import shutil
import struct
import subprocess
import urllib.request
from pathlib import Path

import markdown
from PIL import Image

HERE = Path(__file__).parent
ROOT = HERE.parent
SITE = "https://primvaria.com"
GITHUB = "https://github.com/drscaon"
RAW = "https://raw.githubusercontent.com/drscaon"
WIDTH, HEIGHT = 1200, 675
STATIC = (
    "favicon.svg",
    "social_preview.png",
    "logo.png",
    "robots.txt",
    "demo.mp4",
    "demo_poster.jpg",
    "bench.mp4",
    "bench_poster.jpg",
    "style.css",
)

# (repository, image under docs/images, vertical anchor of the 16:9 crop: 0 top, 0.5 centre)
HEROES = {
    "granulaire": ("moisture_gallery.png", 0.0),
    "maillage": ("all_presets.jpg", 0.5),
    "filaire": ("hero.jpg", 0.5),
    "quincaillerie": ("variation.jpg", 0.5),
}
# generator pages that show no plate under the header: their README opens with a close enough image
NO_PLATE = {"quincaillerie"}
# Markdown files of this repository that are pages of the site
OWN = {
    "docs/contract.md": (
        "contract",
        "OpenUSD contract",
        "What every Primvaria file holds: stage, model hierarchy, identity, variation, measurements.",
    ),
    "docs/stability.md": (
        "stability",
        "Stability and 1.0",
        "What the suite promises today, what 1.0 will promise, and what must hold before it.",
    ),
    "MISSION.md": (
        "mission",
        "Mission",
        "What Primvaria is for, the three verbs every change serves, and what it does not do.",
    ),
}


# ---------------------------------------------------------------- sources
class Source:
    """Where the files of the five repositories are read from."""

    def __init__(self, local: Path | None):
        self.local = local

    def text(self, repo: str, path: str) -> str:
        if repo == "primvaria":
            return (ROOT / path).read_text(encoding="utf-8")
        if self.local is not None:
            return (self.local / repo / path).read_text(encoding="utf-8")
        with urllib.request.urlopen(f"{RAW}/{repo}/main/{path}", timeout=60) as r:
            return r.read().decode("utf-8")

    def modified(self, repo: str, path: str, moment: bool = False) -> str | None:
        """Date (YYYY-MM-DD) of the last commit that changed the file, or with ``moment`` its date
        and time (ISO 8601, with the offset), or None when it cannot be known: a shallow clone, or
        no answer from GitHub. A sitemap date must be the content's."""
        root = ROOT if repo == "primvaria" else (self.local / repo if self.local is not None else None)
        if root is not None:
            git = ["git", "-C", str(root)]
            shallow = subprocess.run(
                git + ["rev-parse", "--is-shallow-repository"], capture_output=True, text=True
            )
            if shallow.returncode or shallow.stdout.strip() != "false":
                return None
            log = subprocess.run(
                git + ["log", "-1", f"--format={'%cI' if moment else '%cs'}", "--", path],
                capture_output=True,
                text=True,
            )
            return log.stdout.strip() or None
        headers = {"Accept": "application/vnd.github+json"}
        if os.environ.get("GITHUB_TOKEN"):
            headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
        url = f"https://api.github.com/repos/drscaon/{repo}/commits?path={path}&per_page=1"
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as r:
                date = json.load(r)[0]["commit"]["committer"]["date"]
                return date if moment else date[:10]
        except Exception:  # noqa: BLE001  (rate limit, network): leave the date out
            return None

    def image(self, repo: str, name: str) -> Image.Image:
        if self.local is not None:
            return Image.open(self.local / repo / "docs" / "images" / name)
        with urllib.request.urlopen(f"{RAW}/{repo}/main/docs/images/{name}", timeout=60) as r:
            return Image.open(io.BytesIO(r.read()))


def cover(im: Image.Image, anchor: float) -> Image.Image:
    """Scale to cover WIDTH x HEIGHT, then crop (horizontally centred)."""
    im = im.convert("RGB")
    s = max(WIDTH / im.width, HEIGHT / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x = (im.width - WIDTH) // 2
    y = round((im.height - HEIGHT) * anchor)
    return im.crop((x, y, x + WIDTH, y + HEIGHT))


# ---------------------------------------------------------------- Markdown
def slug(heading: str, _sep: str = "-") -> str:
    """The anchor GitHub gives a heading, so links written for GitHub work here too."""
    heading = re.sub(r"<[^>]+>", "", heading).replace("`", "").strip().lower()
    return re.sub(r"[^\w\- ]", "", heading).replace(" ", "-")


def site_path(repo: str, path: str, docs: dict[str, set[str]]) -> str | None:
    """The page of the site that renders a repository file, or None when there is none."""
    if repo == "primvaria":
        return f"/{OWN[path][0]}/" if path in OWN else None
    if repo in docs:
        if path == "README.md":
            return f"/{repo}/"
        if path in docs[repo]:
            return f"/{repo}/{Path(path).stem}/"
    return None


def relink(page: str, repo: str, path: str, docs: dict[str, set[str]]) -> str:
    """Point the links of a rendered Markdown file at the site where the site has the page, and at
    GitHub otherwise (a relative link means nothing outside its repository)."""

    def target(url: str) -> str:
        if url.startswith(("#", "mailto:", "/")):
            return url
        url, _, frag = url.partition("#")
        frag = f"#{frag}" if frag else ""
        if url.rstrip("/") == SITE:
            return {"#engines": "/engines/"}.get(frag, "/" + frag)
        m = re.match(rf"{GITHUB}/(\w+)/blob/main/(.+)$", url)
        if m:
            there = site_path(m.group(1), m.group(2), docs)
            return there + frag if there else url + frag
        if re.match(r"[a-z]+:", url):
            return url + frag
        file = posixpath.normpath(posixpath.join(posixpath.dirname(path), url))  # relative to this file
        there = site_path(repo, file, docs)
        if there:
            return there + frag
        kind = "raw" if re.search(r"\.(png|jpe?g|gif|svg|webp)$", file) else "blob"
        base = f"{RAW}/{repo}/main" if kind == "raw" else f"{GITHUB}/{repo}/blob/main"
        return f"{base}/{file}{frag}"

    return re.sub(
        r'\b(href|src)="([^"]*)"',
        lambda m: f'{m.group(1)}="{html.escape(target(html.unescape(m.group(2))))}"',
        page,
    )


def render(text: str, repo: str, path: str, docs: dict[str, set[str]]) -> str:
    md = markdown.Markdown(
        extensions=["tables", "fenced_code", "toc", "sane_lists"],
        extension_configs={"toc": {"slugify": slug}},
    )
    page = md.convert(text)
    page = page.replace("<table>", '<div class="scroll"><table>').replace("</table>", "</table></div>")
    return relink(page, repo, path, docs)


def sections(text: str) -> str:
    """A README without what stands before its first section: logo, badges and tagline are the
    page's own header here."""
    m = re.search(r"^## ", text, re.M)
    return text[m.start() :] if m else text


def title_and_body(text: str) -> tuple[str, str]:
    """The first heading of a Markdown file, and the rest (without the line that points back to
    the README, which the sub-navigation replaces)."""
    m = re.match(r"\s*# (.+)\n", text)
    title, body = (m.group(1).strip(), text[m.end() :]) if m else ("", text)
    body = re.sub(r"^Part of the \[\w+\]\(\.\./README\.md\) documentation\.\n", "", body, flags=re.M)
    return title, body


def doc_links(readme: str, repo: str) -> list[tuple[str, str]]:
    """(path, title) of the docs/ pages a README links to: first the rows of its Documentation
    table, in order and with their titles, then any page linked only from the text."""
    link = rf"\[([^\]]+)\]\({GITHUB}/{repo}/blob/main/(docs/[\w-]+\.md)[#)]"
    found: dict[str, str] = {}
    for label, name in re.findall(rf"^\| {link}", readme, re.M) + re.findall(link, readme):
        found.setdefault(name, label)
    return list(found.items())


# ---------------------------------------------------------------- pages
def mp4_seconds(path: Path) -> float:
    """Duration of an MP4 file, from its movie header (moov/mvhd), with no outside tool."""
    data = path.read_bytes()

    def boxes(start, end):
        i = start
        while i + 8 <= end:
            size, kind = struct.unpack(">I4s", data[i : i + 8])
            head = 8
            if size == 1:
                size, head = struct.unpack(">Q", data[i + 8 : i + 16])[0], 16
            elif size == 0:
                size = end - i
            yield kind, i + head, i + size
            i += size

    for kind, a, b in boxes(0, len(data)):
        if kind == b"moov":
            for k, c, _ in boxes(a, b):
                if k == b"mvhd":
                    if data[c] == 1:  # version 1: 64-bit times
                        scale, duration = struct.unpack(">IQ", data[c + 20 : c + 32])
                    else:
                        scale, duration = struct.unpack(">II", data[c + 12 : c + 20])
                    return duration / scale
    raise ValueError(f"{path}: no movie header")


def page_images(page: str) -> list[tuple[str, str]]:
    """(absolute address, alt text) of each image in a page's content (the header's logo left out)."""
    main = page.split("</header>", 1)[-1]
    out = []
    for tag in re.findall(r"<img\b[^>]*>", main):
        src = re.search(r'\bsrc="([^"]+)"', tag)
        alt = re.search(r'\balt="([^"]*)"', tag)
        if src:
            url = html.unescape(src.group(1))
            out.append(
                (SITE + url if url.startswith("/") else url, html.unescape(alt.group(1)) if alt else "")
            )
    return out


# the home page's videos: id of their section, file and poster under site/
VIDEOS = {"demo": ("demo.mp4", "demo_poster.jpg"), "bench": ("bench.mp4", "bench_poster.jpg")}


def demo_video(home: str, uploaded: str | None, section_id: str = "demo") -> dict:
    """A home page video as schema.org VideoObject: its name and description are its section's
    heading and paragraph, its duration is the file's."""
    file, poster = VIDEOS[section_id]
    section = re.search(rf'<section id="{section_id}".*?</section>', home, re.S).group(0)
    name = re.sub(r"<[^>]+>", "", re.search(r"<h2>(.*?)</h2>", section, re.S).group(1)).strip()
    text = re.sub(r"<[^>]+>", "", re.search(r"<p>(.*?)</p>", section, re.S).group(1))
    seconds = round(mp4_seconds(HERE / file))
    return {
        "@context": "https://schema.org",
        "@type": "VideoObject",
        "name": f"Primvaria: {name.lower()}",
        "description": " ".join(text.split()),
        "thumbnailUrl": f"{SITE}/{poster}",
        "contentUrl": f"{SITE}/{file}",
        "embedUrl": f"{SITE}/#{section_id}",
        "uploadDate": uploaded,
        "duration": f"PT{seconds // 60}M{seconds % 60}S",
        "publisher": {"@id": f"{SITE}/#author"},
    }


def wrap(layout: str, jsonld: str, where: str, title: str, description: str, content: str) -> str:
    page = layout
    for key, value in {
        "{title}": html.escape(title),
        "{description}": html.escape(description, quote=True),
        "{url}": SITE + where,
        "{jsonld}": f'<script type="application/ld+json">{jsonld}</script>' if where == "/" else "",
        "{content}": content.strip(),
    }.items():
        page = page.replace(key, value)
    return page


def header(eyebrow: str, title: str, lede: str = "", extra: str = "") -> str:
    lede = f'\n  <p class="lede">{lede}</p>' if lede else ""
    return f"""<section class="hero page"><div class="wrap">
  <p class="eyebrow">{eyebrow}</p>
  <h1>{html.escape(title)}</h1>{lede}{extra}
</div></section>"""


def prose(body: str) -> str:
    return f'<section class="doc"><div class="wrap">\n{body}\n</div></section>'


def subnav(repo: str, pages: list[tuple[str, str]], current: str) -> str:
    items = [(f"/{repo}/", "Overview")] + [(f"/{repo}/{Path(p).stem}/", t) for p, t in pages]
    here = ' aria-current="page"'
    links = "".join(
        f'<a href="{href}"{here if href == current else ""}>{html.escape(label)}</a>' for href, label in items
    )
    return f'\n  <nav class="subnav" aria-label="{repo.capitalize()} documentation">{links}</nav>'


def cards(home: str) -> dict[str, str]:
    """What the home page says of each generator, to head the generator's own page."""
    out = {}
    for repo in HEROES:
        m = re.search(rf"<h3><a [^>]*>{repo.capitalize()}</a></h3>.*?<p>(.*?)</p>", home, re.S)
        if not m:
            raise SystemExit(f"site/pages/index.html: no card for {repo}")
        out[repo] = m.group(1)
    return out


def build(out: Path, source: Source) -> dict[str, str]:
    """Write the site to ``out``; returns {path on the site: HTML}. The sitemap dates each page by
    the last commit of the files its content comes from."""
    layout = (HERE / "layout.html").read_text(encoding="utf-8")
    jsonld = (HERE / "jsonld.json").read_text(encoding="utf-8").strip()
    home = (HERE / "pages" / "index.html").read_text(encoding="utf-8")
    readmes = {repo: source.text(repo, "README.md") for repo in HEROES}
    pages_of = {repo: doc_links(readmes[repo], repo) for repo in HEROES}
    docs = {repo: {p for p, _ in pages_of[repo]} for repo in HEROES}
    site: dict[str, str] = {}
    made_of: dict[str, list[tuple[str, str]]] = {
        "/": [("primvaria", "site/pages/index.html")],
        "/engines/": [("primvaria", "site/pages/engines.html")],
    }

    videos = []
    for section_id, (file, _) in VIDEOS.items():
        video = demo_video(home, source.modified("primvaria", f"site/{file}", moment=True), section_id)
        if not video["uploadDate"]:
            del video["uploadDate"]
        videos.append(video)
    site["/"] = wrap(
        layout,
        jsonld,
        "/",
        "Primvaria · OpenUSD asset generators for robot simulation",
        "Open-source OpenUSD asset generators for robot simulation: grains, cloth, cables and hardware, "
        "every instance different, tested in Blender and MuJoCo.",
        home,
    ).replace(
        "</head>",
        "".join(
            f'<script type="application/ld+json">{json.dumps(v, ensure_ascii=False)}</script>\n'
            for v in videos
        )
        + "</head>",
        1,
    )
    site["/engines/"] = wrap(
        layout,
        jsonld,
        "/engines/",
        "Engine matrix · Primvaria",
        "Where each Primvaria generator stands in each engine: OpenUSD validators, Blender, MuJoCo, "
        "Isaac Sim.",
        (HERE / "pages" / "engines.html").read_text(encoding="utf-8"),
    )
    for path, (name, title, description) in OWN.items():
        _, body = title_and_body(source.text("primvaria", path))
        content = (
            header('<a href="/">Primvaria</a>', title, description)
            + "\n"
            + prose(render(body, "primvaria", path, docs))
        )
        site[f"/{name}/"] = wrap(layout, jsonld, f"/{name}/", f"{title} · Primvaria", description, content)
        made_of[f"/{name}/"] = [("primvaria", path)]

    lede = cards(home)
    card_alt = {
        repo: html.unescape(re.search(rf'<img src="/img/{repo}\.jpg" alt="([^"]+)"', home).group(1))
        for repo in HEROES
    }
    for repo in HEROES:
        name = repo.capitalize()
        install = f"""
  <div class="install">
    <div class="cmd">
      <span id="cmd">pip install {repo}</span><button type="button" data-copy="cmd">Copy</button>
    </div>
    <a class="btn" href="{GITHUB}/{repo}">Source on GitHub</a>
    <a class="btn" href="https://pypi.org/project/{repo}/">PyPI</a>
  </div>"""
        alt = html.escape(card_alt[repo], quote=True)
        plate = f'\n  <img class="plate" src="/img/{repo}.jpg" alt="{alt}" width="{WIDTH}" height="{HEIGHT}">'
        if repo in NO_PLATE:
            plate = ""
        top = header(
            '<a href="/">Primvaria</a> · generator',
            name,
            lede[repo],
            install + subnav(repo, pages_of[repo], f"/{repo}/") + plate,
        )
        body = render(sections(readmes[repo]), repo, "README.md", docs)
        description = re.sub(r"<[^>]+>", "", lede[repo])
        site[f"/{repo}/"] = wrap(
            layout, jsonld, f"/{repo}/", f"{name} · Primvaria", description, top + "\n" + prose(body)
        )
        made_of[f"/{repo}/"] = [(repo, "README.md")]
        for path, label in pages_of[repo]:
            where = f"/{repo}/{Path(path).stem}/"
            title, text = title_and_body(source.text(repo, path))
            top = header(
                f'<a href="/">Primvaria</a> · <a href="/{repo}/">{name}</a>',
                title or label,
                "",
                subnav(repo, pages_of[repo], where),
            )
            site[where] = wrap(
                layout,
                jsonld,
                where,
                f"{title or label} · {name} · Primvaria",
                f"{name}: {(title or label).lower()}.",
                top + "\n" + prose(render(text, repo, path, docs)),
            )
            made_of[where] = [(repo, path)]

    shutil.rmtree(out, ignore_errors=True)
    (out / "img").mkdir(parents=True)
    for f in STATIC:
        shutil.copy(HERE / f, out / f)
    for repo, (name, anchor) in HEROES.items():
        cover(source.image(repo, name), anchor).save(out / "img" / f"{repo}.jpg", quality=84, optimize=True)
    for where, page in site.items():
        target = out / where.strip("/") / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page, encoding="utf-8")
    dates = {}
    for where in site:
        known = [d for d in (source.modified(r, p) for r, p in made_of[where]) if d]
        dates[where] = max(known) if known else None

    def x(text: str) -> str:
        return html.escape(text, quote=False)

    def media(where: str) -> str:
        """The page's images, and the home page's videos, as sitemap extensions."""
        seen, parts = set(), []
        for url, _ in page_images(site[where]):
            if url not in seen:
                seen.add(url)
                parts.append(f"<image:image><image:loc>{x(url)}</image:loc></image:image>")
        for v in videos if where == "/" else []:
            seconds = round(mp4_seconds(HERE / v["contentUrl"].rsplit("/", 1)[1]))
            parts.append(
                "<video:video>"
                f"<video:thumbnail_loc>{x(v['thumbnailUrl'])}</video:thumbnail_loc>"
                f"<video:title>{x(v['name'])}</video:title>"
                f"<video:description>{x(v['description'])}</video:description>"
                f"<video:content_loc>{x(v['contentUrl'])}</video:content_loc>"
                f"<video:duration>{seconds}</video:duration>"
                + (
                    f"<video:publication_date>{v['uploadDate']}</video:publication_date>"
                    if "uploadDate" in v
                    else ""
                )
                + "</video:video>"
            )
        return "".join(parts)

    urls = "\n".join(
        f"  <url><loc>{SITE}{where}</loc>"
        + (f"<lastmod>{dates[where]}</lastmod>" if dates[where] else "")
        + media(where)
        + "</url>"
        for where in sorted(site)
    )
    (out / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"'
        ' xmlns:image="http://www.google.com/schemas/sitemap-image/1.1"'
        ' xmlns:video="http://www.google.com/schemas/sitemap-video/1.1">\n'
        f"{urls}\n</urlset>\n",
        encoding="utf-8",
    )
    return site


def broken_links(out: Path, site: dict[str, str]) -> list[str]:
    """Links inside the site that lead to no file or to no anchor."""
    ids = {where: set(re.findall(r'\bid="([^"]+)"', page)) for where, page in site.items()}
    problems = []
    for where, page in site.items():
        for url in re.findall(r'\b(?:href|src|poster)="([^"]+)"', page):
            url = html.unescape(url)
            if url.startswith("#"):
                url = where + url
            if not url.startswith("/"):
                continue
            path, _, frag = url.partition("#")
            if path in site:
                if frag and frag not in ids[path]:
                    problems.append(f"{where}: no anchor #{frag} in {path}")
            elif not (out / path.lstrip("/")).is_file():
                problems.append(f"{where}: nothing at {path}")
    return problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--local", type=Path, default=None, help="folder holding clones of the four generators")
    ap.add_argument("--out", type=Path, default=ROOT / "_site")
    args = ap.parse_args(argv)
    site = build(args.out, Source(args.local))
    problems = broken_links(args.out, site)
    for p in problems:
        print(p)
    print(
        f"{len(site)} pages written to {args.out}" + (f", {len(problems)} broken links" if problems else "")
    )
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
