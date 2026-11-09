"""The catalog bot, .github/workflows/catalog.yml. Every week it compares the catalog
with the repositories of its owner on GitHub, which gh writes into a file, with the
websites of the projects in every language, and with the files that say what they work
with and from which the hub draws their pictures on the default branch of each, and
keeps an issue with what differs:

    gh repo list Dennis-Otto --limit 1000 \\
      --json nameWithOwner,homepageUrl,isArchived,isPrivate >repositories.json
    python3 -I .github/mkdocs_project.py --network repositories.json

A difference with one correct edit, such as a German website that appeared or that is
gone, needs no person: with --fix, the comparison makes the edit in projects.toml, line
by line and with every comment in its place, after it asked the web for each address,
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
from collections.abc import Callable, Collection
from dataclasses import dataclass, replace
from functools import cache
from pathlib import Path

from . import web
from .catalog import (
    CATALOG,
    DIFFERS,
    LANGUAGE_NAMES,
    SITE,
    Catalog,
    CatalogError,
    Link,
    Project,
    Source,
)
from .reader import load, read
from .render import WRITE, readme, readmes
from .requirements import RequirementError, values_in

# The fields of gh repo list that the catalog bot reads.
FIELDS = ("nameWithOwner", "homepageUrl", "isArchived", "isPrivate")

# What the bot fixes itself: the command that makes the edits, the branch of its pull
# request, and what the issue says after each difference that the edits fix.
FIX = (
    "python3 -I .github/mkdocs_project.py --network repositories.json "
    "--fix pull-request.md"
)
FIX_BRANCH = "bot/catalog"
FIXED = "*The bot makes this edit.*"
# The data of the tests of the 404 script, which holds the address of every project.
NOT_FOUND_FIXTURE = "tests/fixtures/not-found-data.json"
# A [[project]] of projects.toml up to the next table, a line of its address in the one
# form that the bot edits, a string alone on its line, and the folder of a website that
# lives right below the address.
PROJECT_BLOCK = re.compile(r"^\[\[project\]\]\n(?:(?!\[).*\n)*", re.MULTILINE)
DOCS_LINE = re.compile(r'^(docs(?:\.[a-z]+)?) = "[^"\\]*"\n', re.MULTILINE)
SITE_FOLDER = re.compile(r"[A-Za-z0-9._-]+/")
# The source of the social preview of a repository, whose colors the light behind the
# screenshot of a drawn picture takes, each color of six hexadecimal digits in it,
# and the one that it names its accent, such as --accent: #8ea2ff.
PREVIEW = ".github/social-preview.html"
COLOR = re.compile(r"#[0-9a-f]{6}", re.IGNORECASE)
PREVIEW_ACCENT = re.compile(r"--accent:\s*(#[0-9a-f]{6})", re.IGNORECASE)


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
        raise web.CheckError(
            f"The list of the repositories isn't {wanted}: {error}"
        ) from error
    # An empty list is one that went wrong, not an owner without repositories, and
    # would report every project of the catalog as gone.
    if not isinstance(data, list) or not data or not all(map(listed, data)):
        raise web.CheckError(
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
        successor = websites.get(web.address(website))
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
    if web.at_site(homepage) and web.address(homepage) != web.address(website):
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
    if not web.at_site(first):
        return []
    differences = []
    default = LANGUAGE_NAMES.get(catalog.default, catalog.default)
    for language in catalog.languages[1:]:
        name = LANGUAGE_NAMES.get(language, language)
        if urls[language] != first:
            if not web.exists(probe, urls[language]):
                differences.append(
                    f"`{slug}`: the {name} website {urls[language]} is gone. Remove "
                    f"`docs.{language}`, so that the {name} home page leads to the "
                    f"{default} one."
                )
        elif web.exists(probe, url := f"{web.address(first)}{language}/"):
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
    content = fetch(web.RAW.format(repo, web.DEFAULT_BRANCH, file))
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


def drawing_drift(project: Project, fetch: Callable[[str], bytes | None]) -> list[str]:
    """What the default branch of the repository of project, which fetch reads,
    lacks of the files from which the hub draws pictures of its card: a screenshot
    or its logo that is gone, which would stop scripts/project-pictures.sh, and the
    accent of the drawing among the colors of its social preview."""
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
        if fetch(web.RAW.format(project.repo, web.DEFAULT_BRANCH, file)) is None
    ] + accent_drift(project, image.drawing.accent, fetch)


def accent_drift(
    project: Project, accent: str, fetch: Callable[[str], bytes | None]
) -> list[str]:
    """What differs between accent, the light behind the screenshot of the picture
    that the hub draws of the card of project, and the social preview of its
    repository on the default branch, which fetch reads: its source has no color
    of that accent, so the drawn picture glows in another color than the picture of
    the first language, which is that preview. A repository without that source
    has no colors to compare."""
    content = fetch(web.RAW.format(project.repo, web.DEFAULT_BRANCH, PREVIEW))
    if content is None:
        return []
    page = content.decode("utf-8", "replace")
    if accent in {color.lower() for color in COLOR.findall(page)}:
        return []
    named = PREVIEW_ACCENT.search(page)
    such_as = f", such as {named[1].lower()}, its `--accent`" if named else ""
    return [
        f"`{project.slug}`: the social preview of {project.repo}, {PREVIEW}, has no "
        f"color {accent}, the light behind the screenshot of the picture that the "
        "hub draws of its card, which glows in another color than its preview. Set "
        f"`drawing.accent` to the color of its social preview{such_as}."
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
    pictures in the colors of their social previews, which fetch reads: one
    sentence of Markdown each, in the order of the catalog, and then every public
    repository with a website at SITE that no project names.

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
            and web.at_site(repository.homepage)
        ),
        key=lambda repository: repository.name.lower(),
    )
    websites: dict[str, Repository] = {}
    for repository in published:
        websites.setdefault(web.address(repository.homepage), repository)
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
    shown = {
        web.address(project.website[catalog.default]) for project in catalog.projects
    }
    differences += [
        f"{repository.name} has its website at {repository.homepage}, but {CATALOG} "
        f'has no project for it. Add a `[[project]]` with `repo = "{repository.name}"`.'
        for repository in published
        if repository.name.lower() not in named
        and web.address(repository.homepage) not in shown
    ]
    return differences


def report(differences: list[str], fixed: Collection[str] = ()) -> str:
    """The text of the issue of the catalog bot, in Markdown, with differences, of
    which fixed are those that the edits of the bot fix; each of those says so."""
    pull_request = [
        "The bot keeps the edits that this list marks in one pull request from the "
        f"branch `{FIX_BRANCH}`. Without the pull request, make them as the list "
        f"says, or with `{FIX}`.",
        "",
    ]
    return "\n".join(
        [
            f"The catalog bot compares {CATALOG} with the repositories on GitHub, "
            "with the websites of the projects in every language and with the files "
            "that say what they work with every week, and found "
            f"{len(differences)} difference(s):",
            "",
            *(
                f"- {difference} {FIXED}" if difference in fixed else f"- {difference}"
                for difference in differences
            ),
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
            *(pull_request if fixed else []),
        ]
    )


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


def reads_back(text: str, catalog: Catalog) -> bool:
    """Whether text, that of CATALOG, is catalog and nothing else, so that an edit
    can't change what it doesn't mean to, nor make the file invalid, such as with an
    address in a folder that former of the project names."""
    try:
        written = read(tomllib.loads(text))
    except (tomllib.TOMLDecodeError, CatalogError):
        return False
    return replace(written, former_pages=catalog.former_pages) == catalog


def pull_request_text(catalog: Catalog, edits: list[Edit]) -> str:
    """The text of the pull request of the bot, with what each of edits changes, and
    what a person adds to one that moved a website: the folder that it left, for the
    readers who still come there, and the tests that name it."""
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
    return "\n".join(
        [
            f"The catalog bot compared {CATALOG} with the websites of the projects and "
            "found differences with one correct edit, which it makes here:",
            "",
            *changes,
            "",
            "The bot asked the web first: each new address answers 200, and each one "
            "that it took away answers 404 or 410. The tables of the READMEs, the "
            f"links of the pages of the website and `{NOT_FOUND_FIXTURE}` follow.",
            "",
            *([*moves, ""] if moves else []),
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
    a person. Every file is made before one is written, so that a README without its
    markers leaves them all as they are."""
    text = (root / CATALOG).read_text(encoding="utf-8")
    by_name = {repository.name.lower(): repository for repository in found}
    edits = []
    for project in catalog.projects:
        edit = wanted_docs(catalog, project, by_name, probe)
        edited = None if edit is None else with_docs(text, edit, catalog.languages)
        if edit is None or edited is None:
            continue
        wanted = replace(
            catalog,
            projects=tuple(
                replace(other, docs=edit.docs) if other is project else other
                for other in catalog.projects
            ),
        )
        if reads_back(edited, wanted):
            text, catalog = edited, wanted
            edits.append(edit)
    if not edits:
        return []
    files = healed_files(root, catalog, text, edits)
    remaining = drift(catalog, found, probe, fetch)
    for name, content in files.items():
        (root / name).write_text(content, encoding="utf-8", newline="\n")
    body.write_text(pull_request_text(catalog, edits), encoding="utf-8", newline="\n")
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
