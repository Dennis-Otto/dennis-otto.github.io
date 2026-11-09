"""The fix of the catalog bot, and its run. A difference with one correct edit, such
as a German website that appeared or that is gone, or a drawn picture that glows in
another color than the --accent of the social preview of its repository, needs no
person: with --fix, the comparison of bot.py makes the edit in projects.toml, line by
line and with every comment in its place, after it asked the web for each address,
writes the tables of the READMEs, the data of the tests of the 404 script and the links
of the pages of the website anew, and writes the text of a pull request into the file
that --fix names. The bot keeps one pull request from the branch bot/catalog with them,
and the issue marks them:

    python3 -I .github/mkdocs_project.py --network repositories.json --fix pull-request.md
"""

from __future__ import annotations

import json
import re
import sys
import tomllib
from collections.abc import Callable
from dataclasses import dataclass, replace
from functools import cache
from pathlib import Path

from . import web
from .bot import Repository, drift, preview, report, repositories
from .catalog import (
    CATALOG,
    DIFFERS,
    LANGUAGE_NAMES,
    SITE,
    Catalog,
    CatalogError,
    Link,
    Picture,
    Project,
)
from .reader import load, read
from .render import readme, readmes

# The data of the tests of the 404 script, which holds the address of every project.
NOT_FOUND_FIXTURE = "tests/fixtures/not-found-data.json"
# A [[project]] of projects.toml up to the next table, a line of its address in the one
# form that the bot edits, a string alone on its line, and the folder of a website that
# lives right below the address.
PROJECT_BLOCK = re.compile(r"^\[\[project\]\]\n(?:(?!\[).*\n)*", re.MULTILINE)
DOCS_LINE = re.compile(r'^(docs(?:\.[a-z]+)?) = "[^"\\]*"\n', re.MULTILINE)
SITE_FOLDER = re.compile(r"[A-Za-z0-9._-]+/")
# The line of the light of a drawn picture in the one form that the bot edits.
ACCENT_LINE = re.compile(r'^drawing\.accent = "#[0-9a-f]{6}"\n', re.MULTILINE)


@dataclass(frozen=True)
class Edit:
    """The one correct edit of the catalog for a project: the address of its website
    in every language before, and its button to the documentation after."""

    slug: str
    before: dict[str, str]
    docs: Link

    @property
    def after(self) -> dict[str, str]:
        """The address of the website in every language after the edit."""
        return self.docs.url


def website_moved(
    old: str, repository: Repository | None, probe: Callable[[str], int]
) -> str | None:
    """Where the website at old lives now, for a repository that names another folder
    of SITE as its website: there, when that folder answers and old is gone. With two
    websites that answer, only a person knows which of them the project means, and a
    page deeper in a folder is no website that the catalog could lead to."""
    if repository is None or not web.at_site(repository.homepage):
        return None
    new = web.address(repository.homepage)
    if (
        new == web.address(old)
        or not SITE_FOLDER.fullmatch(new.removeprefix(SITE))
        or not web.exists(probe, new)
        or web.exists(probe, web.address(old))
    ):
        return None
    return new


def wanted_docs(
    catalog: Catalog,
    project: Project,
    found: dict[str, Repository],
    probe: Callable[[str], int],
) -> Edit | None:
    """The edit of the address of the website of project in every language that the
    web asks for, which probe answers, or None when it asks for none or when only a
    person can tell.

    The bot edits only a project whose website is at SITE, and leaves one to a person
    whose repository is gone, private or archived: a repository that was renamed takes
    its website along, so its German website only looks gone. A German website is gone
    only beside an English one that answers: when both are away, the website is.
    """
    if project.docs is None or not web.at_site(project.docs.url[catalog.default]):
        return None
    repository = None
    if project.repo is not None:
        repository = found.get(project.repo.lower())
        if repository is None or repository.private or repository.archived:
            return None
    urls = project.docs.url
    old = urls[catalog.default]
    moved = website_moved(old, repository, probe)
    first = moved or old
    after = {catalog.default: first}
    for language in catalog.languages[1:]:
        own = urls[language]
        folder = f"{web.address(first)}{language}/"
        if own == old or (moved and own == f"{web.address(old)}{language}/"):
            after[language] = folder if web.exists(probe, folder) else first
        elif web.exists(probe, own):
            after[language] = own
        elif web.exists(probe, first):
            after[language] = first
        else:
            return None
    if after == urls:
        return None
    return Edit(project.slug, urls, replace(project.docs, url=after))


def in_turn(pattern: re.Pattern[str], text: str, lines: list[str]) -> str:
    """text with each match of pattern replaced by the next of lines, in turn."""
    written = iter(lines)
    return pattern.sub(lambda _: next(written), text)


def with_docs(text: str, edit: Edit, languages: tuple[str, ...]) -> str | None:
    """text, that of CATALOG, with the lines of the address of the project of edit
    written anew and every other line as it is: one line when every language has the
    same address, or else one for the first language and one for each with an address
    of its own. A key that stays keeps its line, and a new one goes in the place of the
    first. None for a project whose address has another form, such as a comment on its
    line, which only a person can keep."""
    first = edit.after[languages[0]]
    own = [code for code in languages[1:] if edit.after[code] != first]
    wanted = {"docs": first}
    if own:
        wanted = {f"docs.{code}": edit.after[code] for code in (languages[0], *own)}
    for match in PROJECT_BLOCK.finditer(text):
        keys = DOCS_LINE.findall(match[0])
        if f'\nslug = "{edit.slug}"\n' in match[0] and keys:
            lines = [
                f'{key} = "{wanted[key]}"\n' if key in wanted else "" for key in keys
            ]
            lines[0] = "".join(
                f'{key} = "{wanted[key]}"\n' for key in wanted if key not in keys[1:]
            )
            block = in_turn(DOCS_LINE, match[0], lines)
            return f"{text[: match.start()]}{block}{text[match.end() :]}"
    return None


@dataclass(frozen=True)
class Accent:
    """The one correct edit of the light behind the screenshot of the pictures that
    the hub draws of the card of a project: its accent before, the one accent that the
    social preview of its repository names after, and its picture with that light."""

    slug: str
    before: str
    after: str
    picture: Picture


def wanted_accent(
    project: Project,
    found: dict[str, Repository],
    fetch: Callable[[str], bytes | None],
) -> Accent | None:
    """The edit of the light of the drawn pictures of project that the social preview
    of its repository, which fetch reads, asks for, or None when it asks for none or
    when only a person can tell.

    The preview settles it only when it names one accent, once or more often: one
    without an accent of its own, or with two, such as one for each color scheme,
    leaves the choice among its colors to a person, and so does a repository that is
    gone, private or archived, as in wanted_docs.
    """
    image = project.picture
    if image is None or image.drawing is None:
        return None
    repository = found.get(project.repo.lower()) if project.repo else None
    if repository is None or repository.private or repository.archived:
        return None
    before = image.drawing.accent
    seen = preview(project, fetch)
    if seen is None or before in seen.colors or len(set(seen.accents)) != 1:
        return None
    after = seen.accents[0]
    drawing = replace(image.drawing, accent=after)
    return Accent(project.slug, before, after, replace(image, drawing=drawing))


def with_accent(text: str, edit: Accent) -> str | None:
    """text, that of CATALOG, with the line of the light of the project of edit
    written anew and every other line as it is. None for a project whose light has
    another form, such as a comment on its line, which only a person can keep."""
    for match in PROJECT_BLOCK.finditer(text):
        block, count = ACCENT_LINE.subn(f'drawing.accent = "{edit.after}"\n', match[0])
        if f'\nslug = "{edit.slug}"\n' in match[0] and count == 1:
            return f"{text[: match.start()]}{block}{text[match.end() :]}"
    return None


def reads_back(text: str, catalog: Catalog) -> bool:
    """Whether text, that of CATALOG, is catalog and nothing else, so that an edit
    can't change what it doesn't mean to, nor make the file invalid, such as with an
    address in a folder that former of the project names."""
    try:
        written = read(tomllib.loads(text))
    except (tomllib.TOMLDecodeError, CatalogError):
        return False
    return replace(written, former_pages=catalog.former_pages) == catalog


def pull_request_text(
    catalog: Catalog, edits: list[Edit], accents: list[Accent]
) -> str:
    """The text of the pull request of the bot, with what each of edits and accents
    changes and what follows them, and what a person adds to an edit that moved a
    website: the folder that it left, for the readers who still come there, and the
    tests that name it."""
    repos = {project.slug: project.repo for project in catalog.projects}
    changes = []
    moves = []
    for edit in edits:
        for language in catalog.languages:
            name = LANGUAGE_NAMES.get(language, language)
            before, after = edit.before[language], edit.after[language]
            if before != after:
                changes.append(
                    f"- `{edit.slug}`: the {name} home page leads to {after} now, "
                    f"not to {before}."
                )
        old, new = edit.before[catalog.default], edit.after[catalog.default]
        if old != new:
            moves.append(
                f"- `{edit.slug}`: readers who still come to {old} find nothing. To "
                "lead them along, name its folder in `former` and its pages in "
                "`former/<folder>.txt`. The tests that name its folder fail until "
                "they name the new one. Push both onto this branch: the bot leaves a "
                "pull request with a commit of a person alone."
            )
    changes += [
        f"- `{accent.slug}`: the pictures that the hub draws of its card glow in "
        f"{accent.after} now, the `--accent` of the social preview of "
        f"{repos[accent.slug]}, not {accent.before}."
        for accent in accents
    ]
    asked = [
        "The bot asked the web first: each new address answers 200, and each one "
        "that it took away answers 404 or 410. The tables of the READMEs, the "
        f"links of the pages of the website and `{NOT_FOUND_FIXTURE}` follow.",
        "",
    ]
    # A new light changes no other file of the repository: projects.toml is among
    # the files of .github/screenshots-paths.txt, whose change on main starts the
    # screenshot bot, which draws the pictures anew in its own pull request.
    redrawn = [
        "The screenshot bot draws those pictures anew in their new light once this "
        f"pull request is merged: a change of {CATALOG} on `main` starts it.",
        "",
    ]
    return "\n".join(
        [
            f"The catalog bot compared {CATALOG} with the websites of the projects and "
            "with the social previews of their repositories, and found differences "
            "with one correct edit, which it makes here:",
            "",
            *changes,
            "",
            *(asked if edits else []),
            *([*moves, ""] if moves else []),
            *(redrawn if accents else []),
        ]
    )


def relinked(text: str, edits: list[Edit], language: str) -> str:
    """text, that of a page in language, with each link to a website of edits leading
    where the edit leads the website in language now."""
    for edit in edits:
        text = text.replace(f"]({edit.before[language]})", f"]({edit.after[language]})")
    return text


def healed_files(
    root: Path, catalog: Catalog, text: str, edits: list[Edit]
) -> dict[str, str]:
    """Every file in the folder root that follows edits, by its path from root, with
    its new content: text, that of CATALOG, the data of the tests of the 404 script, the
    READMEs with their tables, and each page of the website that links a website of
    edits, as the check of the links and a test of the Security page ask."""
    data = {"moves": catalog.moves(), "projects": catalog.directory()}
    files = {
        CATALOG: text,
        NOT_FOUND_FIXTURE: (
            json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        ),
    }
    for language, name in readmes(catalog).items():
        current = (root / name).read_text(encoding="utf-8")
        files[name] = readme(relinked(current, edits, language), catalog, language)
    for page in sorted((root / "docs").glob("*.md")):
        # Such as security.de.md, beside security.md in the first language.
        language = page.suffixes[0].removeprefix(".")
        if language not in catalog.languages:
            language = catalog.default
        current = page.read_text(encoding="utf-8")
        linked = relinked(current, edits, language)
        if linked != current:
            files[page.relative_to(root).as_posix()] = linked
    return files


def changed(catalog: Catalog, project: Project, edited: Project) -> Catalog:
    """catalog with edited in the place of project."""
    return replace(
        catalog,
        projects=tuple(
            edited if other is project else other for other in catalog.projects
        ),
    )


def heal(
    catalog: Catalog,
    found: list[Repository],
    differences: list[str],
    probe: Callable[[str], int],
    fetch: Callable[[str], bytes | None],
    root: Path,
    body: Path,
) -> list[str]:
    """Make the edits with one correct form in the folder root, and write the text of
    their pull request into the file body: which of differences they fix. Whatever
    remains is what the catalog with the edits still differs in. A project whose edit
    can't be made in its file or doesn't read back as meant keeps its difference, for
    a person. The addresses go first and the lights after them, so that one project
    can get both. Every file is made before one is written, so that a README without
    its markers leaves them all as they are."""
    text = (root / CATALOG).read_text(encoding="utf-8")
    by_name = {repository.name.lower(): repository for repository in found}
    edits = []
    for project in catalog.projects:
        edit = wanted_docs(catalog, project, by_name, probe)
        if edit is None:
            continue
        edited = with_docs(text, edit, catalog.languages)
        wanted = changed(catalog, project, replace(project, docs=edit.docs))
        if edited is not None and reads_back(edited, wanted):
            text, catalog = edited, wanted
            edits.append(edit)
    accents = []
    for project in catalog.projects:
        accent = wanted_accent(project, by_name, fetch)
        if accent is None:
            continue
        edited = with_accent(text, accent)
        wanted = changed(catalog, project, replace(project, picture=accent.picture))
        if edited is not None and reads_back(edited, wanted):
            text, catalog = edited, wanted
            accents.append(accent)
    if not edits and not accents:
        return []
    files = healed_files(root, catalog, text, edits)
    remaining = drift(catalog, found, probe, fetch)
    for name, content in files.items():
        (root / name).write_text(content, encoding="utf-8", newline="\n")
    body.write_text(
        pull_request_text(catalog, edits, accents), encoding="utf-8", newline="\n"
    )
    return [difference for difference in differences if difference not in remaining]


def network(path: Path, root: Path, fix: Path | None = None) -> int:
    """Compare the catalog in the folder root with the repositories in path, the
    JSON of gh repo list, and with the websites of the projects: 0 when the catalog
    is current, DIFFERS with the text of the issue on stdout, 2 when the bot can't
    tell. With fix, the differences with one correct edit are fixed in root, and the
    file fix holds the text of the pull request with the edits, if there are any."""
    fixed: list[str] = []
    try:
        catalog = load(root)
        found = repositories(path.read_text(encoding="utf-8"))
        # Each address is asked once in a run, so that the comparison of the catalog
        # with the edits sees the web that the first one saw.
        probe, fetch = cache(web.status), cache(web.fetched)
        differences = drift(catalog, found, probe, fetch)
        if differences and fix is not None:
            fixed = heal(catalog, found, differences, probe, fetch, root, fix)
    except (CatalogError, web.CheckError, OSError) as error:
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
    sys.stdout.write(report(differences, fixed))
    return DIFFERS
