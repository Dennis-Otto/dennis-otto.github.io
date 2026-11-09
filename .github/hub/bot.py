"""The catalog bot, .github/workflows/catalog.yml. Every week it compares the catalog
with the repositories of its owner on GitHub, which gh writes into a file, with the
websites of the projects in every language, and with the files that say what they work
with and from which the hub draws their pictures on the default branch of each, and
keeps an issue with what differs:

    gh repo list Dennis-Otto --limit 1000 \\
      --json nameWithOwner,homepageUrl,isArchived,isPrivate >repositories.json
    python3 -I .github/mkdocs_project.py --network repositories.json

The run, with the edits that it makes itself, is in fix.py.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Collection
from dataclasses import dataclass

from . import web
from .catalog import CATALOG, LANGUAGE_NAMES, Catalog, Project, Source
from .render import WRITE
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


@dataclass(frozen=True)
class Preview:
    """The colors of the social preview of a repository, in lowercase: every color of
    its source, and those that it names its accent, in their order."""

    colors: frozenset[str]
    accents: tuple[str, ...]


def preview(project: Project, fetch: Callable[[str], bytes | None]) -> Preview | None:
    """The colors of the social preview of the repository of project on its default
    branch, which fetch reads, or None for a repository without its source."""
    content = fetch(web.RAW.format(project.repo, web.DEFAULT_BRANCH, PREVIEW))
    if content is None:
        return None
    page = content.decode("utf-8", "replace")
    return Preview(
        frozenset(color.lower() for color in COLOR.findall(page)),
        tuple(color.lower() for color in PREVIEW_ACCENT.findall(page)),
    )


def accent_drift(
    project: Project, accent: str, fetch: Callable[[str], bytes | None]
) -> list[str]:
    """What differs between accent, the light behind the screenshot of the picture
    that the hub draws of the card of project, and the social preview of its
    repository on the default branch, which fetch reads: its source has no color
    of that accent, so the drawn picture glows in another color than the picture of
    the first language, which is that preview. A repository without that source
    has no colors to compare."""
    seen = preview(project, fetch)
    if seen is None or accent in seen.colors:
        return []
    such_as = f", such as {seen.accents[0]}, its `--accent`" if seen.accents else ""
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
