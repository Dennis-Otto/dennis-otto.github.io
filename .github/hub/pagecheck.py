"""The check of the pages of the built website that the hooks write from projects.toml
and the releases of every project, which sitecheck runs with the rest of its check: the
cards of both home pages with their pictures and their old anchors, the structured data
of the home page of the default language, the Releases pages with the place of the
releases of every project and the link to its feed, and the feed of the releases of
every project in the head of each home page and Releases page.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin

from .built import ADDRESS, EVENTS, RELEASES, RENDER, Built, built
from .catalog import CATALOG, GITHUB, HOME, SITE, Catalog
from .releases import (
    FEED,
    FEED_PAGES,
    FEED_TYPE,
    NEWER,
    NOTES_MARKER,
    RELEASES_PAGE,
    UNREAD,
)
from .render import ATOM, EAGER, MARKER

JSON_LD = "application/ld+json"


@dataclass(frozen=True)
class Finding:
    """A promise of the hooks that the built website breaks: the path of the file in
    the folder of the website, and what is wrong with it, with the fix. A warning is
    what the build left out for a while, such as the releases that the API of GitHub
    refused it, which fails no check."""

    path: str
    message: str
    warning: bool = False


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
                f"projects with a group of {CATALOG}: cards() of {RENDER} writes them "
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
                    f"#{project.slug}: card() of {RENDER} writes one for every project "
                    f"with a group of {CATALOG}"
                )
            messages += [
                f"lacks the anchor #{folder}, where the card of {project.slug} was "
                f"before, as former of {CATALOG} names it: card() of {RENDER} keeps it "
                "in the heading of the card"
                for folder in project.former
                if folder not in page.ids
            ]
        for project, image in pictured:
            src = image.src[language]
            if src not in pictures:
                messages.append(
                    f"shows no {src}, the picture of the card of {project.slug} in "
                    f"{language}: card() of {RENDER} puts the image of {CATALOG} in "
                    "the language of the page on top of it"
                )
                continue
            if project.group == first and src in lazy:
                messages.append(
                    f"loads {src}, the picture of the card of {project.slug}, only as "
                    "it comes into view, though its group is in view as the page "
                    f"opens: section() of {RENDER} gives the pictures of the first "
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
                    f"on_post_page of {EVENTS} puts that of structured_data() into "
                    "its head"
                )
            elif listed != software:
                messages.append(
                    f"lists {', '.join(listed) or 'no project'} in its JSON-LD, not "
                    f"every project with a repo of {CATALOG} in its order, "
                    f"{', '.join(software)}: structured_data() of {ADDRESS} lists them"
                )
        findings += [Finding(name, message) for message in messages]
    return findings + list(missing.values())


def releases_findings(site: Path, catalog: Catalog) -> list[Finding]:
    """What the Releases pages of the website in site break: each has the place of a
    newer release of every project with a repo, which release_history() writes under
    its heading, and the link to the feed of its releases, and a warning, once, for
    each project whose releases the build couldn't read."""
    repos = list(dict.fromkeys(str(p.repo) for p in catalog.projects if p.repo))
    findings: list[Finding] = []
    warned: set[str] = set()
    for language in catalog.languages:
        name = (
            RELEASES_PAGE
            if language == catalog.default
            else f"{language}/{RELEASES_PAGE}"
        )
        page = built(site, name)
        if page is None:
            findings.append(
                Finding(
                    name,
                    f"is missing, the Releases page in {language}: the i18n plugin "
                    "of mkdocs.yml builds it from docs/releases.md and its "
                    "translations",
                )
            )
            continue
        unread = {
            values["data-repo"]: UNREAD in values
            for values in page.of_repos
            if NEWER in values.get("class", "").split()
        }
        for repo in repos:
            if FEED.format(GITHUB, repo) not in page.links:
                findings.append(
                    Finding(
                        name,
                        f"has no link to the feed {FEED.format(GITHUB, repo)}: "
                        f"release_history() of {RELEASES} writes it below the "
                        "releases of every project with a repo",
                    )
                )
            if repo not in unread:
                findings.append(
                    Finding(
                        name,
                        f"has no place of the releases of {repo}: release_history() "
                        f"of {RELEASES} writes one under the heading of every project "
                        f"with a repo of {CATALOG}, in place of {NOTES_MARKER}",
                    )
                )
            elif unread[repo] and repo not in warned:
                warned.add(repo)
                findings.append(
                    Finding(
                        name,
                        f"has no release notes of {repo}: the API of GitHub refused "
                        "the build its releases or didn't answer, so the page links "
                        "them on GitHub, What's new leaves the project out and its "
                        "card shows no Works with until the next build, the daily one "
                        "of the Catalog workflow at the latest. The summary of the job "
                        "of the build says why: run the job again once the API "
                        "answers",
                        warning=True,
                    )
                )
    return findings


def feed_findings(site: Path, catalog: Catalog) -> list[Finding]:
    """What the home pages and the Releases pages of the website in site break: the
    head of each names the feed of the releases of every project, so that a feed
    reader finds it at the address of the page. A page that is missing is a finding
    of home_findings() or releases_findings()."""
    findings: list[Finding] = []
    for language in catalog.languages:
        for page_name in FEED_PAGES:
            name = (
                page_name if language == catalog.default else f"{language}/{page_name}"
            )
            page = built(site, name)
            if page is None:
                continue
            if not any(
                link.get("type") == FEED_TYPE and link.get("href") == ATOM
                for link in page.alternates
            ):
                findings.append(
                    Finding(
                        name,
                        f"names no feed {ATOM} in its head, so a feed reader finds "
                        f"none at its address: on_post_page of {EVENTS} puts the link "
                        f"of feed_link() of {RELEASES} there",
                    )
                )
    return findings
