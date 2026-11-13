"""What the check of the built website and the watch of the live websites read of
the pages of a website, and the files that the fix of a finding of either names.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from html.parser import HTMLParser
from pathlib import Path

from .catalog import HOME, SITE

# The address of a page in a sitemap.
LOCATION = re.compile(r"<loc>\s*([^<]*?)\s*</loc>")
# An address of a sitemap, with the day of its last change, and the day of a release
# that a page shows, as news() and release_history() of RELEASES write it.
SITEMAP_URL = re.compile(r"<url>.*?</url>", re.DOTALL)
LAST_CHANGE = re.compile(r"<lastmod>\s*(\d{4}-\d{2}-\d{2})")
RELEASED = re.compile(r'data-released="(\d{4}-\d{2}-\d{2})"')

# The files that the fix of a finding names: the one that mkdocs.yml names, and those
# with the code of what it writes.
HOOKS = ".github/mkdocs_project.py"
ADDRESS = ".github/hub/address.py"
EVENTS = ".github/hub/events.py"
RENDER = ".github/hub/render.py"
SEARCH = ".github/hub/search.py"
RELEASES = ".github/hub/releases.py"


class Built(HTMLParser):
    """What the check reads of a built page: the id of every element, its cards, the
    address of every picture and of those that load only as they come into view, its
    canonical address, its refresh, every script with its type, the text of every
    script with an id by its id, and the attributes of every element of a
    repository, one with a data-repo, such as the place of a newer release of the
    Releases page."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: set[str] = set()
        self.cards = 0
        self.pictures: list[str] = []
        self.lazy: list[str] = []
        self.canonical: list[str] = []
        self.refresh: list[str] = []
        self.scripts: list[tuple[str, str]] = []
        self.named: dict[str, str] = {}
        self.of_repos: list[dict[str, str]] = []
        self.script: tuple[str, str, list[str]] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {name: value or "" for name, value in attrs}
        if "id" in values:
            self.ids.add(values["id"])
        if "data-repo" in values:
            self.of_repos.append(values)
        if tag == "div" and "card" in values.get("class", "").split():
            self.cards += 1
        elif tag == "img":
            self.pictures.append(values.get("src", ""))
            if values.get("loading") == "lazy":
                self.lazy.append(values.get("src", ""))
        elif tag == "link" and values.get("rel") == "canonical":
            self.canonical.append(values.get("href", ""))
        elif tag == "meta" and values.get("http-equiv", "").lower() == "refresh":
            self.refresh.append(values.get("content", ""))
        elif tag == "script":
            self.script = (values.get("type", ""), values.get("id", ""), [])

    def handle_data(self, data: str) -> None:
        if self.script is not None:
            self.script[2].append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self.script is not None:
            kind, name, parts = self.script
            text = "".join(parts)
            self.scripts.append((kind, text))
            if name:
                self.named[name] = text
            self.script = None


def built(site: Path, name: str) -> Built | None:
    """What the check reads of the page name of the website in site, or None when the
    website lacks it."""
    path = site / name
    if not path.is_file():
        return None
    page = Built()
    page.feed(path.read_text(encoding="utf-8", errors="replace"))
    page.close()
    return page


def text_fields(text: str) -> dict[str, list[str]]:
    """The values of every field of text, a security.txt or a robots.txt, by its
    name in lower case, as both compare names without case, without the comments."""
    found: dict[str, list[str]] = {}
    for line in text.splitlines():
        name, colon, value = line.partition(":")
        if colon and not name.lstrip().startswith("#"):
            found.setdefault(name.strip().lower(), []).append(value.strip())
    return found


def page_at(site: Path, url: str) -> Path | None:
    """The file of the website in site that url leads to, index.html for a folder, or
    None for an address outside the website."""
    if not url.startswith(SITE):
        return None
    path = url.removeprefix(SITE).partition("#")[0].partition("?")[0]
    if not path or path.endswith("/"):
        path += HOME
    return site / path


def dated_before_releases(site: Path, sitemap: str) -> Iterator[tuple[str, str, str]]:
    """Each page of the website in site that sitemap, the text of one of its sitemaps,
    dates before the newest release that the page shows: its address, the day of its
    last change in sitemap, and the day of that release."""
    for url in SITEMAP_URL.findall(sitemap):
        location, changed = LOCATION.search(url), LAST_CHANGE.search(url)
        if location is None or changed is None:
            continue
        path = page_at(site, location[1])
        if path is None or not path.is_file():
            continue
        page = path.read_text(encoding="utf-8", errors="replace")
        day = max(RELEASED.findall(page), default="")
        if day > changed[1]:
            yield location[1], changed[1], day
