"""The hooks of this website, beside those that every website shares in
.github/mkdocs_blueprint.py; mkdocs.yml names both files.

projects.toml, at the root of the repository, lists every project once: its name,
its texts and its links in each language of the website. From it, the hooks put the
cards of the projects into the home page, in the language of the page, and give the
templates the whole list as config.extra["catalog"]. Run as a script, with nothing
but the standard library, this file writes the table of the projects in README.md,
or checks that the table is current, as scripts/check-project.sh does:

    python3 -I .github/mkdocs_project.py --write
    python3 -I .github/mkdocs_project.py --check

While MkDocs builds the website, the hooks also warn, which fails the strict build of
the check docs, about a title of the menu without its translation and a page without
its translation.
"""

from __future__ import annotations

import argparse
import difflib
import io
import logging
import re
import sys
import tomllib
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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
    icon: str
    name: dict[str, str]
    tagline: dict[str, str]
    summary: dict[str, str]
    start: Link
    docs: Link | None


@dataclass(frozen=True)
class Catalog:
    """The projects of projects.toml, with the languages of their texts."""

    languages: tuple[str, ...]
    projects: tuple[Project, ...]

    @property
    def default(self) -> str:
        """The language of the README, the first of the catalog."""
        return self.languages[0]


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
        repo = None
        if "repo" in table:
            repo = self.text(table["repo"], owner, "repo", REPO)
        icon = self.text(table.get("icon"), owner, "icon", ICON)
        name = self.texts(table.get("name"), owner, "name")
        tagline = self.texts(table.get("tagline"), owner, "tagline")
        summary = self.texts(table.get("summary"), owner, "summary")
        start = self.link(table.get("start"), owner, "start")
        docs = None
        if "docs" in table:
            url = self.urls(table["docs"], owner, "docs")
            docs = Link(documentation.icon, documentation.label, url)
        return Project(slug, repo, icon, name, tagline, summary, start, docs)


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
