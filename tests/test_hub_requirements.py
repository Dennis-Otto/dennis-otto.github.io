"""Tests of .github/hub/requirements.py: what a project works with, from the
catalog and from a file of its repository.
"""

from __future__ import annotations

import json
import logging
from dataclasses import replace
from pathlib import PurePosixPath
from types import SimpleNamespace
from typing import Any

import pytest

import hub.address
import hub.catalog
import hub.reader
import hub.releases
import hub.render
import hub.requirements
import hub.web
from hub_helpers import (
    FIXTURES,
    HACS,
    HTML,
    INFO,
    LD_JSON,
    ROOT,
    SITE,
    build,
    catalog_data,
    entry,
    hooks,
    nextcloud,
    page,
    page_at,
    problems,
    raw,
    release,
    source,
    without_repo,
)

COPIER = (FIXTURES / "copier.yml").read_bytes()


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
    catalog = hub.reader.load(ROOT)

    for project in catalog.projects:
        assert (project.requires is None) == (project.repo is None), project.slug
    assert catalog.requirements.label == {
        "en": "Works with {}",
        "de": "Funktioniert mit {}",
    }


def test_the_files_of_the_catalog_hold_what_their_projects_work_with() -> None:
    catalog = hub.reader.load(ROOT)
    works = {
        project.slug: hub.requirements.values_in(
            project.requires,
            (FIXTURES / PurePosixPath(project.requires.file).name).read_bytes(),
        )
        for project in catalog.projects
        if isinstance(project.requires, hub.catalog.Source)
    }

    assert works == {
        "homedarts-for-autodarts": {"": "2026.8.0"},
        "player-switch-for-autodarts": {"chrome": "140", "firefox": "140.0"},
        "paperless-sync": {"min": "33", "max": "35"},
        "paperless-unified-search": {"min": "33", "max": "35"},
        "repo-blueprint": {"": "9.8"},
    }


def test_the_card_of_player_switch_names_each_browser_with_its_oldest_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Its manifest at v1.3.0 names the oldest Chrome, which Edge follows, and the
    # oldest Firefox: two fields of one file, the second deep in its keys.
    catalog = hub.reader.load(ROOT)
    slug = "player-switch-for-autodarts"
    project = next(project for project in catalog.projects if project.slug == slug)
    url = raw(str(project.repo), "v1.3.0", "extension/manifest.json")
    manifest = (FIXTURES / "manifest.json").read_bytes()
    monkeypatch.setattr(hub.web, "download", files({url: manifest}, []))

    works = hub.requirements.requirements(
        replace(catalog, projects=(project,)),
        {str(project.repo): (release("v1.3.0", "2026-11-07"),)},
    )

    assert works == {
        "player-switch-for-autodarts": {
            "en": "Chrome or Edge 140 or newer and Firefox 140.0 or newer, on the "
            "desktop",
            "de": "Chrome oder Edge 140 oder neuer und Firefox 140.0 oder neuer, auf "
            "dem Desktop",
        }
    }


def test_a_project_may_say_what_it_works_with_in_every_language() -> None:
    requires = {"en": "Any computer", "de": "Jeder Computer"}

    catalog = hub.reader.read(catalog_data(entry(requires=requires)))

    assert catalog.projects[0].requires == requires
    assert catalog.requirements == hub.catalog.Link(
        "material-puzzle", {"en": "Works with {}", "de": "Läuft mit {}"}, {}
    )


def test_a_project_may_read_what_it_works_with_from_a_file_of_its_repository() -> None:
    catalog = hub.reader.read(
        catalog_data(entry(requires=source()), entry("two", requires=nextcloud()))
    )

    assert [project.requires for project in catalog.projects] == [
        hub.catalog.Source(
            "hacs.json",
            {"": "homeassistant"},
            {"en": "Home Assistant {} or newer", "de": "Home Assistant {} oder neuer"},
        ),
        hub.catalog.Source(
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
    found = hub.requirements.values_in(
        hub.catalog.Source(file, {"": field}, {}), content
    )

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
    with pytest.raises(hub.requirements.RequirementError) as error:
        hub.requirements.values_in(hub.catalog.Source(file, {"": field}, {}), content)

    assert str(error.value).startswith(message)


def test_the_build_reads_what_a_project_works_with_from_its_latest_release(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asked: list[str] = []
    answers: dict[str, bytes | Exception] = {
        raw("Dennis-Otto/tool", "v2.0.1", "hacs.json"): HACS,
        raw("Dennis-Otto/two", "v1.2.0", "appinfo/info.xml"): INFO,
    }
    monkeypatch.setattr(hub.web, "download", files(answers, asked))
    catalog = hub.reader.read(
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

    assert hub.requirements.requirements(catalog, notes) == {
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
    monkeypatch.setattr(hub.web, "download", files({url: newer}, []))
    catalog = hub.reader.read(catalog_data(entry(requires=source())))
    works = hub.requirements.requirements(
        catalog, {"Dennis-Otto/tool": (release("v2.1.0", "2026-10-24"),)}
    )

    section = hub.render.section(catalog, catalog.groups[0], "de", {}, works)

    assert (
        '<p class="project-requires" markdown>:material-puzzle: Läuft mit Home '
        "Assistant 2026.10.1 oder neuer</p>"
    ) in section


def test_a_file_that_cant_be_read_leaves_the_line_off_the_card(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    gone = hub.web.SearchError(
        f"{raw('Dennis-Otto/gone', 'v1.0.0', 'hacs.json')} can't be downloaded: "
        "HTTP Error 404: Not Found"
    )
    answers: dict[str, bytes | Exception] = {
        raw("Dennis-Otto/gone", "v1.0.0", "hacs.json"): gone,
        raw("Dennis-Otto/moved", "v1.0.0", "hacs.json"): b'{"name": "Moved"}',
    }
    monkeypatch.setattr(hub.web, "download", files(answers, []))
    caplog.set_level(logging.INFO, logger="mkdocs.hooks.project")
    catalog = hub.reader.read(
        catalog_data(
            *(entry(slug, requires=source()) for slug in ("gone", "moved", "new"))
        )
    )
    notes = {
        "Dennis-Otto/gone": (release("v1.0.0", "2026-10-01"),),
        "Dennis-Otto/moved": (release("v1.0.0", "2026-10-01"),),
        "Dennis-Otto/new": (),
    }

    assert hub.requirements.requirements(catalog, notes) == {}
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
    monkeypatch.setattr(hub.web, "download", files({url: HACS}, asked))
    catalog = hub.reader.read(catalog_data(entry(requires=source())))
    notes = {"Dennis-Otto/tool": (release("v2.0.1", "2026-10-20"),)}
    settings = SimpleNamespace(
        extra={"catalog": catalog, hub.render.LEVEL: {}, hub.releases.NOTES: notes}
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
    monkeypatch.setattr(hub.web, "download", lambda url: pytest.fail(str(url)))
    requires = {"en": "Any computer", "de": "Jeder Computer"}
    catalog = hub.reader.read(catalog_data(entry(requires=requires)))
    settings = SimpleNamespace(extra={"catalog": catalog, hub.render.LEVEL: {}})

    markdown = hooks.on_page_markdown("<!-- projects -->\n", page("en"), settings, None)

    assert "Works with Any computer</p>" in markdown
    assert hub.releases.NOTES not in settings.extra


def test_the_line_of_what_a_project_works_with_stands_right_above_the_buttons() -> None:
    catalog = hub.reader.read(
        catalog_data(entry(requires={"en": "Any computer", "de": "Jeder Computer"}))
    )
    project = catalog.projects[0]
    assert isinstance(project.requires, dict)

    line = hub.render.requirement(catalog, project, "de", {"tool": project.requires})
    parts = hub.render.card(project, "de", None, "<div>live</div>", line).split("\n\n")

    assert line == (
        '<p class="project-requires" markdown>:material-puzzle: Läuft mit Jeder '
        "Computer</p>"
    )
    # Below the facts, and right above the buttons at the foot of the card.
    assert parts[4:6] == ["<div>live</div>", line]
    assert parts[6].startswith("[:material-download: Installieren]")


def test_a_card_without_what_its_project_works_with_has_no_line() -> None:
    catalog = hub.reader.read(catalog_data(entry(requires=source())))

    assert hub.render.requirement(catalog, catalog.projects[0], "en", {}) == ""
    assert "project-requires" not in hub.render.section(
        catalog, catalog.groups[0], "en"
    )


def test_the_table_says_what_every_project_works_with() -> None:
    catalog = hub.reader.read(
        catalog_data(
            entry(requires=source()),
            entry("two", requires=nextcloud(), platform="Nextcloud"),
            entry("three", requires={"en": "Linux | macOS", "de": "Linux"}),
            entry("four"),
        )
    )

    rows = hub.render.table(catalog, "en").splitlines()

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
    catalog = hub.reader.read(catalog_data(entry(), entry("two", platform="Nextcloud")))
    works = {"tool": {"en": "Home Assistant 2026.8.0 or newer", "de": "neuer"}}

    head = hub.address.structured_data(catalog, SITE, "Site", works)

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
    settings.extra[hub.requirements.WORKS] = {
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
        "Chrome, Edge, Firefox",
        "Nextcloud 33 to 35 and Paperless-ngx",
        "Nextcloud",
        "GitHub Actions",
        "Cloudflare Workers",
        "Copier",
    ]
