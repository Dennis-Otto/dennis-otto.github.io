"""The hooks of this website, beside those that every website shares in
.github/mkdocs_blueprint.py; mkdocs.yml names both files.

projects.toml, at the root of the repository, lists every project once: its name,
its texts, its picture and its links in each language of the website. From it, the
hooks put the groups of the projects with a card for each into the home page, in
the language of the page, and give the templates the whole list as
config.extra["catalog"], for the 404 page of overrides/404.html. Run as a script,
with nothing but the standard library, this file writes the table of the projects
in README.md and in the German README.de.md, or checks that both tables are current,
as scripts/check-project.sh does; and it lists the pictures of the cards that
scripts/project-pictures.sh makes from the social preview of each repository, in the
first language, and writes the pages from which it draws those of the other languages that have a picture of their
own, with the icon of a card from Material for MkDocs when it needs one:

    python3 -I .github/mkdocs_project.py --write
    python3 -I .github/mkdocs_project.py --check
    python3 -I .github/mkdocs_project.py --pictures
    python3 -I .github/mkdocs_project.py --drawings .cache/pictures

The card of a project with a repo also gets the part of its live facts: the level
of its OpenSSF Best Practices, which the hooks read from bestpractices.dev, and its
repository, for which the script docs/javascripts/projects.js writes its latest
release and its quality numbers from the data of the dashboard into the card as the
page loads. The line <!-- releases --> of the home pages becomes What's new: the
latest release of every project with a repo, the newest first, each with the
headline of its notes, which the hooks read from the API of GitHub, and which the
script brings up to date.

The card of a project that says what it works with, requires in projects.toml, gets
a line about it above its buttons, such as "Works with Home Assistant 2026.8.0 or
newer": a text of the catalog, or one with the values that the hooks read from a
file of the repository at the tag of its latest release, such as homeassistant of
hacs.json, from raw.githubusercontent.com, which needs no token. A file or a value
that can't be read leaves the line off the card until the next build, which passes.
The table of the README names the file, and the structured data the requirements.

The Releases page, docs/releases.md and docs/releases.de.md, gets the notes of the
latest releases of every project with a repo in place of its line
<!-- release-notes -->, under a heading of each project, from the same releases: the
HTML that GitHub makes of their Markdown, of which the page keeps only text,
headings, lists, tables, code and links to https. Without the API, the page links the
releases of each project on GitHub, and the build passes.

The Trust page, docs/trust.md and docs/trust.de.md, gets the guarantees of every
project with a repo, from the texts of [trust] in projects.toml, in two parts that
each read on a phone, under the headings of the page: what every project guarantees
alike, each guarantee once, in place of its line <!-- trust-shared -->, and in place
of its line <!-- trust --> a table with a row for each project and a column for
each of its numbers, which becomes a card for each project on a narrow screen.
The script fills the cells of its latest release and of its numbers from the same
data as on the cards, and the build names the level of its OpenSSF Best Practices.
The line <!-- verify --> becomes the commands that verify the latest release of
every project with the GitHub CLI, a tab for each.

Every week the catalog bot, .github/workflows/catalog.yml, compares the catalog with
the repositories of its owner on GitHub, which gh writes into a file, with the
websites of the projects in every language, and with the files that say what they
work with on the default branch of each, and keeps an issue with what differs:

    gh repo list Dennis-Otto --limit 1000 \\
      --json nameWithOwner,homepageUrl,isArchived,isPrivate >repositories.json
    python3 -I .github/mkdocs_project.py --network repositories.json

Every day the bot also watches what the published website depends on after its
build and nothing else checks: the data of the dashboard, against the schema and the
fields that docs/javascripts/projects.js reads, which .github/dashboard-fields.json
names; the search index of every project website, which the next build takes into
the search; both copies of security.txt, which must hold for 330 days more,
robots.txt with every sitemap and the sitemap of this website; and every old address
of former/, which must lead to its page in the new folder, which must answer. It
keeps an issue with what needs attention, and each line says how to fix it:

    python3 -I .github/mkdocs_project.py --watch

This website lives at the root of the address dennis-otto.github.io, which the
websites of the projects share, each in a folder of its own. So the hooks also write
the files that crawlers and security researchers look for at the root of a host
alone: robots.txt with the sitemap of every website of the address,
security.txt (RFC 9116), and llms.txt (https://llmstxt.org/), the map of the
address for AI assistants: a section for every group of the home page with its
projects, each with its website, its first button and the guides of its website,
such as its installation, which the hooks take from its search index, in English
with the German page of each. The home page of the default language gets the
structured data of the address: the name of the website, its owner and the
projects; and the root of the address, not index.html in it, as its canonical
address.

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
its translation, a page of this website in a folder that former names, and a
security.txt whose policy is no page of the website.

The tests of the hooks fake MkDocs and its plugins. So after the real build, the
check docs runs scripts/check-site.sh with the folder of the website, which checks
there what the hooks promise in the files that they alone write or change after the
build, so that a new version of Material or of mkdocs-static-i18n that changes the
order of the plugins or their files fails the check before the website is published:
both copies of security.txt, with what RFC 9116 asks and a policy that is a page of
the website, robots.txt with every sitemap once, llms.txt with every group and
project as https://llmstxt.org/ asks, the sitemaps with the root of the
address, a page at every old address that leads to its page now, the 404 page with
the old folders, the cards of both home pages with their pictures and their old
anchors, the structured data, and the search index with the pages of this website,
their boosts and the entries of the projects:

    python3 -I .github/mkdocs_project.py --site site
"""

from __future__ import annotations

import argparse
import difflib
import gzip
import http.client
import io
import itertools
import json
import logging
import math
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
from pathlib import Path, PurePosixPath
from string import Template
from typing import Any, NamedTuple, TypeVar
from urllib.parse import quote, urljoin, urlsplit
from xml.etree import ElementTree

# The warnings of MkDocs, which mkdocs build --strict counts.
log = logging.getLogger("mkdocs.hooks.project")

# The root of the repository, with projects.toml and the READMEs.
ROOT = Path(__file__).resolve().parents[1]
CATALOG = "projects.toml"
# The README in the first language of the catalog; that of each further language
# that HEADINGS has the words for is README.<code>.md, such as README.de.md.
README = "README.md"
# The command that writes the tables of the READMEs, for the messages.
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
# How the picture of a card loads: those of the first group, which a reader sees
# first, at once, and the first of them before the other pictures of the page, since
# it is its largest paint; the others only as they come into view. Each says it, so
# that lazy() of .github/mkdocs_blueprint.py, which makes every picture of a page
# but its first wait until it comes into view, leaves it as it is.
FIRST = 'loading="eager" fetchpriority="high"'
EAGER = 'loading="eager"'
LAZY = 'loading="lazy"'
# The page from which scripts/project-pictures.sh draws the picture of a card in a
# language after the first, beside a screenshot of the repository of its project in
# that language, where the social preview of the repository makes that of the first.
DRAWING = ".github/card-picture.html"
# The lines of each README between which the table of the projects goes, and the
# headings of its columns in the language of the README; a first language without
# its own takes those of English.
TABLE_START = "<!-- projects:start -->"
TABLE_END = "<!-- projects:end -->"
HEADINGS = {
    "en": ("Project", "What it does", "Works with", "Start", "Website"),
    "de": ("Projekt", "Was es tut", "Funktioniert mit", "Start", "Website"),
}

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
# The Trust page. The guarantees of every project with a repo come in two parts, each
# under a heading of the page itself, so that its links to their anchors hold in the
# source too: the guarantees of TRUST_VALUED, which every project gives alike, take
# the place of the line SHARED_MARKER, each once with its one value, in a list of the
# class TRUST_SHARED, whose values of TRUST_LINKED link the security policy and the
# form for private reports of every project in the place of {}; and the numbers of
# TRUST_NUMBERS take the place of the line TRUST_MARKER, in a table with a row for
# each project, which the text of numbers names, and the note below it. On a phone,
# each row becomes a card, on which the label of every cell, its data-label, stands
# beside its value, so the page never scrolls sideways. The table is in a part of the
# page with the class TRUST that tells the script where the data of the dashboard is,
# as that of the cards does. The script writes the value of every number of TRUST_LIVE
# into the cell of each project, by its repository and the key of its number; without
# the data, the cell of its release links its releases on GitHub, and the others hold
# DASH. The commands that verify the latest release of every project take the place of
# VERIFY_MARKER: they check the attestation of its release, and the provenance of one
# of its files, which the workflow SIGNER of its repository signed.
TRUST_MARKER = "<!-- trust -->"
TRUST_LINE = re.compile(rf"^{re.escape(TRUST_MARKER)}[ \t]*$", re.MULTILINE)
SHARED_MARKER = "<!-- trust-shared -->"
SHARED_LINE = re.compile(rf"^{re.escape(SHARED_MARKER)}[ \t]*$", re.MULTILINE)
VERIFY_MARKER = "<!-- verify -->"
VERIFY_LINE = re.compile(rf"^{re.escape(VERIFY_MARKER)}[ \t]*$", re.MULTILINE)
TRUST = "trust"
TRUST_SHARED = "trust-shared"
TRUST_VALUED = ("tag", "provenance", "immutable", "sbom", "vex", "policy", "report")
TRUST_LINKED = ("policy", "report")
TRUST_NUMBERS = ("release", "coverage", "mutation", "scorecard", "bestpractices")
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

# What a project works with, on the line of its card above its buttons, after the
# label of [requirements]: a text of the catalog, or one with the values of a file of
# its repository, which the build reads at the tag of its latest release and the
# catalog bot on its default branch, from raw.githubusercontent.com, which needs no
# token. The keys of requires that name such a file, the class of the line, and the
# key of config.extra that keeps what every project works with for the build of
# each language.
RAW = "https://raw.githubusercontent.com/{}/{}/{}"
DEFAULT_BRANCH = "HEAD"
REQUIREMENTS = "requirements"
SOURCE_KEYS = ("file", "field", "text")
REQUIRES = "project-requires"
WORKS = "works_with"
# A value of such a file, a version such as 2026.8.0 or 33, which a text of Markdown
# holds as it is.
VERSION = re.compile(r"[0-9][0-9A-Za-z.+-]{0,31}", re.ASCII)
# A place of a value in a text, {} for the one value of a file, or {name} for each
# of several, such as {min}.
PLACEHOLDER = re.compile(r"\{([^{}]*)\}")

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
# The watch of the catalog bot, which asks the live websites every day for what the
# hub depends on after its build. The file that names what docs/javascripts/
# projects.js reads of the data of the dashboard, the schema of repos.json and the
# kind of every field, which tests/projects.test.mjs keeps equal to the script; how
# a day of the data looks; how far ahead the live security.txt must still hold, of
# the VALID that every build gives it, so that a daily build that stopped shows
# within a month; the most names of a sentence of the issue; and the command.
DASHBOARD_FIELDS = ".github/dashboard-fields.json"
DAY = re.compile(r"\d{4}-\d{2}-\d{2}", re.ASCII)
REPOSITORY = re.compile(r"[\w.-]+/[\w.-]+", re.ASCII)
AHEAD = timedelta(days=330)
NAMED = 5
WATCH = "python3 -I .github/mkdocs_project.py --watch"

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
# Its name has no dot before its extension: mkdocs-static-i18n would take a picture
# such as tool.de.webp for the German one of tool.webp, publish it in its place in
# de/ and lead the German pages there, behind the back of the catalog. A picture in
# another language goes into a folder of its own instead, such as
# images/projects/de/.
IMAGE = Form(
    re.compile(r"(?:[a-z0-9_-]+/)*[a-z0-9_-]+\.(?:avif|jpg|png|svg|webp)"),
    "a picture in docs/, such as images/projects/homedarts-for-autodarts.webp",
)
# A picture of the repository of a project that the hub draws into the picture of a
# card in a language after the first, by its path there: a folder or a name never
# starts with a dot, so the path stays in the repository. It is a still picture,
# since Chromium would catch an animation at any frame.
SCREENSHOT = Form(
    re.compile(
        r"(?:[A-Za-z0-9_-][A-Za-z0-9._-]*/)*[A-Za-z0-9_-][A-Za-z0-9._-]*"
        r"\.(?:jpg|png|svg|webp)"
    ),
    "the path of a JPEG, PNG, SVG or WebP of the repository, such as "
    "docs/images/de/card.png",
)
LOGO = Form(
    SCREENSHOT.pattern,
    "the path of a JPEG, PNG, SVG or WebP of the repository, such as "
    "docs/branding/icon.svg",
)
# The color of the light behind the screenshot of a drawn picture.
ACCENT = Form(
    re.compile(r"#[0-9a-f]{6}"),
    "a color of six lowercase hexadecimal digits, such as #14b8a6",
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
# A file of a repository that says what its project works with, by its path there:
# JSON, YAML or XML, by its extension, each with the form of a field in it.
SOURCE = Form(
    re.compile(
        r"(?:[A-Za-z0-9_-][A-Za-z0-9._-]*/)*[A-Za-z0-9_-][A-Za-z0-9._-]*"
        r"\.(?:json|ya?ml|xml)"
    ),
    "the path of a JSON, YAML or XML file of the repository, such as hacs.json or "
    "appinfo/info.xml",
)
YAML_FIELD = Form(
    re.compile(r"[A-Za-z0-9_-]+"),
    "a key at the top of the YAML, with its value on its line, such as "
    "_min_copier_version",
)
FIELD_FORMS = {
    ".json": Form(
        re.compile(r"[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*"),
        "the keys to the value in the JSON, with a dot between two, such as "
        "homeassistant",
    ),
    ".yml": YAML_FIELD,
    ".yaml": YAML_FIELD,
    ".xml": Form(
        re.compile(r"[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*(?:@[A-Za-z0-9_-]+)?"),
        "the path of an element from the root of the XML, with @ and the name of "
        "one of its attributes for that, such as dependencies/nextcloud@min-version",
    ),
}
# The name of a value of several, by which a text places it, such as min for {min}.
FIELD_NAME = Form(
    re.compile(r"[a-z][a-z0-9_]*"),
    "a name of lowercase letters, digits and underscores, such as min",
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
    "requires",
    "group",
    "icon",
    "name",
    "short",
    "tagline",
    "summary",
    "image",
    "alt",
    "drawing",
    "start",
    "docs",
    "former",
    "second",
)
# The keys that only a project with a card, and so with a group, has.
CARD_KEYS = ("image", "alt", "drawing", "second")
# The keys of drawing, which the comments of projects.toml describe.
DRAWING_KEYS = ("screenshot", "logo", "accent")
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
# The keys of [trust], the texts of the guarantees of the Trust page in every
# language, in the order of the page: the label of each of TRUST_VALUED, with its
# value beside it; the name of the table of the numbers, that of the column of the
# projects and the label of each of TRUST_NUMBERS; and the note below them.
TRUST_KEYS = (*TRUST_VALUED, "numbers", "project", *TRUST_NUMBERS, "note")
ROW_KEYS = ("label", "value")


@dataclass(frozen=True)
class Link:
    """A button of a card: its icon, and its label and address in every language."""

    icon: str
    label: dict[str, str]
    url: dict[str, str]


@dataclass(frozen=True)
class Drawing:
    """How the hub draws the picture of a card in a language after the first: the
    screenshot of the repository of its project for every language that it draws,
    its logo there, or None for the icon of its card, and the color of the light
    behind the screenshot."""

    screenshot: dict[str, str]
    logo: str | None
    accent: str


@dataclass(frozen=True)
class Picture:
    """The picture on top of a card: its file in docs/ and what it shows in every
    language, for those who can't see it, and how the hub draws it in the languages
    whose file it draws, if it draws one."""

    src: dict[str, str]
    alt: dict[str, str]
    drawing: Drawing | None = None


def drawn(src: dict[str, str], languages: tuple[str, ...]) -> list[str]:
    """The languages after the first whose picture of src, by language, is a file of
    its own: the hub draws them, where the social preview of the repository makes
    that of the first."""
    first = src[languages[0]]
    return [language for language in languages[1:] if src[language] != first]


@dataclass(frozen=True)
class Source:
    """Where the build reads what a project works with: a file of its repository, the
    field of every value in it by the name of its place in the texts, "" for the one
    of {}, and the text in every language with the place of every value."""

    file: str
    fields: dict[str, str]
    text: dict[str, str]


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
    # What it works with: a text in every language, or the file of its repository
    # that the build reads it from.
    requires: dict[str, str] | Source | None = None
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
    """The texts of the guarantees of the Trust page, each in every language: those
    of texts by their key of TRUST_KEYS, with the label of every guarantee and
    number, and the value that every project shares of each of TRUST_VALUED, by its
    key in values."""

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
    # The texts of the guarantees of the Trust page.
    trust: Trust
    # The icon and the label, in every language with {}, of the line of a card that
    # says what its project works with.
    requirements: Link
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

    def urls(
        self,
        value: object,
        owner: str,
        key: str,
        form: Form = URL,
        kind: str = "address",
    ) -> dict[str, str]:
        """value as an address in every language, or another kind of text of form:
        one for all of them, or one per language, where a language without its own
        takes that of the first."""
        if not isinstance(value, dict):
            return dict.fromkeys(self.languages, self.text(value, owner, key, form))
        self.known_languages(value, owner, key)
        first = self.languages[0]
        if first not in value:
            self.problem(
                owner,
                join(key, first),
                f"is missing; the other languages take it when they have no {kind}",
            )
        own = {
            language: self.text(value[language], owner, join(key, language), form)
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

    def drawing(
        self, table: dict[str, Any], owner: str, languages: list[str]
    ) -> Drawing | None:
        """How the hub draws the pictures of the card of the project table in
        languages, those after the first whose image is a file of its own: its
        drawing, which a project with a repo needs for them, and has for them
        alone."""
        if "repo" not in table or not languages:
            if "drawing" in table:
                self.problem(
                    owner,
                    "drawing",
                    "is for a project with a repo whose image has a file of its own "
                    "in a language after the first, such as image.de"
                    if "repo" in table
                    else "is for a project with a repo",
                )
            return None
        if "drawing" not in table:
            wanted = ", ".join(join("image", language) for language in languages)
            self.problem(
                owner, "drawing", f"is missing, with which the hub draws {wanted}"
            )
            return None
        value = self.table(table["drawing"], owner, "drawing", DRAWING_KEYS)
        if value is None:
            return None
        key = join("drawing", "screenshot")
        shots = value.get("screenshot")
        if isinstance(shots, dict):
            self.known_languages(shots, owner, key)
            for language in shots:
                if language in self.languages and language not in languages:
                    self.problem(
                        owner,
                        join(key, language),
                        "is for a language whose picture the hub doesn't draw; it "
                        "draws only those of " + ", ".join(languages),
                    )
            screenshot = {
                language: self.text(
                    shots.get(language), owner, join(key, language), SCREENSHOT
                )
                for language in languages
            }
        else:
            screenshot = dict.fromkeys(
                languages, self.text(shots, owner, key, SCREENSHOT)
            )
        logo = None
        if "logo" in value:
            logo = self.text(value["logo"], owner, join("drawing", "logo"), LOGO)
        accent = self.text(
            value.get("accent"), owner, join("drawing", "accent"), ACCENT
        )
        return Drawing(screenshot, logo, accent)

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
        """value as the texts of the guarantees of the Trust page, each in every
        language: a text for every key of TRUST_KEYS, and a table with a label and a
        value for each of TRUST_VALUED, whose value holds {} once for those of
        TRUST_LINKED, where the links to every project go."""
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
                for language, text in values[key].items():
                    if key in TRUST_LINKED and text and text.count("{}") != 1:
                        self.problem(
                            "",
                            join(join(name, "value"), language),
                            "must hold {} once, where the links to every project go,"
                            f" not {text!r}",
                        )
        return Trust(texts, values)

    def requirements(self, value: object) -> Link:
        """value as the line of a card that says what its project works with: its
        icon, and its label in every language with {} once, where that goes."""
        line = self.link(value, "", REQUIREMENTS, url=False)
        for language, text in line.label.items():
            if text and text.count("{}") != 1:
                self.problem(
                    "",
                    join(join(REQUIREMENTS, "label"), language),
                    "must hold {} once, where what a project works with goes, not "
                    f"{text!r}",
                )
        return line

    def requires(self, value: object, owner: str) -> dict[str, str] | Source:
        """value as what a project works with: a text in every language, or a table
        with a file of its repository, the field of its value in it, or a table of
        the fields of several by their names, and a text in every language with the
        place of every value."""
        if not isinstance(value, dict):
            self.problem(
                owner,
                "requires",
                "must be a text in every language, such as requires.en, or a file of "
                "the repository with requires.file, requires.field and requires.text",
            )
            return {}
        if not any(key in value for key in SOURCE_KEYS):
            return self.texts(value, owner, "requires")
        self.table(value, owner, "requires", SOURCE_KEYS)
        file = self.text(value.get("file"), owner, "requires.file", SOURCE)
        form = FIELD_FORMS.get(PurePosixPath(file).suffix)
        fields = self.fields(value.get("field"), owner, form)
        text = self.texts(value.get("text"), owner, "requires.text")
        places = sorted(fields)
        if places == [""]:
            wanted = "{} once, where the value goes"
        else:
            wanted = (
                " and ".join(f"{{{name}}}" for name in fields)
                + " once each, where their values go"
            )
        for language, wording in text.items():
            found = sorted(PLACEHOLDER.findall(wording))
            stray = re.search(r"[{}]", PLACEHOLDER.sub("", wording))
            if wording and places and (found != places or stray):
                self.problem(
                    owner,
                    join("requires.text", language),
                    f"must hold {wanted}, not {wording!r}",
                )
        return Source(file, fields, text)

    def fields(self, value: object, owner: str, form: Form | None) -> dict[str, str]:
        """value as the field of the one value of a file of the form of its kind, by
        the name "", or as a table of the field of each of several by its name."""
        key = "requires.field"
        if not isinstance(value, dict):
            return {"": self.text(value, owner, key, form)}
        if not value:
            self.problem(
                owner, key, "must name a field, or a table of fields by their names"
            )
        fields = {}
        for name, field in value.items():
            if not FIELD_NAME.pattern.fullmatch(name):
                self.problem(
                    owner,
                    join(key, name),
                    f"must be named with {FIELD_NAME.description}, not {name!r}",
                )
                continue
            fields[name] = self.text(field, owner, join(key, name), form)
        return fields

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
        repo = spdx = platform = bestpractices = asset = requires = None
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
            if "requires" in table:
                requires = self.requires(table["requires"], owner)
        else:
            for key in ("license", "platform", "bestpractices", "asset", "requires"):
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
            src = self.urls(table.get("image"), owner, "image", IMAGE, "picture")
            # The languages whose picture the hub draws, where the social preview of
            # the repository makes that of the first.
            languages = drawn(src, self.languages)
            if "repo" in table:
                # scripts/project-pictures.sh makes the pictures of a project with a
                # repo, always as WebPs; a picture of another kind is one made by
                # hand.
                named = isinstance(table.get("image"), dict)
                for language in (self.languages[0], *languages):
                    file = src[language]
                    if file and not file.endswith(".webp"):
                        self.problem(
                            owner,
                            join("image", language) if named else "image",
                            "must be a WebP for a project with a repo, which "
                            f"scripts/project-pictures.sh makes, not {file!r}",
                        )
            drawing = self.drawing(table, owner, languages)
            image = Picture(src, self.texts(table.get("alt"), owner, "alt"), drawing)
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
            requires=requires,
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
        (
            "languages",
            "documentation",
            "facts",
            TRUST,
            REQUIREMENTS,
            "group",
            "project",
        ),
    )
    documentation = reader.link(
        data.get("documentation"), "", "documentation", url=False
    )
    facts = reader.facts(data.get("facts"))
    trust = reader.trust(data.get(TRUST))
    requirements = reader.requirements(data.get(REQUIREMENTS))
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
    return Catalog(tuple(languages), groups, projects, facts, trust, requirements)


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


def picture(image: Picture, language: str, loading: str = LAZY) -> str:
    """The Markdown of the picture on top of a card, in language: with its size, so
    that the page keeps its place before it loads, loading as FIRST, EAGER or LAZY
    say, and without the enlarging of the lightbox, since the picture is a
    preview."""
    width, height = PICTURE
    return (
        f"![{bracketed(image.alt[language])}]({image.src[language]})"
        f'{{ width="{width}" height="{height}" {loading} .off-glb }}'
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


def requirement(
    catalog: Catalog, project: Project, language: str, works: dict[str, dict[str, str]]
) -> str:
    """The Markdown of the line of the card of project that says what it works with,
    in language: the icon and the label of the requirements of catalog, with what
    works has for it in place of {}, or nothing when works has nothing for it."""
    texts = works.get(project.slug)
    if not texts:
        return ""
    line = catalog.requirements
    label = line.label[language].replace("{}", texts[language])
    return f'<p class="{REQUIRES}" markdown>:{line.icon}: {label}</p>'


def card(
    project: Project,
    language: str,
    second: Link | None,
    live: str = "",
    requires: str = "",
    loading: str = LAZY,
) -> str:
    """The Markdown of the card of project: its picture, which loads as loading
    says, its heading with the slug as its anchor, with an anchor of its own for
    every folder of former, so that an address of the home page that led to the card
    under an old slug still does, and with a link to its website, its summary, live,
    the HTML of its live facts if it has them, requires, the line that says what it
    works with if it has one, right above its first button and second, the button
    that Catalog.second gives it."""
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
        parts.append(picture(project.picture, language, loading))
    parts += [heading, project.summary[language]]
    parts += [part for part in (live, requires) if part]
    parts += ["\n".join(buttons), "</div>"]
    return "\n\n".join(parts)


def section(
    catalog: Catalog,
    group: Group,
    language: str,
    levels: dict[int, str] | None = None,
    works: dict[str, dict[str, str]] | None = None,
    *,
    first: bool = False,
) -> str:
    """The Markdown of group: its heading with its id as its anchor, the grid with
    the card of every project in it, each with a repo with its live facts and the
    level of its OpenSSF Best Practices of levels, and what it works with of works,
    by its slug, and its note below the cards. The pictures of the first group of
    the page load at once, the first before the others; those of the other groups
    as they come into view."""
    loading = [FIRST, EAGER] if first else [LAZY]
    members = catalog.members(group)
    parts = [
        f"## {group.heading[language]} {{ #{group.id} }}",
        '<div class="grid" markdown>',
        *(
            card(
                project,
                language,
                catalog.second(project),
                facts(catalog, project, language, levels or {}) if project.repo else "",
                requirement(catalog, project, language, works or {}),
                loading[min(number, len(loading) - 1)],
            )
            for number, project in enumerate(members)
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
    catalog: Catalog,
    language: str,
    levels: dict[int, str] | None = None,
    works: dict[str, dict[str, str]] | None = None,
) -> str:
    """The Markdown of every group with its cards, in language, in a part of the page
    with its own anchor. The part tells the script of the live facts where their data
    is, the language of the page and the texts of the facts in it; levels holds the
    level of the OpenSSF Best Practices of each project by its number, and works what
    each works with by its slug."""
    attributes = script_data(catalog, language)
    return "\n\n".join(
        [
            f'<div class="projects" id="{PROJECTS}"{attributes} markdown>',
            *(
                section(catalog, group, language, levels, works, first=number == 0)
                for number, group in enumerate(catalog.groups)
            ),
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


class RequirementError(Exception):
    """A file of a repository doesn't hold what its project reads from it as what it
    works with: its message says what is wrong, after the name of the file."""


def json_value(data: object, field: str) -> str | None:
    """The value at field of data, a JSON document, by its keys with a dot between
    two: a text as it is, any other value as JSON, or None when it has none."""
    for key in field.split("."):
        if not isinstance(data, dict) or key not in data:
            return None
        data = data[key]
    return data if isinstance(data, str) else json.dumps(data)


def yaml_value(text: str, field: str) -> str | None:
    """The value of field, a key at the top of text, a YAML document, on the line of
    the key: plain or between quotes, without a comment after it, or None when the
    document has no such line. The standard library reads no YAML, and a file such
    as copier.yml may hold tags that no reader of YAML knows."""
    found = re.search(
        rf"^{re.escape(field)}[ \t]*:[ \t]+"
        r"(?:\"([^\"\n]*)\"|'([^'\n]*)'|([^\s\"'#][^\n#]*?))[ \t]*(?:#[^\n]*)?$",
        "\n".join(text.splitlines()),
        re.MULTILINE,
    )
    if found is None:
        return None
    return next(value for value in found.groups() if value is not None)


def xml_value(root: ElementTree.Element, field: str) -> str | None:
    """The value at field of root, the root of an XML document: the attribute after
    @ of the element at the path before it, or the text of that element without
    one, or None when the document has none."""
    path, _, attribute = field.partition("@")
    element = root.find(path)
    if element is None:
        return None
    value = element.get(attribute) if attribute else element.text
    return None if value is None else value.strip()


def values_in(source: Source, content: bytes) -> dict[str, str]:
    """The value of every field of source in content, its file, by its name: each a
    version, or RequirementError."""
    kind = PurePosixPath(source.file).suffix
    try:
        if kind == ".json":
            data = json.loads(content)
            found = {name: json_value(data, at) for name, at in source.fields.items()}
        elif kind == ".xml":
            # The files of the projects' own releases, read by expat, which expands no
            # external entity and stops an expansion that grows out of proportion.
            root = ElementTree.fromstring(content)
            found = {name: xml_value(root, at) for name, at in source.fields.items()}
        else:
            text = content.decode("utf-8-sig")
            found = {name: yaml_value(text, at) for name, at in source.fields.items()}
    # A broken JSON document, or a file that isn't UTF-8, is a ValueError, and a
    # broken XML document a SyntaxError.
    except (ValueError, SyntaxError) as error:
        raise RequirementError(f"can't be read: {error}") from error
    for name, value in found.items():
        field = source.fields[name]
        if value is None:
            raise RequirementError(f"has no field {field}")
        if not VERSION.fullmatch(value):
            raise RequirementError(f"holds {value!r} in {field}, which is no version")
    return {name: str(value) for name, value in found.items()}


def filled(text: str, values: dict[str, str]) -> str:
    """text with the value of values in the place of each, {} for that of the name
    ""."""
    return PLACEHOLDER.sub(lambda place: values[place[1]], text)


def requirements(
    catalog: Catalog, notes: dict[str, tuple[Release, ...]]
) -> dict[str, dict[str, str]]:
    """What every project of the catalog with requires works with, by its slug, in
    every language: its text, or the text of its source with the values that the
    build reads from its file at the tag of the latest release of notes. A project
    whose release or file can't be read, or whose file lacks a value, has none, which
    the log says without a warning, so that the strict build passes."""
    works = {
        project.slug: project.requires
        for project in catalog.projects
        if isinstance(project.requires, dict)
    }
    sources = [
        (project, project.requires)
        for project in catalog.projects
        if isinstance(project.requires, Source)
    ]
    if not sources:
        return works

    def read(pair: tuple[Project, Source]) -> dict[str, str] | None:
        project, source = pair
        releases = notes.get(str(project.repo))
        why = "The card of %s leaves out what it works with until the next build: %s"
        if not releases:
            log.info(why, project.slug, f"the build has no release of {project.repo}")
            return None
        tag = releases[0].tag
        try:
            values = values_in(
                source, download(RAW.format(project.repo, tag, source.file))
            )
        except SearchError as error:
            log.info(why, project.slug, error)
            return None
        except RequirementError as error:
            where = f"{source.file} of {project.repo} at {tag}"
            log.info(why, project.slug, f"{where} {error}")
            return None
        return {
            language: filled(text, values) for language, text in source.text.items()
        }

    with ThreadPoolExecutor(max_workers=len(sources)) as pool:
        found = list(pool.map(read, sources))
    for (project, _), texts in zip(sources, found, strict=True):
        if texts is not None:
            works[project.slug] = texts
    return works


def requirements_of(config: Any) -> dict[str, dict[str, str]]:
    """What every project works with, of requirements, read once for the build of
    every language, with the releases of notes_of when a project reads it from a
    file."""
    if WORKS not in config.extra:
        catalog: Catalog = config.extra["catalog"]
        read = any(isinstance(project.requires, Source) for project in catalog.projects)
        config.extra[WORKS] = requirements(catalog, notes_of(config) if read else {})
    return config.extra[WORKS]


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
    script tells as the time since, the headline of its notes, and the tags of every
    release of the project that the build read, which the script never puts in its
    place, also when one came out the same day. Its count, the
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
    """The HTML of the cell of project, which has a repo, in the column key of
    TRUST_NUMBERS of the table of the Trust page, with the label of its column, which
    a phone shows beside its value: the place of a value of the script for a number
    of TRUST_LIVE, or the level of its OpenSSF Best Practices of levels, which links
    its page at bestpractices.dev."""
    label = escape(catalog.trust.texts[key][language])
    repo = escape(str(project.repo))
    if key in TRUST_LIVE:
        content = DASH
        if key == "release":
            content = f'<a href="{GITHUB}{repo}/releases/latest">GitHub</a>'
        return (
            f'<td data-label="{label}" data-repo="{repo}" data-fact="{key}">'
            f"{content}</td>"
        )
    level = levels.get(project.bestpractices or 0)
    content = DASH
    if level is not None:
        page = BEST_PRACTICES.format(project.bestpractices)
        content = f'<a href="{page}">{escape(catalog.facts[level][language])}</a>'
    return f'<td data-label="{label}">{content}</td>'


def with_repo(catalog: Catalog) -> list[Project]:
    """The projects of catalog that the Trust page shows: those with a repo."""
    return [project for project in catalog.projects if project.repo is not None]


def shared_guarantees(catalog: Catalog, language: str) -> str:
    """The HTML of the guarantees that every project with a repo gives alike, in
    language: a list with each of TRUST_VALUED once, its label and its one value,
    in which those of TRUST_LINKED link the security policy and the form for private
    reports of every project, each under its short name, in the place of {}."""
    targets = {
        "policy": "{}/blob/main/SECURITY.md",
        "report": "{}/security/advisories/new",
    }
    items = []
    for key in TRUST_VALUED:
        label = escape(catalog.trust.texts[key][language])
        value = escape(catalog.trust.values[key][language])
        if key in TRUST_LINKED:
            links = ", ".join(
                f'<a href="{GITHUB}{targets[key].format(escape(str(project.repo)))}">'
                f"{escape(short_name(project, language))}</a>"
                for project in with_repo(catalog)
            )
            value = value.replace("{}", links)
        items.append(f"<div><dt>{label}</dt><dd>{value}</dd></div>")
    return "\n".join([f'<dl class="{TRUST_SHARED}">', *items, "</dl>"])


def numbers_table(
    catalog: Catalog, language: str, levels: dict[int, str] | None = None
) -> str:
    """The HTML of the table of the numbers of every project with a repo, in
    language, which the text of numbers names: a row for each project, under its
    short name, which links its website, and a column for each of TRUST_NUMBERS. Its part of the page tells the script where
    the data of the dashboard is and the language of the page; levels holds the
    level of the OpenSSF Best Practices of each project by its number."""
    texts = {key: text[language] for key, text in catalog.trust.texts.items()}
    data = {"facts": FEED, "history": HISTORY, "locale": language}
    attributes = "".join(f' data-{key}="{escape(text)}"' for key, text in data.items())
    head = "".join(
        f'<th scope="col">{escape(texts[key])}</th>' for key in ("project", *TRUST_NUMBERS)
    )
    rows = [
        f'<tr><th scope="row"><a href="{escape(project.website[language])}">'
        f"{escape(short_name(project, language))}</a></th>"
        + "".join(
            trust_cell(catalog, project, key, language, levels or {})
            for key in TRUST_NUMBERS
        )
        + "</tr>"
        for project in with_repo(catalog)
    ]
    return "\n".join(
        [
            f'<div class="{TRUST}"{attributes}>',
            f'<table aria-label="{escape(texts["numbers"])}">',
            f"<thead><tr>{head}</tr></thead>",
            "<tbody>",
            *rows,
            "</tbody>",
            "</table>",
            "</div>",
        ]
    )


def guarantees(
    catalog: Catalog, language: str, levels: dict[int, str] | None = None
) -> str:
    """The Markdown of the numbers of the Trust page in language, which take the
    place of its line TRUST_MARKER, under the heading of the page: the table of the
    numbers of each project, with the note below it; levels holds the level of the
    OpenSSF Best Practices of each project by its number."""
    note = catalog.trust.texts["note"][language]
    return f"{numbers_table(catalog, language, levels)}\n\n{note}"


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


def links(texts: dict[str, str], urls: dict[str, str], language: str) -> str:
    """A link to every address of urls once, that of language first and then in the
    order of the languages, each with the text of its language."""
    first: dict[str, str] = {}
    for code in sorted(urls, key=lambda other: other != language):
        first.setdefault(urls[code], code)
    return " · ".join(f"[{cell(texts[code])}]({url})" for url, code in first.items())


def works_with(project: Project, language: str) -> str:
    """The cell of the table of the README that says what project works with: its
    text, or for one that the build reads from a file, its platform and a link to the
    file on the default branch, which the link check checks too, or a dash."""
    if isinstance(project.requires, Source):
        file = project.requires.file
        url = f"{GITHUB}{project.repo}/blob/{DEFAULT_BRANCH}/{file}"
        return f"{cell(str(project.platform))} ([{file}]({url}))"
    if project.requires:
        return cell(project.requires[language])
    return DASH


def readmes(catalog: Catalog) -> dict[str, str]:
    """The README of every language that has one, by its language: README.md in the
    first language of the catalog, and README.<code>.md in each further one that
    HEADINGS has the words for."""
    return {catalog.default: README} | {
        language: f"README.{language}.md"
        for language in catalog.languages[1:]
        if language in HEADINGS
    }


def table(catalog: Catalog, language: str) -> str:
    """The table of the README in language: every project with its repository, what
    it does and what it works with in language, its first button and its website,
    with the address of every language, that of language first. The link check of
    the Markdown, which reads no TOML, so checks every address of projects.toml."""
    headings = HEADINGS.get(language, HEADINGS["en"])
    rows = [
        f"| {' | '.join(headings)} |",
        f"|{' --- |' * len(headings)}",
    ]
    for project in catalog.projects:
        name = cell(project.name[language])
        if project.repo is not None:
            repository = project.repo.partition("/")[2]
            name = f"[{repository}](https://github.com/{project.repo})"
        start = links(project.start.label, project.start.url, language)
        website = "—"
        if project.docs is not None:
            shown = {
                code: url.removeprefix("https://").rstrip("/")
                for code, url in project.docs.url.items()
            }
            website = links(shown, project.docs.url, language)
        tagline = cell(project.tagline[language])
        works = works_with(project, language)
        rows.append(f"| {name} | {tagline} | {works} | {start} | {website} |")
    return "\n".join(rows)


def readme(text: str, catalog: Catalog, language: str) -> str:
    """text, that of the README in language, with the table of catalog in language
    between its markers."""
    start = text.find(TABLE_START)
    end = text.find(TABLE_END)
    if start < 0 or end < start:
        raise CatalogError(
            f"{readmes(catalog)[language]} needs the lines {TABLE_START} and "
            f"{TABLE_END}, in this order; the table of the projects goes between them."
        )
    head = text[: start + len(TABLE_START)]
    return f"{head}\n\n{table(catalog, language)}\n\n{text[end:]}"


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
            content = download(url)
            docs = documents(content, url)
        except SearchError as error:
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
    config.extra[LLMS] = config.site_description
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
    """Put the cards of the projects, each with what it works with, the table of
    their guarantees, the commands that verify their releases, their releases and
    What's new in place of their markers, in the language of the page's file, which
    the i18n plugin sets: a page that a further language shows in the default one
    gets them in the default one too."""
    catalog: Catalog = config.extra["catalog"]
    language = page_language(catalog, page)
    markdown = MARKER_LINE.sub(
        lambda _: cards(
            catalog, language, levels_of(config), requirements_of(config)
        ),
        markdown,
    )
    markdown = SHARED_LINE.sub(
        lambda _: shared_guarantees(catalog, language), markdown
    )
    markdown = TRUST_LINE.sub(
        lambda _: guarantees(catalog, language, levels_of(config)), markdown
    )
    markdown = VERIFY_LINE.sub(lambda _: verification(catalog, language), markdown)
    markdown = NOTES_LINE.sub(
        lambda _: release_history(catalog, language, notes_of(config)), markdown
    )
    return NEWS_LINE.sub(lambda _: news(catalog, language, notes_of(config)), markdown)


def on_page_content(html: str, page: Any, config: Any, files: Any) -> str:
    """Put the notes of every release of the Releases page in place of their
    placeholders, in the HTML that MkDocs has made of the Markdown of the page, so
    that the notes pass through no extension of Markdown. They are in
    NOTES_LANGUAGE on every page, and the search index of each language holds them
    from its own page."""
    if NOTES_PLACE.search(html) is None:
        return html
    attributes = f' lang="{NOTES_LANGUAGE}"'
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
    head = structured_data(
        catalog, config.site_url, config.site_name, requirements_of(config)
    )
    return output.replace("</head>", f"{head}</head>", 1)


def on_post_build(config: Any) -> None:
    """Write robots.txt, security.txt and llms.txt at the root of the address and a
    page at every old address of a website that moved, lead the sitemaps to its root
    for the home page of the default language, and add the project websites to the
    search index.

    The i18n plugin builds every further language into the same folder after the
    default one, and each build writes the same files again. It writes the search
    index for every language last, so this hook runs after it, and the index of
    every project is downloaded once. llms.txt takes the guides of every project
    from those indexes, and its summary, the description of the website in the
    default language, from on_config: the i18n plugin builds every further language,
    with its own description, before this hook runs for the default one.
    """
    catalog: Catalog = config.extra["catalog"]
    site = Path(config.site_dir)
    # A website without the search plugin has no index to add to.
    if (site / SEARCH_INDEX).is_file():
        if SEARCH not in config.extra:
            config.extra[SEARCH] = project_search(catalog, config.site_url)
        search: ProjectSearch = config.extra[SEARCH]
        add_to_search(site, search.folders, search.docs)
    found = config.extra[SEARCH].guides if SEARCH in config.extra else {}
    files = dict.fromkeys(
        SECURITY_TXT, security_txt(catalog, config.site_url, build_date())
    )
    files[ROBOTS] = robots(catalog, config.site_url)
    files[LLMS_TXT] = llms_txt(catalog, config.site_url, config.extra[LLMS], found)
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


# The check of the built website, which scripts/check-site.sh runs in the check docs.

# What the annotations of the CI call a finding of the check.
PROMISES = "What the hooks of the hub promise"
NOT_FOUND = "404.html"
LOCATION = re.compile(r"<loc>\s*([^<]*?)\s*</loc>")
# The id of the element of the 404 page with the data of its script, the old folders
# with their new addresses and the projects, as overrides/404.html writes them.
NOT_FOUND_DATA = "not-found-data"
# The schemes of the URIs that a Contact of security.txt may have (RFC 9116, 2.5.3).
CONTACTS = ("https://", "mailto:", "tel:")
JSON_LD = "application/ld+json"
# A link of llms.txt, and an item of a list of links, which is every line of its
# sections, as https://llmstxt.org/ asks: a name and an address, and after them
# with a colon what the page is about.
LLMS_LINK = re.compile(r"\[([^\[\]\n]+)\]\(([^()\s]+)\)")
LLMS_ITEM = re.compile(r"(?:  )*- \[[^\[\]\n]+\]\([^()\s]+\)(?:: .+)?")
# The file of the hooks, which the fix of a finding names.
HOOKS = ".github/mkdocs_project.py"


@dataclass(frozen=True)
class Finding:
    """A promise of the hooks that the built website breaks: the path of the file in
    the folder of the website, and what is wrong with it, with the fix."""

    path: str
    message: str


class Built(HTMLParser):
    """What the check reads of a built page: the id of every element, its cards, the
    address of every picture and of those that load only as they come into view, its
    canonical address, its refresh, every script with its type, and the text of
    every script with an id by its id."""

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
        self.script: tuple[str, str, list[str]] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {name: value or "" for name, value in attrs}
        if "id" in values:
            self.ids.add(values["id"])
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


def expiry(value: str, now: datetime) -> list[str]:
    """What value, the Expires of security.txt, breaks at the moment now: it must be
    a time of RFC 3339 after now, and less than a year after it."""
    try:
        moment: datetime | None = datetime.fromisoformat(value)
    except ValueError:
        moment = None
    if moment is None or moment.tzinfo is None:
        return [
            f"names Expires: {value}, which is no time of RFC 3339 with its zone, "
            f"such as 2027-10-24T00:00:00Z: security_txt() of {HOOKS} writes one"
        ]
    if moment <= now:
        return [
            f"expired at {value}: security_txt() of {HOOKS} writes the midnight a "
            "year after the day of the build, so build the website again, with no "
            "SOURCE_DATE_EPOCH or one of today"
        ]
    if moment - now > VALID:
        return [
            f"expires at {value}, more than {VALID.days} days from now, where RFC "
            f"9116 recommends less than a year: keep VALID of {HOOKS} at "
            f"{VALID.days} days or fewer"
        ]
    return []


def security_fields(site: Path, name: str, text: str, now: datetime) -> list[Finding]:
    """What text, the security.txt at name of the website in site, breaks of RFC 9116
    and of what security_txt promises at the moment now."""
    values = text_fields(text)
    messages: list[str] = []
    contacts = values.get("contact", [])
    if not contacts:
        messages.append(
            f"has no Contact, which RFC 9116 requires: security_txt() of {HOOKS} "
            "writes CONTACT"
        )
    messages += [
        f"names Contact: {contact}, which is no https://, mailto: or tel: address of "
        f"RFC 9116: set CONTACT of {HOOKS} to the form for private reports"
        for contact in contacts
        if not contact.startswith(CONTACTS)
    ]
    expires = values.get("expires", [])
    if len(expires) == 1:
        messages += expiry(expires[0], now)
    else:
        messages.append(
            f"has {len(expires)} Expires, where RFC 9116 asks for exactly one: "
            f"security_txt() of {HOOKS} writes one"
        )
    canonical = values.get("canonical", [])
    messages += [
        f"names no Canonical: {urljoin(SITE, path)}, the address of its copy at "
        f"{path}: security_txt() of {HOOKS} names every path of SECURITY_TXT"
        for path in SECURITY_TXT
        if urljoin(SITE, path) not in canonical
    ]
    policies = values.get("policy", [])
    if not policies:
        messages.append(
            f"has no Policy, the security page of the address: security_txt() of "
            f"{HOOKS} names POLICY"
        )
    for policy in policies:
        page = page_at(site, policy)
        if page is None or not page.is_file():
            messages.append(
                f"names Policy: {policy}, which is no page of the website: keep "
                f"docs/security.md, or change POLICY of {HOOKS}"
            )
    return [Finding(name, message) for message in messages]


def security_findings(site: Path, now: datetime) -> list[Finding]:
    """What both copies of security.txt in the website in site break: they are the
    same, and keep RFC 9116 and what security_txt promises at the moment now."""
    findings: list[Finding] = []
    texts: dict[str, str] = {}
    for name in SECURITY_TXT:
        path = site / name
        if path.is_file():
            texts[name] = path.read_text(encoding="utf-8", errors="replace")
        else:
            findings.append(
                Finding(
                    name,
                    f"is missing: on_post_build of {HOOKS} writes it after the build, "
                    f"so check that hooks of mkdocs.yml names {HOOKS}",
                )
            )
    if len(set(texts.values())) > 1:
        first, second = SECURITY_TXT
        findings.append(
            Finding(
                first,
                f"differs from {second}: on_post_build of {HOOKS} writes the same "
                "text into both, so remove what writes one of them after it, such as "
                "a file in docs/ or another plugin",
            )
        )
    # Each text once, under the first path that has it.
    distinct = {text: name for name, text in reversed(texts.items())}
    for text, name in reversed(distinct.items()):
        findings += security_fields(site, name, text, now)
    return findings


def robots_findings(site: Path, catalog: Catalog) -> list[Finding]:
    """What robots.txt of the website in site breaks: it names the sitemap of this
    website and of every project website at the address once."""
    path = site / ROBOTS
    if not path.is_file():
        return [
            Finding(
                ROBOTS,
                f"is missing: on_post_build of {HOOKS} writes it after the build, so "
                f"check that hooks of mkdocs.yml names {HOOKS}",
            )
        ]
    named = text_fields(path.read_text(encoding="utf-8", errors="replace")).get(
        "sitemap", []
    )
    findings: list[Finding] = []
    for url in sitemaps(catalog, SITE):
        count = named.count(url)
        if count == 0:
            findings.append(
                Finding(
                    ROBOTS,
                    f"names no Sitemap: {url}: robots() of {HOOKS} names the sitemap "
                    f"of this website and of every project of {CATALOG} whose docs "
                    f"are at {SITE}",
                )
            )
        elif count > 1:
            findings.append(
                Finding(
                    ROBOTS,
                    f"names Sitemap: {url} {count} times: robots() of {HOOKS} names "
                    "every sitemap once",
                )
            )
    return findings


def llms_findings(site: Path, catalog: Catalog) -> list[Finding]:
    """What llms.txt of the website in site breaks: as https://llmstxt.org/ asks, it
    starts with the title of the owner, and its sections hold lists of links alone;
    it has a section for every group of the catalog, links the website and the
    first button of every project, every page of this website that it links is in
    the website, and it leads to no decision record."""
    path = site / LLMS_TXT
    if not path.is_file():
        return [
            Finding(
                LLMS_TXT,
                f"is missing: on_post_build of {HOOKS} writes it after the build, so "
                f"check that hooks of mkdocs.yml names {HOOKS}",
            )
        ]
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    messages: list[str] = []
    if not lines or lines[0] != f"# {OWNER}":
        messages.append(
            f"doesn't start with the title # {OWNER}, which https://llmstxt.org/ "
            f"asks for: llms_txt() of {HOOKS} writes it on the first line"
        )
    sections = list(
        itertools.dropwhile(lambda line: not line.startswith("## "), lines)
    )
    strays = [
        line
        for line in sections
        if line and not line.startswith("## ") and not LLMS_ITEM.fullmatch(line)
    ]
    if strays:
        messages.append(
            f"has {len(strays)} line(s) in its sections that are no item of a list "
            f"with a link, such as {strays[0]!r}, where https://llmstxt.org/ asks "
            f"for lists of links alone: llms_item() of {HOOKS} writes each item"
        )
    headings = {line[3:] for line in sections if line.startswith("## ")}
    for group in catalog.groups:
        heading = one_line(group.heading[catalog.default])
        if heading not in headings:
            messages.append(
                f"has no section ## {heading}: llms_txt() of {HOOKS} writes one for "
                f"every group of {CATALOG}"
            )
    urls = [url for _, url in LLMS_LINK.findall(text)]
    for project in catalog.projects:
        # A project without a group has no card of its own, so no first button.
        carded = project.group is not None
        wanted = (project.website[catalog.default],) + (
            (project.start.url[catalog.default],) if carded else ()
        )
        for url in dict.fromkeys(wanted):
            if url not in urls:
                messages.append(
                    f"doesn't link {url} of {project.slug}: llms_txt() of {HOOKS} "
                    f"lists every project of {CATALOG} with its website"
                    + (" and the first button of its card" if carded else "")
                )
    folders = tuple(f"{SITE}{website.folder}" for website in websites(catalog, SITE))
    missing = [
        url
        for url in urls
        if (page := page_at(site, url)) is not None
        and not url.startswith(folders)
        and not page.is_file()
    ]
    if missing:
        messages.append(
            f"links {len(missing)} page(s) of this website that it lacks, such as "
            f"{missing[0]}: change llms_txt() of {HOOKS}, or keep the page"
        )
    records = [url for url in urls if DECISIONS in urlsplit(url).path.split("/")]
    if records:
        messages.append(
            f"links {len(records)} decision record(s), such as {records[0]}, which "
            f"are for maintainers: guides() of {HOOKS} takes the pages of "
            "START_PAGES alone"
        )
    return [Finding(LLMS_TXT, message) for message in messages]


def sitemap_findings(site: Path) -> list[Finding]:
    """What the sitemaps of the website in site break: none names the home page of
    the default language as index.html in place of the root of the address."""
    home = home_address(SITE)
    texts = {
        path.relative_to(site).as_posix(): path.read_text(
            encoding="utf-8", errors="replace"
        )
        for path in sorted(site.rglob(SITEMAP))
    }
    packed = site / f"{SITEMAP}.gz"
    if packed.is_file():
        texts[packed.name] = gzip.decompress(packed.read_bytes()).decode(
            "utf-8", errors="replace"
        )
    return [
        Finding(
            name,
            f"names {urljoin(SITE, HOME)} in place of {SITE}, the canonical address "
            f"of the home page: sitemaps_at_root() of {HOOKS} leads it to the root "
            "after the build",
        )
        for name, text in texts.items()
        if home.search(text)
    ]


def moved_findings(site: Path, catalog: Catalog) -> list[Finding]:
    """What the pages at the old addresses in the website in site break: every page
    of former/<folder>.txt is there, and leads to the same page in the folder of the
    website now."""
    moves = catalog.moves()
    findings: list[Finding] = []
    for folder, pages in catalog.former_pages.items():
        for page in pages:
            name = f"{folder}/{page}"
            target = moved_to(moves[folder], page)
            found = built(site, name)
            if found is None:
                findings.append(
                    Finding(
                        name,
                        f"is missing, an old address that {FORMER}/{folder}.txt lists: "
                        f"on_post_build of {HOOKS} writes a page there that leads to "
                        f"{target}",
                    )
                )
            elif found.canonical != [target] or found.refresh != [f"0; url={target}"]:
                findings.append(
                    Finding(
                        name,
                        f"doesn't lead to {target}, the same page in the folder of the "
                        "website now, with its canonical address and its refresh: "
                        f"moved_page() of {HOOKS} writes both, so remove what writes "
                        "the page after it, such as a file in docs/",
                    )
                )
    return findings


def not_found_findings(site: Path, catalog: Catalog) -> list[Finding]:
    """What the 404 page of the website in site breaks: its script leads every old
    folder of the catalog to the folder of its website now, with the moves of the JSON
    of its element #not-found-data."""
    page = built(site, NOT_FOUND)
    if page is None:
        return [
            Finding(
                NOT_FOUND,
                "is missing: overrides/404.html is the page of every address that "
                "leads nowhere, and theme.custom_dir of mkdocs.yml names overrides",
            )
        ]
    try:
        data = json.loads(page.named.get(NOT_FOUND_DATA, "{}"))
    except ValueError:
        data = None
    moves = data.get("moves") if isinstance(data, dict) else None
    wanted = catalog.moves()
    # A page without the map leads no old folder, which is right without one.
    if (moves or {}) == wanted:
        return []
    if wanted:
        named = ", ".join(f"/{folder}/ to {url}" for folder, url in wanted.items())
        problem = f"doesn't lead {named}, as former of {CATALOG} asks"
    else:
        problem = f"leads old folders that former of {CATALOG} doesn't name"
    return [
        Finding(
            NOT_FOUND,
            f"{problem}: its script needs catalog.moves() as the moves of the JSON "
            f"of #{NOT_FOUND_DATA}, as overrides/404.html writes them",
        )
    ]


def listed_projects(page: Built) -> list[str] | None:
    """The @id of every project that the JSON-LD of page lists, or None when the page
    has no JSON-LD with a list of the projects, or more than one."""
    blocks = [text for kind, text in page.scripts if kind == JSON_LD]
    if len(blocks) != 1:
        return None
    try:
        graph = json.loads(blocks[0])["@graph"]
        projects = next(node for node in graph if node["@type"] == "ItemList")
        return [item["item"]["@id"] for item in projects["itemListElement"]]
    except (KeyError, TypeError, ValueError, StopIteration):
        return None


def home_findings(site: Path, catalog: Catalog) -> list[Finding]:
    """What the home pages of the website in site break: each has the card of every
    project with a group, with its picture in the language of the page, which loads
    at once in the first group, and the anchors of its old folders, and that of the
    default language the JSON-LD with every project with a repo."""
    carded = [project for group in catalog.groups for project in catalog.members(group)]
    # The group that a reader sees as the page opens; a catalog has one at least.
    first = catalog.groups[0].id
    # Every card has its picture, which the type of a project leaves open.
    pictured = [
        (project, project.picture) for project in carded if project.picture is not None
    ]
    software = [
        f"{SITE}#{project.slug}"
        for project in catalog.projects
        if project.repo is not None
    ]
    findings: list[Finding] = []
    # Each picture once, which every home page shows.
    missing: dict[str, Finding] = {}
    for language in catalog.languages:
        name = HOME if language == catalog.default else f"{language}/{HOME}"
        page = built(site, name)
        if page is None:
            findings.append(
                Finding(
                    name,
                    f"is missing, the home page in {language}: the i18n plugin of "
                    "mkdocs.yml builds it from docs/index.md and its translations",
                )
            )
            continue
        messages: list[str] = []
        if page.cards != len(carded):
            messages.append(
                f"has {page.cards} cards, not one for each of the {len(carded)} "
                f"projects with a group of {CATALOG}: cards() of {HOOKS} writes them "
                f"in place of {MARKER}"
            )
        pictures, lazy = (
            {urljoin(f"{SITE}{name}", src).removeprefix(SITE) for src in sources}
            for sources in (page.pictures, page.lazy)
        )
        for project in carded:
            if project.slug not in page.ids:
                messages.append(
                    f"has no card of {project.slug}, whose heading has the anchor "
                    f"#{project.slug}: card() of {HOOKS} writes one for every project "
                    f"with a group of {CATALOG}"
                )
            messages += [
                f"lacks the anchor #{folder}, where the card of {project.slug} was "
                f"before, as former of {CATALOG} names it: card() of {HOOKS} keeps it "
                "in the heading of the card"
                for folder in project.former
                if folder not in page.ids
            ]
        for project, image in pictured:
            src = image.src[language]
            if src not in pictures:
                messages.append(
                    f"shows no {src}, the picture of the card of {project.slug} in "
                    f"{language}: card() of {HOOKS} puts the image of {CATALOG} in "
                    "the language of the page on top of it"
                )
                continue
            if project.group == first and src in lazy:
                messages.append(
                    f"loads {src}, the picture of the card of {project.slug}, only as "
                    "it comes into view, though its group is in view as the page "
                    f"opens: section() of {HOOKS} gives the pictures of the first "
                    f"group {EAGER}, which lazy() of .github/mkdocs_blueprint.py "
                    "leaves as it is"
                )
            if not (site / src).is_file():
                missing.setdefault(
                    src,
                    Finding(
                        src,
                        f"is missing, the picture of the card of {project.slug}: make "
                        "it with bash scripts/project-pictures.sh, or fix image of "
                        f"{project.slug} in {CATALOG}",
                    ),
                )
        if language == catalog.default:
            listed = listed_projects(page)
            if listed is None:
                messages.append(
                    "has no JSON-LD that lists the projects, or more than one: "
                    f"on_post_page of {HOOKS} puts that of structured_data() into "
                    "its head"
                )
            elif listed != software:
                messages.append(
                    f"lists {', '.join(listed) or 'no project'} in its JSON-LD, not "
                    f"every project with a repo of {CATALOG} in its order, "
                    f"{', '.join(software)}: structured_data() of {HOOKS} lists them"
                )
        findings += [Finding(name, message) for message in messages]
    return findings + list(missing.values())


def page_of(location: str) -> str:
    """The page of location, an address in the website or a location of its search
    index, without its section and with its folder for an index.html."""
    return re.sub(r"(^|/)index\.html$", r"\1", location.partition("#")[0])


def search_findings(site: Path, catalog: Catalog) -> list[Finding]:
    """What the search index of the website in site breaks: it keeps every page of
    this website that its sitemap lists, with the boosts that add_to_search gives
    them, and has the entries of the project websites, each in the folder of its
    website."""
    path = site / SEARCH_INDEX
    if not path.is_file():
        return [
            Finding(
                SEARCH_INDEX,
                "is missing: the search plugin of mkdocs.yml writes it, and "
                f"on_post_build of {HOOKS} adds the project websites to it",
            )
        ]
    try:
        docs = documents(path.read_bytes(), SEARCH_INDEX)
    except SearchError as error:
        return [Finding(SEARCH_INDEX, f"can't be read: {error}")]
    folders = tuple(website.folder for website in websites(catalog, SITE))
    own = [doc for doc in docs if not doc["location"].startswith(folders)]
    messages: list[str] = []
    sitemap = site / SITEMAP
    pages = (
        LOCATION.findall(sitemap.read_text(encoding="utf-8", errors="replace"))
        if sitemap.is_file()
        else []
    )
    kept = {page_of(doc["location"]) for doc in own}
    lost = [url for url in pages if page_of(url.removeprefix(SITE)) not in kept]
    if lost:
        messages.append(
            f"has no entry of {len(lost)} page(s) of this website that {SITEMAP} "
            f"lists, such as {lost[0]}: add_to_search() of {HOOKS} keeps the entries "
            "of this website beside those of the projects"
        )
    flat = [
        doc["location"]
        for doc in own
        if boost_of(doc["location"]) is not None and "boost" not in doc
    ]
    if flat:
        messages.append(
            f"gives {len(flat)} entries of this website no boost, such as {flat[0]}: "
            f"add_to_search() of {HOOKS} gives them that of their page after the "
            "search plugin has written the index, so something wrote it again after "
            "on_post_build, which must come last, as check_order() makes sure"
        )
    if folders and len(own) == len(docs):
        messages.append(
            f"has no entry of the {len(folders)} project websites at {SITE}: "
            f"on_post_build of {HOOKS} adds them after the build. When the log of the "
            "build says that the search leaves out every website, GitHub Pages was "
            "away while it ran: run the job again"
        )
    strays = [doc["location"] for doc in own if SEPARATOR in doc["title"]]
    if strays:
        messages.append(
            f"has {len(strays)} entries of a project outside the folder of its "
            f"website, such as {strays[0]}: entries() of {HOOKS} puts every location "
            "into the folder of its website"
        )
    return [Finding(SEARCH_INDEX, message) for message in messages]


def check_site(site: Path, catalog: Catalog, now: datetime) -> list[Finding]:
    """Every promise of the hooks of this website that the website MkDocs built in
    site breaks at the moment now, in the files that the hooks alone write or change
    after the build: security.txt, robots.txt, llms.txt, the sitemaps, the old
    addresses, the 404 page, the home pages and the search index."""
    return [
        *security_findings(site, now),
        *robots_findings(site, catalog),
        *llms_findings(site, catalog),
        *sitemap_findings(site),
        *moved_findings(site, catalog),
        *not_found_findings(site, catalog),
        *home_findings(site, catalog),
        *search_findings(site, catalog),
    ]


def annotation(finding: Finding, folder: str) -> str:
    """The finding as an annotation of the CI, which the summary of the check shows,
    with its path in folder, where MkDocs built the website."""
    message = f"{folder}/{finding.path}: {finding.message}"
    for sign, code in (("%", "%25"), ("\r", "%0D"), ("\n", "%0A")):
        message = message.replace(sign, code)
    return f"::error title={PROMISES}::{message}"


def site_check(site: Path, root: Path) -> int:
    """Check the website that MkDocs built in site against the catalog in the folder
    root: 0 when it keeps every promise of the hooks, 1 with a line for each that it
    breaks, and in the CI an annotation too."""
    folder = site.as_posix().rstrip("/") or "."
    if not site.is_dir():
        print(
            f"{folder} is no folder: build the website with mkdocs build --strict, "
            "and name its folder, such as site.",
            file=sys.stderr,
        )
        return 1
    try:
        catalog = load(root)
    except CatalogError as error:
        print(error, file=sys.stderr)
        return 1
    findings = check_site(site, catalog, datetime.now(UTC))
    if not findings:
        print(
            f"The website in {folder} keeps what the hooks of {HOOKS} promise: "
            "security.txt, robots.txt, llms.txt, the sitemaps, the old addresses, the "
            "404 page, the home pages and the search."
        )
        return 0
    for finding in findings:
        print(f"{folder}/{finding.path}: {finding.message}")
    if os.environ.get("GITHUB_ACTIONS") == "true":
        for finding in findings:
            print(annotation(finding, folder))
    print(
        f"{len(findings)} finding(s): the website breaks what the hooks of {HOOKS} "
        "promise. A new version of Material or of mkdocs-static-i18n that writes its "
        f"files differently, or a change of the hooks, of {CATALOG} or of overrides/, "
        "broke it: fix what each line names, build the website again and check its "
        "folder with bash scripts/check-site.sh site."
    )
    return 1


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


def fetched(url: str) -> bytes | None:
    """The content of url, after its redirects, or None when it answers 404 or 410:
    a file that is gone."""
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT) as response:
            return bytes(response.read())
    except urllib.error.HTTPError as error:
        error.close()
        if error.code in GONE:
            return None
        raise CheckError(
            f"{url} answers {error.code}, where the catalog bot expects 200 or 404; "
            "start it again later."
        ) from error
    # As in status.
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


def requirement_drift(
    project: Project, fetch: Callable[[str], bytes | None]
) -> list[str]:
    """What differs between the file from which the card of project reads what it
    works with and that file on the default branch of its repository, which fetch
    reads: the file is gone, or lacks a value, which the next release would take off
    the card."""
    source = project.requires
    if not isinstance(source, Source):
        return []
    slug, repo, file = project.slug, project.repo, source.file
    advice = (
        "Correct `requires`, or write what the project works with into "
        "`requires` as a text in every language."
    )
    content = fetch(RAW.format(repo, DEFAULT_BRANCH, file))
    if content is None:
        return [
            f"`{slug}`: {repo} has no {file} any more, from which its card reads what "
            f"it works with. {advice}"
        ]
    try:
        values_in(source, content)
    except RequirementError as error:
        return [
            f"`{slug}`: {file} of {repo} {error}, and its card reads what it works "
            f"with from there. {advice}"
        ]
    return []


def drawing_drift(
    project: Project, fetch: Callable[[str], bytes | None]
) -> list[str]:
    """What the default branch of the repository of project, which fetch reads,
    lacks of the files from which the hub draws pictures of its card: a screenshot
    or its logo that is gone, which would stop scripts/project-pictures.sh."""
    image = project.picture
    if image is None or image.drawing is None:
        return []
    files = list(dict.fromkeys(image.drawing.screenshot.values()))
    if image.drawing.logo is not None:
        files.append(image.drawing.logo)
    return [
        f"`{project.slug}`: {project.repo} has no {file} any more, from which the hub "
        "draws a picture of its card. Correct `drawing` with a file of the "
        "repository."
        for file in files
        if fetch(RAW.format(project.repo, DEFAULT_BRANCH, file)) is None
    ]


def drift(
    catalog: Catalog,
    found: list[Repository],
    probe: Callable[[str], int],
    fetch: Callable[[str], bytes | None],
) -> list[str]:
    """What differs between catalog and the repositories of its owner, found, the
    websites of its projects, which probe asks for their status, and the files from
    which their cards read what they work with and from which the hub draws their
    pictures, which fetch reads: one sentence of
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
        differences += requirement_drift(project, fetch)
        differences += drawing_drift(project, fetch)
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
            f"The catalog bot compares {CATALOG} with the repositories on GitHub, "
            "with the websites of the projects in every language and with the files "
            "that say what they work with every week, and found "
            f"{len(differences)} difference(s):",
            "",
            *(f"- {difference}" for difference in differences),
            "",
            f"Change {CATALOG}, whose comments describe every key, and write the "
            "tables of the READMEs with",
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
        differences = drift(catalog, found, status, fetched)
    except (CatalogError, CheckError, OSError) as error:
        print(error, file=sys.stderr)
        return 2
    if not differences:
        print(
            f"{CATALOG} is current: it has every repository with a website at "
            f"{SITE}, every website in a further language, every file that says "
            "what a project works with, and every file from which the hub draws a "
            "picture of a card."
        )
        return 0
    sys.stdout.write(report(differences))
    return DIFFERS


# The watch of the live websites.


class Attention(Exception):
    """What the watch found in a live file that ends its check of the file: the
    sentence of the issue, with its fix."""


@dataclass(frozen=True)
class Kind:
    """The kind of a value of the data of the dashboard, as projects.js takes it:
    what it is in words, for the issue, and whether a value is one."""

    words: str
    fits: Callable[[object], bool]


def is_day(value: object) -> bool:
    """Whether value is a day of the data, such as 2026-10-25."""
    return isinstance(value, str) and DAY.fullmatch(value) is not None


def is_number(value: object, low: float, high: float) -> bool:
    """Whether value is a finite number from low to high, as within() of projects.js
    takes it; a bool is none, as JSON tells them apart."""
    return (
        isinstance(value, int | float)
        and not isinstance(value, bool)
        and math.isfinite(value)
        and low <= value <= high
    )


def is_health(value: object) -> bool:
    """Whether value holds the health of every repository by its name, as a day of
    history.json does."""
    return isinstance(value, dict) and all(
        REPOSITORY.fullmatch(name) is not None and isinstance(health, dict)
        for name, health in value.items()
    )


# The kinds that DASHBOARD_FIELDS may give a field, by their names. A value that
# projects.js can do without may be null; the script leaves its fact off the page.
KINDS = {
    "repository": Kind(
        "the name of a repository (such as Dennis-Otto/repo-blueprint)",
        lambda value: (
            isinstance(value, str) and REPOSITORY.fullmatch(value) is not None
        ),
    ),
    "date": Kind("a day (such as 2026-10-25)", is_day),
    "day": Kind(
        "a day (such as 2026-10-25) or null",
        lambda value: value is None or is_day(value),
    ),
    "text": Kind(
        "a text or null", lambda value: value is None or isinstance(value, str)
    ),
    "github": Kind(
        f"an address at {GITHUB} or null",
        lambda value: value is None
        or (isinstance(value, str) and value.startswith(GITHUB)),
    ),
    "score": Kind(
        "a number from 0 to 10 or null",
        lambda value: value is None or is_number(value, 0, 10),
    ),
    "share": Kind(
        "a number from 0 to 100 or null",
        lambda value: value is None or is_number(value, 0, 100),
    ),
    "hours": Kind(
        "a number of 0 or more, or null",
        lambda value: value is None or is_number(value, 0, math.inf),
    ),
    "health": Kind(
        "an object with the numbers of the health, or null",
        lambda value: value is None or isinstance(value, dict),
    ),
    "health by repository": Kind(
        "an object with the health of every repository by its name", is_health
    ),
}


class Shape(NamedTuple):
    """What projects.js reads of the data of the dashboard, as DASHBOARD_FIELDS names
    it: the schema of repos.json that the script knows, and the kind of every field
    that it reads of an entry of repos.json, of its health and of a day of
    history.json, by the name of each."""

    schema: int
    repos: dict[str, str]
    health: dict[str, str]
    history: dict[str, str]


def dashboard_fields(root: Path) -> Shape:
    """What projects.js reads of the data of the dashboard, from DASHBOARD_FIELDS in
    the folder root."""
    try:
        data = json.loads((root / DASHBOARD_FIELDS).read_text(encoding="utf-8"))
        shape = Shape(data["schema"], data["repos"], data["health"], data["history"])
    # Also a KeyError or a TypeError of data without its keys, or of no object.
    except (OSError, ValueError, LookupError, TypeError) as error:
        raise CheckError(f"{DASHBOARD_FIELDS} can't be read: {error!r}") from error
    if (
        not isinstance(shape.schema, int)
        or isinstance(shape.schema, bool)
        or not all(
            isinstance(fields, dict) and fields and set(fields.values()) <= set(KINDS)
            for fields in (shape.repos, shape.health, shape.history)
        )
    ):
        raise CheckError(
            f"{DASHBOARD_FIELDS} needs schema, the number of the shape of repos.json "
            "that docs/javascripts/projects.js knows, and repos, health and history, "
            "each the kind of every field that the script reads by its name, one of: "
            f"{', '.join(KINDS)}."
        )
    return shape


def few(names: list[str]) -> str:
    """names in a sentence, each as code, NAMED at most, and how many more."""
    shown = [f"`{name}`" for name in names[:NAMED]]
    if len(names) > NAMED:
        shown.append(f"{len(names) - NAMED} more")
    if len(shown) == 1:
        return shown[0]
    return f"{', '.join(shown[:-1])} and {shown[-1]}"


def labeled(items: list[Any], key: str) -> list[tuple[str, dict[str, Any]]]:
    """The objects of items, each by its value of key, such as the name of its
    repository, or by its place in items when it has none."""
    return [
        (item[key] if isinstance(item.get(key), str) else f"number {number}", item)
        for number, item in enumerate(items, start=1)
        if isinstance(item, dict)
    ]


def field_findings(
    url: str, about: str, items: list[tuple[str, Any]], fields: dict[str, str]
) -> list[str]:
    """What items, the objects of the file at url by their names, break of fields,
    the kind of every field that projects.js reads of them: a sentence for every
    field that some of them lack, and one for every field that some of them hold as
    another kind, with the names of those."""
    findings: list[str] = []
    for name, kind in fields.items():
        lacking = [label for label, item in items if name not in item]
        wrong = [
            label
            for label, item in items
            if name in item and not KINDS[kind].fits(item[name])
        ]
        if lacking:
            findings.append(
                f"`{name}` is missing in {url} from {about}: {few(lacking)}, so "
                "the website leaves its fact off the page. The dashboard of the "
                "blueprint took the field away or renamed it: read the new one in "
                f"`docs/javascripts/projects.js`, and name it in `{DASHBOARD_FIELDS}`."
            )
        if wrong:
            findings.append(
                f"`{name}` in {url} isn't {KINDS[kind].words} in {about}: "
                f"{few(wrong)}, so the website leaves its fact off the page. Read the "
                "new value in "
                "`docs/javascripts/projects.js`, and give its kind in "
                f"`{DASHBOARD_FIELDS}`."
            )
    return findings


# What a finding of a file of the dashboard asks for.
DASHBOARD_FIX = (
    "The Dashboard workflow of repo-blueprint publishes it every few hours: look at "
    "its latest runs."
)


def live_json(url: str, fetch: Callable[[str], bytes | None], use: str) -> Any:
    """The JSON at url, which fetch reads, for use, what the website takes from it."""
    content = fetch(url)
    if content is None:
        raise Attention(f"{url} answers 404, so {use}. {DASHBOARD_FIX}")
    try:
        return json.loads(content)
    except ValueError as error:
        raise Attention(
            f"{url} is no JSON ({error}), so {use}. {DASHBOARD_FIX}"
        ) from error


def feed_findings(
    catalog: Catalog, shape: Shape, fetch: Callable[[str], bytes | None]
) -> list[str]:
    """What repos.json of the dashboard breaks of shape, what projects.js reads of
    it, and the repositories of the catalog that it lacks."""
    url = urljoin(SITE, FEED)
    use = "the cards, the Trust page and the Releases page keep the facts of the build"
    try:
        data = live_json(url, fetch, use)
    except Attention as found:
        return [str(found)]
    entries = data.get("repos") if isinstance(data, dict) else None
    if not isinstance(entries, list) or not entries:
        return [
            f"{url} holds no list of repositories in `repos`, so {use}. "
            f"{DASHBOARD_FIX}"
        ]
    if data.get("schema") != shape.schema:
        return [
            f"{url} has the schema {json.dumps(data.get('schema'))}, where "
            f"`docs/javascripts/projects.js` knows {shape.schema}, so the cards take "
            "the numbers of history.json alone, without their releases. Read the "
            "fields of the new schema in the script, and set its `SCHEMA` and "
            f"`schema` of `{DASHBOARD_FIELDS}` to it."
        ]
    repos = labeled(entries, "repo")
    findings: list[str] = []
    if len(repos) < len(entries):
        findings.append(
            f"{len(entries) - len(repos)} of the {len(entries)} entries of `repos` in "
            f"{url} are no objects, which the website leaves out. {DASHBOARD_FIX}"
        )
    findings += field_findings(url, "these entries", repos, shape.repos)
    health = [
        (label, item["health"])
        for label, item in repos
        if isinstance(item.get("health"), dict)
    ]
    findings += field_findings(
        url, "the health of these entries", health, shape.health
    )
    listed = {label for label, _ in repos}
    findings += [
        f"{url} has no entry for {project.repo}, so its card keeps the facts of the "
        "build. The dashboard of the blueprint lists every public repository of the "
        "owner that is neither archived nor a fork, and adds a new one with its next "
        "run."
        for project in catalog.projects
        if project.repo and project.repo not in listed
    ]
    return findings


def history_findings(shape: Shape, fetch: Callable[[str], bytes | None]) -> list[str]:
    """What history.json of the dashboard breaks of shape, what projects.js reads of
    every day of it and of the health of the latest one."""
    url = urljoin(SITE, HISTORY)
    use = (
        "the cards have no numbers to fall back on while repos.json has a shape that "
        "the website doesn't know"
    )
    try:
        data = live_json(url, fetch, use)
    except Attention as found:
        return [str(found)]
    days = labeled(data, "date") if isinstance(data, list) else []
    if not days:
        return [
            f"{url} holds no day, an object with `date` and `repos`, so {use}. "
            f"{DASHBOARD_FIX}"
        ]
    findings = field_findings(url, "these days", days, shape.history)
    # The script takes the health of the latest day alone.
    complete = [
        item
        for _, item in days
        if is_day(item.get("date")) and is_health(item.get("repos"))
    ]
    if complete:
        latest = max(complete, key=lambda item: str(item["date"]))
        findings += field_findings(
            url,
            f"the health on {latest['date']} of these repositories",
            list(latest["repos"].items()),
            shape.health,
        )
    return findings


def index_findings(catalog: Catalog, fetch: Callable[[str], bytes | None]) -> list[str]:
    """What the search index of every project website at SITE breaks, which the next
    build of this website takes into its search: it is there, it is one of Material
    for MkDocs, and it holds an entry at least."""
    findings: list[str] = []
    for website in websites(catalog, SITE):
        url = urljoin(SITE, f"{website.folder}{SEARCH_INDEX}")
        fix = (
            "the next build of this website leaves the website of "
            f"{website.project.name[catalog.default]} out of its search. Look at the "
            "latest run of the workflow that publishes that website; if a new version "
            "of Material for MkDocs moved its index, change `SEARCH_INDEX` of "
            f"`{HOOKS}`."
        )
        content = fetch(url)
        if content is None:
            findings.append(f"{url} answers 404, so {fix}")
            continue
        try:
            docs = documents(content, url)
        except SearchError as error:
            findings.append(f"{str(error).rstrip('.')}, so {fix}")
            continue
        if not docs:
            findings.append(f"{url} holds no entry, so {fix}")
    return findings


# What a finding of a file that every build writes asks for: a new build.
REBUILD = (
    "Every build of this website writes it: start the Catalog workflow with the job "
    "rebuild, and look at the run of the Docs workflow that it starts."
)


def text_of(content: bytes) -> str:
    """content, a text file of the website, as text."""
    return content.decode("utf-8", errors="replace")


def ahead(url: str, content: bytes, now: datetime) -> list[str]:
    """What the security.txt at url, content, breaks at the moment now: it holds for
    more than AHEAD, as the daily build renews it to VALID ahead."""
    expires = text_fields(text_of(content)).get("expires", [])
    moment: datetime | None = None
    if len(expires) == 1:
        try:
            moment = datetime.fromisoformat(expires[0])
        except ValueError:
            moment = None
    if moment is None or moment.tzinfo is None:
        return [
            f"{url} names no Expires with a time of RFC 3339, such as "
            "2027-10-25T00:00:00Z, so security researchers can't tell whether it "
            f"holds. {REBUILD}"
        ]
    if moment - now > AHEAD:
        return []
    return [
        f"{url} holds until {expires[0]}, {AHEAD.days} days or fewer from now, where "
        f"every build of this website renews it to {VALID.days} days ahead: the "
        f"website was last published on {(moment - VALID).date().isoformat()}, "
        f"though the Catalog workflow builds it every day. {REBUILD}"
    ]


def root_findings(
    catalog: Catalog, fetch: Callable[[str], bytes | None], now: datetime
) -> list[str]:
    """What the files at the root of SITE break that crawlers and security
    researchers read: both copies of security.txt hold for more than AHEAD at the
    moment now, robots.txt names every sitemap of the address, and the sitemap of
    this website lists the root of the address."""
    findings: list[str] = []
    for path in SECURITY_TXT:
        url = urljoin(SITE, path)
        content = fetch(url)
        if content is None:
            findings.append(
                f"{url} answers 404, so security researchers find no way to report a "
                f"vulnerability privately. {REBUILD}"
            )
        else:
            findings += ahead(url, content, now)
    url = urljoin(SITE, ROBOTS)
    content = fetch(url)
    if content is None:
        findings.append(
            f"{url} answers 404, so crawlers find the sitemap of no website of the "
            f"address. {REBUILD}"
        )
    else:
        named = text_fields(text_of(content)).get("sitemap", [])
        missing = [found for found in sitemaps(catalog, SITE) if found not in named]
        if missing:
            findings.append(
                f"{url} names no Sitemap: {few(missing)}, so crawlers find those "
                f"websites later. robots() of `{HOOKS}` names the sitemap of every "
                f"website of {CATALOG} at the address. {REBUILD}"
            )
    url = urljoin(SITE, SITEMAP)
    content = fetch(url)
    if content is None:
        findings.append(
            f"{url} answers 404, so crawlers find no page of this website. {REBUILD}"
        )
    elif SITE not in LOCATION.findall(text_of(content)):
        findings.append(
            f"{url} doesn't list {SITE}, the home page of the address. "
            f"sitemaps_at_root() of `{HOOKS}` leads it there after the build. {REBUILD}"
        )
    return findings


def former_findings(
    catalog: Catalog,
    fetch: Callable[[str], bytes | None],
    probe: Callable[[str], int],
) -> list[str]:
    """What the old addresses of former/<folder>.txt break: each answers with its
    page, which leads to the same page in the folder of the website now, and that
    page answers, which probe asks for its status."""
    moves = catalog.moves()
    findings: list[str] = []
    for project in catalog.projects:
        for folder in project.former:
            missing: list[str] = []
            astray: list[str] = []
            gone: list[str] = []
            for page in catalog.former_pages.get(folder, ()):
                target = moved_to(moves[folder], page)
                content = fetch(urljoin(SITE, f"{folder}/{page}"))
                if content is None:
                    missing.append(page)
                    continue
                found = Built()
                found.feed(text_of(content))
                found.close()
                if found.canonical != [target] or found.refresh != [f"0; url={target}"]:
                    astray.append(page)
                elif not exists(probe, target):
                    gone.append(page)
            old = urljoin(SITE, f"{folder}/")
            if missing:
                findings.append(
                    f"Old addresses of {old} that answer 404, though "
                    f"`{FORMER}/{folder}.txt` lists them: {few(missing)}. Old links "
                    f"lead to the 404 page there; on_post_build of `{HOOKS}` writes a "
                    f"page at each that leads to {moves[folder]}. {REBUILD}"
                )
            if astray:
                findings.append(
                    f"Old addresses of {old} that don't lead to the same page in "
                    f"{moves[folder]}: {few(astray)}. moved_page() of `{HOOKS}` writes "
                    "each with its canonical address and its refresh, so remove what "
                    f"writes them after the hooks, such as a file in docs/. {REBUILD}"
                )
            if gone:
                findings.append(
                    f"Old addresses of {old} whose pages in {moves[folder]} answer "
                    f"404, since the website of {project.name[catalog.default]} "
                    f"moved or removed them: {few(gone)}. Bring each page back "
                    "there, such as with a page that leads to its new place, or "
                    f"remove its line from `{FORMER}/{folder}.txt` once it is gone "
                    "for good."
                )
    return findings


def attention(
    catalog: Catalog,
    shape: Shape,
    fetch: Callable[[str], bytes | None],
    probe: Callable[[str], int],
    now: datetime,
) -> list[str]:
    """What needs attention at the moment now in what the live websites at SITE hold
    and the hub depends on after its build, which fetch reads and probe asks for its
    status: the data of the dashboard, against shape, the search index of every
    project website, the files at the root of the address and the old addresses."""
    return [
        *feed_findings(catalog, shape, fetch),
        *history_findings(shape, fetch),
        *index_findings(catalog, fetch),
        *root_findings(catalog, fetch, now),
        *former_findings(catalog, fetch, probe),
    ]


Answer = TypeVar("Answer")


def patient(ask: Callable[[str], Answer]) -> Callable[[str], Answer]:
    """ask, such as fetched or status, tried TRIES times for an address that can't be
    reached or answers oddly, before its CheckError: the watch asks well over a
    hundred addresses every day, and a single lost answer is no finding."""

    def again(url: str) -> Answer:
        for _ in range(TRIES - 1):
            try:
                return ask(url)
            except CheckError:
                continue
        return ask(url)

    return again


def watch_report(findings: list[str]) -> str:
    """The text of the issue of the watch, in Markdown, with findings."""
    return "\n".join(
        [
            f"The watch of the catalog bot asks the live websites at {SITE} every day "
            "for what this website depends on after its build, and found "
            f"{len(findings)} thing(s) that need attention:",
            "",
            *(f"- {finding}" for finding in findings),
            "",
            "The next run closes this issue once nothing needs attention; start the "
            "Catalog workflow by hand with the job watch to check sooner, or run",
            "",
            "```sh",
            WATCH,
            "```",
            "",
        ]
    )


def watch(root: Path) -> int:
    """Watch what the live websites at SITE hold and the hub depends on after its
    build, against the catalog in the folder root: 0 when nothing needs attention,
    DIFFERS with the text of the issue on stdout, 2 when the bot can't tell."""
    try:
        catalog = load(root)
        shape = dashboard_fields(root)
        findings = attention(
            catalog, shape, patient(fetched), patient(status), datetime.now(UTC)
        )
    except (CatalogError, CheckError) as error:
        print(error, file=sys.stderr)
        return 2
    if not findings:
        print(
            f"The live websites at {SITE} hold what this website depends on: the data "
            "of the dashboard in the shape that docs/javascripts/projects.js reads, "
            "the search index of every project website, security.txt for more than "
            f"{AHEAD.days} days, robots.txt with every sitemap, the sitemap of this "
            "website, and a page at every old address that leads to its page now."
        )
        return 0
    sys.stdout.write(watch_report(findings))
    return DIFFERS


# The script.


def pictures(catalog: Catalog) -> str:
    """The pictures of the cards that come from the social preview of a repository,
    those of the first language, one per line for scripts/project-pictures.sh: the
    repository, the file in the repository that the picture goes to, and the
    license of the repository, which is that of the picture too."""
    return "".join(
        f"{project.repo} docs/{project.picture.src[catalog.default]} "
        f"{project.license}\n"
        for project in catalog.projects
        if project.repo is not None and project.picture is not None
    )


class DrawingError(Exception):
    """A picture that the hub draws lacks the icon of its card."""


def theme_icons() -> Path | None:
    """The folder of the icons of Material for MkDocs, which the tools of the website
    in .venv-docs install, or None without them."""
    try:
        import material  # noqa: PLC0415 - only the tools of the website have it
    except ImportError:
        return None
    return Path(str(material.__file__)).parent / "templates" / ".icons"


def icon_svg(icon: str, icons: Path | None) -> str:
    """The SVG of icon, a name of Material for MkDocs such as material-file-tree, from
    the folder icons of the theme, where its set and its name make its path, such as
    material/file-tree.svg or fontawesome/brands/github.svg."""
    if icons is None:
        raise DrawingError(
            f"Drawing the icon {icon} needs Material for MkDocs: set up the tools of "
            "the website in .venv-docs, as CONTRIBUTING.md describes."
        )
    for parts in (1, 2):
        *folders, name = icon.split("-", parts)
        path = icons.joinpath(*folders, f"{name}.svg")
        if path.is_file():
            return path.read_text(encoding="utf-8").strip()
    raise DrawingError(f"Material for MkDocs has no icon {icon} in {icons}.")


def drawings(
    catalog: Catalog, folder: Path, template: str, icons: Path | None
) -> str:
    """Write into folder the page of every picture that the hub draws, from template,
    the page of DRAWING, and list each, one per line for scripts/project-pictures.sh:
    the repository, the file in the repository that the picture goes to, the license
    of the repository, the page, and the address and the file in folder of its
    screenshot and of its logo, or - for both without a logo, where the page shows
    the icon of the card from the folder icons of the theme.

    The page names the files by their names alone, since they are beside it, and
    holds the name and the tagline of the project in the language of the picture,
    the tagline without the name when it starts with it, as in a social preview."""
    lines = []
    folder.mkdir(parents=True, exist_ok=True)
    for project in catalog.projects:
        image = project.picture
        if project.repo is None or image is None or image.drawing is None:
            continue
        drawing = image.drawing
        logo = ["-", "-"]
        if drawing.logo is not None:
            file = f"{project.slug}.logo{PurePosixPath(drawing.logo).suffix}"
            logo = [
                RAW.format(project.repo, DEFAULT_BRANCH, drawing.logo),
                (folder / file).as_posix(),
            ]
            mark = f'<img class="logo" src="{escape(file)}" alt="">'
        else:
            mark = f'<div class="logo icon">{icon_svg(project.icon, icons)}</div>'
        for language, screenshot in drawing.screenshot.items():
            base = f"{project.slug}.{language}"
            shot = f"{base}.screenshot{PurePosixPath(screenshot).suffix}"
            name = project.name[language]
            page = folder / f"{base}.html"
            page.write_text(
                Template(template).substitute(
                    lang=escape(language),
                    name=escape(name),
                    tagline=escape(
                        project.tagline[language].removeprefix(f"{name}: ")
                    ),
                    accent=drawing.accent,
                    logo=mark,
                    screenshot=escape(shot),
                ),
                encoding="utf-8",
                newline="\n",
            )
            fields = [
                project.repo,
                f"docs/{image.src[language]}",
                str(project.license),
                page.as_posix(),
                RAW.format(project.repo, DEFAULT_BRANCH, screenshot),
                (folder / shot).as_posix(),
                *logo,
            ]
            lines.append(" ".join(fields) + "\n")
    return "".join(lines)


def main(argv: list[str] | None = None, root: Path = ROOT) -> int:
    """Write or check the table of the projects in every README, list the pictures of
    the cards, write the pages of those that the hub draws, compare the catalog with
    GitHub and the websites of the projects for the catalog bot, watch the live
    websites, or check the built website."""
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            # The console of Windows may lack a character of the README.
            stream.reconfigure(errors="backslashreplace")
    parser = argparse.ArgumentParser(
        description="Write or check the table of the projects in every README, "
        f"from {CATALOG}, list the pictures of the cards, write the pages of "
        f"those that the hub draws, compare {CATALOG} "
        "with GitHub and the websites of the projects, watch the live websites, or "
        "check the built website."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--write",
        action="store_true",
        help=f"write the table into {README} and the README of every other language",
    )
    mode.add_argument(
        "--check",
        action="store_true",
        help=f"check {CATALOG}, and that every README has its table",
    )
    mode.add_argument(
        "--pictures",
        action="store_true",
        help="list the repository, the picture and the license of every card "
        "whose picture comes from a repository, for scripts/project-pictures.sh",
    )
    mode.add_argument(
        "--drawings",
        metavar="FOLDER",
        type=Path,
        help=f"write the page of {DRAWING} for every picture of a card that the "
        "hub draws into FOLDER, and list the repository, the picture, the license, "
        "the page, and the address and the file of its screenshot and of its logo "
        "of each, for scripts/project-pictures.sh",
    )
    mode.add_argument(
        "--network",
        metavar="REPOSITORIES",
        type=Path,
        help=f"compare {CATALOG} with the repositories of the file REPOSITORIES, "
        f"which gh repo list --json {','.join(FIELDS)} writes, with the websites "
        "of the projects in every language and with the files that say what they "
        "work with, and print what differs as "
        "the issue of the catalog bot: exit 0 when nothing differs, "
        f"{DIFFERS} when something does, and 2 when it can't tell",
    )
    mode.add_argument(
        "--watch",
        action="store_true",
        help=f"ask the live websites at {SITE} for what this website depends on "
        "after its build: the data of the dashboard, against "
        f"{DASHBOARD_FIELDS}, the search index of every project website, "
        "security.txt, robots.txt, the sitemap and the old addresses, and print "
        "what needs attention as the issue of the catalog bot: exit 0 when nothing "
        f"does, {DIFFERS} when something does, and 2 when it can't tell",
    )
    mode.add_argument(
        "--site",
        metavar="SITE",
        type=Path,
        help="check the website that MkDocs built in the folder SITE, such as site, "
        "for what the hooks promise in the files that they alone write: "
        "security.txt, robots.txt, llms.txt, the sitemaps, the old addresses, the 404 "
        "page, the home pages and the search; exit 1 with a line for each broken "
        "promise",
    )
    arguments = parser.parse_args(argv)
    if arguments.network is not None:
        return network(arguments.network, root)
    if arguments.watch:
        return watch(root)
    if arguments.site is not None:
        return site_check(arguments.site, root)
    try:
        catalog = load(root)
        if arguments.pictures:
            sys.stdout.write(pictures(catalog))
            return 0
        if arguments.drawings is not None:
            template = (root / DRAWING).read_text(encoding="utf-8")
            listed = drawings(catalog, arguments.drawings, template, theme_icons())
            sys.stdout.write(listed)
            return 0
        # Every README is read and its table made before one is written, so that
        # a README without its markers leaves the others as they are.
        texts = {}
        for language, name in readmes(catalog).items():
            current = (root / name).read_text(encoding="utf-8")
            texts[name] = (current, readme(current, catalog, language))
    except (CatalogError, DrawingError, OSError) as error:
        print(error, file=sys.stderr)
        return 1
    differs = False
    for name, (current, wanted) in texts.items():
        if wanted == current:
            print(f"{name} has the current table of the projects of {CATALOG}.")
        elif arguments.write:
            (root / name).write_text(wanted, encoding="utf-8", newline="\n")
            print(f"{name} has the table of the projects of {CATALOG} now.")
        else:
            sys.stdout.writelines(
                difflib.unified_diff(
                    current.splitlines(keepends=True),
                    wanted.splitlines(keepends=True),
                    name,
                    f"{name}, from {CATALOG}",
                )
            )
            print(
                f"{name} differs from {CATALOG}; write its table with\n  {WRITE}",
                file=sys.stderr,
            )
            differs = True
    return 1 if differs else 0


if __name__ == "__main__":
    sys.exit(main())
