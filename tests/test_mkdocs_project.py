"""Tests of the hooks of the website and of the script of the README table,
.github/mkdocs_project.py, with fakes of MkDocs in its place."""

from __future__ import annotations

import importlib.util
import io
import gzip
import json
import logging
import os
import re
import runpy
import shutil
import subprocess
import sys
import tomllib
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

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
        "icon": "material-tools",
        "name": {"en": "The tool", "de": "Das Werkzeug"},
        "tagline": {"en": "A tool", "de": "Ein Werkzeug"},
        "summary": {"en": "It does things.", "de": "Es tut Dinge."},
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


def without_repo(project: dict[str, Any]) -> dict[str, Any]:
    """project without its repository, such as the dashboard, and so without the
    keys that go with it."""
    for key in ("repo", "license", "platform"):
        del project[key]
    return project


def catalog_data(*projects: object) -> dict[str, Any]:
    """The tables of a projects.toml with projects, or a single one; a project that
    is no table tests the reader."""
    return {
        "languages": ["en", "de"],
        "documentation": {
            "icon": "material-book",
            "label": {"en": "Documentation", "de": "Dokumentation"},
        },
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
        "ha-autodarts",
        "paperless-sync",
        "paperless-unified-search",
        "issue-assistant",
        "repo-blueprint",
        "dashboard",
    ]
    for project in catalog.projects:
        for texts in (project.name, project.tagline, project.summary):
            assert set(texts) == {"en", "de"}


def test_the_german_blueprint_button_leads_to_the_german_section() -> None:
    blueprint = {project.slug: project for project in hooks.load(ROOT).projects}[
        "repo-blueprint"
    ]

    assert blueprint.start.url == {
        "en": "https://github.com/Dennis-Otto/repo-blueprint#start-a-repository",
        "de": "https://github.com/Dennis-Otto/repo-blueprint/blob/main/README.de.md"
        "#ein-repository-anlegen",
    }


def test_the_dashboard_has_no_repository_and_no_documentation() -> None:
    dashboard = hooks.load(ROOT).projects[-1]

    assert dashboard.repo is None
    assert dashboard.docs is None


def test_both_home_pages_have_the_marker_of_the_cards_once() -> None:
    for page in ("docs/index.md", "docs/index.de.md"):
        markdown = (ROOT / page).read_text(encoding="utf-8")
        assert len(hooks.MARKER_LINE.findall(markdown)) == 1, page


def test_the_cards_follow_a_heading_of_the_second_level() -> None:
    # The headings of the cards are of the third level; a screen reader lists them
    # under the heading of the projects, with no level left out after the title.
    for page in ("docs/index.md", "docs/index.de.md"):
        markdown = (ROOT / page).read_text(encoding="utf-8")
        marker = hooks.MARKER_LINE.search(markdown)
        assert marker is not None, page
        before = markdown[: marker.start()].splitlines()
        headings = [line for line in before if line.startswith("#")]
        assert headings[-1].startswith("## "), page


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
        "ha-autodarts": ("MIT", "Home Assistant"),
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


def test_the_404_page_links_every_project_absolutely() -> None:
    # GitHub Pages serves the page at any depth, where a relative link leads nowhere.
    template = (ROOT / "overrides" / "404.html").read_text(encoding="utf-8")

    assert '{% extends "main.html" %}' in template
    # The heading in both languages, like every sentence of the page.
    assert '<h1>Page not found <span lang="de">· Seite nicht gefunden</span></h1>' in (
        template
    )
    assert "{% for project in catalog.projects %}" in template
    assert "{{ catalog.directory() | tojson }}" in template
    assert re.findall(r'href="([^"]*)"', template) == [
        "{{ project.website[catalog.default] }}",
        "{{ config.site_url }}",
        "{{ config.site_url }}de/",
    ]


def test_the_policy_of_security_txt_is_a_page_of_the_website() -> None:
    assert hooks.POLICY == "security.html"
    assert (ROOT / "docs" / "security.md").is_file()


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
    project = entry("ha-autodarts")
    del project["summary"]["de"]

    assert problems(catalog_data(project)) == ["ha-autodarts: summary.de is missing."]


def test_every_problem_of_the_catalog_is_named_at_once() -> None:
    first = entry("one", icon="Material Tools", sumary="typo")
    first["name"] = "Only English"
    second = entry("two", repo="two", docs={"de": "http://example.org"})
    second["start"]["label"]["fr"] = "Installer"
    data = catalog_data(first, second)
    data["colors"] = "blue"

    assert problems(data) == [
        "colors is unknown; known are languages, documentation, project.",
        "one: sumary is unknown; known are slug, repo, license, platform, icon, "
        "name, tagline, summary, start, docs.",
        "one: icon must be an icon of Material for MkDocs, such as material-download,"
        " not 'Material Tools'.",
        "one: name needs a text in every language: name.en, name.de.",
        "two: repo must be a repository on GitHub, such as Dennis-Otto/ha-autodarts,"
        " not 'two'.",
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

    bad = entry("Bad Slug", repo="Dennis-Otto/bad", docs="https://example.org/")

    assert problems(catalog_data(entry(), "tool", nameless, bad)) == [
        "project 2 must be a table.",
        "project 3: slug is missing.",
        "project 4: slug must be lowercase letters, digits and hyphens, such as "
        "ha-autodarts, not 'Bad Slug'.",
    ]


@pytest.mark.parametrize("projects", [None, [], {"slug": "tool"}])
def test_the_catalog_must_list_projects(projects: object) -> None:
    data = catalog_data()
    data["project"] = projects

    assert problems(data) == [
        "project must list the projects as [[project]] tables.",
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


def test_a_card_has_a_heading_with_an_anchor_and_both_buttons() -> None:
    catalog = hooks.read(catalog_data())

    assert hooks.card(catalog.projects[0], "de") == "\n\n".join(
        [
            '<div class="card" markdown>',
            "### :material-tools:{ .lg .middle } Das Werkzeug { #tool }",
            "---",
            "Es tut Dinge.",
            "[:material-download: Installieren](https://example.org/install)"
            "{ .md-button .md-button--primary }\n"
            "[:material-book: Dokumentation](https://dennis-otto.github.io/tool/de/)"
            "{ .md-button }",
            "</div>",
        ]
    )


def test_a_card_without_documentation_has_one_button() -> None:
    project = entry()
    del project["docs"]

    card = hooks.card(hooks.read(catalog_data(project)).projects[0], "en")

    assert card.count("](") == 1
    assert "[:material-download: Install](https://example.org/install)" in card


def test_the_cards_of_every_project_stand_in_one_grid() -> None:
    catalog = hooks.read(catalog_data(entry("one"), entry("two")))

    cards = hooks.cards(catalog, "en")

    assert cards.startswith(
        '<div class="grid" markdown>\n\n<div class="card" markdown>'
    )
    assert cards.endswith("</div>\n\n</div>")
    assert cards.count('<div class="card" markdown>') == 2
    assert cards.index("{ #one }") < cards.index("{ #two }")


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
            "| Project | What it does | Start | Website |",
            "| --- | --- | --- | --- |",
            "| [tool](https://github.com/Dennis-Otto/tool) | A tool "
            "| [Install](https://example.org/install) "
            "| [dennis-otto.github.io/tool](https://dennis-otto.github.io/tool/) · "
            "[dennis-otto.github.io/tool/de](https://dennis-otto.github.io/tool/de/) |",
            "| [plain](https://github.com/Dennis-Otto/plain) | Yes \\| no "
            "| [Get \\| it](https://example.org/install) | — |",
            "| The board | A tool "
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
    """A repository at root with this catalog and the pages of its documentation."""
    shutil.copyfile(ROOT / "projects.toml", root / "projects.toml")
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
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
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
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
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
        extra={"catalog": hooks.load(ROOT)},
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


def test_robots_of_the_address_lists_the_sitemaps_of_all_six_websites() -> None:
    lines = hooks.robots(hooks.load(ROOT), SITE).splitlines()

    assert [line for line in lines if line.startswith("Sitemap:")] == [
        f"Sitemap: {SITE}sitemap.xml",
        f"Sitemap: {SITE}ha-autodarts/sitemap.xml",
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


def test_the_404_page_gets_the_name_and_the_website_of_every_project() -> None:
    catalog = hooks.load(ROOT)

    directory = catalog.directory()

    assert [item["slug"] for item in directory] == [p.slug for p in catalog.projects]
    assert directory[0] == {
        "slug": "ha-autodarts",
        "name": {
            "en": "Autodarts for Home Assistant",
            "de": "Autodarts für Home Assistant",
        },
        "url": {
            "en": "https://dennis-otto.github.io/ha-autodarts/",
            "de": "https://dennis-otto.github.io/ha-autodarts/de/",
        },
    }
    # The dashboard has no documentation; its button leads to it.
    assert directory[-1]["url"] == dict.fromkeys(
        ("en", "de"), "https://dennis-otto.github.io/repo-blueprint/dashboard/"
    )
    for item in directory:
        assert all(url.startswith("https://") for url in item["url"].values())
    # The template gives it to the script as JSON.
    assert json.loads(json.dumps(directory)) == directory


# The script of the 404 page, which suggests a project for a mistyped address. It
# runs in Node.js, with a stand-in for the page. The runners of the CI have Node.js;
# a computer without it leaves these tests, and their lines, to the CI.
NODE = shutil.which("node")
needs_node = pytest.mark.skipif(
    NODE is None and not os.environ.get("CI"),
    reason="Node.js is not installed here; the CI runs the script of the 404 page.",
)
PAGE = """
class Element {
  constructor() {
    this.children = [];
  }
  append(...children) {
    this.children.push(...children);
  }
}
const box = new Element();
const document = {
  createElement: () => new Element(),
  getElementById: (id) => (id === "did-you-mean" ? box : null),
};
"""


def suggestion(  # pragma: no cover - needs Node.js
    path: str, projects: list[dict[str, Any]] | None = None
) -> dict[str, str]:
    """What the 404 page suggests at path, the projects of the catalog or projects:
    its question in each language, with every link as [name](url); nothing when it
    suggests nothing."""
    template = (ROOT / "overrides" / "404.html").read_text(encoding="utf-8")
    script = re.search(r"<script>(.*?)</script>", template, re.DOTALL)
    assert script is not None
    directory = hooks.load(ROOT).directory() if projects is None else projects
    code = script.group(1).replace(
        "{{ catalog.directory() | tojson }}", json.dumps(directory)
    )
    assert code != script.group(1)
    run = subprocess.run(
        [str(NODE)],
        input=f"const location = {{ pathname: {json.dumps(path)} }};\n{PAGE}{code}\n"
        "console.log(JSON.stringify(box));\n",
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    box = json.loads(run.stdout)
    if not box["children"]:
        assert "className" not in box
        return {}
    assert box["className"] == "admonition question"
    english, german = box["children"]
    assert english["className"] == "admonition-title"
    return {
        line["lang"]: "".join(
            part
            if isinstance(part, str)
            else f"[{part['textContent']}]({part['href']})"
            for part in line["children"]
        )
        for line in (english, german)
    }


@needs_node
@pytest.mark.parametrize(
    "path", ["/autodarts/", "/Autodarts", "/ha-autodarts-v1/x.html"]
)
def test_the_404_page_suggests_the_project_like_the_address(  # pragma: no cover
    path: str,
) -> None:
    assert suggestion(path) == {
        "en": f"Did you mean [Autodarts for Home Assistant]({SITE}ha-autodarts/)?",
        "de": f"Meintest du [Autodarts für Home Assistant]({SITE}ha-autodarts/de/)?",
    }


@needs_node
@pytest.mark.parametrize(
    ("path", "slugs"),
    [
        ("/paperless/", ["paperless-sync", "paperless-unified-search"]),
        ("/search/", ["paperless-unified-search"]),
        ("/blueprint/", ["repo-blueprint"]),
        ("/dashbord/", ["dashboard"]),
        ("/issue-asistant/", ["issue-assistant"]),
    ],
)
def test_the_404_page_suggests_a_project_by_a_word_or_a_typo(  # pragma: no cover
    path: str, slugs: list[str]
) -> None:
    projects = {project.slug: project for project in hooks.load(ROOT).projects}
    links = [
        f"[{projects[slug].name['en']}]({projects[slug].website['en']})"
        for slug in slugs
    ]

    assert suggestion(path)["en"] == f"Did you mean {' or '.join(links)}?"


@needs_node
def test_the_404_page_suggests_the_closest_project_first() -> None:  # pragma: no cover
    projects = [
        {"slug": slug, "name": {"en": slug, "de": slug}, "url": {"en": url, "de": url}}
        for slug, url in [
            ("ketchup", "https://example.org/ketchup/"),
            ("kitten", "https://example.org/kitten/"),
            ("kitchen", "https://example.org/kitchen/"),
        ]
    ]

    # 1, 2 and 3 letters differ.
    assert suggestion("/kitchn/", projects) == {
        "en": "Did you mean [kitchen](https://example.org/kitchen/), "
        "[kitten](https://example.org/kitten/) or "
        "[ketchup](https://example.org/ketchup/)?",
        "de": "Meintest du [kitchen](https://example.org/kitchen/), "
        "[kitten](https://example.org/kitten/) oder "
        "[ketchup](https://example.org/ketchup/)?",
    }


@needs_node
@pytest.mark.parametrize(
    "path", ["/", "/a/", "/xyz/", "/de/foo.html", "/impressum.html", "/%E0%A4%A/"]
)
def test_the_404_page_suggests_nothing_unlike_a_project(  # pragma: no cover
    path: str,
) -> None:
    assert suggestion(path) == {}


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
    assert projects["numberOfItems"] == 5
    elements = projects["itemListElement"]
    assert [element["position"] for element in elements] == [1, 2, 3, 4, 5]
    items = [element["item"] for element in elements]
    assert {item["@type"] for item in items} == {"SoftwareSourceCode"}
    assert [item["@id"] for item in items] == [
        f"{SITE}#ha-autodarts",
        f"{SITE}#paperless-sync",
        f"{SITE}#paperless-unified-search",
        f"{SITE}#issue-assistant",
        f"{SITE}#repo-blueprint",
    ]
    assert items[1] == {
        "@type": "SoftwareSourceCode",
        "@id": f"{SITE}#paperless-sync",
        "name": "Paperless Sync",
        "description": hooks.load(ROOT).projects[1].summary["en"],
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
    "dest_uri", ["de/index.html", "security.html", "decisions/README.html"]
)
def test_no_other_page_gets_the_structured_data(dest_uri: str) -> None:
    page = page_at(dest_uri, title="Open-Source-Apps")

    assert hooks.on_post_page(HTML, page, build()) == HTML


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


# The script.


def repository(root: Path) -> Path:
    """A copy of the catalog and the README of this repository at root."""
    for name in ("projects.toml", "README.md"):
        shutil.copyfile(ROOT / name, root / name)
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
    assert "-| [ha-autodarts](https://github.com/Dennis-Otto/ha-autodarts) | " in (
        output.out
    )
    assert "| Autodarts for Home Assistant, für Dart |" in output.out
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
    assert "one of the arguments --write --check is required" in capsys.readouterr().err


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
