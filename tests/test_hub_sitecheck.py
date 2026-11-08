"""Tests of .github/hub/sitecheck.py: what the hooks promise, checked in the built
website.
"""

from __future__ import annotations

import dataclasses
import gzip
import json
import re
from collections.abc import Callable
from datetime import UTC, date, datetime
from html import escape
from pathlib import Path
from typing import Any

import pytest

import hub.address
import hub.reader
import hub.search
import hub.sitecheck
from hub_helpers import (
    BUILT,
    ROOT,
    SITE,
    catalog_data,
    entry,
    found,
    hooks,
    language,
    page,
    search_index,
    sitemap,
    write,
)

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
    "docs/security.md, or change POLICY of .github/hub/address.py"
)


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
        hub.address.structured_data(catalog, SITE, "Dennis Otto")
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


# The guides of the project websites in llms.txt of the website of hub_site().
HUB_GUIDES = {
    "homedarts-for-autodarts": [
        hub.search.Guide(
            {"en": "Installation", "de": "Installation"},
            {
                "en": f"{SITE}homedarts-for-autodarts/installation.html",
                "de": f"{SITE}homedarts-for-autodarts/de/installation.html",
            },
        )
    ]
}


def hub_site(site: Path, today: date = BUILT_ON) -> Path:
    """The folder site with the website of this repository as the hooks build it on
    today: every file that they write or change after the build, the pages that it
    reads, and a search index with the pages of this website and of every project."""
    catalog = hub.reader.load(ROOT)
    for name in hub.address.SECURITY_TXT:
        write(site / name, hub.address.security_txt(catalog, SITE, today))
    write(site / "security.html", "<!doctype html><title>Security</title>")
    write(site / "releases.html", "<!doctype html><title>Releases</title>")
    write(site / "robots.txt", hub.address.robots(catalog, SITE))
    llms = hub.address.llms_txt(
        catalog, SITE, "The projects of Dennis Otto.", HUB_GUIDES
    )
    write(site / "llms.txt", llms)
    for name, text in hub.address.moved_pages(catalog).items():
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
    hub.address.sitemaps_at_root(site, SITE)
    own = []
    for page in OWN_PAGES:
        boost = hub.search.boost_of(page)
        for location in (page, f"{page}#a-section"):
            doc = {"location": location, "title": "A page", "text": "<p>Text</p>"}
            own.append(doc if boost is None else doc | {"boost": boost})
    projects = [
        {"location": f"{folder}index.html", "title": "Tool › Home", "text": ""}
        for folder in (website.folder for website in hub.search.websites(catalog, SITE))
    ]
    search_index(site, *own, *projects)
    return site


def findings(site: Path, now: datetime = CHECKED) -> list[tuple[str, str]]:
    """What the check of the website in site finds at the moment now, as the path
    and the message of each finding."""
    found = hub.sitecheck.check_site(site, hub.reader.load(ROOT), now)
    return [(finding.path, finding.message) for finding in found]


def test_the_website_that_the_hooks_build_keeps_every_promise(tmp_path: Path) -> None:
    assert findings(hub_site(tmp_path)) == []


def test_the_check_finds_every_missing_file(tmp_path: Path) -> None:
    catalog = hub.reader.load(ROOT)
    pages = sum(len(pages) for pages in catalog.former_pages.values())

    found = findings(tmp_path)

    hooks_named = (
        "is missing: on_post_build of .github/hub/events.py writes it after the "
        "build, so check that hooks of mkdocs.yml names .github/mkdocs_project.py"
    )
    assert found[:4] == [
        (".well-known/security.txt", hooks_named),
        ("security.txt", hooks_named),
        ("robots.txt", hooks_named),
        ("llms.txt", hooks_named),
    ]
    moved = [path for path, _ in found if path.startswith("ha-autodarts/")]
    assert len(moved) == pages
    assert found[4 + pages :] == [
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
            "of .github/hub/events.py adds the project websites to it",
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
            ".github/hub/address.py writes the midnight a year after the day of the "
            "build, so build the website again, with no SOURCE_DATE_EPOCH or one of "
            "today",
            id="expired",
        ),
        pytest.param(
            expires_at("2027-10-20T00:00:00Z"),
            "expires at 2027-10-20T00:00:00Z, more than 365 days from now, where RFC "
            "9116 recommends less than a year: keep VALID of .github/hub/address.py "
            "at 365 days or fewer",
            id="more-than-a-year-ahead",
        ),
        pytest.param(
            expires_at("soon"),
            "names Expires: soon, which is no time of RFC 3339 with its zone, such as "
            "2027-10-24T00:00:00Z: security_txt() of .github/hub/address.py writes "
            "one",
            id="no-time",
        ),
        pytest.param(
            expires_at("2027-01-01T00:00:00"),
            "names Expires: 2027-01-01T00:00:00, which is no time of RFC 3339 with its "
            "zone, such as 2027-10-24T00:00:00Z: security_txt() of "
            ".github/hub/address.py writes one",
            id="no-zone",
        ),
        pytest.param(
            lambda text: re.sub(r"(?m)^Expires: .*\n", "", text),
            "has 0 Expires, where RFC 9116 asks for exactly one: security_txt() of "
            ".github/hub/address.py writes one",
            id="no-expires",
        ),
        pytest.param(
            lambda text: text + "expires: 2027-01-01T00:00:00Z\n",
            "has 2 Expires, where RFC 9116 asks for exactly one: security_txt() of "
            ".github/hub/address.py writes one",
            id="two-expires",
        ),
        pytest.param(
            lambda text: re.sub(r"(?m)^Contact: .*\n", "", text),
            "has no Contact, which RFC 9116 requires: security_txt() of "
            ".github/hub/address.py writes CONTACT",
            id="no-contact",
        ),
        pytest.param(
            lambda text: text + "Contact: http://example.org/report\n",
            "names Contact: http://example.org/report, which is no https://, mailto: "
            "or tel: address of RFC 9116: set CONTACT of .github/hub/address.py to "
            "the form for private reports",
            id="contact-without-tls",
        ),
        pytest.param(
            lambda text: text.replace(f"Canonical: {SITE}security.txt\n", ""),
            f"names no Canonical: {SITE}security.txt, the address of its copy at "
            "security.txt: security_txt() of .github/hub/address.py names every "
            "path of SECURITY_TXT",
            id="one-canonical",
        ),
        pytest.param(
            lambda text: re.sub(r"(?m)^Policy: .*\n", "", text),
            "has no Policy, the security page of the address: security_txt() of "
            ".github/hub/address.py names POLICY",
            id="no-policy",
        ),
        pytest.param(
            lambda text: text.replace(
                f"Policy: {SITE}security.html", "Policy: https://example.org/security"
            ),
            "names Policy: https://example.org/security, which is no page of the "
            "website: keep docs/security.md, or change POLICY of "
            ".github/hub/address.py",
            id="policy-elsewhere",
        ),
    ],
)
def test_security_txt_keeps_rfc_9116(tmp_path: Path, change: Any, message: str) -> None:
    site = hub_site(tmp_path)
    for name in hub.address.SECURITY_TXT:
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
    for name in hub.address.SECURITY_TXT:
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
            "differs from security.txt: on_post_build of .github/hub/events.py "
            "writes the same text into both, so remove what writes one of them after "
            "it, such as a file in docs/ or another plugin",
        ),
        (
            "security.txt",
            "has no Contact, which RFC 9116 requires: security_txt() of "
            ".github/hub/address.py writes CONTACT",
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
            ".github/hub/address.py names the sitemap of this website and of every "
            f"project of projects.toml whose docs are at {SITE}",
        ),
        (
            "robots.txt",
            f"names Sitemap: {SITE}repo-blueprint/sitemap.xml 2 times: robots() of "
            ".github/hub/address.py names every sitemap once",
        ),
    ]


def test_llms_txt_of_the_website_is_the_map_that_llmstxt_org_describes(
    tmp_path: Path,
) -> None:
    site = hub_site(tmp_path)
    llms = (site / "llms.txt").read_text(encoding="utf-8")
    paperless = next(
        line for line in llms.splitlines() if line.startswith("- [Paperless Sync]")
    )
    broken = (
        llms.replace("# Dennis Otto\n", "# Someone\n", 1)
        .replace("## For maintainers on GitHub\n", "## Maintainers\n")
        .replace(f"{paperless}\n", "")
        + "Some text\n"
        + f"  - [Old]({SITE}old.html)\n"
        + f"  - [A record]({SITE}paperless-sync/decisions/0001-a-decision.html)\n"
    )
    write(site / "llms.txt", broken)

    assert findings(site) == [
        (
            "llms.txt",
            "doesn't start with the title # Dennis Otto, which https://llmstxt.org/ "
            "asks for: llms_txt() of .github/hub/address.py writes it on the first "
            "line",
        ),
        (
            "llms.txt",
            "has 1 line(s) in its sections that are no item of a list with a link, "
            "such as 'Some text', where https://llmstxt.org/ asks for lists of links "
            "alone: llms_item() of .github/hub/address.py writes each item",
        ),
        (
            "llms.txt",
            "has no section ## For maintainers on GitHub: llms_txt() of "
            ".github/hub/address.py writes one for every group of projects.toml",
        ),
        (
            "llms.txt",
            f"doesn't link {SITE}paperless-sync/ of paperless-sync: llms_txt() of "
            ".github/hub/address.py lists every project of projects.toml with its "
            "website and the first button of its card",
        ),
        (
            "llms.txt",
            f"links 1 page(s) of this website that it lacks, such as {SITE}old.html: "
            "change llms_txt() of .github/hub/address.py, or keep the page",
        ),
        (
            "llms.txt",
            "links 1 decision record(s), such as "
            f"{SITE}paperless-sync/decisions/0001-a-decision.html, which are for "
            "maintainers: guides() of .github/hub/search.py takes the pages of "
            "START_PAGES alone",
        ),
    ]


def test_llms_txt_needs_no_first_button_of_a_project_without_a_card(
    tmp_path: Path,
) -> None:
    site = hub_site(tmp_path)
    projects = {project.slug: project for project in hub.reader.load(ROOT).projects}
    dashboard = projects["dashboard"].website["en"]
    llms = (site / "llms.txt").read_text(encoding="utf-8")
    kept = [line for line in llms.splitlines() if f"]({dashboard})" not in line]
    write(site / "llms.txt", "".join(f"{line}\n" for line in kept))

    # The dashboard has no group, so no card and no first button of its own.
    assert findings(site) == [
        (
            "llms.txt",
            f"doesn't link {dashboard} of dashboard: llms_txt() of "
            ".github/hub/address.py lists every project of projects.toml with its "
            "website",
        )
    ]


def test_no_sitemap_names_the_home_page_in_place_of_the_root(tmp_path: Path) -> None:
    site = hub_site(tmp_path)
    home = sitemap(f"{SITE}index.html", f"{SITE}about.html")
    write(site / "de/sitemap.xml", home)
    with gzip.GzipFile(site / "sitemap.xml.gz", "wb", mtime=BUILT) as packed:
        packed.write(home.encode("utf-8"))

    message = (
        f"names {SITE}index.html in place of {SITE}, the canonical address of the "
        "home page: sitemaps_at_root() of .github/hub/address.py leads it to the "
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
    elsewhere = hub.address.moved_page(
        "HomeDarts", f"{SITE}homedarts-for-autodarts/", "de"
    )
    write(site / "ha-autodarts/de/games.html", elsewhere)
    refreshed = (site / "ha-autodarts/faq.html").read_text(encoding="utf-8")
    later = refreshed.replace('content="0; ', 'content="5; ')
    write(site / "ha-autodarts/faq.html", later)

    new = f"{SITE}homedarts-for-autodarts/"
    leads = (
        "the same page in the folder of the website now, with its canonical address "
        "and its refresh: moved_page() of .github/hub/address.py writes both, so "
        "remove what writes the page after it, such as a file in docs/"
    )
    # Sorted, as they come in the order of former/ha-autodarts.txt.
    assert sorted(findings(site)) == [
        ("ha-autodarts/de/games.html", f"doesn't lead to {new}de/games.html, {leads}"),
        ("ha-autodarts/faq.html", f"doesn't lead to {new}faq.html, {leads}"),
        (
            "ha-autodarts/games.html",
            "is missing, an old address that former/ha-autodarts.txt lists: "
            "on_post_build of .github/hub/events.py writes a page there that leads "
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
    catalog = hub.reader.load(ROOT)
    data = {"moves": catalog.moves(), "projects": catalog.directory()}
    fixture = ROOT / "tests/fixtures/not-found-data.json"

    assert json.loads(fixture.read_text(encoding="utf-8")) == data


def test_a_404_page_without_its_script_leads_no_old_folder(tmp_path: Path) -> None:
    write(tmp_path / "404.html", '<html lang="en"><p>Nothing here.</p></html>')
    moved = hub.reader.read(catalog_data(entry(former=["old"])))

    assert hub.sitecheck.not_found_findings(tmp_path, moved)[0].message.startswith(
        f"doesn't lead /old/ to {SITE}tool/, as former of projects.toml asks"
    )
    # Without a folder of former, the page leads none.
    assert (
        hub.sitecheck.not_found_findings(tmp_path, hub.reader.read(catalog_data()))
        == []
    )


def test_a_404_page_that_leads_an_old_folder_the_catalog_lacks(tmp_path: Path) -> None:
    write(
        tmp_path / "404.html", not_found_page(not_found_data({"old": f"{SITE}tool/"}))
    )

    [finding] = hub.sitecheck.not_found_findings(
        tmp_path, hub.reader.read(catalog_data())
    )
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
            "has 6 cards, not one for each of the 7 projects with a group of "
            "projects.toml: cards() of .github/hub/render.py writes them in place "
            "of <!-- projects -->",
        ),
        (
            "de/index.html",
            "lacks the anchor #ha-autodarts, where the card of homedarts-for-autodarts "
            "was before, as former of projects.toml names it: card() of "
            ".github/hub/render.py keeps it in the heading of the card",
        ),
        (
            "de/index.html",
            "has no card of paperless-sync, whose heading has the anchor "
            "#paperless-sync: card() of .github/hub/render.py writes one for every "
            "project with a group of projects.toml",
        ),
        (
            "de/index.html",
            "shows no images/projects/de/paperless-sync.webp, the picture of the "
            "card of paperless-sync in de: card() of .github/hub/render.py puts "
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
    first = hub.reader.load(ROOT).groups[0]

    found = findings(site)

    assert len(found) == 2 * len(hub.reader.load(ROOT).members(first))
    assert found[-1] == (
        "de/index.html",
        "loads images/projects/de/paperless-unified-search.webp, the picture of the "
        "card of paperless-unified-search, only as it comes into view, though its "
        "group is in view as the page opens: section() of .github/hub/render.py "
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
            ".github/hub/events.py puts that of structured_data() into its head",
        )
    ]


def test_the_json_ld_lists_every_project_with_a_repo_in_its_order(
    tmp_path: Path,
) -> None:
    site = hub_site(tmp_path)
    catalog = hub.reader.load(ROOT)
    fewer = dataclasses.replace(catalog, projects=catalog.projects[1:2])
    structured_data(site, hub.address.structured_data(fewer, SITE, "Dennis Otto"))

    [(path, message)] = findings(site)
    assert path == "index.html"
    assert message.startswith(
        f"lists {SITE}#player-switch-for-autodarts in its JSON-LD, not every project "
        f"with a repo of projects.toml in its order, {SITE}#homedarts-for-autodarts, "
    )
    assert message.endswith(": structured_data() of .github/hub/address.py lists them")


def test_a_json_ld_without_projects_lists_none(tmp_path: Path) -> None:
    site = hub_site(tmp_path)
    none = dataclasses.replace(hub.reader.load(ROOT), projects=())
    structured_data(site, hub.address.structured_data(none, SITE, "Dennis Otto"))

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
            f"as {SITE}de/about.html: add_to_search() of .github/hub/search.py "
            "keeps the entries of this website beside those of the projects",
        ),
        (
            "search/search_index.json",
            "gives 4 entries of this website no boost, such as releases.html: "
            "add_to_search() of .github/hub/search.py gives them that of their "
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
            f"has no entry of the 7 project websites at {SITE}: on_post_build of "
            ".github/hub/events.py adds them after the build. When the log of the "
            "build says that the search leaves out every website, GitHub Pages was "
            "away while it ran: run the job again",
        ),
        (
            "search/search_index.json",
            "has 1 entries of a project outside the folder of its website, such as "
            "games.html: entries() of .github/hub/search.py puts every location "
            "into the folder of its website",
        ),
    ]


def test_a_website_without_project_websites_needs_none_in_its_search(
    tmp_path: Path,
) -> None:
    search_index(tmp_path, {"location": "index.html", "title": "Home", "text": ""})
    alone = hub.reader.read(catalog_data(entry(docs="https://example.org/tool/")))

    assert hub.sitecheck.search_findings(tmp_path, alone) == []


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
        ".github/mkdocs_project.py promise: security.txt, robots.txt, llms.txt, the "
        "sitemaps, the old addresses, the 404 page, the home pages and the search.\n"
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
    finding = hub.sitecheck.Finding("robots.txt", "100% wrong\r\nhere")

    assert hub.sitecheck.annotation(finding, "site") == (
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
