"""Tests of .github/hub/watch.py: the daily watch of the live websites."""

from __future__ import annotations

import json
import re
import shutil
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlsplit

import pytest

import hub.address
import hub.catalog
import hub.reader
import hub.render
import hub.search
import hub.watch
import hub.web
from hub_helpers import (
    Files,
    ROOT,
    SITE,
    Websites,
    entry,
    guarded,
    hooks,
    index_of,
    page,
    repository,
    section,
)

# The watch of the catalog bot, which asks the live websites every day for what the
# hub depends on after its build.

WATCHED = datetime(2026, 10, 25, 6, 17, tzinfo=UTC)
FEED_URL = f"{SITE}repo-blueprint/dashboard/repos.json"
HISTORY_URL = f"{SITE}repo-blueprint/dashboard/history.json"
SECURITY_URLS = [f"{SITE}.well-known/security.txt", f"{SITE}security.txt"]
DAYS = [
    {
        "date": "2026-10-24",
        "repos": {
            "Dennis-Otto/homedarts-for-autodarts": {
                "coverage": 99.0,
                "mutation": None,
                "answer_hours": None,
            }
        },
    },
    {
        "date": "2026-10-25",
        "repos": {
            "Dennis-Otto/homedarts-for-autodarts": {
                "coverage": 100.0,
                "mutation": 91.4,
                "answer_hours": 2.5,
            }
        },
    },
]
SHAPE_FIX = (
    "read the new one in `docs/javascripts/projects.js`, and name it in "
    "`.github/dashboard-fields.json`."
)
DASHBOARD_FIX = (
    "The Dashboard workflow of repo-blueprint publishes it every few hours: look at "
    "its latest runs."
)
KIND_FIX = (
    "Read the new value in `docs/javascripts/projects.js`, and "
    "give its kind in `.github/dashboard-fields.json`."
)
REBUILD = (
    "Every build of this website writes it: start the Catalog workflow with the job "
    "rebuild, and look at the run of the Docs workflow that it starts."
)


def feed() -> dict[str, Any]:
    """repos.json of the dashboard, as the JS tests read it too."""
    data: dict[str, Any] = json.loads(
        (ROOT / "tests/fixtures/repos.json").read_text(encoding="utf-8")
    )
    return data


def live_files(today: date = WATCHED.date()) -> dict[str, bytes]:
    """Every file that the watch reads for the catalog of this repository by its
    address, as the live websites hold them when nothing needs attention, with the
    security.txt of a build on today."""
    catalog = hub.reader.load(ROOT)
    files = {
        FEED_URL: json.dumps(feed()).encode(),
        HISTORY_URL: json.dumps(DAYS).encode(),
    }
    for website in hub.search.websites(catalog, SITE):
        files[f"{SITE}{website.folder}search/search_index.json"] = index_of(
            section("index.html", "Home")
        )
    text = hub.address.security_txt(catalog, SITE, today).encode()
    for url in SECURITY_URLS:
        files[url] = text
    files[f"{SITE}robots.txt"] = hub.address.robots(catalog, SITE).encode()
    files[f"{SITE}sitemap.xml"] = sitemap_of(SITE)
    for path, html in hub.address.moved_pages(catalog).items():
        files[f"{SITE}{path}"] = html.encode()
    return files


def sitemap_of(*urls: str) -> bytes:
    """A sitemap with the pages at urls."""
    pages = "".join(f"<url><loc>{url}</loc></url>" for url in urls)
    return f"<urlset>{pages}</urlset>".encode()


def new_pages() -> dict[str, int]:
    """The status of the page in the folder now of every old address: 200."""
    catalog = hub.reader.load(ROOT)
    moves = catalog.moves()
    return {
        hub.address.moved_to(moves[folder], page): 200
        for folder, pages in catalog.former_pages.items()
        for page in pages
    }


def watched(
    files: dict[str, bytes] | None = None,
    pages: dict[str, int] | None = None,
    now: datetime = WATCHED,
) -> list[str]:
    """What the watch finds for the catalog of this repository in files and pages,
    or in the live websites when nothing needs attention, at the moment now."""
    return hub.watch.attention(
        hub.reader.load(ROOT),
        hub.watch.dashboard_fields(ROOT),
        Files(live_files() if files is None else files),
        Websites(new_pages() if pages is None else pages),
        now,
    )


def with_feed(change: Callable[[dict[str, Any]], object]) -> list[str]:
    """What the watch finds when change has changed repos.json."""
    data = feed()
    change(data)
    files = live_files()
    files[FEED_URL] = json.dumps(data).encode()
    return watched(files)


def with_days(days: object) -> list[str]:
    """What the watch finds when history.json holds days."""
    files = live_files()
    files[HISTORY_URL] = json.dumps(days).encode()
    return watched(files)


def test_the_watch_finds_nothing_when_the_websites_hold_what_the_hub_needs() -> None:
    catalog = hub.reader.load(ROOT)
    shape = hub.watch.dashboard_fields(ROOT)
    files = Files(live_files())
    pages = Websites(new_pages())

    assert hub.watch.attention(catalog, shape, files, pages, WATCHED) == []

    # It reads every file once: the data of the dashboard, the index of every
    # project website, the files at the root of the address and every old address,
    # and asks every page that an old address leads to for its status.
    assert files.asked == list(live_files())
    assert len(files.asked) == len(set(files.asked))
    assert pages.asked == list(new_pages())
    assert [url for url in files.asked if url.endswith("search_index.json")] == [
        f"{SITE}{website.folder}search/search_index.json"
        for website in hub.search.websites(catalog, SITE)
    ]


def test_the_shape_names_what_the_script_reads_of_the_data_of_the_dashboard() -> None:
    shape = hub.watch.dashboard_fields(ROOT)

    assert shape.schema == 1
    assert shape.repos == {
        "repo": "repository",
        "release": "text",
        "release_url": "github",
        "released": "day",
        "scorecard": "score",
        "health": "health",
    }
    assert shape.health == {
        "coverage": "share",
        "mutation": "share",
        "answer_hours": "hours",
    }
    assert shape.history == {"date": "date", "repos": "health by repository"}
    # The script names the same addresses of the data as the hooks.
    script = (ROOT / "docs/javascripts/projects.js").read_text(encoding="utf-8")
    assert f"const SCHEMA = {shape.schema};" in script
    assert f'data-facts="{hub.render.FEED}"' in script
    assert f'data-history="{hub.render.HISTORY}"' in script


@pytest.mark.parametrize(
    "change",
    [
        lambda data: data.update(schema=2),
        # A new schema may reshape `repos`; its fix is still the schema one.
        lambda data: data.update(schema=2, repos={}),
    ],
)
def test_a_new_schema_of_the_data_needs_the_script_to_learn_it(
    change: Callable[[dict[str, Any]], object],
) -> None:
    assert with_feed(change) == [
        f"{FEED_URL} has the schema 2, where `docs/javascripts/projects.js` knows 1, "
        "so the cards take the numbers of history.json alone, without their "
        "releases. Read the fields of the new schema in the script, and set its "
        "`SCHEMA` and `schema` of `.github/dashboard-fields.json` to it."
    ]


def test_a_field_that_the_data_lacks_is_named_with_its_entries() -> None:
    def change(data: dict[str, Any]) -> None:
        for entry in data["repos"][:6]:
            del entry["release"]
        del data["repos"][1]["health"]["coverage"]

    assert with_feed(change) == [
        f"`release` is missing in {FEED_URL} from these entries: "
        "`Dennis-Otto/dennis-otto.github.io`, `Dennis-Otto/homedarts-for-autodarts`, "
        "`Dennis-Otto/issue-assistant`, `Dennis-Otto/paperless-sync`, "
        "`Dennis-Otto/paperless-unified-search` and 1 more, so the website leaves "
        "its fact off the page. The dashboard of the blueprint took the field away "
        f"or renamed it: {SHAPE_FIX}",
        f"`coverage` is missing in {FEED_URL} from the health of these entries: "
        "`Dennis-Otto/homedarts-for-autodarts`, so the website leaves its fact off "
        "the page. The dashboard of the blueprint took the field away or renamed "
        f"it: {SHAPE_FIX}",
    ]


def test_a_value_of_another_kind_is_named_with_its_entries() -> None:
    def change(data: dict[str, Any]) -> None:
        data["repos"][0]["scorecard"] = "7.8"
        data["repos"][1]["released"] = "yesterday"
        data["repos"][2]["health"]["mutation"] = 0.91 * 1000
        data["repos"][3]["release_url"] = "https://example.com/release"
        data["repos"][4]["health"] = "good"
        data["repos"][5]["scorecard"] = 11

    def wrong(field: str, words: str, about: str, names: str) -> str:
        return (
            f"`{field}` in {FEED_URL} isn't {words} in {about}: {names}, so the "
            f"website leaves its fact off the page. {KIND_FIX}"
        )

    assert with_feed(change) == [
        wrong(
            "release_url",
            "an address at https://github.com/ or null",
            "these entries",
            "`Dennis-Otto/paperless-sync`",
        ),
        wrong(
            "released",
            "a day (such as 2026-10-25) or null",
            "these entries",
            "`Dennis-Otto/homedarts-for-autodarts`",
        ),
        wrong(
            "scorecard",
            "a number from 0 to 10 or null",
            "these entries",
            "`Dennis-Otto/dennis-otto.github.io` and "
            "`Dennis-Otto/player-switch-for-autodarts`",
        ),
        wrong(
            "health",
            "an object with the numbers of the health, or null",
            "these entries",
            "`Dennis-Otto/paperless-unified-search`",
        ),
        wrong(
            "mutation",
            "a number from 0 to 100 or null",
            "the health of these entries",
            "`Dennis-Otto/issue-assistant`",
        ),
    ]


def test_a_repository_that_the_data_lacks_keeps_the_facts_of_the_build() -> None:
    def change(data: dict[str, Any]) -> None:
        data["repos"] = [
            entry
            for entry in data["repos"]
            if entry["repo"] != "Dennis-Otto/paperless-sync"
        ] + ["no object"]
        data["repos"][0]["repo"] = None

    assert with_feed(change) == [
        f"1 of the 7 entries of `repos` in {FEED_URL} are no objects, which the "
        f"website leaves out. {DASHBOARD_FIX}",
        f"`repo` in {FEED_URL} isn't the name of a repository (such as "
        "Dennis-Otto/repo-blueprint) in these entries: `number 1`, so the website "
        f"leaves its fact off the page. {KIND_FIX}",
        # The hub has no card, so only paperless-sync is missing.
        f"{FEED_URL} has no entry for Dennis-Otto/paperless-sync, so its card keeps "
        "the facts of the build. The dashboard of the blueprint lists every public "
        "repository of the owner that is neither archived nor a fork, and adds a new "
        "one with its next run.",
    ]


@pytest.mark.parametrize(
    ("content", "problem"),
    [
        (None, "answers 404"),
        (b"<html></html>", "is no JSON (Expecting value: line 1 column 1 (char 0))"),
        (b'{"schema": 1, "repos": []}', "holds no list of repositories in `repos`"),
        (b"[]", "holds no list of repositories in `repos`"),
    ],
)
def test_data_of_the_dashboard_that_cant_be_read_keeps_the_facts_of_the_build(
    content: bytes | None, problem: str
) -> None:
    files = live_files()
    if content is None:
        del files[FEED_URL]
    else:
        files[FEED_URL] = content

    assert watched(files) == [
        f"{FEED_URL} {problem}, so the cards, the Trust page and the Releases page "
        f"keep the facts of the build. {DASHBOARD_FIX}"
    ]


@pytest.mark.parametrize(
    ("content", "problem"),
    [
        (None, "answers 404"),
        (
            b"{",
            "is no JSON (Expecting property name enclosed in double quotes: line 1 "
            "column 2 (char 1))",
        ),
        (b'{"days": []}', "holds no day, an object with `date` and `repos`"),
        (b"[null]", "holds no day, an object with `date` and `repos`"),
    ],
)
def test_a_history_that_cant_be_read_leaves_the_cards_nothing_to_fall_back_on(
    content: bytes | None, problem: str
) -> None:
    files = live_files()
    if content is None:
        del files[HISTORY_URL]
    else:
        files[HISTORY_URL] = content

    assert watched(files) == [
        f"{HISTORY_URL} {problem}, so the cards have no numbers to fall back on "
        "while repos.json has a shape that the website doesn't know. "
        f"{DASHBOARD_FIX}"
    ]


def test_the_history_needs_every_day_with_its_fields_and_the_latest_health() -> None:
    days = [
        {"repos": {}},
        {"date": "2026-10-23", "repos": []},
        {"date": "2026-10-25", "repos": {"Dennis-Otto/tool": {"coverage": 100}}},
        {"date": "2026-10-24", "repos": {"Dennis-Otto/tool": {"coverage": "all"}}},
    ]

    assert with_days(days) == [
        f"`date` is missing in {HISTORY_URL} from these days: `number 1`, so the "
        "website leaves its fact off the page. The dashboard of the blueprint took "
        f"the field away or renamed it: {SHAPE_FIX}",
        f"`repos` in {HISTORY_URL} isn't an object with the health of every "
        "repository by its name in these days: `2026-10-23`, so the website leaves "
        f"its fact off the page. {KIND_FIX}",
        # The script reads the latest day alone.
        *(
            f"`{name}` is missing in {HISTORY_URL} from the health on 2026-10-25 of "
            "these repositories: `Dennis-Otto/tool`, so the website leaves its fact "
            "off the page. The dashboard of the blueprint took the field away or "
            f"renamed it: {SHAPE_FIX}"
            for name in ("mutation", "answer_hours")
        ),
    ]


def test_a_history_without_a_complete_day_names_its_days_alone() -> None:
    assert with_days([{"date": "today", "repos": {}}]) == [
        f"`date` in {HISTORY_URL} isn't a day (such as 2026-10-25) in these days: "
        f"`today`, so the website leaves its fact off the page. {KIND_FIX}"
    ]


@pytest.mark.parametrize(
    ("kind", "fitting", "other"),
    [
        ("repository", ["Dennis-Otto/repo-blueprint"], [None, "repo-blueprint", 1]),
        ("date", ["2026-10-25"], [None, "2026-10-25T00:00:00Z", 20261025]),
        ("day", ["2026-10-25", None], ["25.10.2026", 1]),
        ("text", ["v1.0.0", "", None], [1, ["v1.0.0"]]),
        (
            "github",
            [f"{hub.catalog.GITHUB}Dennis-Otto/tool/releases", None],
            ["http://github.com/", 1],
        ),
        ("score", [0, 7.8, 10, None], [-1, 10.1, "7.8", True, float("nan")]),
        ("share", [0, 91.4, 100, None], [-0.1, 100.5, "100", False, float("inf")]),
        ("hours", [0, 2.5, 10_000, None], [-1, float("inf"), "2"]),
        ("health", [{}, {"coverage": 100}, None], [[], "good"]),
        (
            "health by repository",
            [{}, {"Dennis-Otto/tool": {}}],
            [None, [], {"tool": {}}, {"Dennis-Otto/tool": None}],
        ),
    ],
)
def test_every_kind_takes_the_values_that_the_script_takes(
    kind: str, fitting: list[object], other: list[object]
) -> None:
    fits = hub.watch.KINDS[kind].fits

    assert [fits(value) for value in fitting] == [True] * len(fitting)
    assert [fits(value) for value in other] == [False] * len(other)


def index_finding(folder: str, name: str, problem: str) -> str:
    """The sentence of the watch for the search index of the website in folder."""
    return (
        f"{SITE}{folder}/search/search_index.json {problem}, so the next build of "
        f"this website leaves the website of {name} out of its search. Look at the "
        "latest run of the workflow that publishes that website; if a new version of "
        "Material for MkDocs moved its index, change `SEARCH_INDEX` of "
        "`.github/hub/search.py`."
    )


def test_a_project_website_whose_index_is_missing_broken_or_empty_is_named() -> None:
    files = live_files()
    index = "{}search/search_index.json".format
    del files[SITE + index("homedarts-for-autodarts/")]
    files[SITE + index("paperless-sync/")] = b"Not Found"
    files[SITE + index("issue-assistant/")] = b'{"docs": {}}'
    files[SITE + index("repo-blueprint/")] = index_of()

    assert watched(files) == [
        index_finding(
            "homedarts-for-autodarts", "HomeDarts for Autodarts", "answers 404"
        ),
        index_finding(
            "paperless-sync",
            "Paperless Sync",
            "is no JSON: Expecting value: line 1 column 1 (char 0)",
        ),
        index_finding(
            "issue-assistant",
            "Issue assistant",
            "is no search index of Material for MkDocs: it needs docs, a list of "
            "entries with a location, a title and a text",
        ),
        index_finding("repo-blueprint", "Repo Blueprint", "holds no entry"),
    ]


def test_a_security_txt_that_the_daily_build_didnt_renew_is_named() -> None:
    # The website was last built 40 days ago, so both copies hold for 325 days.
    files = live_files(WATCHED.date() - timedelta(days=40))

    assert watched(files) == [
        f"{url} holds until 2027-09-15T00:00:00Z, 330 days or fewer from now, where "
        "every build of this website renews it to 365 days ahead: the website was "
        "last published on 2026-09-15, though the Catalog workflow builds it every "
        f"day. {REBUILD}"
        for url in SECURITY_URLS
    ]
    # One built 30 days ago is fine still.
    assert watched(live_files(WATCHED.date() - timedelta(days=30))) == []


@pytest.mark.parametrize(
    "text",
    [
        b"Contact: https://example.com/\n",
        b"Expires: 2027-10-25T00:00:00Z\nExpires: 2027-10-26T00:00:00Z\n",
        b"Expires: next year\n",
        b"Expires: 2027-10-25T00:00:00\n",
    ],
)
def test_a_security_txt_without_one_expiry_with_its_zone_is_named(text: bytes) -> None:
    files = live_files()
    files[SECURITY_URLS[1]] = text

    assert watched(files) == [
        f"{SECURITY_URLS[1]} names no Expires with a time of RFC 3339, such as "
        "2027-10-25T00:00:00Z, so security researchers can't tell whether it holds. "
        f"{REBUILD}"
    ]


def test_the_files_at_the_root_that_are_missing_are_named() -> None:
    files = live_files()
    for url in [*SECURITY_URLS, f"{SITE}robots.txt", f"{SITE}sitemap.xml"]:
        del files[url]

    assert watched(files) == [
        *(
            f"{url} answers 404, so security researchers find no way to report a "
            f"vulnerability privately. {REBUILD}"
            for url in SECURITY_URLS
        ),
        f"{SITE}robots.txt answers 404, so crawlers find the sitemap of no website "
        f"of the address. {REBUILD}",
        f"{SITE}sitemap.xml answers 404, so crawlers find no page of this website. "
        f"{REBUILD}",
    ]


def test_a_robots_txt_without_a_sitemap_and_a_sitemap_without_the_root() -> None:
    files = live_files()
    robots = files[f"{SITE}robots.txt"].decode()
    files[f"{SITE}robots.txt"] = robots.replace(
        f"Sitemap: {SITE}paperless-sync/sitemap.xml\n", ""
    ).encode()
    files[f"{SITE}sitemap.xml"] = sitemap_of(f"{SITE}de/")

    assert watched(files) == [
        f"{SITE}robots.txt names no Sitemap: `{SITE}paperless-sync/sitemap.xml`, so "
        "crawlers find those websites later. robots() of `.github/hub/address.py` "
        "names the sitemap of every website of projects.toml at the address. "
        f"{REBUILD}",
        f"{SITE}sitemap.xml doesn't list {SITE}, the home page of the address. "
        "sitemaps_at_root() of `.github/hub/address.py` leads it there after the "
        f"build. {REBUILD}",
    ]


def test_an_old_address_that_is_missing_astray_or_leads_nowhere_is_named() -> None:
    files = live_files()
    old = f"{SITE}ha-autodarts/"
    new = f"{SITE}homedarts-for-autodarts/"
    del files[f"{old}index.html"]
    files[f"{old}cards.html"] = b"<html><head></head></html>"
    pages = new_pages()
    pages[f"{new}automations.html"] = 404

    assert watched(files, pages) == [
        f"Old addresses of {old} that answer 404, though `former/ha-autodarts.txt` "
        "lists them: `index.html`. Old links lead to the 404 page there; "
        "on_post_build of `.github/hub/events.py` writes a page at each that "
        f"leads to {new}. {REBUILD}",
        f"Old addresses of {old} that don't lead to the same page in {new}: "
        "`cards.html`. moved_page() of `.github/hub/address.py` writes each with "
        "its canonical address and its refresh, so remove what writes them after "
        f"the hooks, such as a file in docs/. {REBUILD}",
        f"Old addresses of {old} whose pages in {new} answer 404, since the website "
        "of HomeDarts for Autodarts moved or removed them: `automations.html`. Bring "
        "each page back there, such as with a page that leads to its new place, or "
        "remove its line from `former/ha-autodarts.txt` once it is gone for good.",
    ]


def test_a_new_page_that_answers_oddly_is_no_finding_but_a_question() -> None:
    pages = new_pages()
    pages[f"{SITE}homedarts-for-autodarts/cards.html"] = 503

    with pytest.raises(hub.web.CheckError) as stop:
        watched(pages=pages)

    assert str(stop.value) == (
        f"{SITE}homedarts-for-autodarts/cards.html answers 503, where the catalog "
        "bot expects 200 or 404; start it again later."
    )


def test_a_lost_answer_is_asked_again_once() -> None:
    answers: list[Any] = [hub.web.CheckError("lost"), b"found"]
    asked: list[str] = []

    def ask(url: str) -> bytes:
        asked.append(url)
        answer = answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return bytes(answer)

    assert hub.watch.patient(ask)(SITE) == b"found"
    assert asked == [SITE, SITE]


def test_an_answer_lost_twice_is_a_question() -> None:
    asked: list[str] = []

    def ask(url: str) -> bytes:
        asked.append(url)
        raise hub.web.CheckError(f"{url} can't be reached: lost")

    with pytest.raises(hub.web.CheckError, match="can't be reached: lost"):
        hub.watch.patient(ask)(SITE)
    assert asked == [SITE] * hub.web.TRIES


@pytest.mark.parametrize(
    ("text", "problem"),
    [
        (None, "FileNotFoundError("),
        ("{", "JSONDecodeError("),
        ("[]", "TypeError("),
        ('{"schema": 1}', "KeyError('repos')"),
    ],
)
def test_a_shape_that_cant_be_read_is_a_question(
    tmp_path: Path, text: str | None, problem: str
) -> None:
    if text is not None:
        (tmp_path / ".github").mkdir()
        (tmp_path / ".github/dashboard-fields.json").write_text(text, encoding="utf-8")

    with pytest.raises(hub.web.CheckError) as stop:
        hub.watch.dashboard_fields(tmp_path)

    assert str(stop.value).startswith(
        f".github/dashboard-fields.json can't be read: {problem}"
    )


@pytest.mark.parametrize(
    "change",
    [
        {"schema": "1"},
        {"schema": True},
        {"repos": []},
        {"health": {}},
        {"history": {"date": "time"}},
    ],
)
def test_a_shape_with_an_unknown_kind_is_a_question(
    tmp_path: Path, change: dict[str, Any]
) -> None:
    data = json.loads(
        (ROOT / ".github/dashboard-fields.json").read_text(encoding="utf-8")
    )
    (tmp_path / ".github").mkdir()
    (tmp_path / ".github/dashboard-fields.json").write_text(
        json.dumps(data | change), encoding="utf-8"
    )

    with pytest.raises(hub.web.CheckError) as stop:
        hub.watch.dashboard_fields(tmp_path)

    assert str(stop.value) == (
        ".github/dashboard-fields.json needs schema, the number of the shape of "
        "repos.json that docs/javascripts/projects.js knows, and repos, health and "
        "history, each the kind of every field that the script reads by its name, "
        "one of: repository, date, day, text, github, score, share, hours, health, "
        "health by repository."
    )


def watch_repository(root: Path) -> None:
    """A copy of what the watch reads of this repository at root."""
    repository(root)
    (root / ".github").mkdir()
    shutil.copyfile(
        ROOT / ".github/dashboard-fields.json", root / ".github/dashboard-fields.json"
    )


def test_the_script_finds_that_nothing_needs_attention(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    watch_repository(tmp_path)
    # security.txt of a build of today, as the daily build writes it.
    monkeypatch.setattr(hub.web, "fetched", Files(live_files(datetime.now(UTC).date())))
    monkeypatch.setattr(hub.web, "status", Websites(new_pages()))

    assert hooks.main(["--watch"], tmp_path) == 0

    assert capsys.readouterr() == (
        f"The live websites at {SITE} hold what this website depends on: the data of "
        "the dashboard in the shape that docs/javascripts/projects.js reads, the "
        "search index of every project website, security.txt for more than 330 "
        "days, robots.txt with every sitemap, the sitemap of this website, and a "
        "page at every old address that leads to its page now.\n",
        "",
    )


def test_the_script_writes_the_issue_when_something_needs_attention(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    watch_repository(tmp_path)
    files = live_files(datetime.now(UTC).date())
    del files[f"{SITE}robots.txt"]
    monkeypatch.setattr(hub.web, "fetched", Files(files))
    monkeypatch.setattr(hub.web, "status", Websites(new_pages()))

    assert hooks.main(["--watch"], tmp_path) == hub.catalog.DIFFERS

    assert capsys.readouterr() == (
        f"The watch of the catalog bot asks the live websites at {SITE} every day for "
        "what this website depends on after its build, and found 1 thing(s) that "
        "need attention:\n"
        "\n"
        f"- {SITE}robots.txt answers 404, so crawlers find the sitemap of no website "
        f"of the address. {REBUILD}\n"
        "\n"
        "The next run closes this issue once nothing needs attention; start the "
        "Catalog workflow by hand with the job watch to check sooner, or run\n"
        "\n"
        "```sh\n"
        "python3 -I .github/mkdocs_project.py --watch\n"
        "```\n",
        "",
    )


def test_the_script_cant_tell_when_a_website_cant_be_reached(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    watch_repository(tmp_path)
    asked: list[str] = []

    def fetched(url: str) -> bytes | None:
        asked.append(url)
        raise hub.web.CheckError(f"{url} can't be reached: timed out")

    monkeypatch.setattr(hub.web, "fetched", fetched)

    assert hooks.main(["--watch"], tmp_path) == 2

    assert capsys.readouterr() == ("", f"{FEED_URL} can't be reached: timed out\n")
    # Each address is asked twice before the watch gives up.
    assert asked == [FEED_URL] * hub.web.TRIES


def test_the_script_cant_tell_without_the_shape(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repository(tmp_path)

    assert hooks.main(["--watch"], tmp_path) == 2

    assert capsys.readouterr().err.startswith(
        ".github/dashboard-fields.json can't be read: FileNotFoundError("
    )


def test_the_workflow_watches_the_live_websites_every_day() -> None:
    workflow = (ROOT / ".github/workflows/catalog.yml").read_text(encoding="utf-8")
    watch = workflow[workflow.index("\n  watch:\n") :]

    assert '- cron: "17 6 * * *"' in workflow
    assert "          - watch\n" in workflow
    assert "if: github.event.schedule == '17 6 * * *' || inputs.job == 'watch'" in watch
    assert "python3 -I .github/mkdocs_project.py --watch " in watch
    # It reads the repository and writes its issue, and nothing else.
    assert re.findall(r"^ +([a-z-]+): (read|write)\b", watch, re.MULTILINE) == [
        ("contents", "read"),
        ("issues", "write"),
    ]
    assert "persist-credentials: false" in watch
    assert 'title="The live websites need attention"' in watch
    assert "--label maintenance" in watch
    # Its findings are in the summary of the job too.
    assert 'cat "$REPORT" >>"$GITHUB_STEP_SUMMARY"' in watch


def test_the_watch_reaches_only_github_and_the_address_of_the_websites() -> None:
    workflow = (ROOT / ".github/workflows/catalog.yml").read_text(encoding="utf-8")

    # gh asks api.github.com and the checkout github.com; the watch reads the live
    # websites at SITE, the data of the dashboard among them, and nothing else.
    assert guarded(workflow[workflow.index("\n  watch:\n") :]) == [
        "api.github.com:443",
        "github.com:443",
        f"{urlsplit(hub.catalog.SITE).hostname}:443",
    ]
    assert urljoin(hub.catalog.SITE, hub.render.FEED).startswith(hub.catalog.SITE)
    assert urljoin(hub.catalog.SITE, hub.render.HISTORY).startswith(hub.catalog.SITE)
