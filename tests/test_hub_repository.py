"""What the real repository holds and what the hooks need of it: the catalog, the
home pages, the READMEs, the settings of MkDocs and the pictures.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tomllib
from html import escape
from pathlib import Path

import pytest

import hub.address
import hub.catalog
import hub.events
import hub.pictures
import hub.reader
import hub.releases
import hub.render
from hub_helpers import ROOT, SITE, language

# The catalog of this repository.


def test_the_catalog_of_the_repository_has_every_project_in_both_languages() -> None:
    catalog = hub.reader.load(ROOT)

    assert catalog.languages == ("en", "de")
    assert [project.slug for project in catalog.projects] == [
        "homedarts-for-autodarts",
        "player-switch-for-autodarts",
        "paperless-sync",
        "paperless-unified-search",
        "issue-assistant",
        "repo-pager",
        "repo-blueprint",
        "dashboard",
    ]
    for project in catalog.projects:
        for texts in (project.name, project.tagline, project.summary):
            assert set(texts) == {"en", "de"}


def test_the_home_page_groups_the_projects_by_their_readers() -> None:
    catalog = hub.reader.load(ROOT)

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
        "maintainers": ["issue-assistant", "repo-pager", "repo-blueprint"],
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
    catalog = hub.reader.load(ROOT)

    for project in catalog.projects:
        if project.group is None:
            continue
        assert project.picture is not None, project.slug
        assert project.picture.src == {
            "en": f"images/projects/{project.slug}.webp",
            "de": f"images/projects/de/{project.slug}.webp",
        }
        for code, alt in project.picture.alt.items():
            # Says what the picture shows, not only the name of the project.
            assert len(alt) > len(project.name["en"]) + 20, alt
            # The screenshot bot brings each new picture without a person, so the
            # alt says what every picture keeps, the name of the project first.
            assert project.name[code] in alt, (project.slug, code)
    assert hub.pictures.pictures(catalog).splitlines() == [
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
    catalog = hub.reader.load(ROOT)
    template = (ROOT / hub.pictures.DRAWING).read_text(encoding="utf-8")
    icons = tmp_path / "icons"
    (icons / "material").mkdir(parents=True)
    for icon in ("bell-ring", "file-tree"):
        (icons / "material" / f"{icon}.svg").write_text("<svg/>", encoding="utf-8")

    lines = hub.pictures.drawings(
        catalog, tmp_path / "pages", template, icons
    ).splitlines()

    carded = [project for project in catalog.projects if project.group is not None]
    assert [line.split()[1] for line in lines] == [
        f"docs/images/projects/de/{project.slug}.webp" for project in carded
    ]
    german = {
        "homedarts-for-autodarts": "docs/images/de/card.png",
        "player-switch-for-autodarts": "docs/images/lobby.de.dark.png",
        "paperless-sync": "docs/images/de/archive-dark.png",
        "repo-pager": "docs/images/diagrams/how-the-pager-works.de.dark.svg",
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


def test_the_social_preview_shows_the_picture_of_every_card() -> None:
    # The collage of .github/social-preview.html: a column for each group, with the
    # picture of each of its cards in the first language, in the order of the home
    # page, so that a new card can't be left out.
    catalog = hub.reader.load(ROOT)
    page = (ROOT / ".github/social-preview.html").read_text(encoding="utf-8")

    columns = [
        re.findall(r'<img src="\.\./docs/([^"]+)" alt="">', column)
        for column in re.findall(r'<div class="column">(.*?)</div>', page, re.DOTALL)
    ]

    assert columns == [
        [
            project.picture.src[catalog.default]
            for project in catalog.members(group)
            if project.picture is not None
        ]
        for group in catalog.groups
    ]
    assert sum(map(len, columns)) == 7


def test_the_pictures_are_small_webps_of_the_size_of_the_cards() -> None:
    for project in hub.reader.load(ROOT).projects:
        if project.picture is None:
            continue
        for src in set(project.picture.src.values()):
            picture = ROOT / "docs" / src
            data = picture.read_bytes()
            # Made by scripts/project-pictures.sh, unless the project has no repo.
            assert project.repo is None or webp_size(data) == hub.render.PICTURE, (
                picture
            )
            # The home page stays light: 60 KB at most for each picture.
            assert len(data) <= 60_000, picture


def test_every_picture_names_the_license_of_its_repository_for_reuse() -> None:
    # The pictures come from the repositories of the projects, some of them under
    # the AGPL; REUSE needs the text of every license that a file names.
    licenses = {path.stem for path in (ROOT / "LICENSES").glob("*.txt")}

    for project in hub.reader.load(ROOT).projects:
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
    catalog = hub.reader.load(ROOT)
    homedarts = catalog.projects[0]

    assert homedarts.repo == "Dennis-Otto/homedarts-for-autodarts"
    assert homedarts.former == ("ha-autodarts",)
    assert catalog.moves()["ha-autodarts"] == f"{SITE}homedarts-for-autodarts/"
    # Every page of its sitemap on 2026-10-21, in both languages.
    pages = catalog.former_pages["ha-autodarts"]
    assert len(pages) == 72
    assert pages[0] == "index.html"
    for page in ("games.html", "de/index.html", "de/games.html", "branding/index.html"):
        assert page in pages, page
    assert sum(page.startswith("decisions/") for page in pages) == 25
    assert sum(page.startswith("de/") for page in pages) == 22
    # Its card keeps the anchor of the old slug, in both languages.
    for code in catalog.languages:
        assert '### <span id="ha-autodarts"></span>:material-bullseye-arrow:' in (
            hub.render.cards(catalog, code)
        )


def test_repo_pager_keeps_the_addresses_of_dennis_otto_pager() -> None:
    # Its repository was Dennis-Otto/dennis-otto-pager until 2026-11-08, and its
    # website lived at /dennis-otto-pager/.
    catalog = hub.reader.load(ROOT)
    pager = {project.slug: project for project in catalog.projects}["repo-pager"]

    assert pager.repo == "Dennis-Otto/repo-pager"
    assert pager.name == {"en": "Repo Pager", "de": "Repo Pager"}
    assert pager.former == ("dennis-otto-pager",)
    assert catalog.moves() == {
        "ha-autodarts": f"{SITE}homedarts-for-autodarts/",
        "dennis-otto-pager": f"{SITE}repo-pager/",
    }
    # Every page of its website under the old name, in both languages.
    pages = catalog.former_pages["dennis-otto-pager"]
    assert len(pages) == 31
    assert pages[0] == "index.html"
    for page in ("setup.html", "how-it-works.html", "de/index.html", "de/setup.html"):
        assert page in pages, page
    assert sum(page.startswith("decisions/") for page in pages) == 18
    assert sum(page.startswith("de/") for page in pages) == 5
    # Its card keeps the anchor of the old slug, in both languages.
    for code in catalog.languages:
        assert '### <span id="dennis-otto-pager"></span>:material-bell-ring:' in (
            hub.render.cards(catalog, code)
        )


def test_the_german_blueprint_button_leads_to_the_german_section() -> None:
    blueprint = {project.slug: project for project in hub.reader.load(ROOT).projects}[
        "repo-blueprint"
    ]

    assert blueprint.start.url == {
        "en": "https://github.com/Dennis-Otto/repo-blueprint#start-a-repository",
        "de": "https://github.com/Dennis-Otto/repo-blueprint/blob/main/README.de.md"
        "#ein-repository-anlegen",
    }


def test_the_dashboard_has_no_repository_no_documentation_and_no_card() -> None:
    catalog = hub.reader.load(ROOT)
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
    assert "](https://dennis-otto.github.io/repo-blueprint/)" in hub.render.card(
        blueprint, "en", catalog.second(blueprint)
    )


def test_both_home_pages_have_the_marker_of_the_cards_once() -> None:
    for page in ("docs/index.md", "docs/index.de.md"):
        markdown = (ROOT / page).read_text(encoding="utf-8")
        assert len(hub.render.MARKER_LINE.findall(markdown)) == 1, page


def test_both_home_pages_have_the_newest_releases_below_the_cards() -> None:
    for page in ("docs/index.md", "docs/index.de.md"):
        markdown = (ROOT / page).read_text(encoding="utf-8")
        news = hub.releases.NEWS_LINE.findall(markdown)
        assert len(news) == 1, page
        cards = markdown.index(hub.render.MARKER)
        heading = markdown.index("{ #whats-new }")
        # Under a heading of its own, after the cards, and with the sentence that
        # links the dashboard and the feed, for a reader without the script.
        assert cards < heading < markdown.index(hub.releases.NEWS_MARKER), page
        after = markdown[markdown.index(hub.releases.NEWS_MARKER) :].split("\n## ")[0]
        assert "](releases.md)" in after, page
        assert "https://dennis-otto.github.io/repo-blueprint/dashboard/)" in after
        assert hub.render.ATOM in after, page


def test_both_releases_pages_have_the_marker_of_the_notes_once() -> None:
    for page in ("docs/releases.md", "docs/releases.de.md"):
        markdown = (ROOT / page).read_text(encoding="utf-8")
        assert len(hub.releases.NOTES_LINE.findall(markdown)) == 1, page
        # With the feed of all releases, for a feed reader, before the releases.
        assert markdown.index(hub.render.ATOM) < markdown.index(
            hub.releases.NOTES_MARKER
        ), page
    assert hub.releases.RELEASES_PAGE == "releases.html"


def test_every_project_with_a_repository_names_its_project_at_bestpractices_dev() -> (
    None
):
    # Every repository of a project has its project at bestpractices.dev, whose
    # badge its README shows with the same number.
    numbers = {
        project.slug: project.bestpractices
        for project in hub.reader.load(ROOT).projects
        if project.repo is not None
    }

    assert numbers == {
        "homedarts-for-autodarts": 14935,
        "player-switch-for-autodarts": 15866,
        "paperless-sync": 15277,
        "paperless-unified-search": 14256,
        "issue-assistant": 15278,
        "repo-pager": 16429,
        "repo-blueprint": 15284,
    }


def test_the_script_reads_the_texts_of_the_facts_that_the_page_gives_it() -> None:
    script = (ROOT / "docs/javascripts/projects.js").read_text(encoding="utf-8")
    read = set(re.findall(r"labels\.([a-z]+)", script)) - {"locale"}

    assert read == set(hub.catalog.SCRIPT)
    for name in ("project-facts", "project-news", "data-facts", "data-history"):
        assert name.removeprefix("data-") in script, name
    assert hub.render.FACTS == "project-facts"


def test_the_pages_with_live_facts_alone_load_their_script() -> None:
    template = (ROOT / "overrides/facts.html").read_text(encoding="utf-8")
    home = (ROOT / "overrides/home.html").read_text(encoding="utf-8")
    config = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")

    assert "{{ super() }}" in template
    assert "<script src=\"{{ 'javascripts/projects.js' | url }}\"></script>" in template
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
    facts = hub.reader.load(ROOT).facts

    assert list(facts) == list(hub.catalog.FACT_KEYS)
    assert facts["coverage"] == {"en": "{} test coverage", "de": "{} Testabdeckung"}
    for key in hub.catalog.VALUED:
        assert all(text.count("{}") == 1 for text in facts[key].values()), key


def test_the_catalog_has_the_texts_of_the_trust_page_in_both_languages() -> None:
    trust = hub.reader.load(ROOT).trust

    assert list(trust.texts) == list(hub.catalog.TRUST_KEYS)
    assert list(trust.values) == list(hub.catalog.TRUST_VALUED)
    for texts in [*trust.texts.values(), *trust.values.values()]:
        assert set(texts) == {"en", "de"}
    assert trust.values["provenance"] == {
        "en": "SLSA Build Level 3",
        "de": "SLSA Build Level 3",
    }
    # The links to the security policy and to the form of every project go in {}.
    for key in hub.catalog.TRUST_LINKED:
        assert all(text.count("{}") == 1 for text in trust.values[key].values()), key


def test_the_trust_page_verifies_the_file_that_each_project_ships() -> None:
    # The files of the latest release that the commands of the Trust page download:
    # the package that its users install, as Verify a release in the SECURITY.md of
    # each project names it, and the SBOM of a project that ships no package.
    verified = {
        project.slug: project.verified
        for project in hub.reader.load(ROOT).projects
        if project.repo is not None
    }

    assert verified == {
        "homedarts-for-autodarts": "homedarts.zip",
        "player-switch-for-autodarts": "player-switch-for-autodarts.spdx.json",
        "paperless-sync": "paperless_sync.tar.gz",
        "paperless-unified-search": "paperless_unified_search.tar.gz",
        "issue-assistant": "issue-assistant.spdx.json",
        "repo-pager": "repo-pager.spdx.json",
        "repo-blueprint": "repo-blueprint.spdx.json",
    }


def test_both_trust_pages_have_the_guarantees_and_then_the_commands() -> None:
    for page in ("docs/trust.md", "docs/trust.de.md"):
        markdown = (ROOT / page).read_text(encoding="utf-8")
        assert len(hub.render.SHARED_LINE.findall(markdown)) == 1, page
        assert len(hub.render.TRUST_LINE.findall(markdown)) == 1, page
        assert len(hub.render.VERIFY_LINE.findall(markdown)) == 1, page
        # Each part under its heading in the source, so that markdownlint finds the
        # anchors that the page links: {#every-project}, then {#numbers}.
        shared = markdown.index("{#every-project}\n\n" + hub.render.SHARED_MARKER)
        numbers = markdown.index("{#numbers}\n\n" + hub.render.TRUST_MARKER)
        assert shared < numbers < markdown.index(hub.render.VERIFY_MARKER), page
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
        marker = hub.render.MARKER_LINE.search(markdown)
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


def test_the_repository_has_a_readme_in_english_and_one_in_german() -> None:
    assert hub.render.readmes(hub.reader.load(ROOT)) == {
        "en": "README.md",
        "de": "README.de.md",
    }


@pytest.mark.parametrize(
    ("language", "name"), [("en", "README.md"), ("de", "README.de.md")]
)
def test_each_readme_of_the_repository_has_the_table_of_the_catalog(
    language: str, name: str
) -> None:
    text = (ROOT / name).read_text(encoding="utf-8")

    assert hub.render.readme(text, hub.reader.load(ROOT), language) == text


@pytest.mark.parametrize(
    ("name", "other", "link"),
    [
        ("README.md", "README.de.md", "**English** · [Deutsch](README.de.md)"),
        ("README.de.md", "README.md", "[English](README.md) · **Deutsch**"),
    ],
)
def test_each_readme_leads_to_the_other_language_below_its_title(
    name: str, other: str, link: str
) -> None:
    lines = (ROOT / name).read_text(encoding="utf-8").splitlines()

    assert lines[:3] == ["# Dennis Otto", "", link]
    assert (ROOT / other).is_file()


@pytest.mark.parametrize("language", ["en", "de"])
def test_the_table_holds_every_address_of_the_catalog_for_the_link_check(
    language: str,
) -> None:
    # The Links workflow checks the Markdown files alone, not projects.toml.
    catalog = hub.reader.load(ROOT)
    table = hub.render.table(catalog, language)

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
    hub.events.check_pages(ROOT / "docs", [language("en"), language("de")])

    assert caplog.messages == []


def test_the_catalog_names_the_license_and_the_platform_of_every_repository() -> None:
    # The licenses as the REUSE.toml of each repository names them.
    projects = hub.reader.load(ROOT).projects

    assert {p.slug: (p.license, p.platform) for p in projects} == {
        "homedarts-for-autodarts": ("MIT", "Home Assistant"),
        "player-switch-for-autodarts": ("MIT", "Chrome, Edge, Firefox"),
        "paperless-sync": ("AGPL-3.0-or-later", "Nextcloud"),
        "paperless-unified-search": ("AGPL-3.0-or-later", "Nextcloud"),
        "issue-assistant": ("MIT", "GitHub Actions"),
        "repo-pager": ("MIT", "Cloudflare Workers"),
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
    assert f'href="#{hub.render.PROJECTS}"' in markup
    assert f'href="{hub.address.SPONSORS}"' in markup
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
    # The pictures of the website are the README's alone, those of a phone and of
    # the Trust page too: the website leaves them out.
    text = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    block = re.search(r"^exclude_docs: \|\n((?:  .+\n)+)", text, re.M)
    assert block is not None
    assert "/images/website-*.png" in block[1].split()
    assert "/images/website-*.webp" in block[1].split()


def test_the_readme_picture_names_the_first_group_and_its_projects() -> None:
    # 1280×800 pixels show the hero and the first group of the home page. Its alt
    # tells those who can't see the picture which projects it shows, so a project
    # that joins the first group needs its name there, as Add a project says.
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    alt = re.search(r'<img src="docs/images/website-light\.png" alt="([^"]+)"', readme)
    assert alt is not None
    catalog = hub.reader.load(ROOT)
    first = catalog.groups[0]

    assert first.heading["en"] in alt[1]
    for project in catalog.members(first):
        assert project.name["en"] in alt[1], project.slug
    # The picture of a phone shows the hero and the heading of the first group.
    phone = re.search(
        r'<img src="docs/images/website-phone-light\.webp" alt="([^"]+)"', readme
    )
    assert phone is not None
    assert first.heading["en"] in phone[1]


def test_the_german_readme_shows_the_german_home_page_and_names_its_first_group() -> (
    None
):
    # The same picture of the German home page, which scripts/screenshots.sh takes
    # as website-*.de.webp, and an alt in German that names the first group and its
    # projects, as that of README.md does in English.
    readme = (ROOT / "README.de.md").read_text(encoding="utf-8")

    assert (
        '<source media="(prefers-color-scheme: dark)" '
        'srcset="docs/images/website-dark.de.webp">'
    ) in readme
    alt = re.search(
        r'<img src="docs/images/website-light\.de\.webp" alt="([^"]+)"', readme
    )
    assert alt is not None
    catalog = hub.reader.load(ROOT)
    first = catalog.groups[0]
    assert first.heading["de"] in alt[1]
    for project in catalog.members(first):
        assert project.name["de"] in alt[1], project.slug
    for scheme in ("light", "dark"):
        assert (ROOT / "docs" / "images" / f"website-{scheme}.de.webp").is_file()


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
        [
            sys.executable,
            "-B",
            "-E",
            "-s",
            str(ROOT / ".github" / "blueprint.py"),
            "screenshots",
            "due",
            "--since",
            "HEAD~1",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    # 0 renders, 1 doesn't; anything else, or a word on stderr, is an error.
    assert run.returncode in (0, 1), run.stderr
    assert not run.stderr, run.stderr
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
        "scripts/screenshots.py",
        "docs/index.md",
        "docs/index.de.md",
        "docs/trust.md",
        "docs/assets/logo.svg",
        "docs/stylesheets/extra.css",
        "docs/javascripts/projects.js",
        "overrides/home.html",
        "mkdocs.yml",
        ".github/mkdocs_project.py",
        ".github/hub/render.py",
        ".github/mkdocs-blueprint.css",
    ):
        assert screenshots_due(tmp_path, path), path
    # The pictures that the bot commits start no run of their own, and neither does
    # a page that the pictures don't show.
    for path in (
        "docs/images/projects/homedarts-for-autodarts.webp",
        "docs/images/website-light.png",
        "docs/images/search-light.webp",
        "docs/about.md",
        "README.md",
    ):
        assert not screenshots_due(tmp_path, path), path


@pytest.mark.parametrize(
    "script", ["icons.sh", "project-pictures.sh", "screenshots.sh"]
)
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

    for project in hub.reader.load(ROOT).projects:
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
    assert hub.address.POLICY == "security.html"
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
    assert f"]({hub.address.CONTACT})" in text
    for project in hub.reader.load(ROOT).projects:
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


def test_the_script_of_the_pictures_finds_the_size_of_a_card() -> None:
    # The Python of scripts/project-pictures.sh runs only in the screenshot bot, so a
    # name that moved would pass every other check. These are its lines that read the
    # code of the hooks, without Pillow, which the tests don't have.
    script = (ROOT / "scripts" / "project-pictures.sh").read_text(encoding="utf-8")
    lines = re.search(
        r'^sys\.path\.insert\(0, "\.github"\)\n(?:from .+\n)+', script, re.M
    )
    assert lines is not None
    assert "import PICTURE" in lines[0]

    result = subprocess.run(
        [sys.executable, "-I", "-B", "-c", f"import sys\n{lines[0]}print(PICTURE)"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(hub.render.PICTURE)


@pytest.mark.parametrize("name", ["security.md", "security.de.md"])
def test_every_test_that_the_security_page_names_is_in_the_file_it_names(
    name: str,
) -> None:
    text = (ROOT / "docs" / name).read_text(encoding="utf-8")
    named = re.findall(
        r"((?:`test_\w+`(?:, | and | und ))*`test_\w+`) in `(tests/test_\w+\.py)`", text
    )
    assert named

    for tests, file in named:
        source = (ROOT / file).read_text(encoding="utf-8")
        for test in re.findall(r"`(test_\w+)`", tests):
            assert f"def {test}(" in source, f"{test} in {file}"
    # No test on the page goes without its file.
    assert sum(len(re.findall(r"`test_\w+`", tests)) for tests, _ in named) == len(
        re.findall(r"`test_\w+`", text)
    )
