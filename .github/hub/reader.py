"""Reads projects.toml into the data classes of catalog.py. The reader goes on
after a problem and names every one of them with its place, so that one run of the build
or of the script shows everything to fix at once.
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import field, replace
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urljoin

from .catalog import (
    ACCENT,
    ASSET,
    CARD_KEYS,
    CATALOG,
    Catalog,
    CatalogError,
    DRAWING_KEYS,
    Drawing,
    FACT_KEYS,
    FIELD_FORMS,
    FIELD_NAME,
    FORMER,
    Form,
    GROUP_KEYS,
    Group,
    ICON,
    IMAGE,
    LANGUAGE,
    LICENSE,
    LOGO,
    Link,
    PAGE,
    PLACEHOLDER,
    PROJECT_KEYS,
    Picture,
    Project,
    REPO,
    REQUIREMENTS,
    ROOT,
    ROW_KEYS,
    SCREENSHOT,
    SITE,
    SLUG,
    SOURCE,
    SOURCE_KEYS,
    Source,
    TRUST,
    TRUST_KEYS,
    TRUST_LINKED,
    TRUST_VALUED,
    Trust,
    URL,
    VALUED,
    drawn,
    join,
)


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
                    (
                        "is for a project with a repo whose image has a file of its own "
                        "in a language after the first, such as image.de"
                        if "repo" in table
                        else "is for a project with a repo"
                    ),
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
