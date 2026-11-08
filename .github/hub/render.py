"""What the hooks write from the catalog: the cards of the home pages, the Trust
page and the tables of the READMEs.

The hooks put the groups of the projects with a card for each into the home page, in the
language of the page. The card of a project with a repo also gets the part of its live
facts: the level of its OpenSSF Best Practices, which the hooks read from
bestpractices.dev, and its repository, for which the script docs/javascripts/projects.js
writes its latest release and its quality numbers from the data of the dashboard into
the card as the page loads.

The Trust page, docs/trust.md and docs/trust.de.md, gets the guarantees of every project
with a repo, from the texts of [trust] in projects.toml, in two parts that each read on
a phone, under the headings of the page: what every project guarantees alike, each
guarantee once, in place of its line <!-- trust-shared -->, and in place of its line
<!-- trust --> a table with a row for each project and a column for each of its numbers,
which becomes a card for each project on a narrow screen. The script fills the cells of
its latest release and of its numbers from the same data as on the cards, and the build
names the level of its OpenSSF Best Practices. The line <!-- verify --> becomes the
commands that verify the latest release of every project with the GitHub CLI, a tab for
each.
"""

from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor
from html import escape
from typing import Any

from . import web
from .catalog import (
    GITHUB,
    HOME,
    LEVELS,
    SCRIPT,
    TRUST,
    TRUST_LINKED,
    TRUST_NUMBERS,
    TRUST_VALUED,
    Catalog,
    CatalogError,
    Group,
    Link,
    Picture,
    Project,
    Source,
    cell,
    log,
)

# The README in the first language of the catalog; that of each further language
# that HEADINGS has the words for is README.<code>.md, such as README.de.md.
README = "README.md"
# The command that writes the tables of the READMEs, for the messages.
WRITE = "python3 -I .github/mkdocs_project.py --write"

# The line of docs/index.md and docs/index.de.md that the groups of cards replace,
# and the anchor of the part of the page that holds them, which the button of the
# hero of overrides/home.html leads to.
MARKER = "<!-- projects -->"
MARKER_LINE = re.compile(rf"^{re.escape(MARKER)}[ \t]*$", re.MULTILINE)
PROJECTS = "projects"
# The size of the picture on top of a card, half that of a social preview on GitHub:
# twice the width of a card in the grid of three, for screens with twice the pixels.
PICTURE = (640, 320)
# How the picture of a card loads: those of the first group, which a reader sees
# first, at once, and the first of them before the other pictures of the page, since
# it is its largest paint; the others only as they come into view. Each says it, so
# that lazy() of .github/mkdocs_blueprint.py, which makes every picture of a page
# but its first wait until it comes into view, leaves it as it is.
FIRST = 'loading="eager" fetchpriority="high"'
EAGER = 'loading="eager"'
LAZY = 'loading="lazy"'

# The lines of each README between which the table of the projects goes, and the
# headings of its columns in the language of the README; a first language without
# its own takes those of English.
TABLE_START = "<!-- projects:start -->"
TABLE_END = "<!-- projects:end -->"
HEADINGS = {
    "en": ("Project", "What it does", "Works with", "Start", "Website"),
    "de": ("Projekt", "Was es tut", "Funktioniert mit", "Start", "Website"),
}

# The live facts of the home pages. The dashboard of the blueprint publishes its data
# at the same address every few hours: repos.json with the latest release and the
# quality numbers of every repository, history.json with those numbers of every day,
# and releases.atom with the newest releases of all of them. As a home page loads,
# docs/javascripts/projects.js reads the first two from there, on the same origin,
# and writes the release and the numbers into the part of each card with a repo that
# has the class FACTS. What's new, in place of the line NEWS_MARKER, is the latest
# release of every project with a repo, the newest first, which the build writes from
# the releases that it reads for the Releases page, each with the headline of its
# notes; the script puts a newer release of the data in place of one that came out
# after the build. Without the script, or without the data, the cards keep what the
# build put into them. The home pages name no feed in their head: Material asks the
# folder of every alternate link there for its sitemap.xml, which the dashboard
# doesn't publish.
DASHBOARD = "/repo-blueprint/dashboard/"
FEED = f"{DASHBOARD}repos.json"
HISTORY = f"{DASHBOARD}history.json"
ATOM = f"{DASHBOARD}releases.atom"
FACTS = "project-facts"

# The Trust page. The guarantees of every project with a repo come in two parts, each
# under a heading of the page itself, so that its links to their anchors hold in the
# source too: the guarantees of TRUST_VALUED, which every project gives alike, take
# the place of the line SHARED_MARKER, each once with its one value, in a list of the
# class TRUST_SHARED, whose values of TRUST_LINKED link the security policy and the
# form for private reports of every project in the place of {}; and the numbers of
# TRUST_NUMBERS take the place of the line TRUST_MARKER, in a table with a row for
# each project, which the text of numbers names, and the note below it. On a phone,
# each row becomes a card, on which the label of every cell, its data-label, stands
# beside its value, so the page never scrolls sideways. The table is in a part of the
# page with the class TRUST that tells the script where the data of the dashboard is,
# as that of the cards does. The script writes the value of every number of TRUST_LIVE
# into the cell of each project, by its repository and the key of its number; without
# the data, the cell of its release links its releases on GitHub, and the others hold
# DASH. The commands that verify the latest release of every project take the place of
# VERIFY_MARKER: they check the attestation of its release, and the provenance of one
# of its files, which the workflow SIGNER of its repository signed.
TRUST_MARKER = "<!-- trust -->"
TRUST_LINE = re.compile(rf"^{re.escape(TRUST_MARKER)}[ \t]*$", re.MULTILINE)
SHARED_MARKER = "<!-- trust-shared -->"
SHARED_LINE = re.compile(rf"^{re.escape(SHARED_MARKER)}[ \t]*$", re.MULTILINE)
VERIFY_MARKER = "<!-- verify -->"
VERIFY_LINE = re.compile(rf"^{re.escape(VERIFY_MARKER)}[ \t]*$", re.MULTILINE)
TRUST_SHARED = "trust-shared"
TRUST_LIVE = ("release", "coverage", "mutation", "scorecard")
DASH = "—"
SIGNER = ".github/workflows/build-release.yml"
# The OpenSSF Best Practices of a project: its page at bestpractices.dev, and its data
# there with the level that it holds. The build reads the level and names it on the
# card, in the language of the page, linked to the page; the reader's browser asks
# bestpractices.dev for nothing, and the Catalog workflow builds the website every
# day. The website shows no badge, which would stay as the build downloaded it: the
# hooks of the blueprint take every badge out of a page. A level that can't be read
# stays off the card until the next build, which never fails for it.
BEST_PRACTICES = "https://www.bestpractices.dev/projects/{}"
BEST_PRACTICES_DATA = "https://www.bestpractices.dev/projects/{}.json"

# The key of config.extra that keeps the levels for the build of each language.
LEVEL = "best_practices"

# The class of the line of a card with what its project works with.
REQUIRES = "project-requires"


def bracketed(text: str) -> str:
    """text between the brackets of a link or a picture of Markdown, where a bracket
    or a backslash of its own would end or change it."""
    return re.sub(r"([\\\[\]])", r"\\\1", text)


def button(link: Link, language: str, *, primary: bool = False) -> str:
    """The Markdown of a button: a link with the classes of Material."""
    classes = ".md-button .md-button--primary" if primary else ".md-button"
    label, url = bracketed(link.label[language]), link.url[language]
    return f"[:{link.icon}: {label}]({url}){{ {classes} }}"


def picture(image: Picture, language: str, loading: str = LAZY) -> str:
    """The Markdown of the picture on top of a card, in language: with its size, so
    that the page keeps its place before it loads, loading as FIRST, EAGER or LAZY
    say, and without the enlarging of the lightbox, since the picture is a
    preview."""
    width, height = PICTURE
    return (
        f"![{bracketed(image.alt[language])}]({image.src[language]})"
        f'{{ width="{width}" height="{height}" {loading} .off-glb }}'
    )


def facts(
    catalog: Catalog, project: Project, language: str, levels: dict[int, str]
) -> str:
    """The HTML of the live facts of the card of a project with a repo: its
    repository and its name, for the script, which adds its release and its quality
    numbers, and the level of its OpenSSF Best Practices of levels, by the number of
    its project, which links its page at bestpractices.dev."""
    texts = {key: text[language] for key, text in catalog.facts.items()}
    level = levels.get(project.bestpractices or 0)
    items = ""
    if level is not None:
        named = texts["bestpractices"].replace("{}", texts[level])
        items = (
            f'<ul class="{FACTS}__list" aria-label="{escape(texts["label"])}">'
            f'<li><a href="{BEST_PRACTICES.format(project.bestpractices)}">'
            f"{escape(named)}</a></li></ul>"
        )
    return (
        f'<div class="{FACTS}" data-repo="{escape(str(project.repo))}"'
        f' data-name="{escape(project.name[language])}">{items}</div>'
    )


def requirement(
    catalog: Catalog, project: Project, language: str, works: dict[str, dict[str, str]]
) -> str:
    """The Markdown of the line of the card of project that says what it works with,
    in language: the icon and the label of the requirements of catalog, with what
    works has for it in place of {}, or nothing when works has nothing for it."""
    texts = works.get(project.slug)
    if not texts:
        return ""
    line = catalog.requirements
    label = line.label[language].replace("{}", texts[language])
    return f'<p class="{REQUIRES}" markdown>:{line.icon}: {label}</p>'


def card(
    project: Project,
    language: str,
    second: Link | None,
    live: str = "",
    requires: str = "",
    loading: str = LAZY,
) -> str:
    """The Markdown of the card of project: its picture, which loads as loading
    says, its heading with the slug as its anchor, with an anchor of its own for
    every folder of former, so that an address of the home page that led to the card
    under an old slug still does, and with a link to its website, its summary, live,
    the HTML of its live facts if it has them, requires, the line that says what it
    works with if it has one, right above its first button and second, the button
    that Catalog.second gives it."""
    buttons = [button(project.start, language, primary=True)]
    if second is not None:
        buttons.append(button(second, language))
    name = f"[{bracketed(project.name[language])}]({project.website[language]})"
    anchors = "".join(f'<span id="{folder}"></span>' for folder in project.former)
    heading = (
        f"### {anchors}:{project.icon}:{{ .lg .middle }} {name} {{ #{project.slug} }}"
    )
    parts = ['<div class="card" markdown>']
    if project.picture is not None:
        parts.append(picture(project.picture, language, loading))
    parts += [heading, project.summary[language]]
    parts += [part for part in (live, requires) if part]
    parts += ["\n".join(buttons), "</div>"]
    return "\n\n".join(parts)


def section(
    catalog: Catalog,
    group: Group,
    language: str,
    levels: dict[int, str] | None = None,
    works: dict[str, dict[str, str]] | None = None,
    *,
    first: bool = False,
) -> str:
    """The Markdown of group: its heading with its id as its anchor, the grid with
    the card of every project in it, each with a repo with its live facts and the
    level of its OpenSSF Best Practices of levels, and what it works with of works,
    by its slug, and its note below the cards. The pictures of the first group of
    the page load at once, the first before the others; those of the other groups
    as they come into view."""
    loading = [FIRST, EAGER] if first else [LAZY]
    members = catalog.members(group)
    parts = [
        f"## {group.heading[language]} {{ #{group.id} }}",
        '<div class="grid" markdown>',
        *(
            card(
                project,
                language,
                catalog.second(project),
                facts(catalog, project, language, levels or {}) if project.repo else "",
                requirement(catalog, project, language, works or {}),
                loading[min(number, len(loading) - 1)],
            )
            for number, project in enumerate(members)
        ),
        "</div>",
    ]
    if group.note is not None:
        parts.append(f'<p class="note" markdown>{group.note[language]}</p>')
    return "\n\n".join(parts)


def script_data(catalog: Catalog, language: str) -> str:
    """The attributes of the part of a page that tell the script of the live facts
    where their data is, the language of the page and the texts of SCRIPT in it."""
    data = {
        "facts": FEED,
        "history": HISTORY,
        "locale": language,
        **{key: catalog.facts[key][language] for key in SCRIPT},
    }
    return "".join(f' data-{key}="{escape(text)}"' for key, text in data.items())


def cards(
    catalog: Catalog,
    language: str,
    levels: dict[int, str] | None = None,
    works: dict[str, dict[str, str]] | None = None,
) -> str:
    """The Markdown of every group with its cards, in language, in a part of the page
    with its own anchor. The part tells the script of the live facts where their data
    is, the language of the page and the texts of the facts in it; levels holds the
    level of the OpenSSF Best Practices of each project by its number, and works what
    each works with by its slug."""
    attributes = script_data(catalog, language)
    return "\n\n".join(
        [
            f'<div class="projects" id="{PROJECTS}"{attributes} markdown>',
            *(
                section(catalog, group, language, levels, works, first=number == 0)
                for number, group in enumerate(catalog.groups)
            ),
            "</div>",
        ]
    )


def best_practices(catalog: Catalog) -> dict[int, str]:
    """The level of the OpenSSF Best Practices of every project of the catalog that
    names its project at bestpractices.dev, by its number: passing, silver or gold.
    A project whose data can't be read, or that holds no level yet, has none, which
    the log says without a warning, so that the strict build passes."""
    numbers = sorted(
        {project.bestpractices for project in catalog.projects if project.bestpractices}
    )
    if not numbers:
        return {}

    def level(number: int) -> str | None:
        url = BEST_PRACTICES_DATA.format(number)
        try:
            data = json.loads(web.download(url))
        except (web.SearchError, ValueError) as error:
            log.info(
                "The cards leave out the level of %s until the next build: %s",
                url,
                error,
            )
            return None
        found = data.get("badge_level") if isinstance(data, dict) else None
        if found not in LEVELS:
            log.info("%s holds no level of the OpenSSF Best Practices: %r", url, found)
            return None
        return str(found)

    with ThreadPoolExecutor(max_workers=len(numbers)) as pool:
        found = dict(zip(numbers, pool.map(level, numbers), strict=True))
    return {number: text for number, text in found.items() if text is not None}


def levels_of(config: Any) -> dict[int, str]:
    """The levels of best_practices, read once for the build of every language."""
    if LEVEL not in config.extra:
        config.extra[LEVEL] = best_practices(config.extra["catalog"])
    found: dict[int, str] = config.extra[LEVEL]
    return found


def short_name(project: Project, language: str) -> str:
    """The name of project in a few words, in language: its short one, if it has
    one."""
    return (project.short or project.name)[language]


def trust_cell(
    catalog: Catalog,
    project: Project,
    key: str,
    language: str,
    levels: dict[int, str],
) -> str:
    """The HTML of the cell of project, which has a repo, in the column key of
    TRUST_NUMBERS of the table of the Trust page, with the label of its column, which
    a phone shows beside its value: the place of a value of the script for a number
    of TRUST_LIVE, or the level of its OpenSSF Best Practices of levels, which links
    its page at bestpractices.dev."""
    label = escape(catalog.trust.texts[key][language])
    repo = escape(str(project.repo))
    if key in TRUST_LIVE:
        content = DASH
        if key == "release":
            content = f'<a href="{GITHUB}{repo}/releases/latest">GitHub</a>'
        return (
            f'<td data-label="{label}" data-repo="{repo}" data-fact="{key}">'
            f"{content}</td>"
        )
    level = levels.get(project.bestpractices or 0)
    content = DASH
    if level is not None:
        page = BEST_PRACTICES.format(project.bestpractices)
        content = f'<a href="{page}">{escape(catalog.facts[level][language])}</a>'
    return f'<td data-label="{label}">{content}</td>'


def with_repo(catalog: Catalog) -> list[Project]:
    """The projects of catalog that the Trust page shows: those with a repo."""
    return [project for project in catalog.projects if project.repo is not None]


def shared_guarantees(catalog: Catalog, language: str) -> str:
    """The HTML of the guarantees that every project with a repo gives alike, in
    language: a list with each of TRUST_VALUED once, its label and its one value,
    in which those of TRUST_LINKED link the security policy and the form for private
    reports of every project, each under its short name, in the place of {}."""
    targets = {
        "policy": "{}/blob/main/SECURITY.md",
        "report": "{}/security/advisories/new",
    }
    items = []
    for key in TRUST_VALUED:
        label = escape(catalog.trust.texts[key][language])
        value = escape(catalog.trust.values[key][language])
        if key in TRUST_LINKED:
            links = ", ".join(
                f'<a href="{GITHUB}{targets[key].format(escape(str(project.repo)))}">'
                f"{escape(short_name(project, language))}</a>"
                for project in with_repo(catalog)
            )
            value = value.replace("{}", links)
        items.append(f"<div><dt>{label}</dt><dd>{value}</dd></div>")
    return "\n".join([f'<dl class="{TRUST_SHARED}">', *items, "</dl>"])


def numbers_table(
    catalog: Catalog, language: str, levels: dict[int, str] | None = None
) -> str:
    """The HTML of the table of the numbers of every project with a repo, in
    language, which the text of numbers names: a row for each project, under its
    short name, which links its website, and a column for each of TRUST_NUMBERS. Its part of the page tells the script where
    the data of the dashboard is and the language of the page; levels holds the
    level of the OpenSSF Best Practices of each project by its number."""
    texts = {key: text[language] for key, text in catalog.trust.texts.items()}
    data = {"facts": FEED, "history": HISTORY, "locale": language}
    attributes = "".join(f' data-{key}="{escape(text)}"' for key, text in data.items())
    head = "".join(
        f'<th scope="col">{escape(texts[key])}</th>'
        for key in ("project", *TRUST_NUMBERS)
    )
    rows = [
        f'<tr><th scope="row"><a href="{escape(project.website[language])}">'
        f"{escape(short_name(project, language))}</a></th>"
        + "".join(
            trust_cell(catalog, project, key, language, levels or {})
            for key in TRUST_NUMBERS
        )
        + "</tr>"
        for project in with_repo(catalog)
    ]
    return "\n".join(
        [
            f'<div class="{TRUST}"{attributes}>',
            f'<table aria-label="{escape(texts["numbers"])}">',
            f"<thead><tr>{head}</tr></thead>",
            "<tbody>",
            *rows,
            "</tbody>",
            "</table>",
            "</div>",
        ]
    )


def guarantees(
    catalog: Catalog, language: str, levels: dict[int, str] | None = None
) -> str:
    """The Markdown of the numbers of the Trust page in language, which take the
    place of its line TRUST_MARKER, under the heading of the page: the table of the
    numbers of each project, with the note below it; levels holds the level of the
    OpenSSF Best Practices of each project by its number."""
    note = catalog.trust.texts["note"][language]
    return f"{numbers_table(catalog, language, levels)}\n\n{note}"


def verification(catalog: Catalog, language: str) -> str:
    """The Markdown of the commands that verify the latest release of every project
    with a repo, a tab for each under its short name in language, with the GitHub
    CLI: the attestation of the release, which ties its tag to its commit and to its
    files, and the provenance of the file that Project.verified names, which the
    workflow SIGNER of its repository signed. Each command stands on a line of its
    own, so that it runs as it is copied into any shell."""
    tabs = []
    for project in catalog.projects:
        if project.repo is None:
            continue
        repo, file = project.repo, project.verified
        commands = [
            "```sh",
            f"gh release verify --repo {repo}",
            f"gh release download --repo {repo} --pattern {file} --clobber",
            f"gh attestation verify {file} --repo {repo}"
            f" --signer-workflow {repo}/{SIGNER}",
            "```",
        ]
        title = short_name(project, language).replace('"', "&quot;")
        block = "\n".join(f"    {line}" for line in commands)
        tabs.append(f'=== "{title}"\n\n{block}')
    return "\n\n".join(tabs)


def home_language(catalog: Catalog, dest_uri: str) -> str | None:
    """The language of the home page that MkDocs writes to dest_uri, index.html at
    the root for the default language and in the folder of each other one, or None
    for every other page."""
    homes = {HOME: catalog.default} | {
        f"{language}/{HOME}": language for language in catalog.languages[1:]
    }
    return homes.get(dest_uri)


def links(texts: dict[str, str], urls: dict[str, str], language: str) -> str:
    """A link to every address of urls once, that of language first and then in the
    order of the languages, each with the text of its language."""
    first: dict[str, str] = {}
    for code in sorted(urls, key=lambda other: other != language):
        first.setdefault(urls[code], code)
    return " · ".join(f"[{cell(texts[code])}]({url})" for url, code in first.items())


def works_with(project: Project, language: str) -> str:
    """The cell of the table of the README that says what project works with: its
    text, or for one that the build reads from a file, its platform and a link to the
    file on the default branch, which the link check checks too, or a dash."""
    if isinstance(project.requires, Source):
        file = project.requires.file
        url = f"{GITHUB}{project.repo}/blob/{web.DEFAULT_BRANCH}/{file}"
        return f"{cell(str(project.platform))} ([{file}]({url}))"
    if project.requires:
        return cell(project.requires[language])
    return DASH


def readmes(catalog: Catalog) -> dict[str, str]:
    """The README of every language that has one, by its language: README.md in the
    first language of the catalog, and README.<code>.md in each further one that
    HEADINGS has the words for."""
    return {catalog.default: README} | {
        language: f"README.{language}.md"
        for language in catalog.languages[1:]
        if language in HEADINGS
    }


def table(catalog: Catalog, language: str) -> str:
    """The table of the README in language: every project with its repository, what
    it does and what it works with in language, its first button and its website,
    with the address of every language, that of language first. The link check of
    the Markdown, which reads no TOML, so checks every address of projects.toml."""
    headings = HEADINGS.get(language, HEADINGS["en"])
    rows = [
        f"| {' | '.join(headings)} |",
        f"|{' --- |' * len(headings)}",
    ]
    for project in catalog.projects:
        name = cell(project.name[language])
        if project.repo is not None:
            repository = project.repo.partition("/")[2]
            name = f"[{repository}](https://github.com/{project.repo})"
        start = links(project.start.label, project.start.url, language)
        website = "—"
        if project.docs is not None:
            shown = {
                code: url.removeprefix("https://").rstrip("/")
                for code, url in project.docs.url.items()
            }
            website = links(shown, project.docs.url, language)
        tagline = cell(project.tagline[language])
        works = works_with(project, language)
        rows.append(f"| {name} | {tagline} | {works} | {start} | {website} |")
    return "\n".join(rows)


def readme(text: str, catalog: Catalog, language: str) -> str:
    """text, that of the README in language, with the table of catalog in language
    between its markers."""
    start = text.find(TABLE_START)
    end = text.find(TABLE_END)
    if start < 0 or end < start:
        raise CatalogError(
            f"{readmes(catalog)[language]} needs the lines {TABLE_START} and "
            f"{TABLE_END}, in this order; the table of the projects goes between them."
        )
    head = text[: start + len(TABLE_START)]
    return f"{head}\n\n{table(catalog, language)}\n\n{text[end:]}"
