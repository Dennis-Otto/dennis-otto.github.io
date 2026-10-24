"""The hooks of this website, beside those that every website shares in
.github/mkdocs_blueprint.py; mkdocs.yml names both files.

projects.toml, at the root of the repository, lists every project once: its name,
its texts, its picture and its links in each language of the website. From it, the
hooks put the groups of the projects with a card for each into the home page, in
the language of the page, and give the templates the whole list as
config.extra["catalog"], for the 404 page of overrides/404.html. Run as a script,
with nothing but the standard library, this file writes the table of the projects
in README.md, or checks that the table is current, as scripts/check-project.sh
does; and it lists the pictures of the cards that scripts/project-pictures.sh makes
from the social preview of each repository:

    python3 -I .github/mkdocs_project.py --write
    python3 -I .github/mkdocs_project.py --check
    python3 -I .github/mkdocs_project.py --pictures

The card of a project with a repo also gets the part of its live facts: the level
of its OpenSSF Best Practices, which the hooks read from bestpractices.dev, and its
repository, for which the script docs/javascripts/projects.js writes its latest
release and its quality numbers from the data of the dashboard into the card as the
page loads. The line <!-- releases --> of the home pages becomes What's new: the
latest release of every project with a repo, the newest first, each with the
headline of its notes, which the hooks read from the API of GitHub, and which the
script brings up to date.

The Releases page, docs/releases.md and docs/releases.de.md, gets the notes of the
latest releases of every project with a repo in place of its line
<!-- release-notes -->, under a heading of each project, from the same releases: the
HTML that GitHub makes of their Markdown, of which the page keeps only text,
headings, lists, tables, code and links to https. Without the API, the page links the
releases of each project on GitHub, and the build passes.

The Trust page, docs/trust.md and docs/trust.de.md, gets the table of the guarantees
of every project with a repo in place of its line <!-- trust -->: a column for each
project and a row for each guarantee, from the texts of [trust] in projects.toml.
The script fills the cells of its latest release and of its numbers from the same
data as on the cards, and the build names the level of its OpenSSF Best Practices.
The line <!-- verify --> becomes the commands that verify the latest release of
every project with the GitHub CLI, a tab for each.

Every week the catalog bot, .github/workflows/catalog.yml, compares the catalog with
the repositories of its owner on GitHub, which gh writes into a file, and with the
websites of the projects in every language, and keeps an issue with what differs:

    gh repo list Dennis-Otto --limit 1000 \\
      --json nameWithOwner,homepageUrl,isArchived,isPrivate >repositories.json
    python3 -I .github/mkdocs_project.py --network repositories.json

This website lives at the root of the address dennis-otto.github.io, which the
websites of the projects share, each in a folder of its own. So the hooks also write
the files that crawlers and security researchers look for at the root of a host
alone: robots.txt with the sitemap of every website of the address, and
security.txt (RFC 9116). The home page of the default language gets the structured
data of the address: the name of the website, its owner and the projects; and the
root of the address, not index.html in it, as its canonical address.

The search box of the website finds the documentation of every project too: after
the build, the hooks download the search index of every project website at the
address and add its pages and sections to the index of this website, each title of
a page after the short name of its project, such as "HomeDarts › Cricket", and each
text cut to a short excerpt. A project whose index can't be downloaded stays out of
the search until the next build, which never fails for it. The Catalog workflow
builds the website every day, so that the search follows the projects.

A project whose website moved to another folder of the address, as a renamed
repository moves it, names the folders where it lived in former. GitHub Pages serves
this website for every path that no project serves, so the old addresses reach it:
the hooks write a page at every old address that former/<folder>.txt lists, which
leads to the same page in the new folder, and the 404 page leads every other address
of the old folder there, such as that of a picture. The card of the project keeps
the anchor of each old folder on the home page.

While MkDocs builds the website, the hooks also warn, which fails the strict build of
the check docs, about a title of the menu without its translation, a page without
its translation, and a page of this website in a folder that former names.
"""

from __future__ import annotations

import argparse
import difflib
import gzip
import http.client
import io
import json
import logging
import os
import re
import sys
import tomllib
import urllib.error
import urllib.request
from collections import Counter
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime, timedelta
from enum import IntEnum
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, NamedTuple
from urllib.parse import urljoin, urlsplit

# The warnings of MkDocs, which mkdocs build --strict counts.
log = logging.getLogger("mkdocs.hooks.project")

# The root of the repository, with projects.toml and README.md.
ROOT = Path(__file__).resolve().parents[1]
CATALOG = "projects.toml"
README = "README.md"
# The command that writes the table of the README, for the messages.
WRITE = "python3 -I .github/mkdocs_project.py --write"

# The line of docs/index.md and docs/index.de.md that the groups of cards replace,
# and the anchor of the part of the page that holds them, which the button of the
# hero of overrides/home.html leads to.
MARKER = "<!-- projects -->"
MARKER_LINE = re.compile(rf"^{re.escape(MARKER)}[ \t]*$", re.MULTILINE)
PROJECTS = "projects"
# The size of the picture on top of a card, half that of a social preview on GitHub:
# twice the width of a card in the grid of three, for screens with twice the pixels.
PICTURE = (640, 320)
# The lines of README.md between which the table of the projects goes.
TABLE_START = "<!-- projects:start -->"
TABLE_END = "<!-- projects:end -->"

# The live facts of the home pages. The dashboard of the blueprint publishes its data
# at the same address every few hours: repos.json with the latest release and the
# quality numbers of every repository, history.json with those numbers of every day,
# and releases.atom with the newest releases of all of them. As a home page loads,
# docs/javascripts/projects.js reads the first two from there, on the same origin,
# and writes the release and the numbers into the part of each card with a repo that
# has the class FACTS. What's new, in place of the line NEWS_MARKER, is the latest
# release of every project with a repo, the newest first, which the build writes from
# the releases that it reads for the Releases page, each with the headline of its
# notes; the script puts a newer release of the data in place of one that came out
# after the build. Without the script, or without the data, the cards keep what the
# build put into them. The home pages name no feed in their head: Material asks the
# folder of every alternate link there for its sitemap.xml, which the dashboard
# doesn't publish.
DASHBOARD = "/repo-blueprint/dashboard/"
FEED = f"{DASHBOARD}repos.json"
HISTORY = f"{DASHBOARD}history.json"
ATOM = f"{DASHBOARD}releases.atom"
FACTS = "project-facts"
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
# day. As the page loads, the script adds the latest release of each project that
# came out after the build, from the data of the dashboard, under its heading.
RELEASES_PAGE = "releases.html"
NOTES_MARKER = "<!-- release-notes -->"
NOTES_LINE = re.compile(rf"^{re.escape(NOTES_MARKER)}[ \t]*$", re.MULTILINE)
RELEASES = 5
PER_PAGE = 20
RELEASES_API = "https://api.github.com/repos/{}/releases?per_page={}"
TOKENS = ("GITHUB_TOKEN", "GH_TOKEN")
NOTES_PLACE = re.compile(r'<div class="release-notes" data-release="([^"<>]*)"></div>')
# The key of config.extra that keeps the releases for the build of each language.
NOTES = "release_notes"
# The language of the notes of every project, that of its changelog, which the page
# names for screen readers, also when it is in another language. The search, which
# every language of the website shares, finds the notes on the page in their
# language alone, so that they don't weigh twice on the index that every page loads.
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
    "a blockquote code dd del details dl dt em hr kbd li ol p pre s strong sub "
    "summary sup table tbody td tfoot th thead tr ul".split()
)
NOTES_RENAMED = {"b": "strong", "i": "em", "tt": "code", "strike": "del"}
NOTES_HEADING = re.compile(r"h([1-6])")
NOTES_LEVEL = re.compile(r"<h([1-6])[\s/>]", re.IGNORECASE)
NOTES_TOP = 4
NOTES_DROPPED = frozenset(
    "audio button canvas form iframe math noscript object picture script select "
    "style svg template textarea video".split()
)
NOTES_VOID = frozenset({"hr"})
# A link or a paragraph that the notes leave empty, such as the link of a picture
# that they leave out, goes too: a link without a text tells a screen reader nothing.
NOTES_EMPTY = re.compile(r'<a href="[^"]*">\s*</a>|<p>\s*</p>')
# The first element of the notes, when it is a heading that names the version of its
# release, such as "1.0.6 (2026-10-23)", which the heading of the release names.
NOTES_VERSION = re.compile(r"\s*<h[1-6][^>]*>(.*?)</h[1-6]>", re.DOTALL)
# What's new tells a release with the headline of its notes: the bold lead of their
# first item, such as "Dark mode" of "**Dark mode:** the settings ...", when it has
# more than one word, or else the first sentence of their first item or paragraph,
# without the references to its pull request and its commit, such as " (#9)
# (3fb0bf5)", and HEADLINE characters at most.
NOTES_FIRST = re.compile(r"<(li|p)>(.*?)</\1>", re.DOTALL)
NOTES_LEAD = re.compile(r"\s*(?:<p>\s*)?<strong>(.*?)</strong>", re.DOTALL)
REFERENCES = re.compile(r"(?:\s*\((?:#\d+|[0-9a-f]{7,40})\))+$")
HEADLINE = 120
# A tag of a release, and the day of its publication, as the API names them.
TAG = re.compile(r"[A-Za-z0-9][\w.+-]{0,99}", re.ASCII)
PUBLISHED = re.compile(r"(\d{4}-\d{2}-\d{2})T[\d:.]+Z")
# The Trust page. Its table of the guarantees of every project with a repo takes the
# place of the line TRUST_MARKER, in a part of the page with the class TRUST that
# tells the script where the data of the dashboard is, as that of the cards does. The
# script writes the value of every row of TRUST_LIVE into the cell of each project,
# by its repository and the key of its row; without the data, the cell of its
# release links its releases on GitHub, and the others hold DASH. Each row of
# TRUST_VALUED has one value that every project shares. The commands that verify the
# latest release of every project take the place of VERIFY_MARKER: they check the
# attestation of its release, and the provenance of one of its files, which the
# workflow SIGNER of its repository signed.
TRUST_MARKER = "<!-- trust -->"
TRUST_LINE = re.compile(rf"^{re.escape(TRUST_MARKER)}[ \t]*$", re.MULTILINE)
VERIFY_MARKER = "<!-- verify -->"
VERIFY_LINE = re.compile(rf"^{re.escape(VERIFY_MARKER)}[ \t]*$", re.MULTILINE)
TRUST = "trust"
TRUST_ROWS = (
    "release",
    "tag",
    "provenance",
    "immutable",
    "sbom",
    "vex",
    "coverage",
    "mutation",
    "scorecard",
    "bestpractices",
    "policy",
    "report",
)
TRUST_VALUED = ("tag", "provenance", "immutable", "sbom", "vex", "policy", "report")
TRUST_LIVE = ("release", "coverage", "mutation", "scorecard")
DASH = "—"
GITHUB = "https://github.com/"
SIGNER = ".github/workflows/build-release.yml"
# The OpenSSF Best Practices of a project: its page at bestpractices.dev, and its data
# there with the level that it holds. The build reads the level and names it on the
# card, in the language of the page, linked to the page; the reader's browser asks
# bestpractices.dev for nothing, and the Catalog workflow builds the website every
# day. The website shows no badge, which would stay as the build downloaded it: the
# hooks of the blueprint take every badge out of a page. A level that can't be read
# stays off the card until the next build, which never fails for it.
BEST_PRACTICES = "https://www.bestpractices.dev/projects/{}"
BEST_PRACTICES_DATA = "https://www.bestpractices.dev/projects/{}.json"
LEVELS = ("passing", "silver", "gold")
# The key of config.extra that keeps the levels for the build of each language.
LEVEL = "best_practices"

# The pages of docs/ that have no translation yet, by their path there without the
# suffix of the default language, such as "guide.md". A page leaves this list with
# its translation; today every page has one.
UNTRANSLATED: frozenset[str] = frozenset()
# The decision records stay in English, as in every repository of the blueprint.
ENGLISH_ONLY = "decisions/"

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
# The home page of the default language, at the root of the address, which alone
# gets the structured data; and the title of its preview card, as the social plugin
# of Material writes it into the head of the page.
HOME = "index.html"
SOCIAL_TITLE = re.compile(r'(<meta property="(?:og|twitter):title" content=")[^"]*(">)')
# How long security.txt holds from the day of the build: its Expires is the midnight
# a year later, less than a year ahead, as RFC 9116 recommends. Every change of main
# publishes the website again, and with it a later date.
VALID = timedelta(days=365)

# The catalog bot, .github/workflows/catalog.yml. The address in whose folders the
# websites of the projects live, the fields of gh repo list that it reads, how many
# seconds it waits for a website, and the answers of a website that is gone.
SITE = "https://dennis-otto.github.io/"
FIELDS = ("nameWithOwner", "homepageUrl", "isArchived", "isPrivate")
TIMEOUT = 30
GONE = frozenset({404, 410})
# The exit code of --network when the catalog differs: not 1, which Python gives
# when it stops with an exception, so that a crash can't pass for a difference.
DIFFERS = 3
# The languages of the catalog by their names, for the messages of the bot.
LANGUAGE_NAMES = {"en": "English", "de": "German"}

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
SEARCH_TIMEOUT = 10
TRIES = 2
EXCERPT = 200
BUDGET = 120_000
SEPARATOR = " › "
# What an entry of a project website is worth to the search follows from the name of
# its page, the last part of its location without .html, in every language. The
# pages that a reader looks for first are START_PAGES, and those for maintainers
# MAINTAINER_PAGES; a page in a folder named DECISIONS, at any depth, is a decision
# record, and the search keeps its page but none of its sections. The budget gives
# up the sections of the pages for maintainers first and the entries of the pages
# last. The search of Material ranks the matches of an entry with a boost higher or
# lower: those of START_PAGES with START_BOOST, those of the pages for maintainers
# and of every decision record with LOW_BOOST, this website's own records too.
START_PAGES = frozenset(
    "faq getting-started guide install installation troubleshooting".split()
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
FORMER = "former"
MOVED = {
    "en": ("This page has moved", "This page has moved to the website of {}:"),
    "de": (
        "Diese Seite ist umgezogen",
        "Diese Seite ist auf die Website von {} umgezogen:",
    ),
}


@dataclass(frozen=True)
class Form:
    """What a text of projects.toml must look like, and how a message says it."""

    pattern: re.Pattern[str]
    description: str


LANGUAGE = re.compile(r"[a-z]{2,3}(?:[_-][A-Za-z0-9]+)*")
SLUG = Form(
    re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*"),
    "lowercase letters, digits and hyphens, such as homedarts-for-autodarts",
)
REPO = Form(
    re.compile(r"[A-Za-z0-9-]+/[A-Za-z0-9._-]+"),
    "a repository on GitHub, such as Dennis-Otto/homedarts-for-autodarts",
)
LICENSE = Form(
    re.compile(r"[A-Za-z0-9]+(?:[.-][A-Za-z0-9]+)*"),
    "the SPDX identifier of a license, such as MIT or AGPL-3.0-or-later",
)
ICON = Form(
    re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)+"),
    "an icon of Material for MkDocs, such as material-download",
)
# An address that a link of Markdown can hold as it is.
URL = Form(
    re.compile(r"https://[^\s()<>]+"),
    "an address with https:// and without spaces or parentheses",
)
# A picture in docs/, by its path there, which a link of Markdown can hold as it is.
IMAGE = Form(
    re.compile(r"(?:[a-z0-9_-]+/)*[a-z0-9_-]+\.(?:avif|jpg|png|svg|webp)"),
    "a picture in docs/, such as images/projects/homedarts-for-autodarts.webp",
)
# A file of a release, which the commands of the Trust page name as they are, so
# without a space or a character that a shell reads.
ASSET = Form(
    re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*"),
    "the name of a file of its releases, such as homedarts.zip",
)
# A page of a former website, by its path from the folder of that website: a folder
# or a name never starts with a dot, so the path stays in the folder.
PAGE = Form(
    re.compile(r"(?:[A-Za-z0-9_-][A-Za-z0-9._-]*/)*[A-Za-z0-9_-][A-Za-z0-9._-]*\.html"),
    "the path of a page from the folder of the website, such as games.html or "
    "de/index.html",
)
# The keys of a [[group]] and of a [[project]], which the comments of projects.toml
# describe.
GROUP_KEYS = ("id", "heading", "note")
PROJECT_KEYS = (
    "slug",
    "repo",
    "license",
    "platform",
    "bestpractices",
    "asset",
    "group",
    "icon",
    "name",
    "short",
    "tagline",
    "summary",
    "image",
    "alt",
    "start",
    "docs",
    "former",
    "second",
)
# The keys that only a project with a card, and so with a group, has.
CARD_KEYS = ("image", "alt", "second")
# The keys of [facts], the texts of the live facts in every language, which the
# comments of projects.toml describe. Those of VALUED hold {} where the value goes;
# the page gives those of SCRIPT to the script, and the build takes the others, and
# github too, for the Releases page.
FACT_KEYS = (
    "label",
    "released",
    "coverage",
    "mutation",
    "scorecard",
    "answer",
    "bestpractices",
    *LEVELS,
    "projects",
    "github",
    "releases",
)
VALUED = (
    "released",
    "coverage",
    "mutation",
    "scorecard",
    "answer",
    "bestpractices",
    "releases",
)
SCRIPT = ("label", "released", "coverage", "mutation", "scorecard", "answer", "github")
# The keys of [trust], the texts of the table of the Trust page in every language:
# those of the table, and the label of every row of TRUST_ROWS, which those of
# TRUST_VALUED hold as label, with their value beside it.
TRUST_KEYS = ("caption", "guarantee", "note", *TRUST_ROWS)
ROW_KEYS = ("label", "value")


@dataclass(frozen=True)
class Link:
    """A button of a card: its icon, and its label and address in every language."""

    icon: str
    label: dict[str, str]
    url: dict[str, str]


@dataclass(frozen=True)
class Picture:
    """The picture on top of a card: its file in docs/, and what it shows in every
    language, for those who can't see it."""

    src: str
    alt: dict[str, str]


@dataclass(frozen=True)
class Group:
    """A group of cards on the home page, under a heading of its own, with a note
    below the cards if it has one."""

    id: str
    heading: dict[str, str]
    note: dict[str, str] | None


@dataclass(frozen=True)
class Project:
    """A card of the home page, and a row of the table of the README.

    A project with a group has a card with a picture; one without, such as the
    dashboard, is the second button of the card that names it as its second.
    """

    slug: str
    repo: str | None
    license: str | None
    platform: str | None
    icon: str
    name: dict[str, str]
    tagline: dict[str, str]
    summary: dict[str, str]
    start: Link
    docs: Link | None
    group: str | None = None
    picture: Picture | None = None
    second: str | None = None
    # Its name in a few words, where it stands before the title of each page of its
    # website in the search, if its name is long.
    short: dict[str, str] | None = None
    # The number of its project at bestpractices.dev, whose level of the OpenSSF
    # Best Practices its card names.
    bestpractices: int | None = None
    # The file of its releases that its users install, which the Trust page verifies.
    asset: str | None = None
    # The folders of the address where its website lived before.
    former: tuple[str, ...] = ()

    @property
    def website(self) -> dict[str, str]:
        """Its address on the web in every language: that of its documentation, or
        where its first button leads when it has none."""
        return (self.docs or self.start).url

    @property
    def verified(self) -> str:
        """The file of its latest release that the Trust page verifies: its asset, or
        else the SBOM that every release carries, named after its repository, such
        as repo-blueprint.spdx.json."""
        return self.asset or f"{str(self.repo).partition('/')[2]}.spdx.json"


@dataclass(frozen=True)
class Trust:
    """The texts of the table of the Trust page, each in every language: those of
    texts by their key of TRUST_KEYS, with the label of every row, and the value
    that every project shares in each row of TRUST_VALUED, by its key in values."""

    texts: dict[str, dict[str, str]]
    values: dict[str, dict[str, str]]


@dataclass(frozen=True)
class Catalog:
    """The groups and the projects of projects.toml, with the languages of their
    texts."""

    languages: tuple[str, ...]
    groups: tuple[Group, ...]
    projects: tuple[Project, ...]
    # The texts of the live facts, by their key of FACT_KEYS and their language.
    facts: dict[str, dict[str, str]]
    # The texts of the table of the Trust page.
    trust: Trust
    # The pages of every former website, by its folder, from FORMER/<folder>.txt,
    # which load reads.
    former_pages: dict[str, tuple[str, ...]] = field(default_factory=dict)

    @property
    def default(self) -> str:
        """The language of the README, the first of the catalog."""
        return self.languages[0]

    def members(self, group: Group) -> list[Project]:
        """The projects whose cards stand in group, in the order of the catalog."""
        return [project for project in self.projects if project.group == group.id]

    def second(self, project: Project) -> Link | None:
        """The second button of the card of project: the first button of the project
        that it names as its second, or else the button to its documentation."""
        if project.second is not None:
            return {other.slug: other for other in self.projects}[
                project.second
            ].start
        return project.docs

    def directory(self) -> list[dict[str, Any]]:
        """Every project for the script of the 404 page, which gets it as JSON: its
        slug, the folders where its website lived before, and its name and its
        website in every language."""
        return [
            {
                "slug": project.slug,
                "former": list(project.former),
                "name": project.name,
                "url": project.website,
            }
            for project in self.projects
        ]

    def moves(self) -> dict[str, str]:
        """Every folder where the website of a project lived before, by the address
        of the folder where it lives now, for the script of the 404 page."""
        return {
            folder: urljoin(project.docs.url[self.default], ".")
            for project in self.projects
            if project.docs is not None
            for folder in project.former
        }


class CatalogError(Exception):
    """projects.toml, or the table of the README, isn't as the website needs it."""


def join(key: str, name: str) -> str:
    """The dotted key of name in the table key, as projects.toml writes it."""
    return f"{key}.{name}" if key else name


class Reader:
    """Reads the tables of projects.toml and collects every problem on the way, so
    that a single run names them all."""

    def __init__(self, languages: tuple[str, ...]) -> None:
        self.languages = languages
        self.problems: list[str] = []

    def problem(self, owner: str, key: str, message: str) -> None:
        """Note a problem with key, of the project owner if there is one."""
        where = ": ".join(part for part in (owner, key) if part)
        self.problems.append(f"{where} {message}.")

    def table(
        self, value: object, owner: str, key: str, known: tuple[str, ...]
    ) -> dict[str, Any] | None:
        """value as a table whose keys are among known, or None."""
        if value is None:
            self.problem(owner, key, "is missing")
            return None
        if not isinstance(value, dict):
            self.problem(owner, key, "must be a table")
            return None
        for name in value:
            if name not in known:
                self.problem(
                    owner, join(key, name), f"is unknown; known are {', '.join(known)}"
                )
        return value

    def text(
        self, value: object, owner: str, key: str, form: Form | None = None
    ) -> str:
        """value as a text on one line, of the form if there is one."""
        if value is None:
            self.problem(owner, key, "is missing")
        elif not isinstance(value, str) or not value.strip() or "\n" in value:
            self.problem(owner, key, "must be a text on one line")
        elif form is not None and not form.pattern.fullmatch(value):
            self.problem(owner, key, f"must be {form.description}, not {value!r}")
        else:
            return value
        return ""

    def known_languages(self, value: dict[str, Any], owner: str, key: str) -> None:
        """Note every language of value that the catalog doesn't list."""
        for language in value:
            if language not in self.languages:
                self.problem(
                    owner,
                    join(key, language),
                    "is in a language that languages doesn't list "
                    f"({', '.join(self.languages)})",
                )

    def texts(self, value: object, owner: str, key: str) -> dict[str, str]:
        """value as a text in every language, such as name.en and name.de."""
        if not isinstance(value, dict):
            wanted = ", ".join(join(key, language) for language in self.languages)
            self.problem(owner, key, f"needs a text in every language: {wanted}")
            return {}
        self.known_languages(value, owner, key)
        return {
            language: self.text(value.get(language), owner, join(key, language))
            for language in self.languages
        }

    def urls(self, value: object, owner: str, key: str) -> dict[str, str]:
        """value as an address in every language: one for all of them, or one per
        language, where a language without its own takes that of the first."""
        if not isinstance(value, dict):
            return dict.fromkeys(self.languages, self.text(value, owner, key, URL))
        self.known_languages(value, owner, key)
        first = self.languages[0]
        if first not in value:
            self.problem(
                owner,
                join(key, first),
                "is missing; the other languages take it when they have no address",
            )
        own = {
            language: self.text(value[language], owner, join(key, language), URL)
            for language in self.languages
            if language in value
        }
        return {
            language: own.get(language, own.get(first, ""))
            for language in self.languages
        }

    def link(self, value: object, owner: str, key: str, *, url: bool = True) -> Link:
        """value as a button: its icon, its label and, if url, its address."""
        known = ("icon", "label", "url") if url else ("icon", "label")
        table = self.table(value, owner, key, known)
        if table is None:
            return Link("", {}, {})
        return Link(
            icon=self.text(table.get("icon"), owner, join(key, "icon"), ICON),
            label=self.texts(table.get("label"), owner, join(key, "label")),
            url=self.urls(table.get("url"), owner, join(key, "url")) if url else {},
        )

    def number(self, value: object, owner: str, key: str) -> int | None:
        """value as the number of a project at bestpractices.dev."""
        if isinstance(value, int) and not isinstance(value, bool) and value > 0:
            return value
        self.problem(
            owner,
            key,
            "must be the number of the project at bestpractices.dev, as in the "
            f"address of its badge, such as 14935, not {value!r}",
        )
        return None

    def former(self, value: object, owner: str, docs: Link | None) -> tuple[str, ...]:
        """value as the folders of the address where the website of a project lived
        before, each once, for a project whose docs, the website, is in a folder of
        SITE now."""
        if not isinstance(value, list) or not value:
            self.problem(
                owner,
                "former",
                "must list the folders of the address where its website lived "
                'before, such as ["ha-autodarts"]',
            )
            return ()
        folders = [self.text(item, owner, "former", SLUG) for item in value]
        twice = {folder for folder in folders if folder and folders.count(folder) > 1}
        for folder in sorted(twice):
            self.problem(owner, "former", f"names {folder!r} more than once")
        if docs is None or folder_of(docs.url[self.languages[0]]) is None:
            self.problem(
                owner,
                "former",
                f"is for a project whose docs are a website in a folder of {SITE}, "
                "where the old addresses lead",
            )
        return tuple(folder for folder in dict.fromkeys(folders) if folder)

    def facts(self, value: object) -> dict[str, dict[str, str]]:
        """value as the texts of the live facts, each in every language, those of
        VALUED with {} once, where the script writes the value."""
        table = self.table(value, "", "facts", FACT_KEYS)
        if table is None:
            return {}
        texts = {
            key: self.texts(table.get(key), "", join("facts", key)) for key in FACT_KEYS
        }
        for key in VALUED:
            for language, text in texts[key].items():
                if text and text.count("{}") != 1:
                    self.problem(
                        "",
                        join(join("facts", key), language),
                        "must hold {} once, where the script writes the value, not "
                        f"{text!r}",
                    )
        return texts

    def trust(self, value: object) -> Trust:
        """value as the texts of the table of the Trust page, each in every language:
        a text for every key of TRUST_KEYS, and a table with a label and a value for
        each of TRUST_VALUED."""
        table = self.table(value, "", TRUST, TRUST_KEYS)
        if table is None:
            return Trust({}, {})
        texts: dict[str, dict[str, str]] = {}
        values: dict[str, dict[str, str]] = {}
        for key in TRUST_KEYS:
            name = join(TRUST, key)
            if key not in TRUST_VALUED:
                texts[key] = self.texts(table.get(key), "", name)
                continue
            row = self.table(table.get(key), "", name, ROW_KEYS)
            if row is not None:
                texts[key] = self.texts(row.get("label"), "", join(name, "label"))
                values[key] = self.texts(row.get("value"), "", join(name, "value"))
        return Trust(texts, values)

    def project(
        self, value: object, number: int, documentation: Link
    ) -> Project | None:
        """value as a project, the entry number of the catalog, whose button to its
        documentation has the icon and the label of documentation."""
        slug = value.get("slug") if isinstance(value, dict) else None
        named = isinstance(slug, str) and SLUG.pattern.fullmatch(slug) is not None
        owner = str(slug) if named else f"project {number}"
        table = self.table(value, owner, "", PROJECT_KEYS)
        if table is None:
            return None
        # In the order of the keys, which is that of the messages.
        slug = self.text(slug, owner, "slug", SLUG)
        repo = spdx = platform = bestpractices = asset = None
        if "repo" in table:
            repo = self.text(table["repo"], owner, "repo", REPO)
            # What the structured data of the home page says about the code.
            spdx = self.text(table.get("license"), owner, "license", LICENSE)
            platform = self.text(table.get("platform"), owner, "platform")
            if "bestpractices" in table:
                bestpractices = self.number(
                    table["bestpractices"], owner, "bestpractices"
                )
            if "asset" in table:
                asset = self.text(table["asset"], owner, "asset", ASSET)
        else:
            for key in ("license", "platform", "bestpractices", "asset"):
                if key in table:
                    self.problem(owner, key, "is for a project with a repo")
        group = None
        if "group" in table:
            group = self.text(table["group"], owner, "group", SLUG)
        else:
            for key in CARD_KEYS:
                if key in table:
                    self.problem(owner, key, "is for a project with a group")
        icon = self.text(table.get("icon"), owner, "icon", ICON)
        name = self.texts(table.get("name"), owner, "name")
        short = None
        if "short" in table:
            short = self.texts(table["short"], owner, "short")
        tagline = self.texts(table.get("tagline"), owner, "tagline")
        summary = self.texts(table.get("summary"), owner, "summary")
        image = second = None
        if group is not None:
            src = self.text(table.get("image"), owner, "image", IMAGE)
            # scripts/project-pictures.sh makes the picture of a project with a repo,
            # always as a WebP; a picture of another kind is one made by hand.
            if "repo" in table and src and not src.endswith(".webp"):
                self.problem(
                    owner,
                    "image",
                    "must be a WebP for a project with a repo, which "
                    f"scripts/project-pictures.sh makes, not {src!r}",
                )
            image = Picture(src=src, alt=self.texts(table.get("alt"), owner, "alt"))
            if "second" in table:
                second = self.text(table["second"], owner, "second", SLUG)
        start = self.link(table.get("start"), owner, "start")
        docs = None
        if "docs" in table:
            url = self.urls(table["docs"], owner, "docs")
            docs = Link(documentation.icon, documentation.label, url)
        former: tuple[str, ...] = ()
        if "former" in table:
            former = self.former(table["former"], owner, docs)
        return Project(
            slug,
            repo,
            spdx,
            platform,
            icon,
            name,
            tagline,
            summary,
            start,
            docs,
            group=group,
            picture=image,
            second=second,
            short=short,
            bestpractices=bestpractices,
            asset=asset,
            former=former,
        )

    def group(self, value: object, number: int) -> Group | None:
        """value as a group of cards, the entry number of the groups."""
        id_ = value.get("id") if isinstance(value, dict) else None
        named = isinstance(id_, str) and SLUG.pattern.fullmatch(id_) is not None
        owner = f"group {id_}" if named else f"group {number}"
        table = self.table(value, owner, "", GROUP_KEYS)
        if table is None:
            return None
        id_ = self.text(id_, owner, "id", SLUG)
        heading = self.texts(table.get("heading"), owner, "heading")
        note = None
        if "note" in table:
            note = self.texts(table["note"], owner, "note")
        return Group(id_, heading, note)

    def entries(self, value: object, key: str) -> list[object]:
        """value as the list of the [[key]] tables of the catalog."""
        if isinstance(value, list) and value:
            return value
        self.problem("", key, f"must list the {key}s as [[{key}]] tables")
        return []

    def cards(self, groups: tuple[Group, ...], projects: tuple[Project, ...]) -> None:
        """Note every id that names more than one group, every group of a project
        that names no group of the catalog, every second that names no other
        project, every project that no card shows, and every group without a card."""
        ids = [group.id for group in groups if group.id]
        for id_ in sorted({id_ for id_ in ids if ids.count(id_) > 1}):
            self.problem(f"group {id_}", "id", "names more than one group")
        slugs = {project.slug for project in projects}
        shown = set()
        for project in projects:
            if project.group and project.group not in ids:
                known = ", ".join(dict.fromkeys(ids)) or "none"
                self.problem(
                    project.slug,
                    "group",
                    f"must be the id of a group of the catalog ({known}), "
                    f"not {project.group!r}",
                )
            if project.second and project.second not in slugs - {project.slug}:
                self.problem(
                    project.slug,
                    "second",
                    f"names no other project of the catalog, not {project.second!r}",
                )
            # A group with a problem of its own counts, to name that problem alone.
            if project.group is not None:
                shown |= {project.slug, project.second}
        for project in projects:
            if project.slug and project.slug not in shown:
                self.problem(
                    project.slug,
                    "",
                    "is on no card of the home page: give it a group, or name it as "
                    "the second of a project with one",
                )
        grouped = {project.group for project in projects}
        for id_ in dict.fromkeys(ids):
            if id_ not in grouped:
                self.problem(f"group {id_}", "", "has no project")

    def moves(self, groups: tuple[Group, ...], projects: tuple[Project, ...]) -> None:
        """Note every folder of former that the address or the home page uses
        already, where an old address would hide what is there or take its anchor:
        a further language of this website, the folder of a website of the catalog,
        the slug of a project or the id of a group; and every one that more than one
        project names."""
        used = {
            *self.languages[1:],
            *(group.id for group in groups),
            *(project.slug for project in projects),
        }
        for project in projects:
            folder = folder_of(project.website[self.languages[0]])
            if folder is not None:
                used.add(folder.partition("/")[0])
        named = [folder for project in projects for folder in project.former]
        for project in projects:
            for folder in project.former:
                if folder in used:
                    self.problem(
                        project.slug,
                        "former",
                        f"names {folder!r}, which the address or the home page uses "
                        "already: as a language, the folder of a website, a slug or "
                        "the id of a group",
                    )
                elif named.count(folder) > 1:
                    self.problem(
                        project.slug,
                        "former",
                        f"names {folder!r}, which another project names too",
                    )


def read(data: dict[str, Any]) -> Catalog:
    """The catalog that data, the tables of projects.toml, describes."""
    languages = data.get("languages")
    if (
        not isinstance(languages, list)
        or not languages
        or not all(
            isinstance(code, str) and LANGUAGE.fullmatch(code) for code in languages
        )
        or len(set(languages)) < len(languages)
    ):
        raise CatalogError(
            f"{CATALOG}: languages must list the language codes of the website, "
            'each once and that of the README first, such as ["en", "de"].'
        )
    reader = Reader(tuple(languages))
    reader.table(
        data,
        "",
        "",
        ("languages", "documentation", "facts", TRUST, "group", "project"),
    )
    documentation = reader.link(
        data.get("documentation"), "", "documentation", url=False
    )
    facts = reader.facts(data.get("facts"))
    trust = reader.trust(data.get(TRUST))
    groups = tuple(
        group
        for number, entry in enumerate(reader.entries(data.get("group"), "group"), 1)
        if (group := reader.group(entry, number)) is not None
    )
    entries = reader.entries(data.get("project"), "project")
    projects = tuple(
        project
        for number, entry in enumerate(entries, start=1)
        if (project := reader.project(entry, number, documentation)) is not None
    )
    slugs = [project.slug for project in projects if project.slug]
    for slug in sorted({slug for slug in slugs if slugs.count(slug) > 1}):
        reader.problem(slug, "slug", "names more than one project")
    reader.cards(groups, projects)
    reader.moves(groups, projects)
    if reader.problems:
        raise CatalogError(
            f"{CATALOG} has {len(reader.problems)} problem(s):\n"
            + "\n".join(f"  {problem}" for problem in reader.problems)
            + f"\nThe comments at the top of {CATALOG} describe every key."
        )
    return Catalog(tuple(languages), groups, projects, facts, trust)


def folder_of(url: str, site_url: str = SITE) -> str | None:
    """The folder of site_url that the website at url lives in, such as
    homedarts-for-autodarts/, or None for a website elsewhere or at its root."""
    folder = urljoin(url, ".")
    if folder.startswith(site_url) and folder != site_url:
        return folder.removeprefix(site_url)
    return None


def former_pages(catalog: Catalog, root: Path) -> dict[str, tuple[str, ...]]:
    """The pages of the former website in every folder of former, from
    FORMER/<folder>.txt in the folder root, each once."""
    found: dict[str, tuple[str, ...]] = {}
    problems: list[str] = []
    for project in catalog.projects:
        for folder in project.former:
            name = f"{FORMER}/{folder}.txt"
            try:
                text = (root / name).read_text(encoding="utf-8")
            except OSError as error:
                problems.append(
                    f"{name}, the pages of the former website of {project.slug}, "
                    f"can't be read: {error}"
                )
                continue
            pages = []
            for number, line in enumerate(text.splitlines(), start=1):
                page = line.strip()
                if not page or page.startswith("#"):
                    continue
                if PAGE.pattern.fullmatch(page):
                    pages.append(page)
                else:
                    problems.append(
                        f"{name}:{number} must be {PAGE.description}, not {page!r}"
                    )
            if not pages:
                problems.append(f"{name} lists no page of the former website")
            found[folder] = tuple(dict.fromkeys(pages))
    if problems:
        raise CatalogError(
            f"The pages of the former websites have {len(problems)} problem(s):\n"
            + "\n".join(f"  {problem}." for problem in problems)
            + f"\nThe comments at the top of {CATALOG} describe {FORMER}."
        )
    return found


def load(root: Path = ROOT) -> Catalog:
    """The catalog of projects.toml in the folder root, with the pages of the former
    websites that it names."""
    try:
        text = (root / CATALOG).read_text(encoding="utf-8")
    except OSError as error:
        raise CatalogError(f"{CATALOG} can't be read: {error}") from error
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        raise CatalogError(f"{CATALOG} isn't valid TOML: {error}") from error
    catalog = read(data)
    return replace(catalog, former_pages=former_pages(catalog, root))


def bracketed(text: str) -> str:
    """text between the brackets of a link or a picture of Markdown, where a bracket
    or a backslash of its own would end or change it."""
    return re.sub(r"([\\\[\]])", r"\\\1", text)


def button(link: Link, language: str, *, primary: bool = False) -> str:
    """The Markdown of a button: a link with the classes of Material."""
    classes = ".md-button .md-button--primary" if primary else ".md-button"
    label, url = bracketed(link.label[language]), link.url[language]
    return f"[:{link.icon}: {label}]({url}){{ {classes} }}"


def picture(image: Picture, language: str) -> str:
    """The Markdown of the picture on top of a card: with its size, so that the page
    keeps its place before it loads, loaded only as it comes into view, and without
    the enlarging of the lightbox, since the picture is a preview."""
    width, height = PICTURE
    return (
        f"![{bracketed(image.alt[language])}]({image.src})"
        f'{{ width="{width}" height="{height}" loading="lazy" .off-glb }}'
    )


def facts(
    catalog: Catalog, project: Project, language: str, levels: dict[int, str]
) -> str:
    """The HTML of the live facts of the card of a project with a repo: its
    repository and its name, for the script, which adds its release and its quality
    numbers, and the level of its OpenSSF Best Practices of levels, by the number of
    its project, which links its page at bestpractices.dev."""
    texts = {key: text[language] for key, text in catalog.facts.items()}
    level = levels.get(project.bestpractices or 0)
    items = ""
    if level is not None:
        named = texts["bestpractices"].replace("{}", texts[level])
        items = (
            f'<ul class="{FACTS}__list" aria-label="{escape(texts["label"])}">'
            f'<li><a href="{BEST_PRACTICES.format(project.bestpractices)}">'
            f"{escape(named)}</a></li></ul>"
        )
    return (
        f'<div class="{FACTS}" data-repo="{escape(str(project.repo))}"'
        f' data-name="{escape(project.name[language])}">{items}</div>'
    )


def card(project: Project, language: str, second: Link | None, live: str = "") -> str:
    """The Markdown of the card of project: its picture, its heading with the slug as
    its anchor, with an anchor of its own for every folder of former, so that an
    address of the home page that led to the card under an old slug still does, and
    with a link to its website, its summary, live, the HTML of its live facts if it
    has them, its first button and second, the button that Catalog.second gives
    it."""
    buttons = [button(project.start, language, primary=True)]
    if second is not None:
        buttons.append(button(second, language))
    name = f"[{bracketed(project.name[language])}]({project.website[language]})"
    anchors = "".join(f'<span id="{folder}"></span>' for folder in project.former)
    heading = (
        f"### {anchors}:{project.icon}:{{ .lg .middle }} {name} {{ #{project.slug} }}"
    )
    parts = ['<div class="card" markdown>']
    if project.picture is not None:
        parts.append(picture(project.picture, language))
    parts += [heading, project.summary[language]]
    if live:
        parts.append(live)
    parts += ["\n".join(buttons), "</div>"]
    return "\n\n".join(parts)


def section(
    catalog: Catalog, group: Group, language: str, levels: dict[int, str] | None = None
) -> str:
    """The Markdown of group: its heading with its id as its anchor, the grid with
    the card of every project in it, each with a repo with its live facts and the
    level of its OpenSSF Best Practices of levels, and its note below the cards."""
    parts = [
        f"## {group.heading[language]} {{ #{group.id} }}",
        '<div class="grid" markdown>',
        *(
            card(
                project,
                language,
                catalog.second(project),
                facts(catalog, project, language, levels or {}) if project.repo else "",
            )
            for project in catalog.members(group)
        ),
        "</div>",
    ]
    if group.note is not None:
        parts.append(f'<p class="note" markdown>{group.note[language]}</p>')
    return "\n\n".join(parts)


def script_data(catalog: Catalog, language: str) -> str:
    """The attributes of the part of a page that tell the script of the live facts
    where their data is, the language of the page and the texts of SCRIPT in it."""
    data = {
        "facts": FEED,
        "history": HISTORY,
        "locale": language,
        **{key: catalog.facts[key][language] for key in SCRIPT},
    }
    return "".join(f' data-{key}="{escape(text)}"' for key, text in data.items())


def cards(
    catalog: Catalog, language: str, levels: dict[int, str] | None = None
) -> str:
    """The Markdown of every group with its cards, in language, in a part of the page
    with its own anchor. The part tells the script of the live facts where their data
    is, the language of the page and the texts of the facts in it; levels holds the
    level of the OpenSSF Best Practices of each project by its number."""
    attributes = script_data(catalog, language)
    return "\n\n".join(
        [
            f'<div class="projects" id="{PROJECTS}"{attributes} markdown>',
            *(section(catalog, group, language, levels) for group in catalog.groups),
            "</div>",
        ]
    )


def best_practices(catalog: Catalog) -> dict[int, str]:
    """The level of the OpenSSF Best Practices of every project of the catalog that
    names its project at bestpractices.dev, by its number: passing, silver or gold.
    A project whose data can't be read, or that holds no level yet, has none, which
    the log says without a warning, so that the strict build passes."""
    numbers = sorted(
        {project.bestpractices for project in catalog.projects if project.bestpractices}
    )
    if not numbers:
        return {}

    def level(number: int) -> str | None:
        url = BEST_PRACTICES_DATA.format(number)
        try:
            data = json.loads(download(url))
        except (SearchError, ValueError) as error:
            log.info(
                "The cards leave out the level of %s until the next build: %s",
                url,
                error,
            )
            return None
        found = data.get("badge_level") if isinstance(data, dict) else None
        if found not in LEVELS:
            log.info("%s holds no level of the OpenSSF Best Practices: %r", url, found)
            return None
        return str(found)

    with ThreadPoolExecutor(max_workers=len(numbers)) as pool:
        found = dict(zip(numbers, pool.map(level, numbers), strict=True))
    return {number: text for number, text in found.items() if text is not None}


def levels_of(config: Any) -> dict[int, str]:
    """The levels of best_practices, read once for the build of every language."""
    if LEVEL not in config.extra:
        config.extra[LEVEL] = best_practices(config.extra["catalog"])
    return config.extra[LEVEL]


@dataclass(frozen=True)
class Release:
    """A release of a project, as the Releases page and What's new show it: its tag,
    its page on GitHub, the day it was published, its notes as the HTML that the page
    keeps of them, and their headline."""

    tag: str
    url: str
    day: date
    notes: str
    headline: str


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
        if name == "a":
            # A link that the notes leave out has left its text alone.
            if not (self.links and self.links.pop()):
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


def headline(notes: str) -> str:
    """The headline of notes, the HTML that the page keeps of the notes of a release,
    which What's new shows: the bold lead of their first item or paragraph without its
    colon, when it has more than one word, or else its first sentence without the
    references to its pull request and its commit, each cut to HEADLINE characters;
    or nothing for notes without an item or a paragraph."""
    first = NOTES_FIRST.search(notes)
    if first is None:
        return ""
    lead = NOTES_LEAD.match(first[2])
    if lead is not None:
        bold = plain(lead[1]).rstrip(":").strip()
        if " " in bold:
            return cut(bold, HEADLINE)
    text = REFERENCES.sub("", plain(first[2]))
    return cut(text.partition(". ")[0].removesuffix("."), HEADLINE)


def published(value: object) -> date | None:
    """The day of value, the time at which the API says that a release was
    published, such as 2026-10-15T21:33:15Z, or None."""
    found = PUBLISHED.fullmatch(value) if isinstance(value, str) else None
    if found is None:
        return None
    try:
        return date.fromisoformat(found[1])
    except ValueError:
        return None


def releases_in(repo: str, data: list[Any]) -> tuple[Release, ...]:
    """The RELEASES latest releases of repo in data, its releases as the API lists
    them, the newest first: each that is no draft and no prerelease, with a tag and
    the day it was published, with its page on GitHub and its notes as the page
    keeps them."""
    found: list[Release] = []
    for entry in data:
        if not isinstance(entry, dict) or entry.get("draft") or entry.get("prerelease"):
            continue
        tag, day = entry.get("tag_name"), published(entry.get("published_at"))
        if not isinstance(tag, str) or not TAG.fullmatch(tag) or day is None:
            continue
        body = entry.get("body_html")
        notes = notes_html(body if isinstance(body, str) else "", tag.removeprefix("v"))
        url = f"{GITHUB}{repo}/releases/tag/{tag}"
        found.append(Release(tag, url, day, notes, headline(notes)))
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
    none, which the log says without a warning, so that the strict build passes."""
    repos = list(dict.fromkeys(str(p.repo) for p in catalog.projects if p.repo))
    if not repos:
        return {}

    def read(repo: str) -> tuple[Release, ...] | None:
        try:
            data = json.loads(download(releases_request(repo)))
        except (SearchError, ValueError) as error:
            log.info(
                "The Releases page links the releases of %s on GitHub until the next "
                "build: %s",
                repo,
                error,
            )
            return None
        if not isinstance(data, list):
            log.info("The API of GitHub sent no list of the releases of %s", repo)
            return None
        return releases_in(repo, data)

    with ThreadPoolExecutor(max_workers=len(repos)) as pool:
        found = dict(zip(repos, pool.map(read, repos), strict=True))
    return {repo: releases for repo, releases in found.items() if releases is not None}


def notes_of(config: Any) -> dict[str, tuple[Release, ...]]:
    """The releases of release_notes, read once for the build of every language."""
    if NOTES not in config.extra:
        config.extra[NOTES] = release_notes(config.extra["catalog"])
    return config.extra[NOTES]


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


def news(
    catalog: Catalog, language: str, notes: dict[str, tuple[Release, ...]]
) -> str:
    """The HTML of What's new in language, in place of its marker: the latest release
    of every project with a repo of notes, the newest first, each with the name of its
    project and its tag, which link its notes on the Releases page, its day, which the
    script tells as the time since, and the headline of its notes. Its count, the
    number of projects with a repo, is how many releases the script shows, with a
    newer one of the data of the dashboard in place of one of the build."""
    count = sum(project.repo is not None for project in catalog.projects)
    items = []
    for project, release in latest(catalog, notes):
        day = release.day.isoformat()
        name = f"{project.name[language]} {release.tag}"
        lead = (
            f'<span class="{NEWS}__headline" lang="{NOTES_LANGUAGE}">'
            f"{escape(release.headline)}</span>"
            if release.headline
            else ""
        )
        items.append(
            f'<li data-repo="{escape(str(project.repo))}"'
            f' data-release="{escape(release.tag)}" data-released="{day}">'
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
    build, its releases of notes with a heading, their day, their link to GitHub and
    the placeholder of their notes, and a link to all its releases on GitHub."""
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
        parts += [
            f"## {project.name[language]} {{ #{project.slug} }}",
            f'<div class="release-newer" data-repo="{escape(repo)}"'
            f' data-releases="{escape(" ".join(r.tag for r in releases))}"'
            f' data-released="{newest}"></div>',
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


def short_name(project: Project, language: str) -> str:
    """The name of project in a few words, in language: its short one, if it has
    one."""
    return (project.short or project.name)[language]


def trust_cell(
    catalog: Catalog,
    project: Project,
    key: str,
    language: str,
    levels: dict[int, str],
) -> str:
    """The HTML of the cell of project, which has a repo, in the row key of the
    table of the Trust page: the place of a value of the script for a row of
    TRUST_LIVE, the level of its OpenSSF Best Practices of levels, which links its
    page at bestpractices.dev, or the value that every project shares, which links
    its security policy or its form for private reports in their rows."""
    repo = escape(str(project.repo))
    if key in TRUST_LIVE:
        content = DASH
        if key == "release":
            content = f'<a href="{GITHUB}{repo}/releases/latest">GitHub</a>'
        return f'<td data-repo="{repo}" data-fact="{key}">{content}</td>'
    if key == "bestpractices":
        level = levels.get(project.bestpractices or 0)
        content = DASH
        if level is not None:
            page = BEST_PRACTICES.format(project.bestpractices)
            content = f'<a href="{page}">{escape(catalog.facts[level][language])}</a>'
        return f"<td>{content}</td>"
    value = escape(catalog.trust.values[key][language])
    links = {
        "policy": f"{GITHUB}{repo}/blob/main/SECURITY.md",
        "report": f"{GITHUB}{repo}/security/advisories/new",
    }
    if key in links:
        value = f'<a href="{links[key]}">{value}</a>'
    return f"<td>{value}</td>"


def trust_table(
    catalog: Catalog, language: str, levels: dict[int, str] | None = None
) -> str:
    """The HTML of the table of the Trust page in language, with its note below it,
    in Markdown: a column for every project with a repo, under its short name, which
    links its website, and a row for every guarantee of TRUST_ROWS. Its part of the
    page tells the script where the data of the dashboard is and the language of the
    page; levels holds the level of the OpenSSF Best Practices of each project by
    its number."""
    texts = {key: text[language] for key, text in catalog.trust.texts.items()}
    projects = [project for project in catalog.projects if project.repo is not None]
    data = {"facts": FEED, "history": HISTORY, "locale": language}
    attributes = "".join(f' data-{key}="{escape(text)}"' for key, text in data.items())
    head = "".join(
        f'<th scope="col"><a href="{escape(project.website[language])}">'
        f"{escape(short_name(project, language))}</a></th>"
        for project in projects
    )
    rows = [
        f'<tr><th scope="row">{escape(texts[key])}</th>'
        + "".join(
            trust_cell(catalog, project, key, language, levels or {})
            for project in projects
        )
        + "</tr>"
        for key in TRUST_ROWS
    ]
    return "\n".join(
        [
            f'<div class="{TRUST}"{attributes}>',
            "<table>",
            f"<caption>{escape(texts['caption'])}</caption>",
            f'<thead><tr><th scope="col">{escape(texts["guarantee"])}</th>{head}'
            "</tr></thead>",
            "<tbody>",
            *rows,
            "</tbody>",
            "</table>",
            "</div>",
            "",
            texts["note"],
        ]
    )


def verification(catalog: Catalog, language: str) -> str:
    """The Markdown of the commands that verify the latest release of every project
    with a repo, a tab for each under its short name in language, with the GitHub
    CLI: the attestation of the release, which ties its tag to its commit and to its
    files, and the provenance of the file that Project.verified names, which the
    workflow SIGNER of its repository signed. Each command stands on a line of its
    own, so that it runs as it is copied into any shell."""
    tabs = []
    for project in catalog.projects:
        if project.repo is None:
            continue
        repo, file = project.repo, project.verified
        commands = [
            "```sh",
            f"gh release verify --repo {repo}",
            f"gh release download --repo {repo} --pattern {file} --clobber",
            f"gh attestation verify {file} --repo {repo}"
            f" --signer-workflow {repo}/{SIGNER}",
            "```",
        ]
        title = short_name(project, language).replace('"', "&quot;")
        block = "\n".join(f"    {line}" for line in commands)
        tabs.append(f'=== "{title}"\n\n{block}')
    return "\n\n".join(tabs)


def home_language(catalog: Catalog, dest_uri: str) -> str | None:
    """The language of the home page that MkDocs writes to dest_uri, index.html at
    the root for the default language and in the folder of each other one, or None
    for every other page."""
    homes = {HOME: catalog.default} | {
        f"{language}/{HOME}": language for language in catalog.languages[1:]
    }
    return homes.get(dest_uri)


def cell(text: str) -> str:
    """text in a cell of a table of Markdown, where a | would end the cell."""
    return text.replace("|", "\\|")


def links(texts: dict[str, str], urls: dict[str, str]) -> str:
    """A link to every address of urls once, in the order of the languages, each with
    the text of its language."""
    first: dict[str, str] = {}
    for language, url in urls.items():
        first.setdefault(url, language)
    return " · ".join(
        f"[{cell(texts[language])}]({url})" for url, language in first.items()
    )


def table(catalog: Catalog) -> str:
    """The table of the README: every project with its repository, its first button
    and its website, with the address of every language. The link check of the
    Markdown, which reads no TOML, so checks every address of projects.toml."""
    language = catalog.default
    rows = [
        "| Project | What it does | Start | Website |",
        "| --- | --- | --- | --- |",
    ]
    for project in catalog.projects:
        name = cell(project.name[language])
        if project.repo is not None:
            repository = project.repo.partition("/")[2]
            name = f"[{repository}](https://github.com/{project.repo})"
        start = links(project.start.label, project.start.url)
        website = "—"
        if project.docs is not None:
            shown = {
                code: url.removeprefix("https://").rstrip("/")
                for code, url in project.docs.url.items()
            }
            website = links(shown, project.docs.url)
        tagline = cell(project.tagline[language])
        rows.append(f"| {name} | {tagline} | {start} | {website} |")
    return "\n".join(rows)


def readme(text: str, catalog: Catalog) -> str:
    """text, that of README.md, with the table of catalog between its markers."""
    start = text.find(TABLE_START)
    end = text.find(TABLE_END)
    if start < 0 or end < start:
        raise CatalogError(
            f"{README} needs the lines {TABLE_START} and {TABLE_END}, in this order; "
            "the table of the projects goes between them."
        )
    head = text[: start + len(TABLE_START)]
    return f"{head}\n\n{table(catalog)}\n\n{text[end:]}"


# The files at the root of the address, and the structured data of the home page.


def sitemaps(catalog: Catalog, site_url: str) -> list[str]:
    """The sitemap of this website and that of every project whose documentation
    lives at the same address, each once."""
    found = [urljoin(site_url, "sitemap.xml")]
    for project in catalog.projects:
        if project.docs is None:
            continue
        # The sitemap of a website in several languages lists every language.
        url = project.docs.url[catalog.default]
        if url.startswith(site_url):
            found.append(urljoin(url, "sitemap.xml"))
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


def build_date() -> date:
    """The day of the build in UTC, or that of SOURCE_DATE_EPOCH, which makes the
    same build come out the same on every day."""
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    moment = datetime.fromtimestamp(int(epoch), UTC) if epoch else datetime.now(UTC)
    return moment.date()


def sitemaps_at_root(site: Path, site_url: str) -> None:
    """Lead every sitemap of the website in site to the root of the address where it
    names the home page of the default language as index.html: as the version in
    that language of the German home page, which the i18n plugin lists without the
    page and so without its canonical address. The packed sitemap.xml.gz keeps the
    time of its build."""
    home = re.compile(rf'(?<=[">]){re.escape(urljoin(site_url, HOME))}(?=["<])')
    for path in site.rglob("sitemap.xml"):
        text = path.read_text(encoding="utf-8")
        path.write_text(home.sub(site_url, text), encoding="utf-8", newline="\n")
    packed = site / "sitemap.xml.gz"
    if packed.is_file():
        with gzip.GzipFile(packed) as reader:
            text = reader.read().decode("utf-8")
            built = reader.mtime
        with gzip.GzipFile(packed, "wb", mtime=built) as writer:
            writer.write(home.sub(site_url, text).encode("utf-8"))


def structured_data(catalog: Catalog, site_url: str, site_name: str) -> str:
    """The tags for the head of the home page: the link to the owner's profile, and
    the JSON-LD of the website, its owner and every project with a repository.

    Search engines take the name of a website from the home page at the root of a
    host alone, so this one names it for every website of the address.
    """
    language = catalog.default
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
                        "runtimePlatform": project.platform,
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


# The search of every project.


class SearchError(Exception):
    """The search index of a project website can't be downloaded, or isn't one."""


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


def rank_of(page: str) -> Rank | None:
    """The rank of the sections of page, the location of a page of a website without
    its #, such as de/installation.html or installation/, or None for a decision
    record, whose sections the search leaves out."""
    parts = page.split("/")
    if DECISIONS in parts[:-1]:
        return None
    names = [part.removesuffix(".html") for part in parts if part]
    # A page kept as the index of its folder, such as guide/index.html, is named
    # after its folder.
    if len(names) > 1 and names[-1] == "index":
        names.pop()
    name = names[-1] if names else ""
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


def download(url: str | urllib.request.Request) -> bytes:
    """The content of url, or of the address of a request with its headers, tried
    TRIES times before SearchError."""
    problem: Exception | None = None
    for _ in range(TRIES):
        try:
            with urllib.request.urlopen(url, timeout=SEARCH_TIMEOUT) as response:
                return bytes(response.read())
        except urllib.error.HTTPError as error:
            error.close()
            problem = error
        # As in status: a broken answer is no OSError, and urllib raises a
        # ValueError for an address that it can't ask.
        except (OSError, http.client.HTTPException, ValueError) as error:
            problem = error
    address = url.full_url if isinstance(url, urllib.request.Request) else url
    raise SearchError(f"{address} can't be downloaded: {problem}")


def documents(content: bytes, url: str) -> list[dict[str, Any]]:
    """The entries of content, the search index at url, as the search plugin of
    Material writes it: each with its location, its title and its text."""
    try:
        data = json.loads(content)
    # Also a UnicodeDecodeError, which is a ValueError too.
    except ValueError as error:
        raise SearchError(f"{url} is no JSON: {error}") from error
    docs = data.get("docs") if isinstance(data, dict) else None
    if not isinstance(docs, list) or not all(
        isinstance(doc, dict)
        and all(isinstance(doc.get(key), str) for key in ("location", "title"))
        and isinstance(doc.get("text", ""), str)
        for doc in docs
    ):
        raise SearchError(
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


def project_search(catalog: Catalog, site_url: str) -> tuple[list[str], list[Any]]:
    """The folders of the project websites at site_url, and the entries of their
    search indexes for the index of this website, BUDGET bytes at most. A website
    whose index can't be downloaded or read has none, which the log says without a
    warning, so that the strict build passes while a website is away. The log says
    how many pages and sections of each website the search keeps, so that a drop
    shows in the log of the build."""
    sites = websites(catalog, site_url)
    if not sites:
        return [], []

    def search(website: Website) -> list[Entry]:
        url = urljoin(site_url, f"{website.folder}{SEARCH_INDEX}")
        try:
            docs = documents(download(url), url)
        except SearchError as error:
            log.info(
                "The search leaves out the website of %s until the next build: %s",
                website.project.slug,
                error,
            )
            return []
        return entries(catalog, website, docs)

    # Every website at once, so that a slow one doesn't wait for the others.
    with ThreadPoolExecutor(max_workers=len(sites)) as pool:
        found = list(pool.map(search, sites))
    chosen = within(found, BUDGET)
    for website, docs, its in zip(sites, found, chosen, strict=True):
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
    log.info(
        "The search adds %d entries of %d of the %d project websites.",
        len(kept),
        sum(1 for docs in found if docs),
        len(sites),
    )
    return [website.folder for website in sites], kept


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


# The hooks of MkDocs.


def built_languages(config: Any) -> list[Any]:
    """The languages that the i18n plugin builds the website in, the default first."""
    plugin = config.plugins.get("i18n")
    if plugin is None:
        return []
    languages = [language for language in plugin.config.languages if language.build]
    return sorted(languages, key=lambda language: not language.default)


def titles(nav: Any) -> Iterator[str]:
    """The titles of the menu of mkdocs.yml, with those of its sections."""
    for item in nav or []:
        if isinstance(item, dict):
            for title, value in item.items():
                yield title
                if isinstance(value, list):
                    yield from titles(value)


def check_languages(catalog: Catalog, languages: list[Any]) -> None:
    """Warn about a language of the website that the catalog has no texts in."""
    for language in languages:
        if language.locale not in catalog.languages:
            log.warning(
                "The website is built in %s, but %s has no texts in it: add %s to "
                "its languages, and a text in it to every project.",
                language.locale,
                CATALOG,
                language.locale,
            )


def check_menu(nav: Any, languages: list[Any]) -> None:
    """Warn about a title of the menu that a further language doesn't translate."""
    for language in languages[1:]:
        translations = language.nav_translations or {}
        for title in titles(nav):
            if title not in translations:
                log.warning(
                    "The menu title '%s' has no translation in %s: add it to "
                    "nav_translations of %s in mkdocs.yml.",
                    title,
                    language.locale,
                    language.locale,
                )


def check_order(config: Any) -> None:
    """Warn when the i18n plugin would write the search index after this hook adds
    the project websites to it, which would drop them without a word.

    The i18n plugin writes the index of every language in its on_post_build, and
    MkDocs runs the event of the higher priority first. The hook asks for a lower
    one than the plugin's, rather than for the order in which MkDocs registers the
    two, so that a version of the plugin that lowers its own stops the build.
    """
    method = getattr(config.plugins.get("i18n"), "on_post_build", None)
    if method is None:
        return
    theirs = getattr(method, "mkdocs_priority", 0)
    ours = on_post_build.mkdocs_priority  # type: ignore[attr-defined]
    if theirs <= ours:
        log.warning(
            "The i18n plugin writes the search index with the priority %d, after the "
            "%d of on_post_build of .github/mkdocs_project.py, so the search would "
            "lose the pages of the project websites: set on_post_build."
            "mkdocs_priority there below %d.",
            theirs,
            ours,
            theirs,
        )


def check_pages(docs: Path, languages: list[Any]) -> None:
    """Warn about a page of docs/ without its translation into a further language,
    and about a page of UNTRANSLATED that has one by now. A page of the default
    language may carry its suffix, such as guide.en.md beside guide.de.md."""
    locales = [language.locale for language in languages]
    further = locales[1:]
    for page in sorted(docs.rglob("*.md")):
        path = page.relative_to(docs).as_posix()
        suffixes = page.suffixes
        suffix = suffixes[-2][1:] if len(suffixes) > 1 else ""
        if path.startswith(ENGLISH_ONLY) or suffix in further:
            continue
        base = page.name.removesuffix(".md")
        if suffix in locales[:1]:
            base = base.removesuffix(f".{suffix}")
        listed = page.with_name(f"{base}.md").relative_to(docs).as_posix()
        for locale in further:
            twin = page.with_name(f"{base}.{locale}.md")
            translation = twin.relative_to(docs).as_posix()
            if listed in UNTRANSLATED and twin.is_file():
                log.warning(
                    "docs/%s has its translation docs/%s now: remove it from "
                    "UNTRANSLATED in .github/mkdocs_project.py.",
                    path,
                    translation,
                )
            elif listed not in UNTRANSLATED and not twin.is_file():
                log.warning(
                    "docs/%s has no translation in %s: write docs/%s, or list the "
                    "page in UNTRANSLATED of .github/mkdocs_project.py.",
                    path,
                    locale,
                    translation,
                )


def on_config(config: Any) -> Any:
    """Read the catalog for the cards and the templates, check the translations, and
    check that the project websites reach the search index of every language.

    The i18n plugin builds every further language with the same configuration, which
    has the catalog by then; the checks run once, for every language.
    """
    if "catalog" in config.extra:
        return config
    try:
        catalog = load(Path(config.config_file_path).parent)
    except CatalogError as error:
        # MkDocs only when it builds, so that the script needs the standard library.
        from mkdocs.exceptions import PluginError

        raise PluginError(str(error)) from error
    config.extra["catalog"] = catalog
    languages = built_languages(config)
    check_languages(catalog, languages)
    check_menu(config.nav, languages)
    check_pages(Path(config.docs_dir), languages)
    check_order(config)
    return config


def on_files(files: Any, config: Any) -> Any:
    """Warn about a file of this website in a folder of former, where a page at an
    old address would replace it, or it would hide that the website there moved."""
    catalog: Catalog = config.extra["catalog"]
    folders = tuple(f"{folder}/" for folder in catalog.moves())
    for file in files:
        if file.dest_uri.startswith(folders):
            log.warning(
                "The website writes %s into %s, the folder of a former website in "
                "%s, whose old addresses lead to its website now: move the file out "
                "of the folder.",
                file.dest_uri,
                file.dest_uri.partition("/")[0],
                CATALOG,
            )
    return files


def on_serve(server: Any, config: Any, builder: Any) -> Any:
    """Build the website again when projects.toml changes, while mkdocs serve runs."""
    server.watch(str(Path(config.config_file_path).parent / CATALOG))
    return server


def page_language(catalog: Catalog, page: Any) -> str:
    """The language of the file of page, which the i18n plugin sets, or the default
    one of the catalog for a language that it doesn't know."""
    locale = getattr(page.file, "locale", None)
    return locale if locale in catalog.languages else catalog.default


def on_page_markdown(markdown: str, page: Any, config: Any, files: Any) -> str:
    """Put the cards of the projects, the table of their guarantees, the commands
    that verify their releases, their releases and What's new in place of their
    markers, in the language of the page's file, which the i18n plugin sets: a page
    that a further language shows in the default one gets them in the default one
    too."""
    catalog: Catalog = config.extra["catalog"]
    language = page_language(catalog, page)
    markdown = MARKER_LINE.sub(
        lambda _: cards(catalog, language, levels_of(config)), markdown
    )
    markdown = TRUST_LINE.sub(
        lambda _: trust_table(catalog, language, levels_of(config)), markdown
    )
    markdown = VERIFY_LINE.sub(lambda _: verification(catalog, language), markdown)
    markdown = NOTES_LINE.sub(
        lambda _: release_history(catalog, language, notes_of(config)), markdown
    )
    return NEWS_LINE.sub(lambda _: news(catalog, language, notes_of(config)), markdown)


def on_page_content(html: str, page: Any, config: Any, files: Any) -> str:
    """Put the notes of every release of the Releases page in place of their
    placeholders, in the HTML that MkDocs has made of the Markdown of the page, so
    that the notes pass through no extension of Markdown. The search, which every
    language shares, takes them from the page in NOTES_LANGUAGE alone."""
    if NOTES_PLACE.search(html) is None:
        return html
    catalog: Catalog = config.extra["catalog"]
    language = page_language(catalog, page)
    attributes = f' lang="{NOTES_LANGUAGE}"'
    if language != NOTES_LANGUAGE:
        attributes += " data-search-exclude"
    found = {
        escape(f"{repo}@{release.tag}"): release.notes
        for repo, releases in notes_of(config).items()
        for release in releases
    }
    return NOTES_PLACE.sub(
        lambda place: f'<div class="release-notes"{attributes}>'
        f"{found.get(place[1], '')}</div>",
        html,
    )


def on_pre_page(page: Any, config: Any, files: Any) -> Any:
    """Make the root of the address the canonical address of the home page of the
    default language, rather than index.html in it, as the url of the WebSite of the
    structured data says. The link rel=canonical of the page, its og:url and the
    sitemap take it from the page, which MkDocs has just made."""
    if page.file.dest_uri == HOME:
        page.canonical_url = config.site_url
    return page


def on_page_context(context: Any, page: Any, config: Any, nav: Any) -> Any:
    """Lead the links between the languages of a page, its hreflang links and the
    language switch, to the root of the address where they name the home page of
    the default language, as its canonical address does.

    The i18n plugin sets them anew for every page just before, with the address of
    each language's version of the page, as MkDocs writes that of a page: relative
    to the root of the website, such as index.html and de/index.html. It sets them
    as an attribute of extra, which the templates read before its item.
    """
    for alternate in getattr(config.extra, "alternate", None) or []:
        if alternate.get("link") == HOME:
            alternate["link"] = "./"
    return context


def on_post_page(output: str, page: Any, config: Any) -> str:
    """Put the structured data of the address into the home page of the default
    language, index.html at the root, and into no other page.

    That home page gets the title of the page on its preview card for shared links
    too: the social plugin of Material gives it the bare name of the website, while
    the German one, which Material doesn't count as the home page, has the title of
    its front matter already.
    """
    if page.file.dest_uri != HOME:
        return output
    catalog: Catalog = config.extra["catalog"]
    title = page.meta.get("title")
    if title:
        content = escape(f"{title} - {config.site_name}")
        output = SOCIAL_TITLE.sub(lambda tag: f"{tag[1]}{content}{tag[2]}", output)
    head = structured_data(catalog, config.site_url, config.site_name)
    return output.replace("</head>", f"{head}</head>", 1)


def on_post_build(config: Any) -> None:
    """Write robots.txt and security.txt at the root of the address and a page at
    every old address of a website that moved, lead the sitemaps to its root for the
    home page of the default language, and add the project websites to the search
    index.

    The i18n plugin builds every further language into the same folder after the
    default one, and each build writes the same files again. It writes the search
    index for every language last, so this hook runs after it, and the index of
    every project is downloaded once.
    """
    catalog: Catalog = config.extra["catalog"]
    site = Path(config.site_dir)
    # A website without the search plugin has no index to add to.
    if (site / SEARCH_INDEX).is_file():
        if SEARCH not in config.extra:
            config.extra[SEARCH] = project_search(catalog, config.site_url)
        add_to_search(site, *config.extra[SEARCH])
    files = dict.fromkeys(
        SECURITY_TXT, security_txt(catalog, config.site_url, build_date())
    )
    files["robots.txt"] = robots(catalog, config.site_url)
    files.update(moved_pages(catalog))
    for name, text in files.items():
        path = site / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
    sitemaps_at_root(site, config.site_url)
    if not (site / POLICY).is_file():
        log.warning(
            "security.txt names %s as the policy of the address, but the website has "
            "no such page: keep docs/security.md, or change POLICY in "
            ".github/mkdocs_project.py.",
            urljoin(config.site_url, POLICY),
        )


# Last of all plugins, after the i18n plugin, which comes last with -100: what the
# decorator event_priority(-110) of mkdocs.plugins sets, which the script can't
# import. check_order stops the build when a new version of the plugin comes later.
on_post_build.mkdocs_priority = -110  # type: ignore[attr-defined]


# The catalog bot.


class CheckError(Exception):
    """The catalog bot can't tell whether the catalog is current: the list of the
    repositories is broken, or a website can't be reached or answers oddly."""


@dataclass(frozen=True)
class Repository:
    """A repository of the owner on GitHub, as gh repo list describes it."""

    name: str
    homepage: str
    archived: bool
    private: bool


def listed(item: object) -> bool:
    """Whether item describes a repository with every field of FIELDS."""
    return (
        isinstance(item, dict)
        and all(field in item for field in FIELDS)
        and isinstance(item["nameWithOwner"], str)
        and isinstance(item["homepageUrl"], str | None)
        and isinstance(item["isArchived"], bool)
        and isinstance(item["isPrivate"], bool)
    )


def repositories(text: str) -> list[Repository]:
    """The repositories of text, the JSON that gh repo list writes with the fields of
    FIELDS."""
    wanted = f"the JSON of gh repo list --json {','.join(FIELDS)}"
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise CheckError(
            f"The list of the repositories isn't {wanted}: {error}"
        ) from error
    # An empty list is one that went wrong, not an owner without repositories, and
    # would report every project of the catalog as gone.
    if not isinstance(data, list) or not data or not all(map(listed, data)):
        raise CheckError(
            f"The list of the repositories must be {wanted}, with one at least."
        )
    return [
        Repository(
            item["nameWithOwner"],
            item["homepageUrl"] or "",
            item["isArchived"],
            item["isPrivate"],
        )
        for item in data
    ]


def address(url: str) -> str:
    """url as the bot compares addresses: with https://, its host in lowercase and
    its path ending in a slash, as GitHub Pages serves the folder of a website."""
    parts = urlsplit(url.strip())
    return f"https://{parts.netloc.lower()}{parts.path.rstrip('/')}/"


def at_site(url: str) -> bool:
    """Whether url is the address of a website in a folder of SITE, as that of a
    project is: neither this website at its root nor one elsewhere."""
    found = address(url)
    return found.startswith(SITE) and found != SITE


def status(url: str) -> int:
    """The HTTP status with which url answers a HEAD request, after its redirects."""
    request = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return int(response.status)
    except urllib.error.HTTPError as error:
        error.close()
        return error.code
    # http.client.HTTPException, such as a broken status line, is no OSError, and
    # urllib raises a ValueError for an address that it can't ask.
    except (OSError, http.client.HTTPException, ValueError) as error:
        raise CheckError(f"{url} can't be reached: {error}") from error


def exists(probe: Callable[[str], int], url: str) -> bool:
    """Whether the website at url is there, by the status that probe gives: 200 is
    a website, 404 and 410 none, and anything else no answer to rely on."""
    code = probe(url)
    if code == 200:
        return True
    if code in GONE:
        return False
    raise CheckError(
        f"{url} answers {code}, where the catalog bot expects 200 or 404; "
        "start it again later."
    )


def repository_drift(
    project: Project,
    found: dict[str, Repository],
    websites: dict[str, Repository],
    named: set[str],
    language: str,
) -> list[str]:
    """What differs between project and its repository on GitHub, found by its name
    in lowercase: gone, perhaps renamed to the public repository of websites that
    has its website, private, archived, or with another website. named holds the
    repositories of the catalog in lowercase, and language is the default one."""
    if project.repo is None:
        return []
    slug, repo, website = project.slug, project.repo, project.website[language]
    repository = found.get(repo.lower())
    if repository is None:
        successor = websites.get(address(website))
        if successor is not None and successor.name.lower() not in named:
            return [
                f"`{slug}`: {repo} is no repository on GitHub any more, and "
                f"{successor.name} has its website {website}; it was renamed. Set "
                f'`repo = "{successor.name}"`.'
            ]
        return [
            f"`{slug}`: {repo} is no public repository on GitHub any more; it was "
            "renamed, made private or deleted. Correct `repo`, or remove the project."
        ]
    if repository.private:
        return [
            f"`{slug}`: {repo} is private now. Remove the project, or make the "
            "repository public again."
        ]
    if repository.archived:
        return [
            f"`{slug}`: {repo} is archived. Remove the project, or unarchive the "
            "repository."
        ]
    homepage = repository.homepage
    if at_site(homepage) and address(homepage) != address(website):
        return [
            f"`{slug}`: {repo} names {homepage} as its website on GitHub, but "
            f"{CATALOG} leads to {website}. Correct `docs`, or the website of the "
            "repository."
        ]
    return []


def language_drift(
    catalog: Catalog, project: Project, probe: Callable[[str], int]
) -> list[str]:
    """What differs between the documentation of project in the further languages
    of catalog and its websites in them, which probe asks for their status: a
    website in a language that the catalog doesn't lead to, and one that it leads to
    and that is gone.

    Only a website at SITE is asked, built as MkDocs builds one in several
    languages: each further language in a folder named after it, such as de/.
    """
    if project.docs is None:
        return []
    urls, slug = project.docs.url, project.slug
    first = urls[catalog.default]
    if not at_site(first):
        return []
    differences = []
    default = LANGUAGE_NAMES.get(catalog.default, catalog.default)
    for language in catalog.languages[1:]:
        name = LANGUAGE_NAMES.get(language, language)
        if urls[language] != first:
            if not exists(probe, urls[language]):
                differences.append(
                    f"`{slug}`: the {name} website {urls[language]} is gone. Remove "
                    f"`docs.{language}`, so that the {name} home page leads to the "
                    f"{default} one."
                )
        elif exists(probe, url := f"{address(first)}{language}/"):
            differences.append(
                f"`{slug}`: it has a {name} website at {url} now. Write "
                f'`docs.{catalog.default} = "{first}"` and `docs.{language} = "{url}"` '
                f"in place of `docs`, so that the {name} home page leads there."
            )
    return differences


def drift(
    catalog: Catalog, found: list[Repository], probe: Callable[[str], int]
) -> list[str]:
    """What differs between catalog and the repositories of its owner, found, and the
    websites of its projects, which probe asks for their status: one sentence of
    Markdown each, in the order of the catalog, and then every public repository
    with a website at SITE that no project names.

    A private repository counts only when the catalog names it, so that the text,
    which becomes a public issue, never names one that only a person's token sees.
    """
    by_name = {repository.name.lower(): repository for repository in found}
    # The public repositories with a website at SITE, by their names.
    published = sorted(
        (
            repository
            for repository in found
            if not repository.private
            and not repository.archived
            and at_site(repository.homepage)
        ),
        key=lambda repository: repository.name.lower(),
    )
    websites: dict[str, Repository] = {}
    for repository in published:
        websites.setdefault(address(repository.homepage), repository)
    named = {project.repo.lower() for project in catalog.projects if project.repo}
    differences: list[str] = []
    for project in catalog.projects:
        differences += repository_drift(
            project, by_name, websites, named, catalog.default
        )
        differences += language_drift(catalog, project, probe)
    # The website of a project of the catalog is no new one: its repository was
    # renamed, as the project says, or another repository names it too.
    shown = {address(project.website[catalog.default]) for project in catalog.projects}
    differences += [
        f"{repository.name} has its website at {repository.homepage}, but {CATALOG} "
        f'has no project for it. Add a `[[project]]` with `repo = "{repository.name}"`.'
        for repository in published
        if repository.name.lower() not in named
        and address(repository.homepage) not in shown
    ]
    return differences


def report(differences: list[str]) -> str:
    """The text of the issue of the catalog bot, in Markdown, with differences."""
    return "\n".join(
        [
            f"The catalog bot compares {CATALOG} with the repositories on GitHub and "
            "with the websites of the projects in every language every week, and "
            f"found {len(differences)} difference(s):",
            "",
            *(f"- {difference}" for difference in differences),
            "",
            f"Change {CATALOG}, whose comments describe every key, and write the "
            "table of the README with",
            "",
            "```sh",
            WRITE,
            "```",
            "",
            "A new card needs its picture too, which "
            "`bash scripts/project-pictures.sh` makes. The next run closes this issue "
            "once the catalog is current; start the Catalog workflow by hand to "
            "check sooner.",
            "",
        ]
    )


def network(path: Path, root: Path) -> int:
    """Compare the catalog in the folder root with the repositories in path, the
    JSON of gh repo list, and with the websites of the projects: 0 when the catalog
    is current, DIFFERS with the text of the issue on stdout, 2 when the bot can't
    tell."""
    try:
        catalog = load(root)
        found = repositories(path.read_text(encoding="utf-8"))
        differences = drift(catalog, found, status)
    except (CatalogError, CheckError, OSError) as error:
        print(error, file=sys.stderr)
        return 2
    if not differences:
        print(
            f"{CATALOG} is current: it has every repository with a website at "
            f"{SITE}, and every website in a further language."
        )
        return 0
    sys.stdout.write(report(differences))
    return DIFFERS


# The script.


def pictures(catalog: Catalog) -> str:
    """The pictures of the cards that come from the social preview of a repository,
    one per line for scripts/project-pictures.sh: the repository, the file in the
    repository that the picture goes to, and the license of the repository, which
    is that of the picture too."""
    return "".join(
        f"{project.repo} docs/{project.picture.src} {project.license}\n"
        for project in catalog.projects
        if project.repo is not None and project.picture is not None
    )


def main(argv: list[str] | None = None, root: Path = ROOT) -> int:
    """Write or check the table of the projects in README.md, list the pictures of
    the cards, or compare the catalog with GitHub and the websites of the projects
    for the catalog bot."""
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            # The console of Windows may lack a character of the README.
            stream.reconfigure(errors="backslashreplace")
    parser = argparse.ArgumentParser(
        description=f"Write or check the table of the projects in {README}, "
        f"from {CATALOG}, list the pictures of the cards, or compare {CATALOG} "
        "with GitHub and the websites of the projects."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--write", action="store_true", help=f"write the table into {README}"
    )
    mode.add_argument(
        "--check",
        action="store_true",
        help=f"check {CATALOG}, and that {README} has its table",
    )
    mode.add_argument(
        "--pictures",
        action="store_true",
        help="list the repository, the picture and the license of every card "
        "whose picture comes from a repository, for scripts/project-pictures.sh",
    )
    mode.add_argument(
        "--network",
        metavar="REPOSITORIES",
        type=Path,
        help=f"compare {CATALOG} with the repositories of the file REPOSITORIES, "
        f"which gh repo list --json {','.join(FIELDS)} writes, and with the "
        "websites of the projects in every language, and print what differs as "
        "the issue of the catalog bot: exit 0 when nothing differs, "
        f"{DIFFERS} when something does, and 2 when it can't tell",
    )
    arguments = parser.parse_args(argv)
    if arguments.network is not None:
        return network(arguments.network, root)
    path = root / README
    try:
        catalog = load(root)
        if arguments.pictures:
            sys.stdout.write(pictures(catalog))
            return 0
        current = path.read_text(encoding="utf-8")
        wanted = readme(current, catalog)
    except (CatalogError, OSError) as error:
        print(error, file=sys.stderr)
        return 1
    if wanted == current:
        print(f"{README} has the current table of the projects of {CATALOG}.")
        return 0
    if arguments.write:
        path.write_text(wanted, encoding="utf-8", newline="\n")
        print(f"{README} has the table of the projects of {CATALOG} now.")
        return 0
    sys.stdout.writelines(
        difflib.unified_diff(
            current.splitlines(keepends=True),
            wanted.splitlines(keepends=True),
            README,
            f"{README}, from {CATALOG}",
        )
    )
    print(
        f"{README} differs from {CATALOG}; write its table with\n  {WRITE}",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
