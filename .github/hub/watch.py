"""The watch of the catalog bot. Every day the bot also watches what the published
website depends on after its build and nothing else checks: the data of the dashboard,
against the schema and the fields that docs/javascripts/projects.js reads, which
.github/dashboard-fields.json names; the search index of every project website, which
the next build takes into the search; both copies of security.txt, which must hold for
330 days more, robots.txt with every sitemap and the sitemap of this website; and every
old address of former/, which must lead to its page in the new folder, which must
answer. It keeps an issue with what needs attention, and each line says how to fix it:

    python3 -I .github/mkdocs_project.py --watch
"""

from __future__ import annotations

import json
import math
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, NamedTuple, TypeVar
from urllib.parse import urljoin

from . import web
from .address import ROBOTS, SECURITY_TXT, SITEMAP, VALID, moved_to, sitemaps
from .built import ADDRESS, EVENTS, LOCATION, SEARCH, Built, text_fields
from .catalog import CATALOG, DIFFERS, FORMER, GITHUB, SITE, Catalog, CatalogError
from .reader import load
from .render import FEED, HISTORY
from .search import SEARCH_INDEX, documents, websites

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
# How old repos.json of the dashboard may be at the time of the watch: the Dashboard
# workflow of repo-blueprint writes it every two hours, so a day is a dozen runs that
# published nothing new.
STALE = timedelta(hours=24)
NAMED = 5
WATCH = "python3 -I .github/mkdocs_project.py --watch"


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


def moment_of(value: object) -> datetime | None:
    """value as a moment, when it is a time with its zone, such as
    2026-11-11T17:45:19Z, as the dashboard writes when it wrote its data."""
    if not isinstance(value, str) or DAY.match(value) is None:
        return None
    try:
        moment = datetime.fromisoformat(value)
    except ValueError:
        return None
    return moment if moment.tzinfo is not None else None


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
    "time": Kind(
        "a time with its zone (such as 2026-11-11T17:45:19Z)",
        lambda value: moment_of(value) is not None,
    ),
    "day": Kind(
        "a day (such as 2026-10-25) or null",
        lambda value: value is None or is_day(value),
    ),
    "text": Kind(
        "a text or null", lambda value: value is None or isinstance(value, str)
    ),
    "github": Kind(
        f"an address at {GITHUB} or null",
        lambda value: (
            value is None or (isinstance(value, str) and value.startswith(GITHUB))
        ),
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
    it: the schema of repos.json that the script knows, the kind of every field
    that it reads of an entry of repos.json, of its health and of a day of
    history.json, by the name of each, and the kind of every field of repos.json
    itself that the watch alone reads, such as the time at which it was written."""

    schema: int
    repos: dict[str, str]
    health: dict[str, str]
    history: dict[str, str]
    feed: dict[str, str]


def dashboard_fields(root: Path) -> Shape:
    """What projects.js reads of the data of the dashboard, from DASHBOARD_FIELDS in
    the folder root."""
    try:
        data = json.loads((root / DASHBOARD_FIELDS).read_text(encoding="utf-8"))
        shape = Shape(
            data["schema"], data["repos"], data["health"], data["history"], data["feed"]
        )
    # Also a KeyError or a TypeError of data without its keys, or of no object.
    except (OSError, ValueError, LookupError, TypeError) as error:
        raise web.CheckError(f"{DASHBOARD_FIELDS} can't be read: {error!r}") from error
    if (
        not isinstance(shape.schema, int)
        or isinstance(shape.schema, bool)
        or not all(
            isinstance(fields, dict) and fields and set(fields.values()) <= set(KINDS)
            for fields in (shape.repos, shape.health, shape.history, shape.feed)
        )
    ):
        raise web.CheckError(
            f"{DASHBOARD_FIELDS} needs schema, the number of the shape of repos.json "
            "that docs/javascripts/projects.js knows, repos, health and history, each "
            "the kind of every field that the script reads by its name, and feed, the "
            "kind of every field of repos.json itself that the watch alone reads, one "
            f"of: {', '.join(KINDS)}."
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


def age_findings(
    url: str, data: dict[str, Any], shape: Shape, now: datetime
) -> list[str]:
    """What data, repos.json of the dashboard at url, breaks at the moment now of the
    fields of the feed of shape, which the watch alone reads: each is there, of its
    kind, and a time no more than STALE before now."""
    findings: list[str] = []
    use = "the watch can't tell how old the facts of the cards and the Trust page are"
    for name, kind in shape.feed.items():
        value = data.get(name)
        if name not in data:
            findings.append(f"`{name}` is missing in {url}, so {use}. {DASHBOARD_FIX}")
        elif not KINDS[kind].fits(value):
            findings.append(
                f"`{name}` in {url} is {json.dumps(value)}, not {KINDS[kind].words}, "
                f"so {use}. {DASHBOARD_FIX}"
            )
        elif (moment := moment_of(value)) is not None and now - moment > STALE:
            hours = int((now - moment).total_seconds() // 3600)
            findings.append(
                f"{url} was written at {value}, {hours} hours before the watch, though "
                "the dashboard writes it every two hours, so the cards, the Trust page "
                "and the Releases page show the releases and the scores of that time. "
                f"{DASHBOARD_FIX}"
            )
    return findings


def feed_findings(
    catalog: Catalog, shape: Shape, fetch: Callable[[str], bytes | None], now: datetime
) -> list[str]:
    """What repos.json of the dashboard breaks at the moment now of shape, what
    projects.js reads of it and how old the watch lets it be, and the repositories of
    the catalog that it lacks."""
    url = urljoin(SITE, FEED)
    use = "the cards, the Trust page and the Releases page keep the facts of the build"
    try:
        data = live_json(url, fetch, use)
    except Attention as found:
        return [str(found)]
    # The dashboard raises the schema when it reshapes the data, so a new schema
    # comes first: its fix is to teach projects.js the new shape.
    if isinstance(data, dict) and data.get("schema") != shape.schema:
        return [
            f"{url} has the schema {json.dumps(data.get('schema'))}, where "
            f"`docs/javascripts/projects.js` knows {shape.schema}, so the cards take "
            "the numbers of history.json alone, without their releases. Read the "
            "fields of the new schema in the script, and set its `SCHEMA` and "
            f"`schema` of `{DASHBOARD_FIELDS}` to it."
        ]
    entries = data.get("repos") if isinstance(data, dict) else None
    if not isinstance(entries, list) or not entries:
        return [
            f"{url} holds no list of repositories in `repos`, so {use}. {DASHBOARD_FIX}"
        ]
    findings = age_findings(url, data, shape, now)
    repos = labeled(entries, "repo")
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
    findings += field_findings(url, "the health of these entries", health, shape.health)
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
            f"`{SEARCH}`."
        )
        content = fetch(url)
        if content is None:
            findings.append(f"{url} answers 404, so {fix}")
            continue
        try:
            docs = documents(content, url)
        except web.SearchError as error:
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
                f"websites later. robots() of `{ADDRESS}` names the sitemap of every "
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
            f"sitemaps_at_root() of `{ADDRESS}` leads it there after the build. {REBUILD}"
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
                elif not web.exists(probe, target):
                    gone.append(page)
            old = urljoin(SITE, f"{folder}/")
            if missing:
                findings.append(
                    f"Old addresses of {old} that answer 404, though "
                    f"`{FORMER}/{folder}.txt` lists them: {few(missing)}. Old links "
                    f"lead to the 404 page there; on_post_build of `{EVENTS}` writes a "
                    f"page at each that leads to {moves[folder]}. {REBUILD}"
                )
            if astray:
                findings.append(
                    f"Old addresses of {old} that don't lead to the same page in "
                    f"{moves[folder]}: {few(astray)}. moved_page() of `{ADDRESS}` "
                    "writes each with its canonical address and its refresh, so remove "
                    f"what writes them after the hooks, such as a file in docs/. {REBUILD}"
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
        *feed_findings(catalog, shape, fetch, now),
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
        for _ in range(web.TRIES - 1):
            try:
                return ask(url)
            except web.CheckError:
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
            catalog, shape, patient(web.fetched), patient(web.status), datetime.now(UTC)
        )
    except (CatalogError, web.CheckError) as error:
        print(error, file=sys.stderr)
        return 2
    if not findings:
        print(
            f"The live websites at {SITE} hold what this website depends on: the data "
            "of the dashboard in the shape that docs/javascripts/projects.js reads, "
            f"written within {STALE // timedelta(hours=1)} hours, the search index of "
            "every project website, security.txt for more than "
            f"{AHEAD.days} days, robots.txt with every sitemap, the sitemap of this "
            "website, and a page at every old address that leads to its page now."
        )
        return 0
    sys.stdout.write(watch_report(findings))
    return DIFFERS
