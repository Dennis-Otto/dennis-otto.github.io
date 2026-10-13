"""Tests of the hooks of the website and of the script of the README table,
.github/mkdocs_project.py, with fakes of MkDocs in its place."""

from __future__ import annotations

import importlib.util
import io
import logging
import runpy
import shutil
import subprocess
import sys
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


def test_the_readme_of_the_repository_has_the_table_of_the_catalog() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")

    assert hooks.readme(text, hooks.load(ROOT)) == text


def test_the_pages_of_the_repository_have_their_translations(
    caplog: pytest.LogCaptureFixture,
) -> None:
    hooks.check_pages(ROOT / "docs", [language("en"), language("de")])

    assert caplog.messages == []


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
    project = entry()
    del project["repo"], project["docs"]

    read = hooks.read(catalog_data(project)).projects[0]

    assert read.repo is None
    assert read.docs is None


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
        "one: sumary is unknown; known are "
        "slug, repo, icon, name, tagline, summary, start, docs.",
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


def test_the_table_lists_the_projects_with_a_repository() -> None:
    plain = entry("plain", tagline={"en": "Yes | no", "de": "Ja | nein"})
    del plain["docs"]
    dashboard = entry("dashboard")
    del dashboard["repo"]
    catalog = hooks.read(catalog_data(entry("tool"), plain, dashboard))

    assert hooks.table(catalog) == "\n".join(
        [
            "| Project | What it does | Website |",
            "| --- | --- | --- |",
            "| [tool](https://github.com/Dennis-Otto/tool) | A tool "
            "| [dennis-otto.github.io/tool](https://dennis-otto.github.io/tool/) |",
            "| [plain](https://github.com/Dennis-Otto/plain) | Yes \\| no | — |",
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
