"""The releases of the projects, from the API of GitHub.

The line <!-- releases --> of the home pages becomes What's new: the latest release of
every project with a repo, the newest first, each with the headline of its notes, which
the script docs/javascripts/projects.js brings up to date.

The Releases page, docs/releases.md and docs/releases.de.md, gets the notes of the
latest releases of every project with a repo in place of its line
<!-- release-notes -->, under a heading of each project, from the same releases: the HTML that GitHub makes of
their Markdown, of which the page keeps only text, headings, lists, tables, code and
links to https, and the notes for users alone, without the list of every pull request
that the release bot writes below them. Without the API, the page links the releases of
each project on GitHub, and the build passes.

The sitemap and the date of the last change of a page take the last commit of its
Markdown, while these pages change with every release of a project: redate() dates them
by the newest release that they show, when it came out later.
"""

from __future__ import annotations

import json
import os
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date, datetime
from html import escape
from html.parser import HTMLParser
from typing import Any

from . import web
from .catalog import GITHUB, Catalog, Project, cell, log
from .render import script_data, short_name
from .search import cut, plain, summarize

# What's new, in place of the line NEWS_MARKER of the home pages, in a part of the
# page with the class NEWS; DASHBOARD in render.py tells the whole of the live facts.
NEWS = "project-news"
NEWS_MARKER = "<!-- releases -->"
NEWS_LINE = re.compile(rf"^{re.escape(NEWS_MARKER)}[ \t]*$", re.MULTILINE)
# The Releases page, docs/releases.md and docs/releases.de.md, RELEASES_PAGE in the
# folder of each language, which What's new links. Its line NOTES_MARKER becomes the
# RELEASES latest releases of every project with a repo, under a heading of each
# project and the newest first, each with its day, its link to GitHub and its notes,
# after a list of links to the heading of every project. The build reads them from
# the API of GitHub, RELEASES_API, as the HTML that GitHub makes of the Markdown of
# their notes, and keeps only the elements of NOTES_KEPT, without an attribute but
# the address of a link to https: no script, no picture and no style of a release
# reaches the page. A draft and a prerelease, such as a beta for testers, stay out,
# so the build asks for PER_PAGE releases to find RELEASES. A token in TOKENS, where
# one is set, lifts the limit of the API from 60 requests an hour to 5,000; the
# hooks send it to the API alone. The notes take the place of their placeholder,
# NOTES_PLACE, in the HTML of the page, so that no Markdown extension, such as the
# snippets that include a file, sees a word of them. A project whose releases can't
# be read keeps its heading and the link to its releases on GitHub until the next
# build, which never fails for it; the Catalog workflow builds the website every
# day. Its place of a newer release has the attribute UNREAD then, from which the
# check of the built website warns of it and the watch of the live websites reports
# it the next day, and the summary of the job says why. As
# the page loads, the script adds the latest release of each project that
# came out after the build, from the data of the dashboard, under its heading.
RELEASES_PAGE = "releases.html"
NOTES_MARKER = "<!-- release-notes -->"
NOTES_LINE = re.compile(rf"^{re.escape(NOTES_MARKER)}[ \t]*$", re.MULTILINE)
RELEASES = 5
PER_PAGE = 20
RELEASES_API = "https://api.github.com/repos/{}/releases?per_page={}"
TOKENS = ("GITHUB_TOKEN", "GH_TOKEN")
NOTES_PLACE = re.compile(r'<div class="release-notes" data-release="([^"<>]*)"></div>')
NEWER = "release-newer"
UNREAD = "data-unread"
# The key of config.extra that keeps the releases for the build of each language.
NOTES = "release_notes"
# The language of the notes of every project, that of its changelog, which the page
# names for screen readers, also when it is in another language. Each language has
# a search index of its own, so the index of every language holds the notes once,
# from its own Releases page.
NOTES_LANGUAGE = "en"
# The elements of the notes that the page keeps, as they are or as the one that
# NOTES_RENAMED names. A heading of the notes stands below that of its release: the
# level of their first heading, which NOTES_LEVEL finds, becomes NOTES_TOP, h4, and
# every other level moves with it, from h4 to h6, so that no level is left out after
# the heading of the release, as release-please writes a heading of the third level
# before one of the second. The elements of NOTES_DROPPED go with
# everything inside them, every other one leaves its text, such as a span, or
# nothing, such as a picture. A line break of the notes, which GitHub makes of every
# line of their Markdown, becomes a space.
NOTES_KEPT = frozenset(
    [
        "a",
        "blockquote",
        "code",
        "dd",
        "del",
        "details",
        "dl",
        "dt",
        "em",
        "hr",
        "kbd",
        "li",
        "ol",
        "p",
        "pre",
        "s",
        "strong",
        "sub",
        "summary",
        "sup",
        "table",
        "tbody",
        "td",
        "tfoot",
        "th",
        "thead",
        "tr",
        "ul",
    ]
)
NOTES_RENAMED = {"b": "strong", "i": "em", "tt": "code", "strike": "del"}
NOTES_HEADING = re.compile(r"h([1-6])")
NOTES_LEVEL = re.compile(r"<h([1-6])[\s/>]", re.IGNORECASE)
NOTES_TOP = 4
NOTES_DROPPED = frozenset(
    [
        "audio",
        "button",
        "canvas",
        "form",
        "iframe",
        "math",
        "noscript",
        "object",
        "picture",
        "script",
        "select",
        "style",
        "svg",
        "template",
        "textarea",
        "video",
    ]
)
NOTES_VOID = frozenset({"hr"})
# A link or a paragraph that the notes leave empty, such as the link of a picture
# that they leave out, goes too: a link without a text tells a screen reader nothing.
NOTES_EMPTY = re.compile(r'<a href="[^"]*">\s*</a>|<p>\s*</p>')
# The first element of the notes, when it is a heading that names the version of its
# release, such as "1.0.6 (2026-10-23)", which the heading of the release names.
NOTES_VERSION = re.compile(r"\s*<h[1-6][^>]*>(.*?)</h[1-6]>", re.DOTALL)
# The heading above every pull request of a release, which the release bot of the
# blueprint writes below the notes for users, as PULL_REQUESTS of its
# blueprint/changelog.py: the same changes again, as the subjects of their commits.
# The Releases page shows the notes for users once and leaves that list to the link
# of each release on GitHub. NOTES_HEADINGS finds every heading of the notes.
PULLS = "Every pull request of this release"
NOTES_HEADINGS = re.compile(r"<h[1-6][^>]*>(.*?)</h[1-6]>", re.DOTALL | re.IGNORECASE)
# What's new tells a release with the headline of its notes: the bold lead of their
# first item, such as "Dark mode" of "**Dark mode:** the settings ...", when it has
# more than one word, or else the first sentence of their first item or paragraph,
# without the references to its pull request and its commit, such as " (#9)
# (3fb0bf5)", and HEADLINE characters at most. A bold lead of one word is the scope
# of a commit, such as "popup:" of "**popup:** hide the form (#4)", which the
# headline leaves out, so that it begins with the first word of the sentence, in
# capitals.
NOTES_FIRST = re.compile(r"<(li|p)>(.*?)</\1>", re.DOTALL)
NOTES_LEAD = re.compile(r"\s*(?:<p>\s*)?<strong>(.*?)</strong>", re.DOTALL)
REFERENCES = re.compile(r"(?:\s*\((?:#\d+|[0-9a-f]{7,40})\))+$")
HEADLINE = 120
# What's new tells a release of maintenance as such, with the text maintenance of
# [facts] in the language of the page in place of its headline: one whose notes list
# its pull requests, each an item that ends with the references to its pull request
# and its commit, as release-please writes them under "Every pull request of this
# release", and of which none changes what a user of the project sees. The scope of
# a commit says so, the bold lead of its item: one of INTERNAL, such as "ci:" of a
# fix of the project's own jobs in GitHub Actions, changes nothing for a user, and
# one of QUIET, such as "deps:" of an update of a dependency, only when no item of
# the notes without such references, which a person wrote in the words of a user,
# says what it changes, as "The Copilot engine works with version 1.0.103" does. A
# release whose notes list no pull request is never one of maintenance: nothing
# tells. NOTES_ITEM is the text of every item before the next item or its end,
# without the items of a list inside it.
NOTES_ITEM = re.compile(r"<li>((?:(?!</?li>).)*)", re.DOTALL)
INTERNAL = frozenset(["build", "chore", "ci", "refactor", "style", "test", "tests"])
QUIET = frozenset(["deps", "deps-dev", "dev-deps", "docs"])
# A tag of a release, and the moment of its publication, as the API names them.
TAG = re.compile(r"[A-Za-z0-9][\w.+-]{0,99}", re.ASCII)
PUBLISHED = re.compile(r"\d{4}-\d{2}-\d{2}T[\d:.]+Z")
# The pages that show the releases of the build, by the HTML that news() and
# release_history() write: the home pages with What's new and the Releases pages. The
# plugin git-revision-date-localized dates every page by the last commit of its
# Markdown, under the name REVISION of the meta of the page, from which the hooks of
# the blueprint take the date of the sitemap, page.update_date; redate() dates these
# pages by the newest release that they show, when it came out later.
SHOWN = re.compile(rf'<div class="(?:{NEWS}|release-newer)"')
DATES = "git-revision-date-localized"
REVISION = "git_revision_date_localized"


@dataclass(frozen=True)
class Release:
    """A release of a project, as the Releases page and What's new show it: its tag,
    its page on GitHub, the moment it was published, in UTC, its notes as the HTML
    that the page keeps of them, their headline, and whether it is a release of
    maintenance alone, which What's new tells as such."""

    tag: str
    url: str
    published: datetime
    notes: str
    headline: str
    maintenance: bool = False

    @property
    def day(self) -> date:
        """The day the release was published, in UTC."""
        return self.published.date()


class Notes(HTMLParser):
    """The HTML of the notes of a release that the page keeps: the elements of
    NOTES_KEPT and the headings below that of the release, each closed and without an
    attribute, and the links to https with their address alone; of every other
    element its text, but of those of NOTES_DROPPED. top is the level of the first
    heading of the notes, which becomes NOTES_TOP."""

    def __init__(self, top: int = 1) -> None:
        super().__init__(convert_charrefs=True)
        self.top = top
        self.parts: list[str] = []
        # The elements that the notes hold open, the innermost last; for every link
        # whether the notes keep it; and the elements of NOTES_DROPPED around the
        # parser.
        self.open: list[str] = []
        self.links: list[bool] = []
        self.dropped: list[str] = []

    def kept(self, tag: str) -> str | None:
        """The element that the notes keep for tag, or None for one that they don't."""
        tag = NOTES_RENAMED.get(tag, tag)
        heading = NOTES_HEADING.fullmatch(tag)
        if heading is not None:
            level = int(heading[1]) - self.top + NOTES_TOP
            return f"h{min(6, max(NOTES_TOP, level))}"
        return tag if tag in NOTES_KEPT else None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in NOTES_DROPPED:
            self.dropped.append(tag)
        if self.dropped:
            return
        if tag == "br":
            self.parts.append("\n")
            return
        name = self.kept(tag)
        if name == "a":
            href = dict(attrs).get("href") or ""
            link = href.startswith("https://") and not any(c.isspace() for c in href)
            self.links.append(link)
            if link:
                self.parts.append(f'<a href="{escape(href)}">')
                self.open.append(name)
        elif name is not None:
            self.parts.append(f"<{name}>")
            if name not in NOTES_VOID:
                self.open.append(name)

    def handle_endtag(self, tag: str) -> None:
        if self.dropped:
            if tag == self.dropped[-1]:
                self.dropped.pop()
            return
        name = self.kept(tag)
        # A link that the notes leave out has left its text alone.
        if name == "a" and not (self.links and self.links.pop()):
            return
        if name in self.open:
            while (last := self.open.pop()) != name:
                self.parts.append(f"</{last}>")
            self.parts.append(f"</{name}>")

    def handle_data(self, data: str) -> None:
        if not self.dropped:
            self.parts.append(escape(data, quote=False))

    def html(self) -> str:
        """The notes, with every element that they hold open closed, and without a
        link or a paragraph that they leave empty."""
        closed = "".join(f"</{name}>" for name in reversed(self.open))
        notes, emptied = "".join(self.parts) + closed, 1
        # A paragraph that held only an empty link is empty once the link has gone.
        while emptied:
            notes, emptied = NOTES_EMPTY.subn("", notes)
        return notes.strip()


def notes_html(html: str, version: str) -> str:
    """The notes of a release with version, html as GitHub makes it of their
    Markdown, as the page keeps them, without a heading in front that names the
    version, such as one of release-please."""
    first = NOTES_VERSION.match(html)
    if first is not None and version and version in plain(first[1]):
        html = html[first.end() :]
    heading = NOTES_LEVEL.search(html)
    parser = Notes(int(heading[1]) if heading is not None else 1)
    parser.feed(html)
    parser.close()
    return parser.html()


def for_users(html: str) -> str:
    """html, the notes of a release as GitHub makes them of their Markdown, without
    the list of every pull request below their notes for users, from the heading
    PULLS on; notes without that heading, such as those of an older release, as they
    are."""
    for heading in NOTES_HEADINGS.finditer(html):
        if plain(heading[1]) == PULLS:
            return html[: heading.start()]
    return html


def headline(notes: str) -> str:
    """The headline of notes, the HTML that the page keeps of the notes of a release,
    which What's new shows: the bold lead of their first item or paragraph without its
    colon, when it has more than one word, or else its first sentence without the
    references to its pull request and its commit, and without a bold lead of one
    word in front of it, the scope of a commit, which begins it in capitals then,
    each cut to HEADLINE characters; or nothing for notes without an item or a
    paragraph."""
    first = NOTES_FIRST.search(notes)
    if first is None:
        return ""
    text = REFERENCES.sub("", plain(first[2]))
    lead = NOTES_LEAD.match(first[2])
    if lead is not None:
        bold = plain(lead[1]).rstrip(":").strip()
        if " " in bold:
            return cut(bold, HEADLINE)
        rest = REFERENCES.sub("", plain(first[2][lead.end() :])).lstrip(": ")
        if rest:
            text = rest[:1].upper() + rest[1:]
    return cut(text.partition(". ")[0].removesuffix("."), HEADLINE)


def scope(item: str) -> str | None:
    """The scope of a commit that item, the HTML of an item of the notes, names in
    its bold lead of one word, such as deps of "<strong>deps:</strong> update", or
    None."""
    lead = NOTES_LEAD.match(item)
    if lead is None:
        return None
    bold = plain(lead[1])
    if not bold.endswith(":") or " " in bold:
        return None
    return bold.removesuffix(":").lower()


def maintenance(notes: str) -> bool:
    """Whether notes, the HTML that the page keeps of the notes of a release, are
    those of a release of maintenance alone: they list pull requests, and the scope
    of each is one of INTERNAL, or one of QUIET while no item in the words of a user
    says what changed."""
    scopes: list[str | None] = []
    told = False
    for item in NOTES_ITEM.findall(notes):
        if REFERENCES.search(plain(item)) is None:
            told = True
        else:
            scopes.append(scope(item))
    return bool(scopes) and all(
        found in INTERNAL or (found in QUIET and not told) for found in scopes
    )


def published(value: object) -> datetime | None:
    """The moment of value, the time at which the API says that a release was
    published, such as 2026-10-15T21:33:15Z, in UTC, or None."""
    if not isinstance(value, str) or PUBLISHED.fullmatch(value) is None:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def releases_in(repo: str, data: list[Any]) -> tuple[Release, ...]:
    """The RELEASES latest releases of repo in data, its releases as the API lists
    them, the newest first: each that is no draft and no prerelease, with a tag and
    the moment it was published, with its page on GitHub and its notes as the page
    keeps them: those for users alone, and all of them when nothing stands above the
    list of every pull request. What's new tells a release by all of its notes, whose
    pull requests name their scopes."""
    found: list[Release] = []
    for entry in data:
        if not isinstance(entry, dict) or entry.get("draft") or entry.get("prerelease"):
            continue
        tag, moment = entry.get("tag_name"), published(entry.get("published_at"))
        if not isinstance(tag, str) or not TAG.fullmatch(tag) or moment is None:
            continue
        body, version = entry.get("body_html"), tag.removeprefix("v")
        html = body if isinstance(body, str) else ""
        notes = notes_html(html, version)
        shown = notes_html(for_users(html), version) or notes
        url = f"{GITHUB}{repo}/releases/tag/{tag}"
        found.append(
            Release(tag, url, moment, shown, headline(notes), maintenance(notes))
        )
        if len(found) == RELEASES:
            break
    return tuple(found)


def releases_request(repo: str) -> urllib.request.Request:
    """The request of the API of GitHub for the releases of repo, with their notes as
    HTML, and with the token of the first of TOKENS that is set, which goes to the API
    alone and to no other host that the API might send the request on to."""
    request = urllib.request.Request(
        RELEASES_API.format(repo, PER_PAGE),
        headers={
            "Accept": "application/vnd.github.html+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    token = next((os.environ[name] for name in TOKENS if os.environ.get(name)), "")
    if token:
        request.add_unredirected_header("Authorization", f"Bearer {token}")
    return request


def release_notes(catalog: Catalog) -> dict[str, tuple[Release, ...]]:
    """The RELEASES latest releases of every project of the catalog with a repo, by
    its repo, from the API of GitHub. A project whose releases can't be read has
    none, which the log says without a warning, so that the strict build passes, and
    so does the summary of the job in GitHub Actions, as a table with a row for each
    repo, where the check of the built website warns of it too."""
    repos = list(dict.fromkeys(str(p.repo) for p in catalog.projects if p.repo))
    if not repos:
        return {}

    def read(repo: str) -> tuple[Release, ...] | str:
        try:
            data = json.loads(web.download(releases_request(repo)))
        except (web.SearchError, ValueError) as error:
            log.info(
                "The Releases page links the releases of %s on GitHub until the next "
                "build: %s",
                repo,
                error,
            )
            return str(error)
        if not isinstance(data, list):
            log.info("The API of GitHub sent no list of the releases of %s", repo)
            return "the API of GitHub sent no list of releases"
        return releases_in(repo, data)

    with ThreadPoolExecutor(max_workers=len(repos)) as pool:
        found = dict(zip(repos, pool.map(read, repos), strict=True))
    notes = {
        repo: releases
        for repo, releases in found.items()
        if isinstance(releases, tuple)
    }
    rows = [
        f"| [{repo}]({GITHUB}{repo}/releases) | "
        + (
            f"{len(releases)} |"
            if isinstance(releases, tuple)
            else f"none: {cell(releases)} |"
        )
        for repo, releases in found.items()
    ]
    # So that the log of every build shows whose releases the pages lack.
    told = (
        f"The Releases page and What's new have the releases of {len(notes)} of the "
        f"{len(repos)} repositories of the catalog."
    )
    log.info(told)
    summarize(
        "\n".join(
            [
                "### The releases of every project",
                "",
                told,
                "",
                "| Repository | Releases on the page |",
                "| --- | --- |",
                *rows,
                "",
            ]
        )
    )
    return notes


def notes_of(config: Any) -> dict[str, tuple[Release, ...]]:
    """The releases of release_notes, read once for the build of every language."""
    if NOTES not in config.extra:
        config.extra[NOTES] = release_notes(config.extra["catalog"])
    found: dict[str, tuple[Release, ...]] = config.extra[NOTES]
    return found


def redate(html: str, page: Any, config: Any) -> None:
    """Date page, whose html MkDocs has made of its Markdown, by the newest release
    that the build read, when it shows the releases, by SHOWN, and that release came
    out after the day of the last commit of its Markdown: the date of the sitemap,
    page.update_date, and the date of its last change that the page shows, as the
    plugin DATES writes it into the meta of the page, where it dated the page.

    Every on_page_markdown has run then, also that of the hooks of the blueprint,
    which dates a page by its Markdown alone, while the build fills these pages with
    the releases of every project."""
    if SHOWN.search(html) is None:
        return
    newest = max(
        (releases[0].published for releases in notes_of(config).values() if releases),
        default=None,
    )
    if newest is None or newest.date().isoformat() <= str(page.update_date):
        return
    page.update_date = newest.date().isoformat()
    plugin = config.plugins.get(DATES)
    if plugin is not None and REVISION in page.meta:
        # As the plugin dates a page, without a commit of its own.
        timestamp = int(newest.timestamp())
        plugin._render_date("", page, plugin._get_locale(page), REVISION, "", timestamp)


def release_anchor(project: Project, release: Release) -> str:
    """The anchor of the heading of release on the Releases page, from the slug of
    its project and its tag, such as homedarts-for-autodarts-v2-0-1."""
    return "-".join([project.slug, *re.findall(r"[a-z0-9]+", release.tag.lower())])


def latest(
    catalog: Catalog, notes: dict[str, tuple[Release, ...]]
) -> list[tuple[Project, Release]]:
    """The latest release of every project of the catalog with a repo whose releases
    notes holds, the newest first, and of a day in the order of the catalog."""
    found = [
        (project, notes[project.repo][0])
        for project in catalog.projects
        if project.repo is not None and notes.get(project.repo)
    ]
    # A stable sort, which keeps the order of the catalog within a day.
    return sorted(found, key=lambda pair: pair[1].day, reverse=True)


def news(catalog: Catalog, language: str, notes: dict[str, tuple[Release, ...]]) -> str:
    """The HTML of What's new in language, in place of its marker: the latest release
    of every project with a repo of notes, the newest first, each with the name of its
    project and its tag, which link its notes on the Releases page, its day, which the
    script tells as the time since, the headline of its notes, or the text maintenance
    of the facts in language for a release of maintenance alone, and the tags of every
    release of the project that the build read, which the script never puts in its
    place, also when one came out the same day. Its count, the
    number of projects with a repo, is how many releases the script shows, with a
    newer one of the data of the dashboard in place of one of the build."""
    count = sum(project.repo is not None for project in catalog.projects)
    items = []
    for project, release in latest(catalog, notes):
        day = release.day.isoformat()
        name = f"{project.name[language]} {release.tag}"
        if release.maintenance:
            lead = (
                f'<span class="{NEWS}__headline">'
                f"{escape(catalog.facts['maintenance'][language])}</span>"
            )
        elif release.headline:
            lead = (
                f'<span class="{NEWS}__headline" lang="{NOTES_LANGUAGE}">'
                f"{escape(release.headline)}</span>"
            )
        else:
            lead = ""
        tags = " ".join(r.tag for r in notes.get(str(project.repo), ()))
        items.append(
            f'<li data-repo="{escape(str(project.repo))}"'
            f' data-release="{escape(release.tag)}" data-released="{day}"'
            f' data-releases="{escape(tags)}">'
            f'<a href="{RELEASES_PAGE}#{release_anchor(project, release)}">'
            f'{escape(name)}</a> <time datetime="{day}" data-ago>{day}</time>'
            f"{lead}</li>"
        )
    inner = f'<ul class="{NEWS}__list">{"".join(items)}</ul>' if items else ""
    return f'<div class="{NEWS}" data-count="{count}">{inner}</div>'


def release_history(
    catalog: Catalog, language: str, notes: dict[str, tuple[Release, ...]]
) -> str:
    """The Markdown of the Releases page in language, in place of its marker: a list
    of links to the heading of every project with a repo, which tells the script
    where the data of the dashboard is, and for each project in the order of the
    catalog its heading, the place of a release of the data that came out after the
    build, marked UNREAD when the build couldn't read the releases, which a
    repository without a release yet is not, its releases of notes with a
    heading, their day, their link to GitHub and the placeholder of their notes,
    and a link to all its releases on GitHub."""
    texts = {key: text[language] for key, text in catalog.facts.items()}
    projects = [project for project in catalog.projects if project.repo is not None]
    links = "".join(
        f'<li><a href="#{project.slug}">{escape(short_name(project, language))}</a></li>'
        for project in projects
    )
    parts = [
        f'<nav class="release-filter" aria-label="{escape(texts["projects"])}"'
        f"{script_data(catalog, language)}><ul>{links}</ul></nav>"
    ]
    for project in projects:
        repo, short = str(project.repo), short_name(project, language)
        releases = notes.get(repo, ())
        newest = releases[0].day.isoformat() if releases else ""
        unread = "" if repo in notes else f" {UNREAD}"
        parts += [
            f"## {project.name[language]} {{ #{project.slug} }}",
            f'<div class="{NEWER}" data-repo="{escape(repo)}"'
            f' data-releases="{escape(" ".join(r.tag for r in releases))}"'
            f' data-released="{newest}"{unread}></div>',
        ]
        for release in releases:
            day, tag = release.day.isoformat(), release.tag.replace("_", r"\_")
            place = escape(f"{repo}@{release.tag}")
            parts += [
                f"### {short} {tag} {{ #{release_anchor(project, release)} }}",
                f'<p class="release-meta"><time datetime="{day}" data-ago>{day}</time>'
                f' · <a href="{escape(release.url)}">{escape(texts["github"])}</a></p>',
                f'<div class="release-notes" data-release="{place}"></div>',
            ]
        everything = texts["releases"].replace("{}", short)
        parts.append(
            f'<p class="release-all"><a href="{GITHUB}{escape(repo)}/releases">'
            f"{escape(everything)}</a></p>"
        )
    return "\n\n".join(parts)
