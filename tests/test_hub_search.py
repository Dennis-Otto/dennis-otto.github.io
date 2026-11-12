"""Tests of .github/hub/search.py: the search index of every project website in the
search of this one.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import pytest

import hub.reader
import hub.search
import hub.web
from hub_helpers import (
    ROOT,
    SITE,
    catalog_data,
    entry,
    index_of,
    search_index,
    section,
)

# The search of every project.

# The search index of a project website in English and German, as the search plugin
# of Material and the i18n plugin write it, with a page of each kind of entry and of
# each rank: an installation, a changelog and a decision record.
FIXTURE = ROOT / "tests/fixtures/search_index.json"


def project_website(slug: str = "tool", **changes: Any) -> Any:
    """The website of the project of entry() in the folder slug/ of the address."""
    catalog = hub.reader.read(catalog_data(entry(slug, **changes)))
    return hub.search.Website(catalog.projects[0], f"{slug}/")


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
    assert hub.search.excerpt(html) == text


def test_a_long_text_is_cut_after_a_whole_word() -> None:
    words = " ".join(f"word{number}" for number in range(100))

    text = (
        hub.search.excerpt(f"<p>{words}</p>").removeprefix("<p>").removesuffix("</p>")
    )

    assert len(text) <= hub.search.EXCERPT == 200
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
    assert hub.search.excerpt(words) == f"<p>{excerpt}</p>"


def test_the_search_finds_the_websites_in_folders_of_the_address() -> None:
    elsewhere = entry("elsewhere", docs="https://elsewhere.example.org/docs/")
    plain = entry("plain")
    del plain["docs"]
    page = entry("page", docs={"en": f"{SITE}page/guide.html", "de": f"{SITE}de/"})
    twice = entry("twice", docs=f"{SITE}tool/")
    root = entry("root", docs=SITE)
    catalog = hub.reader.read(
        catalog_data(entry(), elsewhere, plain, page, twice, root)
    )

    found = hub.search.websites(catalog, SITE)

    assert [(site.project.slug, site.folder) for site in found] == [
        ("tool", "tool/"),
        ("page", "page/"),
    ]


def test_the_search_of_the_address_has_every_project_website() -> None:
    found = hub.search.websites(hub.reader.load(ROOT), SITE)

    assert [site.folder for site in found] == [
        "homedarts-for-autodarts/",
        "player-switch-for-autodarts/",
        "paperless-sync/",
        "paperless-unified-search/",
        "issue-assistant/",
        "repo-pager/",
        "repo-blueprint/",
    ]
    assert found[0].project.short == {"en": "HomeDarts", "de": "HomeDarts"}


def test_the_entries_of_a_website_go_into_its_folder_under_its_name() -> None:
    content = FIXTURE.read_bytes()
    docs = hub.search.documents(content, "tool/search/search_index.json")
    short = {"en": "Tool & Co", "de": "Werkzeug"}

    found = hub.search.entries(
        hub.reader.read(catalog_data()),
        project_website(short=short),
        docs,
        hub.search.index_languages(content),
    )

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
        # The boosts are those of every language, and the sections of a page that a
        # reader looks for first rank lower in a further language than in the first.
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
            "TRANSLATED_START",
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

    found = hub.search.entries(
        hub.reader.read(catalog_data()), project_website(), docs, []
    )

    # The folder of a language that the catalog doesn't know is in the first one.
    titles = [doc["title"] for _, doc in found]
    assert titles == ["The tool › Home", "The tool › Accueil"]


def test_an_entry_without_a_text_is_one() -> None:
    docs = hub.search.documents(
        b'{"docs": [{"location": "a.html", "title": "A"}]}', "x"
    )

    assert hub.search.entries(
        hub.reader.read(catalog_data()), project_website(), docs, []
    ) == [
        hub.search.Entry(
            hub.search.Rank.PAGE,
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
        # The help of a browser extension and the setup of a service that each user
        # runs on their own.
        ("help.html", "START"),
        ("de/help.html", "START"),
        ("setup.html", "START"),
        ("setup/", "START"),
        # A page kept as the index of its folder is named after its folder.
        ("guide/index.html", "START"),
        ("de/installation/index.html", "START"),
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
    found = hub.search.rank_of(page)

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
        ("help.html#renewal-failing", 2),
        ("de/setup.html", 2),
        ("changelog/index.html#100", 0.5),
    ],
)
def test_the_name_of_a_page_boosts_its_entries(
    location: str, boost: float | None
) -> None:
    assert hub.search.boost_of(location) == boost


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

    with pytest.raises(hub.web.SearchError) as error:
        hub.search.documents(content, url)

    assert str(error.value).startswith(f"{url} {problem}")


def doc(number: int, size: int = 0, location: str = "") -> dict[str, str]:
    """An entry of a search index at location, or page<number>.html, whose text has
    size pieces that gzip can't pack much, different in every entry."""
    text = "".join(
        f"{(number * 7919 + index) ** 3 % 1000003:x}" for index in range(size)
    )
    location = location or f"page{number}.html"
    return {"location": location, "title": f"Page {number}", "text": text}


def pages(*docs: dict[str, str]) -> list[Any]:
    """The entries of the pages docs of a project website."""
    return [hub.search.Entry(hub.search.Rank.PAGE, page) for page in docs]


def rank(location: str) -> hub.search.Rank:
    """The rank of the entry at location, as entries() ranks it: a page, or a section
    of a page that the search keeps."""
    if "#" not in location:
        return hub.search.Rank.PAGE
    found = hub.search.rank_of(location.partition("#")[0])
    assert found is not None, location
    return found


def ranked(website: list[Any]) -> list[Any]:
    """The entries of website, each with the rank of its location, as
    entries() ranks them."""
    return [
        hub.search.Entry(
            rank(page["location"]),
            page,
        )
        for page in website
    ]


def flat(kept: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """The entries that within() keeps of every website, one after another."""
    return [page for website in kept for page in website]


def test_the_entries_within_the_budget_are_all_kept() -> None:
    found = [pages(doc(1), doc(2)), [], pages(doc(3))]

    assert hub.search.within(found, 1000) == [[doc(1), doc(2)], [], [doc(3)]]
    assert hub.search.within([], 0) == []


def test_the_largest_website_gives_up_its_last_pages_first() -> None:
    large = [doc(number, 40) for number in range(10)]
    small = [doc(number, 40) for number in range(10, 13)]
    budget = hub.search.packed(large[:5] + small)

    kept = hub.search.within([pages(*large), pages(*small)], budget)

    assert kept == [large[:5], small]
    assert (
        hub.search.packed(flat(kept)) <= budget < hub.search.packed(large[:6] + small)
    )


def test_every_website_gives_up_its_pages_beyond_the_same_number() -> None:
    large = [doc(number, 40) for number in range(10)]
    small = [doc(number, 40) for number in range(10, 13)]
    budget = hub.search.packed(large[:2] + small[:2])

    assert hub.search.within([pages(*large), pages(*small)], budget) == [
        large[:2],
        small[:2],
    ]
    assert hub.search.within([pages(*large), pages(*small)], 10) == [[], []]


def test_a_decision_record_gives_up_its_page_before_the_pages_for_readers() -> None:
    first = doc(1, 40, "index.html")
    record = doc(2, 40, "decisions/0001-one-search.html")
    installation = doc(3, 40, "installation.html")
    german = doc(4, 40, "de/installation.html")
    other = doc(5, 40, "games.html")
    website = [first, record, installation, german]
    budget = hub.search.packed([first, installation, german, other])

    kept = hub.search.within([pages(*website), pages(other)], budget)

    assert kept == [[first, installation, german], [other]]
    assert hub.search.within([pages(*website), pages(other)], 10**6) == [
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
        return hub.search.within(found, hub.search.packed(list(docs)))[0]

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

    budget = hub.search.packed(long[:3] + short[:3] + other)
    assert hub.search.within(found, budget) == [long[:3] + short[:3], other]
    budget = hub.search.packed(long[:4] + short + other)
    assert hub.search.within(found, budget) == [long[:4] + short, other]
    budget = hub.search.packed(long[:2] + short[:2] + other)
    assert hub.search.within(found, budget) == [long[:2] + short[:2], other]


def test_the_search_of_the_address_adds_every_project_website(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, "mkdocs.hooks.project")
    asked: list[str] = []

    def download(url: str) -> bytes:
        asked.append(url)
        if "paperless-sync" in url:
            raise hub.web.SearchError(f"{url} can't be downloaded: timed out")
        if "issue-assistant" in url:
            return b"<html></html>"
        return index_of(section("index.html", "Home"), section("index.html#a", "A"))

    monkeypatch.setattr(hub.web, "download", download)

    folders, docs, guides = hub.search.project_search(hub.reader.load(ROOT), SITE)

    assert folders == [
        "homedarts-for-autodarts/",
        "player-switch-for-autodarts/",
        "paperless-sync/",
        "paperless-unified-search/",
        "issue-assistant/",
        "repo-pager/",
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
        ("repo-pager/index.html", "Repo Pager › Home"),
        ("repo-pager/index.html#a", "A"),
        ("repo-blueprint/index.html", "Repo Blueprint › Home"),
        ("repo-blueprint/index.html#a", "A"),
    ]
    # No website has a guide, and those that are away have none either.
    slugs = [
        website.project.slug
        for website in hub.search.websites(hub.reader.load(ROOT), SITE)
    ]
    assert guides == {slug: [] for slug in slugs}
    # Not a warning, which would fail the strict build.
    assert sorted((record.levelno, record.message) for record in caplog.records) == [
        (logging.INFO, "The search adds 10 entries of 5 of the 7 project websites."),
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
                "repo-pager",
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
    monkeypatch.setattr(hub.web, "download", lambda url: index_of(*website))
    monkeypatch.setattr(hub.search, "BUDGET", 1000)

    folders, docs, _ = hub.search.project_search(hub.reader.read(catalog_data()), SITE)

    assert folders == ["tool/"]
    assert 0 < len(docs) < len(website)
    assert hub.search.packed(docs) <= 1000
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
    catalog = hub.reader.read(catalog_data(entry("large"), entry("small")))
    # What the budget has room for: the entry of every page of both websites in
    # every language, and the sections of the pages that a reader looks for first.
    wanted = [
        doc
        for project, docs in zip(catalog.projects, (large, small), strict=True)
        for rank, doc in hub.search.entries(
            catalog, hub.search.Website(project, f"{project.slug}/"), docs, ["en"]
        )
        if rank
        in (
            hub.search.Rank.PAGE,
            hub.search.Rank.START,
            hub.search.Rank.TRANSLATED_START,
        )
    ]
    budget = hub.search.packed(wanted)

    def download(url: str) -> bytes:
        return index_of(*(large if "/large/" in url else small))

    monkeypatch.setattr(hub.web, "download", download)
    monkeypatch.setattr(hub.search, "BUDGET", budget)

    folders, docs, _ = hub.search.project_search(catalog, SITE)

    assert folders == ["large/", "small/"]
    # In the order of the index, every section after its page; no section of a
    # decision record, and none of a page for maintainers or of any other page
    # while the budget has no room for them all.
    assert [doc["location"] for doc in docs] == [doc["location"] for doc in wanted]
    assert hub.search.packed(docs) <= budget
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


def test_a_start_page_ranks_lower_in_a_further_language_of_its_website() -> None:
    docs = [
        section("faq.html", "FAQ"),
        section("faq.html#renewal", "Renewal"),
        # A language of the index, one of the catalog, and one that the index
        # doesn't name but whose folder has a home page.
        section("nl/faq.html#renewal", "Vernieuwing"),
        section("de/faq.html#renewal", "Erneuerung"),
        section("pl/index.html", "Start"),
        section("pl/faq.html#renewal", "Odnowienie"),
        # A folder that is no language, and one that looks like one without a home
        # page, are folders of the first language.
        section("kinds/faq.html#renewal", "Renewal"),
        section("id/faq.html#renewal", "Renewal"),
        # A page that a reader doesn't look for first keeps its rank in every
        # language.
        section("nl/games.html#cricket", "Cricket"),
    ]

    found = hub.search.entries(
        hub.reader.read(catalog_data()), project_website(), docs, ["en", "nl"]
    )

    assert [
        (doc["location"], rank.name) for rank, doc in found if "#" in doc["location"]
    ] == [
        ("tool/faq.html#renewal", "START"),
        ("tool/nl/faq.html#renewal", "TRANSLATED_START"),
        ("tool/de/faq.html#renewal", "TRANSLATED_START"),
        ("tool/pl/faq.html#renewal", "TRANSLATED_START"),
        ("tool/kinds/faq.html#renewal", "START"),
        ("tool/id/faq.html#renewal", "START"),
        ("tool/nl/games.html#cricket", "OTHER"),
    ]


def test_a_start_page_in_five_languages_leaves_a_small_website_its_help(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, "mkdocs.hooks.project")
    number = 0

    def page(location: str, sections: int) -> list[dict[str, str]]:
        nonlocal number
        docs: list[dict[str, str]] = []
        for part in range(sections + 1):
            number += 1
            anchor = f"#question-{part}" if part else ""
            docs.append(doc(number, 12, f"{location}{anchor}"))
        return docs

    # A large website whose FAQ is whole in five languages, as that of HomeDarts,
    # and a small one whose only page that a reader looks for first is its help, as
    # that of Player Switch, which has more sections than the FAQ.
    large = [
        *page("index.html", 0),
        *page("faq.html", 26),
        *(
            item
            for language in ("de", "nl", "fr", "es")
            for item in (
                *page(f"{language}/index.html", 0),
                *page(f"{language}/faq.html", 26),
            )
        ),
    ]
    small = [*page("index.html", 0), *page("help.html", 43)]
    catalog = hub.reader.read(catalog_data(entry("large"), entry("small")))
    # Room for the entry of every page, the help and the FAQ in English, and some
    # of the FAQ in the further languages.
    first = [item for item in large if "/" not in item["location"]]
    budget = (
        hub.search.packed(
            [item for item in large if "#" not in item["location"]]
            + [item for item in first if "#" in item["location"]]
            + small
        )
        + 2000
    )

    def download(url: str) -> bytes:
        return index_of(*(large if "/large/" in url else small))

    monkeypatch.setattr(hub.web, "download", download)
    monkeypatch.setattr(hub.search, "BUDGET", budget)

    _, docs, guides = hub.search.project_search(catalog, SITE)

    locations = {item["location"] for item in docs}
    assert hub.search.packed(docs) <= budget
    # The help of the small website and the FAQ of the large one in its first
    # language are whole, and the further languages share what is left.
    assert {f"small/{item['location']}" for item in small} <= locations
    assert {f"large/{item['location']}" for item in first} <= locations
    translated = [
        place for place in locations if place.startswith("large/de/faq.html#")
    ]
    assert 0 < len(translated) < 26
    assert [guide.url["en"] for guide in guides["small"]] == [f"{SITE}small/help.html"]


def test_a_catalog_without_project_websites_adds_nothing() -> None:
    plain = entry()
    del plain["docs"]

    assert hub.search.project_search(hub.reader.read(catalog_data(plain)), SITE) == (
        [],
        [],
        {},
    )


def test_the_guides_of_a_website_are_its_pages_for_readers_in_their_order() -> None:
    docs = [
        section("index.html", "Home"),
        section("troubleshooting.html", "Troubleshooting"),
        # The index lacks the entry of the page, so its first section names it.
        section("faq.html#a-question", "A question"),
        section("faq.html#another", "Another question"),
        section("decisions/0001-installation.html", "Install it so"),
        section("changelog.html", "Changelog"),
        section("installation.html", "Install &amp; <em>set up</em>"),
        section("installation.html#docker", "With Docker"),
        section("de/installation.html", "Installieren"),
        section("de/faq.html", "Fragen"),
        # A language of the website that the catalog lacks, and a German page
        # without its English one.
        section("nl/installation.html", "Installeren"),
        section("nl/guide.html", "Handleiding"),
        section("de/guide/index.html", "Anleitung"),
        section("guide/index.html", "The [guide]"),
        section("more help/faq.html", "Help"),
        # Languages that lunr can't stem, so the languages of the index lack them.
        section("pl/index.html", "Start"),
        section("pl/faq.html", "Pytania"),
        section("pt-BR/index.html", "Início"),
        section("pt-BR/faq.html", "Perguntas"),
    ]

    found = hub.search.guides(
        hub.reader.read(catalog_data()),
        project_website(),
        docs,
        SITE,
        ["en", "de", "nl"],
    )

    assert found == [
        hub.search.Guide(
            {"en": "Install & set up", "de": "Installieren"},
            {
                "en": f"{SITE}tool/installation.html",
                "de": f"{SITE}tool/de/installation.html",
            },
        ),
        hub.search.Guide(
            {"en": "The [guide]", "de": "Anleitung"},
            {
                "en": f"{SITE}tool/guide/index.html",
                "de": f"{SITE}tool/de/guide/index.html",
            },
        ),
        hub.search.Guide(
            {"en": "A question", "de": "Fragen"},
            {"en": f"{SITE}tool/faq.html", "de": f"{SITE}tool/de/faq.html"},
        ),
        # Its address stays in the folder of the website, whatever the index holds.
        hub.search.Guide({"en": "Help"}, {"en": f"{SITE}tool/more%20help/faq.html"}),
        hub.search.Guide(
            {"en": "Troubleshooting"}, {"en": f"{SITE}tool/troubleshooting.html"}
        ),
    ]


def test_the_help_and_the_setup_of_a_website_are_guides_in_their_order() -> None:
    docs = [
        section("index.html", "Home"),
        section("faq.html", "FAQ"),
        section("help.html", "Help"),
        section("setup.html", "Set up"),
        section("installation.html", "Installation"),
    ]

    found = hub.search.guides(
        hub.reader.read(catalog_data()), project_website(), docs, SITE, ["en"]
    )

    # The installation and the setup before the guides, and the help before the
    # answers to the questions.
    assert [guide.title["en"] for guide in found] == [
        "Installation",
        "Set up",
        "Help",
        "FAQ",
    ]


def test_a_website_without_the_languages_of_its_index_has_the_guides_of_each() -> None:
    docs = [section("faq.html", "FAQ"), section("nl/faq.html", "Vragen")]

    found = hub.search.guides(
        hub.reader.read(catalog_data()), project_website(), docs, SITE, []
    )

    # Without the languages of its index, nl/ is a folder like any other.
    assert [guide.url["en"] for guide in found] == [
        f"{SITE}tool/faq.html",
        f"{SITE}tool/nl/faq.html",
    ]


@pytest.mark.parametrize(
    ("index", "languages"),
    [
        ({"config": {"lang": ["en", "de", "nl"]}, "docs": []}, ["en", "de", "nl"]),
        ({"config": {"lang": ["en", 7, None]}, "docs": []}, ["en"]),
        ({"config": {"lang": "en"}, "docs": []}, []),
        ({"config": [], "docs": []}, []),
        ({"docs": []}, []),
    ],
)
def test_the_languages_of_a_search_index_are_those_of_its_config(
    index: dict[str, Any], languages: list[str]
) -> None:
    assert hub.search.index_languages(json.dumps(index).encode()) == languages


def test_the_search_gives_llms_txt_the_guides_of_every_website(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def download(url: str) -> bytes:
        if "/other/" in url:
            raise hub.web.SearchError(f"{url} can't be downloaded: timed out")
        return json.dumps(
            {
                "config": {"lang": ["en", "de", "fr"]},
                "docs": [
                    section("installation.html", "Installation"),
                    section("de/installation.html", "Installation"),
                    section("fr/installation.html", "Installation"),
                ],
            }
        ).encode()

    monkeypatch.setattr(hub.web, "download", download)

    catalog = hub.reader.read(catalog_data(entry(), entry("other")))

    found = hub.search.project_search(catalog, SITE)

    assert found.guides == {
        "tool": [
            hub.search.Guide(
                {"en": "Installation", "de": "Installation"},
                {
                    "en": f"{SITE}tool/installation.html",
                    "de": f"{SITE}tool/de/installation.html",
                },
            )
        ],
        "other": [],
    }


def test_the_entries_of_the_projects_follow_those_of_the_website(
    tmp_path: Path,
) -> None:
    own = [section("index.html", "Home"), section("de/index.html", "Startseite")]
    path = search_index(tmp_path, *own, section("tool/old.html", "Old"))
    docs = [section("tool/index.html", "The tool › Home")]

    hub.search.add_to_search(tmp_path, ["tool/", "other/"], docs)

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

    hub.search.add_to_search(tmp_path, ["tool/"], [])

    docs = json.loads(path.read_text(encoding="utf-8"))["docs"]
    assert [(doc["location"], doc.get("boost")) for doc in docs] == [
        ("index.html", None),
        (record, 0.5),
        (f"de/{record}#context", 0.5),
        ("decisions/index.html", 3),
    ]


# The summary of the Docs build, which counts the entries of every project website
# that the search takes.


def kept(folder: str) -> str:
    """The row of the summary for the website in folder with a page and a section,
    which the search keeps."""
    return f"| [{folder}]({SITE}{folder}/) | 1 of 1 | 1 of 1 |"


def test_the_build_writes_the_search_of_every_project_website_into_its_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    summary = tmp_path / "summary.md"
    summary.write_text("Before\n", encoding="utf-8")
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))

    def download(url: str) -> bytes:
        if "paperless-sync" in url:
            raise hub.web.SearchError(f"{url} can't be downloaded: a|b")
        if "issue-assistant" in url:
            return index_of()
        return index_of(section("index.html", "Home"), section("index.html#a", "A"))

    monkeypatch.setattr(hub.web, "download", download)

    hub.search.project_search(hub.reader.load(ROOT), SITE)

    assert summary.read_text(encoding="utf-8") == "\n".join(
        [
            "Before",
            "### The search of every project website",
            "",
            "The search adds 10 entries of 5 of the 7 project websites.",
            "",
            "| Project website | Pages kept | Sections kept |",
            "| --- | --- | --- |",
            kept("homedarts-for-autodarts"),
            kept("player-switch-for-autodarts"),
            f"| [paperless-sync]({SITE}paperless-sync/) | left out: "
            f"{SITE}paperless-sync/search/search_index.json can't be downloaded: "
            "a\\|b | |",
            kept("paperless-unified-search"),
            f"| [issue-assistant]({SITE}issue-assistant/) | left out: its index "
            "holds no entry | |",
            kept("repo-pager"),
            kept("repo-blueprint"),
            "",
        ]
    )


def test_a_summary_that_cant_be_written_never_fails_the_build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, "mkdocs.hooks.project")
    # A folder, which can't be opened as a file.
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(tmp_path))

    hub.search.summarize("text")

    assert len(caplog.records) == 1
    assert caplog.records[0].levelno == logging.INFO
    assert caplog.messages[0].startswith("The summary of the job can't be written: ")
