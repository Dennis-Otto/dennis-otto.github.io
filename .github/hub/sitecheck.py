"""The check of the built website. The tests of the hooks fake MkDocs and its
plugins. So after the real build, the check docs runs scripts/check-site.sh with the
folder of the website, which checks there what the hooks promise in the files that they
alone write or change after the build, so that a new version of Material or of
mkdocs-static-i18n that changes the order of the plugins or their files fails the check
before the website is published: both copies of security.txt, with what RFC 9116 asks
and a policy that is a page of the website, robots.txt with every sitemap once, llms.txt
with every group and project as https://llmstxt.org/ asks, the sitemaps with the root of
the address and the dates of the pages with releases, a page at every old address that
leads to its page now, the 404 page with the old folders, the cards of both home pages
with their pictures and their old anchors, the structured data, the Releases pages with
the releases of every project, and the search index with the pages of this website,
their boosts and the entries of the projects. It warns of the releases of a project
that the build couldn't read, which fails nothing, as the next build brings them.
"""

from __future__ import annotations

import gzip
import itertools
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from . import web
from .address import (
    LLMS_TXT,
    OWNER,
    ROBOTS,
    SECURITY_TXT,
    SITEMAP,
    VALID,
    home_address,
    moved_to,
    one_line,
    sitemaps,
)
from .built import (
    ADDRESS,
    EVENTS,
    HOOKS,
    LOCATION,
    RELEASES,
    RENDER,
    SEARCH,
    Built,
    built,
    dated_before_releases,
    page_at,
    text_fields,
)
from .catalog import CATALOG, FORMER, HOME, SITE, Catalog, CatalogError
from .reader import load
from .releases import NEWER, NOTES_MARKER, RELEASES_PAGE, UNREAD
from .render import EAGER, MARKER
from .search import DECISIONS, SEARCH_INDEX, SEPARATOR, boost_of, documents, websites

# What the annotations of the CI call a finding of the check, and a warning of it.
PROMISES = "What the hooks of the hub promise"
LEFT_OUT = "What the build of the hub left out"
NOT_FOUND = "404.html"

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


@dataclass(frozen=True)
class Finding:
    """A promise of the hooks that the built website breaks: the path of the file in
    the folder of the website, and what is wrong with it, with the fix. A warning is
    what the build left out for a while, such as the releases that the API of GitHub
    refused it, which fails no check."""

    path: str
    message: str
    warning: bool = False


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
            f"such as 2027-10-24T00:00:00Z: security_txt() of {ADDRESS} writes one"
        ]
    if moment <= now:
        return [
            f"expired at {value}: security_txt() of {ADDRESS} writes the midnight a "
            "year after the day of the build, so build the website again, with no "
            "SOURCE_DATE_EPOCH or one of today"
        ]
    if moment - now > VALID:
        return [
            f"expires at {value}, more than {VALID.days} days from now, where RFC "
            f"9116 recommends less than a year: keep VALID of {ADDRESS} at "
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
            f"has no Contact, which RFC 9116 requires: security_txt() of {ADDRESS} "
            "writes CONTACT"
        )
    messages += [
        f"names Contact: {contact}, which is no https://, mailto: or tel: address of "
        f"RFC 9116: set CONTACT of {ADDRESS} to the form for private reports"
        for contact in contacts
        if not contact.startswith(CONTACTS)
    ]
    expires = values.get("expires", [])
    if len(expires) == 1:
        messages += expiry(expires[0], now)
    else:
        messages.append(
            f"has {len(expires)} Expires, where RFC 9116 asks for exactly one: "
            f"security_txt() of {ADDRESS} writes one"
        )
    canonical = values.get("canonical", [])
    messages += [
        f"names no Canonical: {urljoin(SITE, path)}, the address of its copy at "
        f"{path}: security_txt() of {ADDRESS} names every path of SECURITY_TXT"
        for path in SECURITY_TXT
        if urljoin(SITE, path) not in canonical
    ]
    policies = values.get("policy", [])
    if not policies:
        messages.append(
            f"has no Policy, the security page of the address: security_txt() of "
            f"{ADDRESS} names POLICY"
        )
    for policy in policies:
        page = page_at(site, policy)
        if page is None or not page.is_file():
            messages.append(
                f"names Policy: {policy}, which is no page of the website: keep "
                f"docs/security.md, or change POLICY of {ADDRESS}"
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
                    f"is missing: on_post_build of {EVENTS} writes it after the build, "
                    f"so check that hooks of mkdocs.yml names {HOOKS}",
                )
            )
    if len(set(texts.values())) > 1:
        first, second = SECURITY_TXT
        findings.append(
            Finding(
                first,
                f"differs from {second}: on_post_build of {EVENTS} writes the same "
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
                f"is missing: on_post_build of {EVENTS} writes it after the build, so "
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
                    f"names no Sitemap: {url}: robots() of {ADDRESS} names the sitemap "
                    f"of this website and of every project of {CATALOG} whose docs "
                    f"are at {SITE}",
                )
            )
        elif count > 1:
            findings.append(
                Finding(
                    ROBOTS,
                    f"names Sitemap: {url} {count} times: robots() of {ADDRESS} names "
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
                f"is missing: on_post_build of {EVENTS} writes it after the build, so "
                f"check that hooks of mkdocs.yml names {HOOKS}",
            )
        ]
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    messages: list[str] = []
    if not lines or lines[0] != f"# {OWNER}":
        messages.append(
            f"doesn't start with the title # {OWNER}, which https://llmstxt.org/ "
            f"asks for: llms_txt() of {ADDRESS} writes it on the first line"
        )
    sections = list(itertools.dropwhile(lambda line: not line.startswith("## "), lines))
    strays = [
        line
        for line in sections
        if line and not line.startswith("## ") and not LLMS_ITEM.fullmatch(line)
    ]
    if strays:
        messages.append(
            f"has {len(strays)} line(s) in its sections that are no item of a list "
            f"with a link, such as {strays[0]!r}, where https://llmstxt.org/ asks "
            f"for lists of links alone: llms_item() of {ADDRESS} writes each item"
        )
    headings = {line[3:] for line in sections if line.startswith("## ")}
    for group in catalog.groups:
        heading = one_line(group.heading[catalog.default])
        if heading not in headings:
            messages.append(
                f"has no section ## {heading}: llms_txt() of {ADDRESS} writes one for "
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
                    f"doesn't link {url} of {project.slug}: llms_txt() of {ADDRESS} "
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
            f"{missing[0]}: change llms_txt() of {ADDRESS}, or keep the page"
        )
    records = [url for url in urls if DECISIONS in urlsplit(url).path.split("/")]
    if records:
        messages.append(
            f"links {len(records)} decision record(s), such as {records[0]}, which "
            f"are for maintainers: guides() of {SEARCH} takes the pages of "
            "START_PAGES alone"
        )
    return [Finding(LLMS_TXT, message) for message in messages]


def sitemap_findings(site: Path) -> list[Finding]:
    """What the sitemaps of the website in site break: none names the home page of
    the default language as index.html in place of the root of the address, and none
    dates a page before the newest release that it shows."""
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
    findings = [
        Finding(
            name,
            f"names {urljoin(SITE, HOME)} in place of {SITE}, the canonical address "
            f"of the home page: sitemaps_at_root() of {ADDRESS} leads it to the root "
            "after the build",
        )
        for name, text in texts.items()
        if home.search(text)
    ]
    return findings + [
        Finding(
            name,
            f"dates {url} {changed}, before {day}, the day of the newest release that "
            f"the page shows: redate() of {RELEASES} dates it by the releases of the "
            "build in on_page_content, after the hooks that date a page by its Markdown",
        )
        for name, text in texts.items()
        for url, changed, day in dated_before_releases(site, text)
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
                        f"on_post_build of {EVENTS} writes a page there that leads to "
                        f"{target}",
                    )
                )
            elif found.canonical != [target] or found.refresh != [f"0; url={target}"]:
                findings.append(
                    Finding(
                        name,
                        f"doesn't lead to {target}, the same page in the folder of the "
                        "website now, with its canonical address and its refresh: "
                        f"moved_page() of {ADDRESS} writes both, so remove what writes "
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
                f"on_post_build of {EVENTS} adds the project websites to it",
            )
        ]
    try:
        docs = documents(path.read_bytes(), SEARCH_INDEX)
    except web.SearchError as error:
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
            f"lists, such as {lost[0]}: add_to_search() of {SEARCH} keeps the entries "
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
            f"add_to_search() of {SEARCH} gives them that of their page after the "
            "search plugin has written the index, so something wrote it again after "
            "on_post_build, which must come last, as check_order() makes sure"
        )
    if folders and len(own) == len(docs):
        messages.append(
            f"has no entry of the {len(folders)} project websites at {SITE}: "
            f"on_post_build of {EVENTS} adds them after the build. When the log of the "
            "build says that the search leaves out every website, GitHub Pages was "
            "away while it ran: run the job again"
        )
    strays = [doc["location"] for doc in own if SEPARATOR in doc["title"]]
    if strays:
        messages.append(
            f"has {len(strays)} entries of a project outside the folder of its "
            f"website, such as {strays[0]}: entries() of {SEARCH} puts every location "
            "into the folder of its website"
        )
    return [Finding(SEARCH_INDEX, message) for message in messages]


def releases_findings(site: Path, catalog: Catalog) -> list[Finding]:
    """What the Releases pages of the website in site break: each has the place of a
    newer release of every project with a repo, which release_history() writes under
    its heading, and a warning, once, for each project whose releases the build
    couldn't read."""
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


def check_site(site: Path, catalog: Catalog, now: datetime) -> list[Finding]:
    """Every promise of the hooks of this website that the website MkDocs built in
    site breaks at the moment now, in the files that the hooks alone write or change
    after the build: security.txt, robots.txt, llms.txt, the sitemaps, the old
    addresses, the 404 page, the home pages, the Releases pages and the search
    index."""
    return [
        *security_findings(site, now),
        *robots_findings(site, catalog),
        *llms_findings(site, catalog),
        *sitemap_findings(site),
        *moved_findings(site, catalog),
        *not_found_findings(site, catalog),
        *home_findings(site, catalog),
        *releases_findings(site, catalog),
        *search_findings(site, catalog),
    ]


def annotation(finding: Finding, folder: str) -> str:
    """The finding as an annotation of the CI, which the summary of the check shows,
    with its path in folder, where MkDocs built the website: an error, or a warning
    for what the build left out for a while."""
    message = f"{folder}/{finding.path}: {finding.message}"
    for sign, code in (("%", "%25"), ("\r", "%0D"), ("\n", "%0A")):
        message = message.replace(sign, code)
    if finding.warning:
        return f"::warning title={LEFT_OUT}::{message}"
    return f"::error title={PROMISES}::{message}"


def site_check(site: Path, root: Path) -> int:
    """Check the website that MkDocs built in site against the catalog in the folder
    root: 0 when it keeps every promise of the hooks, 1 with a line for each that it
    breaks, and in the CI an annotation too. A warning, what the build left out for
    a while, gets its line and its annotation and fails nothing."""
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
    for finding in findings:
        print(f"{folder}/{finding.path}: {finding.message}")
    if os.environ.get("GITHUB_ACTIONS") == "true":
        for finding in findings:
            print(annotation(finding, folder))
    broken = [finding for finding in findings if not finding.warning]
    if not broken:
        print(
            f"The website in {folder} keeps what the hooks of {HOOKS} promise: "
            "security.txt, robots.txt, llms.txt, the sitemaps, the old addresses, the "
            "404 page, the home pages, the Releases pages and the search."
        )
        return 0
    print(
        f"{len(broken)} finding(s): the website breaks what the hooks of {HOOKS} "
        "promise. A new version of Material or of mkdocs-static-i18n that writes its "
        f"files differently, or a change of the hooks, of {CATALOG} or of overrides/, "
        "broke it: fix what each line names, build the website again and check its "
        "folder with bash scripts/check-site.sh site."
    )
    return 1
