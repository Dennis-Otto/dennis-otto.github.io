"""Tests of .github/hub/events.py, through .github/mkdocs_project.py, as MkDocs calls
them, with fakes of MkDocs in its place.
"""

from __future__ import annotations

import json
import logging
import shutil
import sys
from datetime import date
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

import hub.address
import hub.events
import hub.reader
import hub.render
import hub.search
import hub.web
from hub_helpers import (
    EPOCH,
    HTML,
    LD_JSON,
    ROOT,
    SITE,
    build,
    catalog_data,
    hooks,
    index_of,
    language,
    page,
    page_at,
    search_index,
    section,
    sitemap,
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
        site_description="The projects.",
    )


def website(root: Path) -> Path:
    """A repository at root with this catalog, the pages of the former websites that
    it names and the pages of its documentation."""
    shutil.copyfile(ROOT / "projects.toml", root / "projects.toml")
    shutil.copytree(ROOT / "former", root / "former")
    docs = root / "docs"
    (docs / "decisions").mkdir(parents=True)
    for name in ("index.md", "index.de.md", "decisions/README.md"):
        (docs / name).write_text("# Page\n", encoding="utf-8")
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

    assert settings.extra["catalog"] == hub.reader.load(ROOT)
    assert settings.extra[hub.address.LLMS] == "The projects."
    assert caplog.messages == []


def test_on_config_reads_the_catalog_once_for_every_language(tmp_path: Path) -> None:
    website(tmp_path)
    settings = config(tmp_path, language("en"), GERMAN, nav=NAV)
    hooks.on_config(settings)
    catalog = settings.extra["catalog"]
    # The build of the German website has the same configuration, with the
    # description in German.
    (tmp_path / "projects.toml").unlink()
    settings.site_description = "Die Projekte."

    assert hooks.on_config(settings) is settings
    assert settings.extra["catalog"] is catalog
    assert settings.extra[hub.address.LLMS] == "The projects."


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
        "the page in UNTRANSLATED of .github/hub/events.py.",
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
    hub.events.check_languages(
        hub.reader.read(catalog_data()), [language("en"), language("fr")]
    )

    assert caplog.messages == [
        "The website is built in fr, but projects.toml has no texts in it: add fr to "
        "its languages, and a text in it to every project."
    ]


def test_the_languages_of_the_website_are_those_built_the_default_first() -> None:
    french = language("fr", build=False)
    settings = config(Path(), GERMAN, french, language("en"))

    assert [item.locale for item in hub.events.built_languages(settings)] == [
        "en",
        "de",
    ]


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

    hub.events.check_menu(nav, languages)

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
    hub.events.check_menu(None, [language("en"), language("de")])

    assert caplog.messages == []


def test_an_untranslated_page_must_be_listed_and_leave_the_list_once_translated(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(hub.events, "UNTRANSLATED", frozenset({"security.md"}))
    docs = tmp_path / "docs"
    (docs / "guide" / "decisions").mkdir(parents=True)
    (docs / "decisions").mkdir()
    for name in (
        "index.md",
        "index.de.md",
        "security.md",
        "decisions/0001-record.md",
        "guide/setup.md",
        "guide/decisions/x.md",
        "notes.v2.md",
    ):
        (docs / name).write_text("# Page\n", encoding="utf-8")
    languages = [language("en"), language("de")]

    hub.events.check_pages(docs, languages)
    (docs / "security.de.md").write_text("# Sicherheit\n", encoding="utf-8")
    hub.events.check_pages(docs, languages)

    assert caplog.messages == [
        "docs/guide/decisions/x.md has no translation in de: write "
        "docs/guide/decisions/x.de.md, or list the page in UNTRANSLATED of "
        ".github/hub/events.py.",
        "docs/guide/setup.md has no translation in de: write docs/guide/setup.de.md,"
        " or list the page in UNTRANSLATED of .github/hub/events.py.",
        "docs/notes.v2.md has no translation in de: write docs/notes.v2.de.md, or "
        "list the page in UNTRANSLATED of .github/hub/events.py.",
    ] * 2 + [
        "docs/security.md has its translation docs/security.de.md now: remove it "
        "from UNTRANSLATED in .github/hub/events.py."
    ]


def test_a_page_may_carry_the_suffix_of_the_default_language(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(hub.events, "UNTRANSLATED", frozenset({"security.md"}))
    docs = tmp_path / "docs"
    docs.mkdir()
    for name in ("guide.en.md", "guide.de.md", "faq.en.md", "security.en.md"):
        (docs / name).write_text("# Page\n", encoding="utf-8")

    hub.events.check_pages(docs, [language("en"), language("de")])

    assert caplog.messages == [
        "docs/faq.en.md has no translation in de: write docs/faq.de.md, or list "
        "the page in UNTRANSLATED of .github/hub/events.py.",
    ]


@pytest.mark.parametrize(
    ("locale", "language"), [("de", "de"), ("en", "en"), ("fr", "en"), (None, "en")]
)
def test_the_cards_take_the_place_of_the_marker_in_the_language_of_the_page(
    locale: str | None, language: str
) -> None:
    catalog = hub.reader.read(catalog_data())
    settings = SimpleNamespace(extra={"catalog": catalog})
    markdown = "# Home\n\n<!-- projects -->  \n\n## Support\n"

    result = hooks.on_page_markdown(markdown, page(locale), settings, None)

    assert result == f"# Home\n\n{hub.render.cards(catalog, language)}\n\n## Support\n"


def test_a_marker_within_a_line_stays_as_it_is() -> None:
    settings = SimpleNamespace(extra={"catalog": hub.reader.read(catalog_data())})
    markdown = "The line `<!-- projects -->` marks the cards.\n"

    assert hooks.on_page_markdown(markdown, page("en"), settings, None) == markdown


def test_mkdocs_serve_builds_again_when_the_catalog_changes(tmp_path: Path) -> None:
    watched: list[str] = []
    server = SimpleNamespace(watch=watched.append)

    assert hooks.on_serve(server, config(tmp_path), None) is server
    assert watched == [str(tmp_path / "projects.toml")]


TITLE = "Open-source apps for Home Assistant, Nextcloud and Paperless-ngx"


def test_on_post_build_writes_robots_and_security_txt_at_the_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv("SOURCE_DATE_EPOCH", EPOCH)
    (tmp_path / "security.html").write_text("<html></html>", encoding="utf-8")
    settings = build(tmp_path)
    catalog = settings.extra["catalog"]

    home = sitemap(f"{SITE}index.html")
    (tmp_path / "sitemap.xml").write_text(home, encoding="utf-8", newline="\n")

    # The build of the German website, into the same folder, with the description
    # in German, and then that of the English one.
    settings.site_description = "Die Projekte von Dennis Otto."
    hooks.on_post_build(settings)
    settings.site_description = "The projects of Dennis Otto."
    hooks.on_post_build(settings)

    robots = hub.address.robots(catalog, SITE)
    security = hub.address.security_txt(catalog, SITE, date(2026, 10, 13))
    # Without the search, llms.txt has no guides, and its summary stays English.
    llms = hub.address.llms_txt(catalog, SITE, "The projects of Dennis Otto.", {})
    assert (tmp_path / "robots.txt").read_bytes() == robots.encode()
    for name in (".well-known/security.txt", "security.txt"):
        assert (tmp_path / name).read_bytes() == security.encode()
    assert (tmp_path / "llms.txt").read_bytes() == llms.encode()
    sitemaps = (tmp_path / "sitemap.xml").read_text(encoding="utf-8")
    assert f"<loc>{SITE}</loc>" in sitemaps
    assert caplog.messages == []


def test_on_post_build_gives_llms_txt_the_guides_of_the_search(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "security.html").write_text("<html></html>", encoding="utf-8")
    search_index(tmp_path, section("index.html", "Home"))

    def download(url: str) -> bytes:
        return index_of(section("faq.html", "Questions"))

    monkeypatch.setattr(hub.web, "download", download)
    settings = build(tmp_path)

    hooks.on_post_build(settings)

    llms = (tmp_path / "llms.txt").read_text(encoding="utf-8")
    assert f"  - [Questions]({SITE}paperless-sync/faq.html)\n" in llms
    assert llms == hub.address.llms_txt(
        settings.extra["catalog"],
        SITE,
        "The projects of Dennis Otto.",
        settings.extra[hub.search.SEARCH].guides,
    )


def test_on_post_build_warns_when_the_policy_of_security_txt_is_missing(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    hooks.on_post_build(build(tmp_path))

    assert (tmp_path / ".well-known" / "security.txt").is_file()
    assert caplog.messages == [
        "security.txt names https://dennis-otto.github.io/security.html as the "
        "policy of the address, but the website has no such page: keep "
        "docs/security.md, or change POLICY in .github/hub/address.py."
    ]


def test_on_post_build_writes_a_page_at_every_old_address(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SOURCE_DATE_EPOCH", EPOCH)
    (tmp_path / "security.html").write_text("<html></html>", encoding="utf-8")
    settings = build(tmp_path)

    hooks.on_post_build(settings)
    # The build of the German website, into the same folder.
    hooks.on_post_build(settings)

    pages = hub.address.moved_pages(settings.extra["catalog"])
    written = sorted(
        path.relative_to(tmp_path).as_posix()
        for folder in ("ha-autodarts", "dennis-otto-pager")
        for path in (tmp_path / folder).rglob("*")
        if path.is_file()
    )
    assert written == sorted(pages)
    for name, text in pages.items():
        assert (tmp_path / name).read_bytes() == text.encode(), name


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
    settings = SimpleNamespace(extra={"catalog": hub.reader.read(catalog_data())})

    hooks.on_files(files_at("index.html", "tool/x.html"), settings)

    assert caplog.messages == []


def test_the_404_page_gets_the_name_and_the_website_of_every_project() -> None:
    catalog = hub.reader.load(ROOT)

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
            # From the catalog: the pull request of the bot removes a German website
            # that is gone, and its checks must pass.
            "de": catalog.projects[0].website["de"],
        },
    }
    pager = 5
    assert directory[pager]["slug"] == "repo-pager"
    assert directory[pager]["former"] == ["dennis-otto-pager"]
    assert [item["former"] for item in directory[1:pager] + directory[pager + 1 :]] == [
        []
    ] * 6
    # The dashboard has no documentation; its button leads to it.
    assert directory[-1]["url"] == dict.fromkeys(
        ("en", "de"), "https://dennis-otto.github.io/repo-blueprint/dashboard/"
    )
    for item in directory:
        assert all(url.startswith("https://") for url in item["url"].values())
    # The template gives it to the script as JSON.
    assert json.loads(json.dumps(directory)) == directory


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
    assert hub.render.ATOM not in output


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
    head = hub.address.structured_data(hub.reader.load(ROOT), SITE, "Dennis Otto")
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


def test_on_post_build_adds_the_project_websites_to_the_search_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    own = section("index.html", "Home")
    path = search_index(tmp_path, own)
    asked: list[str] = []

    def download(url: str) -> bytes:
        asked.append(url)
        return index_of(section("index.html", "Home"))

    monkeypatch.setattr(hub.web, "download", download)
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
        "repo-pager/index.html",
        "repo-blueprint/index.html",
    ]
    assert len(asked) == 7


def test_on_post_build_downloads_nothing_without_the_search(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    asked: list[str] = []
    monkeypatch.setattr(hub.web, "download", asked.append)
    settings = build(tmp_path)

    hooks.on_post_build(settings)

    assert asked == []
    assert hub.search.SEARCH not in settings.extra
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
        "after the -110 of on_post_build of .github/hub/events.py, so the "
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
    assert (
        markup.index(include)
        < markup.index("</script>")
        < markup.index("{{ super() }}")
    )
    assert (ROOT / "overrides" / "partials" / "search-hold.js").is_file()
    # The pages of the website all take it, the home page and the 404 page too, the
    # home page and the Trust page through the template of the pages with live facts.
    for name in ("facts.html", "404.html"):
        page = (ROOT / "overrides" / name).read_text(encoding="utf-8")
        assert '{% extends "main.html" %}' in page
    home = (ROOT / "overrides" / "home.html").read_text(encoding="utf-8")
    assert '{% extends "facts.html" %}' in home
