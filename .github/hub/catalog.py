"""The catalog of this website, as data: projects.toml, at the root of the
repository, lists every project once: its name, its texts, its picture and its links in
each language of the website. reader.py reads the file into the data classes of this
module, and every other module takes them from it, with the words that several of them
share.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

# The warnings of MkDocs, which mkdocs build --strict counts.
log = logging.getLogger("mkdocs.hooks.project")

# The root of the repository, with projects.toml and the READMEs.
ROOT = Path(__file__).resolve().parents[2]
CATALOG = "projects.toml"

# The words of the Trust page that the catalog names too, of which TRUST_MARKER in
# render.py tells the whole: the table of projects.toml with its texts, which of them
# have a value that every project gives alike, which of those link a page of each
# project, and the numbers of its table.
TRUST = "trust"
TRUST_VALUED = ("tag", "provenance", "immutable", "sbom", "vex", "policy", "report")
TRUST_LINKED = ("policy", "report")
TRUST_NUMBERS = ("release", "coverage", "mutation", "scorecard", "bestpractices")

# The address of every repository.
GITHUB = "https://github.com/"

# The levels of the OpenSSF Best Practices, of which BEST_PRACTICES in render.py
# tells the whole.
LEVELS = ("passing", "silver", "gold")

# What a project works with, on the line of its card above its buttons, which
# requirements.py tells the whole of: the table of projects.toml with the label of
# the line, and the keys of requires that name a file of its repository.
REQUIREMENTS = "requirements"
SOURCE_KEYS = ("file", "field", "text")

# A place of a value in a text, {} for the one value of a file, or {name} for each
# of several, such as {min}.
PLACEHOLDER = re.compile(r"\{([^{}]*)\}")

# The home page of the default language, at the root of the address, which alone
# gets the structured data.
HOME = "index.html"

# The address in whose folders the websites of the projects live.
SITE = "https://dennis-otto.github.io/"

# The exit code of --network when the catalog differs: not 1, which Python gives
# when it stops with an exception, so that a crash can't pass for a difference.
DIFFERS = 3
# The languages of the catalog by their names, for the messages of the bot.
LANGUAGE_NAMES = {"en": "English", "de": "German"}

# The folder of the lists of the pages of a website that moved to another folder of
# the address, FORMER/<folder>.txt, of which MOVED in address.py tells the whole.
FORMER = "former"


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
            return {other.slug: other for other in self.projects}[project.second].start
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


def cell(text: str) -> str:
    """text in a cell of a table of Markdown, where a | would end the cell."""
    return text.replace("|", "\\|")
