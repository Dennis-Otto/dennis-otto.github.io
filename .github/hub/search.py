"""The search box of the website finds the documentation of every project too:
after the build, the hooks download the search index of every project website at the
address and add its pages and sections to the index of this website, each title of a
page after the short name of its project, such as "HomeDarts › Cricket", and each text
cut to a short excerpt. A project whose index can't be downloaded stays out of the
search until the next build, which never fails for it. The Catalog workflow builds the
website every day, so that the search follows the projects.
"""

from __future__ import annotations

import gzip
import json
import os
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from enum import IntEnum
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, NamedTuple
from urllib.parse import quote, urljoin

from . import web
from .catalog import Catalog, Project, cell, log
from .reader import folder_of

# The search of the website, which finds the documentation of every project too. The
# search plugin writes one index for every language of a website, at SEARCH_INDEX in
# its folder; the hooks add the pages and sections of the index of every project
# website at the address to that of this website. A download may take
# SEARCH_TIMEOUT seconds and is tried TRIES times. A section keeps EXCERPT
# characters of its text at most, as plain text without its code, such as the
# source of a diagram; and the projects add BUDGET bytes at most to the index,
# packed with gzip as GitHub Pages sends it, since every page loads the index. The
# title of a page of a project starts with the short name of the project and
# SEPARATOR, such as "HomeDarts › Cricket".
SEARCH_INDEX = "search/search_index.json"
# The key of config.extra that keeps the entries of the project websites for the
# build of each further language, which downloads no index again.
SEARCH = "project_search"
EXCERPT = 200
BUDGET = 120_000
SEPARATOR = " › "
# What an entry of a project website is worth to the search follows from the name of
# its page, the last part of its location without .html, in every language. The
# pages that a reader looks for first are START_PAGES, in the order in which a reader
# needs them, which llms.txt keeps, and those for maintainers MAINTAINER_PAGES; a
# page in a folder named DECISIONS, at any depth, is a decision record, and the
# search keeps its page but none of its sections. The budget gives up the sections
# of the pages for maintainers first and the entries of the pages last. The search
# of Material ranks the matches of an entry with a boost higher or lower: those of
# START_PAGES with START_BOOST, those of the pages for maintainers and of every
# decision record with LOW_BOOST, this website's own records too.
START_PAGES = (
    "getting-started",
    "install",
    "installation",
    "guide",
    "faq",
    "troubleshooting",
)
MAINTAINER_PAGES = frozenset(
    "automation changelog development releases roadmap".split()
)
DECISIONS = "decisions"
START_BOOST = 2
LOW_BOOST = 0.5
# The elements of HTML that a line of text ends at, where the excerpt of a section
# puts a space between their texts, and that of a block of code, which it leaves out.
BLOCKS = frozenset(
    "address blockquote br dd details div dl dt figcaption figure h1 h2 h3 h4 h5 h6 "
    "hr li ol p pre section summary table td th tr ul".split()
)
CODE = "pre"


@dataclass(frozen=True)
class Website:
    """The documentation of a project at the address, in a folder of its own, such
    as homedarts-for-autodarts/, which every location of its search index is
    relative to."""

    project: Project
    folder: str


class Rank(IntEnum):
    """What an entry of a project website is worth to the search, the highest last:
    the budget gives up the entries of the lowest rank first."""

    # A section of a page for maintainers, such as the changelog.
    MAINTAINERS = 1
    # A section of any other page.
    OTHER = 2
    # A section of a page that a reader looks for first, such as the installation.
    START = 3
    # The entry of a page: its title, and its text before its first heading.
    PAGE = 4


class Entry(NamedTuple):
    """An entry of a project website, as the index of this website holds it, and
    what it is worth to the search."""

    rank: Rank
    doc: dict[str, Any]


def page_name(page: str) -> str:
    """The name of page, the location of a page of a website without its #: its last
    part without .html, such as installation for de/installation.html or
    installation/, or "" for the home page of the website."""
    names = [part.removesuffix(".html") for part in page.split("/") if part]
    # A page kept as the index of its folder, such as guide/index.html, is named
    # after its folder.
    if len(names) > 1 and names[-1] == "index":
        names.pop()
    return names[-1] if names else ""


def rank_of(page: str) -> Rank | None:
    """The rank of the sections of page, the location of a page of a website without
    its #, such as de/installation.html or installation/, or None for a decision
    record, whose sections the search leaves out."""
    if DECISIONS in page.split("/")[:-1]:
        return None
    name = page_name(page)
    if name in START_PAGES:
        return Rank.START
    if name in MAINTAINER_PAGES:
        return Rank.MAINTAINERS
    return Rank.OTHER


def boost_of(location: str) -> float | None:
    """The boost of the search for the entry at location and every entry of its page,
    or None for one that the search ranks as it is."""
    boosts = {Rank.START: START_BOOST, Rank.MAINTAINERS: LOW_BOOST, None: LOW_BOOST}
    return boosts.get(rank_of(location.partition("#")[0]))


class Plain(HTMLParser):
    """The text of HTML without its tags, and without its blocks of code."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.code = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == CODE:
            self.code += 1
        if tag in BLOCKS:
            self.parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag == CODE and self.code:
            self.code -= 1
        if tag in BLOCKS:
            self.parts.append(" ")

    def handle_data(self, data: str) -> None:
        if not self.code:
            self.parts.append(data)


def plain(html: str) -> str:
    """The text of html on one line, without its tags and its blocks of code."""
    parser = Plain()
    parser.feed(html)
    parser.close()
    return " ".join("".join(parser.parts).split())


def cut(text: str, size: int) -> str:
    """text with size characters at most: cut after a whole word and ended with an
    ellipsis when it is longer."""
    if len(text) <= size:
        return text
    # Room for the ellipsis; a word longer than size is cut within.
    room = size - 1
    return (text[: room + 1].rpartition(" ")[0] or text[:room]).rstrip(",.;:") + "…"


def excerpt(html: str) -> str:
    """The text of a section, html, as the search shows it below the title of a
    match: a paragraph with EXCERPT characters of its plain text at most, cut after a
    whole word and ended with an ellipsis, or nothing for a section without text."""
    text = cut(plain(html), EXCERPT)
    return f"<p>{escape(text, quote=False)}</p>" if text else ""


def websites(catalog: Catalog, site_url: str) -> list[Website]:
    """The projects whose documentation is a website in a folder of site_url, each
    folder once, in the order of the catalog."""
    found: dict[str, Project] = {}
    for project in catalog.projects:
        if project.docs is None:
            continue
        folder = folder_of(project.docs.url[catalog.default], site_url)
        if folder is not None:
            found.setdefault(folder, project)
    return [Website(project, folder) for folder, project in found.items()]


def documents(content: bytes, url: str) -> list[dict[str, Any]]:
    """The entries of content, the search index at url, as the search plugin of
    Material writes it: each with its location, its title and its text."""
    try:
        data = json.loads(content)
    # Also a UnicodeDecodeError, which is a ValueError too.
    except ValueError as error:
        raise web.SearchError(f"{url} is no JSON: {error}") from error
    docs = data.get("docs") if isinstance(data, dict) else None
    if not isinstance(docs, list) or not all(
        isinstance(doc, dict)
        and all(isinstance(doc.get(key), str) for key in ("location", "title"))
        and isinstance(doc.get("text", ""), str)
        for doc in docs
    ):
        raise web.SearchError(
            f"{url} is no search index of Material for MkDocs: it needs docs, a list "
            "of entries with a location, a title and a text."
        )
    return docs


def language_of(catalog: Catalog, location: str) -> str:
    """The language of the page at location of a project website, which MkDocs
    builds in a folder named after each further language, such as de/."""
    for language in catalog.languages[1:]:
        if location.startswith(f"{language}/"):
            return language
    return catalog.default


def entries(
    catalog: Catalog, website: Website, docs: list[dict[str, Any]]
) -> list[Entry]:
    """The entries of docs, the search index of website, as the index of this
    website holds them, each with its rank: each location in the folder of the
    website, each text an excerpt, and the title of each page after the short name
    of its project in the language of the page. Titles and excerpts are plain text,
    escaped, since the search shows them as HTML. The entries of a page get the
    boost of its name, and a decision record keeps the entry of its page alone.

    The search of Material shows a match of a section under the page whose entry
    comes before it, with the same location up to the #. A section whose page the
    index lacks, as the i18n plugin leaves some, gets its page from its title, so
    that the match has a page to stand under.
    """
    project = website.project
    names = project.short or project.name
    found: list[Entry] = []
    pages: set[str] = set()
    for doc in docs:
        location = doc["location"]
        page, section, _ = location.partition("#")
        title = escape(plain(doc["title"]), quote=False)
        boost = {} if (value := boost_of(page)) is None else {"boost": value}
        if page not in pages:
            pages.add(page)
            name = escape(names[language_of(catalog, page)], quote=False)
            entry = {
                "location": f"{website.folder}{page}",
                "title": f"{name}{SEPARATOR}{title}",
                # The text of a page before its first heading, if it has one.
                "text": "" if section else excerpt(doc.get("text", "")),
            }
            found.append(Entry(Rank.PAGE, entry | boost))
        rank = rank_of(page)
        if section and rank is not None:
            entry = {
                "location": f"{website.folder}{location}",
                "title": title,
                "text": excerpt(doc.get("text", "")),
            }
            found.append(Entry(rank, entry | boost))
    return found


class Guide(NamedTuple):
    """A page of a project website that a reader looks for first, such as its
    installation, for llms.txt: its title and its address in every language whose
    page the website has, the default language first."""

    title: dict[str, str]
    url: dict[str, str]


def index_languages(content: bytes) -> list[str]:
    """The languages of content, a search index that documents() has read, as the
    search plugin names them in its config, such as en, de and nl, or none for an
    index without them. MkDocs builds the pages of every language after the first of
    a website in a folder named after it, such as nl/."""
    config = json.loads(content).get("config")
    names = config.get("lang") if isinstance(config, dict) else None
    if not isinstance(names, list):
        return []
    return [name for name in names if isinstance(name, str)]


LANGUAGE_FOLDER = re.compile(r"[a-z]{2}(?:[-_][A-Za-z]{2,4})?")
"""A folder of a website in another language, such as pl or pt-BR."""


def guides(
    catalog: Catalog,
    website: Website,
    docs: list[dict[str, Any]],
    site_url: str,
    languages: list[str],
) -> list[Guide]:
    """The guides of website at site_url, from docs, its search index in languages:
    every page of the default language that START_PAGES names, in their order, each
    with its title as plain text and with the same page in every further language of
    the catalog that the index has, such as de/installation.html for
    installation.html. A decision record is none, and neither is a page in the folder
    of another language, of the catalog or of the website, such as nl/faq.html. A
    page whose entry the index lacks takes its title from its first section, as in
    entries()."""
    titles: dict[str, str] = {}
    for doc in docs:
        titles.setdefault(doc["location"].partition("#")[0], plain(doc["title"]))
    # The search of MkDocs names only the languages that lunr can stem, so a
    # folder that looks like a language code and has a home page is one too.
    found_languages = (
        page.partition("/")[0]
        for page in titles
        if LANGUAGE_FOLDER.fullmatch(page.partition("/")[0])
        and f"{page.partition('/')[0]}/index.html" in titles
    )
    others = tuple(
        f"{language}/"
        for language in dict.fromkeys(
            (*catalog.languages, *languages, *found_languages)
        )
        if language != catalog.default
    )
    found: list[tuple[int, Guide]] = []
    for page in titles:
        if page.startswith(others) or rank_of(page) is not Rank.START:
            continue
        pages = {catalog.default: page} | {
            language: f"{language}/{page}"
            for language in catalog.languages[1:]
            if f"{language}/{page}" in titles
        }
        # Within the folder of the website, whatever its index holds.
        urls = {
            language: f"{site_url}{website.folder}{quote(path, safe='/%')}"
            for language, path in pages.items()
        }
        titled = {language: titles[path] for language, path in pages.items()}
        found.append((START_PAGES.index(page_name(page)), Guide(titled, urls)))
    return [guide for _, guide in sorted(found, key=lambda item: item[0])]


class ProjectSearch(NamedTuple):
    """What the search indexes of the project websites give this website: the
    folders of the websites, their entries for the search index of this website, and
    the guides of each website for llms.txt, by the slug of its project."""

    folders: list[str]
    docs: list[Any]
    guides: dict[str, list[Guide]]


def packed(docs: list[dict[str, Any]]) -> int:
    """The size of docs in bytes in a search index, packed with gzip."""
    data = json.dumps(docs, separators=(",", ":")).encode("utf-8")
    return len(gzip.compress(data, mtime=0))


def within(found: list[list[Entry]], budget: int) -> list[list[dict[str, Any]]]:
    """The entries of every website of found, in their order, that fit into budget
    bytes packed with gzip. The budget gives up the entries of the lowest rank
    first, all of them before any of the next rank: the sections of the pages for
    maintainers, those of the other pages, those of the pages that a reader looks
    for first, and the entries of the pages last. Of the sections of a rank, the
    page with the most gives up its last ones first, so that every page keeps its
    first sections, such as the latest release of a changelog; of the pages, the
    website with the most gives up its last pages first, so that the largest
    website gives up a page before a smaller one gives up any, and a decision
    record before any other page of its website. A section goes with the entry of
    its page, after it."""
    # The place of each entry among the others of its rank: a page among the pages
    # of its website, and a section among the sections of its page. A decision
    # record comes after every other page of its website, so that it gives up its
    # entry before any page for readers does.
    places: list[list[int]] = []
    for docs in found:
        counts: Counter[tuple[Rank, str]] = Counter()
        readers = sum(
            1
            for rank, doc in docs
            if rank is Rank.PAGE and rank_of(doc["location"]) is not None
        )
        row: list[int] = []
        for rank, doc in docs:
            page = doc["location"].partition("#")[0]
            if rank is Rank.PAGE:
                record = rank_of(page) is None
                row.append(counts[rank, str(record)] + (readers if record else 0))
                counts[rank, str(record)] += 1
            else:
                row.append(counts[rank, page])
                counts[rank, page] += 1
        places.append(row)
    # The most places of each rank, the highest rank first: a step of the budget
    # keeps the first places of a rank in every page or website once every rank
    # above it is whole.
    ranks = sorted(Rank, reverse=True)
    most = dict.fromkeys(ranks, 0)
    for docs, row in zip(found, places, strict=True):
        for (rank, _), place in zip(docs, row, strict=True):
            most[rank] = max(most[rank], place + 1)

    def first(step: int) -> list[list[dict[str, Any]]]:
        limit: dict[Rank, int] = {}
        for rank in ranks:
            limit[rank] = min(step, most[rank])
            step -= limit[rank]
        return [
            [
                doc
                for (rank, doc), place in zip(docs, row, strict=True)
                if place < limit[rank]
            ]
            for docs, row in zip(found, places, strict=True)
        ]

    def size(step: int) -> int:
        return packed([doc for docs in first(step) for doc in docs])

    # Within budget with the first low steps, and over it with high.
    low, high = 0, sum(most.values())
    if size(high) <= budget:
        return first(high)
    while high - low > 1:
        middle = (low + high) // 2
        if size(middle) <= budget:
            low = middle
        else:
            high = middle
    return first(low)


def summarize(text: str) -> None:
    """Add text, Markdown, to the summary of the job in GitHub Actions, which the
    page of its run shows, when the job has one; a summary that can't be written
    never fails the build."""
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    try:
        with open(path, "a", encoding="utf-8") as summary:
            summary.write(text)
    except OSError as error:
        log.info("The summary of the job can't be written: %s", error)


def project_search(catalog: Catalog, site_url: str) -> ProjectSearch:
    """The folders of the project websites at site_url, the entries of their search
    indexes for the index of this website, BUDGET bytes at most, and the guides of
    each for llms.txt. A website whose index can't be downloaded or read has neither,
    which the log says without a warning, so that the strict build passes while a
    website is away. The log says how many pages and sections of each website the
    search keeps, so that a drop shows in the log of the build, and so does the
    summary of the job in GitHub Actions, as a table with a row for each website."""
    sites = websites(catalog, site_url)
    if not sites:
        return ProjectSearch([], [], {})

    def search(website: Website) -> tuple[list[Entry], list[Guide], str]:
        url = urljoin(site_url, f"{website.folder}{SEARCH_INDEX}")
        try:
            content = web.download(url)
            docs = documents(content, url)
        except web.SearchError as error:
            log.info(
                "The search leaves out the website of %s until the next build: %s",
                website.project.slug,
                error,
            )
            return [], [], str(error)
        languages = index_languages(content)
        return (
            entries(catalog, website, docs),
            guides(catalog, website, docs, site_url, languages),
            "",
        )

    # Every website at once, so that a slow one doesn't wait for the others.
    with ThreadPoolExecutor(max_workers=len(sites)) as pool:
        results = list(pool.map(search, sites))
    found = [its for its, _, _ in results]
    chosen = within(found, BUDGET)
    rows: list[str] = []
    for website, docs, its, (_, _, problem) in zip(
        sites, found, chosen, results, strict=True
    ):
        name = f"[{website.project.slug}]({urljoin(site_url, website.folder)})"
        if docs:
            pages = sum(1 for rank, _ in docs if rank is Rank.PAGE)
            kept_pages = sum(1 for doc in its if "#" not in doc["location"])
            log.info(
                "The search keeps %d of the %d pages and %d of the %d sections of "
                "the website of %s.",
                kept_pages,
                pages,
                len(its) - kept_pages,
                len(docs) - pages,
                website.project.slug,
            )
            rows.append(
                f"| {name} | {kept_pages} of {pages} | "
                f"{len(its) - kept_pages} of {len(docs) - pages} |"
            )
        else:
            left_out = cell(problem or "its index holds no entry")
            rows.append(f"| {name} | left out: {left_out} | |")
    kept = [doc for its in chosen for doc in its]
    total = sum(map(len, found))
    if len(kept) < total:
        log.info(
            "The search keeps %d of the %d entries of the project websites, %d bytes "
            "packed with gzip at most.",
            len(kept),
            total,
            BUDGET,
        )
    # So that the log of every build shows what the search holds.
    added = (
        f"The search adds {len(kept)} entries of {sum(1 for docs in found if docs)} "
        f"of the {len(sites)} project websites."
    )
    log.info(added)
    summarize(
        "\n".join(
            [
                "### The search of every project website",
                "",
                added,
                "",
                "| Project website | Pages kept | Sections kept |",
                "| --- | --- | --- |",
                *rows,
                "",
            ]
        )
    )
    return ProjectSearch(
        [website.folder for website in sites],
        kept,
        {
            website.project.slug: its
            for website, (_, its, _) in zip(sites, results, strict=True)
        },
    )


def add_to_search(site: Path, folders: list[str], docs: list[Any]) -> None:
    """Put docs, the entries of the project websites in folders, into the search
    index of the website in site, in place of any that an earlier build of another
    language put there. The entries of this website get the boost of their page as
    those of the projects do, such as its decision records, unless they have one."""
    path = site / SEARCH_INDEX
    index = json.loads(path.read_text(encoding="utf-8"))
    own = [
        doc for doc in index["docs"] if not doc["location"].startswith(tuple(folders))
    ]
    for doc in own:
        boost = boost_of(doc["location"])
        if boost is not None:
            doc.setdefault("boost", boost)
    index["docs"] = own + docs
    # As the search plugin of Material writes it.
    text = json.dumps(index, separators=(",", ":"))
    path.write_text(text, encoding="utf-8", newline="\n")
