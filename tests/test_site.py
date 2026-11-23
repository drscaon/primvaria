"""The site is built page by page from the repositories' Markdown files."""

import importlib.util
import re
from pathlib import Path

import pytest

pytest.importorskip("markdown")
Image = pytest.importorskip("PIL.Image")

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location("site_build", ROOT / "site" / "build.py")
site_build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(site_build)

GH = "https://github.com/drscaon"


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    """The site built from four made-up generator repositories."""
    local = tmp_path_factory.mktemp("repos")
    for repo, (image, _) in site_build.HEROES.items():
        docs = local / repo / "docs"
        (docs / "images").mkdir(parents=True)
        Image.new("RGB", (800, 600), "#336699").save(docs / "images" / image)
        blob = f"{GH}/{repo}/blob/main"
        readme = [
            '<h1 align="center">logo and badges</h1>',
            "## What it does",
            "Makes things; see [Limits](#limits), the [matrix](https://primvaria.com/#engines),",
            f"the [contract]({GH}/primvaria/blob/main/docs/contract.md)",
            f"and a [detail]({blob}/docs/usage.md#options-of-the-tool).",
            "## Limits",
            "Some.",
            "## Documentation",
            "| Page | What it holds |\n|---|---|",
            f"| [Usage in depth]({blob}/docs/usage.md) | Options. |",
            f"| [Limits and roadmap]({blob}/docs/limits.md) | Limits. |",
        ]
        usage = [
            "# Usage in depth",
            "Options.",
            f"Part of the [{repo.capitalize()}](../README.md) documentation.",
            "## Options of `the tool`",
            "| a | b |\n|---|---|\n| 1 | 2 |",
            "See [limits](limits.md#known-limits), the [overview](../README.md#what-it-does),",
            "a [script](../scripts/x.py) and ![a picture](images/x.png).",
        ]
        text = "\n\n".join(readme).replace("|\n\n|", "|\n|").replace(",\n\n", ",\n")
        (local / repo / "README.md").write_text(text + "\n", encoding="utf-8")
        (docs / "usage.md").write_text("\n\n".join(usage).replace(",\n\n", ",\n") + "\n", encoding="utf-8")
        (docs / "limits.md").write_text(
            "# Limits and roadmap\n\n## Known limits\n\nSome.\n", encoding="utf-8"
        )
    out = tmp_path_factory.mktemp("site")
    site = site_build.build(out, site_build.Source(local))
    return out, site


def test_one_page_per_subject(built):
    out, site = built
    expected = {"/", "/engines/", "/contract/", "/stability/", "/mission/"}
    for repo in site_build.HEROES:
        expected |= {f"/{repo}/", f"/{repo}/usage/", f"/{repo}/limits/"}
    assert set(site) == expected
    for where in site:
        assert (out / where.strip("/") / "index.html").is_file()
    assert all((out / "img" / f"{repo}.jpg").is_file() for repo in site_build.HEROES)
    sitemap = (out / "sitemap.xml").read_text(encoding="utf-8")
    assert all(f"<loc>https://primvaria.com{where}</loc>" in sitemap for where in site)


def test_sitemap_dates_are_the_content_s(built, tmp_path):
    """A page's lastmod is the last commit of its own source, not the day of the build; a source
    whose history is unknown (here the made-up generators, not git repositories) gets no date."""
    import subprocess

    out, _ = built
    sitemap = (out / "sitemap.xml").read_text(encoding="utf-8")
    entries = dict(
        re.findall(r"<loc>https://primvaria.com([^<]*)</loc>(?:<lastmod>([^<]*)</lastmod>)?", sitemap)
    )
    assert entries["/granulaire/"] == ""  # no history to read
    shallow = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "--is-shallow-repository"], capture_output=True, text=True
    ).stdout.strip()
    if shallow != "false":
        assert entries["/mission/"] == ""
        return
    expected = subprocess.run(
        ["git", "-C", str(ROOT), "log", "-1", "--format=%cs", "--", "MISSION.md"],
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert entries["/mission/"] == expected


def test_no_link_inside_the_site_is_broken(built):
    out, site = built
    assert site_build.broken_links(out, site) == []


def test_a_broken_link_is_found(built):
    out, site = built
    bad = dict(site, **{"/x/": '<a href="/nowhere/">a</a> <a href="/engines/#no-such-anchor">b</a>'})
    assert len(site_build.broken_links(out, bad)) == 2


def test_links_written_for_github_point_inside_the_site(built):
    _, site = built
    page = site["/granulaire/"]
    assert "logo and badges" not in page  # the README's own header is replaced by the page's
    assert 'href="/granulaire/usage/#options-of-the-tool"' in page
    assert 'href="/engines/"' in page and 'href="/contract/"' in page
    assert 'href="#limits"' in page and 'id="limits"' in page
    doc = site["/granulaire/usage/"]
    assert 'id="options-of-the-tool"' in doc  # the anchor GitHub gives the heading
    assert 'href="/granulaire/limits/#known-limits"' in doc
    assert 'href="/granulaire/#what-it-does"' in doc
    # what the site does not hold goes to GitHub: files as pages, images as files
    assert f'href="{GH}/granulaire/blob/main/scripts/x.py"' in doc
    assert 'src="https://raw.githubusercontent.com/drscaon/granulaire/main/docs/images/x.png"' in doc
    assert "Part of the" not in doc and '<div class="scroll"><table>' in doc


def test_every_page_has_its_own_title_and_address(built):
    _, site = built
    titles = [re.search(r"<title>(.*?)</title>", page).group(1) for page in site.values()]
    assert len(set(titles)) == len(titles)
    for where, page in site.items():
        assert f'<link rel="canonical" href="https://primvaria.com{where}">' in page
        assert "{" + "content}" not in page and "{" + "title}" not in page


def test_sub_navigation_follows_the_documentation_table(built):
    _, site = built
    nav = re.search(r'<nav class="subnav".*?</nav>', site["/maillage/limits/"], re.S).group(0)
    assert re.findall(r">([^<]+)</a>", nav) == ["Overview", "Usage in depth", "Limits and roadmap"]
    assert 'href="/maillage/limits/" aria-current="page"' in nav


def test_every_content_image_has_alt_text(built):
    """Search engines and screen readers read an image by its alt text: every image in a page's
    content has one (the header's logo, beside the name it shows, is decorative)."""
    _, site = built
    for where, page in site.items():
        for url, alt in site_build.page_images(page):
            assert alt.strip(), f"{where}: {url} has no alt text"


def test_sitemap_lists_each_page_s_images_and_the_videos(built):
    import xml.etree.ElementTree as ET

    out, site = built
    ns = {
        "s": "http://www.sitemaps.org/schemas/sitemap/0.9",
        "image": "http://www.google.com/schemas/sitemap-image/1.1",
        "video": "http://www.google.com/schemas/sitemap-video/1.1",
    }
    root = ET.parse(out / "sitemap.xml").getroot()
    for url in root.findall("s:url", ns):
        where = url.find("s:loc", ns).text.removeprefix("https://primvaria.com")
        listed = [i.find("image:loc", ns).text for i in url.findall("image:image", ns)]
        assert listed == list(dict.fromkeys(u for u, _ in site_build.page_images(site[where]))), where
        videos = url.findall("video:video", ns)
        assert len(videos) == (len(site_build.VIDEOS) if where == "/" else 0), where
    videos = root.find("s:url", ns).findall("video:video", ns)
    for video, (file, poster) in zip(videos, site_build.VIDEOS.values(), strict=True):
        seconds = round(site_build.mp4_seconds(ROOT / "site" / file))
        assert int(video.find("video:duration", ns).text) == seconds > 0
        assert video.find("video:content_loc", ns).text.endswith("/" + file)
        assert video.find("video:thumbnail_loc", ns).text.endswith("/" + poster)
        for tag in ("thumbnail_loc", "title", "description", "content_loc"):
            assert video.find(f"video:{tag}", ns).text.strip(), tag


def test_home_page_describes_its_videos(built):
    """The home page carries a schema.org VideoObject per video with what Google requires (name, description,
    thumbnail, upload date) and the duration of the file itself."""
    import json
    import subprocess

    _, site = built
    blocks = [
        json.loads(b) for b in re.findall(r'<script type="application/ld\+json">(.*?)</script>', site["/"])
    ]
    videos = [b for b in blocks if b.get("@type") == "VideoObject"]
    assert len({v["name"] for v in videos}) == len(videos) == len(site_build.VIDEOS)
    for video, (file, _) in zip(videos, site_build.VIDEOS.values(), strict=True):
        for key in ("name", "description", "thumbnailUrl", "contentUrl"):
            assert video[key], key
        seconds = round(site_build.mp4_seconds(ROOT / "site" / file))
        assert video["duration"] == f"PT{seconds // 60}M{seconds % 60}S"
    shallow = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "--is-shallow-repository"], capture_output=True, text=True
    ).stdout.strip()
    for video in videos if shallow == "false" else []:
        assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d", video["uploadDate"])
    assert all('"VideoObject"' not in page for where, page in site.items() if where != "/")


def test_quincaillerie_page_has_no_plate(built):
    out, _ = built
    page = (out / "quincaillerie" / "index.html").read_text(encoding="utf-8")
    assert 'class="plate"' not in page
    assert 'class="plate"' in (out / "filaire" / "index.html").read_text(encoding="utf-8")
