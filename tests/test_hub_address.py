"""Tests of .github/hub/address.py: the files at the root of the address, the
structured data, the sitemaps and the pages at the old addresses.
"""

from __future__ import annotations

import dataclasses
import gzip
import json
import re
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest

import hub.address
import hub.reader
import hub.search
import hub.sitecheck
from hub_helpers import (
    BUILT,
    EPOCH,
    HTML,
    LD_JSON,
    ROOT,
    SITE,
    build,
    catalog_data,
    entry,
    found,
    group_data,
    hooks,
    language,
    page,
    page_at,
    sitemap,
)


def test_robots_lists_the_sitemap_of_every_website_at_the_address_once() -> None:
    elsewhere = entry("elsewhere", docs="https://elsewhere.example.org/docs/")
    plain = entry("plain")
    del plain["docs"]
    page = entry("page", docs={"en": f"{SITE}page/guide.html", "de": f"{SITE}de/"})
    twice = entry("twice", docs=f"{SITE}tool/")
    catalog = hub.reader.read(catalog_data(entry(), elsewhere, plain, page, twice))

    assert hub.address.robots(catalog, SITE) == (
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
    lines = hub.address.robots(hub.reader.load(ROOT), SITE).splitlines()

    assert [line for line in lines if line.startswith("Sitemap:")] == [
        f"Sitemap: {SITE}sitemap.xml",
        f"Sitemap: {SITE}homedarts-for-autodarts/sitemap.xml",
        f"Sitemap: {SITE}player-switch-for-autodarts/sitemap.xml",
        f"Sitemap: {SITE}paperless-sync/sitemap.xml",
        f"Sitemap: {SITE}paperless-unified-search/sitemap.xml",
        f"Sitemap: {SITE}issue-assistant/sitemap.xml",
        f"Sitemap: {SITE}dennis-otto-pager/sitemap.xml",
        f"Sitemap: {SITE}repo-blueprint/sitemap.xml",
    ]


# What llms.txt says below its summary, in a catalog in English and German.
LLMS_INFO = (
    "Each project below links its website, the first step for its users, such as "
    "its installation, and the guides of its website that a reader looks for first, "
    "each with its page in German where there is one. The "
    f"[search]({SITE}) of this website finds the pages of every website, and the "
    f"[Releases page]({SITE}releases.html) has the notes of the latest releases of "
    "every project."
)


def test_llms_txt_maps_every_project_of_every_group_with_its_guides() -> None:
    board = entry(
        "board",
        name={"en": "The board", "de": "Die Tafel"},
        tagline={"en": "A [board]", "de": "Eine Tafel"},
        start={
            "icon": "material-view-dashboard",
            "label": {"en": "Board", "de": "Tafel"},
            "url": f"{SITE}tool/board/",
        },
    )
    for key in ("group", "image", "alt", "docs"):
        del board[key]
    start = {
        "icon": "material-download",
        "label": {"en": "Install", "de": "Installieren"},
        "url": {"en": "https://example.org/install", "de": "https://example.org/de/"},
    }
    tool = entry(second="board", start=start)
    # A project that names one with a card of its own as its second.
    other = entry(
        "other",
        group="more",
        second="tool",
        tagline={"en": "Another   tool", "de": "Noch eins"},
    )
    data = catalog_data(tool, board, other)
    more = group_data("more", heading={"en": "More [tools]", "de": "Mehr"})
    data["group"].append(more)
    catalog = hub.reader.read(data)
    found = {
        "tool": [
            hub.search.Guide(
                {"en": "Install", "de": "Installieren"},
                {"en": f"{SITE}tool/install.html", "de": f"{SITE}tool/de/install.html"},
            ),
            hub.search.Guide({"en": "FAQ"}, {"en": f"{SITE}tool/faq.html"}),
        ],
        "other": [],
    }

    text = hub.address.llms_txt(catalog, SITE, "The projects\n  of Dennis Otto.", found)

    assert text == (
        "# Dennis Otto\n"
        "\n"
        "> The projects of Dennis Otto.\n"
        "\n"
        f"{LLMS_INFO}\n"
        "\n"
        "## Tools\n"
        "\n"
        f"- [The tool]({SITE}tool/): A tool. In German: "
        f"[Das Werkzeug]({SITE}tool/de/)\n"
        "  - [Install](https://example.org/install): In German: "
        "[Installieren](https://example.org/de/)\n"
        f"  - [The board]({SITE}tool/board/): A (board)\n"
        f"  - [Install]({SITE}tool/install.html): In German: "
        f"[Installieren]({SITE}tool/de/install.html)\n"
        f"  - [FAQ]({SITE}tool/faq.html)\n"
        "\n"
        "## More (tools)\n"
        "\n"
        f"- [The tool]({SITE}other/): Another tool. In German: "
        f"[Das Werkzeug]({SITE}other/de/)\n"
        "  - [Install](https://example.org/install)\n"
    )


def test_llms_txt_of_a_website_in_one_language_has_no_translations() -> None:
    catalog = dataclasses.replace(hub.reader.read(catalog_data()), languages=("en",))

    text = hub.address.llms_txt(catalog, SITE, None, {})

    assert text == (
        "# Dennis Otto\n"
        "\n"
        "Each project below links its website, the first step for its users, such as "
        "its installation, and the guides of its website that a reader looks for "
        f"first. The [search]({SITE}) of this website finds the pages of every "
        f"website, and the [Releases page]({SITE}releases.html) has the notes of the "
        "latest releases of every project.\n"
        "\n"
        "## Tools\n"
        "\n"
        f"- [The tool]({SITE}tool/): A tool\n"
        "  - [Install](https://example.org/install)\n"
    )


def test_llms_txt_names_a_language_without_a_name_by_its_code() -> None:
    catalog = dataclasses.replace(
        hub.reader.read(catalog_data()), languages=("en", "xx")
    )
    project = catalog.projects[0]
    name = project.name | {"xx": "Xx tool"}
    url = project.website | {"xx": f"{SITE}tool/xx/"}

    assert hub.address.llms_item(catalog, name, url) == (
        f"- [The tool]({SITE}tool/): In xx: [Xx tool]({SITE}tool/xx/)"
    )


def test_llms_txt_of_the_address_lists_every_project() -> None:
    catalog = hub.reader.load(ROOT)

    text = hub.address.llms_txt(catalog, SITE, None, {})

    links = [url for _, url in hub.sitecheck.LLMS_LINK.findall(text)]
    for project in catalog.projects:
        assert project.website["en"] in links
        assert project.start.url["en"] in links
    assert [line for line in text.splitlines() if line.startswith("## ")] == [
        "## For the smart home and the document archive",
        "## For maintainers on GitHub",
    ]
    # The dashboard, which has no card of its own, under the card of the blueprint.
    assert (
        f"  - [Repository dashboard]({SITE}repo-blueprint/dashboard/): The state of "
        "every repository at a glance\n"
    ) in text


def test_security_txt_has_the_fields_of_rfc_9116() -> None:
    text = hub.address.security_txt(hub.reader.load(ROOT), SITE, date(2026, 10, 13))

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
    text = hub.address.security_txt(hub.reader.read(catalog_data()), SITE, today)
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

    assert hub.address.build_date() == date(2026, 10, 13)


def test_the_day_of_the_build_is_today_in_utc(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SOURCE_DATE_EPOCH", raising=False)
    before = datetime.now(UTC).date()

    built = hub.address.build_date()

    assert before <= built <= datetime.now(UTC).date()


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
    assert hub.address.moved_to(f"{SITE}new/", page) == target


def test_the_page_at_an_old_address_leads_to_the_new_one_with_its_fragment() -> None:
    target = f"{SITE}homedarts-for-autodarts/de/games.html"

    page = hub.address.moved_page("HomeDarts for Autodarts", target, "de")

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
    page = hub.address.moved_page("The tool", f"{SITE}tool/", language)

    assert f'<html lang="{language}">' in page
    assert "<title>This page has moved - The tool</title>" in page
    assert (
        "<p>This page has moved to the website of The tool: "
        f'<a href="{SITE}tool/">dennis-otto.github.io/tool/</a></p>'
    ) in page


def test_no_text_or_address_breaks_the_page_at_an_old_address() -> None:
    page = hub.address.moved_page(
        '<b>"A & B"</b>', 'https://example.org/"</script><x', "en"
    )

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
    catalog = hub.reader.read(catalog_data(entry(former=["old-tool"]), entry("two")))
    catalog = dataclasses.replace(
        catalog, former_pages={"old-tool": ("index.html", "de/guide.html")}
    )

    pages = hub.address.moved_pages(catalog)

    assert pages == {
        "old-tool/index.html": hub.address.moved_page("The tool", f"{SITE}tool/", "en"),
        "old-tool/de/guide.html": hub.address.moved_page(
            "Das Werkzeug", f"{SITE}tool/de/guide.html", "de"
        ),
    }


def test_the_old_website_of_homedarts_for_autodarts_leads_to_the_new_one() -> None:
    pages = hub.address.moved_pages(hub.reader.load(ROOT))

    assert len(pages) == 72
    assert pages["ha-autodarts/index.html"] == hub.address.moved_page(
        "HomeDarts for Autodarts", f"{SITE}homedarts-for-autodarts/", "en"
    )
    assert pages["ha-autodarts/de/games.html"] == hub.address.moved_page(
        "HomeDarts for Autodarts", f"{SITE}homedarts-for-autodarts/de/games.html", "de"
    )
    assert all(name.startswith("ha-autodarts/") for name in pages)


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
    assert projects["numberOfItems"] == 7
    elements = projects["itemListElement"]
    assert [element["position"] for element in elements] == [1, 2, 3, 4, 5, 6, 7]
    items = [element["item"] for element in elements]
    assert {item["@type"] for item in items} == {"SoftwareSourceCode"}
    assert [item["@id"] for item in items] == [
        f"{SITE}#homedarts-for-autodarts",
        f"{SITE}#player-switch-for-autodarts",
        f"{SITE}#paperless-sync",
        f"{SITE}#paperless-unified-search",
        f"{SITE}#issue-assistant",
        f"{SITE}#dennis-otto-pager",
        f"{SITE}#repo-blueprint",
    ]
    assert items[2] == {
        "@type": "SoftwareSourceCode",
        "@id": f"{SITE}#paperless-sync",
        "name": "Paperless Sync",
        "description": hub.reader.load(ROOT).projects[2].summary["en"],
        "url": f"{SITE}paperless-sync/",
        "codeRepository": "https://github.com/Dennis-Otto/paperless-sync",
        "license": "https://spdx.org/licenses/AGPL-3.0-or-later.html",
        "runtimePlatform": "Nextcloud",
        "isAccessibleForFree": True,
        "maintainer": {"@id": f"{SITE}#owner"},
    }


def test_no_text_of_the_catalog_ends_the_script_of_the_structured_data() -> None:
    summary = {"en": "Ends </script><!-- here", "de": "Endet hier"}
    catalog = hub.reader.read(catalog_data(entry(summary=summary)))

    head = hub.address.structured_data(catalog, SITE, "Site")

    assert head.count("<") == 3
    block = LD_JSON.search(head)
    assert block is not None
    item = json.loads(block.group(1))["@graph"][2]["itemListElement"][0]["item"]
    assert item["description"] == "Ends </script><!-- here"


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

    hub.address.sitemaps_at_root(tmp_path, SITE)

    for folder in (tmp_path, tmp_path / "de"):
        assert (folder / "sitemap.xml").read_bytes() == wanted.encode()
    with gzip.GzipFile(packed) as reader:
        assert reader.read() == wanted.encode()
        assert reader.mtime == BUILT


def test_a_website_without_a_packed_sitemap_needs_none(tmp_path: Path) -> None:
    built = sitemap(f"{SITE}de/index.html")
    (tmp_path / "sitemap.xml").write_text(built, encoding="utf-8", newline="\n")

    hub.address.sitemaps_at_root(tmp_path, SITE)

    assert not (tmp_path / "sitemap.xml.gz").exists()
    assert (tmp_path / "sitemap.xml").read_text(encoding="utf-8") == built.replace(
        f'"{SITE}index.html"', f'"{SITE}"'
    )
