"""What several of the tests of the hooks share: the file of the hooks as MkDocs loads
it, and the catalogs, the websites and the answers of the web that they fake.
"""

from __future__ import annotations

import importlib.util
import io
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path, PurePosixPath
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

import hub.address
import hub.bot
import hub.catalog
import hub.reader
import hub.releases
import hub.requirements

ROOT = Path(__file__).resolve().parents[1]
HOOKS = ROOT / ".github/mkdocs_project.py"


def load_hooks() -> ModuleType:
    spec = importlib.util.spec_from_file_location("mkdocs_project", HOOKS)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # MkDocs puts a hook into sys.modules too, where its data classes look it up.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


hooks = load_hooks()


def entry(slug: str = "tool", **changes: Any) -> dict[str, Any]:
    """A [[project]] of projects.toml, as tomllib reads it."""
    project: dict[str, Any] = {
        "slug": slug,
        "repo": f"Dennis-Otto/{slug}",
        "license": "MIT",
        "platform": "Home Assistant",
        "group": "tools",
        "icon": "material-tools",
        "name": {"en": "The tool", "de": "Das Werkzeug"},
        "tagline": {"en": "A tool", "de": "Ein Werkzeug"},
        "summary": {"en": "It does things.", "de": "Es tut Dinge."},
        "image": f"images/projects/{slug}.webp",
        "alt": {"en": "The tool at work", "de": "Das Werkzeug bei der Arbeit"},
        "start": {
            "icon": "material-download",
            "label": {"en": "Install", "de": "Installieren"},
            "url": "https://example.org/install",
        },
        "docs": {
            "en": f"https://dennis-otto.github.io/{slug}/",
            "de": f"https://dennis-otto.github.io/{slug}/de/",
        },
    }
    project.update(changes)
    return project


def own_pictures(slug: str = "tool") -> dict[str, str]:
    """The image of a project with a picture of its own in German."""
    return {
        "en": f"images/projects/{slug}.webp",
        "de": f"images/projects/de/{slug}.webp",
    }


def drawing_data(**changes: Any) -> dict[str, Any]:
    """The drawing of a project whose German picture the hub draws, as tomllib
    reads it."""
    return {
        "screenshot": "docs/images/de/shot.png",
        "logo": "docs/logo.svg",
        "accent": "#14b8a6",
    } | changes


def drawn(slug: str = "tool", **changes: Any) -> dict[str, Any]:
    """A project with a repo whose German picture the hub draws, with changes."""
    return entry(
        slug, **({"image": own_pictures(slug), "drawing": drawing_data()} | changes)
    )


def without_repo(project: dict[str, Any]) -> dict[str, Any]:
    """project without its repository, such as the dashboard, and so without the
    keys that go with it."""
    for key in ("repo", "license", "platform"):
        del project[key]
    return project


def without_card(project: dict[str, Any]) -> dict[str, Any]:
    """project without a group, such as the dashboard, and so without the keys of its
    card."""
    for key in ("group", "image", "alt"):
        del project[key]
    return project


def group_data(id_: str = "tools", **changes: Any) -> dict[str, Any]:
    """A [[group]] of projects.toml, as tomllib reads it."""
    group: dict[str, Any] = {
        "id": id_,
        "heading": {"en": "Tools", "de": "Werkzeuge"},
    }
    group.update(changes)
    return group


def facts_data() -> dict[str, Any]:
    """The [facts] of a projects.toml, as tomllib reads it."""
    return {
        "label": {"en": "Facts", "de": "Fakten"},
        "released": {"en": "released {}", "de": "erschienen {}"},
        "coverage": {"en": "{} covered", "de": "{} abgedeckt"},
        "mutation": {"en": "{} mutants", "de": "{} Mutanten"},
        "scorecard": {"en": "Scorecard {}", "de": "Scorecard {}"},
        "answer": {"en": "answer in {}", "de": "Antwort nach {}"},
        "bestpractices": {"en": "Best Practices {}", "de": "Best Practices {}"},
        "passing": {"en": "passing", "de": "bestanden"},
        "silver": {"en": "silver", "de": "Silber"},
        "gold": {"en": "gold", "de": "Gold"},
        "projects": {"en": "Projects", "de": "Projekte"},
        "github": {"en": "On GitHub", "de": "Auf GitHub"},
        "releases": {"en": "All of {} on GitHub", "de": "Alle von {} auf GitHub"},
    }


# The rows of [trust] whose value every project shares, which a table with its label
# and its value holds; the value of the last two holds {} for the links to every
# project.
VALUED_ROWS = ("tag", "provenance", "immutable", "sbom", "vex", "policy", "report")
LINKED_ROWS = ("policy", "report")


def trust_data() -> dict[str, Any]:
    """The [trust] of a projects.toml, as tomllib reads it: every text in English,
    and in German with "auf Deutsch" after it."""

    def texts(text: str) -> dict[str, str]:
        return {"en": text, "de": f"{text} auf Deutsch"}

    data: dict[str, Any] = {
        key: texts(key.capitalize())
        for key in (
            "numbers",
            "project",
            "release",
            "coverage",
            "mutation",
            "scorecard",
            "bestpractices",
        )
    }
    data["note"] = {
        "en": "From the [dashboard](https://example.org/dashboard/).",
        "de": "Aus dem [Dashboard](https://example.org/dashboard/).",
    }
    for key in VALUED_ROWS:
        value = f"{key} value: {{}}" if key in LINKED_ROWS else f"{key} value"
        data[key] = {"label": texts(key.capitalize()), "value": texts(value)}
    return data


def catalog_data(*projects: object) -> dict[str, Any]:
    """The tables of a projects.toml with projects, or a single one, in the group
    tools; a project that is no table tests the reader."""
    return {
        "languages": ["en", "de"],
        "documentation": {
            "icon": "material-book",
            "label": {"en": "Documentation", "de": "Dokumentation"},
        },
        "facts": facts_data(),
        "trust": trust_data(),
        "requirements": {
            "icon": "material-puzzle",
            "label": {"en": "Works with {}", "de": "Läuft mit {}"},
        },
        "group": [group_data()],
        "project": list(projects) or [entry()],
    }


def problems(data: dict[str, Any]) -> list[str]:
    """The problems that reading data finds, one per line."""
    with pytest.raises(hub.catalog.CatalogError) as error:
        hub.reader.read(data)
    lines = str(error.value).splitlines()
    assert lines[0] == f"projects.toml has {len(lines) - 2} problem(s):"
    assert lines[-1] == "The comments at the top of projects.toml describe every key."
    return [line.strip() for line in lines[1:-1]]


def release(
    tag: str, day: str, headline: str = "", repo: str = "Dennis-Otto/one"
) -> Any:
    """A release that the build read, with notes of one paragraph."""
    url = f"https://github.com/{repo}/releases/tag/{tag}"
    return hub.releases.Release(
        tag, url, date.fromisoformat(day), "<p>Notes</p>", headline
    )


# What a project works with.


# The files from which the cards of the catalog of this repository read what their
# projects work with, as the latest releases held them in October 2026.
FIXTURES = ROOT / "tests/fixtures/requirements"
HACS = (FIXTURES / "hacs.json").read_bytes()
INFO = (FIXTURES / "info.xml").read_bytes()


def source(**changes: Any) -> dict[str, Any]:
    """The requires of a project that reads what it works with from hacs.json, as
    tomllib reads it."""
    data: dict[str, Any] = {
        "file": "hacs.json",
        "field": "homeassistant",
        "text": {
            "en": "Home Assistant {} or newer",
            "de": "Home Assistant {} oder neuer",
        },
    }
    data.update(changes)
    return data


def nextcloud() -> dict[str, Any]:
    """The requires of a project that reads the versions of Nextcloud that it works
    with from its info.xml, as tomllib reads it."""
    return source(
        file="appinfo/info.xml",
        field={
            "min": "dependencies/nextcloud@min-version",
            "max": "dependencies/nextcloud@max-version",
        },
        text={"en": "Nextcloud {min} to {max}", "de": "Nextcloud {min} bis {max}"},
    )


def raw(repo: str, ref: str, file: str) -> str:
    """The address of file of repo at ref, a tag or HEAD, at
    raw.githubusercontent.com."""
    return f"https://raw.githubusercontent.com/{repo}/{ref}/{file}"


def source_files(ref: str) -> dict[str, bytes]:
    """The fixture of every file that the catalog of this repository reads what a
    project works with from, by its address at ref."""
    return {
        raw(str(project.repo), ref, project.requires.file): (
            FIXTURES / PurePosixPath(project.requires.file).name
        ).read_bytes()
        for project in hub.reader.load(ROOT).projects
        if isinstance(project.requires, hub.catalog.Source)
    }


def drawn_files(project: Any) -> dict[str, bytes]:
    """A stand-in for every file from which the hub draws a picture of the card of
    project, by its address on the default branch: its screenshots and its logo."""
    drawing = project.picture.drawing if project.picture is not None else None
    if drawing is None:
        return {}
    names = [*drawing.screenshot.values(), *filter(None, [drawing.logo])]
    return {raw(str(project.repo), "HEAD", name): b"RIFF" for name in names}


def network_files() -> dict[str, bytes]:
    """Every file that the catalog bot reads for the catalog of this repository, by
    its address on the default branch, in the order in which it asks: for each
    project the file that says what it works with, then those from which the hub
    draws its pictures."""
    files: dict[str, bytes] = {}
    sources = source_files("HEAD")
    for project in hub.reader.load(ROOT).projects:
        if isinstance(project.requires, hub.catalog.Source):
            url = raw(str(project.repo), "HEAD", project.requires.file)
            files[url] = sources[url]
        files |= drawn_files(project)
    return files


# The hooks of MkDocs.


def language(
    locale: str,
    *,
    default: bool | None = None,
    build: bool = True,
    nav_translations: dict[str, str] | None = None,
) -> SimpleNamespace:
    """A language of the i18n plugin, as its configuration gives it."""
    return SimpleNamespace(
        locale=locale,
        default=locale == "en" if default is None else default,
        build=build,
        nav_translations=nav_translations,
    )


def page(locale: str | None) -> SimpleNamespace:
    """A page of MkDocs, whose file has the language that the i18n plugin gives it."""
    file = SimpleNamespace() if locale is None else SimpleNamespace(locale=locale)
    return SimpleNamespace(file=file)


# The files at the root of the address, the 404 page and the structured data.

SITE = "https://dennis-otto.github.io/"
# 2026-10-13 at 23:30 in UTC, already the next day in Germany.
EPOCH = "1791934200"
LD_JSON = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.DOTALL)
# The head of a page as Material writes it, with the tags of the social plugin, which
# give the home page the bare name of the website.
HTML = (
    "<html><head><title>Dennis Otto</title>\n"
    '<meta property="og:title" content="Dennis Otto">\n'
    '<meta property="twitter:title" content="Dennis Otto">\n'
    "</head><body></body></html>"
)


def build(site: Path | None = None) -> SimpleNamespace:
    """The parts of the configuration of MkDocs that the hooks of a build read."""
    return SimpleNamespace(
        # Nothing that the projects work with, which the build reads from GitHub.
        # And the description of the website in English, which on_config keeps.
        extra={
            "catalog": hub.reader.load(ROOT),
            hub.requirements.WORKS: {},
            hub.address.LLMS: "The projects of Dennis Otto.",
        },
        site_dir=str(site),
        site_url=SITE,
        site_name="Dennis Otto",
        site_description="The projects of Dennis Otto.",
    )


def page_at(dest_uri: str, **meta: str) -> SimpleNamespace:
    """A page of MkDocs that is written to dest_uri in the folder of the website,
    with the keys of its front matter, and the canonical address that MkDocs gives
    it."""
    return SimpleNamespace(
        file=SimpleNamespace(dest_uri=dest_uri),
        meta=meta,
        canonical_url=f"{SITE}{dest_uri}",
    )


def sitemap(*urls: str) -> str:
    """A sitemap of the i18n plugin: a <url> for every address, with its English and
    its German version as the alternates."""
    entries = []
    for url in urls:
        english = url.replace(f"{SITE}de/", SITE)
        german = english.replace(SITE, f"{SITE}de/", 1)
        entries.append(
            "    <url>\n"
            f"        <loc>{url}</loc>\n"
            f'        <xhtml:link rel="alternate" hreflang="en" href="{english}"/>\n'
            f'        <xhtml:link rel="alternate" hreflang="de" href="{german}"/>\n'
            "    </url>\n"
        )
    return f"<urlset>\n{''.join(entries)}</urlset>\n"


# The time of a build, which MkDocs writes into the packed sitemap.
BUILT = 1791849600


def index_of(*docs: dict[str, Any]) -> bytes:
    """A search index with docs, as the search plugin writes it."""
    return json.dumps({"config": {"lang": ["en"]}, "docs": list(docs)}).encode()


def section(location: str, title: str = "A section", text: str = "") -> dict[str, str]:
    """An entry of a search index: a page, or a section of one with a #."""
    return {"location": location, "title": title, "text": text}


class Download:
    """A stand-in for urllib.request.urlopen: the answer to each request in turn,
    content or an error, and the requests with their time limits."""

    def __init__(self, *answers: bytes | Exception) -> None:
        self.answers = list(answers)
        self.requests: list[tuple[Any, float]] = []

    def __call__(self, url: Any, timeout: float) -> Any:
        self.requests.append((url, timeout))
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return io.BytesIO(answer)


def search_index(site: Path, *docs: dict[str, Any]) -> Path:
    """The search index of the website in site, with docs."""
    path = site / "search/search_index.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    index = {"config": {"lang": ["en", "de"]}, "docs": list(docs)}
    path.write_text(json.dumps(index), encoding="utf-8")
    return path


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


# The catalog bot, which compares the catalog with GitHub and the websites of the
# projects.


def listed_repo(
    name: str,
    homepage: str | None = "",
    *,
    archived: bool = False,
    private: bool = False,
) -> dict[str, Any]:
    """A repository of the owner as gh repo list --json nameWithOwner,homepageUrl,
    isArchived,isPrivate describes it."""
    return {
        "nameWithOwner": f"Dennis-Otto/{name}",
        "homepageUrl": homepage,
        "isArchived": archived,
        "isPrivate": private,
    }


def found(*items: dict[str, Any]) -> list[Any]:
    """The repositories of items, read as the bot reads the list of gh."""
    return hub.bot.repositories(json.dumps(list(items)))


class Websites:
    """A stand-in for hub.web.status: the status of every address it knows, 404 for
    every other, and the addresses that the bot asked for, in their order."""

    def __init__(self, answers: dict[str, int] | None = None) -> None:
        self.answers = answers or {}
        self.asked: list[str] = []

    def __call__(self, url: str) -> int:
        self.asked.append(url)
        return self.answers.get(url, 404)


class Files:
    """A stand-in for hub.web.fetched: the content of every file that it knows by its
    address, None for every other, and the addresses that the bot asked for, in
    their order."""

    def __init__(self, answers: dict[str, bytes] | None = None) -> None:
        self.answers = answers or {}
        self.asked: list[str] = []

    def __call__(self, url: str) -> bytes | None:
        self.asked.append(url)
        return self.answers.get(url)


def one_language(slug: str = "tool", **changes: Any) -> dict[str, Any]:
    """A project whose website, at the address, is in English alone."""
    return entry(slug, docs=f"{SITE}{slug}/", **changes)


def drift(
    *projects: dict[str, Any],
    repositories: list[Any],
    websites: Websites | None = None,
    files: Files | None = None,
) -> list[str]:
    """What the bot finds for a catalog of projects."""
    return hub.bot.drift(
        hub.reader.read(catalog_data(*projects)),
        repositories,
        websites or Websites(),
        files or Files(),
    )


# The repositories of the owner as gh listed them on 2026-10-13, with a private and
# an archived one of the kind that a person's token sees too, ha-autodarts under the
# name that it has since 2026-10-21 and the pager, public since 2026-11-03, under
# the name that it has since 2026-11-08.
TODAY = [
    listed_repo("repo-pager", f"{SITE}repo-pager/"),
    listed_repo("paperless-unified-search", f"{SITE}paperless-unified-search/"),
    listed_repo("homedarts-for-autodarts", f"{SITE}homedarts-for-autodarts/"),
    listed_repo("player-switch-for-autodarts", f"{SITE}player-switch-for-autodarts/"),
    listed_repo("paperless-sync", f"{SITE}paperless-sync/"),
    listed_repo("issue-assistant", f"{SITE}issue-assistant/"),
    listed_repo("dennis-otto.github.io", SITE),
    listed_repo("repo-blueprint", f"{SITE}repo-blueprint/"),
    listed_repo("ha-blueprints"),
    listed_repo("ios", "https://itunes.apple.com/us/app/nextcloud/id1125420102"),
    listed_repo("an-old-site", f"{SITE}an-old-site/", archived=True, private=True),
    listed_repo("a-private-tool", private=True),
]
# The German websites of the catalog of this repository, from the catalog: the pull
# request of the bot adds one that appeared and removes one that is gone, and its
# checks must pass.
GERMAN_SITES = {
    project.docs.url["de"]: 200
    for project in hub.reader.load(ROOT).projects
    if project.docs is not None and project.docs.url["de"] != project.docs.url["en"]
}


def in_french(value: Any) -> Any:
    """value, a part of the tables of projects.toml, in French in place of German."""
    if isinstance(value, dict):
        return {
            ("fr" if key == "de" else key): in_french(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [in_french(item) for item in value]
    return value


def guarded(job: str) -> list[str]:
    """The hosts that harden-runner lets job reach: job, a job of catalog.yml with
    a token that writes, blocks every other host from its first step on and runs
    without sudo and Docker, so that no step can lift the block."""
    steps = job[job.index("\n    steps:\n") :]
    first = steps.index("\n      - ")
    second = steps.index("\n      - ", first + 1)
    guard = steps[first : second + 1]
    assert "uses: step-security/harden-runner@" in guard
    assert "\n          egress-policy: block\n" in guard
    assert "\n          disable-sudo-and-containers: true\n" in guard
    endpoints = guard[guard.index("allowed-endpoints: >\n") :].splitlines()[1:]
    hosts = [line.strip() for line in endpoints if line.startswith(" " * 12)]
    # Before a step needs the network, the job waits until harden-runner has
    # removed Docker, which a job that ends first leaves behind and hangs, and
    # until each of its hosts gets through: an answer of the DNS that passed
    # harden-runner by blocks its host for up to a minute (#88).
    wait = steps[second : steps.index("\n      - ", second + 1) + 1]
    assert wait.startswith(
        "\n      - name: Wait until Harden-Runner has removed Docker and lets the "
        "hosts through\n"
    )
    assert "pgrep -x 'apt-get|dpkg'" in wait
    waits = re.findall(r"^ +for host in (.+); do$", wait, re.MULTILINE)
    assert [f"{host}:443" for host in waits[0].split()] == hosts
    return hosts


def lists(root: Path, *items: dict[str, Any]) -> Path:
    """The file of gh repo list with items, in root."""
    path = root / "repositories.json"
    path.write_text(json.dumps(list(items)), encoding="utf-8")
    return path


ADVICE = (
    "Correct `requires`, or write what the project works with into `requires` as a "
    "text in every language."
)


# The script.


def repository(root: Path) -> Path:
    """A copy of the catalog, with the pages of the former websites that it names,
    and of the READMEs of this repository at root, with the folders of the other files
    that the fix of the catalog bot writes; the English README."""
    for name in ("projects.toml", "README.md", "README.de.md"):
        shutil.copyfile(ROOT / name, root / name)
    shutil.copytree(ROOT / "former", root / "former")
    (root / "docs").mkdir()
    (root / hub.bot.NOT_FOUND_FIXTURE).parent.mkdir(parents=True)
    shutil.copyfile(ROOT / hub.bot.NOT_FOUND_FIXTURE, root / hub.bot.NOT_FOUND_FIXTURE)
    return root / "README.md"
