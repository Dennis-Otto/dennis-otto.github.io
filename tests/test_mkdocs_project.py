"""Tests of the hooks of the website and of the script of the README table,
.github/mkdocs_project.py, with fakes of MkDocs in its place."""

from __future__ import annotations

import dataclasses
import email.message
import http.client
import importlib.util
import io
import gzip
import json
import logging
import re
import runpy
import shutil
import subprocess
import sys
import tomllib
from datetime import UTC, date, datetime, timedelta
from html import escape
from pathlib import Path, PurePosixPath
from types import ModuleType, SimpleNamespace
from collections.abc import Callable
from typing import Any
from urllib.parse import urlsplit

import pytest

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
    with pytest.raises(hooks.CatalogError) as error:
        hooks.read(data)
    lines = str(error.value).splitlines()
    assert lines[0] == f"projects.toml has {len(lines) - 2} problem(s):"
    assert lines[-1] == "The comments at the top of projects.toml describe every key."
    return [line.strip() for line in lines[1:-1]]


# The catalog of this repository.


def test_the_catalog_of_the_repository_has_every_project_in_both_languages() -> None:
    catalog = hooks.load(ROOT)

    assert catalog.languages == ("en", "de")
    assert [project.slug for project in catalog.projects] == [
        "homedarts-for-autodarts",
        "player-switch-for-autodarts",
        "paperless-sync",
        "paperless-unified-search",
        "issue-assistant",
        "repo-blueprint",
        "dashboard",
    ]
    for project in catalog.projects:
        for texts in (project.name, project.tagline, project.summary):
            assert set(texts) == {"en", "de"}


def test_the_home_page_groups_the_projects_by_their_readers() -> None:
    catalog = hooks.load(ROOT)

    assert {
        group.id: [project.slug for project in catalog.members(group)]
        for group in catalog.groups
    } == {
        "home-and-archive": [
            "homedarts-for-autodarts",
            "player-switch-for-autodarts",
            "paperless-sync",
            "paperless-unified-search",
        ],
        "maintainers": ["issue-assistant", "repo-blueprint"],
    }
    first, second = catalog.groups
    assert first.heading["en"] == "For the smart home and the document archive"
    assert second.heading["en"] == "For maintainers on GitHub"
    # The sentence under the Paperless cards links both of them, in both languages.
    assert first.note is not None
    assert second.note is None
    for note in first.note.values():
        for slug in ("paperless-sync", "paperless-unified-search"):
            assert f"](https://dennis-otto.github.io/{slug}/)" in note


def test_every_card_has_a_picture_from_the_social_preview_of_its_repository() -> None:
    catalog = hooks.load(ROOT)

    for project in catalog.projects:
        if project.group is None:
            continue
        assert project.picture is not None, project.slug
        assert project.picture.src == {
            "en": f"images/projects/{project.slug}.webp",
            "de": f"images/projects/de/{project.slug}.webp",
        }
        for language, alt in project.picture.alt.items():
            # Says what the picture shows, not only the name of the project.
            assert len(alt) > len(project.name["en"]) + 20, alt
            # The screenshot bot brings each new picture without a person, so the
            # alt says what every picture keeps, the name of the project first.
            assert project.name[language] in alt, (project.slug, language)
    assert hooks.pictures(catalog).splitlines() == [
        f"{project.repo} docs/images/projects/{project.slug}.webp {project.license}"
        for project in catalog.projects
        if project.group is not None
    ]


def test_the_german_home_page_shows_german_pictures_that_the_hub_draws(
    tmp_path: Path,
) -> None:
    # The social previews of the projects speak English, so the hub draws the
    # picture of every card in German: its name and its German tagline beside a
    # screenshot of its repository, in German where the project has one.
    catalog = hooks.load(ROOT)
    template = (ROOT / hooks.DRAWING).read_text(encoding="utf-8")
    icons = tmp_path / "icons"
    (icons / "material").mkdir(parents=True)
    (icons / "material" / "file-tree.svg").write_text("<svg/>", encoding="utf-8")

    lines = hooks.drawings(catalog, tmp_path / "pages", template, icons).splitlines()

    carded = [project for project in catalog.projects if project.group is not None]
    assert [line.split()[1] for line in lines] == [
        f"docs/images/projects/de/{project.slug}.webp" for project in carded
    ]
    german = {
        "homedarts-for-autodarts": "docs/images/de/card.png",
        "player-switch-for-autodarts": "docs/images/switcher.de.dark.png",
        "paperless-sync": "docs/images/de/archive-dark.png",
    }
    for project in carded:
        assert project.picture is not None
        drawing = project.picture.drawing
        assert drawing is not None, project.slug
        if project.slug in german:
            assert drawing.screenshot == {"de": german[project.slug]}
            assert "auf Deutsch" in project.picture.alt["de"]
        else:
            # Its screenshots speak English alone, so the alt promises no German.
            assert "auf Deutsch" not in project.picture.alt["de"]
        page = (tmp_path / "pages" / f"{project.slug}.de.html").read_text(
            encoding="utf-8"
        )
        assert '<html lang="de">' in page
        assert f"<h1>{escape(project.name['de'])}</h1>" in page
        assert "$" not in page


def webp_size(data: bytes) -> tuple[int, int]:
    """The width and height of a lossy WebP, from the frame header of its VP8 chunk."""
    assert data[:4] == b"RIFF"
    assert data[8:16] == b"WEBPVP8 "
    assert data[23:26] == bytes([0x9D, 0x01, 0x2A])
    width = int.from_bytes(data[26:28], "little") & 0x3FFF
    height = int.from_bytes(data[28:30], "little") & 0x3FFF
    return width, height


def test_the_pictures_are_small_webps_of_the_size_of_the_cards() -> None:
    for project in hooks.load(ROOT).projects:
        if project.picture is None:
            continue
        for src in set(project.picture.src.values()):
            picture = ROOT / "docs" / src
            data = picture.read_bytes()
            # Made by scripts/project-pictures.sh, unless the project has no repo.
            assert project.repo is None or webp_size(data) == hooks.PICTURE, picture
            # The home page stays light: 60 KB at most for each picture.
            assert len(data) <= 60_000, picture


def test_every_picture_names_the_license_of_its_repository_for_reuse() -> None:
    # The pictures come from the repositories of the projects, some of them under
    # the AGPL; REUSE needs the text of every license that a file names.
    licenses = {path.stem for path in (ROOT / "LICENSES").glob("*.txt")}

    for project in hooks.load(ROOT).projects:
        # A picture made by hand for a project without a repo is this repository's.
        if project.picture is None or project.repo is None:
            continue
        for src in set(project.picture.src.values()):
            sidecar = ROOT / "docs" / f"{src}.license"
            # REUSE-IgnoreStart
            assert sidecar.read_text(encoding="utf-8") == (
                "SPDX-FileCopyrightText: Dennis Otto and the contributors to "
                f"{project.repo}\n"
                f"SPDX-License-Identifier: {project.license}\n"
            )
            # REUSE-IgnoreEnd
        assert project.license in licenses


def test_homedarts_for_autodarts_keeps_the_addresses_of_ha_autodarts() -> None:
    # Its repository was Dennis-Otto/ha-autodarts until 2026-10-21, and its website
    # lived at /ha-autodarts/.
    catalog = hooks.load(ROOT)
    homedarts = catalog.projects[0]

    assert homedarts.repo == "Dennis-Otto/homedarts-for-autodarts"
    assert homedarts.former == ("ha-autodarts",)
    assert catalog.moves() == {"ha-autodarts": f"{SITE}homedarts-for-autodarts/"}
    # Every page of its sitemap on 2026-10-21, in both languages.
    pages = catalog.former_pages["ha-autodarts"]
    assert len(pages) == 72
    assert pages[0] == "index.html"
    for page in ("games.html", "de/index.html", "de/games.html", "branding/index.html"):
        assert page in pages, page
    assert sum(page.startswith("decisions/") for page in pages) == 25
    assert sum(page.startswith("de/") for page in pages) == 22
    # Its card keeps the anchor of the old slug, in both languages.
    for language in catalog.languages:
        assert '### <span id="ha-autodarts"></span>:material-bullseye-arrow:' in (
            hooks.cards(catalog, language)
        )


def test_the_german_blueprint_button_leads_to_the_german_section() -> None:
    blueprint = {project.slug: project for project in hooks.load(ROOT).projects}[
        "repo-blueprint"
    ]

    assert blueprint.start.url == {
        "en": "https://github.com/Dennis-Otto/repo-blueprint#start-a-repository",
        "de": "https://github.com/Dennis-Otto/repo-blueprint/blob/main/README.de.md"
        "#ein-repository-anlegen",
    }


def test_the_dashboard_has_no_repository_no_documentation_and_no_card() -> None:
    catalog = hooks.load(ROOT)
    projects = {project.slug: project for project in catalog.projects}
    dashboard = projects["dashboard"]

    assert dashboard.repo is None
    assert dashboard.docs is None
    assert dashboard.group is None
    # The card of the blueprint, which builds it, leads to it with its second button,
    # and to the website of the blueprint with its heading.
    blueprint = projects["repo-blueprint"]
    assert catalog.second(blueprint) == dashboard.start
    assert dashboard.start.label == {"en": "Dashboard", "de": "Dashboard"}
    assert "](https://dennis-otto.github.io/repo-blueprint/)" in hooks.card(
        blueprint, "en", catalog.second(blueprint)
    )


def test_both_home_pages_have_the_marker_of_the_cards_once() -> None:
    for page in ("docs/index.md", "docs/index.de.md"):
        markdown = (ROOT / page).read_text(encoding="utf-8")
        assert len(hooks.MARKER_LINE.findall(markdown)) == 1, page


def test_both_home_pages_have_the_newest_releases_below_the_cards() -> None:
    for page in ("docs/index.md", "docs/index.de.md"):
        markdown = (ROOT / page).read_text(encoding="utf-8")
        news = hooks.NEWS_LINE.findall(markdown)
        assert len(news) == 1, page
        cards = markdown.index(hooks.MARKER)
        heading = markdown.index("{ #whats-new }")
        # Under a heading of its own, after the cards, and with the sentence that
        # links the dashboard and the feed, for a reader without the script.
        assert cards < heading < markdown.index(hooks.NEWS_MARKER), page
        after = markdown[markdown.index(hooks.NEWS_MARKER) :].split("\n## ")[0]
        assert "](releases.md)" in after, page
        assert "https://dennis-otto.github.io/repo-blueprint/dashboard/)" in after
        assert hooks.ATOM in after, page


def test_both_releases_pages_have_the_marker_of_the_notes_once() -> None:
    for page in ("docs/releases.md", "docs/releases.de.md"):
        markdown = (ROOT / page).read_text(encoding="utf-8")
        assert len(hooks.NOTES_LINE.findall(markdown)) == 1, page
        # With the feed of all releases, for a feed reader, before the releases.
        assert markdown.index(hooks.ATOM) < markdown.index(hooks.NOTES_MARKER), page
    assert hooks.RELEASES_PAGE == "releases.html"


def test_every_project_with_a_repository_names_its_project_at_bestpractices_dev() -> None:
    # Every repository of a project has its project at bestpractices.dev, whose
    # badge its README shows with the same number, but Player Switch for Autodarts,
    # which has none yet: its card and the Trust page name no level for it.
    numbers = {
        project.slug: project.bestpractices
        for project in hooks.load(ROOT).projects
        if project.repo is not None
    }

    assert numbers == {
        "homedarts-for-autodarts": 14935,
        "player-switch-for-autodarts": None,
        "paperless-sync": 15277,
        "paperless-unified-search": 14256,
        "issue-assistant": 15278,
        "repo-blueprint": 15284,
    }


def test_the_script_reads_the_texts_of_the_facts_that_the_page_gives_it() -> None:
    script = (ROOT / "docs/javascripts/projects.js").read_text(encoding="utf-8")
    read = set(re.findall(r"labels\.([a-z]+)", script)) - {"locale"}

    assert read == set(hooks.SCRIPT)
    for name in ("project-facts", "project-news", "data-facts", "data-history"):
        assert name.removeprefix("data-") in script, name
    assert hooks.FACTS == "project-facts"


def test_the_pages_with_live_facts_alone_load_their_script() -> None:
    template = (ROOT / "overrides/facts.html").read_text(encoding="utf-8")
    home = (ROOT / "overrides/home.html").read_text(encoding="utf-8")
    config = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")

    assert "{{ super() }}" in template
    assert '<script src="{{ \'javascripts/projects.js\' | url }}"></script>' in template
    # The home pages load it once, through the template that they extend.
    assert '{% extends "facts.html" %}' in home
    assert "<script" not in home
    assert "projects.js" not in config
    # The Trust page and the Releases page in every language, whose table and newer
    # releases the script fills too.
    for page in (
        "docs/trust.md",
        "docs/trust.de.md",
        "docs/releases.md",
        "docs/releases.de.md",
    ):
        front = (ROOT / page).read_text(encoding="utf-8").split("\n---\n", 1)[0]
        assert re.search(r"^template: facts\.html$", front, re.MULTILINE), page


def test_the_catalog_has_the_texts_of_the_facts_in_both_languages() -> None:
    facts = hooks.load(ROOT).facts

    assert list(facts) == list(hooks.FACT_KEYS)
    assert facts["coverage"] == {"en": "{} test coverage", "de": "{} Testabdeckung"}
    for key in hooks.VALUED:
        assert all(text.count("{}") == 1 for text in facts[key].values()), key


def test_the_catalog_has_the_texts_of_the_trust_page_in_both_languages() -> None:
    trust = hooks.load(ROOT).trust

    assert list(trust.texts) == list(hooks.TRUST_KEYS)
    assert list(trust.values) == list(hooks.TRUST_VALUED)
    for texts in [*trust.texts.values(), *trust.values.values()]:
        assert set(texts) == {"en", "de"}
    assert trust.values["provenance"] == {
        "en": "SLSA Build Level 3",
        "de": "SLSA Build Level 3",
    }
    # The links to the security policy and to the form of every project go in {}.
    for key in hooks.TRUST_LINKED:
        assert all(text.count("{}") == 1 for text in trust.values[key].values()), key


def test_the_trust_page_verifies_the_file_that_each_project_ships() -> None:
    # The files of the latest release that the commands of the Trust page download:
    # the package that its users install, as Verify a release in the SECURITY.md of
    # each project names it, and the SBOM of a project that ships no package.
    verified = {
        project.slug: project.verified
        for project in hooks.load(ROOT).projects
        if project.repo is not None
    }

    assert verified == {
        "homedarts-for-autodarts": "homedarts.zip",
        "player-switch-for-autodarts": "player-switch-for-autodarts.spdx.json",
        "paperless-sync": "paperless_sync.tar.gz",
        "paperless-unified-search": "paperless_unified_search.tar.gz",
        "issue-assistant": "issue-assistant.spdx.json",
        "repo-blueprint": "repo-blueprint.spdx.json",
    }


def test_both_trust_pages_have_the_guarantees_and_then_the_commands() -> None:
    for page in ("docs/trust.md", "docs/trust.de.md"):
        markdown = (ROOT / page).read_text(encoding="utf-8")
        assert len(hooks.SHARED_LINE.findall(markdown)) == 1, page
        assert len(hooks.TRUST_LINE.findall(markdown)) == 1, page
        assert len(hooks.VERIFY_LINE.findall(markdown)) == 1, page
        # Each part under its heading in the source, so that markdownlint finds the
        # anchors that the page links: {#every-project}, then {#numbers}.
        shared = markdown.index("{#every-project}\n\n" + hooks.SHARED_MARKER)
        numbers = markdown.index("{#numbers}\n\n" + hooks.TRUST_MARKER)
        assert shared < numbers < markdown.index(hooks.VERIFY_MARKER), page
        # They link the security page of the website itself, and the decisions.
        assert "](security.md)" in markdown, page


def test_the_menu_has_the_tabs_home_trust_and_about() -> None:
    text = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    nav = text[text.index("\nnav:\n") :].split("\n\n", 1)[0]

    # A tab for each entry at the top, and the pages of a tab in its section: the
    # security page of the website under Trust, the automation under About.
    assert re.findall(r"^  - ([A-Za-z]+):", nav, re.MULTILINE) == [
        "Home",
        "Trust",
        "About",
    ]
    for page in ("trust.md", "security.md", "about.md", "automation.md"):
        assert page in nav, page
    # The blueprint adds its automation page to the menu of every website that
    # doesn't name it, as a tab of its own.
    assert re.search(r"^      - automation\.md$", nav, re.MULTILINE)


def test_the_groups_follow_the_heading_of_the_hero() -> None:
    # The hero of the template has the heading of the first level, so the page has
    # none before the groups, whose headings are of the second level and those of
    # the cards of the third: a screen reader lists them with no level left out.
    for page in ("docs/index.md", "docs/index.de.md"):
        markdown = (ROOT / page).read_text(encoding="utf-8")
        marker = hooks.MARKER_LINE.search(markdown)
        assert marker is not None, page
        # The text of the page, after its front matter.
        body = markdown[markdown.index("---", 3) + 3 : marker.start()]
        assert [line for line in body.splitlines() if line.startswith("#")] == []


def test_mkdocs_runs_the_hooks_of_every_website_and_those_of_this_one() -> None:
    # Without the hook, the marker stays a comment and the home pages lose their
    # cards while the strict build passes.
    text = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    listed = re.search(r"^hooks:\n((?:[ \t]+- .*\n)+)", text, re.MULTILINE)

    assert listed is not None
    assert re.findall(r"- (\S+)", listed.group(1)) == [
        ".github/mkdocs_blueprint.py",
        ".github/mkdocs_project.py",
    ]


def test_the_readme_of_the_repository_has_the_table_of_the_catalog() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")

    assert hooks.readme(text, hooks.load(ROOT)) == text


def test_the_table_holds_every_address_of_the_catalog_for_the_link_check() -> None:
    # The Links workflow checks the Markdown files alone, not projects.toml.
    catalog = hooks.load(ROOT)
    table = hooks.table(catalog)

    for project in catalog.projects:
        buttons = [project.start]
        if project.docs is not None:
            buttons.append(project.docs)
        for button in buttons:
            for url in button.url.values():
                assert f"]({url})" in table, url


def test_the_pages_of_the_repository_have_their_translations(
    caplog: pytest.LogCaptureFixture,
) -> None:
    hooks.check_pages(ROOT / "docs", [language("en"), language("de")])

    assert caplog.messages == []


def test_the_catalog_names_the_license_and_the_platform_of_every_repository() -> None:
    # The licenses as the REUSE.toml of each repository names them.
    projects = hooks.load(ROOT).projects

    assert {p.slug: (p.license, p.platform) for p in projects} == {
        "homedarts-for-autodarts": ("MIT", "Home Assistant"),
        "player-switch-for-autodarts": ("MIT", "Google Chrome"),
        "paperless-sync": ("AGPL-3.0-or-later", "Nextcloud"),
        "paperless-unified-search": ("AGPL-3.0-or-later", "Nextcloud"),
        "issue-assistant": ("MIT", "GitHub Actions"),
        "repo-blueprint": ("MIT-0", "Copier"),
        "dashboard": (None, None),
    }


def front_matter(page: str) -> str:
    """The front matter of a page of docs/."""
    text = (ROOT / "docs" / page).read_text(encoding="utf-8")
    match = re.match(r"---\n(.*?)\n---\n", text, re.DOTALL)
    assert match is not None, page
    return match.group(1)


@pytest.mark.parametrize(
    ("page", "title", "card"),
    [
        (
            "index.md",
            "Open-source apps for Home Assistant, Nextcloud and Paperless-ngx",
            "Home Assistant, Nextcloud and Paperless-ngx",
        ),
        (
            "index.de.md",
            "Open-Source-Apps für Home Assistant, Nextcloud und Paperless-ngx",
            "Home Assistant, Nextcloud und Paperless-ngx",
        ),
    ],
)
def test_both_home_pages_name_the_projects_in_the_title_of_search_results(
    page: str, title: str, card: str
) -> None:
    # Material puts the title into <title> and og:title, instead of the bare name
    # of the website or "Startseite", and the preview card shows the shorter one.
    meta = front_matter(page)
    keys = dict(re.findall(r'^(\w+): "?(.+?)"?$', meta, re.MULTILINE))

    assert keys["title"] == title
    assert f"social:\n  cards_layout_options:\n    title: {card}\n" in meta
    # Short enough for search engines to show it whole.
    assert 50 <= len(keys["description"]) <= 160
    assert "Paperless-ngx" in keys["description"]


def test_mkdocs_takes_the_404_page_from_the_overrides_of_the_website() -> None:
    text = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")

    assert re.search(r"^theme:\n  custom_dir: overrides$", text, re.MULTILINE)
    assert re.search(
        r"^site_url: https://dennis-otto\.github\.io/$", text, re.MULTILINE
    )
    assert (ROOT / "overrides" / "404.html").is_file()


HERO_KEYS = ("lead", "projects", "sponsor")


@pytest.mark.parametrize("page", ["index.md", "index.de.md"])
def test_both_home_pages_are_landing_pages_with_a_hero(page: str) -> None:
    meta = front_matter(page)

    assert re.search(r"^template: home\.html$", meta, re.MULTILINE)
    # Neither the menu nor the outline nor a footer that leads to the next page.
    assert "hide:\n  - navigation\n  - toc\n  - footer\n" in meta
    hero = re.search(r"^hero:\n((?:  .*\n?)+)", meta, re.MULTILINE)
    assert hero is not None
    keys = re.findall(r"^  (\w+): \S", hero.group(1), re.MULTILINE)
    assert tuple(keys) == HERO_KEYS


def test_the_hero_has_the_heading_and_leads_to_the_projects() -> None:
    template = (ROOT / "overrides" / "home.html").read_text(encoding="utf-8")
    markup = template.split("-#}", 1)[1]

    # Through the template of the pages with live facts, for the script of the cards.
    assert '{% extends "facts.html" %}' in markup
    assert markup.count("<h1>") == 1
    assert "<h1>{{ config.site_name | e }}</h1>" in markup
    assert f'href="#{hooks.PROJECTS}"' in markup
    assert f'href="{hooks.SPONSORS}"' in markup
    for key in HERO_KEYS:
        assert f"{{{{ hero.{key} | e }}}}" in markup
    # No pencil that edits the page and no date of its last change: the block of the
    # content of the theme, which has both, is replaced, not extended.
    assert "{% block content %}" in markup
    content = markup.split("{% block content %}", 1)[1].split("{% endblock %}", 1)[0]
    assert "super()" not in content
    assert "partials/actions.html" not in markup
    assert "{{ page.content }}" in content


def test_the_header_leads_to_the_profile_and_the_pencil_to_this_repository() -> None:
    text = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")

    assert re.search(r"^repo_url: https://github\.com/Dennis-Otto$", text, re.M)
    assert re.search(r"^repo_name: Dennis-Otto$", text, re.M)
    # Absolute, since the address of the header is no longer the repository.
    assert re.search(
        r"^edit_uri: https://github\.com/Dennis-Otto/dennis-otto\.github\.io/edit/"
        r"main/docs/$",
        text,
        re.M,
    )
    assert "  logo: assets/logo.svg\n  favicon: assets/logo.svg\n" in text
    assert (ROOT / "docs" / "assets" / "logo.svg").is_file()
    # The Releases page in the section Home, which the home page leads to.
    assert (
        "nav:\n  - Home:\n      - index.md\n      - Releases: releases.md\n"
        "  - Trust:\n" in text
    )
    assert (
        "          Home: Startseite\n          Releases: Neuigkeiten\n"
        "          Trust: Vertrauen\n" in text
    )
    # The decision records left the menu; the security page and the About page link
    # them.
    for page in ("security.md", "about.md"):
        markdown = (ROOT / "docs" / page).read_text(encoding="utf-8")
        assert "](decisions/README.md)" in markdown, page


def test_the_readme_shows_the_website_in_the_colors_of_the_reader() -> None:
    # scripts/screenshots.sh takes both pictures. The link check reads no srcset, so
    # this test notices a picture that is gone or renamed.
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert (
        '<source media="(prefers-color-scheme: dark)" '
        'srcset="docs/images/website-dark.png">'
    ) in readme
    assert '<img src="docs/images/website-light.png" alt="' in readme
    for scheme in ("light", "dark"):
        picture = (ROOT / "docs" / "images" / f"website-{scheme}.png").read_bytes()
        assert picture[:8] == b"\x89PNG\r\n\x1a\n"
        assert picture[12:16] == b"IHDR"
        size = (int.from_bytes(picture[16:20]), int.from_bytes(picture[20:24]))
        assert size == (1280, 800), scheme
    # The pictures are the README's alone: the website leaves them out.
    text = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    block = re.search(r"^exclude_docs: \|\n((?:  .+\n)+)", text, re.M)
    assert block is not None
    assert "/images/website-*.png" in block[1].split()


def test_the_readme_picture_names_the_first_group_and_its_projects() -> None:
    # 1280×800 pixels show the hero and the first group of the home page. Its alt
    # tells those who can't see the picture which projects it shows, so a project
    # that joins the first group needs its name there, as Add a project says.
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    alt = re.search(r'<img src="docs/images/website-light\.png" alt="([^"]+)"', readme)
    assert alt is not None
    catalog = hooks.load(ROOT)
    first = catalog.groups[0]

    assert first.heading["en"] in alt[1]
    for project in catalog.members(first):
        assert project.name["en"] in alt[1], project.slug


def test_the_screenshots_renew_the_card_pictures_before_they_show_them() -> None:
    # The screenshot bot runs scripts/screenshots.sh every week, after every release
    # and on demand, so the cards follow the social previews of the projects, and
    # the pictures of the README show the cards with their new pictures.
    text = (ROOT / "scripts" / "screenshots.sh").read_text(encoding="utf-8")
    lines = text.splitlines()

    renew = lines.index("bash scripts/project-pictures.sh")
    build = next(i for i, line in enumerate(lines) if '"$mkdocs" build' in line)
    assert renew < build


def commit_all(root: Path, message: str) -> None:
    """Commit every file of root, unsigned and by a test author."""
    git = ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com"]
    subprocess.run([*git, "add", "--all"], cwd=root, check=True)
    subprocess.run(
        [*git, "-c", "commit.gpgsign=false", "commit", "--quiet", "-m", message],
        cwd=root,
        check=True,
    )


def screenshots_due(root: Path, path: str) -> bool:
    """Whether the screenshot bot of the blueprint renders after a commit that
    changes only path, asked as its workflow asks: `blueprint.py screenshots due`.
    The bot runs in a process of its own: the blueprint tests it, and the coverage
    of these tests is that of this project."""
    file = root / path
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(f"A change of {path}.\n", encoding="utf-8")
    commit_all(root, f"Change {path}")
    run = subprocess.run(
        [sys.executable, "-B", "-E", "-s", str(ROOT / ".github" / "blueprint.py"),
         "screenshots", "due", "--since", "HEAD~1"],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    # 0 renders, 1 doesn't; anything else, or a word on stderr, is an error.
    assert run.returncode in (0, 1) and not run.stderr, run.stderr
    return run.returncode == 0


def test_a_change_of_the_home_page_or_its_cards_starts_the_screenshot_bot(
    tmp_path: Path,
) -> None:
    # After a change of main, the bot renders only when the change touches a file
    # of .github/screenshots-paths.txt.
    for path in (".github/screenshots-paths.txt", "scripts/screenshots.sh"):
        (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / path, tmp_path / path)
    subprocess.run(["git", "init", "--quiet"], cwd=tmp_path, check=True)
    commit_all(tmp_path, "Base")

    for path in (
        "projects.toml",
        "scripts/project-pictures.sh",
        ".github/card-picture.html",
        "scripts/screenshots.sh",
        "docs/index.md",
        "docs/index.de.md",
        "docs/assets/logo.svg",
        "docs/stylesheets/extra.css",
        "docs/javascripts/projects.js",
        "overrides/home.html",
        "mkdocs.yml",
        ".github/mkdocs_project.py",
        ".github/mkdocs-blueprint.css",
    ):
        assert screenshots_due(tmp_path, path), path
    # The pictures that the bot commits start no run of their own, and neither does
    # a page that the pictures don't show.
    for path in (
        "docs/images/projects/homedarts-for-autodarts.webp",
        "docs/images/website-light.png",
        "docs/about.md",
        "README.md",
    ):
        assert not screenshots_due(tmp_path, path), path


@pytest.mark.parametrize("script", ["icons.sh", "project-pictures.sh", "screenshots.sh"])
def test_the_pictures_come_from_the_same_chromium_on_every_machine(script: str) -> None:
    # Playwright's image has an amd64 and an arm64 build, and the Chromium of the
    # arm64 build draws other bytes and lives in another folder. So the script runs
    # the amd64 build everywhere, emulated on ARM, and a run on Apple silicon
    # changes no picture.
    text = (ROOT / "scripts" / script).read_text(encoding="utf-8")
    runs = re.findall(r"docker run .*", text)

    assert runs
    for run in runs:
        assert "--platform linux/amd64 " in run, run
    assert "/chrome-headless-shell-linux64/" in text


# A number of websites or projects in a text is wrong after the next project, and an
# accepted decision record would have to change with it: the texts say "every
# website" and list the projects only where a test checks them against projects.toml.
NUMBERS = (
    r"\d+|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve"
    r"|zwei|drei|vier|fünf|sechs|sieben|acht|neun|zehn|elf|zwölf"
)
COUNTED = re.compile(
    rf"\b(?:{NUMBERS})\s+(?:(?:more|other|weitere|andere)\s+)?"
    r"(?:project\s+|projekt-)?"
    r"(?:websites|repositories|repositorys|projects|projekte|folders|ordner)\b"
    rf"|\b(?:all|alle|of\s+the|der)\s+(?:{NUMBERS})\b",
    re.IGNORECASE,
)


@pytest.mark.parametrize(
    ("text", "counted"),
    [
        ("all six websites", True),
        ("Five more websites → the same address", True),
        ("the five project websites included", True),
        ("Fünf weitere Websites", True),
        ("die fünf Projekt-Websites", True),
        ("außerhalb der fünf Projekt-Ordner", True),
        ("Six repositories publish a website", True),
        ("For your browser, all six are one origin", True),
        ("die heikelste der sechs.", True),
        ("6 websites", True),
        ("every website at the address", False),
        ("Six boundaries. 1, a pull request", False),
        ("three sentences about the projects", False),
        ("the 404 page of the whole address", False),
    ],
)
def test_a_number_of_websites_is_found_in_a_text(text: str, counted: bool) -> None:
    assert bool(COUNTED.search(text)) is counted


def test_no_text_names_a_number_of_websites() -> None:
    paths = [
        ROOT / "README.md",
        ROOT / "mkdocs.yml",
        ROOT / "projects.toml",
        *sorted((ROOT / "docs").rglob("*.md")),
        *sorted((ROOT / "docs" / "diagrams").glob("*.mmd")),
        *sorted((ROOT / "overrides").rglob("*.html")),
    ]
    found = [
        f"{path.relative_to(ROOT).as_posix()}: {match[0]}"
        for path in paths
        for match in COUNTED.finditer(path.read_text(encoding="utf-8"))
    ]

    assert found == []


def test_the_issue_chooser_links_the_issues_of_every_project() -> None:
    # The forms of this repository are about the website; the chooser sends a
    # question about a project to the issues of its own repository.
    path = ROOT / ".github" / "ISSUE_TEMPLATE" / "config.yml"
    text = path.read_text(encoding="utf-8")

    for project in hooks.load(ROOT).projects:
        if project.repo is not None:
            url = f"https://github.com/{project.repo}/issues/new/choose"
            assert f"    url: {url}\n" in text, project.slug


def test_the_root_of_the_address_has_the_icons_that_browsers_ask_for() -> None:
    # MkDocs copies both from docs/ to the root of the website.
    icon = (ROOT / "docs" / "favicon.ico").read_bytes()
    # The header of an ICO file: reserved, type 1 and the number of images, then an
    # entry of 16 bytes per image that starts with its width and its height.
    assert icon[:4] == b"\x00\x00\x01\x00"
    count = int.from_bytes(icon[4:6], "little")
    entries = [icon[6 + 16 * index : 8 + 16 * index] for index in range(count)]
    assert sorted((width, height) for width, height in entries) == [
        (16, 16),
        (32, 32),
        (48, 48),
    ]
    touch = (ROOT / "docs" / "apple-touch-icon.png").read_bytes()
    assert touch[:8] == b"\x89PNG\r\n\x1a\n"
    assert (int.from_bytes(touch[16:20]), int.from_bytes(touch[20:24])) == (180, 180)
    # Color without alpha, which iOS would show as black.
    assert touch[25] == 2


def test_the_404_page_links_every_project_absolutely() -> None:
    # GitHub Pages serves the page at any depth, where a relative link leads nowhere.
    template = (ROOT / "overrides" / "404.html").read_text(encoding="utf-8")

    assert '{% extends "main.html" %}' in template
    # The heading in both languages, like every sentence of the page.
    assert '<h1>Page not found <span lang="de">· Seite nicht gefunden</span></h1>' in (
        template
    )
    assert "{% for project in catalog.projects %}" in template
    # Its script, overrides/partials/not-found.js, gets the projects and the old
    # folders as JSON; tests/not-found.test.mjs runs it.
    assert (
        '{{ {"moves": catalog.moves(), "projects": catalog.directory()} | tojson }}'
        in template
    )
    assert '{% include "partials/not-found.js" %}' in template
    assert re.findall(r'href="([^"]*)"', template) == [
        "{{ project.website[catalog.default] }}",
        "{{ config.site_url }}",
        "{{ config.site_url }}de/",
    ]


def test_the_policy_of_security_txt_is_a_page_of_the_website() -> None:
    assert hooks.POLICY == "security.html"
    assert (ROOT / "docs" / "security.md").is_file()


@pytest.mark.parametrize(
    ("page", "locale", "heading"),
    [
        ("security.md", "en", "Security and privacy"),
        ("security.de.md", "de", "Sicherheit und Datenschutz"),
    ],
)
def test_the_security_page_links_the_report_form_of_every_website(
    page: str, locale: str, heading: str
) -> None:
    # security.txt makes the page the policy of every website at the address, so
    # it links each of them, in the language of the page, and the private report
    # form of the repository that builds it; the dashboard is Repo Blueprint's.
    text = (ROOT / "docs" / page).read_text(encoding="utf-8")

    assert f"\n# {heading}\n" in text
    assert f"]({hooks.CONTACT})" in text
    for project in hooks.load(ROOT).projects:
        assert f"]({project.website[locale]})" in text, project.slug
        if project.repo is not None:
            form = f"https://github.com/{project.repo}/security/advisories/new"
            assert f"]({form})" in text, project.slug
    # The decision records stay in English, and both pages link them.
    assert "](decisions/README.md)" in text


def test_the_repository_gains_the_topics_of_a_website() -> None:
    github = ROOT / ".github"
    settings = tomllib.loads((github / "repository.toml").read_text(encoding="utf-8"))
    project = tomllib.loads(
        (github / "repository.project.toml").read_text(encoding="utf-8")
    )
    topics = project["repository"]["topics"]

    assert topics == [
        "mkdocs-material",
        "personal-website",
        "developer-portfolio",
        "self-hosted",
        "open-source",
    ]
    # GitHub takes at most 20 topics, and the settings bot adds these to the others.
    assert len(set(settings["repository"]["topics"]) | set(topics)) <= 20


# Reading projects.toml.


def test_a_valid_catalog_is_read_with_an_address_in_every_language() -> None:
    catalog = hooks.read(catalog_data(entry(docs="https://example.org/docs/")))

    project = catalog.projects[0]
    assert catalog.default == "en"
    assert project.repo == "Dennis-Otto/tool"
    assert project.start == hooks.Link(
        "material-download",
        {"en": "Install", "de": "Installieren"},
        {"en": "https://example.org/install", "de": "https://example.org/install"},
    )
    assert project.docs == hooks.Link(
        "material-book",
        {"en": "Documentation", "de": "Dokumentation"},
        {"en": "https://example.org/docs/", "de": "https://example.org/docs/"},
    )


def test_a_language_without_its_own_address_takes_that_of_the_first() -> None:
    data = catalog_data(entry(docs={"en": "https://example.org/docs/"}))

    project = hooks.read(data).projects[0]

    assert project.docs is not None
    assert project.docs.url == {
        "en": "https://example.org/docs/",
        "de": "https://example.org/docs/",
    }


def test_repo_and_docs_may_be_left_out() -> None:
    project = without_repo(entry())
    del project["docs"]

    read = hooks.read(catalog_data(project)).projects[0]

    assert read.repo is None
    assert read.license is None
    assert read.platform is None
    assert read.docs is None


def test_a_project_with_a_repo_names_its_license_and_its_platform() -> None:
    project = entry()
    del project["license"], project["platform"]

    assert problems(catalog_data(project)) == [
        "tool: license is missing.",
        "tool: platform is missing.",
    ]


def test_license_and_platform_are_for_a_project_with_a_repo() -> None:
    project = entry()
    del project["repo"]

    assert problems(catalog_data(project)) == [
        "tool: license is for a project with a repo.",
        "tool: platform is for a project with a repo.",
    ]


@pytest.mark.parametrize("spdx", ["MIT", "MIT-0", "AGPL-3.0-or-later", "Apache-2.0"])
def test_a_license_is_an_spdx_identifier(spdx: str) -> None:
    assert hooks.read(catalog_data(entry(license=spdx))).projects[0].license == spdx


@pytest.mark.parametrize("spdx", ["MIT License", "MIT OR Apache-2.0", "-MIT", "GPL/2"])
def test_a_license_that_is_no_spdx_identifier_is_named(spdx: str) -> None:
    assert problems(catalog_data(entry(license=spdx))) == [
        "tool: license must be the SPDX identifier of a license, such as MIT or "
        f"AGPL-3.0-or-later, not {spdx!r}."
    ]


def test_the_website_of_a_project_is_its_documentation_or_its_start() -> None:
    plain = entry("plain")
    del plain["docs"]

    tool, plain_project = hooks.read(catalog_data(entry(), plain)).projects

    assert tool.website == {
        "en": "https://dennis-otto.github.io/tool/",
        "de": "https://dennis-otto.github.io/tool/de/",
    }
    assert plain_project.website == {
        "en": "https://example.org/install",
        "de": "https://example.org/install",
    }


@pytest.mark.parametrize(
    "languages",
    [None, "en", [], ["en", 1], ["en", "Deutsch"], ["en", "de", "en"]],
)
def test_the_languages_must_be_a_list_of_distinct_codes(languages: Any) -> None:
    data = catalog_data()
    data["languages"] = languages

    with pytest.raises(hooks.CatalogError, match="languages must list the language"):
        hooks.read(data)


def test_a_missing_german_text_is_named_with_its_project() -> None:
    project = entry("homedarts-for-autodarts")
    del project["summary"]["de"]

    assert problems(catalog_data(project)) == [
        "homedarts-for-autodarts: summary.de is missing."
    ]


def test_every_problem_of_the_catalog_is_named_at_once() -> None:
    first = entry("one", icon="Material Tools", sumary="typo")
    first["name"] = "Only English"
    second = entry("two", repo="two", docs={"de": "http://example.org"})
    second["start"]["label"]["fr"] = "Installer"
    data = catalog_data(first, second)
    data["colors"] = "blue"

    assert problems(data) == [
        "colors is unknown; known are languages, documentation, facts, trust, "
        "requirements, group, project.",
        "one: sumary is unknown; known are slug, repo, license, platform, "
        "bestpractices, asset, requires, group, icon, name, short, tagline, summary, "
        "image, alt, drawing, start, docs, former, second.",
        "one: icon must be an icon of Material for MkDocs, such as material-download,"
        " not 'Material Tools'.",
        "one: name needs a text in every language: name.en, name.de.",
        "two: repo must be a repository on GitHub, such as "
        "Dennis-Otto/homedarts-for-autodarts, not 'two'.",
        "two: start.label.fr is in a language that languages doesn't list (en, de).",
        "two: docs.en is missing; the other languages take it when they have no "
        "address.",
        "two: docs.de must be an address with https:// and without spaces or "
        "parentheses, not 'http://example.org'.",
    ]


@pytest.mark.parametrize(
    ("value", "message"),
    [
        (7, "must be a text on one line"),
        ("  ", "must be a text on one line"),
        ("Two\nlines", "must be a text on one line"),
    ],
)
def test_a_text_must_be_a_text_on_one_line(value: object, message: str) -> None:
    project = entry()
    project["summary"]["en"] = value

    assert problems(catalog_data(project)) == [f"tool: summary.en {message}."]


def test_an_address_must_hold_no_spaces_or_parentheses() -> None:
    project = entry()
    project["start"]["url"] = "https://example.org/a (b)"

    assert problems(catalog_data(project)) == [
        "tool: start.url must be an address with https:// and without spaces or "
        "parentheses, not 'https://example.org/a (b)'."
    ]


def test_a_missing_or_wrong_table_is_named_once() -> None:
    first = entry("one")
    del first["start"]
    second = entry("two", start="https://example.org")
    data = catalog_data(first, second)
    del data["documentation"]

    assert problems(data) == [
        "documentation is missing.",
        "one: start is missing.",
        "two: start must be a table.",
    ]


def test_a_project_without_a_valid_slug_is_named_by_its_number() -> None:
    nameless = entry()
    del nameless["slug"]

    bad = entry(
        "Bad Slug",
        repo="Dennis-Otto/bad",
        docs="https://example.org/",
        image="images/bad.webp",
    )

    assert problems(catalog_data(entry(), "tool", nameless, bad)) == [
        "project 2 must be a table.",
        "project 3: slug is missing.",
        "project 4: slug must be lowercase letters, digits and hyphens, such as "
        "homedarts-for-autodarts, not 'Bad Slug'.",
    ]


@pytest.mark.parametrize("projects", [None, [], {"slug": "tool"}])
def test_the_catalog_must_list_projects(projects: object) -> None:
    data = catalog_data()
    data["project"] = projects

    assert problems(data) == [
        "project must list the projects as [[project]] tables.",
        "group tools has no project.",
    ]


@pytest.mark.parametrize("groups", [None, [], {"id": "tools"}])
def test_the_catalog_must_list_groups(groups: object) -> None:
    data = catalog_data()
    data["group"] = groups

    assert problems(data) == [
        "group must list the groups as [[group]] tables.",
        "tool: group must be the id of a group of the catalog (none), not 'tools'.",
    ]


def test_a_group_has_a_heading_and_may_have_a_note() -> None:
    note = {"en": "[Both](#tool) work together.", "de": "[Beide](#tool) zusammen."}
    data = catalog_data(entry(), entry("other", group="more"))
    data["group"].append(group_data("more", note=note))

    catalog = hooks.read(data)

    assert catalog.groups == (
        hooks.Group("tools", {"en": "Tools", "de": "Werkzeuge"}, None),
        hooks.Group("more", {"en": "Tools", "de": "Werkzeuge"}, note),
    )
    assert [[p.slug for p in catalog.members(group)] for group in catalog.groups] == [
        ["tool"],
        ["other"],
    ]


def test_a_project_may_name_the_folders_where_its_website_lived_before() -> None:
    catalog = hooks.read(
        catalog_data(entry(former=["old-tool", "older-tool"]), entry("two"))
    )
    moved, other = catalog.projects

    assert moved.former == ("old-tool", "older-tool")
    assert other.former == ()
    assert catalog.moves() == {
        "old-tool": f"{SITE}tool/",
        "older-tool": f"{SITE}tool/",
    }
    # read alone reads no file: load adds the pages of the former websites.
    assert catalog.former_pages == {}


def test_the_new_folder_is_that_of_the_website_in_the_default_language() -> None:
    docs = {"en": f"{SITE}new/guide.html", "de": f"{SITE}de/"}
    project = entry(former=["old"], docs=docs)

    assert hooks.read(catalog_data(project)).moves() == {"old": f"{SITE}new/"}


@pytest.mark.parametrize(
    ("former", "message"),
    [
        (
            "old",
            "must list the folders of the address where its website lived before, "
            'such as ["ha-autodarts"]',
        ),
        (
            [],
            "must list the folders of the address where its website lived before, "
            'such as ["ha-autodarts"]',
        ),
        (
            ["Old Tool"],
            "must be lowercase letters, digits and hyphens, such as "
            "homedarts-for-autodarts, not 'Old Tool'",
        ),
        ([7], "must be a text on one line"),
        (["old", "older", "old"], "names 'old' more than once"),
    ],
)
def test_former_lists_folders_of_the_address(former: object, message: str) -> None:
    assert problems(catalog_data(entry(former=former))) == [f"tool: former {message}."]


@pytest.mark.parametrize(
    "docs",
    [
        None,
        "https://elsewhere.example.org/tool/",
        hooks.SITE,
        f"{hooks.SITE}index.html",
    ],
)
def test_former_needs_a_website_in_a_folder_of_the_address(docs: str | None) -> None:
    project = entry(former=["old"], docs=docs)
    if docs is None:
        del project["docs"]

    assert problems(catalog_data(project)) == [
        f"tool: former is for a project whose docs are a website in a folder of {SITE},"
        " where the old addresses lead."
    ]


def test_former_names_no_folder_or_anchor_that_is_in_use() -> None:
    data = catalog_data(
        entry(former=["de", "tools", "two", "docs-of-two", "elsewhere", "shared"]),
        entry("two", docs=f"{SITE}docs-of-two/guide.html", former=["shared"]),
        # Its website is elsewhere, so it takes no folder of the address.
        entry("three", docs="https://elsewhere.example.org/elsewhere/"),
    )
    in_use = (
        "which the address or the home page uses already: as a language, the folder "
        "of a website, a slug or the id of a group."
    )

    assert problems(data) == [
        f"tool: former names 'de', {in_use}",
        f"tool: former names 'tools', {in_use}",
        f"tool: former names 'two', {in_use}",
        f"tool: former names 'docs-of-two', {in_use}",
        "tool: former names 'shared', which another project names too.",
        "two: former names 'shared', which another project names too.",
    ]


def test_the_pages_of_a_former_website_are_read_from_its_list(tmp_path: Path) -> None:
    catalog = hooks.read(catalog_data(entry(former=["old-tool", "older-tool"])))
    (tmp_path / "former").mkdir()
    (tmp_path / "former" / "old-tool.txt").write_text(
        "# The pages of the old website.\n\nindex.html\n  de/games.html  \n"
        "decisions/0001-a_b.c.html\nindex.html\n",
        encoding="utf-8",
    )
    (tmp_path / "former" / "older-tool.txt").write_text("guide.html\n", encoding="utf-8")

    assert hooks.former_pages(catalog, tmp_path) == {
        "old-tool": ("index.html", "de/games.html", "decisions/0001-a_b.c.html"),
        "older-tool": ("guide.html",),
    }


def test_every_problem_of_the_lists_of_the_former_websites_is_named(
    tmp_path: Path,
) -> None:
    catalog = hooks.read(
        catalog_data(entry(former=["broken", "empty", "missing"]))
    )
    (tmp_path / "former").mkdir()
    (tmp_path / "former" / "broken.txt").write_text(
        "games.html\n/index.html\n../up.html\n.hidden/page.html\npicture.png\n"
        "a page.html\nde/\n",
        encoding="utf-8",
    )
    (tmp_path / "former" / "empty.txt").write_text("# Nothing yet.\n", encoding="utf-8")

    with pytest.raises(hooks.CatalogError) as error:
        hooks.former_pages(catalog, tmp_path)

    lines = str(error.value).splitlines()
    page = (
        "must be the path of a page from the folder of the website, such as "
        "games.html or de/index.html"
    )
    assert lines[0] == "The pages of the former websites have 8 problem(s):"
    assert lines[1:7] == [
        f"  former/broken.txt:{number} {page}, not {line!r}."
        for number, line in [
            (2, "/index.html"),
            (3, "../up.html"),
            (4, ".hidden/page.html"),
            (5, "picture.png"),
            (6, "a page.html"),
            (7, "de/"),
        ]
    ]
    assert lines[7] == "  former/empty.txt lists no page of the former website."
    assert lines[8].startswith(
        "  former/missing.txt, the pages of the former website of tool, can't be read: "
    )
    assert lines[9] == "The comments at the top of projects.toml describe former."


def test_the_catalog_needs_the_lists_of_its_former_websites(tmp_path: Path) -> None:
    shutil.copyfile(ROOT / "projects.toml", tmp_path / "projects.toml")

    with pytest.raises(hooks.CatalogError, match=r"former/ha-autodarts\.txt, the"):
        hooks.load(tmp_path)


def test_a_project_may_have_a_short_name_in_every_language() -> None:
    short = {"en": "Tool", "de": "Werkzeug"}
    catalog = hooks.read(catalog_data(entry(short=short), entry("plain")))

    assert [project.short for project in catalog.projects] == [short, None]


@pytest.mark.parametrize(
    ("short", "problem"),
    [
        ({"en": "Tool"}, "tool: short.de is missing."),
        ("Tool", "tool: short needs a text in every language: short.en, short.de."),
    ],
)
def test_a_short_name_needs_every_language(short: object, problem: str) -> None:
    assert problems(catalog_data(entry(short=short))) == [problem]


def test_every_problem_of_a_group_is_named() -> None:
    data = catalog_data(entry(), entry("other", group="Bad Id"))
    nameless = group_data(heading={"en": "Only English"}, colour="red")
    del nameless["id"]
    data["group"] += [
        nameless,
        "more",
        group_data("Bad Id"),
        group_data("tools", note="One language"),
        group_data("empty"),
    ]

    assert problems(data) == [
        "group 2: colour is unknown; known are id, heading, note.",
        "group 2: id is missing.",
        "group 2: heading.de is missing.",
        "group 3 must be a table.",
        "group 4: id must be lowercase letters, digits and hyphens, such as "
        "homedarts-for-autodarts, not 'Bad Id'.",
        "group tools: note needs a text in every language: note.en, note.de.",
        "other: group must be lowercase letters, digits and hyphens, such as "
        "homedarts-for-autodarts, not 'Bad Id'.",
        "group tools: id names more than one group.",
        "group empty has no project.",
    ]


def test_a_project_names_a_group_of_the_catalog() -> None:
    assert problems(catalog_data(entry(), entry("other", group="toys"))) == [
        "other: group must be the id of a group of the catalog (tools), not "
        "'toys'.",
    ]


def test_a_card_needs_a_picture_with_a_text_for_those_who_cant_see_it() -> None:
    project = entry()
    del project["image"], project["alt"]

    assert problems(catalog_data(project)) == [
        "tool: image is missing.",
        "tool: alt needs a text in every language: alt.en, alt.de.",
    ]


@pytest.mark.parametrize(
    "image", ["images/tool.webp", "tool.png", "a/b-c/d_e.svg", "x.jpg", "x.avif"]
)
def test_a_picture_is_a_file_in_docs(image: str) -> None:
    # One made by hand, for a project without a repo, can be of any of these kinds.
    project = without_repo(entry(image=image))
    picture = hooks.read(catalog_data(project)).projects[0].picture

    assert picture == hooks.Picture(
        {"en": image, "de": image},
        {"en": "The tool at work", "de": "Das Werkzeug bei der Arbeit"},
    )


@pytest.mark.parametrize(
    "image",
    [
        "/images/tool.webp",
        "../tool.webp",
        "images/tool.gif",
        "a b.png",
        # mkdocs-static-i18n would publish it as the German images/tool.webp.
        "images/tool.de.webp",
    ],
)
def test_a_picture_outside_docs_or_of_another_kind_is_named(image: str) -> None:
    assert problems(catalog_data(entry(image=image))) == [
        "tool: image must be a picture in docs/, such as "
        f"images/projects/homedarts-for-autodarts.webp, not {image!r}."
    ]


@pytest.mark.parametrize("image", ["tool.png", "a/b-c/d_e.svg", "x.jpg", "x.avif"])
def test_the_picture_of_a_project_with_a_repo_is_a_webp(image: str) -> None:
    # scripts/project-pictures.sh writes a WebP, whatever the name of the file says.
    assert problems(catalog_data(entry(image=image))) == [
        "tool: image must be a WebP for a project with a repo, which "
        f"scripts/project-pictures.sh makes, not {image!r}."
    ]


def test_a_picture_may_have_a_file_in_each_language() -> None:
    picture = hooks.read(catalog_data(drawn())).projects[0].picture

    assert picture == hooks.Picture(
        own_pictures(),
        {"en": "The tool at work", "de": "Das Werkzeug bei der Arbeit"},
        hooks.Drawing({"de": "docs/images/de/shot.png"}, "docs/logo.svg", "#14b8a6"),
    )


def test_a_language_without_a_picture_of_its_own_takes_that_of_the_first() -> None:
    project = entry(image={"en": "images/projects/tool.webp"})
    picture = hooks.read(catalog_data(project)).projects[0].picture

    assert picture is not None
    assert picture.src == dict.fromkeys(("en", "de"), "images/projects/tool.webp")
    # The social preview makes it in every language, so the hub draws none.
    assert picture.drawing is None


def test_the_picture_of_the_first_language_is_needed() -> None:
    project = without_repo(entry(image={"de": "images/de/tool.png"}))

    assert problems(catalog_data(project)) == [
        "tool: image.en is missing; the other languages take it when they have no "
        "picture."
    ]


def test_every_picture_of_a_project_with_a_repo_is_a_webp() -> None:
    project = drawn(image={"en": "images/tool.png", "de": "images/de/tool.png"})

    assert problems(catalog_data(project)) == [
        f"tool: image.{language} must be a WebP for a project with a repo, which "
        f"scripts/project-pictures.sh makes, not {image!r}."
        for language, image in (("en", "images/tool.png"), ("de", "images/de/tool.png"))
    ]


def test_the_hub_draws_the_picture_of_its_own_in_a_further_language() -> None:
    # The social preview of the repository speaks the first language alone.
    project = drawn()
    del project["drawing"]

    assert problems(catalog_data(project)) == [
        "tool: drawing is missing, with which the hub draws image.de."
    ]


def test_a_drawing_is_for_a_picture_of_its_own_of_a_project_with_a_repo() -> None:
    # A picture of a project without a repo is made by hand, in every language.
    board = without_repo(drawn("board"))

    assert problems(catalog_data(entry(drawing=drawing_data()), board)) == [
        "tool: drawing is for a project with a repo whose image has a file of its "
        "own in a language after the first, such as image.de.",
        "board: drawing is for a project with a repo.",
    ]


@pytest.mark.parametrize(
    ("drawing", "problem"),
    [
        ("docs/images/de/shot.png", "drawing must be a table."),
        (
            drawing_data(size=2),
            "drawing.size is unknown; known are screenshot, logo, accent.",
        ),
        ({"accent": "#14b8a6"}, "drawing.screenshot is missing."),
        (
            drawing_data(screenshot=".github/shot.png"),
            "drawing.screenshot must be the path of a JPEG, PNG, SVG or WebP of the "
            "repository, such as docs/images/de/card.png, not '.github/shot.png'.",
        ),
        (
            # Chromium would catch an animation at any frame.
            drawing_data(screenshot="docs/images/de/demo.gif"),
            "drawing.screenshot must be the path of a JPEG, PNG, SVG or WebP of the "
            "repository, such as docs/images/de/card.png, not "
            "'docs/images/de/demo.gif'.",
        ),
        (
            drawing_data(logo="../logo.svg"),
            "drawing.logo must be the path of a JPEG, PNG, SVG or WebP of the "
            "repository, such as docs/branding/icon.svg, not '../logo.svg'.",
        ),
        (
            drawing_data(accent="#14B8A6"),
            "drawing.accent must be a color of six lowercase hexadecimal digits, "
            "such as #14b8a6, not '#14B8A6'.",
        ),
        (
            {"screenshot": "docs/images/de/shot.png"},
            "drawing.accent is missing.",
        ),
    ],
)
def test_a_drawing_names_each_of_its_problems(drawing: object, problem: str) -> None:
    assert problems(catalog_data(drawn(drawing=drawing))) == [f"tool: {problem}"]


def test_a_drawing_may_have_a_screenshot_in_each_language_that_it_draws() -> None:
    project = drawn(drawing=drawing_data(screenshot={"de": "docs/de/shot.webp"}))
    picture = hooks.read(catalog_data(project)).projects[0].picture

    assert picture is not None
    assert picture.drawing == hooks.Drawing(
        {"de": "docs/de/shot.webp"}, "docs/logo.svg", "#14b8a6"
    )


def test_a_drawing_has_a_screenshot_for_each_language_that_it_draws_alone() -> None:
    screenshot = {"en": "docs/en/shot.png", "fr": "docs/fr/shot.png"}
    project = drawn(drawing=drawing_data(screenshot=screenshot))

    assert problems(catalog_data(project)) == [
        "tool: drawing.screenshot.fr is in a language that languages doesn't list "
        "(en, de).",
        "tool: drawing.screenshot.en is for a language whose picture the hub doesn't "
        "draw; it draws only those of de.",
        "tool: drawing.screenshot.de is missing.",
    ]


def test_picture_and_second_are_for_a_project_with_a_group() -> None:
    project = entry()
    del project["group"]
    project["second"] = "tool"

    assert problems(catalog_data(project, entry("other"))) == [
        "tool: image is for a project with a group.",
        "tool: alt is for a project with a group.",
        "tool: second is for a project with a group.",
        "tool is on no card of the home page: give it a group, or name it as the "
        "second of a project with one.",
    ]


def test_a_project_without_a_card_is_the_second_button_of_another() -> None:
    board = without_card(without_repo(entry("board")))
    catalog = hooks.read(catalog_data(entry(second="board"), board))

    tool, board_project = catalog.projects

    assert tool.second == "board"
    assert board_project.group is None
    assert board_project.picture is None
    assert catalog.second(tool) == board_project.start
    assert catalog.second(board_project) == board_project.docs


@pytest.mark.parametrize(
    ("second", "message"),
    [
        ("tool", "second names no other project of the catalog, not 'tool'"),
        ("toy", "second names no other project of the catalog, not 'toy'"),
        ("A Toy", "second must be lowercase letters, digits and hyphens, such as "
         "homedarts-for-autodarts, not 'A Toy'"),
    ],
)
def test_the_second_of_a_card_is_another_project(second: str, message: str) -> None:
    assert problems(catalog_data(entry(second=second))) == [f"tool: {message}."]


def test_every_project_is_on_a_card_of_the_home_page() -> None:
    # The dashboard of this catalog without the card of the blueprint.
    board = without_card(without_repo(entry("board")))

    assert problems(catalog_data(entry(), board)) == [
        "board is on no card of the home page: give it a group, or name it as the "
        "second of a project with one.",
    ]


def test_two_projects_may_not_share_a_slug() -> None:
    data = catalog_data(entry("tool"), entry("tool"), entry("other"))

    assert problems(data) == ["tool: slug names more than one project."]


def test_a_missing_catalog_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(hooks.CatalogError, match=r"projects\.toml can't be read"):
        hooks.load(tmp_path)


def test_a_catalog_that_is_no_toml_is_an_error(tmp_path: Path) -> None:
    (tmp_path / "projects.toml").write_text("languages = [", encoding="utf-8")

    with pytest.raises(hooks.CatalogError, match=r"projects\.toml isn't valid TOML"):
        hooks.load(tmp_path)


# The cards of the home page.


def test_a_card_has_a_picture_a_heading_with_an_anchor_and_both_buttons() -> None:
    catalog = hooks.read(catalog_data())
    project = catalog.projects[0]

    assert hooks.card(project, "de", catalog.second(project)) == "\n\n".join(
        [
            '<div class="card" markdown>',
            "![Das Werkzeug bei der Arbeit](images/projects/tool.webp)"
            '{ width="640" height="320" loading="lazy" .off-glb }',
            "### :material-tools:{ .lg .middle } "
            "[Das Werkzeug](https://dennis-otto.github.io/tool/de/) { #tool }",
            "Es tut Dinge.",
            "[:material-download: Installieren](https://example.org/install)"
            "{ .md-button .md-button--primary }\n"
            "[:material-book: Dokumentation](https://dennis-otto.github.io/tool/de/)"
            "{ .md-button }",
            "</div>",
        ]
    )


def test_a_card_keeps_the_anchor_of_every_folder_where_its_website_lived() -> None:
    catalog = hooks.read(catalog_data(entry(former=["old-tool", "older-tool"])))
    project = catalog.projects[0]

    card = hooks.card(project, "en", catalog.second(project))

    assert (
        '### <span id="old-tool"></span><span id="older-tool"></span>'
        ":material-tools:{ .lg .middle } "
        "[The tool](https://dennis-otto.github.io/tool/) { #tool }"
    ) in card.split("\n\n")


def test_a_card_without_a_second_button_has_one_button() -> None:
    project = entry()
    del project["docs"]

    card = hooks.card(hooks.read(catalog_data(project)).projects[0], "en", None)

    assert card.count("{ .md-button") == 1
    assert "[:material-download: Install](https://example.org/install)" in card
    # The heading links the website, which is where the first button leads.
    assert "[The tool](https://example.org/install) { #tool }" in card


def test_a_card_without_a_picture_starts_with_its_heading() -> None:
    project = hooks.read(catalog_data()).projects[0]
    plain = hooks.Project(**{**project.__dict__, "picture": None})

    card = hooks.card(plain, "en", None)

    assert card.split("\n\n")[1].startswith("### ")
    assert "![" not in card


def test_a_card_shows_the_picture_of_the_language_of_its_page() -> None:
    project = hooks.read(catalog_data(drawn())).projects[0]

    assert "](images/projects/tool.webp){" in hooks.card(project, "en", None)
    assert "](images/projects/de/tool.webp){" in hooks.card(project, "de", None)


def test_the_pictures_of_the_first_group_load_at_once_the_first_before_all() -> None:
    # The first row of cards is in view as the page opens, and its first picture is
    # the largest paint of the page; the other groups are further down.
    data = catalog_data(entry("one"), entry("two"), entry("three", group="more"))
    data["group"].append(group_data("more"))

    markdown = hooks.cards(hooks.read(data), "en")

    # Each says how it loads, so that the hook of the blueprint that makes every
    # picture of a page but its first wait leaves it as it is.
    assert re.findall(r'\{ width="640" height="320" (.*?) \.off-glb \}', markdown) == [
        'loading="eager" fetchpriority="high"',
        'loading="eager"',
        'loading="lazy"',
    ]


def test_no_picture_of_the_first_row_of_the_home_page_waits() -> None:
    catalog = hooks.load(ROOT)
    first, *others = catalog.groups

    for language in catalog.languages:
        top = hooks.section(catalog, first, language, first=True)
        assert top.count('loading="eager"') == len(catalog.members(first))
        assert top.count('fetchpriority="high"') == 1
        for group in others:
            below = hooks.section(catalog, group, language)
            assert below.count('loading="lazy"') == len(catalog.members(group))


def test_a_card_escapes_brackets_in_its_texts() -> None:
    # A bracket or a backslash would end or change the link or the picture.
    project = entry(name={"en": "The [new] tool", "de": r"Das \ Werkzeug"})
    project["alt"]["en"] = "A [beta] screen"
    project["start"]["label"]["en"] = "Get [it]"

    catalog = hooks.read(catalog_data(project))
    english = hooks.card(catalog.projects[0], "en", None)
    german = hooks.card(catalog.projects[0], "de", None)

    assert r"![A \[beta\] screen](" in english
    assert r"[The \[new\] tool](" in english
    assert r"[:material-download: Get \[it\]](" in english
    assert r"[Das \\ Werkzeug](" in german


def test_a_group_has_its_heading_its_cards_and_its_note() -> None:
    note = {"en": "They work together.", "de": "Sie arbeiten zusammen."}
    data = catalog_data(entry("one"), entry("two"))
    data["group"][0]["note"] = note
    catalog = hooks.read(data)

    section = hooks.section(catalog, catalog.groups[0], "de")

    assert section.startswith(
        "## Werkzeuge { #tools }\n\n"
        '<div class="grid" markdown>\n\n<div class="card" markdown>'
    )
    assert section.endswith(
        '</div>\n\n</div>\n\n<p class="note" markdown>Sie arbeiten zusammen.</p>'
    )
    assert section.count('<div class="card" markdown>') == 2
    assert section.index("{ #one }") < section.index("{ #two }")


def test_the_groups_stand_in_the_part_of_the_page_that_the_hero_leads_to() -> None:
    data = catalog_data(entry("one"), entry("two", group="more"))
    data["group"].append(group_data("more"))
    catalog = hooks.read(data)

    cards = hooks.cards(catalog, "en")

    assert cards.startswith('<div class="projects" id="projects" data-facts="')
    assert ' markdown>\n\n## Tools { #tools }' in cards
    assert cards.endswith("</div>\n\n</div>\n\n</div>")
    assert cards.index("{ #tools }") < cards.index("{ #one }")
    assert cards.index("{ #one }") < cards.index("{ #more }")
    assert cards.index("{ #more }") < cards.index("{ #two }")
    assert '<p class="note"' not in cards


def test_both_languages_show_the_same_projects_in_the_same_groups() -> None:
    catalog = hooks.load(ROOT)
    anchors = re.compile(r"\{ #([a-z0-9-]+) \}")

    english = anchors.findall(hooks.cards(catalog, "en"))
    german = anchors.findall(hooks.cards(catalog, "de"))

    assert english == german == [
        "home-and-archive",
        "homedarts-for-autodarts",
        "player-switch-for-autodarts",
        "paperless-sync",
        "paperless-unified-search",
        "maintainers",
        "issue-assistant",
        "repo-blueprint",
    ]


# The live facts.


def test_a_project_may_name_its_project_at_bestpractices_dev() -> None:
    catalog = hooks.read(catalog_data(entry(bestpractices=14935)))

    assert catalog.projects[0].bestpractices == 14935
    assert hooks.read(catalog_data()).projects[0].bestpractices is None


@pytest.mark.parametrize("number", [0, -1, "14935", True, 1.5, None])
def test_the_project_at_bestpractices_dev_is_a_number(number: object) -> None:
    assert problems(catalog_data(entry(bestpractices=number))) == [
        "tool: bestpractices must be the number of the project at bestpractices.dev, "
        f"as in the address of its badge, such as 14935, not {number!r}."
    ]


def test_bestpractices_is_for_a_project_with_a_repo() -> None:
    project = without_repo(entry(bestpractices=14935))

    assert problems(catalog_data(project)) == [
        "tool: bestpractices is for a project with a repo."
    ]


def test_the_catalog_needs_the_texts_of_the_facts() -> None:
    data = catalog_data()
    del data["facts"]

    assert problems(data) == ["facts is missing."]


def test_every_problem_of_the_facts_is_named() -> None:
    data = catalog_data()
    facts = data["facts"]
    facts["colour"] = "blue"
    del facts["passing"]
    facts["released"]["de"] = "erschienen"
    facts["coverage"]["en"] = "{} of {}"
    facts["answer"] = "in {}"
    # The name of the list holds no value.
    facts["label"] = {"en": "Facts {}", "de": "Fakten {}"}

    assert problems(data) == [
        "facts.colour is unknown; known are label, released, coverage, mutation, "
        "scorecard, answer, bestpractices, passing, silver, gold, projects, github, "
        "releases.",
        "facts.answer needs a text in every language: facts.answer.en, "
        "facts.answer.de.",
        "facts.passing needs a text in every language: facts.passing.en, "
        "facts.passing.de.",
        "facts.released.de must hold {} once, where the script writes the value, not "
        "'erschienen'.",
        "facts.coverage.en must hold {} once, where the script writes the value, not "
        "'{} of {}'.",
    ]


def test_the_facts_must_be_a_table() -> None:
    data = catalog_data()
    data["facts"] = ["released {}"]

    assert problems(data) == ["facts must be a table."]


def test_the_live_facts_stand_between_the_summary_and_the_buttons() -> None:
    project = hooks.read(catalog_data()).projects[0]

    parts = hooks.card(project, "en", None, "<div>live</div>").split("\n\n")

    # The buttons stand at the foot of the card, the facts above them.
    assert parts[3:5] == ["It does things.", "<div>live</div>"]
    assert parts[5].startswith("[:material-download: Install]")


def test_every_card_with_a_repo_names_the_level_of_its_best_practices() -> None:
    catalog = hooks.read(catalog_data(entry(bestpractices=14935), entry("two")))

    section = hooks.section(catalog, catalog.groups[0], "de", {14935: "silver"})

    assert (
        '<div class="project-facts" data-repo="Dennis-Otto/tool"'
        ' data-name="Das Werkzeug"><ul class="project-facts__list" aria-label="Fakten">'
        '<li><a href="https://www.bestpractices.dev/projects/14935">'
        "Best Practices Silber</a></li></ul></div>"
    ) in section
    # A project without its number or its level has the facts of the script alone.
    assert (
        '<div class="project-facts" data-repo="Dennis-Otto/two"'
        ' data-name="Das Werkzeug"></div>'
    ) in section


def test_a_card_whose_level_the_build_could_not_read_has_the_script_facts() -> None:
    catalog = hooks.read(catalog_data(entry(bestpractices=14935)))

    assert hooks.facts(catalog, catalog.projects[0], "en", {}) == (
        '<div class="project-facts" data-repo="Dennis-Otto/tool"'
        ' data-name="The tool"></div>'
    )


def test_a_card_without_a_repo_has_no_facts() -> None:
    catalog = hooks.read(catalog_data(without_repo(entry())))

    assert "project-facts" not in hooks.section(catalog, catalog.groups[0], "en")


def test_the_facts_escape_their_texts() -> None:
    project = entry(name={"en": 'The "best" <tool> & co', "de": "Das Werkzeug"})
    data = catalog_data(project | {"bestpractices": 1})
    data["facts"]["label"]["en"] = 'Facts "now"'
    data["facts"]["gold"]["en"] = "<gold> & more"
    catalog = hooks.read(data)

    facts = hooks.facts(catalog, catalog.projects[0], "en", {1: "gold"})

    assert 'data-name="The &quot;best&quot; &lt;tool&gt; &amp; co"' in facts
    assert 'aria-label="Facts &quot;now&quot;"' in facts
    assert ">Best Practices &lt;gold&gt; &amp; more</a>" in facts


def answers(*pairs: tuple[int, object]) -> Any:
    """A stand-in for download: the data of each project at bestpractices.dev by its
    number, as JSON, or the error that its download raises."""

    def download(url: str) -> bytes:
        number = int(url.removeprefix("https://www.bestpractices.dev/projects/")[:-5])
        answer = dict(pairs)[number]
        if isinstance(answer, Exception):
            raise answer
        return answer if isinstance(answer, bytes) else json.dumps(answer).encode()

    return download


def test_the_build_reads_the_level_of_every_project_at_bestpractices_dev(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    projects = [entry(f"p{number}", bestpractices=number) for number in range(1, 8)]
    download = answers(
        (1, {"badge_level": "passing", "name": "One"}),
        (2, {"badge_level": "silver"}),
        (3, {"badge_level": "gold"}),
        (4, {"badge_level": "in_progress"}),
        (5, hooks.SearchError("https://www.bestpractices.dev/projects/5.json: 503")),
        (6, b"<html>"),
        (7, ["silver"]),
    )
    monkeypatch.setattr(hooks, "download", download)
    caplog.set_level(logging.INFO, logger="mkdocs.hooks.project")

    levels = hooks.best_practices(hooks.read(catalog_data(*projects)))

    assert levels == {1: "passing", 2: "silver", 3: "gold"}
    # Without a warning, which would fail the strict build while the website is away.
    assert {record.levelno for record in caplog.records} == {logging.INFO}
    assert len(caplog.records) == 4


def test_the_build_asks_for_no_level_without_a_project_at_bestpractices_dev(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(hooks, "download", lambda url: pytest.fail(url))

    assert hooks.best_practices(hooks.read(catalog_data())) == {}


def test_the_levels_are_read_once_for_every_language(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asked: list[str] = []

    def download(url: str) -> bytes:
        asked.append(url)
        return b'{"badge_level": "silver"}'

    monkeypatch.setattr(hooks, "download", download)
    catalog = hooks.read(catalog_data(entry(bestpractices=14935)))
    settings = SimpleNamespace(extra={"catalog": catalog})
    markdown = "<!-- projects -->\n"

    english = hooks.on_page_markdown(markdown, page("en"), settings, None)
    german = hooks.on_page_markdown(markdown, page("de"), settings, None)

    assert asked == ["https://www.bestpractices.dev/projects/14935.json"]
    assert "Best Practices silver</a>" in english
    assert "Best Practices Silber</a>" in german
    # A page without the cards asks for nothing.
    assert hooks.on_page_markdown("# Security\n", page("en"), settings, None)
    assert len(asked) == 1


@pytest.mark.parametrize("language", ["en", "de"])
def test_the_cards_tell_the_script_where_the_data_is_and_its_texts(
    language: str,
) -> None:
    data = catalog_data()
    data["facts"]["label"][language] = 'Facts "now"'
    catalog = hooks.read(data)

    first = hooks.cards(catalog, language).split("\n", 1)[0]

    texts = {key: catalog.facts[key][language] for key in hooks.SCRIPT}
    texts["label"] = "Facts &quot;now&quot;"
    assert first == (
        '<div class="projects" id="projects"'
        ' data-facts="/repo-blueprint/dashboard/repos.json"'
        ' data-history="/repo-blueprint/dashboard/history.json"'
        f' data-locale="{language}"'
        + "".join(f' data-{key}="{text}"' for key, text in texts.items())
        + " markdown>"
    )


# The releases of the projects: What's new and the Releases page.


def release_data(tag: str = "v1.0.0", **changes: Any) -> dict[str, Any]:
    """A release as the API of GitHub lists it, with its notes as the HTML that
    GitHub makes of their Markdown."""
    data: dict[str, Any] = {
        "tag_name": tag,
        "name": tag,
        "draft": False,
        "prerelease": False,
        "published_at": "2026-10-23T19:04:13Z",
        "html_url": f"https://github.com/Dennis-Otto/tool/releases/tag/{tag}",
        "body_html": "<h3>Features</h3>\n<ul>\n<li><strong>Dark mode:</strong> the "
        "settings<br>\nfollow the system.</li>\n</ul>",
    }
    data.update(changes)
    return data


def releases_api(answers: dict[str, object], asked: list[Any] | None = None) -> Any:
    """A stand-in for download: the releases of each repository by its name, as the
    API lists them, or the error that its download raises; asked keeps every
    request."""

    def download(request: Any) -> bytes:
        if asked is not None:
            asked.append(request)
        address = request.full_url.removeprefix("https://api.github.com/repos/")
        answer = answers[address.partition("/releases?")[0]]
        if isinstance(answer, Exception):
            raise answer
        return answer if isinstance(answer, bytes) else json.dumps(answer).encode()

    return download


def release(
    tag: str, day: str, headline: str = "", repo: str = "Dennis-Otto/one"
) -> Any:
    """A release that the build read, with notes of one paragraph."""
    url = f"https://github.com/{repo}/releases/tag/{tag}"
    return hooks.Release(tag, url, date.fromisoformat(day), "<p>Notes</p>", headline)


@pytest.fixture
def no_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """No token of a workflow, as on a computer without one."""
    for name in hooks.TOKENS:
        monkeypatch.delenv(name, raising=False)


@pytest.mark.usefixtures("no_token")
def test_the_build_reads_the_latest_releases_of_every_project_from_github(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asked: list[Any] = []
    listed = [
        release_data("v2.0.0-beta.1", prerelease=True),
        release_data("v1.9.0", draft=True),
        release_data("v1.8.0", published_at="2026-10-22T08:00:00Z"),
        "no release",
        release_data("not a tag!"),
        release_data(None),
        release_data("v1.7.1", published_at="yesterday"),
        release_data("v1.7.0", published_at="2026-02-30T08:00:00Z"),
        release_data("v1.6.0", body_html=None),
        *(release_data(f"v1.{minor}.0") for minor in (5, 4, 3, 2)),
    ]
    answers = {"Dennis-Otto/tool": listed, "Dennis-Otto/two": []}
    monkeypatch.setattr(hooks, "download", releases_api(answers, asked))
    catalog = hooks.read(
        catalog_data(entry(), entry("two"), without_repo(entry("three")))
    )

    found = hooks.release_notes(catalog)

    # Neither a draft nor a prerelease, nor one without a tag or a day.
    assert list(found) == ["Dennis-Otto/tool", "Dennis-Otto/two"]
    assert found["Dennis-Otto/two"] == ()
    releases = found["Dennis-Otto/tool"]
    assert [item.tag for item in releases] == [
        "v1.8.0",
        "v1.6.0",
        "v1.5.0",
        "v1.4.0",
        "v1.3.0",
    ]
    assert releases[0] == hooks.Release(
        "v1.8.0",
        "https://github.com/Dennis-Otto/tool/releases/tag/v1.8.0",
        date(2026, 10, 22),
        "<h4>Features</h4>\n<ul>\n<li><strong>Dark mode:</strong> the settings\n"
        "\nfollow the system.</li>\n</ul>",
        "Dark mode",
    )
    assert (releases[1].notes, releases[1].headline) == ("", "")
    # One request of each repository, for the releases with their notes as HTML,
    # and without a token, which isn't set.
    assert sorted(request.full_url for request in asked) == [
        "https://api.github.com/repos/Dennis-Otto/tool/releases?per_page=20",
        "https://api.github.com/repos/Dennis-Otto/two/releases?per_page=20",
    ]
    for request in asked:
        assert request.get_header("Accept") == "application/vnd.github.html+json"
        assert request.get_header("X-github-api-version") == "2022-11-28"
        assert not request.has_header("Authorization")


@pytest.mark.parametrize(
    ("variables", "token"),
    [
        ({"GITHUB_TOKEN": "of-the-workflow", "GH_TOKEN": "of-gh"}, "of-the-workflow"),
        ({"GITHUB_TOKEN": "", "GH_TOKEN": "of-gh"}, "of-gh"),
    ],
)
def test_a_token_of_the_workflow_goes_to_the_api_alone(
    monkeypatch: pytest.MonkeyPatch, variables: dict[str, str], token: str
) -> None:
    for name, value in variables.items():
        monkeypatch.setenv(name, value)

    request = hooks.releases_request("Dennis-Otto/tool")

    assert request.get_header("Authorization") == f"Bearer {token}"
    # Not among the headers that urllib takes along when the API sends the request
    # on to another host.
    assert "Authorization" not in request.headers
    assert request.unredirected_hdrs == {"Authorization": f"Bearer {token}"}


@pytest.mark.usefixtures("no_token")
def test_a_project_whose_releases_cant_be_read_has_none(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    answers = {
        "Dennis-Otto/tool": hooks.SearchError("HTTP Error 403: rate limit exceeded"),
        "Dennis-Otto/two": b"<html>",
        "Dennis-Otto/three": {"message": "Not Found"},
    }
    monkeypatch.setattr(hooks, "download", releases_api(answers))
    caplog.set_level(logging.INFO, logger="mkdocs.hooks.project")
    catalog = hooks.read(catalog_data(entry(), entry("two"), entry("three")))

    assert hooks.release_notes(catalog) == {}
    # Without a warning, which would fail the strict build while the API is away.
    assert {record.levelno for record in caplog.records} == {logging.INFO}
    assert len(caplog.records) == 3


def test_the_build_asks_for_no_releases_without_a_project_with_a_repo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(hooks, "download", lambda url: pytest.fail(str(url)))

    catalog = hooks.read(catalog_data(without_repo(entry())))

    assert hooks.release_notes(catalog) == {}


def test_a_failed_download_of_a_request_names_its_address(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    error = hooks.urllib.error.URLError("timed out")
    monkeypatch.setattr(hooks.urllib.request, "urlopen", Download(error, error))

    with pytest.raises(hooks.SearchError) as raised:
        hooks.download(hooks.releases_request("Dennis-Otto/tool"))

    assert str(raised.value) == (
        "https://api.github.com/repos/Dennis-Otto/tool/releases?per_page=20 can't be "
        "downloaded: <urlopen error timed out>"
    )


@pytest.mark.parametrize(
    ("html", "kept"),
    [
        ('<p>Run <script>alert("x")</script>it</p>', "<p>Run it</p>"),
        ('<p onclick="steal()" style="color: red">Text</p>', "<p>Text</p>"),
        ('<img src="https://example.org/x.png" onerror="steal()">', ""),
        # A picture with its link to the full size, as GitHub writes it.
        (
            '<p><a href="https://camo.example.org/x"><img src="x.png"></a> </p>after',
            "after",
        ),
        ('<a href="https://x.org/"><code>x</code></a>', '<a href="https://x.org/"><code>x</code></a>'),
        ('<a href="javascript:steal()">a link</a>', "a link"),
        (
            '<a href="https://github.com/x" data-hovercard-url="/x" onclick="s()">x</a>',
            '<a href="https://github.com/x">x</a>',
        ),
        (
            '<a href="https://example.org/?a=&quot;b&quot;">q</a>',
            '<a href="https://example.org/?a=&quot;b&quot;">q</a>',
        ),
        ('<a href="http://example.org/">plain</a>', "plain"),
        ('<a href="https://exa mple.org/">space</a>', "space"),
        ("<a>no address</a>", "no address"),
        ("<div><span>Text</span> &lt;script&gt;</div>", "Text &lt;script&gt;"),
        ("<svg><text>drawn</text></svg><p>after</p>", "<p>after</p>"),
        ("<object><svg><text>x</text></svg>y</object>z", "z"),
        ("<iframe src='https://example.org'></iframe><p>p</p>", "<p>p</p>"),
        (
            "<b>bold</b> <i>it</i> <tt>code</tt> <strike>old</strike>",
            "<strong>bold</strong> <em>it</em> <code>code</code> <del>old</del>",
        ),
        ("<ul><li>open", "<ul><li>open</li></ul>"),
        ("<p>one</em> two</p></ul>", "<p>one two</p>"),
        ("<ul><li><p>item</ul>", "<ul><li><p>item</p></li></ul>"),
        ("<p><a href='https://x.org/'>link</p> after", '<p><a href="https://x.org/">link</a></p> after'),
        ("line<br>\nbreak<br/>end", "line\n\nbreak\nend"),
        ("<!-- a comment --><p>x</p>", "<p>x</p>"),
        ("<hr><hr/>", "<hr><hr>"),
        (
            "<table><tr><td align='left'>cell</td></tr></table>",
            "<table><tr><td>cell</td></tr></table>",
        ),
        ("<input type='checkbox' checked> done", "done"),
    ],
)
def test_the_notes_keep_text_lists_code_and_links_to_https_alone(
    html: str, kept: str
) -> None:
    assert hooks.notes_html(html, "1.0.0") == kept


def test_the_headings_of_the_notes_stand_below_the_heading_of_their_release() -> None:
    assert hooks.notes_html("<h2>All</h2><h3>Features</h3><h5>Small</h5>", "1") == (
        "<h4>All</h4><h5>Features</h5><h6>Small</h6>"
    )
    assert hooks.notes_html("<h3>Features</h3><H4>More</H4>", "1") == (
        "<h4>Features</h4><h5>More</h5>"
    )
    assert hooks.notes_html("<h1>Big</h1><h6>Tiny</h6>", "1") == (
        "<h4>Big</h4><h6>Tiny</h6>"
    )
    # As release-please writes them: the section of the changelog, and then every
    # pull request of the release, with a heading of a higher level.
    assert hooks.notes_html(
        "<h3>Fixed</h3><h2>Every pull request</h2><h3>Bug fixes</h3>", "1"
    ) == ("<h4>Fixed</h4><h4>Every pull request</h4><h4>Bug fixes</h4>")


def test_the_notes_leave_out_a_heading_in_front_that_names_their_version() -> None:
    html = (
        '<h2><a href="https://github.com/x/compare/v1.0.5...v1.0.6">1.0.6</a> '
        "(2026-10-23)</h2>\n<h3>Bug fixes</h3>"
    )

    assert hooks.notes_html(html, "1.0.6") == "<h4>Bug fixes</h4>"
    assert hooks.notes_html(html, "1.0.7") == (
        '<h4><a href="https://github.com/x/compare/v1.0.5...v1.0.6">1.0.6</a> '
        "(2026-10-23)</h4>\n<h5>Bug fixes</h5>"
    )
    assert hooks.notes_html("<p>1.0.6</p><h2>1.0.6</h2>", "1.0.6") == (
        "<p>1.0.6</p><h4>1.0.6</h4>"
    )
    assert hooks.notes_html("<h2>Notes</h2>", "") == "<h4>Notes</h4>"


@pytest.mark.parametrize(
    ("notes", "expected"),
    [
        (
            "<h4>Features</h4><ul><li><strong>Dark mode:</strong> the settings.</li>",
            "Dark mode",
        ),
        ("<ul><li><strong>Dark mode</strong>: the settings.</li></ul>", "Dark mode"),
        (
            "<ul><li>\n<p><strong>A loose item:</strong> its text</p></li></ul>",
            "A loose item",
        ),
        (
            '<ul><li><strong>popup:</strong> hide the form until asked for (<a href="'
            'https://github.com/x/pull/4">#4</a>) (<a href="https://github.com/x/'
            'commit/84ffac1">84ffac1</a>)</li></ul>',
            "popup: hide the form until asked for",
        ),
        ("<p>Each release reaches the store. Google reviews it.</p>", "Each release reaches the store"),
        ("<p>One sentence.</p>", "One sentence"),
        ("<p>" + "word " * 40 + "</p>", " ".join(["word"] * 24) + "…"),
        ("<h4>Only a heading</h4>", ""),
        ("", ""),
    ],
)
def test_what_s_new_tells_a_release_by_the_headline_of_its_notes(
    notes: str, expected: str
) -> None:
    assert hooks.headline(notes) == expected


@pytest.mark.parametrize(
    ("value", "day"),
    [
        ("2026-10-15T21:33:15Z", date(2026, 10, 15)),
        ("2026-10-15T21:33:15.120Z", date(2026, 10, 15)),
        ("2026-02-30T08:00:00Z", None),
        ("2026-10-15", None),
        (None, None),
        (20261015, None),
    ],
)
def test_a_release_was_published_on_the_day_that_the_api_names(
    value: object, day: date | None
) -> None:
    assert hooks.published(value) == day


def test_a_release_has_an_anchor_from_its_project_and_its_tag() -> None:
    project = hooks.read(catalog_data()).projects[0]
    tagged = release("v2.0.1-beta.1+build_7", "2026-10-01")

    assert hooks.release_anchor(project, tagged) == "tool-v2-0-1-beta-1-build-7"


def test_what_s_new_lists_the_latest_release_of_every_project_newest_first() -> None:
    quoted = {"en": 'The "two" <tool>', "de": "Zwei"}
    catalog = hooks.read(
        catalog_data(
            entry("one"),
            entry("two", name=quoted),
            entry("three"),
            without_repo(entry("four")),
            entry("five"),
        )
    )
    notes = {
        "Dennis-Otto/one": (
            release("v1.0.0", "2026-10-20", "Dark mode"),
            release("v0.9.0", "2026-10-01", "Older"),
        ),
        "Dennis-Otto/two": (release("v2.0.0", "2026-10-22", 'A "quoted" <b>'),),
        "Dennis-Otto/three": (release("v3.0.0", "2026-10-20"),),
        "Dennis-Otto/five": (),
    }

    html = hooks.news(catalog, "en", notes)

    # Four projects with a repo, the count of the script; the newest first, and of a
    # day in the order of the catalog, each with the tags of every release that the
    # build read; five without a release has none.
    assert html == (
        '<div class="project-news" data-count="4"><ul class="project-news__list">'
        '<li data-repo="Dennis-Otto/two" data-release="v2.0.0"'
        ' data-released="2026-10-22" data-releases="v2.0.0">'
        '<a href="releases.html#two-v2-0-0">'
        "The &quot;two&quot; &lt;tool&gt; v2.0.0</a>"
        ' <time datetime="2026-10-22" data-ago>2026-10-22</time>'
        '<span class="project-news__headline" lang="en">'
        "A &quot;quoted&quot; &lt;b&gt;</span></li>"
        '<li data-repo="Dennis-Otto/one" data-release="v1.0.0"'
        ' data-released="2026-10-20" data-releases="v1.0.0 v0.9.0">'
        '<a href="releases.html#one-v1-0-0">'
        "The tool v1.0.0</a>"
        ' <time datetime="2026-10-20" data-ago>2026-10-20</time>'
        '<span class="project-news__headline" lang="en">Dark mode</span></li>'
        '<li data-repo="Dennis-Otto/three" data-release="v3.0.0"'
        ' data-released="2026-10-20" data-releases="v3.0.0">'
        '<a href="releases.html#three-v3-0-0">'
        "The tool v3.0.0</a>"
        ' <time datetime="2026-10-20" data-ago>2026-10-20</time></li>'
        "</ul></div>"
    )
    assert ">Zwei v2.0.0</a>" in hooks.news(catalog, "de", notes)


def test_what_s_new_without_releases_leaves_its_place_to_the_script() -> None:
    catalog = hooks.read(catalog_data(entry(), entry("two")))

    assert hooks.news(catalog, "en", {}) == (
        '<div class="project-news" data-count="2"></div>'
    )


def test_the_releases_page_has_the_releases_of_every_project_with_a_repo() -> None:
    catalog = hooks.read(
        catalog_data(
            entry("one", short={"en": "One", "de": "Eins"}),
            without_repo(entry("two")),
            entry("three"),
        )
    )
    notes = {
        "Dennis-Otto/one": (
            release("v1.0.0", "2026-10-20"),
            release("v0.9_1", "2026-10-01"),
        ),
    }

    nav, *parts = hooks.release_history(catalog, "en", notes).split("\n\n")

    # The list of the projects tells the script where the data is.
    assert nav == (
        '<nav class="release-filter" aria-label="Projects"'
        f'{hooks.script_data(catalog, "en")}><ul><li><a href="#one">One</a></li>'
        '<li><a href="#three">The tool</a></li></ul></nav>'
    )
    meta = (
        '<p class="release-meta"><time datetime="{0}" data-ago>{0}</time> · '
        '<a href="https://github.com/Dennis-Otto/one/releases/tag/{1}">On GitHub</a></p>'
    )
    assert parts == [
        "## The tool { #one }",
        '<div class="release-newer" data-repo="Dennis-Otto/one"'
        ' data-releases="v1.0.0 v0.9_1" data-released="2026-10-20"></div>',
        "### One v1.0.0 { #one-v1-0-0 }",
        meta.format("2026-10-20", "v1.0.0"),
        '<div class="release-notes" data-release="Dennis-Otto/one@v1.0.0"></div>',
        "### One v0.9\\_1 { #one-v0-9-1 }",
        meta.format("2026-10-01", "v0.9_1"),
        '<div class="release-notes" data-release="Dennis-Otto/one@v0.9_1"></div>',
        '<p class="release-all"><a href="https://github.com/Dennis-Otto/one/releases">'
        "All of One on GitHub</a></p>",
        # A project whose releases the build couldn't read links them on GitHub.
        "## The tool { #three }",
        '<div class="release-newer" data-repo="Dennis-Otto/three" data-releases=""'
        ' data-released=""></div>',
        '<p class="release-all"><a href="https://github.com/Dennis-Otto/three/'
        'releases">All of The tool on GitHub</a></p>',
    ]


def test_the_german_releases_page_has_the_texts_in_german() -> None:
    catalog = hooks.read(catalog_data(entry(short={"en": "Tool", "de": "Werkzeug"})))
    notes = {"Dennis-Otto/tool": (release("v1.0.0", "2026-10-20", repo="x/y"),)}

    markdown = hooks.release_history(catalog, "de", notes)

    assert 'aria-label="Projekte" data-facts=' in markdown
    assert ' data-locale="de"' in markdown
    assert "## Das Werkzeug { #tool }" in markdown
    assert "### Werkzeug v1.0.0 { #tool-v1-0-0 }" in markdown
    assert ">Auf GitHub</a></p>" in markdown
    assert ">Alle von Werkzeug auf GitHub</a></p>" in markdown


@pytest.mark.usefixtures("no_token")
def test_the_releases_are_read_once_for_both_pages_and_every_language(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asked: list[Any] = []
    answers = {"Dennis-Otto/tool": [release_data("v1.0.0")]}
    monkeypatch.setattr(hooks, "download", releases_api(answers, asked))
    settings = SimpleNamespace(extra={"catalog": hooks.read(catalog_data())})
    markdown = "## News\n\n<!-- releases -->\t\n\nSee the `<!-- releases -->`.\n"

    news = hooks.on_page_markdown(markdown, page("de"), settings, None)
    history = hooks.on_page_markdown(
        "# Releases\n\n<!-- release-notes -->\n", page("en"), settings, None
    )

    assert len(asked) == 1
    assert news.startswith(
        '## News\n\n<div class="project-news" data-count="1"><ul class="project-'
    )
    assert news.endswith("</ul></div>\n\nSee the `<!-- releases -->`.\n")
    assert '<a href="releases.html#tool-v1-0-0">Das Werkzeug v1.0.0</a>' in news
    assert "\n\n### The tool v1.0.0 { #tool-v1-0-0 }\n\n" in history
    # A page without the markers asks for nothing.
    assert hooks.on_page_markdown("# Security\n", page("en"), settings, None)
    assert len(asked) == 1


@pytest.mark.usefixtures("no_token")
def test_without_the_api_both_pages_link_the_releases_on_github(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    offline = hooks.SearchError("api.github.com can't be downloaded: offline")
    monkeypatch.setattr(hooks, "download", releases_api({"Dennis-Otto/tool": offline}))
    settings = SimpleNamespace(extra={"catalog": hooks.read(catalog_data())})

    news = hooks.on_page_markdown("<!-- releases -->\n", page("en"), settings, None)
    history = hooks.on_page_markdown("<!-- release-notes -->\n", page("en"), settings, None)
    html = hooks.on_page_content(history, page("en"), settings, None)

    assert news == '<div class="project-news" data-count="1"></div>\n'
    assert "###" not in history
    assert html == history
    assert (
        '<a href="https://github.com/Dennis-Otto/tool/releases">All of The tool on '
        "GitHub</a>" in history
    )


@pytest.mark.parametrize("locale", ["en", "de", None])
def test_the_notes_take_the_place_of_their_placeholders_in_the_html(
    locale: str | None,
) -> None:
    notes = {"Dennis-Otto/tool": (release("v1.0.0", "2026-10-20"),)}
    catalog = hooks.read(catalog_data())
    settings = SimpleNamespace(extra={"catalog": catalog, hooks.NOTES: notes})
    html = (
        '<h3 id="tool-v1-0-0">The tool v1.0.0</h3>\n'
        '<div class="release-notes" data-release="Dennis-Otto/tool@v1.0.0"></div>\n'
        '<div class="release-notes" data-release="Dennis-Otto/tool@v0.1.0"></div>'
    )

    result = hooks.on_page_content(html, page(locale), settings, None)

    # In English, as the notes are, on the page of every language, so that the
    # search index of each language holds them. A release without notes gets none.
    attributes = ' lang="en"'
    assert result == (
        '<h3 id="tool-v1-0-0">The tool v1.0.0</h3>\n'
        f'<div class="release-notes"{attributes}><p>Notes</p></div>\n'
        f'<div class="release-notes"{attributes}></div>'
    )


def test_a_page_without_the_placeholder_of_notes_asks_for_no_release(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(hooks, "download", lambda url: pytest.fail(str(url)))
    settings = SimpleNamespace(extra={"catalog": hooks.read(catalog_data())})

    assert hooks.on_page_content("<p>Text</p>", page("en"), settings, None) == (
        "<p>Text</p>"
    )


@pytest.mark.usefixtures("no_token")
def test_no_script_or_picture_of_a_release_reaches_the_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    body = (
        '<p onmouseover="steal()">Fixed</p><script>steal()</script>'
        '<img src="https://example.org/track.gif" onerror="steal()">'
        '<a href="javascript:steal()">link</a><style>p { display: none }</style>'
        '<iframe src="https://example.org/"></iframe><svg onload="steal()"></svg>'
    )
    answers = {"Dennis-Otto/tool": [release_data("v1.0.0", body_html=body)]}
    monkeypatch.setattr(hooks, "download", releases_api(answers))
    settings = SimpleNamespace(extra={"catalog": hooks.read(catalog_data())})
    markdown = hooks.on_page_markdown("<!-- release-notes -->\n", page("en"), settings, None)

    html = hooks.on_page_content(markdown, page("en"), settings, None)

    notes = html[html.index('<div class="release-notes"') :].split("\n\n")[0]
    assert notes == '<div class="release-notes" lang="en"><p>Fixed</p>link</div>'
    for word in ("<script", "<img", "<style", "<iframe", "<svg", "steal", "javascript"):
        assert word not in html, word


# What a project works with.


# The files from which the cards of the catalog of this repository read what their
# projects work with, as the latest releases held them in October 2026.
FIXTURES = ROOT / "tests/fixtures/requirements"
HACS = (FIXTURES / "hacs.json").read_bytes()
INFO = (FIXTURES / "info.xml").read_bytes()
COPIER = (FIXTURES / "copier.yml").read_bytes()


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
        for project in hooks.load(ROOT).projects
        if isinstance(project.requires, hooks.Source)
    }


def drawn_files(project: Any) -> dict[str, bytes]:
    """A stand-in for every file from which the hub draws a picture of the card of
    project, by its address on the default branch: its screenshots and its logo."""
    drawing = project.picture.drawing if project.picture is not None else None
    if drawing is None:
        return {}
    names = [*drawing.screenshot.values(), *filter(None, [drawing.logo])]
    return {raw(str(project.repo), "HEAD", name): b"RIFF" for name in names}


def drawing_files() -> dict[str, bytes]:
    """drawn_files of every project of the catalog of this repository."""
    files: dict[str, bytes] = {}
    for project in hooks.load(ROOT).projects:
        files |= drawn_files(project)
    return files


def network_files() -> dict[str, bytes]:
    """Every file that the catalog bot reads for the catalog of this repository, by
    its address on the default branch, in the order in which it asks: for each
    project the file that says what it works with, then those from which the hub
    draws its pictures."""
    files: dict[str, bytes] = {}
    sources = source_files("HEAD")
    for project in hooks.load(ROOT).projects:
        if isinstance(project.requires, hooks.Source):
            url = raw(str(project.repo), "HEAD", project.requires.file)
            files[url] = sources[url]
        files |= drawn_files(project)
    return files


def files(answers: dict[str, bytes | Exception], asked: list[str]) -> Any:
    """A stand-in for download: the content of every file by its address, or the
    error that its download raises, and the addresses that the build asked for."""

    def download(url: str) -> bytes:
        asked.append(url)
        answer = answers[url]
        if isinstance(answer, Exception):
            raise answer
        return answer

    return download


def test_every_project_with_a_repository_says_what_it_works_with() -> None:
    catalog = hooks.load(ROOT)

    for project in catalog.projects:
        assert (project.requires is None) == (project.repo is None), project.slug
    assert catalog.requirements.label == {
        "en": "Works with {}",
        "de": "Funktioniert mit {}",
    }


def test_the_files_of_the_catalog_hold_what_their_projects_work_with() -> None:
    catalog = hooks.load(ROOT)
    works = {
        project.slug: hooks.values_in(
            project.requires,
            (FIXTURES / PurePosixPath(project.requires.file).name).read_bytes(),
        )
        for project in catalog.projects
        if isinstance(project.requires, hooks.Source)
    }

    assert works == {
        "homedarts-for-autodarts": {"": "2026.8.0"},
        "paperless-sync": {"min": "33", "max": "35"},
        "paperless-unified-search": {"min": "33", "max": "35"},
        "repo-blueprint": {"": "9.8"},
    }


def test_a_project_may_say_what_it_works_with_in_every_language() -> None:
    requires = {"en": "Any computer", "de": "Jeder Computer"}

    catalog = hooks.read(catalog_data(entry(requires=requires)))

    assert catalog.projects[0].requires == requires
    assert catalog.requirements == hooks.Link(
        "material-puzzle", {"en": "Works with {}", "de": "Läuft mit {}"}, {}
    )


def test_a_project_may_read_what_it_works_with_from_a_file_of_its_repository() -> None:
    catalog = hooks.read(
        catalog_data(entry(requires=source()), entry("two", requires=nextcloud()))
    )

    assert [project.requires for project in catalog.projects] == [
        hooks.Source(
            "hacs.json",
            {"": "homeassistant"},
            {"en": "Home Assistant {} or newer", "de": "Home Assistant {} oder neuer"},
        ),
        hooks.Source(
            "appinfo/info.xml",
            {
                "min": "dependencies/nextcloud@min-version",
                "max": "dependencies/nextcloud@max-version",
            },
            {"en": "Nextcloud {min} to {max}", "de": "Nextcloud {min} bis {max}"},
        ),
    ]


@pytest.mark.parametrize(
    ("requires", "messages"),
    [
        (
            "Any computer",
            [
                "tool: requires must be a text in every language, such as "
                "requires.en, or a file of the repository with requires.file, "
                "requires.field and requires.text."
            ],
        ),
        ({"en": "Any computer"}, ["tool: requires.de is missing."]),
        (
            source(file="hacs.toml", colour="blue"),
            [
                "tool: requires.colour is unknown; known are file, field, text.",
                "tool: requires.file must be the path of a JSON, YAML or XML file of "
                "the repository, such as hacs.json or appinfo/info.xml, not "
                "'hacs.toml'.",
            ],
        ),
        (
            {"field": "homeassistant", "text": {"en": "{}", "de": "{}"}},
            ["tool: requires.file is missing."],
        ),
        (
            source(field="home/assistant"),
            [
                "tool: requires.field must be the keys to the value in the JSON, with "
                "a dot between two, such as homeassistant, not 'home/assistant'."
            ],
        ),
        (
            source(file="copier.yml", field="copier.version"),
            [
                "tool: requires.field must be a key at the top of the YAML, with its "
                "value on its line, such as _min_copier_version, not "
                "'copier.version'."
            ],
        ),
        (
            source(file="appinfo/info.xml", field="dependencies/php[@min-version]"),
            [
                "tool: requires.field must be the path of an element from the root of "
                "the XML, with @ and the name of one of its attributes for that, such "
                "as dependencies/nextcloud@min-version, not "
                "'dependencies/php[@min-version]'."
            ],
        ),
        (source(field=7), ["tool: requires.field must be a text on one line."]),
        (
            source(field={}),
            [
                "tool: requires.field must name a field, or a table of fields by "
                "their names."
            ],
        ),
        (
            source(field={"Min": "version", "max": "version"}, text={"en": "{max}"}),
            [
                "tool: requires.field.Min must be named with a name of lowercase "
                "letters, digits and underscores, such as min, not 'Min'.",
                "tool: requires.text.de is missing.",
            ],
        ),
        (
            source(text={"en": "Home Assistant", "de": "Home Assistant {} {}"}),
            [
                "tool: requires.text.en must hold {} once, where the value goes, not "
                "'Home Assistant'.",
                "tool: requires.text.de must hold {} once, where the value goes, not "
                "'Home Assistant {} {}'.",
            ],
        ),
        (
            source(text={"en": "Home Assistant {} or newer}", "de": "{min} {}"}),
            [
                "tool: requires.text.en must hold {} once, where the value goes, not "
                "'Home Assistant {} or newer}'.",
                "tool: requires.text.de must hold {} once, where the value goes, not "
                "'{min} {}'.",
            ],
        ),
        (
            nextcloud() | {"text": {"en": "Nextcloud {min}", "de": "Nextcloud {}"}},
            [
                "tool: requires.text.en must hold {min} and {max} once each, where "
                "their values go, not 'Nextcloud {min}'.",
                "tool: requires.text.de must hold {min} and {max} once each, where "
                "their values go, not 'Nextcloud {}'.",
            ],
        ),
    ],
)
def test_every_problem_of_what_a_project_works_with_is_named(
    requires: object, messages: list[str]
) -> None:
    assert problems(catalog_data(entry(requires=requires))) == messages


def test_what_a_project_works_with_goes_with_its_repository() -> None:
    project = without_repo(entry(requires={"en": "Any", "de": "Jedes"}))

    assert problems(catalog_data(entry("one"), project)) == [
        "tool: requires is for a project with a repo."
    ]


def test_the_catalog_needs_the_line_of_what_a_project_works_with() -> None:
    data = catalog_data()
    del data["requirements"]

    assert problems(data) == ["requirements is missing."]


def test_the_label_of_the_line_holds_the_place_of_what_a_project_works_with() -> None:
    data = catalog_data()
    data["requirements"]["label"] = {"en": "Works with {} and {}", "de": "Läuft mit"}

    assert problems(data) == [
        "requirements.label.en must hold {} once, where what a project works with "
        "goes, not 'Works with {} and {}'.",
        "requirements.label.de must hold {} once, where what a project works with "
        "goes, not 'Läuft mit'.",
    ]


@pytest.mark.parametrize(
    ("file", "field", "content", "value"),
    [
        ("hacs.json", "homeassistant", HACS, "2026.8.0"),
        ("package.json", "engines.node", b'{"engines": {"node": "20.11"}}', "20.11"),
        (
            "manifest.json",
            "minimum_chrome_version",
            b'{"minimum_chrome_version": 120}',
            "120",
        ),
        ("copier.yml", "_min_copier_version", COPIER, "9.8"),
        ("a.yaml", "version", b"version: 1.2.3 # the oldest\r\nnext: 2\r\n", "1.2.3"),
        ("a.yml", "version", b"\xef\xbb\xbfversion:  '4.0+1'\n", "4.0+1"),
        ("appinfo/info.xml", "dependencies/nextcloud@max-version", INFO, "35"),
        ("appinfo/info.xml", "version", INFO, "1.2.0"),
    ],
)
def test_a_value_is_read_from_a_json_yaml_or_xml_file(
    file: str, field: str, content: bytes, value: str
) -> None:
    found = hooks.values_in(hooks.Source(file, {"": field}, {}), content)

    assert found == {"": value}


@pytest.mark.parametrize(
    ("file", "field", "content", "message"),
    [
        ("hacs.json", "homeassistant", b"{", "can't be read: Expecting property name"),
        ("hacs.json", "homeassistant", b'{"name": "x"}', "has no field homeassistant"),
        ("hacs.json", "a.b", b'{"a": "b"}', "has no field a.b"),
        (
            "hacs.json",
            "homeassistant",
            b'{"homeassistant": true}',
            "holds 'true' in homeassistant, which is no version",
        ),
        (
            "hacs.json",
            "homeassistant",
            b'{"homeassistant": "<b>2026</b>"}',
            "holds '<b>2026</b>' in homeassistant, which is no version",
        ),
        ("copier.yml", "_min", b"_min_copier_version: 9.8\n", "has no field _min"),
        ("copier.yml", "_min", b"  _min: 9.8\n", "has no field _min"),
        ("copier.yml", "_min", b"_min: \xff\n", "can't be read: 'utf-8' codec"),
        ("info.xml", "id", b"<info>", "can't be read: no element found"),
        ("info.xml", "id", b"<info><id/></info>", "has no field id"),
        ("info.xml", "php@min-version", b"<info/>", "has no field php@min-version"),
        (
            "info.xml",
            "php@min-version",
            b"<info><php/></info>",
            "has no field php@min-version",
        ),
    ],
)
def test_a_file_without_its_value_is_named(
    file: str, field: str, content: bytes, message: str
) -> None:
    with pytest.raises(hooks.RequirementError) as error:
        hooks.values_in(hooks.Source(file, {"": field}, {}), content)

    assert str(error.value).startswith(message)


def test_the_build_reads_what_a_project_works_with_from_its_latest_release(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asked: list[str] = []
    answers: dict[str, bytes | Exception] = {
        raw("Dennis-Otto/tool", "v2.0.1", "hacs.json"): HACS,
        raw("Dennis-Otto/two", "v1.2.0", "appinfo/info.xml"): INFO,
    }
    monkeypatch.setattr(hooks, "download", files(answers, asked))
    catalog = hooks.read(
        catalog_data(
            entry(requires=source()),
            entry("two", requires=nextcloud()),
            entry("three", requires={"en": "Any computer", "de": "Jeder Computer"}),
            entry("four"),
        )
    )
    notes = {
        "Dennis-Otto/tool": (
            release("v2.0.1", "2026-10-20"),
            release("v2.0.0", "2026-10-01"),
        ),
        "Dennis-Otto/two": (release("v1.2.0", "2026-10-12"),),
    }

    assert hooks.requirements(catalog, notes) == {
        "tool": {
            "en": "Home Assistant 2026.8.0 or newer",
            "de": "Home Assistant 2026.8.0 oder neuer",
        },
        "two": {"en": "Nextcloud 33 to 35", "de": "Nextcloud 33 bis 35"},
        "three": {"en": "Any computer", "de": "Jeder Computer"},
    }
    # The file of the latest release alone, once.
    assert sorted(asked) == sorted(answers)


def test_a_new_value_in_the_file_of_a_release_changes_the_card(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    newer = HACS.replace(b'"2026.8.0"', b'"2026.10.1"')
    assert newer != HACS
    url = raw("Dennis-Otto/tool", "v2.1.0", "hacs.json")
    monkeypatch.setattr(hooks, "download", files({url: newer}, []))
    catalog = hooks.read(catalog_data(entry(requires=source())))
    works = hooks.requirements(
        catalog, {"Dennis-Otto/tool": (release("v2.1.0", "2026-10-24"),)}
    )

    section = hooks.section(catalog, catalog.groups[0], "de", {}, works)

    assert (
        '<p class="project-requires" markdown>:material-puzzle: Läuft mit Home '
        "Assistant 2026.10.1 oder neuer</p>"
    ) in section


def test_a_file_that_cant_be_read_leaves_the_line_off_the_card(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    gone = hooks.SearchError(
        f"{raw('Dennis-Otto/gone', 'v1.0.0', 'hacs.json')} can't be downloaded: "
        "HTTP Error 404: Not Found"
    )
    answers: dict[str, bytes | Exception] = {
        raw("Dennis-Otto/gone", "v1.0.0", "hacs.json"): gone,
        raw("Dennis-Otto/moved", "v1.0.0", "hacs.json"): b'{"name": "Moved"}',
    }
    monkeypatch.setattr(hooks, "download", files(answers, []))
    caplog.set_level(logging.INFO, logger="mkdocs.hooks.project")
    catalog = hooks.read(
        catalog_data(
            *(entry(slug, requires=source()) for slug in ("gone", "moved", "new"))
        )
    )
    notes = {
        "Dennis-Otto/gone": (release("v1.0.0", "2026-10-01"),),
        "Dennis-Otto/moved": (release("v1.0.0", "2026-10-01"),),
        "Dennis-Otto/new": (),
    }

    assert hooks.requirements(catalog, notes) == {}
    # Without a warning, which would fail the strict build while GitHub is away.
    assert {record.levelno for record in caplog.records} == {logging.INFO}
    why = "The card of {} leaves out what it works with until the next build: {}"
    assert sorted(record.getMessage() for record in caplog.records) == sorted(
        [
            why.format("gone", gone),
            why.format(
                "moved",
                "hacs.json of Dennis-Otto/moved at v1.0.0 has no field homeassistant",
            ),
            why.format("new", "the build has no release of Dennis-Otto/new"),
        ]
    )


def test_what_the_projects_work_with_is_read_once_for_every_language(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asked: list[str] = []
    url = raw("Dennis-Otto/tool", "v2.0.1", "hacs.json")
    monkeypatch.setattr(hooks, "download", files({url: HACS}, asked))
    catalog = hooks.read(catalog_data(entry(requires=source())))
    notes = {"Dennis-Otto/tool": (release("v2.0.1", "2026-10-20"),)}
    settings = SimpleNamespace(
        extra={"catalog": catalog, hooks.LEVEL: {}, hooks.NOTES: notes}
    )
    markdown = "<!-- projects -->\n"

    english = hooks.on_page_markdown(markdown, page("en"), settings, None)
    german = hooks.on_page_markdown(markdown, page("de"), settings, None)

    assert asked == [url]
    assert "Works with Home Assistant 2026.8.0 or newer</p>" in english
    assert "Läuft mit Home Assistant 2026.8.0 oder neuer</p>" in german


def test_texts_alone_need_no_release_and_no_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(hooks, "download", lambda url: pytest.fail(str(url)))
    requires = {"en": "Any computer", "de": "Jeder Computer"}
    catalog = hooks.read(catalog_data(entry(requires=requires)))
    settings = SimpleNamespace(extra={"catalog": catalog, hooks.LEVEL: {}})

    markdown = hooks.on_page_markdown("<!-- projects -->\n", page("en"), settings, None)

    assert "Works with Any computer</p>" in markdown
    assert hooks.NOTES not in settings.extra


def test_the_line_of_what_a_project_works_with_stands_right_above_the_buttons() -> None:
    catalog = hooks.read(
        catalog_data(entry(requires={"en": "Any computer", "de": "Jeder Computer"}))
    )
    project = catalog.projects[0]

    line = hooks.requirement(catalog, project, "de", {"tool": project.requires})
    parts = hooks.card(project, "de", None, "<div>live</div>", line).split("\n\n")

    assert line == (
        '<p class="project-requires" markdown>:material-puzzle: Läuft mit Jeder '
        "Computer</p>"
    )
    # Below the facts, and right above the buttons at the foot of the card.
    assert parts[4:6] == ["<div>live</div>", line]
    assert parts[6].startswith("[:material-download: Installieren]")


def test_a_card_without_what_its_project_works_with_has_no_line() -> None:
    catalog = hooks.read(catalog_data(entry(requires=source())))

    assert hooks.requirement(catalog, catalog.projects[0], "en", {}) == ""
    assert "project-requires" not in hooks.section(catalog, catalog.groups[0], "en")


def test_the_table_says_what_every_project_works_with() -> None:
    catalog = hooks.read(
        catalog_data(
            entry(requires=source()),
            entry("two", requires=nextcloud(), platform="Nextcloud"),
            entry("three", requires={"en": "Linux | macOS", "de": "Linux"}),
            entry("four"),
        )
    )

    rows = hooks.table(catalog).splitlines()

    assert rows[0] == "| Project | What it does | Works with | Start | Website |"
    # The platform and the file, which the link check checks, or the text.
    cells = [row.split(" | A tool | ")[1].split(" | [Install]")[0] for row in rows[2:]]
    assert cells == [
        "Home Assistant ([hacs.json]"
        "(https://github.com/Dennis-Otto/tool/blob/HEAD/hacs.json))",
        "Nextcloud ([appinfo/info.xml]"
        "(https://github.com/Dennis-Otto/two/blob/HEAD/appinfo/info.xml))",
        "Linux \\| macOS",
        "—",
    ]


def test_the_structured_data_names_what_every_project_works_with() -> None:
    catalog = hooks.read(catalog_data(entry(), entry("two", platform="Nextcloud")))
    works = {"tool": {"en": "Home Assistant 2026.8.0 or newer", "de": "neuer"}}

    head = hooks.structured_data(catalog, SITE, "Site", works)

    block = LD_JSON.search(head)
    assert block is not None
    items = json.loads(block.group(1))["@graph"][2]["itemListElement"]
    # The platform of a project whose build has nothing that it works with.
    assert [item["item"]["runtimePlatform"] for item in items] == [
        "Home Assistant 2026.8.0 or newer",
        "Nextcloud",
    ]


def test_the_home_page_names_what_every_project_works_with() -> None:
    settings = build()
    settings.extra[hooks.WORKS] = {
        "paperless-sync": {
            "en": "Nextcloud 33 to 35 and Paperless-ngx",
            "de": "Nextcloud 33 bis 35 und Paperless-ngx",
        }
    }

    output = hooks.on_post_page(HTML, page_at("index.html"), settings)

    blocks = LD_JSON.findall(output)
    items = json.loads(blocks[0])["@graph"][2]["itemListElement"]
    assert [item["item"]["runtimePlatform"] for item in items] == [
        "Home Assistant",
        "Google Chrome",
        "Nextcloud 33 to 35 and Paperless-ngx",
        "Nextcloud",
        "GitHub Actions",
        "Copier",
    ]


# The Trust page.


def test_a_project_with_a_repo_may_name_the_file_that_its_users_install() -> None:
    catalog = hooks.read(catalog_data(entry(asset="homedarts.zip"), entry("two")))
    first, second = catalog.projects

    assert first.asset == "homedarts.zip"
    assert first.verified == "homedarts.zip"
    # Without one, the commands take the SBOM that every release carries.
    assert second.asset is None
    assert second.verified == "two.spdx.json"


@pytest.mark.parametrize("asset", ["a b.zip", "../tool.zip", "*.zip", "-tool.zip", "x;y"])
def test_an_asset_is_the_name_of_a_file(asset: str) -> None:
    assert problems(catalog_data(entry(asset=asset))) == [
        "tool: asset must be the name of a file of its releases, such as "
        f"homedarts.zip, not {asset!r}."
    ]


def test_asset_is_for_a_project_with_a_repo() -> None:
    project = without_repo(entry(asset="tool.zip"))

    assert problems(catalog_data(project)) == ["tool: asset is for a project with a repo."]


def test_the_catalog_needs_the_texts_of_the_trust_page() -> None:
    data = catalog_data()
    del data["trust"]

    assert problems(data) == ["trust is missing."]


def test_the_texts_of_the_trust_page_must_be_a_table() -> None:
    data = catalog_data()
    data["trust"] = ["Guarantee"]

    assert problems(data) == ["trust must be a table."]


def test_every_problem_of_the_texts_of_the_trust_page_is_named() -> None:
    data = catalog_data()
    trust = data["trust"]
    trust["colour"] = "blue"
    del trust["numbers"]
    trust["release"] = {"en": "Latest release"}
    trust["tag"] = "gitsign"
    trust["sbom"]["kind"] = "SPDX"
    del trust["vex"]["value"]
    del trust["policy"]
    trust["report"]["value"]["de"] = "vertraulich"

    assert problems(data) == [
        "trust.colour is unknown; known are tag, provenance, immutable, sbom, vex, "
        "policy, report, numbers, project, release, coverage, mutation, scorecard, "
        "bestpractices, note.",
        "trust.tag must be a table.",
        "trust.sbom.kind is unknown; known are label, value.",
        "trust.vex.value needs a text in every language: trust.vex.value.en, "
        "trust.vex.value.de.",
        "trust.policy is missing.",
        "trust.report.value.de must hold {} once, where the links to every project "
        "go, not 'vertraulich'.",
        "trust.numbers needs a text in every language: trust.numbers.en, "
        "trust.numbers.de.",
        "trust.release.de is missing.",
    ]


def trust_catalog() -> Any:
    """A catalog with two projects with a repo, the first with its short name, its
    project at bestpractices.dev and the file that its users install, and a third
    without a repo."""
    short = {"en": "Tool", "de": "Werkzeug"}
    return hooks.read(
        catalog_data(
            entry(short=short, bestpractices=1, asset="tool.zip"),
            entry("two", bestpractices=2),
            without_repo(entry("site")),
        )
    )


def test_the_guarantees_that_every_project_shares_are_listed_once() -> None:
    shared = hooks.shared_guarantees(trust_catalog(), "en")

    assert shared.split("\n") == [
        '<dl class="trust-shared">',
        "<div><dt>Tag</dt><dd>tag value</dd></div>",
        "<div><dt>Provenance</dt><dd>provenance value</dd></div>",
        "<div><dt>Immutable</dt><dd>immutable value</dd></div>",
        "<div><dt>Sbom</dt><dd>sbom value</dd></div>",
        "<div><dt>Vex</dt><dd>vex value</dd></div>",
        # The security policy and the form for private reports of every project with
        # a repo, under its short name, in the place of {}.
        '<div><dt>Policy</dt><dd>policy value: <a href="https://github.com/'
        'Dennis-Otto/tool/blob/main/SECURITY.md">Tool</a>, <a href="https://'
        'github.com/Dennis-Otto/two/blob/main/SECURITY.md">The tool</a></dd></div>',
        '<div><dt>Report</dt><dd>report value: <a href="https://github.com/'
        'Dennis-Otto/tool/security/advisories/new">Tool</a>, <a href="https://'
        'github.com/Dennis-Otto/two/security/advisories/new">The tool</a></dd></div>',
        "</dl>",
    ]
    assert "Dennis-Otto/site" not in shared


def test_the_guarantees_that_every_project_shares_are_in_the_language() -> None:
    shared = hooks.shared_guarantees(trust_catalog(), "de")

    assert "<div><dt>Tag auf Deutsch</dt><dd>tag value auf Deutsch</dd></div>" in shared
    assert ">Werkzeug</a>, <a " in shared
    assert shared.count("</a> auf Deutsch</dd>") == 2


def test_the_numbers_have_a_row_for_every_project_with_a_repo() -> None:
    table = hooks.numbers_table(trust_catalog(), "de", {1: "silver"})
    lines = table.split("\n")

    # Its text names the table for screen readers, as the heading above it does,
    # without the permalink of the heading; its part of the page tells the script
    # where the data is and the language of the page.
    assert lines[:2] == [
        '<div class="trust" data-facts="/repo-blueprint/dashboard/repos.json"'
        ' data-history="/repo-blueprint/dashboard/history.json" data-locale="de">',
        '<table aria-label="Numbers auf Deutsch">',
    ]
    # A column for the project and one for each number.
    assert lines[2] == (
        '<thead><tr><th scope="col">Project auf Deutsch</th>'
        '<th scope="col">Release auf Deutsch</th>'
        '<th scope="col">Coverage auf Deutsch</th>'
        '<th scope="col">Mutation auf Deutsch</th>'
        '<th scope="col">Scorecard auf Deutsch</th>'
        '<th scope="col">Bestpractices auf Deutsch</th></tr></thead>'
    )
    # Each project under its short name, which links its website in the language.
    heads = re.findall(r'<tr><th scope="row">(.*?)</th>', table)
    assert heads == [
        '<a href="https://dennis-otto.github.io/tool/de/">Werkzeug</a>',
        '<a href="https://dennis-otto.github.io/two/de/">Das Werkzeug</a>',
    ]
    assert "Dennis-Otto/site" not in table
    assert lines[-3:] == ["</tbody>", "</table>", "</div>"]


def test_every_number_of_a_project_has_its_label_for_a_phone() -> None:
    table = hooks.numbers_table(trust_catalog(), "en", {1: "silver"})
    rows = re.findall(r'<tr><th scope="row">.*?</th>(.*?)</tr>', table)
    cells = [re.findall(r"<td[^>]*>.*?</td>", row) for row in rows]

    # The script fills the cells of a live number; without it, the release links
    # the releases on GitHub, and the others hold a dash. On a phone, each cell
    # shows its data-label beside its value.
    assert cells[0] == [
        '<td data-label="Release" data-repo="Dennis-Otto/tool" data-fact="release">'
        '<a href="https://github.com/Dennis-Otto/tool/releases/latest">GitHub</a></td>',
        '<td data-label="Coverage" data-repo="Dennis-Otto/tool" data-fact="coverage">'
        "—</td>",
        '<td data-label="Mutation" data-repo="Dennis-Otto/tool" data-fact="mutation">'
        "—</td>",
        '<td data-label="Scorecard" data-repo="Dennis-Otto/tool"'
        ' data-fact="scorecard">—</td>',
        # The level of the Best Practices, as the build read it.
        '<td data-label="Bestpractices">'
        '<a href="https://www.bestpractices.dev/projects/1">silver</a></td>',
    ]
    # Or a dash without one.
    assert cells[1][0] == (
        '<td data-label="Release" data-repo="Dennis-Otto/two" data-fact="release">'
        '<a href="https://github.com/Dennis-Otto/two/releases/latest">GitHub</a></td>'
    )
    assert cells[1][-1] == '<td data-label="Bestpractices">—</td>'


def test_the_numbers_without_levels_have_a_dash_for_every_project() -> None:
    table = hooks.numbers_table(trust_catalog(), "en")

    assert "bestpractices.dev" not in table
    assert table.count('<td data-label="Bestpractices">—</td>') == 2


def test_the_numbers_of_the_trust_page_have_their_note_below_them() -> None:
    catalog = trust_catalog()

    text = hooks.guarantees(catalog, "de", {1: "silver"})

    # The table, with its note below it; the page has the headings.
    assert text == "\n\n".join(
        [
            hooks.numbers_table(catalog, "de", {1: "silver"}),
            "Aus dem [Dashboard](https://example.org/dashboard/).",
        ]
    )


def test_the_trust_page_escapes_its_texts() -> None:
    data = catalog_data(
        entry(name={"en": 'The "best" <tool>', "de": "Das Werkzeug"}, bestpractices=1)
    )
    data["trust"]["project"]["en"] = "Projects & more"
    data["trust"]["numbers"]["en"] = 'The "numbers"'
    data["trust"]["coverage"]["en"] = 'The "coverage"'
    data["trust"]["tag"]["label"]["en"] = "<Signed> tags"
    data["trust"]["sbom"]["value"]["en"] = 'SPDX "and" CycloneDX'
    data["trust"]["policy"]["value"]["en"] = "<{}>"
    data["facts"]["gold"]["en"] = "<gold>"
    catalog = hooks.read(data)

    shared = hooks.shared_guarantees(catalog, "en")
    table = hooks.numbers_table(catalog, "en", {1: "gold"})

    assert "<dt>&lt;Signed&gt; tags</dt>" in shared
    assert "<dd>SPDX &quot;and&quot; CycloneDX</dd>" in shared
    assert "<dd>&lt;<a href=" in shared
    assert ">The &quot;best&quot; &lt;tool&gt;</a>&gt;</dd>" in shared
    assert '<th scope="col">Projects &amp; more</th>' in table
    assert '<table aria-label="The &quot;numbers&quot;">' in table
    assert '<td data-label="The &quot;coverage&quot;" data-repo=' in table
    assert ">The &quot;best&quot; &lt;tool&gt;</a></th>" in table
    assert ">&lt;gold&gt;</a></td>" in table


def test_the_real_trust_page_names_each_shared_guarantee_once() -> None:
    catalog = hooks.load(ROOT)
    projects = [project for project in catalog.projects if project.repo is not None]

    for language in catalog.languages:
        text = hooks.shared_guarantees(catalog, language) + hooks.guarantees(
            catalog, language, {}
        )
        for key in VALUED_ROWS:
            value = catalog.trust.values[key][language].partition("{}")[0]
            assert text.count(f"<dd>{escape(value)}") == 1, (language, key)
        # Each project has its row of numbers, and its links to its security policy
        # and to its form for private reports.
        assert text.count('<tr><th scope="row">') == len(projects)
        assert text.count("/blob/main/SECURITY.md") == len(projects)
        assert text.count("/security/advisories/new") == len(projects)


def test_the_commands_verify_the_latest_release_of_every_project() -> None:
    commands = hooks.verification(trust_catalog(), "de")

    assert commands == (
        '=== "Werkzeug"\n'
        "\n"
        "    ```sh\n"
        "    gh release verify --repo Dennis-Otto/tool\n"
        "    gh release download --repo Dennis-Otto/tool --pattern tool.zip --clobber\n"
        "    gh attestation verify tool.zip --repo Dennis-Otto/tool --signer-workflow"
        " Dennis-Otto/tool/.github/workflows/build-release.yml\n"
        "    ```\n"
        "\n"
        '=== "Das Werkzeug"\n'
        "\n"
        "    ```sh\n"
        "    gh release verify --repo Dennis-Otto/two\n"
        "    gh release download --repo Dennis-Otto/two --pattern two.spdx.json --clobber\n"
        "    gh attestation verify two.spdx.json --repo Dennis-Otto/two"
        " --signer-workflow Dennis-Otto/two/.github/workflows/build-release.yml\n"
        "    ```"
    )


def test_the_title_of_a_tab_of_the_commands_keeps_its_quotes() -> None:
    catalog = hooks.read(
        catalog_data(entry(name={"en": 'The "tool"', "de": "Das Werkzeug"}))
    )

    assert hooks.verification(catalog, "en").startswith('=== "The &quot;tool&quot;"\n')


@pytest.mark.parametrize(
    ("locale", "language"), [("de", "de"), ("en", "en"), ("fr", "en"), (None, "en")]
)
def test_the_table_and_the_commands_take_the_place_of_their_markers(
    locale: str | None, language: str
) -> None:
    catalog = trust_catalog()
    # The levels that the build read once for every language.
    settings = SimpleNamespace(extra={"catalog": catalog, hooks.LEVEL: {1: "gold"}})
    markdown = (
        "# Trust\n\n<!-- trust-shared -->\n\n<!-- trust -->\n\n"
        "## Check\n\n<!-- verify --> \n"
    )

    result = hooks.on_page_markdown(markdown, page(locale), settings, None)

    assert result == (
        f"# Trust\n\n{hooks.shared_guarantees(catalog, language)}\n\n"
        f"{hooks.guarantees(catalog, language, {1: 'gold'})}\n\n"
        f"## Check\n\n{hooks.verification(catalog, language)}\n"
    )


@pytest.mark.parametrize(
    ("dest_uri", "language"),
    [
        ("index.html", "en"),
        ("de/index.html", "de"),
        ("en/index.html", None),
        ("de/security.html", None),
        ("fr/index.html", None),
    ],
)
def test_the_home_pages_are_the_index_of_the_root_and_of_each_language(
    dest_uri: str, language: str | None
) -> None:
    assert hooks.home_language(hooks.read(catalog_data()), dest_uri) == language


# The table of the README.


def test_the_table_lists_every_project_with_the_address_of_every_language() -> None:
    plain = entry("plain", tagline={"en": "Yes | no", "de": "Ja | nein"})
    del plain["docs"]
    plain["start"]["label"]["en"] = "Get | it"
    dashboard = entry(
        "dashboard",
        name={"en": "The board", "de": "Die Tafel"},
        start={
            "icon": "material-arrow-right",
            "label": {"en": "Open", "de": "Öffnen"},
            "url": {"en": "https://example.org/", "de": "https://example.org/de/"},
        },
        docs="https://example.org/docs/",
    )
    without_repo(dashboard)
    catalog = hooks.read(catalog_data(entry("tool"), plain, dashboard))

    assert hooks.table(catalog) == "\n".join(
        [
            "| Project | What it does | Works with | Start | Website |",
            "| --- | --- | --- | --- | --- |",
            "| [tool](https://github.com/Dennis-Otto/tool) | A tool | — "
            "| [Install](https://example.org/install) "
            "| [dennis-otto.github.io/tool](https://dennis-otto.github.io/tool/) · "
            "[dennis-otto.github.io/tool/de](https://dennis-otto.github.io/tool/de/) |",
            "| [plain](https://github.com/Dennis-Otto/plain) | Yes \\| no | — "
            "| [Get \\| it](https://example.org/install) | — |",
            "| The board | A tool | — "
            "| [Open](https://example.org/) · [Öffnen](https://example.org/de/) "
            "| [example.org/docs](https://example.org/docs/) |",
        ]
    )


def test_the_table_replaces_what_stands_between_the_markers() -> None:
    catalog = hooks.read(catalog_data())
    text = "# Title\n\n<!-- projects:start -->\nold\n<!-- projects:end -->\n\nEnd\n"

    written = hooks.readme(text, catalog)

    assert written == (
        "# Title\n\n<!-- projects:start -->\n\n"
        f"{hooks.table(catalog)}\n\n<!-- projects:end -->\n\nEnd\n"
    )
    assert hooks.readme(written, catalog) == written


@pytest.mark.parametrize(
    "text",
    [
        "No markers\n",
        "<!-- projects:start -->\n",
        "<!-- projects:end -->\n",
        "<!-- projects:end -->\n<!-- projects:start -->\n",
    ],
)
def test_the_readme_needs_both_markers_in_order(text: str) -> None:
    with pytest.raises(hooks.CatalogError, match=r"README\.md needs the lines"):
        hooks.readme(text, hooks.read(catalog_data()))


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


def config(root: Path, *languages: SimpleNamespace, nav: Any = None) -> Any:
    """The parts of the configuration of MkDocs that the hooks read."""
    plugins: dict[str, Any] = {}
    if languages:
        plugins["i18n"] = SimpleNamespace(
            config=SimpleNamespace(languages=list(languages))
        )
    return SimpleNamespace(
        config_file_path=str(root / "mkdocs.yml"),
        docs_dir=str(root / "docs"),
        extra={},
        nav=nav,
        plugins=plugins,
    )


def website(root: Path) -> Path:
    """A repository at root with this catalog, the pages of the former websites that
    it names and the pages of its documentation."""
    shutil.copyfile(ROOT / "projects.toml", root / "projects.toml")
    shutil.copytree(ROOT / "former", root / "former")
    docs = root / "docs"
    (docs / "decisions").mkdir(parents=True)
    for page in ("index.md", "index.de.md", "decisions/README.md"):
        (docs / page).write_text("# Page\n", encoding="utf-8")
    return docs


GERMAN = language(
    "de", nav_translations={"Home": "Startseite", "Decisions": "Entscheidungen"}
)
NAV = [{"Home": "index.md"}, {"Decisions": "decisions/README.md"}]


def test_on_config_gives_the_templates_the_catalog(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    website(tmp_path)
    settings = config(tmp_path, language("en"), GERMAN, nav=NAV)

    assert hooks.on_config(settings) is settings

    assert settings.extra["catalog"] == hooks.load(ROOT)
    assert caplog.messages == []


def test_on_config_reads_the_catalog_once_for_every_language(tmp_path: Path) -> None:
    website(tmp_path)
    settings = config(tmp_path, language("en"), GERMAN, nav=NAV)
    hooks.on_config(settings)
    catalog = settings.extra["catalog"]
    # The build of the German website has the same configuration.
    (tmp_path / "projects.toml").unlink()

    assert hooks.on_config(settings) is settings
    assert settings.extra["catalog"] is catalog


def test_on_config_stops_the_build_at_a_broken_catalog(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class PluginError(Exception):
        pass

    # MkDocs, which the tests of the script don't install.
    monkeypatch.setitem(sys.modules, "mkdocs", ModuleType("mkdocs"))
    monkeypatch.setitem(
        sys.modules, "mkdocs.exceptions", SimpleNamespace(PluginError=PluginError)
    )
    (tmp_path / "projects.toml").write_text("languages = []\n", encoding="utf-8")

    with pytest.raises(PluginError, match="languages must list"):
        hooks.on_config(config(tmp_path))


def test_on_config_warns_about_what_lacks_a_translation(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    docs = website(tmp_path)
    (docs / "guide.md").write_text("# Guide\n", encoding="utf-8")
    nav = [*NAV, {"Guide": "guide.md"}]

    hooks.on_config(config(tmp_path, language("en"), GERMAN, nav=nav))

    assert caplog.messages == [
        "The menu title 'Guide' has no translation in de: add it to "
        "nav_translations of de in mkdocs.yml.",
        "docs/guide.md has no translation in de: write docs/guide.de.md, or list "
        "the page in UNTRANSLATED of .github/mkdocs_project.py.",
    ]
    assert {record.levelno for record in caplog.records} == {logging.WARNING}
    assert {record.name for record in caplog.records} == {"mkdocs.hooks.project"}


def test_on_config_checks_nothing_on_a_website_in_one_language(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    docs = website(tmp_path)
    (docs / "guide.md").write_text("# Guide\n", encoding="utf-8")

    hooks.on_config(config(tmp_path, nav=[{"Guide": "guide.md"}]))

    assert caplog.messages == []


def test_a_language_of_the_website_needs_the_texts_of_the_catalog(
    caplog: pytest.LogCaptureFixture,
) -> None:
    hooks.check_languages(hooks.read(catalog_data()), [language("en"), language("fr")])

    assert caplog.messages == [
        "The website is built in fr, but projects.toml has no texts in it: add fr to "
        "its languages, and a text in it to every project."
    ]


def test_the_languages_of_the_website_are_those_built_the_default_first() -> None:
    french = language("fr", build=False)
    settings = config(Path(), GERMAN, french, language("en"))

    assert [item.locale for item in hooks.built_languages(settings)] == ["en", "de"]


def test_every_title_of_the_menu_needs_a_translation(
    caplog: pytest.LogCaptureFixture,
) -> None:
    nav = [
        "index.md",
        {"Home": "index.md"},
        {"Guide": [{"Install": "install.md"}, "faq.md", {"Use": "use.md"}]},
    ]
    languages = [
        language("en"),
        language("de", nav_translations={"Home": "Start", "Use": "Benutzen"}),
        language("nl"),
    ]

    hooks.check_menu(nav, languages)

    assert [message.split(":")[0] for message in caplog.messages] == [
        "The menu title 'Guide' has no translation in de",
        "The menu title 'Install' has no translation in de",
        "The menu title 'Home' has no translation in nl",
        "The menu title 'Guide' has no translation in nl",
        "The menu title 'Install' has no translation in nl",
        "The menu title 'Use' has no translation in nl",
    ]


def test_a_menu_from_the_pages_needs_no_translations(
    caplog: pytest.LogCaptureFixture,
) -> None:
    hooks.check_menu(None, [language("en"), language("de")])

    assert caplog.messages == []


def test_an_untranslated_page_must_be_listed_and_leave_the_list_once_translated(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(hooks, "UNTRANSLATED", frozenset({"security.md"}))
    docs = tmp_path / "docs"
    (docs / "guide" / "decisions").mkdir(parents=True)
    (docs / "decisions").mkdir()
    for page in (
        "index.md",
        "index.de.md",
        "security.md",
        "decisions/0001-record.md",
        "guide/setup.md",
        "guide/decisions/x.md",
        "notes.v2.md",
    ):
        (docs / page).write_text("# Page\n", encoding="utf-8")
    languages = [language("en"), language("de")]

    hooks.check_pages(docs, languages)
    (docs / "security.de.md").write_text("# Sicherheit\n", encoding="utf-8")
    hooks.check_pages(docs, languages)

    assert caplog.messages == [
        "docs/guide/decisions/x.md has no translation in de: write "
        "docs/guide/decisions/x.de.md, or list the page in UNTRANSLATED of "
        ".github/mkdocs_project.py.",
        "docs/guide/setup.md has no translation in de: write docs/guide/setup.de.md,"
        " or list the page in UNTRANSLATED of .github/mkdocs_project.py.",
        "docs/notes.v2.md has no translation in de: write docs/notes.v2.de.md, or "
        "list the page in UNTRANSLATED of .github/mkdocs_project.py.",
    ] * 2 + [
        "docs/security.md has its translation docs/security.de.md now: remove it "
        "from UNTRANSLATED in .github/mkdocs_project.py."
    ]


def test_a_page_may_carry_the_suffix_of_the_default_language(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(hooks, "UNTRANSLATED", frozenset({"security.md"}))
    docs = tmp_path / "docs"
    docs.mkdir()
    for name in ("guide.en.md", "guide.de.md", "faq.en.md", "security.en.md"):
        (docs / name).write_text("# Page\n", encoding="utf-8")

    hooks.check_pages(docs, [language("en"), language("de")])

    assert caplog.messages == [
        "docs/faq.en.md has no translation in de: write docs/faq.de.md, or list "
        "the page in UNTRANSLATED of .github/mkdocs_project.py.",
    ]


def page(locale: str | None) -> SimpleNamespace:
    """A page of MkDocs, whose file has the language that the i18n plugin gives it."""
    file = SimpleNamespace() if locale is None else SimpleNamespace(locale=locale)
    return SimpleNamespace(file=file)


@pytest.mark.parametrize(
    ("locale", "language"), [("de", "de"), ("en", "en"), ("fr", "en"), (None, "en")]
)
def test_the_cards_take_the_place_of_the_marker_in_the_language_of_the_page(
    locale: str | None, language: str
) -> None:
    catalog = hooks.read(catalog_data())
    settings = SimpleNamespace(extra={"catalog": catalog})
    markdown = "# Home\n\n<!-- projects -->  \n\n## Support\n"

    result = hooks.on_page_markdown(markdown, page(locale), settings, None)

    assert result == f"# Home\n\n{hooks.cards(catalog, language)}\n\n## Support\n"


def test_a_marker_within_a_line_stays_as_it_is() -> None:
    settings = SimpleNamespace(extra={"catalog": hooks.read(catalog_data())})
    markdown = "The line `<!-- projects -->` marks the cards.\n"

    assert hooks.on_page_markdown(markdown, page("en"), settings, None) == markdown


def test_mkdocs_serve_builds_again_when_the_catalog_changes(tmp_path: Path) -> None:
    watched: list[str] = []
    server = SimpleNamespace(watch=watched.append)

    assert hooks.on_serve(server, config(tmp_path), None) is server
    assert watched == [str(tmp_path / "projects.toml")]


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
TITLE = "Open-source apps for Home Assistant, Nextcloud and Paperless-ngx"


def build(site: Path | None = None) -> SimpleNamespace:
    """The parts of the configuration of MkDocs that the hooks of a build read."""
    return SimpleNamespace(
        # Nothing that the projects work with, which the build reads from GitHub.
        extra={"catalog": hooks.load(ROOT), hooks.WORKS: {}},
        site_dir=str(site),
        site_url=SITE,
        site_name="Dennis Otto",
    )


def test_robots_lists_the_sitemap_of_every_website_at_the_address_once() -> None:
    elsewhere = entry("elsewhere", docs="https://elsewhere.example.org/docs/")
    plain = entry("plain")
    del plain["docs"]
    page = entry("page", docs={"en": f"{SITE}page/guide.html", "de": f"{SITE}de/"})
    twice = entry("twice", docs=f"{SITE}tool/")
    catalog = hooks.read(catalog_data(entry(), elsewhere, plain, page, twice))

    assert hooks.robots(catalog, SITE) == (
        f"# Every website at {SITE} with its sitemap, from projects.toml of\n"
        "# https://github.com/Dennis-Otto/dennis-otto.github.io\n"
        "User-agent: *\n"
        "Allow: /\n"
        "\n"
        f"Sitemap: {SITE}sitemap.xml\n"
        f"Sitemap: {SITE}tool/sitemap.xml\n"
        f"Sitemap: {SITE}page/sitemap.xml\n"
    )


def test_robots_of_the_address_lists_the_sitemap_of_every_website() -> None:
    lines = hooks.robots(hooks.load(ROOT), SITE).splitlines()

    assert [line for line in lines if line.startswith("Sitemap:")] == [
        f"Sitemap: {SITE}sitemap.xml",
        f"Sitemap: {SITE}homedarts-for-autodarts/sitemap.xml",
        f"Sitemap: {SITE}player-switch-for-autodarts/sitemap.xml",
        f"Sitemap: {SITE}paperless-sync/sitemap.xml",
        f"Sitemap: {SITE}paperless-unified-search/sitemap.xml",
        f"Sitemap: {SITE}issue-assistant/sitemap.xml",
        f"Sitemap: {SITE}repo-blueprint/sitemap.xml",
    ]


def test_security_txt_has_the_fields_of_rfc_9116() -> None:
    text = hooks.security_txt(hooks.load(ROOT), SITE, date(2026, 10, 13))

    assert text == (
        f"# Report a vulnerability of any website at {SITE} privately.\n"
        "Contact: https://github.com/Dennis-Otto/dennis-otto.github.io/security/"
        "advisories/new\n"
        "Expires: 2027-10-13T00:00:00Z\n"
        "Preferred-Languages: en, de\n"
        f"Canonical: {SITE}.well-known/security.txt\n"
        f"Canonical: {SITE}security.txt\n"
        f"Policy: {SITE}security.html\n"
    )


@pytest.mark.parametrize(
    "today", [date(2026, 10, 13), date(2027, 3, 1), date(2028, 2, 29)]
)
def test_security_txt_expires_at_the_midnight_a_year_after_the_build(
    today: date,
) -> None:
    text = hooks.security_txt(hooks.read(catalog_data()), SITE, today)
    field = re.search(r"^Expires: (.+)$", text, re.MULTILINE)
    assert field is not None

    # RFC 3339 in UTC; less than a year after any moment of the day of the build.
    expires = datetime.fromisoformat(field.group(1))
    midnight = datetime(today.year, today.month, today.day, tzinfo=UTC)
    assert expires.utcoffset() == timedelta(0)
    assert expires - midnight == timedelta(days=365)


def test_the_day_of_the_build_is_that_of_source_date_epoch_in_utc(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SOURCE_DATE_EPOCH", EPOCH)

    assert hooks.build_date() == date(2026, 10, 13)


def test_the_day_of_the_build_is_today_in_utc(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SOURCE_DATE_EPOCH", raising=False)
    before = datetime.now(UTC).date()

    built = hooks.build_date()

    assert before <= built <= datetime.now(UTC).date()


def test_on_post_build_writes_robots_and_security_txt_at_the_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv("SOURCE_DATE_EPOCH", EPOCH)
    (tmp_path / "security.html").write_text("<html></html>", encoding="utf-8")
    settings = build(tmp_path)
    catalog = settings.extra["catalog"]

    home = sitemap(f"{SITE}index.html")
    (tmp_path / "sitemap.xml").write_text(home, encoding="utf-8", newline="\n")

    hooks.on_post_build(settings)
    # The build of the German website, into the same folder.
    hooks.on_post_build(settings)

    robots = hooks.robots(catalog, SITE)
    security = hooks.security_txt(catalog, SITE, date(2026, 10, 13))
    assert (tmp_path / "robots.txt").read_bytes() == robots.encode()
    for name in (".well-known/security.txt", "security.txt"):
        assert (tmp_path / name).read_bytes() == security.encode()
    sitemaps = (tmp_path / "sitemap.xml").read_text(encoding="utf-8")
    assert f"<loc>{SITE}</loc>" in sitemaps
    assert caplog.messages == []


def test_on_post_build_warns_when_the_policy_of_security_txt_is_missing(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    hooks.on_post_build(build(tmp_path))

    assert (tmp_path / ".well-known" / "security.txt").is_file()
    assert caplog.messages == [
        "security.txt names https://dennis-otto.github.io/security.html as the "
        "policy of the address, but the website has no such page: keep "
        "docs/security.md, or change POLICY in .github/mkdocs_project.py."
    ]


@pytest.mark.parametrize(
    ("page", "target"),
    [
        ("index.html", f"{SITE}new/"),
        ("de/index.html", f"{SITE}new/de/"),
        ("branding/index.html", f"{SITE}new/branding/"),
        ("games.html", f"{SITE}new/games.html"),
        ("de/games.html", f"{SITE}new/de/games.html"),
        ("reindex.html", f"{SITE}new/reindex.html"),
    ],
)
def test_an_old_page_leads_to_the_same_page_in_the_new_folder(
    page: str, target: str
) -> None:
    # As MkDocs links a page index.html: by its folder.
    assert hooks.moved_to(f"{SITE}new/", page) == target


def test_the_page_at_an_old_address_leads_to_the_new_one_with_its_fragment() -> None:
    target = f"{SITE}homedarts-for-autodarts/de/games.html"

    page = hooks.moved_page("HomeDarts for Autodarts", target, "de")

    assert page == (
        "<!doctype html>\n"
        '<html lang="de">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>Diese Seite ist umgezogen - HomeDarts for Autodarts</title>\n"
        '<meta name="robots" content="noindex">\n'
        f'<link rel="canonical" href="{target}">\n'
        f'<meta http-equiv="refresh" content="0; url={target}">\n'
        f'<script>location.replace("{target}" + location.search + location.hash);'
        "</script>\n"
        "</head>\n"
        "<body>\n"
        "<p>Diese Seite ist auf die Website von HomeDarts for Autodarts umgezogen: "
        f'<a href="{target}">dennis-otto.github.io/homedarts-for-autodarts/de/games.html'
        "</a></p>\n"
        "</body>\n"
        "</html>\n"
    )


@pytest.mark.parametrize("language", ["en", "fr"])
def test_a_page_at_an_old_address_is_in_english_without_texts_of_its_language(
    language: str,
) -> None:
    page = hooks.moved_page("The tool", f"{SITE}tool/", language)

    assert f'<html lang="{language}">' in page
    assert "<title>This page has moved - The tool</title>" in page
    assert (
        "<p>This page has moved to the website of The tool: "
        f'<a href="{SITE}tool/">dennis-otto.github.io/tool/</a></p>'
    ) in page


def test_no_text_or_address_breaks_the_page_at_an_old_address() -> None:
    page = hooks.moved_page('<b>"A & B"</b>', 'https://example.org/"</script><x', "en")

    assert "&lt;b&gt;&quot;A &amp; B&quot;&lt;/b&gt;" in page
    href = "https://example.org/&quot;&lt;/script&gt;&lt;x"
    assert f'<link rel="canonical" href="{href}">' in page
    # No address can end the script early.
    script = page[page.index("<script>") : page.index("</script>")]
    assert script == (
        '<script>location.replace("https://example.org/\\"\\u003c/script>\\u003cx" '
        "+ location.search + location.hash);"
    )
    assert "<b>" not in page


def test_every_old_page_gets_its_page_in_the_language_of_its_folder() -> None:
    catalog = hooks.read(catalog_data(entry(former=["old-tool"]), entry("two")))
    catalog = dataclasses.replace(
        catalog, former_pages={"old-tool": ("index.html", "de/guide.html")}
    )

    pages = hooks.moved_pages(catalog)

    assert pages == {
        "old-tool/index.html": hooks.moved_page("The tool", f"{SITE}tool/", "en"),
        "old-tool/de/guide.html": hooks.moved_page(
            "Das Werkzeug", f"{SITE}tool/de/guide.html", "de"
        ),
    }


def test_the_old_website_of_homedarts_for_autodarts_leads_to_the_new_one() -> None:
    pages = hooks.moved_pages(hooks.load(ROOT))

    assert len(pages) == 72
    assert pages["ha-autodarts/index.html"] == hooks.moved_page(
        "HomeDarts for Autodarts", f"{SITE}homedarts-for-autodarts/", "en"
    )
    assert pages["ha-autodarts/de/games.html"] == hooks.moved_page(
        "HomeDarts for Autodarts", f"{SITE}homedarts-for-autodarts/de/games.html", "de"
    )
    assert all(name.startswith("ha-autodarts/") for name in pages)


def test_on_post_build_writes_a_page_at_every_old_address(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SOURCE_DATE_EPOCH", EPOCH)
    (tmp_path / "security.html").write_text("<html></html>", encoding="utf-8")
    settings = build(tmp_path)

    hooks.on_post_build(settings)
    # The build of the German website, into the same folder.
    hooks.on_post_build(settings)

    pages = hooks.moved_pages(settings.extra["catalog"])
    written = sorted(
        path.relative_to(tmp_path).as_posix()
        for path in (tmp_path / "ha-autodarts").rglob("*")
        if path.is_file()
    )
    assert written == sorted(pages)
    for name, page in pages.items():
        assert (tmp_path / name).read_bytes() == page.encode(), name


def files_at(*dest_uris: str) -> list[SimpleNamespace]:
    """The files of a website, as MkDocs gives them to on_files."""
    return [SimpleNamespace(dest_uri=dest_uri) for dest_uri in dest_uris]


def test_no_file_of_the_website_goes_into_a_former_folder(
    caplog: pytest.LogCaptureFixture,
) -> None:
    settings = build()
    files = files_at(
        "index.html",
        "ha-autodarts/games.html",
        "ha-autodarts-v2/games.html",
        "images/ha-autodarts/x.webp",
        "ha-autodarts/images/x.webp",
    )

    assert hooks.on_files(files, settings) is files
    assert caplog.messages == [
        f"The website writes {name} into ha-autodarts, the folder of a former website "
        "in projects.toml, whose old addresses lead to its website now: move the file "
        "out of the folder."
        for name in ("ha-autodarts/games.html", "ha-autodarts/images/x.webp")
    ]
    assert {record.levelno for record in caplog.records} == {logging.WARNING}


def test_a_catalog_without_former_folders_takes_every_file(
    caplog: pytest.LogCaptureFixture,
) -> None:
    settings = SimpleNamespace(extra={"catalog": hooks.read(catalog_data())})

    hooks.on_files(files_at("index.html", "tool/x.html"), settings)

    assert caplog.messages == []


def test_the_404_page_gets_the_name_and_the_website_of_every_project() -> None:
    catalog = hooks.load(ROOT)

    directory = catalog.directory()

    assert [item["slug"] for item in directory] == [p.slug for p in catalog.projects]
    assert directory[0] == {
        "slug": "homedarts-for-autodarts",
        "former": ["ha-autodarts"],
        "name": {
            "en": "HomeDarts for Autodarts",
            "de": "HomeDarts for Autodarts",
        },
        "url": {
            "en": "https://dennis-otto.github.io/homedarts-for-autodarts/",
            "de": "https://dennis-otto.github.io/homedarts-for-autodarts/de/",
        },
    }
    assert [item["former"] for item in directory[1:]] == [[]] * 6
    # The dashboard has no documentation; its button leads to it.
    assert directory[-1]["url"] == dict.fromkeys(
        ("en", "de"), "https://dennis-otto.github.io/repo-blueprint/dashboard/"
    )
    for item in directory:
        assert all(url.startswith("https://") for url in item["url"].values())
    # The template gives it to the script as JSON.
    assert json.loads(json.dumps(directory)) == directory


def page_at(dest_uri: str, **meta: str) -> SimpleNamespace:
    """A page of MkDocs that is written to dest_uri in the folder of the website,
    with the keys of its front matter, and the canonical address that MkDocs gives
    it."""
    return SimpleNamespace(
        file=SimpleNamespace(dest_uri=dest_uri),
        meta=meta,
        canonical_url=f"{SITE}{dest_uri}",
    )


def test_the_home_page_names_the_website_its_owner_and_the_projects() -> None:
    output = hooks.on_post_page(HTML, page_at("index.html"), build())

    assert output.count('<link rel="me" href="https://github.com/Dennis-Otto">') == 1
    assert output.index("</title>") < output.index("ld+json") < output.index("</head>")
    blocks = LD_JSON.findall(output)
    assert len(blocks) == 1
    data = json.loads(blocks[0])
    assert data["@context"] == "https://schema.org"
    website, person, projects = data["@graph"]
    assert website == {
        "@type": "WebSite",
        "@id": f"{SITE}#website",
        "url": SITE,
        "name": "Dennis Otto",
        "inLanguage": ["en", "de"],
        "publisher": {"@id": f"{SITE}#owner"},
    }
    assert person == {
        "@type": "Person",
        "@id": f"{SITE}#owner",
        "name": "Dennis Otto",
        "url": SITE,
        "sameAs": [
            "https://github.com/Dennis-Otto",
            "https://github.com/sponsors/Dennis-Otto",
        ],
    }
    assert projects["@type"] == "ItemList"
    assert projects["numberOfItems"] == 6
    elements = projects["itemListElement"]
    assert [element["position"] for element in elements] == [1, 2, 3, 4, 5, 6]
    items = [element["item"] for element in elements]
    assert {item["@type"] for item in items} == {"SoftwareSourceCode"}
    assert [item["@id"] for item in items] == [
        f"{SITE}#homedarts-for-autodarts",
        f"{SITE}#player-switch-for-autodarts",
        f"{SITE}#paperless-sync",
        f"{SITE}#paperless-unified-search",
        f"{SITE}#issue-assistant",
        f"{SITE}#repo-blueprint",
    ]
    assert items[2] == {
        "@type": "SoftwareSourceCode",
        "@id": f"{SITE}#paperless-sync",
        "name": "Paperless Sync",
        "description": hooks.load(ROOT).projects[2].summary["en"],
        "url": f"{SITE}paperless-sync/",
        "codeRepository": "https://github.com/Dennis-Otto/paperless-sync",
        "license": "https://spdx.org/licenses/AGPL-3.0-or-later.html",
        "runtimePlatform": "Nextcloud",
        "isAccessibleForFree": True,
        "maintainer": {"@id": f"{SITE}#owner"},
    }


def test_no_text_of_the_catalog_ends_the_script_of_the_structured_data() -> None:
    summary = {"en": "Ends </script><!-- here", "de": "Endet hier"}
    catalog = hooks.read(catalog_data(entry(summary=summary)))

    head = hooks.structured_data(catalog, SITE, "Site")

    assert head.count("<") == 3
    block = LD_JSON.search(head)
    assert block is not None
    item = json.loads(block.group(1))["@graph"][2]["itemListElement"][0]["item"]
    assert item["description"] == "Ends </script><!-- here"


@pytest.mark.parametrize(
    "dest_uri",
    ["security.html", "decisions/README.html", "de/security.html", "en/index.html"],
)
def test_no_other_page_gets_the_structured_data(dest_uri: str) -> None:
    page = page_at(dest_uri, title="Open-Source-Apps")

    assert hooks.on_post_page(HTML, page, build()) == HTML


def test_the_german_home_page_gets_no_structured_data_and_no_feed() -> None:
    # Material asks the folder of every alternate link in the head for its
    # sitemap.xml, which the dashboard doesn't publish, so no home page names its feed.
    page = page_at("de/index.html", title="Open-Source-Apps")

    assert hooks.on_post_page(HTML, page, build()) == HTML


def test_the_home_page_names_no_feed_in_its_head() -> None:
    output = hooks.on_post_page(HTML, page_at("index.html"), build())

    assert 'rel="alternate"' not in output
    assert hooks.ATOM not in output


def test_the_preview_card_of_the_home_page_has_the_title_of_the_page() -> None:
    # As the German home page has it, and as the title of the browser tab reads.
    output = hooks.on_post_page(HTML, page_at("index.html", title=TITLE), build())

    for tag in ("og:title", "twitter:title"):
        assert f'<meta property="{tag}" content="{TITLE} - Dennis Otto">' in output
    assert "<title>Dennis Otto</title>" in output


def test_the_title_of_the_preview_card_is_escaped() -> None:
    page = page_at("index.html", title='Apps "for" A & B')

    output = hooks.on_post_page(HTML, page, build())

    assert 'content="Apps &quot;for&quot; A &amp; B - Dennis Otto"' in output


def test_a_home_page_without_a_title_keeps_its_preview_card() -> None:
    output = hooks.on_post_page(HTML, page_at("index.html"), build())

    assert output.count('content="Dennis Otto"') == 2


def test_the_home_page_has_the_root_of_the_address_as_its_canonical_address() -> None:
    # Search engines take the name of the website from the home page at the root of
    # an address, which the url of the WebSite of the structured data names.
    home = page_at("index.html")

    assert hooks.on_pre_page(home, build(), None) is home

    assert home.canonical_url == SITE
    head = hooks.structured_data(hooks.load(ROOT), SITE, "Dennis Otto")
    block = LD_JSON.search(head)
    assert block is not None
    assert json.loads(block.group(1))["@graph"][0]["url"] == home.canonical_url


@pytest.mark.parametrize(
    "dest_uri", ["de/index.html", "security.html", "decisions/index.html"]
)
def test_every_other_page_keeps_its_canonical_address(dest_uri: str) -> None:
    page = page_at(dest_uri)

    hooks.on_pre_page(page, build(), None)

    assert page.canonical_url == f"{SITE}{dest_uri}"


class Extra(dict[str, Any]):
    """extra of the configuration of MkDocs, which the i18n plugin gives the links
    between the languages of a page as an attribute, alternate."""

    alternate: list[dict[str, str]]


def alternates(english: str, german: str) -> list[dict[str, str]]:
    """The links of the language switch as the i18n plugin sets them for a page:
    relative to the root of the website."""
    return [
        {"name": "English", "link": english, "lang": "en"},
        {"name": "Deutsch", "link": german, "lang": "de"},
    ]


@pytest.mark.parametrize("dest_uri", ["index.html", "de/index.html"])
def test_the_languages_of_the_home_page_lead_to_the_root_of_the_address(
    dest_uri: str,
) -> None:
    extra = Extra(alternate=alternates("/index.html", "/de/index.html"))
    extra.alternate = alternates("index.html", "de/index.html")
    settings = SimpleNamespace(extra=extra)
    context: dict[str, Any] = {}

    assert hooks.on_page_context(context, page_at(dest_uri), settings, None) is context

    # The templates write ./ relative to the page: ../ on the German home page.
    assert extra.alternate == alternates("./", "de/index.html")
    # The item stays, which the templates read on the 404 page alone.
    assert extra["alternate"] == alternates("/index.html", "/de/index.html")


def test_the_languages_of_every_other_page_stay() -> None:
    extra = Extra()
    extra.alternate = alternates("decisions/index.html", "de/decisions/index.html")
    settings = SimpleNamespace(extra=extra)

    hooks.on_page_context({}, page_at("decisions/index.html"), settings, None)

    assert extra.alternate == alternates(
        "decisions/index.html", "de/decisions/index.html"
    )


def test_a_website_in_one_language_has_no_language_switch() -> None:
    settings = SimpleNamespace(extra={})

    assert hooks.on_page_context({}, page_at("index.html"), settings, None) == {}
    assert settings.extra == {}


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


def test_the_sitemaps_lead_to_the_root_for_the_english_home_page(
    tmp_path: Path,
) -> None:
    built = sitemap(
        f"{SITE}index.html",
        f"{SITE}decisions/index.html",
        f"{SITE}de/index.html",
        f"{SITE}de/decisions/index.html",
    )
    wanted = built.replace(f">{SITE}index.html<", f">{SITE}<").replace(
        f'"{SITE}index.html"', f'"{SITE}"'
    )
    assert f"{SITE}index.html" not in wanted
    assert wanted.count(f'"{SITE}"') == 2
    # The sitemap at the root, its copy in the folder of the German pages, and the
    # packed one, as MkDocs and .github/mkdocs_blueprint.py write them.
    (tmp_path / "de").mkdir()
    for folder in (tmp_path, tmp_path / "de"):
        (folder / "sitemap.xml").write_text(built, encoding="utf-8", newline="\n")
    packed = tmp_path / "sitemap.xml.gz"
    with gzip.GzipFile(packed, "wb", mtime=BUILT) as writer:
        writer.write(built.encode())

    hooks.sitemaps_at_root(tmp_path, SITE)

    for folder in (tmp_path, tmp_path / "de"):
        assert (folder / "sitemap.xml").read_bytes() == wanted.encode()
    with gzip.GzipFile(packed) as reader:
        assert reader.read() == wanted.encode()
        assert reader.mtime == BUILT


def test_a_website_without_a_packed_sitemap_needs_none(tmp_path: Path) -> None:
    built = sitemap(f"{SITE}de/index.html")
    (tmp_path / "sitemap.xml").write_text(built, encoding="utf-8", newline="\n")

    hooks.sitemaps_at_root(tmp_path, SITE)

    assert not (tmp_path / "sitemap.xml.gz").exists()
    assert (tmp_path / "sitemap.xml").read_text(encoding="utf-8") == built.replace(
        f'"{SITE}index.html"', f'"{SITE}"'
    )


# The search of every project.

# The search index of a project website in English and German, as the search plugin
# of Material and the i18n plugin write it, with a page of each kind of entry and of
# each rank: an installation, a changelog and a decision record.
FIXTURE = ROOT / "tests/fixtures/search_index.json"


def project_website(slug: str = "tool", **changes: Any) -> Any:
    """The website of the project of entry() in the folder slug/ of the address."""
    catalog = hooks.read(catalog_data(entry(slug, **changes)))
    return hooks.Website(catalog.projects[0], f"{slug}/")


def index_of(*docs: dict[str, Any]) -> bytes:
    """A search index with docs, as the search plugin writes it."""
    return json.dumps({"config": {"lang": ["en"]}, "docs": list(docs)}).encode()


def section(location: str, title: str = "A section", text: str = "") -> dict[str, str]:
    """An entry of a search index: a page, or a section of one with a #."""
    return {"location": location, "title": title, "text": text}


@pytest.mark.parametrize(
    ("html", "text"),
    [
        ("", ""),
        ("<p>  </p>", ""),
        ("<p>Darts &amp; <code>points</code>.</p>", "<p>Darts &amp; points.</p>"),
        # Blocks end a word, the tags within a line don't.
        (
            "<p>One</p><p>two</p><ul><li>three</li><li>four</li></ul>",
            "<p>One two three four</p>",
        ),
        ("<p>A <strong>bold</strong>er<br>line</p>", "<p>A bolder line</p>"),
        # Blocks of code, such as the source of a diagram, are left out.
        (
            '<p>Before</p><pre class="mermaid"><code>flowchart TB\n  a --> b</code></pre>'
            "<p>after</p>",
            "<p>Before after</p>",
        ),
        ("<pre><pre>nested</pre> still code</pre><p>text</p>", "<p>text</p>"),
        ("</pre><p>A stray end</p>", "<p>A stray end</p>"),
        # What the search would take for HTML is escaped.
        ("<p>1 &lt; 2 &gt; 0 &quot;a&quot;</p>", '<p>1 &lt; 2 &gt; 0 "a"</p>'),
        ("Text without tags", "<p>Text without tags</p>"),
    ],
)
def test_an_excerpt_is_the_plain_text_of_a_section(html: str, text: str) -> None:
    assert hooks.excerpt(html) == text


def test_a_long_text_is_cut_after_a_whole_word() -> None:
    words = " ".join(f"word{number}" for number in range(100))

    text = hooks.excerpt(f"<p>{words}</p>").removeprefix("<p>").removesuffix("</p>")

    assert len(text) <= hooks.EXCERPT == 200
    assert text.endswith(" word29…")
    assert words.startswith(text.removesuffix("…") + " ")


@pytest.mark.parametrize(
    ("words", "excerpt"),
    [
        # A word that ends before the ellipsis stays whole.
        ("a" * 198 + " next", "a" * 198 + "…"),
        ("a" * 199 + " next", "a" * 199 + "…"),
        # A word longer than the excerpt is cut within.
        ("a" * 200 + " next", "a" * 199 + "…"),
        ("a" * 201, "a" * 199 + "…"),
        # The punctuation before the cut goes.
        ("a" * 150 + ", " + "b" * 60, "a" * 150 + "…"),
        ("a" * 199, "a" * 199),
        ("a" * 200, "a" * 200),
    ],
)
def test_the_excerpt_has_200_characters_at_most(words: str, excerpt: str) -> None:
    assert hooks.excerpt(words) == f"<p>{excerpt}</p>"


def test_the_search_finds_the_websites_in_folders_of_the_address() -> None:
    elsewhere = entry("elsewhere", docs="https://elsewhere.example.org/docs/")
    plain = entry("plain")
    del plain["docs"]
    page = entry("page", docs={"en": f"{SITE}page/guide.html", "de": f"{SITE}de/"})
    twice = entry("twice", docs=f"{SITE}tool/")
    root = entry("root", docs=SITE)
    catalog = hooks.read(catalog_data(entry(), elsewhere, plain, page, twice, root))

    found = hooks.websites(catalog, SITE)

    assert [(site.project.slug, site.folder) for site in found] == [
        ("tool", "tool/"),
        ("page", "page/"),
    ]


def test_the_search_of_the_address_has_every_project_website() -> None:
    found = hooks.websites(hooks.load(ROOT), SITE)

    assert [site.folder for site in found] == [
        "homedarts-for-autodarts/",
        "player-switch-for-autodarts/",
        "paperless-sync/",
        "paperless-unified-search/",
        "issue-assistant/",
        "repo-blueprint/",
    ]
    assert found[0].project.short == {"en": "HomeDarts", "de": "HomeDarts"}


def test_the_entries_of_a_website_go_into_its_folder_under_its_name() -> None:
    docs = hooks.documents(FIXTURE.read_bytes(), "tool/search/search_index.json")
    short = {"en": "Tool & Co", "de": "Werkzeug"}

    found = hooks.entries(hooks.read(catalog_data()), project_website(short=short), docs)

    assert [(rank.name, doc) for rank, doc in found] == [
        (
            "PAGE",
            {
                "location": "tool/index.html",
                "title": "Tool &amp; Co › Home",
                "text": "",
            },
        ),
        (
            "OTHER",
            {
                "location": "tool/index.html#the-tool",
                "title": "The tool",
                "text": (
                    "<p>It throws darts &amp; counts the points of every visit.</p>"
                ),
            },
        ),
        # A page with a text before its first heading keeps it.
        (
            "PAGE",
            {
                "location": "tool/games.html",
                "title": "Tool &amp; Co › Games",
                "text": "<p>Every game of the tool, before its first heading.</p>",
            },
        ),
        (
            "OTHER",
            {
                "location": "tool/games.html#cricket",
                "title": "Cricket &lt;3",
                "text": "<p>Close 15 to 20 and the bull. One mark Two marks</p>",
            },
        ),
        # A page that a reader looks for first ranks higher, and so do its sections.
        (
            "PAGE",
            {
                "location": "tool/installation.html",
                "title": "Tool &amp; Co › Installation",
                "text": "<p>Install it with HACS.</p>",
                "boost": 2,
            },
        ),
        (
            "START",
            {
                "location": "tool/installation.html#hacs",
                "title": "HACS",
                "text": "<p>Open HACS.</p>",
                "boost": 2,
            },
        ),
        # A page for maintainers ranks lower.
        (
            "PAGE",
            {
                "location": "tool/changelog.html",
                "title": "Tool &amp; Co › Changelog",
                "text": "",
                "boost": 0.5,
            },
        ),
        (
            "MAINTAINERS",
            {
                "location": "tool/changelog.html#100",
                "title": "1.0.0",
                "text": "<p>The first release.</p>",
                "boost": 0.5,
            },
        ),
        # A decision record keeps its page and none of its sections.
        (
            "PAGE",
            {
                "location": "tool/decisions/0001-one-search.html",
                "title": "Tool &amp; Co › 1. One search",
                "text": "",
                "boost": 0.5,
            },
        ),
        # A page in German has the German name. The page that the index lists
        # twice is there once, and tags and boosts stay on the project website.
        (
            "PAGE",
            {
                "location": "tool/de/index.html",
                "title": "Werkzeug › Startseite",
                "text": "",
            },
        ),
        (
            "OTHER",
            {
                "location": "tool/de/index.html#das-werkzeug",
                "title": "Das Werkzeug",
                "text": "<p>Es wirft Darts.</p>",
            },
        ),
        # The German page without an entry gets one from its first section.
        (
            "PAGE",
            {
                "location": "tool/de/games.html",
                "title": "Werkzeug › Cricket",
                "text": "",
            },
        ),
        (
            "OTHER",
            {
                "location": "tool/de/games.html#cricket",
                "title": "Cricket",
                "text": "<p>Schließe 15 bis 20 und das Bull.</p>",
            },
        ),
        (
            "OTHER",
            {
                "location": "tool/de/games.html#cut-throat",
                "title": "Cut-Throat",
                "text": "",
            },
        ),
        # The ranks and boosts are those of every language.
        (
            "PAGE",
            {
                "location": "tool/de/installation.html",
                "title": "Werkzeug › HACS",
                "text": "",
                "boost": 2,
            },
        ),
        (
            "START",
            {
                "location": "tool/de/installation.html#hacs",
                "title": "HACS",
                "text": "<p>Öffne HACS.</p>",
                "boost": 2,
            },
        ),
        # Also the decision record without an entry keeps its page alone.
        (
            "PAGE",
            {
                "location": "tool/de/decisions/0001-one-search.html",
                "title": "Werkzeug › Kontext",
                "text": "",
                "boost": 0.5,
            },
        ),
    ]


def test_a_page_has_the_name_of_its_project_without_a_short_one() -> None:
    docs = [section("index.html", "Home"), section("fr/index.html", "Accueil")]

    found = hooks.entries(hooks.read(catalog_data()), project_website(), docs)

    # The folder of a language that the catalog doesn't know is in the first one.
    titles = [doc["title"] for _, doc in found]
    assert titles == ["The tool › Home", "The tool › Accueil"]


def test_an_entry_without_a_text_is_one() -> None:
    docs = hooks.documents(b'{"docs": [{"location": "a.html", "title": "A"}]}', "x")

    assert hooks.entries(hooks.read(catalog_data()), project_website(), docs) == [
        hooks.Entry(
            hooks.Rank.PAGE,
            {"location": "tool/a.html", "title": "The tool › A", "text": ""},
        )
    ]


@pytest.mark.parametrize(
    ("page", "rank"),
    [
        ("index.html", "OTHER"),
        ("", "OTHER"),
        ("games.html", "OTHER"),
        ("kinds/container.html", "OTHER"),
        # The pages that a reader looks for first, in every language and with the
        # addresses of folders that use_directory_urls of MkDocs makes.
        ("installation.html", "START"),
        ("de/installation.html", "START"),
        ("getting-started/", "START"),
        ("de/troubleshooting/", "START"),
        ("faq.html", "START"),
        ("guide.html", "START"),
        ("install.html", "START"),
        # A page kept as the index of its folder is named after its folder.
        ("guide/index.html", "START"),
        ("de/installation/index.html", "START"),
        ("index.html", "OTHER"),
        ("branding/index.html", "OTHER"),
        # The pages for maintainers.
        ("changelog.html", "MAINTAINERS"),
        ("de/releases.html", "MAINTAINERS"),
        ("development.html", "MAINTAINERS"),
        ("automation/", "MAINTAINERS"),
        ("roadmap.html", "MAINTAINERS"),
        # A page named after the folder of the decision records is none, but every
        # page in that folder is, at any depth.
        ("decisions.html", "OTHER"),
        ("decisions/", None),
        ("decisions/index.html", None),
        ("decisions/0001-one-search.html", None),
        ("de/decisions/0001-one-search/", None),
        ("reference/decisions/faq.html", None),
    ],
)
def test_the_name_of_a_page_ranks_its_sections(page: str, rank: str | None) -> None:
    found = hooks.rank_of(page)

    assert (None if found is None else found.name) == rank


@pytest.mark.parametrize(
    ("location", "boost"),
    [
        ("installation.html#hacs", 2),
        ("de/faq.html", 2),
        ("changelog.html#100", 0.5),
        ("decisions/0001-one-search.html", 0.5),
        ("games.html#cricket", None),
        ("index.html", None),
        ("guide/index.html", 2),
        ("changelog/index.html#100", 0.5),
    ],
)
def test_the_name_of_a_page_boosts_its_entries(
    location: str, boost: float | None
) -> None:
    assert hooks.boost_of(location) == boost


@pytest.mark.parametrize(
    ("content", "problem"),
    [
        (b"<html>Not Found</html>", "is no JSON: Expecting value: line 1 column 1"),
        (b"\xff\xfe\xfa", "is no JSON:"),
        (b"[]", "is no search index of Material for MkDocs: it needs docs"),
        (b'{"config": {}}', "is no search index"),
        (b'{"docs": {}}', "is no search index"),
        (b'{"docs": ["index.html"]}', "is no search index"),
        (b'{"docs": [{"location": "index.html"}]}', "is no search index"),
        (b'{"docs": [{"title": "Home", "text": ""}]}', "is no search index"),
        (
            b'{"docs": [{"location": "index.html", "title": "Home", "text": 1}]}',
            "is no search index",
        ),
    ],
)
def test_a_broken_search_index_is_named(content: bytes, problem: str) -> None:
    url = f"{SITE}tool/search/search_index.json"

    with pytest.raises(hooks.SearchError) as error:
        hooks.documents(content, url)

    assert str(error.value).startswith(f"{url} {problem}")


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


def not_found() -> Any:
    """The error of urllib for an index that a website doesn't have."""
    return hooks.urllib.error.HTTPError(
        f"{SITE}tool/search/search_index.json",
        404,
        "Not Found",
        email.message.Message(),
        io.BytesIO(b"Not Found"),
    )


def test_an_index_is_downloaded_with_a_time_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    urlopen = Download(b"{}")
    monkeypatch.setattr(hooks.urllib.request, "urlopen", urlopen)

    assert hooks.download(f"{SITE}tool/search/search_index.json") == b"{}"
    assert urlopen.requests == [(f"{SITE}tool/search/search_index.json", 10)]


@pytest.mark.parametrize(
    "error",
    [
        hooks.urllib.error.URLError("timed out"),
        http.client.RemoteDisconnected("closed"),
        ValueError("unknown url type"),
    ],
)
def test_a_failed_download_is_tried_again(
    monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    urlopen = Download(error, b"{}")
    monkeypatch.setattr(hooks.urllib.request, "urlopen", urlopen)

    assert hooks.download(f"{SITE}tool/search/search_index.json") == b"{}"
    assert len(urlopen.requests) == hooks.TRIES == 2


def test_a_download_gives_up_after_its_tries(monkeypatch: pytest.MonkeyPatch) -> None:
    errors = [not_found(), not_found()]
    monkeypatch.setattr(hooks.urllib.request, "urlopen", Download(*errors))

    with pytest.raises(hooks.SearchError) as error:
        hooks.download(f"{SITE}tool/search/search_index.json")

    assert str(error.value) == (
        f"{SITE}tool/search/search_index.json can't be downloaded: "
        "HTTP Error 404: Not Found"
    )
    # The answers of the errors are closed, as an answer without an error is.
    assert all(answer.fp.closed for answer in errors)


def doc(number: int, size: int = 0, location: str = "") -> dict[str, str]:
    """An entry of a search index at location, or page<number>.html, whose text has
    size pieces that gzip can't pack much, different in every entry."""
    text = "".join(f"{(number * 7919 + index) ** 3 % 1000003:x}" for index in range(size))
    location = location or f"page{number}.html"
    return {"location": location, "title": f"Page {number}", "text": text}


def pages(*docs: dict[str, str]) -> list[Any]:
    """The entries of the pages docs of a project website."""
    return [hooks.Entry(hooks.Rank.PAGE, page) for page in docs]


def ranked(website: list[Any]) -> list[Any]:
    """The entries of website, each with the rank of its location, as
    entries() ranks them."""
    return [
        hooks.Entry(
            hooks.Rank.PAGE
            if "#" not in page["location"]
            else hooks.rank_of(page["location"].partition("#")[0]),
            page,
        )
        for page in website
    ]


def flat(kept: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """The entries that within() keeps of every website, one after another."""
    return [page for website in kept for page in website]


def test_the_entries_within_the_budget_are_all_kept() -> None:
    found = [pages(doc(1), doc(2)), [], pages(doc(3))]

    assert hooks.within(found, 1000) == [[doc(1), doc(2)], [], [doc(3)]]
    assert hooks.within([], 0) == []


def test_the_largest_website_gives_up_its_last_pages_first() -> None:
    large = [doc(number, 40) for number in range(10)]
    small = [doc(number, 40) for number in range(10, 13)]
    budget = hooks.packed(large[:5] + small)

    kept = hooks.within([pages(*large), pages(*small)], budget)

    assert kept == [large[:5], small]
    assert hooks.packed(flat(kept)) <= budget < hooks.packed(large[:6] + small)


def test_every_website_gives_up_its_pages_beyond_the_same_number() -> None:
    large = [doc(number, 40) for number in range(10)]
    small = [doc(number, 40) for number in range(10, 13)]
    budget = hooks.packed(large[:2] + small[:2])

    assert hooks.within([pages(*large), pages(*small)], budget) == [
        large[:2],
        small[:2],
    ]
    assert hooks.within([pages(*large), pages(*small)], 10) == [[], []]


def test_a_decision_record_gives_up_its_page_before_the_pages_for_readers() -> None:
    first = doc(1, 40, "index.html")
    record = doc(2, 40, "decisions/0001-one-search.html")
    installation = doc(3, 40, "installation.html")
    german = doc(4, 40, "de/installation.html")
    other = doc(5, 40, "games.html")
    website = [first, record, installation, german]
    budget = hooks.packed([first, installation, german, other])

    kept = hooks.within([pages(*website), pages(other)], budget)

    assert kept == [[first, installation, german], [other]]
    assert hooks.within([pages(*website), pages(other)], 10**6) == [
        website,
        [other],
    ]


def test_the_budget_gives_up_the_sections_of_the_lowest_rank_first() -> None:
    website = [
        doc(1, 30, "index.html"),
        doc(2, 30, "index.html#about"),
        doc(3, 30, "installation.html"),
        doc(4, 30, "installation.html#hacs"),
        doc(5, 30, "changelog.html"),
        doc(6, 30, "changelog.html#200"),
        doc(7, 30, "changelog.html#100"),
        doc(8, 30, "games.html"),
        doc(9, 30, "games.html#cricket"),
    ]
    found = [ranked(website)]
    index, about, installation, hacs, changelog, _, _, games, cricket = website
    page_entries = [index, installation, changelog, games]

    def kept(*docs: dict[str, str]) -> list[dict[str, str]]:
        return hooks.within(found, hooks.packed(list(docs)))[0]

    # Every section after its page, in the order of the index: first the changelog
    # loses its sections, then the other pages, then the installation, and the
    # pages go last, the last page first.
    assert kept(*website) == website
    without_changelog = [index, about, installation, hacs, changelog, games, cricket]
    assert kept(*without_changelog) == without_changelog
    assert kept(index, installation, hacs, changelog, games) == [
        index,
        installation,
        hacs,
        changelog,
        games,
    ]
    assert kept(*page_entries) == page_entries
    assert kept(index, installation) == [index, installation]


def test_the_page_with_the_most_sections_gives_up_its_last_ones_first() -> None:
    long = [doc(0, 30, "games.html")] + [
        doc(number, 30, f"games.html#game-{number}") for number in range(1, 7)
    ]
    short = [doc(7, 30, "cards.html")] + [
        doc(number, 30, f"cards.html#card-{number}") for number in range(8, 10)
    ]
    other = [doc(10, 30, "index.html"), doc(11, 30, "index.html#about")]
    found = [ranked(long + short), ranked(other)]

    budget = hooks.packed(long[:3] + short[:3] + other)
    assert hooks.within(found, budget) == [long[:3] + short[:3], other]
    budget = hooks.packed(long[:4] + short + other)
    assert hooks.within(found, budget) == [long[:4] + short, other]
    budget = hooks.packed(long[:2] + short[:2] + other)
    assert hooks.within(found, budget) == [long[:2] + short[:2], other]


def search_index(site: Path, *docs: dict[str, Any]) -> Path:
    """The search index of the website in site, with docs."""
    path = site / "search/search_index.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    index = {"config": {"lang": ["en", "de"]}, "docs": list(docs)}
    path.write_text(json.dumps(index), encoding="utf-8")
    return path


def test_the_search_of_the_address_adds_every_project_website(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, "mkdocs.hooks.project")
    asked: list[str] = []

    def download(url: str) -> bytes:
        asked.append(url)
        if "paperless-sync" in url:
            raise hooks.SearchError(f"{url} can't be downloaded: timed out")
        if "issue-assistant" in url:
            return b"<html></html>"
        return index_of(section("index.html", "Home"), section("index.html#a", "A"))

    monkeypatch.setattr(hooks, "download", download)

    folders, docs = hooks.project_search(hooks.load(ROOT), SITE)

    assert folders == [
        "homedarts-for-autodarts/",
        "player-switch-for-autodarts/",
        "paperless-sync/",
        "paperless-unified-search/",
        "issue-assistant/",
        "repo-blueprint/",
    ]
    assert sorted(asked) == sorted(
        f"{SITE}{folder}search/search_index.json" for folder in folders
    )
    assert [(entry["location"], entry["title"]) for entry in docs] == [
        ("homedarts-for-autodarts/index.html", "HomeDarts › Home"),
        ("homedarts-for-autodarts/index.html#a", "A"),
        ("player-switch-for-autodarts/index.html", "Player Switch › Home"),
        ("player-switch-for-autodarts/index.html#a", "A"),
        ("paperless-unified-search/index.html", "Paperless Unified Search › Home"),
        ("paperless-unified-search/index.html#a", "A"),
        ("repo-blueprint/index.html", "Repo Blueprint › Home"),
        ("repo-blueprint/index.html#a", "A"),
    ]
    # Not a warning, which would fail the strict build.
    assert sorted((record.levelno, record.message) for record in caplog.records) == [
        (logging.INFO, "The search adds 8 entries of 4 of the 6 project websites."),
        *(
            (
                logging.INFO,
                "The search keeps 1 of the 1 pages and 1 of the 1 sections of the "
                f"website of {slug}.",
            )
            for slug in (
                "homedarts-for-autodarts",
                "paperless-unified-search",
                "player-switch-for-autodarts",
                "repo-blueprint",
            )
        ),
        (
            logging.INFO,
            "The search leaves out the website of issue-assistant until the next "
            f"build: {SITE}issue-assistant/search/search_index.json is no JSON: "
            "Expecting value: line 1 column 1 (char 0)",
        ),
        (
            logging.INFO,
            "The search leaves out the website of paperless-sync until the next "
            f"build: {SITE}paperless-sync/search/search_index.json can't be "
            "downloaded: timed out",
        ),
    ]


def test_the_search_says_when_it_keeps_part_of_the_websites(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, "mkdocs.hooks.project")
    website = [doc(number, 40) for number in range(10)]
    monkeypatch.setattr(hooks, "download", lambda url: index_of(*website))
    monkeypatch.setattr(hooks, "BUDGET", 1000)

    folders, docs = hooks.project_search(hooks.read(catalog_data()), SITE)

    assert folders == ["tool/"]
    assert 0 < len(docs) < len(website)
    assert hooks.packed(docs) <= 1000
    assert caplog.messages == [
        f"The search keeps {len(docs)} of the 10 pages and 0 of the 0 sections of "
        "the website of tool.",
        f"The search keeps {len(docs)} of the 10 entries of the project websites, "
        "1000 bytes packed with gzip at most.",
        f"The search adds {len(docs)} entries of 1 of the 1 project websites.",
    ]


def large_website() -> list[dict[str, str]]:
    """The search index of a large project website in English and German, as long
    as the website of HomeDarts: pages of every rank, each with sections, and many
    decision records whose sections would fill the budget alone."""
    docs: list[dict[str, str]] = []
    number = 0

    def page(location: str, sections: int) -> None:
        nonlocal number
        for part in range(sections + 1):
            number += 1
            anchor = f"#part-{part}" if part else ""
            docs.append(doc(number, 12, f"{location}{anchor}"))

    for language in ("", "de/"):
        page(f"{language}automations.html", 30)
        page(f"{language}changelog.html", 60)
        for record in range(40):
            page(f"{language}decisions/{record:04}-a-decision.html", 8)
        page(f"{language}development.html", 30)
        page(f"{language}games.html", 20)
        page(f"{language}getting-started.html", 6)
        page(f"{language}index.html", 4)
        page(f"{language}installation.html", 8)
        page(f"{language}troubleshooting.html", 10)
    return docs


def test_a_large_website_keeps_every_page_and_those_a_reader_looks_for(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, "mkdocs.hooks.project")
    large = large_website()
    small = [doc(9000, 12, "index.html"), doc(9001, 12, "index.html#about")]
    catalog = hooks.read(catalog_data(entry("large"), entry("small")))
    # What the budget has room for: the entry of every page of both websites in
    # every language, and the sections of the pages that a reader looks for first.
    wanted = [
        doc
        for project, docs in zip(catalog.projects, (large, small), strict=True)
        for rank, doc in hooks.entries(
            catalog, hooks.Website(project, f"{project.slug}/"), docs
        )
        if rank in (hooks.Rank.PAGE, hooks.Rank.START)
    ]
    budget = hooks.packed(wanted)

    def download(url: str) -> bytes:
        return index_of(*(large if "/large/" in url else small))

    monkeypatch.setattr(hooks, "download", download)
    monkeypatch.setattr(hooks, "BUDGET", budget)

    folders, docs = hooks.project_search(catalog, SITE)

    assert folders == ["large/", "small/"]
    # In the order of the index, every section after its page; no section of a
    # decision record, and none of a page for maintainers or of any other page
    # while the budget has no room for them all.
    assert [doc["location"] for doc in docs] == [doc["location"] for doc in wanted]
    assert hooks.packed(docs) <= budget
    locations = {doc["location"] for doc in docs}
    for language in ("", "de/"):
        assert f"large/{language}installation.html#part-8" in locations
        assert f"large/{language}getting-started.html#part-6" in locations
        assert f"large/{language}decisions/0039-a-decision.html" in locations
    assert not any("#" in place and "/decisions/" in place for place in locations)
    assert caplog.messages[:2] == [
        "The search keeps 96 of the 96 pages and 48 of the 336 sections of the "
        "website of large.",
        "The search keeps 1 of the 1 pages and 0 of the 1 sections of the website "
        "of small.",
    ]


def test_a_catalog_without_project_websites_adds_nothing() -> None:
    plain = entry()
    del plain["docs"]

    assert hooks.project_search(hooks.read(catalog_data(plain)), SITE) == ([], [])


def test_the_entries_of_the_projects_follow_those_of_the_website(
    tmp_path: Path,
) -> None:
    own = [section("index.html", "Home"), section("de/index.html", "Startseite")]
    path = search_index(tmp_path, *own, section("tool/old.html", "Old"))
    docs = [section("tool/index.html", "The tool › Home")]

    hooks.add_to_search(tmp_path, ["tool/", "other/"], docs)

    # In place of those of an earlier build, as compact as the search plugin writes.
    text = path.read_text(encoding="utf-8")
    assert json.loads(text) == {"config": {"lang": ["en", "de"]}, "docs": own + docs}
    assert text == json.dumps(json.loads(text), separators=(",", ":"))


def test_the_decision_records_of_the_website_rank_low_as_those_of_the_projects(
    tmp_path: Path,
) -> None:
    record = "decisions/0002-the-root-website-owns-the-address.html"
    path = search_index(
        tmp_path,
        section("index.html", "Home"),
        section(record, "2. The root website owns the address"),
        section(f"de/{record}#context", "Context"),
        # A boost of its own, from the front matter of the page, stays.
        {**section("decisions/index.html", "Decisions"), "boost": 3},
    )

    hooks.add_to_search(tmp_path, ["tool/"], [])

    docs = json.loads(path.read_text(encoding="utf-8"))["docs"]
    assert [(doc["location"], doc.get("boost")) for doc in docs] == [
        ("index.html", None),
        (record, 0.5),
        (f"de/{record}#context", 0.5),
        ("decisions/index.html", 3),
    ]


def test_on_post_build_adds_the_project_websites_to_the_search_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    own = section("index.html", "Home")
    path = search_index(tmp_path, own)
    asked: list[str] = []

    def download(url: str) -> bytes:
        asked.append(url)
        return index_of(section("index.html", "Home"))

    monkeypatch.setattr(hooks, "download", download)
    settings = build(tmp_path)

    hooks.on_post_build(settings)
    # The build of the German website, after which the i18n plugin writes the index
    # of both languages, and the hook adds the projects again without a download.
    search_index(tmp_path, own, section("de/index.html", "Startseite"))
    hooks.on_post_build(settings)

    docs = json.loads(path.read_text(encoding="utf-8"))["docs"]
    assert [doc["location"] for doc in docs] == [
        "index.html",
        "de/index.html",
        "homedarts-for-autodarts/index.html",
        "player-switch-for-autodarts/index.html",
        "paperless-sync/index.html",
        "paperless-unified-search/index.html",
        "issue-assistant/index.html",
        "repo-blueprint/index.html",
    ]
    assert len(asked) == 6


def test_on_post_build_downloads_nothing_without_the_search(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    asked: list[str] = []
    monkeypatch.setattr(hooks, "download", asked.append)
    settings = build(tmp_path)

    hooks.on_post_build(settings)

    assert asked == []
    assert hooks.SEARCH not in settings.extra
    assert not (tmp_path / "search").exists()


def test_on_post_build_runs_after_the_i18n_plugin() -> None:
    # The i18n plugin writes the search index of every language with -100.
    assert hooks.on_post_build.mkdocs_priority < -100


def i18n_post_build(priority: int | None) -> Any:
    """The on_post_build of the i18n plugin, with the priority that the decorator
    event_priority of MkDocs gives it, or none: the hook reads that alone."""
    if priority is None:
        return SimpleNamespace()
    return SimpleNamespace(mkdocs_priority=priority)


@pytest.mark.parametrize("priority", [-100, -109, None])
def test_on_config_lets_the_i18n_plugin_write_the_search_index_first(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, priority: int | None
) -> None:
    website(tmp_path)
    settings = config(tmp_path, language("en"), GERMAN, nav=NAV)
    settings.plugins["i18n"].on_post_build = i18n_post_build(priority)

    hooks.on_config(settings)

    assert caplog.messages == []


@pytest.mark.parametrize("priority", [-110, -200])
def test_on_config_stops_the_build_when_the_i18n_plugin_comes_after_it(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, priority: int
) -> None:
    # A version of the plugin that lowers its priority would write the index of
    # every language anew after the hook, without the project websites.
    website(tmp_path)
    settings = config(tmp_path, language("en"), GERMAN, nav=NAV)
    settings.plugins["i18n"].on_post_build = i18n_post_build(priority)

    hooks.on_config(settings)

    assert caplog.messages == [
        f"The i18n plugin writes the search index with the priority {priority}, "
        "after the -110 of on_post_build of .github/mkdocs_project.py, so the "
        "search would lose the pages of the project websites: set "
        f"on_post_build.mkdocs_priority there below {priority}."
    ]
    assert [record.levelno for record in caplog.records] == [logging.WARNING]


def test_every_page_loads_the_search_index_after_the_page() -> None:
    # The index with every project website is the largest file of a page, so
    # overrides/main.html holds its request back until the reader goes to the
    # search box, or until a second after the page has loaded, when the browser is
    # idle. The script has to run before Material's, which asks for the index. It is
    # overrides/partials/search-hold.js, inline; tests/search-hold.test.mjs runs it.
    template = (ROOT / "overrides" / "main.html").read_text(encoding="utf-8")
    markup = template.split("-#}", 1)[1]
    include = '{% include "partials/search-hold.js" %}'

    assert '{% extends "base.html" %}' in markup
    assert markup.index(include) < markup.index("</script>") < markup.index("{{ super() }}")
    assert (ROOT / "overrides" / "partials" / "search-hold.js").is_file()
    # The pages of the website all take it, the home page and the 404 page too, the
    # home page and the Trust page through the template of the pages with live facts.
    for name in ("facts.html", "404.html"):
        page = (ROOT / "overrides" / name).read_text(encoding="utf-8")
        assert '{% extends "main.html" %}' in page
    home = (ROOT / "overrides" / "home.html").read_text(encoding="utf-8")
    assert '{% extends "facts.html" %}' in home


# The check of the built website, which reads the files that MkDocs and the hooks
# wrote. Its folder here holds what the hooks write, with pages as MkDocs builds them.

# The moment of the check: the day after the build of EPOCH, 2026-10-13.
CHECKED = datetime(2026, 10, 14, 12, tzinfo=UTC)
BUILT_ON = date(2026, 10, 13)
# The pages of this website in its sitemap, and so in its search index.
OWN_PAGES = (
    "index.html",
    "about.html",
    "releases.html",
    "decisions/0001-record-decisions.html",
    "de/index.html",
    "de/about.html",
)
POLICY_MESSAGE = (
    f"names Policy: {SITE}security.html, which is no page of the website: keep "
    "docs/security.md, or change POLICY of .github/mkdocs_project.py"
)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def home_page(catalog: Any, language: str) -> str:
    """A home page in language as MkDocs builds it from the cards of the hooks: the
    logo, a card for every project with a group with its picture in language,
    relative to the page, and its anchors, and in the default language the
    structured data."""
    up = "" if language == catalog.default else "../"
    cards = []
    for group in catalog.groups:
        for project in catalog.members(group):
            anchors = "".join(
                f'<span id="{folder}"></span>' for folder in project.former
            )
            cards.append(
                '<div class="card">'
                f'<p><img alt="" src="{up}{project.picture.src[language]}"'
                ' width="640"></p>'
                f'<h3 id="{project.slug}">{anchors}{escape(project.name[language])}'
                "</h3></div>"
            )
    head = (
        hooks.structured_data(catalog, SITE, "Dennis Otto")
        if language == catalog.default
        else ""
    )
    return (
        f'<!doctype html><html lang="{language}"><head><meta charset="utf-8">'
        f'{head}</head><body><img src="{up}assets/logo.svg" alt="">'
        f'<div class="grid cards">{"".join(cards)}</div></body></html>'
    )


def not_found_data(moves: dict[str, str] | None = None) -> str:
    """The data of the script of the 404 page as JSON: the old folders of moves, or
    none without it, and no project."""
    return json.dumps({"projects": []} | ({} if moves is None else {"moves": moves}))


def not_found_page(data: str) -> str:
    """The 404 page with the data of its script, whose JSON is data, and its script."""
    return (
        '<!doctype html><html lang="en"><body><p>Nothing here.</p>'
        '<script id="__config" type="application/json">{"base": "."}</script>'
        f'<script type="application/json" id="not-found-data">{data}</script>'
        "<script>(() => {})();</script>"
        '<script src="assets/javascripts/bundle.js"></script></body></html>'
    )


def hub_site(site: Path, today: date = BUILT_ON) -> Path:
    """The folder site with the website of this repository as the hooks build it on
    today: every file that they write or change after the build, the pages that it
    reads, and a search index with the pages of this website and of every project."""
    catalog = hooks.load(ROOT)
    for name in hooks.SECURITY_TXT:
        write(site / name, hooks.security_txt(catalog, SITE, today))
    write(site / "security.html", "<!doctype html><title>Security</title>")
    write(site / "robots.txt", hooks.robots(catalog, SITE))
    for name, text in hooks.moved_pages(catalog).items():
        write(site / name, text)
    write(site / "404.html", not_found_page(not_found_data(catalog.moves())))
    for language in catalog.languages:
        name = "index.html" if language == "en" else f"{language}/index.html"
        write(site / name, home_page(catalog, language))
    for project in catalog.projects:
        if project.picture is not None:
            for src in project.picture.src.values():
                write(site / src, "RIFF")
    # As the i18n plugin writes them, before the hooks lead them to the root.
    urls = sitemap(*(f"{SITE}{page}" for page in OWN_PAGES))
    for name in ("sitemap.xml", "de/sitemap.xml"):
        write(site / name, urls)
    with gzip.GzipFile(site / "sitemap.xml.gz", "wb", mtime=BUILT) as packed:
        packed.write(urls.encode("utf-8"))
    hooks.sitemaps_at_root(site, SITE)
    own = []
    for page in OWN_PAGES:
        boost = hooks.boost_of(page)
        for location in (page, f"{page}#a-section"):
            doc = {"location": location, "title": "A page", "text": "<p>Text</p>"}
            own.append(doc if boost is None else doc | {"boost": boost})
    projects = [
        {"location": f"{folder}index.html", "title": "Tool › Home", "text": ""}
        for folder in (website.folder for website in hooks.websites(catalog, SITE))
    ]
    search_index(site, *own, *projects)
    return site


def findings(site: Path, now: datetime = CHECKED) -> list[tuple[str, str]]:
    """What the check of the website in site finds at the moment now, as the path
    and the message of each finding."""
    found = hooks.check_site(site, hooks.load(ROOT), now)
    return [(finding.path, finding.message) for finding in found]


def test_the_website_that_the_hooks_build_keeps_every_promise(tmp_path: Path) -> None:
    assert findings(hub_site(tmp_path)) == []


def test_the_check_finds_every_missing_file(tmp_path: Path) -> None:
    catalog = hooks.load(ROOT)
    pages = sum(len(pages) for pages in catalog.former_pages.values())

    found = findings(tmp_path)

    hooks_named = (
        "is missing: on_post_build of .github/mkdocs_project.py writes it after the "
        "build, so check that hooks of mkdocs.yml names .github/mkdocs_project.py"
    )
    assert found[:3] == [
        (".well-known/security.txt", hooks_named),
        ("security.txt", hooks_named),
        ("robots.txt", hooks_named),
    ]
    moved = [path for path, _ in found if path.startswith("ha-autodarts/")]
    assert len(moved) == pages
    assert found[3 + pages :] == [
        (
            "404.html",
            "is missing: overrides/404.html is the page of every address that leads "
            "nowhere, and theme.custom_dir of mkdocs.yml names overrides",
        ),
        (
            "index.html",
            "is missing, the home page in en: the i18n plugin of mkdocs.yml builds it "
            "from docs/index.md and its translations",
        ),
        (
            "de/index.html",
            "is missing, the home page in de: the i18n plugin of mkdocs.yml builds it "
            "from docs/index.md and its translations",
        ),
        (
            "search/search_index.json",
            "is missing: the search plugin of mkdocs.yml writes it, and on_post_build "
            "of .github/mkdocs_project.py adds the project websites to it",
        ),
    ]


def test_security_txt_needs_its_policy_page(tmp_path: Path) -> None:
    site = hub_site(tmp_path)
    (site / "security.html").unlink()

    # Both copies are the same, so the finding names the first.
    assert findings(site) == [(".well-known/security.txt", POLICY_MESSAGE)]


def expires_at(moment: str) -> Callable[[str], str]:
    """The change of a security.txt that makes it expire at moment."""
    return lambda text: re.sub(r"(?m)^Expires: .*$", f"Expires: {moment}", text)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        pytest.param(
            expires_at("2026-10-01T00:00:00Z"),
            "expired at 2026-10-01T00:00:00Z: security_txt() of "
            ".github/mkdocs_project.py writes the midnight a year after the day of the "
            "build, so build the website again, with no SOURCE_DATE_EPOCH or one of "
            "today",
            id="expired",
        ),
        pytest.param(
            expires_at("2027-10-20T00:00:00Z"),
            "expires at 2027-10-20T00:00:00Z, more than 365 days from now, where RFC "
            "9116 recommends less than a year: keep VALID of .github/mkdocs_project.py "
            "at 365 days or fewer",
            id="more-than-a-year-ahead",
        ),
        pytest.param(
            expires_at("soon"),
            "names Expires: soon, which is no time of RFC 3339 with its zone, such as "
            "2027-10-24T00:00:00Z: security_txt() of .github/mkdocs_project.py writes "
            "one",
            id="no-time",
        ),
        pytest.param(
            expires_at("2027-01-01T00:00:00"),
            "names Expires: 2027-01-01T00:00:00, which is no time of RFC 3339 with its "
            "zone, such as 2027-10-24T00:00:00Z: security_txt() of "
            ".github/mkdocs_project.py writes one",
            id="no-zone",
        ),
        pytest.param(
            lambda text: re.sub(r"(?m)^Expires: .*\n", "", text),
            "has 0 Expires, where RFC 9116 asks for exactly one: security_txt() of "
            ".github/mkdocs_project.py writes one",
            id="no-expires",
        ),
        pytest.param(
            lambda text: text + "expires: 2027-01-01T00:00:00Z\n",
            "has 2 Expires, where RFC 9116 asks for exactly one: security_txt() of "
            ".github/mkdocs_project.py writes one",
            id="two-expires",
        ),
        pytest.param(
            lambda text: re.sub(r"(?m)^Contact: .*\n", "", text),
            "has no Contact, which RFC 9116 requires: security_txt() of "
            ".github/mkdocs_project.py writes CONTACT",
            id="no-contact",
        ),
        pytest.param(
            lambda text: text + "Contact: http://example.org/report\n",
            "names Contact: http://example.org/report, which is no https://, mailto: "
            "or tel: address of RFC 9116: set CONTACT of .github/mkdocs_project.py to "
            "the form for private reports",
            id="contact-without-tls",
        ),
        pytest.param(
            lambda text: text.replace(f"Canonical: {SITE}security.txt\n", ""),
            f"names no Canonical: {SITE}security.txt, the address of its copy at "
            "security.txt: security_txt() of .github/mkdocs_project.py names every "
            "path of SECURITY_TXT",
            id="one-canonical",
        ),
        pytest.param(
            lambda text: re.sub(r"(?m)^Policy: .*\n", "", text),
            "has no Policy, the security page of the address: security_txt() of "
            ".github/mkdocs_project.py names POLICY",
            id="no-policy",
        ),
        pytest.param(
            lambda text: text.replace(
                f"Policy: {SITE}security.html", "Policy: https://example.org/security"
            ),
            "names Policy: https://example.org/security, which is no page of the "
            "website: keep docs/security.md, or change POLICY of "
            ".github/mkdocs_project.py",
            id="policy-elsewhere",
        ),
    ],
)
def test_security_txt_keeps_rfc_9116(
    tmp_path: Path, change: Any, message: str
) -> None:
    site = hub_site(tmp_path)
    for name in hooks.SECURITY_TXT:
        path = site / name
        write(path, change(path.read_text(encoding="utf-8")))

    assert findings(site) == [(".well-known/security.txt", message)]


@pytest.mark.parametrize(
    "line",
    [
        # Names of fields compare without case, as RFC 9116 says.
        "contact: mailto:security@example.org",
        "CONTACT: tel:+49-30-1234567",
        # A policy may be the index of a folder of the website.
        f"Policy: {SITE}",
        f"Policy: {SITE}de/#a-section",
        "# A comment: Contact: http://example.org/",
    ],
)
def test_security_txt_may_have_more_than_the_hooks_write(
    tmp_path: Path, line: str
) -> None:
    site = hub_site(tmp_path)
    for name in hooks.SECURITY_TXT:
        path = site / name
        write(path, f"{path.read_text(encoding='utf-8')}\n{line}\n")

    assert findings(site) == []


def test_security_txt_is_the_same_in_both_places(tmp_path: Path) -> None:
    site = hub_site(tmp_path)
    root = site / "security.txt"
    write(root, root.read_text(encoding="utf-8").replace("Contact:", "Kontakt:"))

    # Both copies are checked, each once, as each may differ from the other.
    assert findings(site) == [
        (
            ".well-known/security.txt",
            "differs from security.txt: on_post_build of .github/mkdocs_project.py "
            "writes the same text into both, so remove what writes one of them after "
            "it, such as a file in docs/ or another plugin",
        ),
        (
            "security.txt",
            "has no Contact, which RFC 9116 requires: security_txt() of "
            ".github/mkdocs_project.py writes CONTACT",
        ),
    ]


def test_robots_names_the_sitemap_of_every_project_website_once(
    tmp_path: Path,
) -> None:
    site = hub_site(tmp_path)
    robots = (site / "robots.txt").read_text(encoding="utf-8")
    paperless = f"Sitemap: {SITE}paperless-sync/sitemap.xml\n"
    blueprint = f"Sitemap: {SITE}repo-blueprint/sitemap.xml\n"
    write(site / "robots.txt", robots.replace(paperless, "") + blueprint.lower())

    assert findings(site) == [
        (
            "robots.txt",
            f"names no Sitemap: {SITE}paperless-sync/sitemap.xml: robots() of "
            ".github/mkdocs_project.py names the sitemap of this website and of every "
            f"project of projects.toml whose docs are at {SITE}",
        ),
        (
            "robots.txt",
            f"names Sitemap: {SITE}repo-blueprint/sitemap.xml 2 times: robots() of "
            ".github/mkdocs_project.py names every sitemap once",
        ),
    ]


def test_no_sitemap_names_the_home_page_in_place_of_the_root(tmp_path: Path) -> None:
    site = hub_site(tmp_path)
    home = sitemap(f"{SITE}index.html", f"{SITE}about.html")
    write(site / "de/sitemap.xml", home)
    with gzip.GzipFile(site / "sitemap.xml.gz", "wb", mtime=BUILT) as packed:
        packed.write(home.encode("utf-8"))

    message = (
        f"names {SITE}index.html in place of {SITE}, the canonical address of the "
        "home page: sitemaps_at_root() of .github/mkdocs_project.py leads it to the "
        "root after the build"
    )
    assert findings(site) == [("de/sitemap.xml", message), ("sitemap.xml.gz", message)]


def test_a_website_without_a_packed_sitemap_or_one_of_its_own_passes(
    tmp_path: Path,
) -> None:
    site = hub_site(tmp_path)
    for name in ("sitemap.xml", "sitemap.xml.gz", "de/sitemap.xml"):
        (site / name).unlink()

    assert findings(site) == []


def test_every_old_address_has_its_page_that_leads_to_the_same_page_now(
    tmp_path: Path,
) -> None:
    site = hub_site(tmp_path)
    (site / "ha-autodarts/games.html").unlink()
    elsewhere = hooks.moved_page("HomeDarts", f"{SITE}homedarts-for-autodarts/", "de")
    write(site / "ha-autodarts/de/games.html", elsewhere)
    refreshed = (site / "ha-autodarts/faq.html").read_text(encoding="utf-8")
    later = refreshed.replace('content="0; ', 'content="5; ')
    write(site / "ha-autodarts/faq.html", later)

    new = f"{SITE}homedarts-for-autodarts/"
    leads = (
        "the same page in the folder of the website now, with its canonical address "
        "and its refresh: moved_page() of .github/mkdocs_project.py writes both, so "
        "remove what writes the page after it, such as a file in docs/"
    )
    # Sorted, as they come in the order of former/ha-autodarts.txt.
    assert sorted(findings(site)) == [
        ("ha-autodarts/de/games.html", f"doesn't lead to {new}de/games.html, {leads}"),
        ("ha-autodarts/faq.html", f"doesn't lead to {new}faq.html, {leads}"),
        (
            "ha-autodarts/games.html",
            "is missing, an old address that former/ha-autodarts.txt lists: "
            "on_post_build of .github/mkdocs_project.py writes a page there that leads "
            f"to {new}games.html",
        ),
    ]


@pytest.mark.parametrize(
    "data",
    [
        not_found_data({"ha-autodarts": "https://dennis-otto.github.io/elsewhere/"}),
        not_found_data({}),
        # Without its moves, without an object, or no JSON at all.
        not_found_data(),
        "null",
        "{not json",
    ],
)
def test_the_404_page_leads_every_old_folder_to_its_website(
    tmp_path: Path, data: str
) -> None:
    site = hub_site(tmp_path)
    write(site / "404.html", not_found_page(data))

    assert findings(site) == [
        (
            "404.html",
            f"doesn't lead /ha-autodarts/ to {SITE}homedarts-for-autodarts/, as former "
            "of projects.toml asks: its script needs catalog.moves() as the moves of "
            "the JSON of #not-found-data, as overrides/404.html writes them",
        )
    ]


def test_the_tests_of_the_404_script_run_it_on_the_data_of_the_website() -> None:
    # tests/not-found.test.mjs runs overrides/partials/not-found.js on this file, so
    # it must hold what overrides/404.html writes into #not-found-data for
    # projects.toml. After a change of the catalog, write it anew with
    # json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) and a newline.
    catalog = hooks.load(ROOT)
    data = {"moves": catalog.moves(), "projects": catalog.directory()}
    fixture = ROOT / "tests/fixtures/not-found-data.json"

    assert json.loads(fixture.read_text(encoding="utf-8")) == data


def test_a_404_page_without_its_script_leads_no_old_folder(tmp_path: Path) -> None:
    write(tmp_path / "404.html", '<html lang="en"><p>Nothing here.</p></html>')
    moved = hooks.read(catalog_data(entry(former=["old"])))

    assert hooks.not_found_findings(tmp_path, moved)[0].message.startswith(
        f"doesn't lead /old/ to {SITE}tool/, as former of projects.toml asks"
    )
    # Without a folder of former, the page leads none.
    assert hooks.not_found_findings(tmp_path, hooks.read(catalog_data())) == []


def test_a_404_page_that_leads_an_old_folder_the_catalog_lacks(tmp_path: Path) -> None:
    write(tmp_path / "404.html", not_found_page(not_found_data({"old": f"{SITE}tool/"})))

    [finding] = hooks.not_found_findings(tmp_path, hooks.read(catalog_data()))
    assert finding.message == (
        "leads old folders that former of projects.toml doesn't name: its script "
        "needs catalog.moves() as the moves of the JSON of #not-found-data, as "
        "overrides/404.html writes them"
    )


def test_every_home_page_has_the_card_of_every_project(tmp_path: Path) -> None:
    site = hub_site(tmp_path)
    german = site / "de/index.html"
    text = german.read_text(encoding="utf-8")
    # The card of Paperless Sync, from its own div to the end of it.
    within = r'<div class="card">(?:(?!</div>).)*'
    card = re.search(within + r'"paperless-sync".*?</div>', text)
    assert card is not None
    anchor = '<span id="ha-autodarts"></span>'
    write(german, text.replace(card[0], "").replace(anchor, ""))

    assert findings(site) == [
        (
            "de/index.html",
            "has 5 cards, not one for each of the 6 projects with a group of "
            "projects.toml: cards() of .github/mkdocs_project.py writes them in place "
            "of <!-- projects -->",
        ),
        (
            "de/index.html",
            "lacks the anchor #ha-autodarts, where the card of homedarts-for-autodarts "
            "was before, as former of projects.toml names it: card() of "
            ".github/mkdocs_project.py keeps it in the heading of the card",
        ),
        (
            "de/index.html",
            "has no card of paperless-sync, whose heading has the anchor "
            "#paperless-sync: card() of .github/mkdocs_project.py writes one for every "
            "project with a group of projects.toml",
        ),
        (
            "de/index.html",
            "shows no images/projects/de/paperless-sync.webp, the picture of the "
            "card of paperless-sync in de: card() of .github/mkdocs_project.py puts "
            "the image of projects.toml in the language of the page on top of it",
        ),
    ]


def test_the_pictures_of_the_first_group_load_at_once_in_the_website(
    tmp_path: Path,
) -> None:
    # The hook of the blueprint makes every picture that doesn't say how it loads,
    # but the first of a page, wait until it comes into view.
    site = hub_site(tmp_path)
    for name in ("index.html", "de/index.html"):
        page = site / name
        text = page.read_text(encoding="utf-8")
        write(page, text.replace(' width="640"', ' width="640" loading="lazy"'))
    first = hooks.load(ROOT).groups[0]

    found = findings(site)

    assert len(found) == 2 * len(hooks.load(ROOT).members(first))
    assert found[-1] == (
        "de/index.html",
        "loads images/projects/de/paperless-unified-search.webp, the picture of the "
        "card of paperless-unified-search, only as it comes into view, though its "
        "group is in view as the page opens: section() of .github/mkdocs_project.py "
        'gives the pictures of the first group loading="eager", which lazy() of '
        ".github/mkdocs_blueprint.py leaves as it is",
    )


def test_every_card_has_its_picture_in_the_website(tmp_path: Path) -> None:
    site = hub_site(tmp_path)
    (site / "images/projects/issue-assistant.webp").unlink()

    # Once, though both home pages show it.
    assert findings(site) == [
        (
            "images/projects/issue-assistant.webp",
            "is missing, the picture of the card of issue-assistant: make it with bash "
            "scripts/project-pictures.sh, or fix image of issue-assistant in "
            "projects.toml",
        )
    ]


def structured_data(site: Path, head: str) -> None:
    """The home page of the website in site with head in place of the structured
    data that the hooks put into its head."""
    home = site / "index.html"
    tags = re.compile(r'<link rel="me".*?</script>\n', re.DOTALL)
    write(home, tags.sub(lambda _: head, home.read_text(encoding="utf-8")))


@pytest.mark.parametrize(
    "script",
    [
        "",
        '<script type="application/ld+json">{"@graph": [</script>',
        '<script type="application/ld+json">{"@graph": []}</script>',
        '<script type="application/ld+json">{"@graph": [{"name": "x"}]}</script>',
        '<script type="application/ld+json">{"@graph": [{"@type": "ItemList"}]}'
        "</script>",
        '<script type="application/ld+json">{}</script>'
        '<script type="application/ld+json">{}</script>',
    ],
)
def test_the_home_page_has_one_json_ld_with_the_projects(
    tmp_path: Path, script: str
) -> None:
    site = hub_site(tmp_path)
    structured_data(site, script)

    assert findings(site) == [
        (
            "index.html",
            "has no JSON-LD that lists the projects, or more than one: on_post_page of "
            ".github/mkdocs_project.py puts that of structured_data() into its head",
        )
    ]


def test_the_json_ld_lists_every_project_with_a_repo_in_its_order(
    tmp_path: Path,
) -> None:
    site = hub_site(tmp_path)
    catalog = hooks.load(ROOT)
    fewer = dataclasses.replace(catalog, projects=catalog.projects[1:2])
    structured_data(site, hooks.structured_data(fewer, SITE, "Dennis Otto"))

    [(path, message)] = findings(site)
    assert path == "index.html"
    assert message.startswith(
        f"lists {SITE}#player-switch-for-autodarts in its JSON-LD, not every project "
        f"with a repo of projects.toml in its order, {SITE}#homedarts-for-autodarts, "
    )
    assert message.endswith(
        ": structured_data() of .github/mkdocs_project.py lists them"
    )


def test_a_json_ld_without_projects_lists_none(tmp_path: Path) -> None:
    site = hub_site(tmp_path)
    none = dataclasses.replace(hooks.load(ROOT), projects=())
    structured_data(site, hooks.structured_data(none, SITE, "Dennis Otto"))

    [(_, message)] = findings(site)
    assert message.startswith("lists no project in its JSON-LD")


def test_the_search_keeps_the_pages_of_this_website_with_their_boosts(
    tmp_path: Path,
) -> None:
    site = hub_site(tmp_path)
    index = json.loads((site / "search/search_index.json").read_text(encoding="utf-8"))
    docs = [
        {key: value for key, value in doc.items() if key != "boost"}
        for doc in index["docs"]
        if doc["location"].partition("#")[0] != "de/about.html"
    ]
    search_index(site, *docs)

    assert findings(site) == [
        (
            "search/search_index.json",
            f"has no entry of 1 page(s) of this website that sitemap.xml lists, such "
            f"as {SITE}de/about.html: add_to_search() of .github/mkdocs_project.py "
            "keeps the entries of this website beside those of the projects",
        ),
        (
            "search/search_index.json",
            "gives 4 entries of this website no boost, such as releases.html: "
            "add_to_search() of .github/mkdocs_project.py gives them that of their "
            "page after the search plugin has written the index, so something wrote "
            "it again after on_post_build, which must come last, as check_order() "
            "makes sure",
        ),
    ]


def test_the_search_has_the_entries_of_the_project_websites(tmp_path: Path) -> None:
    site = hub_site(tmp_path)
    index = json.loads((site / "search/search_index.json").read_text(encoding="utf-8"))
    own = [doc for doc in index["docs"] if " › " not in doc["title"]]
    stray = {"location": "games.html", "title": "HomeDarts › Games", "text": ""}
    search_index(site, *own, stray)

    assert findings(site) == [
        (
            "search/search_index.json",
            f"has no entry of the 6 project websites at {SITE}: on_post_build of "
            ".github/mkdocs_project.py adds them after the build. When the log of the "
            "build says that the search leaves out every website, GitHub Pages was "
            "away while it ran: run the job again",
        ),
        (
            "search/search_index.json",
            "has 1 entries of a project outside the folder of its website, such as "
            "games.html: entries() of .github/mkdocs_project.py puts every location "
            "into the folder of its website",
        ),
    ]


def test_a_website_without_project_websites_needs_none_in_its_search(
    tmp_path: Path,
) -> None:
    search_index(tmp_path, {"location": "index.html", "title": "Home", "text": ""})
    alone = hooks.read(catalog_data(entry(docs="https://example.org/tool/")))

    assert hooks.search_findings(tmp_path, alone) == []


def test_a_search_index_that_is_none_is_named(tmp_path: Path) -> None:
    site = hub_site(tmp_path)
    write(site / "search/search_index.json", '{"docs": "none"}')

    [(path, message)] = findings(site)
    assert path == "search/search_index.json"
    assert message.startswith(
        "can't be read: search/search_index.json is no search index of Material for "
        "MkDocs"
    )


def test_the_check_runs_as_the_script_with_the_folder_of_the_website(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    site = hub_site(tmp_path / "site", datetime.now(UTC).date())

    assert hooks.main(["--site", str(site)]) == 0

    assert capsys.readouterr().out == (
        f"The website in {site.as_posix()} keeps what the hooks of "
        ".github/mkdocs_project.py promise: security.txt, robots.txt, the sitemaps, "
        "the old addresses, the 404 page, the home pages and the search.\n"
    )


@pytest.mark.parametrize("actions", [True, False])
def test_the_script_names_every_broken_promise_and_annotates_it_in_the_ci(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    actions: bool,
) -> None:
    if actions:
        monkeypatch.setenv("GITHUB_ACTIONS", "true")
    else:
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    site = hub_site(tmp_path / "site", datetime.now(UTC).date())
    (site / "security.html").unlink()
    monkeypatch.chdir(tmp_path)

    assert hooks.main(["--site", "site/"]) == 1

    lines = capsys.readouterr().out.splitlines()
    finding = f"site/.well-known/security.txt: {POLICY_MESSAGE}"
    annotations = [f"::error title=What the hooks of the hub promise::{finding}"]
    assert lines[:-1] == [finding, *(annotations if actions else [])]
    assert lines[-1].startswith(
        "1 finding(s): the website breaks what the hooks of .github/mkdocs_project.py "
        "promise."
    )
    assert lines[-1].endswith("check its folder with bash scripts/check-site.sh site.")


def test_an_annotation_keeps_its_message_on_one_line() -> None:
    finding = hooks.Finding("robots.txt", "100% wrong\r\nhere")

    assert hooks.annotation(finding, "site") == (
        "::error title=What the hooks of the hub promise::"
        "site/robots.txt: 100%25 wrong%0D%0Ahere"
    )


def test_the_check_needs_the_folder_of_a_built_website(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert hooks.main(["--site", str(tmp_path / "site")]) == 1

    assert capsys.readouterr().err == (
        f"{(tmp_path / 'site').as_posix()} is no folder: build the website with "
        "mkdocs build --strict, and name its folder, such as site.\n"
    )


def test_the_check_needs_the_catalog(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert hooks.main(["--site", str(tmp_path)], tmp_path) == 1

    assert "projects.toml can't be read" in capsys.readouterr().err


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
    return hooks.repositories(json.dumps(list(items)))


class Websites:
    """A stand-in for hooks.status: the status of every address it knows, 404 for
    every other, and the addresses that the bot asked for, in their order."""

    def __init__(self, answers: dict[str, int] | None = None) -> None:
        self.answers = answers or {}
        self.asked: list[str] = []

    def __call__(self, url: str) -> int:
        self.asked.append(url)
        return self.answers.get(url, 404)


class Files:
    """A stand-in for hooks.fetched: the content of every file that it knows by its
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
    return hooks.drift(
        hooks.read(catalog_data(*projects)),
        repositories,
        websites or Websites(),
        files or Files(),
    )


# The repositories of the owner as gh listed them on 2026-10-13, with a private and
# an archived one of the kind that a person's token sees too, and ha-autodarts under
# the name that it has since 2026-10-21.
TODAY = [
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
# The German websites of the projects on that day.
GERMAN_SITES = {
    f"{SITE}homedarts-for-autodarts/de/": 200,
    f"{SITE}player-switch-for-autodarts/de/": 200,
    f"{SITE}paperless-sync/de/": 200,
    f"{SITE}paperless-unified-search/de/": 200,
    f"{SITE}repo-blueprint/de/": 200,
}


def test_the_catalog_of_the_repository_is_current() -> None:
    websites = Websites(GERMAN_SITES)
    files = Files(network_files())

    assert hooks.drift(hooks.load(ROOT), found(*TODAY), websites, files) == []
    # The file of every project that reads what it works with from one, and those
    # from which the hub draws its pictures.
    assert files.asked == list(network_files())
    # The German website of every project at the address: those of the catalog,
    # and those that may have appeared.
    assert websites.asked == [
        f"{SITE}{slug}/de/"
        for slug in (
            "homedarts-for-autodarts",
            "player-switch-for-autodarts",
            "paperless-sync",
            "paperless-unified-search",
            "issue-assistant",
            "repo-blueprint",
        )
    ]


def test_the_bot_compares_with_the_address_of_the_website() -> None:
    settings = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    site_url = re.search(r"^site_url: (\S+)$", settings, re.MULTILINE)

    assert site_url is not None
    assert hooks.SITE == site_url[1] == SITE


def test_a_new_repository_with_a_website_at_the_address_needs_a_project() -> None:
    repositories = found(
        listed_repo("tool", f"{SITE}tool/"),
        listed_repo("new-thing", "https://Dennis-Otto.github.io/new-thing"),
    )

    assert drift(one_language(), repositories=repositories) == [
        "Dennis-Otto/new-thing has its website at "
        "https://Dennis-Otto.github.io/new-thing, but projects.toml has no project "
        'for it. Add a `[[project]]` with `repo = "Dennis-Otto/new-thing"`.'
    ]


def test_new_repositories_follow_the_catalog_by_their_names() -> None:
    repositories = found(
        listed_repo("tool", f"{SITE}tool-docs/"),
        listed_repo("zebra", f"{SITE}zebra/"),
        listed_repo("Alpaca", f"{SITE}alpaca/"),
    )

    differences = drift(one_language(), repositories=repositories)

    assert [difference.split()[0] for difference in differences] == [
        "`tool`:",
        "Dennis-Otto/Alpaca",
        "Dennis-Otto/zebra",
    ]


def test_a_repository_without_a_website_at_the_address_needs_no_project() -> None:
    repositories = found(
        listed_repo("tool", f"{SITE}tool/"),
        # An archived and a private repository, which the issue never names.
        listed_repo("old", f"{SITE}old/", archived=True),
        listed_repo("secret", f"{SITE}secret/", private=True),
        # This website, at the root of the address, and websites elsewhere.
        listed_repo("dennis-otto.github.io", "https://dennis-otto.github.io"),
        listed_repo("app", "https://example.org/app/"),
        listed_repo("lookalike", "https://dennis-otto.github.io.example.org/x/"),
        listed_repo("empty", ""),
        listed_repo("none", None),
    )

    assert drift(one_language(), repositories=repositories) == []


def test_a_repository_with_the_website_of_a_project_needs_no_other() -> None:
    repositories = found(
        listed_repo("tool", f"{SITE}tool/"),
        listed_repo("tool-mirror", f"{SITE}tool/"),
    )

    assert drift(one_language(), repositories=repositories) == []


def test_a_renamed_repository_is_found_by_its_website() -> None:
    repositories = found(listed_repo("better-tool", f"{SITE}tool"))

    assert drift(one_language(), repositories=repositories) == [
        "`tool`: Dennis-Otto/tool is no repository on GitHub any more, and "
        f"Dennis-Otto/better-tool has its website {SITE}tool/; it was renamed. Set "
        '`repo = "Dennis-Otto/better-tool"`.'
    ]


def test_a_repository_that_is_gone_is_named() -> None:
    repositories = found(listed_repo("other", "https://example.org/"))

    assert drift(one_language(), repositories=repositories) == [
        "`tool`: Dennis-Otto/tool is no public repository on GitHub any more; it "
        "was renamed, made private or deleted. Correct `repo`, or remove the "
        "project."
    ]


def test_the_repository_of_another_project_is_no_successor() -> None:
    # board names the website of tool on GitHub, whose repository is gone.
    repositories = found(listed_repo("board", f"{SITE}tool/"))

    assert drift(one_language(), one_language("board"), repositories=repositories) == [
        "`tool`: Dennis-Otto/tool is no public repository on GitHub any more; it "
        "was renamed, made private or deleted. Correct `repo`, or remove the "
        "project.",
        f"`board`: Dennis-Otto/board names {SITE}tool/ as its website on GitHub, "
        f"but projects.toml leads to {SITE}board/. Correct `docs`, or the website "
        "of the repository.",
    ]


PRIVATE = (
    "`tool`: Dennis-Otto/tool is private now. Remove the project, or make the "
    "repository public again."
)


@pytest.mark.parametrize(
    ("archived", "private", "message"),
    [
        (
            True,
            False,
            "`tool`: Dennis-Otto/tool is archived. Remove the project, or unarchive "
            "the repository.",
        ),
        (False, True, PRIVATE),
        (True, True, PRIVATE),
    ],
)
def test_an_archived_or_private_repository_of_the_catalog_is_named(
    archived: bool, private: bool, message: str
) -> None:
    repositories = found(
        listed_repo("tool", f"{SITE}tool/", archived=archived, private=private)
    )

    assert drift(one_language(), repositories=repositories) == [message]


@pytest.mark.parametrize(
    "homepage",
    [
        f"{SITE}tool/",
        f"{SITE}tool",
        "https://DENNIS-OTTO.github.io/tool/",
        "http://dennis-otto.github.io/tool/",
        # A website elsewhere, or none, is the repository's own business.
        "https://example.org/tool/",
        "",
    ],
)
def test_a_repository_with_the_website_of_its_project_is_current(
    homepage: str,
) -> None:
    repositories = found(listed_repo("tool", homepage))

    assert drift(one_language(), repositories=repositories) == []


def test_a_repository_with_another_website_at_the_address_is_named() -> None:
    repositories = found(listed_repo("tool", f"{SITE}tool-docs/"))

    assert drift(one_language(), repositories=repositories) == [
        f"`tool`: Dennis-Otto/tool names {SITE}tool-docs/ as its website on GitHub, "
        f"but projects.toml leads to {SITE}tool/. Correct `docs`, or the website of "
        "the repository."
    ]


def test_a_project_without_a_repository_has_none_to_compare() -> None:
    board = without_card(without_repo(one_language("board")))
    tool = one_language(second="board")

    assert drift(tool, board, repositories=found(listed_repo("tool"))) == []


def test_a_german_website_that_appeared_is_named() -> None:
    websites = Websites({f"{SITE}tool/de/": 200})

    assert drift(
        one_language(), repositories=found(listed_repo("tool")), websites=websites
    ) == [
        f"`tool`: it has a German website at {SITE}tool/de/ now. Write "
        f'`docs.en = "{SITE}tool/"` and `docs.de = "{SITE}tool/de/"` in place of '
        "`docs`, so that the German home page leads there."
    ]
    assert websites.asked == [f"{SITE}tool/de/"]


def test_the_fix_for_a_german_website_that_appeared_is_valid_toml() -> None:
    # A project in English alone writes docs as one address, beside which a docs.de
    # would be a second value of docs, so the issue has docs replaced instead.
    written = f'docs = "{SITE}tool/"\n'
    repositories = found(listed_repo("tool"))
    websites = Websites({f"{SITE}tool/de/": 200})
    [difference] = drift(
        entry(**tomllib.loads(written)), repositories=repositories, websites=websites
    )
    keys = re.findall(r'`(docs\.\w+ = "[^"]+")`', difference)
    fixed = "".join(f"{key}\n" for key in keys)

    assert len(keys) == 2
    assert drift(
        entry(**tomllib.loads(fixed)), repositories=repositories, websites=websites
    ) == []


def test_the_folder_of_a_language_is_found_without_the_slash_of_the_website() -> None:
    websites = Websites()

    drift(
        entry(docs=f"{SITE}tool"),
        repositories=found(listed_repo("tool")),
        websites=websites,
    )

    assert websites.asked == [f"{SITE}tool/de/"]


@pytest.mark.parametrize("code", [404, 410])
def test_a_german_website_that_is_gone_is_named(code: int) -> None:
    websites = Websites({f"{SITE}tool/de/": code})
    repositories = found(listed_repo("tool"))

    assert drift(entry(), repositories=repositories, websites=websites) == [
        f"`tool`: the German website {SITE}tool/de/ is gone. Remove `docs.de`, so "
        "that the German home page leads to the English one."
    ]
    assert websites.asked == [f"{SITE}tool/de/"]


def test_a_german_website_of_the_catalog_is_current() -> None:
    websites = Websites({f"{SITE}tool/de/": 200})
    repositories = found(listed_repo("tool"))

    assert drift(entry(), repositories=repositories, websites=websites) == []


def test_only_a_website_at_the_address_is_asked_for_its_languages() -> None:
    websites = Websites()
    elsewhere = entry(docs="https://example.org/tool/")
    without_docs = entry("board")
    del without_docs["docs"]
    repositories = found(listed_repo("tool"), listed_repo("board"))

    differences = drift(
        elsewhere, without_docs, repositories=repositories, websites=websites
    )

    assert differences == []
    assert websites.asked == []


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


def test_a_language_without_a_name_is_named_by_its_code() -> None:
    data = in_french(catalog_data(one_language()))
    data["languages"] = ["en", "fr"]
    websites = Websites({f"{SITE}tool/fr/": 200})

    assert hooks.drift(
        hooks.read(data), found(listed_repo("tool")), websites, Files()
    ) == [
        f"`tool`: it has a fr website at {SITE}tool/fr/ now. Write "
        f'`docs.en = "{SITE}tool/"` and `docs.fr = "{SITE}tool/fr/"` in place of '
        "`docs`, so that the fr home page leads there."
    ]


@pytest.mark.parametrize(
    ("languages", "code"),
    [("one", 500), ("both", 403), ("both", 301)],
)
def test_an_odd_answer_of_a_website_stops_the_bot(languages: str, code: int) -> None:
    project = one_language() if languages == "one" else entry()
    websites = Websites({f"{SITE}tool/de/": code})

    with pytest.raises(hooks.CheckError) as error:
        drift(project, repositories=found(listed_repo("tool")), websites=websites)

    assert str(error.value) == (
        f"{SITE}tool/de/ answers {code}, where the catalog bot expects 200 or 404; "
        "start it again later."
    )


@pytest.mark.parametrize(
    ("url", "wanted"),
    [
        (f"{SITE}tool/", f"{SITE}tool/"),
        (" https://Dennis-Otto.GitHub.io/tool ", f"{SITE}tool/"),
        ("http://dennis-otto.github.io/tool//", f"{SITE}tool/"),
        ("https://dennis-otto.github.io", SITE),
        ("", "https:///"),
    ],
)
def test_addresses_are_compared_as_github_pages_serves_them(
    url: str, wanted: str
) -> None:
    assert hooks.address(url) == wanted


@pytest.mark.parametrize(
    ("url", "wanted"),
    [
        (f"{SITE}tool/", True),
        (f"{SITE}tool/de/", True),
        (SITE, False),
        ("https://dennis-otto.github.io.example.org/tool/", False),
        ("https://example.org/", False),
        ("", False),
    ],
)
def test_a_website_of_a_project_is_in_a_folder_of_the_address(
    url: str, wanted: bool
) -> None:
    assert hooks.at_site(url) is wanted


def test_the_list_of_the_repositories_takes_a_missing_website_as_none() -> None:
    repositories = found(
        listed_repo("tool", None),
        listed_repo("app", "https://x.org/", archived=True, private=True),
    )

    assert repositories == [
        hooks.Repository("Dennis-Otto/tool", "", archived=False, private=False),
        hooks.Repository(
            "Dennis-Otto/app", "https://x.org/", archived=True, private=True
        ),
    ]


@pytest.mark.parametrize(
    "items",
    [
        {},
        [],
        ["Dennis-Otto/tool"],
        [{"nameWithOwner": "Dennis-Otto/tool"}],
        [{**listed_repo("tool"), "nameWithOwner": None}],
        [{**listed_repo("tool"), "homepageUrl": 1}],
        [{**listed_repo("tool"), "isArchived": "false"}],
        [{**listed_repo("tool"), "isPrivate": None}],
        [listed_repo("tool"), None],
    ],
)
def test_a_broken_list_of_the_repositories_stops_the_bot(items: object) -> None:
    with pytest.raises(hooks.CheckError) as error:
        hooks.repositories(json.dumps(items))

    assert str(error.value) == (
        "The list of the repositories must be the JSON of gh repo list --json "
        "nameWithOwner,homepageUrl,isArchived,isPrivate, with one at least."
    )


def test_a_list_of_the_repositories_that_is_no_json_stops_the_bot() -> None:
    with pytest.raises(hooks.CheckError) as error:
        hooks.repositories("GraphQL: Could not resolve to a User")

    assert str(error.value).startswith(
        "The list of the repositories isn't the JSON of gh repo list --json "
        "nameWithOwner,homepageUrl,isArchived,isPrivate: Expecting value"
    )


class Response:
    """A stand-in for the answer of urllib.request.urlopen."""

    status = 200

    def __enter__(self) -> Response:
        return self

    def __exit__(self, *exception: object) -> None:
        return None


def test_the_status_of_a_website_comes_from_a_head_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[tuple[Any, float]] = []

    def urlopen(request: Any, timeout: float) -> Response:
        requests.append((request, timeout))
        return Response()

    monkeypatch.setattr(hooks.urllib.request, "urlopen", urlopen)

    assert hooks.status(f"{SITE}tool/de/") == 200
    [(request, timeout)] = requests
    assert (request.full_url, request.get_method()) == (f"{SITE}tool/de/", "HEAD")
    assert timeout == hooks.TIMEOUT == 30


def test_a_website_that_is_gone_answers_with_its_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    errors: list[Any] = []

    def urlopen(request: Any, timeout: float) -> Response:
        error = hooks.urllib.error.HTTPError(
            request.full_url, 404, "Not Found", email.message.Message(), None
        )
        errors.append(error)
        raise error

    monkeypatch.setattr(hooks.urllib.request, "urlopen", urlopen)

    assert hooks.status(f"{SITE}tool/de/") == 404
    # The answer of the website is closed, as an answer without an error is.
    assert errors[0].fp.closed


def test_a_website_that_cant_be_reached_stops_the_bot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def urlopen(request: Any, timeout: float) -> Response:
        raise hooks.urllib.error.URLError("timed out")

    monkeypatch.setattr(hooks.urllib.request, "urlopen", urlopen)

    with pytest.raises(hooks.CheckError) as error:
        hooks.status(f"{SITE}tool/de/")

    assert str(error.value) == (
        f"{SITE}tool/de/ can't be reached: <urlopen error timed out>"
    )


def test_the_issue_names_every_difference_and_how_to_fix_it() -> None:
    text = hooks.report(["`tool`: one.", "Dennis-Otto/app: two."])

    assert text == (
        "The catalog bot compares projects.toml with the repositories on GitHub, with "
        "the websites of the projects in every language and with the files that say "
        "what they work with every week, and found 2 difference(s):\n"
        "\n"
        "- `tool`: one.\n"
        "- Dennis-Otto/app: two.\n"
        "\n"
        "Change projects.toml, whose comments describe every key, and write the "
        "table of the README with\n"
        "\n"
        "```sh\n"
        "python3 -I .github/mkdocs_project.py --write\n"
        "```\n"
        "\n"
        "A new card needs its picture too, which `bash scripts/project-pictures.sh` "
        "makes. The next run closes this issue once the catalog is current; start "
        "the Catalog workflow by hand to check sooner.\n"
    )


def test_the_workflow_of_the_bot_compares_every_week() -> None:
    workflow = (ROOT / ".github/workflows/catalog.yml").read_text(encoding="utf-8")

    assert '- cron: "23 5 * * 1"' in workflow
    assert "  workflow_dispatch:\n" in workflow
    # gh lists the fields that the comparison reads, and the bot runs it.
    assert f"--json {','.join(hooks.FIELDS)} " in workflow
    assert "python3 -I .github/mkdocs_project.py --network " in workflow
    # It reads the repository and writes the issue, and nothing else.
    catalog = workflow[: workflow.index("\n  rebuild:\n")]
    assert "\npermissions: {}\n" in workflow
    assert re.findall(r"^ +([a-z-]+): (read|write)\b", catalog, re.MULTILINE) == [
        ("contents", "read"),
        ("issues", "write"),
    ]
    assert "persist-credentials: false" in catalog
    assert 'title="The project catalog is out of date"' in catalog
    # By hand, it compares unless it is asked to build the website.
    assert "if: github.event.schedule == '23 5 * * 1' || inputs.job == 'catalog'" in (
        catalog
    )
    assert "        default: catalog\n" in catalog


def test_the_workflow_of_the_bot_builds_the_website_every_day() -> None:
    workflow = (ROOT / ".github/workflows/catalog.yml").read_text(encoding="utf-8")
    rebuild = workflow[workflow.index("\n  rebuild:\n") :]

    assert '- cron: "41 4 * * *"' in workflow
    assert "if: github.event.schedule == '41 4 * * *' || inputs.job == 'rebuild'" in (
        rebuild
    )
    # It starts the Docs workflow on main, which publishes the website, and may do
    # nothing else.
    assert "run: gh workflow run docs.yml --ref main\n" in rebuild
    assert re.findall(r"^ +([a-z-]+): (read|write)\b", rebuild, re.MULTILINE) == [
        ("actions", "write")
    ]
    assert "actions/checkout" not in rebuild
    # The group is that of the job, not that of the trigger: a comparison started
    # by hand and the one of Monday wait for each other.
    assert (
        "  group: ${{ github.workflow }}-${{ (github.event.schedule == '41 4 * * *'"
        " || inputs.job == 'rebuild') && 'rebuild' || 'catalog' }}\n"
    ) in workflow
    docs = (ROOT / ".github/workflows/docs.yml").read_text(encoding="utf-8")
    assert "\n  workflow_dispatch:\n" in docs


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


def test_the_bot_reaches_only_github_and_the_address_of_the_websites() -> None:
    workflow = (ROOT / ".github/workflows/catalog.yml").read_text(encoding="utf-8")
    hosts = guarded(
        workflow[workflow.index("\n  catalog:\n") : workflow.index("\n  rebuild:\n")]
    )

    # gh asks api.github.com and the checkout github.com; the comparison asks the
    # websites at SITE for their status and reads the files that say what a
    # project works with from RAW, and reaches nothing else.
    assert hosts == [
        "api.github.com:443",
        "github.com:443",
        f"{urlsplit(hooks.SITE).hostname}:443",
        f"{urlsplit(hooks.RAW).hostname}:443",
    ]
    assert "egress-policy: audit" not in workflow
    # The bot asks every website in a further language of a project whose website
    # is at SITE, so one on another host would be blocked.
    catalog = hooks.load(ROOT)
    for project in catalog.projects:
        if project.docs is not None and hooks.at_site(
            project.docs.url[catalog.default]
        ):
            for url in project.docs.url.values():
                assert f"{urlsplit(url).hostname}:443" in hosts, url


def test_the_rebuild_reaches_only_the_api_of_github() -> None:
    workflow = (ROOT / ".github/workflows/catalog.yml").read_text(encoding="utf-8")

    # gh workflow run asks api.github.com alone, and the job checks out nothing.
    assert guarded(workflow[workflow.index("\n  rebuild:\n") :]) == [
        "api.github.com:443"
    ]


def lists(root: Path, *items: dict[str, Any]) -> Path:
    """The file of gh repo list with items, in root."""
    path = root / "repositories.json"
    path.write_text(json.dumps(list(items)), encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (http.client.BadStatusLine("HTTP/9 OK"), "HTTP/9 OK"),
        (http.client.RemoteDisconnected("closed"), "closed"),
        (ValueError("unknown url type"), "unknown url type"),
    ],
)
def test_a_website_that_answers_brokenly_stops_the_bot(
    monkeypatch: pytest.MonkeyPatch, error: Exception, message: str
) -> None:
    def urlopen(request: Any, timeout: float) -> Response:
        raise error

    monkeypatch.setattr(hooks.urllib.request, "urlopen", urlopen)

    with pytest.raises(hooks.CheckError) as stop:
        hooks.status(f"{SITE}tool/de/")

    assert str(stop.value) == f"{SITE}tool/de/ can't be reached: {message}"


def test_a_crash_of_the_bot_cant_pass_for_a_difference() -> None:
    # Python exits with 1 when it stops with an exception and argparse with 2, so
    # the workflow takes only DIFFERS for the text of an issue.
    workflow = (ROOT / ".github/workflows/catalog.yml").read_text(encoding="utf-8")
    cases = re.findall(r"^ {12}(\S+)\)", workflow, re.MULTILINE)

    assert hooks.DIFFERS not in {0, 1, 2}
    assert cases == ["0", str(hooks.DIFFERS), "*"]


def test_an_unexpected_error_of_the_bot_isnt_a_difference(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository(tmp_path)

    def status(url: str) -> int:
        raise RuntimeError(url)

    monkeypatch.setattr(hooks, "status", status)

    # It reaches Python, which exits with 1, never with DIFFERS.
    with pytest.raises(RuntimeError):
        hooks.main(["--network", str(lists(tmp_path, *TODAY))], tmp_path)


def test_the_script_finds_the_catalog_of_the_repository_current(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Without a README, which the comparison doesn't need.
    repository(tmp_path).unlink()
    monkeypatch.setattr(hooks, "status", Websites(GERMAN_SITES))
    monkeypatch.setattr(hooks, "fetched", Files(network_files()))

    assert hooks.main(["--network", str(lists(tmp_path, *TODAY))], tmp_path) == 0

    assert capsys.readouterr() == (
        "projects.toml is current: it has every repository with a website at "
        f"{SITE}, every website in a further language, every file that says "
        "what a project works with, and every file from which the hub draws a "
        "picture of a card.\n",
        "",
    )


def test_the_script_writes_the_issue_when_the_catalog_differs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    repository(tmp_path)
    # Every German website is gone, those of the catalog among them, and every file
    # that says what a project works with; the pictures are there.
    monkeypatch.setattr(hooks, "status", Websites())
    monkeypatch.setattr(hooks, "fetched", Files(drawing_files()))
    new = listed_repo("new-thing", f"{SITE}new-thing/")

    assert hooks.main(["--network", str(lists(tmp_path, *TODAY, new))], tmp_path) == 3

    output = capsys.readouterr()
    assert output.err == ""
    def german(slug: str) -> str:
        return (
            f"`{slug}`: the German website {SITE}{slug}/de/ is gone. Remove "
            "`docs.de`, so that the German home page leads to the English one."
        )

    def file(slug: str, name: str) -> str:
        return (
            f"`{slug}`: Dennis-Otto/{slug} has no {name} any more, from which its "
            f"card reads what it works with. {ADVICE}"
        )

    assert output.out == hooks.report(
        [
            german("homedarts-for-autodarts"),
            file("homedarts-for-autodarts", "hacs.json"),
            german("player-switch-for-autodarts"),
            german("paperless-sync"),
            file("paperless-sync", "appinfo/info.xml"),
            german("paperless-unified-search"),
            file("paperless-unified-search", "appinfo/info.xml"),
            german("repo-blueprint"),
            file("repo-blueprint", "copier.yml"),
            f"Dennis-Otto/new-thing has its website at {SITE}new-thing/, but "
            "projects.toml has no project for it. Add a `[[project]]` with "
            '`repo = "Dennis-Otto/new-thing"`.',
        ]
    )


@pytest.mark.parametrize(
    ("catalog", "items", "message"),
    [
        (True, None, "repositories.json"),
        (True, [], "The list of the repositories must be"),
        (False, [listed_repo("tool")], "projects.toml can't be read"),
    ],
)
def test_the_script_says_when_it_cant_tell(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    catalog: bool,
    items: list[dict[str, Any]] | None,
    message: str,
) -> None:
    if catalog:
        repository(tmp_path)
    if items is not None:
        lists(tmp_path, *items)

    path = tmp_path / "repositories.json"
    assert hooks.main(["--network", str(path)], tmp_path) == 2

    output = capsys.readouterr()
    assert output.out == ""
    assert message in output.err


def test_the_script_says_when_a_website_cant_be_reached(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    repository(tmp_path)

    def status(url: str) -> int:
        raise hooks.CheckError(f"{url} can't be reached: timed out")

    monkeypatch.setattr(hooks, "status", status)

    assert hooks.main(["--network", str(lists(tmp_path, *TODAY))], tmp_path) == 2
    assert capsys.readouterr() == (
        "",
        f"{SITE}homedarts-for-autodarts/de/ can't be reached: timed out\n",
    )


ADVICE = (
    "Correct `requires`, or write what the project works with into `requires` as a "
    "text in every language."
)


def test_the_bot_reads_what_a_project_works_with_on_its_default_branch() -> None:
    url = raw("Dennis-Otto/tool", "HEAD", "hacs.json")
    files = Files({url: HACS})

    assert drift(
        one_language(requires=source()),
        repositories=found(listed_repo("tool")),
        files=files,
    ) == []
    assert files.asked == [url]


def test_a_file_that_is_gone_from_the_default_branch_is_named() -> None:
    assert drift(
        one_language(requires=source()), repositories=found(listed_repo("tool"))
    ) == [
        "`tool`: Dennis-Otto/tool has no hacs.json any more, from which its card "
        f"reads what it works with. {ADVICE}"
    ]


def test_a_file_without_its_value_on_the_default_branch_is_named() -> None:
    url = raw("Dennis-Otto/tool", "HEAD", "appinfo/info.xml")
    files = Files({url: INFO.replace(b' max-version="35"', b"")})

    assert drift(
        one_language(requires=nextcloud()),
        repositories=found(listed_repo("tool")),
        files=files,
    ) == [
        "`tool`: appinfo/info.xml of Dennis-Otto/tool has no field "
        "dependencies/nextcloud@max-version, and its card reads what it works with "
        f"from there. {ADVICE}"
    ]


def test_the_bot_checks_the_files_from_which_the_hub_draws_a_picture() -> None:
    shot = raw("Dennis-Otto/tool", "HEAD", "docs/images/de/shot.png")
    logo = raw("Dennis-Otto/tool", "HEAD", "docs/logo.svg")
    files = Files({shot: b"RIFF"})

    assert drift(
        one_language(image=own_pictures(), drawing=drawing_data()),
        repositories=found(listed_repo("tool")),
        files=files,
    ) == [
        "`tool`: Dennis-Otto/tool has no docs/logo.svg any more, from which the hub "
        "draws a picture of its card. Correct `drawing` with a file of the "
        "repository."
    ]
    assert files.asked == [shot, logo]


def test_a_project_that_says_what_it_works_with_in_texts_has_no_file() -> None:
    files = Files()

    assert drift(
        one_language(requires={"en": "Any computer", "de": "Jeder Computer"}),
        repositories=found(listed_repo("tool")),
        files=files,
    ) == []
    assert files.asked == []


def test_a_file_comes_with_a_time_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    url = raw("Dennis-Otto/tool", "HEAD", "hacs.json")
    urlopen = Download(HACS)
    monkeypatch.setattr(hooks.urllib.request, "urlopen", urlopen)

    assert hooks.fetched(url) == HACS
    assert urlopen.requests == [(url, hooks.TIMEOUT)]


@pytest.mark.parametrize("code", [404, 410])
def test_a_file_that_is_gone_has_no_content(
    monkeypatch: pytest.MonkeyPatch, code: int
) -> None:
    url = raw("Dennis-Otto/tool", "HEAD", "hacs.json")
    error = hooks.urllib.error.HTTPError(
        url, code, "Gone", email.message.Message(), io.BytesIO(b"")
    )
    monkeypatch.setattr(hooks.urllib.request, "urlopen", Download(error))

    assert hooks.fetched(url) is None
    # The answer is closed, as an answer without an error is.
    assert error.fp.closed


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (
            hooks.urllib.error.HTTPError(
                "https://raw.githubusercontent.com/",
                503,
                "Unavailable",
                email.message.Message(),
                io.BytesIO(b""),
            ),
            "answers 503, where the catalog bot expects 200 or 404; start it again "
            "later.",
        ),
        (
            hooks.urllib.error.URLError("timed out"),
            "can't be reached: <urlopen error timed out>",
        ),
    ],
)
def test_a_file_that_cant_be_read_stops_the_bot(
    monkeypatch: pytest.MonkeyPatch, error: Exception, message: str
) -> None:
    url = raw("Dennis-Otto/tool", "HEAD", "hacs.json")
    monkeypatch.setattr(hooks.urllib.request, "urlopen", Download(error))

    with pytest.raises(hooks.CheckError) as stopped:
        hooks.fetched(url)

    assert str(stopped.value) == f"{url} {message}"


# The script.


def repository(root: Path) -> Path:
    """A copy of the catalog, with the pages of the former websites that it names,
    and of the README of this repository at root."""
    for name in ("projects.toml", "README.md"):
        shutil.copyfile(ROOT / name, root / name)
    shutil.copytree(ROOT / "former", root / "former")
    return root / "README.md"


def test_check_passes_when_the_table_is_current(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repository(tmp_path)

    assert hooks.main(["--check"], tmp_path) == 0
    assert capsys.readouterr().out == (
        "README.md has the current table of the projects of projects.toml.\n"
    )


def test_check_shows_a_table_edited_by_hand_and_the_command_that_fixes_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    readme = repository(tmp_path)
    text = readme.read_text(encoding="utf-8")
    edited = text.replace("local and in realtime", "für Dart")
    readme.write_text(edited, encoding="utf-8", newline="\n")

    assert hooks.main(["--check"], tmp_path) == 1

    output = capsys.readouterr()
    assert "--- README.md\n+++ README.md, from projects.toml\n" in output.out
    assert (
        "-| [homedarts-for-autodarts]"
        "(https://github.com/Dennis-Otto/homedarts-for-autodarts) | "
    ) in output.out
    tagline = "HomeDarts for Autodarts: Autodarts boards in Home Assistant, für Dart"
    assert f"| {tagline} |" in output.out
    assert output.err == (
        "README.md differs from projects.toml; write its table with\n"
        "  python3 -I .github/mkdocs_project.py --write\n"
    )
    assert readme.read_text(encoding="utf-8") == edited


def test_write_brings_the_table_up_to_date_once(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    readme = repository(tmp_path)
    text = readme.read_text(encoding="utf-8")
    start = text.index("<!-- projects:start -->") + len("<!-- projects:start -->")
    emptied = text[:start] + "\n" + text[text.index("<!-- projects:end") :]
    readme.write_text(emptied, encoding="utf-8", newline="\n")

    assert hooks.main(["--write"], tmp_path) == 0
    assert hooks.main(["--write"], tmp_path) == 0

    assert readme.read_bytes() == text.encode()
    assert capsys.readouterr().out == (
        "README.md has the table of the projects of projects.toml now.\n"
        "README.md has the current table of the projects of projects.toml.\n"
    )


def test_a_missing_german_text_fails_the_check(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repository(tmp_path)
    catalog = tmp_path / "projects.toml"
    text = catalog.read_text(encoding="utf-8")
    start = text.index('summary.de = "Die OCR')
    removed = text[:start] + text[text.index("\n", start) + 1 :]
    catalog.write_text(removed, encoding="utf-8", newline="\n")

    assert hooks.main(["--check"], tmp_path) == 1
    assert capsys.readouterr().err == (
        "projects.toml has 1 problem(s):\n"
        "  paperless-unified-search: summary.de is missing.\n"
        "The comments at the top of projects.toml describe every key.\n"
    )


def test_a_missing_readme_fails_the_check(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repository(tmp_path).unlink()

    assert hooks.main(["--write"], tmp_path) == 1
    assert "README.md" in capsys.readouterr().err


def test_the_script_needs_check_or_write(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as stop:
        hooks.main([])

    assert stop.value.code == 2
    assert (
        "one of the arguments --write --check --pictures --drawings --network --site "
        "is required"
        in capsys.readouterr().err
    )


def test_the_script_lists_the_pictures_for_the_script_that_makes_them(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Without a README, which the list doesn't need.
    repository(tmp_path).unlink()

    assert hooks.main(["--pictures"], tmp_path) == 0

    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == (
        "Dennis-Otto/homedarts-for-autodarts "
        "docs/images/projects/homedarts-for-autodarts.webp MIT"
    )
    assert lines[2] == (
        "Dennis-Otto/paperless-sync docs/images/projects/paperless-sync.webp "
        "AGPL-3.0-or-later"
    )
    assert len(lines) == 6


def test_a_broken_catalog_lists_no_pictures(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert hooks.main(["--pictures"], tmp_path) == 1

    output = capsys.readouterr()
    assert output.out == ""
    assert "projects.toml can't be read" in output.err


# A page of the drawn pictures with every placeholder of DRAWING.
TEMPLATE = "${lang}|${name}|${tagline}|${accent}|${logo}|${screenshot}"


def test_the_hub_writes_the_page_of_every_picture_that_it_draws(
    tmp_path: Path,
) -> None:
    # The tagline without the name, which the picture shows above it.
    tagline = {"en": "The tool: a tool", "de": "Das Werkzeug: Ein <Werkzeug> & mehr"}
    plain = entry("plain")
    board = without_repo(entry("board", image={"en": "b.png", "de": "de/b.png"}))
    catalog = hooks.read(catalog_data(drawn(tagline=tagline), plain, board))
    folder = tmp_path / "pages"

    listed = hooks.drawings(catalog, folder, TEMPLATE, None)

    assert listed == (
        "Dennis-Otto/tool docs/images/projects/de/tool.webp MIT "
        f"{folder.as_posix()}/tool.de.html "
        "https://raw.githubusercontent.com/Dennis-Otto/tool/HEAD/docs/images/de/shot.png "
        f"{folder.as_posix()}/tool.de.screenshot.png "
        "https://raw.githubusercontent.com/Dennis-Otto/tool/HEAD/docs/logo.svg "
        f"{folder.as_posix()}/tool.logo.svg\n"
    )
    assert (folder / "tool.de.html").read_text(encoding="utf-8") == (
        "de|Das Werkzeug|Ein &lt;Werkzeug&gt; &amp; mehr|#14b8a6|"
        '<img class="logo" src="tool.logo.svg" alt="">|tool.de.screenshot.png'
    )
    assert sorted(path.name for path in folder.iterdir()) == ["tool.de.html"]


def test_a_drawn_picture_without_a_logo_shows_the_icon_of_its_card(
    tmp_path: Path,
) -> None:
    write(tmp_path / "icons/material/tools.svg", "<svg>tools</svg>\n")
    drawing = drawing_data()
    del drawing["logo"]
    catalog = hooks.read(catalog_data(drawn(drawing=drawing)))

    listed = hooks.drawings(catalog, tmp_path / "pages", "${logo}", tmp_path / "icons")

    assert listed.split()[-2:] == ["-", "-"]
    assert (tmp_path / "pages/tool.de.html").read_text(encoding="utf-8") == (
        '<div class="logo icon"><svg>tools</svg></div>'
    )


def test_an_icon_of_a_set_with_styles_is_in_their_folders(tmp_path: Path) -> None:
    write(tmp_path / "fontawesome/brands/github.svg", "<svg>github</svg>")

    assert hooks.icon_svg("fontawesome-brands-github", tmp_path) == "<svg>github</svg>"


def test_an_icon_that_the_theme_lacks_is_named(tmp_path: Path) -> None:
    with pytest.raises(hooks.DrawingError) as error:
        hooks.icon_svg("material-nothing-here", tmp_path)

    assert str(error.value) == (
        f"Material for MkDocs has no icon material-nothing-here in {tmp_path}."
    )


def test_the_icons_come_from_the_theme_that_the_tools_of_the_website_install(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    theme = SimpleNamespace(__file__=str(tmp_path / "material" / "__init__.py"))
    monkeypatch.setitem(sys.modules, "material", theme)

    assert hooks.theme_icons() == tmp_path / "material" / "templates" / ".icons"


def test_without_the_tools_of_the_website_there_are_no_icons(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(sys.modules, "material", None)

    assert hooks.theme_icons() is None
    with pytest.raises(hooks.DrawingError) as error:
        hooks.icon_svg("material-tools", None)
    assert str(error.value) == (
        "Drawing the icon material-tools needs Material for MkDocs: set up the tools "
        "of the website in .venv-docs, as CONTRIBUTING.md describes."
    )


def test_the_script_writes_the_pages_of_the_pictures_that_the_hub_draws(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    repository(tmp_path).unlink()
    write(tmp_path / hooks.DRAWING, (ROOT / hooks.DRAWING).read_text(encoding="utf-8"))
    write(tmp_path / "icons/material/file-tree.svg", "<svg/>")
    monkeypatch.setattr(hooks, "theme_icons", lambda: tmp_path / "icons")
    monkeypatch.chdir(tmp_path)

    assert hooks.main(["--drawings", "pages"], tmp_path) == 0

    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 6
    assert lines[-1].split()[:4] == [
        "Dennis-Otto/repo-blueprint",
        "docs/images/projects/de/repo-blueprint.webp",
        "MIT-0",
        "pages/repo-blueprint.de.html",
    ]
    page = (tmp_path / "pages/repo-blueprint.de.html").read_text(encoding="utf-8")
    assert '<div class="logo icon"><svg/></div>' in page


def test_a_picture_that_the_hub_cannot_draw_stops_the_script(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    repository(tmp_path).unlink()
    write(tmp_path / hooks.DRAWING, TEMPLATE)
    monkeypatch.setattr(hooks, "theme_icons", lambda: None)
    monkeypatch.chdir(tmp_path)

    assert hooks.main(["--drawings", "pages"], tmp_path) == 1

    assert capsys.readouterr() == (
        "",
        "Drawing the icon material-file-tree needs Material for MkDocs: set up the "
        "tools of the website in .venv-docs, as CONTRIBUTING.md describes.\n",
    )


def test_a_card_without_a_repository_has_no_picture_to_make() -> None:
    board = without_repo(entry("board"))

    assert hooks.pictures(hooks.read(catalog_data(entry(), board))) == (
        "Dennis-Otto/tool docs/images/projects/tool.webp MIT\n"
    )


def test_the_script_writes_what_a_console_cannot_show_as_escapes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository(tmp_path)
    console = io.TextIOWrapper(io.BytesIO(), encoding="ascii")
    monkeypatch.setattr(sys, "stdout", console)
    monkeypatch.setattr(sys, "stderr", io.StringIO())

    assert hooks.main(["--check"], tmp_path) == 0
    assert console.errors == "backslashreplace"


def test_the_script_runs_as_a_program(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "argv", [str(HOOKS), "--check"])

    with pytest.raises(SystemExit) as stop:
        runpy.run_path(str(HOOKS), run_name="__main__")

    assert stop.value.code == 0
    assert "current table" in capsys.readouterr().out


def test_the_script_needs_the_standard_library_alone(tmp_path: Path) -> None:
    repository(tmp_path)
    script = tmp_path / ".github" / "mkdocs_project.py"
    script.parent.mkdir()
    shutil.copyfile(HOOKS, script)

    result = subprocess.run(
        [sys.executable, "-I", "-S", str(script), "--check"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )

    assert (result.returncode, result.stderr) == (0, "")
