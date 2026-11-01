"""Tests of .github/hub/render.py: the cards of the home pages, the Trust page and the
tables of the READMEs.
"""

from __future__ import annotations

import json
import logging
import re
from html import escape
from types import SimpleNamespace
from typing import Any

import pytest

import hub.catalog
import hub.reader
import hub.render
import hub.web
from hub_helpers import (
    ROOT,
    VALUED_ROWS,
    catalog_data,
    drawn,
    entry,
    group_data,
    hooks,
    in_french,
    language,
    page,
    section,
    without_repo,
)

# The cards of the home page.


def test_a_card_has_a_picture_a_heading_with_an_anchor_and_both_buttons() -> None:
    catalog = hub.reader.read(catalog_data())
    project = catalog.projects[0]

    assert hub.render.card(project, "de", catalog.second(project)) == "\n\n".join(
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
    catalog = hub.reader.read(catalog_data(entry(former=["old-tool", "older-tool"])))
    project = catalog.projects[0]

    card = hub.render.card(project, "en", catalog.second(project))

    assert (
        '### <span id="old-tool"></span><span id="older-tool"></span>'
        ":material-tools:{ .lg .middle } "
        "[The tool](https://dennis-otto.github.io/tool/) { #tool }"
    ) in card.split("\n\n")


def test_a_card_without_a_second_button_has_one_button() -> None:
    project = entry()
    del project["docs"]

    card = hub.render.card(
        hub.reader.read(catalog_data(project)).projects[0], "en", None
    )

    assert card.count("{ .md-button") == 1
    assert "[:material-download: Install](https://example.org/install)" in card
    # The heading links the website, which is where the first button leads.
    assert "[The tool](https://example.org/install) { #tool }" in card


def test_a_card_without_a_picture_starts_with_its_heading() -> None:
    project = hub.reader.read(catalog_data()).projects[0]
    plain = hub.catalog.Project(**{**project.__dict__, "picture": None})

    card = hub.render.card(plain, "en", None)

    assert card.split("\n\n")[1].startswith("### ")
    assert "![" not in card


def test_a_card_shows_the_picture_of_the_language_of_its_page() -> None:
    project = hub.reader.read(catalog_data(drawn())).projects[0]

    assert "](images/projects/tool.webp){" in hub.render.card(project, "en", None)
    assert "](images/projects/de/tool.webp){" in hub.render.card(project, "de", None)


def test_the_pictures_of_the_first_group_load_at_once_the_first_before_all() -> None:
    # The first row of cards is in view as the page opens, and its first picture is
    # the largest paint of the page; the other groups are further down.
    data = catalog_data(entry("one"), entry("two"), entry("three", group="more"))
    data["group"].append(group_data("more"))

    markdown = hub.render.cards(hub.reader.read(data), "en")

    # Each says how it loads, so that the hook of the blueprint that makes every
    # picture of a page but its first wait leaves it as it is.
    assert re.findall(r'\{ width="640" height="320" (.*?) \.off-glb \}', markdown) == [
        'loading="eager" fetchpriority="high"',
        'loading="eager"',
        'loading="lazy"',
    ]


def test_no_picture_of_the_first_row_of_the_home_page_waits() -> None:
    catalog = hub.reader.load(ROOT)
    first, *others = catalog.groups

    for language in catalog.languages:
        top = hub.render.section(catalog, first, language, first=True)
        assert top.count('loading="eager"') == len(catalog.members(first))
        assert top.count('fetchpriority="high"') == 1
        for group in others:
            below = hub.render.section(catalog, group, language)
            assert below.count('loading="lazy"') == len(catalog.members(group))


def test_a_card_escapes_brackets_in_its_texts() -> None:
    # A bracket or a backslash would end or change the link or the picture.
    project = entry(name={"en": "The [new] tool", "de": r"Das \ Werkzeug"})
    project["alt"]["en"] = "A [beta] screen"
    project["start"]["label"]["en"] = "Get [it]"

    catalog = hub.reader.read(catalog_data(project))
    english = hub.render.card(catalog.projects[0], "en", None)
    german = hub.render.card(catalog.projects[0], "de", None)

    assert r"![A \[beta\] screen](" in english
    assert r"[The \[new\] tool](" in english
    assert r"[:material-download: Get \[it\]](" in english
    assert r"[Das \\ Werkzeug](" in german


def test_a_group_has_its_heading_its_cards_and_its_note() -> None:
    note = {"en": "They work together.", "de": "Sie arbeiten zusammen."}
    data = catalog_data(entry("one"), entry("two"))
    data["group"][0]["note"] = note
    catalog = hub.reader.read(data)

    section = hub.render.section(catalog, catalog.groups[0], "de")

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
    catalog = hub.reader.read(data)

    cards = hub.render.cards(catalog, "en")

    assert cards.startswith('<div class="projects" id="projects" data-facts="')
    assert " markdown>\n\n## Tools { #tools }" in cards
    assert cards.endswith("</div>\n\n</div>\n\n</div>")
    assert cards.index("{ #tools }") < cards.index("{ #one }")
    assert cards.index("{ #one }") < cards.index("{ #more }")
    assert cards.index("{ #more }") < cards.index("{ #two }")
    assert '<p class="note"' not in cards


def test_both_languages_show_the_same_projects_in_the_same_groups() -> None:
    catalog = hub.reader.load(ROOT)
    anchors = re.compile(r"\{ #([a-z0-9-]+) \}")

    english = anchors.findall(hub.render.cards(catalog, "en"))
    german = anchors.findall(hub.render.cards(catalog, "de"))

    assert (
        english
        == german
        == [
            "home-and-archive",
            "homedarts-for-autodarts",
            "player-switch-for-autodarts",
            "paperless-sync",
            "paperless-unified-search",
            "maintainers",
            "issue-assistant",
            "repo-blueprint",
        ]
    )


def test_the_live_facts_stand_between_the_summary_and_the_buttons() -> None:
    project = hub.reader.read(catalog_data()).projects[0]

    parts = hub.render.card(project, "en", None, "<div>live</div>").split("\n\n")

    # The buttons stand at the foot of the card, the facts above them.
    assert parts[3:5] == ["It does things.", "<div>live</div>"]
    assert parts[5].startswith("[:material-download: Install]")


def test_every_card_with_a_repo_names_the_level_of_its_best_practices() -> None:
    catalog = hub.reader.read(catalog_data(entry(bestpractices=14935), entry("two")))

    section = hub.render.section(catalog, catalog.groups[0], "de", {14935: "silver"})

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
    catalog = hub.reader.read(catalog_data(entry(bestpractices=14935)))

    assert hub.render.facts(catalog, catalog.projects[0], "en", {}) == (
        '<div class="project-facts" data-repo="Dennis-Otto/tool"'
        ' data-name="The tool"></div>'
    )


def test_a_card_without_a_repo_has_no_facts() -> None:
    catalog = hub.reader.read(catalog_data(without_repo(entry())))

    assert "project-facts" not in hub.render.section(catalog, catalog.groups[0], "en")


def test_the_facts_escape_their_texts() -> None:
    project = entry(name={"en": 'The "best" <tool> & co', "de": "Das Werkzeug"})
    data = catalog_data(project | {"bestpractices": 1})
    data["facts"]["label"]["en"] = 'Facts "now"'
    data["facts"]["gold"]["en"] = "<gold> & more"
    catalog = hub.reader.read(data)

    facts = hub.render.facts(catalog, catalog.projects[0], "en", {1: "gold"})

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
        (5, hub.web.SearchError("https://www.bestpractices.dev/projects/5.json: 503")),
        (6, b"<html>"),
        (7, ["silver"]),
    )
    monkeypatch.setattr(hub.web, "download", download)
    caplog.set_level(logging.INFO, logger="mkdocs.hooks.project")

    levels = hub.render.best_practices(hub.reader.read(catalog_data(*projects)))

    assert levels == {1: "passing", 2: "silver", 3: "gold"}
    # Without a warning, which would fail the strict build while the website is away.
    assert {record.levelno for record in caplog.records} == {logging.INFO}
    assert len(caplog.records) == 4


def test_the_build_asks_for_no_level_without_a_project_at_bestpractices_dev(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(hub.web, "download", lambda url: pytest.fail(url))

    assert hub.render.best_practices(hub.reader.read(catalog_data())) == {}


def test_the_levels_are_read_once_for_every_language(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asked: list[str] = []

    def download(url: str) -> bytes:
        asked.append(url)
        return b'{"badge_level": "silver"}'

    monkeypatch.setattr(hub.web, "download", download)
    catalog = hub.reader.read(catalog_data(entry(bestpractices=14935)))
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
    catalog = hub.reader.read(data)

    first = hub.render.cards(catalog, language).split("\n", 1)[0]

    texts = {key: catalog.facts[key][language] for key in hub.catalog.SCRIPT}
    texts["label"] = "Facts &quot;now&quot;"
    assert first == (
        '<div class="projects" id="projects"'
        ' data-facts="/repo-blueprint/dashboard/repos.json"'
        ' data-history="/repo-blueprint/dashboard/history.json"'
        f' data-locale="{language}"'
        + "".join(f' data-{key}="{text}"' for key, text in texts.items())
        + " markdown>"
    )


def trust_catalog() -> Any:
    """A catalog with two projects with a repo, the first with its short name, its
    project at bestpractices.dev and the file that its users install, and a third
    without a repo."""
    short = {"en": "Tool", "de": "Werkzeug"}
    return hub.reader.read(
        catalog_data(
            entry(short=short, bestpractices=1, asset="tool.zip"),
            entry("two", bestpractices=2),
            without_repo(entry("site")),
        )
    )


def test_the_guarantees_that_every_project_shares_are_listed_once() -> None:
    shared = hub.render.shared_guarantees(trust_catalog(), "en")

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
    shared = hub.render.shared_guarantees(trust_catalog(), "de")

    assert "<div><dt>Tag auf Deutsch</dt><dd>tag value auf Deutsch</dd></div>" in shared
    assert ">Werkzeug</a>, <a " in shared
    assert shared.count("</a> auf Deutsch</dd>") == 2


def test_the_numbers_have_a_row_for_every_project_with_a_repo() -> None:
    table = hub.render.numbers_table(trust_catalog(), "de", {1: "silver"})
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
    table = hub.render.numbers_table(trust_catalog(), "en", {1: "silver"})
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
    table = hub.render.numbers_table(trust_catalog(), "en")

    assert "bestpractices.dev" not in table
    assert table.count('<td data-label="Bestpractices">—</td>') == 2


def test_the_numbers_of_the_trust_page_have_their_note_below_them() -> None:
    catalog = trust_catalog()

    text = hub.render.guarantees(catalog, "de", {1: "silver"})

    # The table, with its note below it; the page has the headings.
    assert text == "\n\n".join(
        [
            hub.render.numbers_table(catalog, "de", {1: "silver"}),
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
    catalog = hub.reader.read(data)

    shared = hub.render.shared_guarantees(catalog, "en")
    table = hub.render.numbers_table(catalog, "en", {1: "gold"})

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
    catalog = hub.reader.load(ROOT)
    projects = [project for project in catalog.projects if project.repo is not None]

    for language in catalog.languages:
        text = hub.render.shared_guarantees(catalog, language) + hub.render.guarantees(
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
    commands = hub.render.verification(trust_catalog(), "de")

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
    catalog = hub.reader.read(
        catalog_data(entry(name={"en": 'The "tool"', "de": "Das Werkzeug"}))
    )

    assert hub.render.verification(catalog, "en").startswith(
        '=== "The &quot;tool&quot;"\n'
    )


@pytest.mark.parametrize(
    ("locale", "language"), [("de", "de"), ("en", "en"), ("fr", "en"), (None, "en")]
)
def test_the_table_and_the_commands_take_the_place_of_their_markers(
    locale: str | None, language: str
) -> None:
    catalog = trust_catalog()
    # The levels that the build read once for every language.
    settings = SimpleNamespace(
        extra={"catalog": catalog, hub.render.LEVEL: {1: "gold"}}
    )
    markdown = (
        "# Trust\n\n<!-- trust-shared -->\n\n<!-- trust -->\n\n"
        "## Check\n\n<!-- verify --> \n"
    )

    result = hooks.on_page_markdown(markdown, page(locale), settings, None)

    assert result == (
        f"# Trust\n\n{hub.render.shared_guarantees(catalog, language)}\n\n"
        f"{hub.render.guarantees(catalog, language, {1: 'gold'})}\n\n"
        f"## Check\n\n{hub.render.verification(catalog, language)}\n"
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
    assert (
        hub.render.home_language(hub.reader.read(catalog_data()), dest_uri) == language
    )


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
    catalog = hub.reader.read(catalog_data(entry("tool"), plain, dashboard))

    assert hub.render.table(catalog, "en") == "\n".join(
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


def test_the_german_table_has_the_german_texts_and_the_german_addresses_first() -> None:
    plain = entry("plain", tagline={"en": "Yes | no", "de": "Ja | nein"})
    del plain["docs"]
    plain["requires"] = {"en": "Linux", "de": "Linux | macOS"}
    english = entry("english", docs={"en": "https://example.org/docs/"})
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
    catalog = hub.reader.read(catalog_data(entry("tool"), plain, english, dashboard))

    assert hub.render.table(catalog, "de") == "\n".join(
        [
            "| Projekt | Was es tut | Funktioniert mit | Start | Website |",
            "| --- | --- | --- | --- | --- |",
            "| [tool](https://github.com/Dennis-Otto/tool) | Ein Werkzeug | — "
            "| [Installieren](https://example.org/install) "
            "| [dennis-otto.github.io/tool/de](https://dennis-otto.github.io/tool/de/) · "
            "[dennis-otto.github.io/tool](https://dennis-otto.github.io/tool/) |",
            "| [plain](https://github.com/Dennis-Otto/plain) | Ja \\| nein "
            "| Linux \\| macOS | [Installieren](https://example.org/install) | — |",
            # A website in English alone, which the German table links all the same.
            "| [english](https://github.com/Dennis-Otto/english) | Ein Werkzeug | — "
            "| [Installieren](https://example.org/install) "
            "| [example.org/docs](https://example.org/docs/) |",
            "| Die Tafel | Ein Werkzeug | — "
            "| [Öffnen](https://example.org/de/) · [Open](https://example.org/) "
            "| [example.org/docs](https://example.org/docs/) |",
        ]
    )


def test_a_readme_takes_the_english_headings_in_a_language_without_its_own() -> None:
    data = in_french(catalog_data(entry("tool")))
    data["languages"] = ["fr", "en"]
    catalog = hub.reader.read(data)

    assert hub.render.readmes(catalog) == {"fr": "README.md", "en": "README.en.md"}
    assert hub.render.table(catalog, "fr").splitlines()[0] == (
        "| Project | What it does | Works with | Start | Website |"
    )


def test_a_further_language_without_headings_has_no_readme_of_its_own() -> None:
    data = in_french(catalog_data(entry("tool")))
    data["languages"] = ["en", "fr"]
    catalog = hub.reader.read(data)

    assert hub.render.readmes(catalog) == {"en": "README.md"}


@pytest.mark.parametrize("language", ["en", "de"])
def test_the_table_replaces_what_stands_between_the_markers(language: str) -> None:
    catalog = hub.reader.read(catalog_data())
    text = "# Title\n\n<!-- projects:start -->\nold\n<!-- projects:end -->\n\nEnd\n"

    written = hub.render.readme(text, catalog, language)

    assert written == (
        "# Title\n\n<!-- projects:start -->\n\n"
        f"{hub.render.table(catalog, language)}\n\n<!-- projects:end -->\n\nEnd\n"
    )
    assert hub.render.readme(written, catalog, language) == written


@pytest.mark.parametrize(
    "text",
    [
        "No markers\n",
        "<!-- projects:start -->\n",
        "<!-- projects:end -->\n",
        "<!-- projects:end -->\n<!-- projects:start -->\n",
    ],
)
@pytest.mark.parametrize(
    ("language", "name"), [("en", r"README\.md"), ("de", r"README\.de\.md")]
)
def test_the_readme_needs_both_markers_in_order(
    text: str, language: str, name: str
) -> None:
    with pytest.raises(hub.catalog.CatalogError, match=rf"^{name} needs the lines"):
        hub.render.readme(text, hub.reader.read(catalog_data()), language)
