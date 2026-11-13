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
    site = site_build.build(out, site_build.Source(local), "2026-11-13")
    return out, site


def test_one_page_per_subject(built):
    out, site = built
    expected = {"/", "/engines/", "/contract/", "/mission/"}
    for repo in site_build.HEROES:
        expected |= {f"/{repo}/", f"/{repo}/usage/", f"/{repo}/limits/"}
    assert set(site) == expected
    for where in site:
        assert (out / where.strip("/") / "index.html").is_file()
    assert all((out / "img" / f"{repo}.jpg").is_file() for repo in site_build.HEROES)
    sitemap = (out / "sitemap.xml").read_text(encoding="utf-8")
    assert all(f"<loc>https://primvaria.com{where}</loc>" in sitemap for where in site)


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
