"""The hooks of this website, beside those that every website shares in
.github/mkdocs_blueprint.py; mkdocs.yml names both files.

projects.toml, at the root of the repository, lists every project once: its name,
its texts and its links in each language of the website. From it, the hooks put the
cards of the projects into the home page, in the language of the page, and give the
templates the whole list as config.extra["catalog"], for the 404 page of
overrides/404.html. Run as a script, with nothing but the standard library, this
file writes the table of the projects in README.md, or checks that the table is
current, as scripts/check-project.sh does:

    python3 -I .github/mkdocs_project.py --write
    python3 -I .github/mkdocs_project.py --check

This website lives at the root of the address dennis-otto.github.io, which the
websites of the projects share, each in a folder of its own. So the hooks also write
the files that crawlers and security researchers look for at the root of a host
alone: robots.txt with the sitemap of every website of the address, and
security.txt (RFC 9116). The home page of the default language gets the structured
data of the address: the name of the website, its owner and the projects; and the
root of the address, not index.html in it, as its canonical address.

While MkDocs builds the website, the hooks also warn, which fails the strict build of
the check docs, about a title of the menu without its translation and a page without
its translation.
"""

from __future__ import annotations

import argparse
import difflib
import gzip
import io
import json
import logging
import os
import re
import sys
import tomllib
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from html import escape
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

# The warnings of MkDocs, which mkdocs build --strict counts.
log = logging.getLogger("mkdocs.hooks.project")

# The root of the repository, with projects.toml and README.md.
ROOT = Path(__file__).resolve().parents[1]
CATALOG = "projects.toml"
README = "README.md"
# The command that writes the table of the README, for the messages.
WRITE = "python3 -I .github/mkdocs_project.py --write"

# The line of docs/index.md and docs/index.de.md that the cards replace.
MARKER = "<!-- projects -->"
MARKER_LINE = re.compile(rf"^{re.escape(MARKER)}[ \t]*$", re.MULTILINE)
# The lines of README.md between which the table of the projects goes.
TABLE_START = "<!-- projects:start -->"
TABLE_END = "<!-- projects:end -->"

# The pages of docs/ that have no translation yet, by their path there without the
# suffix of the default language. A page leaves this list with its translation.
UNTRANSLATED = frozenset({"security.md"})
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


@dataclass(frozen=True)
class Form:
    """What a text of projects.toml must look like, and how a message says it."""

    pattern: re.Pattern[str]
    description: str


LANGUAGE = re.compile(r"[a-z]{2,3}(?:[_-][A-Za-z0-9]+)*")
SLUG = Form(
    re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*"),
    "lowercase letters, digits and hyphens, such as ha-autodarts",
)
REPO = Form(
    re.compile(r"[A-Za-z0-9-]+/[A-Za-z0-9._-]+"),
    "a repository on GitHub, such as Dennis-Otto/ha-autodarts",
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
# The keys of a [[project]], which the comments of projects.toml describe.
PROJECT_KEYS = (
    "slug",
    "repo",
    "license",
    "platform",
    "icon",
    "name",
    "tagline",
    "summary",
    "start",
    "docs",
)


@dataclass(frozen=True)
class Link:
    """A button of a card: its icon, and its label and address in every language."""

    icon: str
    label: dict[str, str]
    url: dict[str, str]


@dataclass(frozen=True)
class Project:
    """A card of the home page, and a row of the table of the README."""

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

    @property
    def website(self) -> dict[str, str]:
        """Its address on the web in every language: that of its documentation, or
        where its first button leads when it has none."""
        return (self.docs or self.start).url


@dataclass(frozen=True)
class Catalog:
    """The projects of projects.toml, with the languages of their texts."""

    languages: tuple[str, ...]
    projects: tuple[Project, ...]

    @property
    def default(self) -> str:
        """The language of the README, the first of the catalog."""
        return self.languages[0]

    def directory(self) -> list[dict[str, Any]]:
        """Every project for the script of the 404 page, which gets it as JSON: its
        slug, and its name and its website in every language."""
        return [
            {"slug": project.slug, "name": project.name, "url": project.website}
            for project in self.projects
        ]


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
        repo = spdx = platform = None
        if "repo" in table:
            repo = self.text(table["repo"], owner, "repo", REPO)
            # What the structured data of the home page says about the code.
            spdx = self.text(table.get("license"), owner, "license", LICENSE)
            platform = self.text(table.get("platform"), owner, "platform")
        else:
            for key in ("license", "platform"):
                if key in table:
                    self.problem(owner, key, "is for a project with a repo")
        icon = self.text(table.get("icon"), owner, "icon", ICON)
        name = self.texts(table.get("name"), owner, "name")
        tagline = self.texts(table.get("tagline"), owner, "tagline")
        summary = self.texts(table.get("summary"), owner, "summary")
        start = self.link(table.get("start"), owner, "start")
        docs = None
        if "docs" in table:
            url = self.urls(table["docs"], owner, "docs")
            docs = Link(documentation.icon, documentation.label, url)
        return Project(
            slug, repo, spdx, platform, icon, name, tagline, summary, start, docs
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
    reader.table(data, "", "", ("languages", "documentation", "project"))
    documentation = reader.link(
        data.get("documentation"), "", "documentation", url=False
    )
    entries = data.get("project")
    if not isinstance(entries, list) or not entries:
        reader.problem("", "project", "must list the projects as [[project]] tables")
        entries = []
    projects = tuple(
        project
        for number, entry in enumerate(entries, start=1)
        if (project := reader.project(entry, number, documentation)) is not None
    )
    slugs = [project.slug for project in projects if project.slug]
    for slug in sorted({slug for slug in slugs if slugs.count(slug) > 1}):
        reader.problem(slug, "slug", "names more than one project")
    if reader.problems:
        raise CatalogError(
            f"{CATALOG} has {len(reader.problems)} problem(s):\n"
            + "\n".join(f"  {problem}" for problem in reader.problems)
            + f"\nThe comments at the top of {CATALOG} describe every key."
        )
    return Catalog(tuple(languages), projects)


def load(root: Path = ROOT) -> Catalog:
    """The catalog of projects.toml in the folder root."""
    try:
        text = (root / CATALOG).read_text(encoding="utf-8")
    except OSError as error:
        raise CatalogError(f"{CATALOG} can't be read: {error}") from error
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        raise CatalogError(f"{CATALOG} isn't valid TOML: {error}") from error
    return read(data)


def button(link: Link, language: str, *, primary: bool = False) -> str:
    """The Markdown of a button: a link with the classes of Material."""
    classes = ".md-button .md-button--primary" if primary else ".md-button"
    label, url = link.label[language], link.url[language]
    return f"[:{link.icon}: {label}]({url}){{ {classes} }}"


def card(project: Project, language: str) -> str:
    """The Markdown of the card of project, whose heading has the slug as its anchor."""
    buttons = [button(project.start, language, primary=True)]
    if project.docs is not None:
        buttons.append(button(project.docs, language))
    heading = f"### :{project.icon}:{{ .lg .middle }} {project.name[language]}"
    return "\n\n".join(
        [
            '<div class="card" markdown>',
            f"{heading} {{ #{project.slug} }}",
            "---",
            project.summary[language],
            "\n".join(buttons),
            "</div>",
        ]
    )


def cards(catalog: Catalog, language: str) -> str:
    """The Markdown of the grid with the card of every project, in language."""
    return "\n\n".join(
        [
            '<div class="grid" markdown>',
            *(card(project, language) for project in catalog.projects),
            "</div>",
        ]
    )


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
                        # Not the author: ha-autodarts began as a fork.
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
    """Read the catalog for the cards and the templates, and check the translations.

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
    return config


def on_serve(server: Any, config: Any, builder: Any) -> Any:
    """Build the website again when projects.toml changes, while mkdocs serve runs."""
    server.watch(str(Path(config.config_file_path).parent / CATALOG))
    return server


def on_page_markdown(markdown: str, page: Any, config: Any, files: Any) -> str:
    """Put the cards of the projects in place of the marker, in the language of the
    page's file, which the i18n plugin sets: a page that a further language shows in
    the default one gets its cards in the default one too."""
    catalog: Catalog = config.extra["catalog"]
    locale = getattr(page.file, "locale", None)
    language = locale if locale in catalog.languages else catalog.default
    return MARKER_LINE.sub(lambda _: cards(catalog, language), markdown)


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

    Its preview card for shared links gets the title of the page too: the social
    plugin of Material gives the home page the bare name of the website, while the
    German one, which Material doesn't count as the home page, has the title of its
    front matter already.
    """
    if page.file.dest_uri != HOME:
        return output
    title = page.meta.get("title")
    if title:
        content = escape(f"{title} - {config.site_name}")
        output = SOCIAL_TITLE.sub(lambda tag: f"{tag[1]}{content}{tag[2]}", output)
    head = structured_data(config.extra["catalog"], config.site_url, config.site_name)
    return output.replace("</head>", f"{head}</head>", 1)


def on_post_build(config: Any) -> None:
    """Write robots.txt and security.txt at the root of the address, and lead the
    sitemaps to its root for the home page of the default language.

    The i18n plugin builds every further language into the same folder after the
    default one, and each build writes the same files again.
    """
    catalog: Catalog = config.extra["catalog"]
    site = Path(config.site_dir)
    files = dict.fromkeys(
        SECURITY_TXT, security_txt(catalog, config.site_url, build_date())
    )
    files["robots.txt"] = robots(catalog, config.site_url)
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


# The script.


def main(argv: list[str] | None = None, root: Path = ROOT) -> int:
    """Write or check the table of the projects in README.md."""
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            # The console of Windows may lack a character of the README.
            stream.reconfigure(errors="backslashreplace")
    parser = argparse.ArgumentParser(
        description=f"Write or check the table of the projects in {README}, "
        f"from {CATALOG}."
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
    arguments = parser.parse_args(argv)
    path = root / README
    try:
        catalog = load(root)
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
