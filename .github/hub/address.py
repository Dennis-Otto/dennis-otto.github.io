"""The address dennis-otto.github.io as a whole.

This website lives at the root of the address, which the websites of the projects share,
each in a folder of its own. So the hooks also write the files that crawlers and
security researchers look for at the root of a host alone: robots.txt with the sitemap
of every website of the address, security.txt (RFC 9116), and llms.txt
(https://llmstxt.org/), the map of the address for AI assistants: a section for every
group of the home page with its projects, each with its website, its first button and
the guides of its website, such as its installation, which the hooks take from its
search index, in English with the German page of each. The home page of the default
language gets the structured data of the address: the name of the website, its owner and
the projects; and the root of the address, not index.html in it, as its canonical
address.

A project whose website moved to another folder of the address, as a renamed repository
moves it, names the folders where it lived in former. GitHub Pages serves this website
for every path that no project serves, so the old addresses reach it: the hooks write a
page at every old address that former/<folder>.txt lists, which leads to the same page
in the new folder, and the 404 page leads every other address of the old folder there,
such as that of a picture. The card of the project keeps the anchor of each old folder
on the home page.
"""

from __future__ import annotations

import gzip
import json
import os
import re
from datetime import UTC, date, datetime, timedelta
from html import escape
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from .catalog import Catalog, HOME, LANGUAGE_NAMES
from .search import Guide, language_of
from .releases import RELEASES_PAGE

# The owner of the address, whom the structured data of the home page names.
OWNER = "Dennis Otto"
PROFILE = "https://github.com/Dennis-Otto"
SPONSORS = "https://github.com/sponsors/Dennis-Otto"
# security.txt: where a vulnerability of any website of the address is reported
# privately, and the page of this website that describes its security. The file
# stands at its place under /.well-known/ and, for older tools, at the root.
CONTACT = "https://github.com/Dennis-Otto/dennis-otto.github.io/security/advisories/new"
POLICY = "security.html"
SECURITY_TXT = (".well-known/security.txt", "security.txt")

# The title of the preview card of the home page, as the social plugin of Material
# writes it into the head of the page.
SOCIAL_TITLE = re.compile(r'(<meta property="(?:og|twitter):title" content=")[^"]*(">)')
# How long security.txt holds from the day of the build: its Expires is the midnight
# a year later, less than a year ahead, as RFC 9116 recommends. Every change of main
# publishes the website again, and with it a later date.
VALID = timedelta(days=365)
# The files that name the sitemaps: robots.txt at the root of the address, and the
# sitemap in every folder of the pages of a website.
ROBOTS = "robots.txt"
SITEMAP = "sitemap.xml"
# llms.txt (https://llmstxt.org/) at the root of the address: the map of every
# website of the address in Markdown, for AI assistants, in the default language;
# and the key of config.extra that keeps its summary, the description of the
# website in the default language, which on_config reads before the i18n plugin
# gives each further language its own.
LLMS_TXT = "llms.txt"
LLMS = "llms_summary"

# The old addresses of a website that moved to another folder of the address. The
# pages of its old website are listed in FORMER/<folder>.txt, one on each line by
# its path from that folder, such as games.html or de/index.html; an empty line and
# one that starts with # are none. The build writes a page at each, in the folder
# of this website, that leads to the same path in the folder of the website now: at
# once with its script, which keeps the query and the fragment of the address, and
# without the script by its refresh. A reader who stops on it sees the texts of
# MOVED in the language of the page, those of English in a language without its
# own, and the new address, which search engines take as its canonical one; they
# list no page at an old address.
MOVED = {
    "en": ("This page has moved", "This page has moved to the website of {}:"),
    "de": (
        "Diese Seite ist umgezogen",
        "Diese Seite ist auf die Website von {} umgezogen:",
    ),
}


# The files at the root of the address, and the structured data of the home page.


def sitemaps(catalog: Catalog, site_url: str) -> list[str]:
    """The sitemap of this website and that of every project whose documentation
    lives at the same address, each once."""
    found = [urljoin(site_url, SITEMAP)]
    for project in catalog.projects:
        if project.docs is None:
            continue
        # The sitemap of a website in several languages lists every language.
        url = project.docs.url[catalog.default]
        if url.startswith(site_url):
            found.append(urljoin(url, SITEMAP))
    return list(dict.fromkeys(found))


def robots(catalog: Catalog, site_url: str) -> str:
    """robots.txt: every crawler may read every website of the address, and finds
    their sitemaps here, so that a new project in the catalog gets its line."""
    lines = [
        f"# Every website at {site_url} with its sitemap, from projects.toml of",
        "# https://github.com/Dennis-Otto/dennis-otto.github.io",
        "User-agent: *",
        "Allow: /",
        "",
        *(f"Sitemap: {url}" for url in sitemaps(catalog, site_url)),
    ]
    return "\n".join(lines) + "\n"


def security_txt(catalog: Catalog, site_url: str, today: date) -> str:
    """security.txt (RFC 9116) for every website of the address, valid until the
    midnight a year after today, the day of the build."""
    expires = (today + VALID).isoformat()
    lines = [
        f"# Report a vulnerability of any website at {site_url} privately.",
        f"Contact: {CONTACT}",
        f"Expires: {expires}T00:00:00Z",
        f"Preferred-Languages: {', '.join(catalog.languages)}",
        *(f"Canonical: {urljoin(site_url, path)}" for path in SECURITY_TXT),
        f"Policy: {urljoin(site_url, POLICY)}",
    ]
    return "\n".join(lines) + "\n"


# The brackets of the name of a link, which a text of llms.txt can't hold there, as
# its parsers take the first ] for the end of the name, and what takes their place.
LINK_NAME = str.maketrans("[]", "()")


def one_line(text: str) -> str:
    """text for llms.txt: on one line, with a space between two words, and with
    parentheses for its brackets."""
    return " ".join(text.split()).translate(LINK_NAME)


def llms_item(
    catalog: Catalog,
    name: dict[str, str],
    url: dict[str, str],
    note: dict[str, str] | None = None,
    *,
    depth: int = 0,
) -> str:
    """An item of a list of llms.txt at depth, below the item of its project: name,
    which links url, in the default language, after it note, and the page of every
    further language that has an address of its own, with its name, such as
    "In German: [Erste Schritte](.../de/getting-started.html)"."""
    default = catalog.default
    notes = [one_line(note[default])] if note else []
    for language in catalog.languages[1:]:
        address = url.get(language, url[default])
        if address != url[default]:
            label = LANGUAGE_NAMES.get(language, language)
            title = one_line(name.get(language, name[default]))
            notes.append(f"In {label}: [{title}]({address})")
    item = f"{'  ' * depth}- [{one_line(name[default])}]({url[default]})"
    return f"{item}: {'. '.join(notes)}" if notes else item


def llms_txt(
    catalog: Catalog,
    site_url: str,
    summary: str | None,
    found: dict[str, list[Guide]],
) -> str:
    """llms.txt (https://llmstxt.org/) of the address: the map of every website at
    site_url in Markdown, for AI assistants, in the default language. Its title is
    the owner, its summary that of this website, and a section for every group of the
    home page, under its heading, lists its projects: each with its name, which links
    its website, and its tagline, and below it the first button of its card, the
    project without a card that it names as its second, such as the dashboard, and
    the guides of its website in found, by its slug. A link names the page of every
    further language with an address of its own, and none leads to a decision
    record, which no guide is."""
    others = [LANGUAGE_NAMES.get(language, language) for language in catalog.languages]
    translated = (
        f", each with its page in {' and '.join(others[1:])} where there is one"
        if others[1:]
        else ""
    )
    lines = [f"# {OWNER}", ""]
    if summary:
        lines += [f"> {one_line(summary)}", ""]
    lines += [
        "Each project below links its website, the first step for its users, such "
        "as its installation, and the guides of its website that a reader looks for "
        f"first{translated}. The [search]({site_url}) of this website finds the pages "
        "of every website, and the "
        f"[Releases page]({urljoin(site_url, RELEASES_PAGE)}) has the notes of the "
        "latest releases of every project.",
        "",
    ]
    projects = {project.slug: project for project in catalog.projects}
    for group in catalog.groups:
        lines += [f"## {one_line(group.heading[catalog.default])}", ""]
        for project in catalog.members(group):
            lines += [
                llms_item(catalog, project.name, project.website, project.tagline),
                llms_item(catalog, project.start.label, project.start.url, depth=1),
            ]
            # A project with a card of its own has its own item.
            if project.second is not None and projects[project.second].group is None:
                second = projects[project.second]
                lines.append(
                    llms_item(
                        catalog, second.name, second.website, second.tagline, depth=1
                    )
                )
            lines += [
                llms_item(catalog, guide.title, guide.url, depth=1)
                for guide in found.get(project.slug, [])
            ]
        lines.append("")
    return "\n".join(lines)


def build_date() -> date:
    """The day of the build in UTC, or that of SOURCE_DATE_EPOCH, which makes the
    same build come out the same on every day."""
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    moment = datetime.fromtimestamp(int(epoch), UTC) if epoch else datetime.now(UTC)
    return moment.date()


def home_address(site_url: str) -> re.Pattern[str]:
    """The address of the home page of the default language as index.html, as a
    sitemap of the website at site_url names it where it should name the root."""
    return re.compile(rf'(?<=[">]){re.escape(urljoin(site_url, HOME))}(?=["<])')


def sitemaps_at_root(site: Path, site_url: str) -> None:
    """Lead every sitemap of the website in site to the root of the address where it
    names the home page of the default language as index.html: as the version in
    that language of the German home page, which the i18n plugin lists without the
    page and so without its canonical address. The packed sitemap.xml.gz keeps the
    time of its build."""
    home = home_address(site_url)
    for path in site.rglob(SITEMAP):
        text = path.read_text(encoding="utf-8")
        path.write_text(home.sub(site_url, text), encoding="utf-8", newline="\n")
    packed = site / f"{SITEMAP}.gz"
    if packed.is_file():
        with gzip.GzipFile(packed) as reader:
            text = reader.read().decode("utf-8")
            built = reader.mtime
        with gzip.GzipFile(packed, "wb", mtime=built) as writer:
            writer.write(home.sub(site_url, text).encode("utf-8"))


def structured_data(
    catalog: Catalog,
    site_url: str,
    site_name: str,
    works: dict[str, dict[str, str]] | None = None,
) -> str:
    """The tags for the head of the home page: the link to the owner's profile, and
    the JSON-LD of the website, its owner and every project with a repository, whose
    runtime platform is what it works with of works, by its slug, where the build
    has that, or else its platform.

    Search engines take the name of a website from the home page at the root of a
    host alone, so this one names it for every website of the address. Schema.org
    gives the requirements of the code of a SoftwareSourceCode its runtimePlatform,
    such as Python 2.3; softwareRequirements is for a SoftwareApplication, whose
    rich results Google judges by its price and its ratings.
    """
    language = catalog.default
    works = works or {}
    owner = {"@id": f"{site_url}#owner"}
    software = [project for project in catalog.projects if project.repo is not None]
    graph: list[dict[str, Any]] = [
        {
            "@type": "WebSite",
            "@id": f"{site_url}#website",
            "url": site_url,
            "name": site_name,
            "inLanguage": list(catalog.languages),
            "publisher": owner,
        },
        {
            "@type": "Person",
            **owner,
            "name": OWNER,
            "url": site_url,
            "sameAs": [PROFILE, SPONSORS],
        },
        {
            "@type": "ItemList",
            "@id": f"{site_url}#projects",
            "name": "Projects",
            "numberOfItems": len(software),
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": position,
                    "item": {
                        "@type": "SoftwareSourceCode",
                        # The anchor of its card on the home page.
                        "@id": f"{site_url}#{project.slug}",
                        "name": project.name[language],
                        "description": project.summary[language],
                        "url": project.website[language],
                        "codeRepository": f"https://github.com/{project.repo}",
                        "license": f"https://spdx.org/licenses/{project.license}.html",
                        "runtimePlatform": works.get(project.slug, {}).get(language)
                        or project.platform,
                        "isAccessibleForFree": True,
                        # Not the author: HomeDarts for Autodarts began as a
                        # fork.
                        "maintainer": owner,
                    },
                }
                for position, project in enumerate(software, start=1)
            ],
        },
    ]
    data = json.dumps(
        {"@context": "https://schema.org", "@graph": graph},
        ensure_ascii=False,
        separators=(",", ":"),
    )
    # No text of the catalog can end the script early, such as with </script>.
    data = data.replace("<", "\\u003c")
    return (
        f'<link rel="me" href="{PROFILE}">\n'
        f'<script type="application/ld+json">{data}</script>\n'
    )


# The old addresses of a website that moved.


def moved_to(folder: str, page: str) -> str:
    """The address of page, a path from the folder of a former website, in folder,
    the address of the folder of the website now: that of its folder for an
    index.html, as MkDocs links such a page."""
    return urljoin(folder, re.sub(r"(^|/)index\.html$", r"\1", page))


def moved_page(name: str, target: str, language: str) -> str:
    """The HTML of a page at an old address in language, which leads to target, the
    address of the same page on the website of the project name now.

    Its script leads there at once, with the query and the fragment of the old
    address, such as #a-section; without the script, the refresh leads there
    without them, and a reader who stops sees the texts of MOVED and the link.
    Search engines take target as its canonical address and list no page here.
    """
    title, sentence = MOVED.get(language, MOVED["en"])
    href = escape(target)
    # No address can end the script early, such as with </script>.
    script = json.dumps(target).replace("<", "\\u003c")
    return "\n".join(
        [
            "<!doctype html>",
            f'<html lang="{escape(language)}">',
            "<head>",
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            f"<title>{escape(title)} - {escape(name)}</title>",
            '<meta name="robots" content="noindex">',
            f'<link rel="canonical" href="{href}">',
            f'<meta http-equiv="refresh" content="0; url={href}">',
            f"<script>location.replace({script} + location.search + location.hash);"
            "</script>",
            "</head>",
            "<body>",
            f"<p>{escape(sentence.format(name))} "
            f'<a href="{href}">{escape(target.removeprefix("https://"))}</a></p>',
            "</body>",
            "</html>",
            "",
        ]
    )


def moved_pages(catalog: Catalog) -> dict[str, str]:
    """The page at every old address of a website that moved, by its path in the
    folder of this website, such as ha-autodarts/de/games.html, with its HTML: in
    the language of its folder, and leading to the same path in the folder of the
    website now."""
    moves = catalog.moves()
    pages: dict[str, str] = {}
    for project in catalog.projects:
        for folder in project.former:
            for page in catalog.former_pages.get(folder, ()):
                language = language_of(catalog, page)
                target = moved_to(moves[folder], page)
                pages[f"{folder}/{page}"] = moved_page(
                    project.name[language], target, language
                )
    return pages
