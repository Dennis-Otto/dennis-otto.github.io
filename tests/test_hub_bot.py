"""Tests of the comparison of the catalog bot in .github/hub/bot.py, of its issue and
of its workflow.
"""

from __future__ import annotations

import http.client
import json
import re
import tomllib
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import pytest

import hub.bot
import hub.catalog
import hub.reader
import hub.web
from hub_helpers import (
    ADVICE,
    Files,
    GERMAN_SITES,
    ROOT,
    SITE,
    TODAY,
    Websites,
    catalog_data,
    drawn_files,
    drift,
    entry,
    found,
    guarded,
    hooks,
    in_french,
    listed_repo,
    lists,
    network_files,
    one_language,
    repository,
    without_card,
    without_repo,
)


def drawing_files() -> dict[str, bytes]:
    """drawn_files of every project of the catalog of this repository."""
    files: dict[str, bytes] = {}
    for project in hub.reader.load(ROOT).projects:
        files |= drawn_files(project)
    return files


def test_the_catalog_of_the_repository_is_current() -> None:
    websites = Websites(GERMAN_SITES)
    files = Files(network_files())

    assert hub.bot.drift(hub.reader.load(ROOT), found(*TODAY), websites, files) == []
    # The file of every project that reads what it works with from one, and those
    # from which the hub draws its pictures.
    assert files.asked == list(network_files())
    # The German website of every project at the address: those of the catalog,
    # and those that may have appeared.
    assert websites.asked == [
        f"{project.docs.url['en']}de/"
        for project in hub.reader.load(ROOT).projects
        if project.docs is not None
    ]


def test_the_bot_compares_with_the_address_of_the_website() -> None:
    settings = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    site_url = re.search(r"^site_url: (\S+)$", settings, re.MULTILINE)

    assert site_url is not None
    assert hub.catalog.SITE == site_url[1] == SITE


def test_a_new_repository_with_a_website_at_the_address_needs_a_project() -> None:
    repositories = found(
        listed_repo("tool", f"{SITE}tool/"),
        listed_repo("new-thing", "https://Dennis-Otto.github.io/new-thing"),
    )

    assert drift(one_language(), repositories=repositories) == [
        "Dennis-Otto/new-thing has its website at "
        "https://Dennis-Otto.github.io/new-thing, but projects.toml has no project "
        'for it. Add a `[[project]]` with `repo = "Dennis-Otto/new-thing"`.'
    ]


def test_new_repositories_follow_the_catalog_by_their_names() -> None:
    repositories = found(
        listed_repo("tool", f"{SITE}tool-docs/"),
        listed_repo("zebra", f"{SITE}zebra/"),
        listed_repo("Alpaca", f"{SITE}alpaca/"),
    )

    differences = drift(one_language(), repositories=repositories)

    assert [difference.split()[0] for difference in differences] == [
        "`tool`:",
        "Dennis-Otto/Alpaca",
        "Dennis-Otto/zebra",
    ]


def test_a_repository_without_a_website_at_the_address_needs_no_project() -> None:
    repositories = found(
        listed_repo("tool", f"{SITE}tool/"),
        # An archived and a private repository, which the issue never names.
        listed_repo("old", f"{SITE}old/", archived=True),
        listed_repo("secret", f"{SITE}secret/", private=True),
        # This website, at the root of the address, and websites elsewhere.
        listed_repo("dennis-otto.github.io", "https://dennis-otto.github.io"),
        listed_repo("app", "https://example.org/app/"),
        listed_repo("lookalike", "https://dennis-otto.github.io.example.org/x/"),
        listed_repo("empty", ""),
        listed_repo("none", None),
    )

    assert drift(one_language(), repositories=repositories) == []


def test_a_repository_with_the_website_of_a_project_needs_no_other() -> None:
    repositories = found(
        listed_repo("tool", f"{SITE}tool/"),
        listed_repo("tool-mirror", f"{SITE}tool/"),
    )

    assert drift(one_language(), repositories=repositories) == []


def test_a_renamed_repository_is_found_by_its_website() -> None:
    repositories = found(listed_repo("better-tool", f"{SITE}tool"))

    assert drift(one_language(), repositories=repositories) == [
        "`tool`: Dennis-Otto/tool is no repository on GitHub any more, and "
        f"Dennis-Otto/better-tool has its website {SITE}tool/; it was renamed. Set "
        '`repo = "Dennis-Otto/better-tool"`.'
    ]


def test_a_repository_that_is_gone_is_named() -> None:
    repositories = found(listed_repo("other", "https://example.org/"))

    assert drift(one_language(), repositories=repositories) == [
        "`tool`: Dennis-Otto/tool is no public repository on GitHub any more; it "
        "was renamed, made private or deleted. Correct `repo`, or remove the "
        "project."
    ]


def test_the_repository_of_another_project_is_no_successor() -> None:
    # board names the website of tool on GitHub, whose repository is gone.
    repositories = found(listed_repo("board", f"{SITE}tool/"))

    assert drift(one_language(), one_language("board"), repositories=repositories) == [
        "`tool`: Dennis-Otto/tool is no public repository on GitHub any more; it "
        "was renamed, made private or deleted. Correct `repo`, or remove the "
        "project.",
        f"`board`: Dennis-Otto/board names {SITE}tool/ as its website on GitHub, "
        f"but projects.toml leads to {SITE}board/. Correct `docs`, or the website "
        "of the repository.",
    ]


PRIVATE = (
    "`tool`: Dennis-Otto/tool is private now. Remove the project, or make the "
    "repository public again."
)


@pytest.mark.parametrize(
    ("archived", "private", "message"),
    [
        (
            True,
            False,
            "`tool`: Dennis-Otto/tool is archived. Remove the project, or unarchive "
            "the repository.",
        ),
        (False, True, PRIVATE),
        (True, True, PRIVATE),
    ],
)
def test_an_archived_or_private_repository_of_the_catalog_is_named(
    archived: bool, private: bool, message: str
) -> None:
    repositories = found(
        listed_repo("tool", f"{SITE}tool/", archived=archived, private=private)
    )

    assert drift(one_language(), repositories=repositories) == [message]


@pytest.mark.parametrize(
    "homepage",
    [
        f"{SITE}tool/",
        f"{SITE}tool",
        "https://DENNIS-OTTO.github.io/tool/",
        "http://dennis-otto.github.io/tool/",
        # A website elsewhere, or none, is the repository's own business.
        "https://example.org/tool/",
        "",
    ],
)
def test_a_repository_with_the_website_of_its_project_is_current(
    homepage: str,
) -> None:
    repositories = found(listed_repo("tool", homepage))

    assert drift(one_language(), repositories=repositories) == []


def test_a_repository_with_another_website_at_the_address_is_named() -> None:
    repositories = found(listed_repo("tool", f"{SITE}tool-docs/"))

    assert drift(one_language(), repositories=repositories) == [
        f"`tool`: Dennis-Otto/tool names {SITE}tool-docs/ as its website on GitHub, "
        f"but projects.toml leads to {SITE}tool/. Correct `docs`, or the website of "
        "the repository."
    ]


def test_a_project_without_a_repository_has_none_to_compare() -> None:
    board = without_card(without_repo(one_language("board")))
    tool = one_language(second="board")

    assert drift(tool, board, repositories=found(listed_repo("tool"))) == []


def test_a_german_website_that_appeared_is_named() -> None:
    websites = Websites({f"{SITE}tool/de/": 200})

    assert drift(
        one_language(), repositories=found(listed_repo("tool")), websites=websites
    ) == [
        f"`tool`: it has a German website at {SITE}tool/de/ now. Write "
        f'`docs.en = "{SITE}tool/"` and `docs.de = "{SITE}tool/de/"` in place of '
        "`docs`, so that the German home page leads there."
    ]
    assert websites.asked == [f"{SITE}tool/de/"]


def test_the_fix_for_a_german_website_that_appeared_is_valid_toml() -> None:
    # A project in English alone writes docs as one address, beside which a docs.de
    # would be a second value of docs, so the issue has docs replaced instead.
    written = f'docs = "{SITE}tool/"\n'
    repositories = found(listed_repo("tool"))
    websites = Websites({f"{SITE}tool/de/": 200})
    [difference] = drift(
        entry(**tomllib.loads(written)), repositories=repositories, websites=websites
    )
    keys = re.findall(r'`(docs\.\w+ = "[^"]+")`', difference)
    fixed = "".join(f"{key}\n" for key in keys)

    assert len(keys) == 2
    assert (
        drift(
            entry(**tomllib.loads(fixed)), repositories=repositories, websites=websites
        )
        == []
    )


def test_the_folder_of_a_language_is_found_without_the_slash_of_the_website() -> None:
    websites = Websites()

    drift(
        entry(docs=f"{SITE}tool"),
        repositories=found(listed_repo("tool")),
        websites=websites,
    )

    assert websites.asked == [f"{SITE}tool/de/"]


@pytest.mark.parametrize("code", [404, 410])
def test_a_german_website_that_is_gone_is_named(code: int) -> None:
    websites = Websites({f"{SITE}tool/de/": code})
    repositories = found(listed_repo("tool"))

    assert drift(entry(), repositories=repositories, websites=websites) == [
        f"`tool`: the German website {SITE}tool/de/ is gone. Remove `docs.de`, so "
        "that the German home page leads to the English one."
    ]
    assert websites.asked == [f"{SITE}tool/de/"]


def test_a_german_website_of_the_catalog_is_current() -> None:
    websites = Websites({f"{SITE}tool/de/": 200})
    repositories = found(listed_repo("tool"))

    assert drift(entry(), repositories=repositories, websites=websites) == []


def test_only_a_website_at_the_address_is_asked_for_its_languages() -> None:
    websites = Websites()
    elsewhere = entry(docs="https://example.org/tool/")
    without_docs = entry("board")
    del without_docs["docs"]
    repositories = found(listed_repo("tool"), listed_repo("board"))

    differences = drift(
        elsewhere, without_docs, repositories=repositories, websites=websites
    )

    assert differences == []
    assert websites.asked == []


def test_a_language_without_a_name_is_named_by_its_code() -> None:
    data = in_french(catalog_data(one_language()))
    data["languages"] = ["en", "fr"]
    websites = Websites({f"{SITE}tool/fr/": 200})

    assert hub.bot.drift(
        hub.reader.read(data), found(listed_repo("tool")), websites, Files()
    ) == [
        f"`tool`: it has a fr website at {SITE}tool/fr/ now. Write "
        f'`docs.en = "{SITE}tool/"` and `docs.fr = "{SITE}tool/fr/"` in place of '
        "`docs`, so that the fr home page leads there."
    ]


@pytest.mark.parametrize(
    ("languages", "code"),
    [("one", 500), ("both", 403), ("both", 301)],
)
def test_an_odd_answer_of_a_website_stops_the_bot(languages: str, code: int) -> None:
    project = one_language() if languages == "one" else entry()
    websites = Websites({f"{SITE}tool/de/": code})

    with pytest.raises(hub.web.CheckError) as error:
        drift(project, repositories=found(listed_repo("tool")), websites=websites)

    assert str(error.value) == (
        f"{SITE}tool/de/ answers {code}, where the catalog bot expects 200 or 404; "
        "start it again later."
    )


@pytest.mark.parametrize(
    ("url", "wanted"),
    [
        (f"{SITE}tool/", f"{SITE}tool/"),
        (" https://Dennis-Otto.GitHub.io/tool ", f"{SITE}tool/"),
        ("http://dennis-otto.github.io/tool//", f"{SITE}tool/"),
        ("https://dennis-otto.github.io", SITE),
        ("", "https:///"),
    ],
)
def test_addresses_are_compared_as_github_pages_serves_them(
    url: str, wanted: str
) -> None:
    assert hub.web.address(url) == wanted


@pytest.mark.parametrize(
    ("url", "wanted"),
    [
        (f"{SITE}tool/", True),
        (f"{SITE}tool/de/", True),
        (SITE, False),
        ("https://dennis-otto.github.io.example.org/tool/", False),
        ("https://example.org/", False),
        ("", False),
    ],
)
def test_a_website_of_a_project_is_in_a_folder_of_the_address(
    url: str, wanted: bool
) -> None:
    assert hub.web.at_site(url) is wanted


def test_the_list_of_the_repositories_takes_a_missing_website_as_none() -> None:
    repositories = found(
        listed_repo("tool", None),
        listed_repo("app", "https://x.org/", archived=True, private=True),
    )

    assert repositories == [
        hub.bot.Repository("Dennis-Otto/tool", "", archived=False, private=False),
        hub.bot.Repository(
            "Dennis-Otto/app", "https://x.org/", archived=True, private=True
        ),
    ]


@pytest.mark.parametrize(
    "items",
    [
        {},
        [],
        ["Dennis-Otto/tool"],
        [{"nameWithOwner": "Dennis-Otto/tool"}],
        [{**listed_repo("tool"), "nameWithOwner": None}],
        [{**listed_repo("tool"), "homepageUrl": 1}],
        [{**listed_repo("tool"), "isArchived": "false"}],
        [{**listed_repo("tool"), "isPrivate": None}],
        [listed_repo("tool"), None],
    ],
)
def test_a_broken_list_of_the_repositories_stops_the_bot(items: object) -> None:
    with pytest.raises(hub.web.CheckError) as error:
        hub.bot.repositories(json.dumps(items))

    assert str(error.value) == (
        "The list of the repositories must be the JSON of gh repo list --json "
        "nameWithOwner,homepageUrl,isArchived,isPrivate, with one at least."
    )


def test_a_list_of_the_repositories_that_is_no_json_stops_the_bot() -> None:
    with pytest.raises(hub.web.CheckError) as error:
        hub.bot.repositories("GraphQL: Could not resolve to a User")

    assert str(error.value).startswith(
        "The list of the repositories isn't the JSON of gh repo list --json "
        "nameWithOwner,homepageUrl,isArchived,isPrivate: Expecting value"
    )


def test_the_issue_names_every_difference_and_how_to_fix_it() -> None:
    text = hub.bot.report(["`tool`: one.", "Dennis-Otto/app: two."])

    assert text == (
        "The catalog bot compares projects.toml with the repositories on GitHub, with "
        "the websites of the projects in every language and with the files that say "
        "what they work with every week, and found 2 difference(s):\n"
        "\n"
        "- `tool`: one.\n"
        "- Dennis-Otto/app: two.\n"
        "\n"
        "Change projects.toml, whose comments describe every key, and write the "
        "tables of the READMEs with\n"
        "\n"
        "```sh\n"
        "python3 -I .github/mkdocs_project.py --write\n"
        "```\n"
        "\n"
        "A new card needs its picture too, which `bash scripts/project-pictures.sh` "
        "makes. The next run closes this issue once the catalog is current; start "
        "the Catalog workflow by hand to check sooner.\n"
    )


def test_the_workflow_of_the_bot_compares_every_week() -> None:
    workflow = (ROOT / ".github/workflows/catalog.yml").read_text(encoding="utf-8")

    assert '- cron: "23 5 * * 1"' in workflow
    assert "  workflow_dispatch:\n" in workflow
    # gh lists the fields that the comparison reads, and the bot runs it.
    assert f"--json {','.join(hub.bot.FIELDS)} " in workflow
    assert "python3 -I .github/mkdocs_project.py --network " in workflow
    # It reads the repository and writes the issue, and nothing else.
    catalog = workflow[: workflow.index("\n  catalog-pull-request:\n")]
    assert "\npermissions: {}\n" in workflow
    assert re.findall(r"^ +([a-z-]+): (read|write)\b", catalog, re.MULTILINE) == [
        ("contents", "read"),
        ("issues", "write"),
    ]
    assert "persist-credentials: false" in catalog
    assert 'title="The project catalog is out of date"' in catalog
    # By hand, it compares unless it is asked to build the website.
    assert "if: github.event.schedule == '23 5 * * 1' || inputs.job == 'catalog'" in (
        catalog
    )
    assert "        default: catalog\n" in catalog


def test_the_workflow_of_the_bot_builds_the_website_every_day() -> None:
    workflow = (ROOT / ".github/workflows/catalog.yml").read_text(encoding="utf-8")
    rebuild = workflow[
        workflow.index("\n  rebuild:\n") : workflow.index("\n  watch:\n")
    ]

    assert '- cron: "41 4 * * *"' in workflow
    assert "if: github.event.schedule == '41 4 * * *' || inputs.job == 'rebuild'" in (
        rebuild
    )
    # It starts the Docs workflow on main, which publishes the website, and may do
    # nothing else.
    assert "run: gh workflow run docs.yml --ref main\n" in rebuild
    assert re.findall(r"^ +([a-z-]+): (read|write)\b", rebuild, re.MULTILINE) == [
        ("actions", "write")
    ]
    assert "actions/checkout" not in rebuild
    # The group is that of the job, not that of the trigger: a comparison started
    # by hand and the one of Monday wait for each other, and so do two watches.
    assert (
        "  group: ${{ github.workflow }}-${{ (github.event.schedule == '17 6 * * *'"
        " || inputs.job == 'watch') && 'watch' || (github.event.schedule == "
        "'41 4 * * *' || inputs.job == 'rebuild') && 'rebuild' || 'catalog' }}\n"
    ) in workflow
    docs = (ROOT / ".github/workflows/docs.yml").read_text(encoding="utf-8")
    assert "\n  workflow_dispatch:\n" in docs


def test_the_bot_reaches_only_github_and_the_address_of_the_websites() -> None:
    workflow = (ROOT / ".github/workflows/catalog.yml").read_text(encoding="utf-8")
    hosts = guarded(
        workflow[
            workflow.index("\n  catalog:\n") : workflow.index(
                "\n  catalog-pull-request:\n"
            )
        ]
    )

    # gh asks api.github.com and the checkout github.com; the comparison asks the
    # websites at SITE for their status and reads the files that say what a
    # project works with from RAW, its edits go to the store of the artifacts, and
    # it reaches nothing else.
    assert hosts == [
        "api.github.com:443",
        "github.com:443",
        f"{urlsplit(hub.catalog.SITE).hostname}:443",
        f"{urlsplit(hub.web.RAW).hostname}:443",
        "results-receiver.actions.githubusercontent.com:443",
    ]
    assert "egress-policy: audit" not in workflow
    # The bot asks every website in a further language of a project whose website
    # is at SITE, so one on another host would be blocked.
    catalog = hub.reader.load(ROOT)
    for project in catalog.projects:
        if project.docs is not None and hub.web.at_site(
            project.docs.url[catalog.default]
        ):
            for url in project.docs.url.values():
                assert f"{urlsplit(url).hostname}:443" in hosts, url


def test_the_rebuild_reaches_only_the_api_of_github() -> None:
    workflow = (ROOT / ".github/workflows/catalog.yml").read_text(encoding="utf-8")

    # gh workflow run asks api.github.com alone, and the job checks out nothing.
    rebuild = workflow[
        workflow.index("\n  rebuild:\n") : workflow.index("\n  watch:\n")
    ]
    assert guarded(rebuild) == ["api.github.com:443"]


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (http.client.BadStatusLine("HTTP/9 OK"), "HTTP/9 OK"),
        (http.client.RemoteDisconnected("closed"), "closed"),
        (ValueError("unknown url type"), "unknown url type"),
    ],
)
def test_a_website_that_answers_brokenly_stops_the_bot(
    monkeypatch: pytest.MonkeyPatch, error: Exception, message: str
) -> None:
    def urlopen(request: Any, timeout: float) -> Response:
        raise error

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)

    with pytest.raises(hub.web.CheckError) as stop:
        hub.web.status(f"{SITE}tool/de/")

    assert str(stop.value) == f"{SITE}tool/de/ can't be reached: {message}"


def test_a_crash_of_the_bot_cant_pass_for_a_difference() -> None:
    # Python exits with 1 when it stops with an exception and argparse with 2, so
    # the workflow takes only DIFFERS for the text of an issue, of the comparison
    # and of the watch alike.
    workflow = (ROOT / ".github/workflows/catalog.yml").read_text(encoding="utf-8")
    cases = re.findall(r"^ {12}(\S+)\)", workflow, re.MULTILINE)

    assert hub.catalog.DIFFERS not in {0, 1, 2}
    assert cases == ["0", str(hub.catalog.DIFFERS), "*"] * 2


def test_an_unexpected_error_of_the_bot_isnt_a_difference(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository(tmp_path)

    def status(url: str) -> int:
        raise RuntimeError(url)

    monkeypatch.setattr(hub.web, "status", status)

    # It reaches Python, which exits with 1, never with DIFFERS.
    with pytest.raises(RuntimeError):
        hooks.main(["--network", str(lists(tmp_path, *TODAY))], tmp_path)


def test_the_script_finds_the_catalog_of_the_repository_current(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Without a README, which the comparison doesn't need.
    repository(tmp_path).unlink()
    monkeypatch.setattr(hub.web, "status", Websites(GERMAN_SITES))
    monkeypatch.setattr(hub.web, "fetched", Files(network_files()))

    assert hooks.main(["--network", str(lists(tmp_path, *TODAY))], tmp_path) == 0

    assert capsys.readouterr() == (
        "projects.toml is current: it has every repository with a website at "
        f"{SITE}, every website in a further language, every file that says "
        "what a project works with, and every file from which the hub draws a "
        "picture of a card.\n",
        "",
    )


def test_the_script_writes_the_issue_when_the_catalog_differs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    repository(tmp_path)
    # Every German website is gone, those of the catalog among them, and every file
    # that says what a project works with; the pictures are there.
    monkeypatch.setattr(hub.web, "status", Websites())
    monkeypatch.setattr(hub.web, "fetched", Files(drawing_files()))
    new = listed_repo("new-thing", f"{SITE}new-thing/")

    assert hooks.main(["--network", str(lists(tmp_path, *TODAY, new))], tmp_path) == 3

    output = capsys.readouterr()
    assert output.err == ""
    differences = []
    for project in hub.reader.load(ROOT).projects:
        slug = project.slug
        if project.docs is not None and project.docs.url["de"] in GERMAN_SITES:
            differences.append(
                f"`{slug}`: the German website {SITE}{slug}/de/ is gone. Remove "
                "`docs.de`, so that the German home page leads to the English one."
            )
        if isinstance(project.requires, hub.catalog.Source):
            differences.append(
                f"`{slug}`: Dennis-Otto/{slug} has no {project.requires.file} any "
                f"more, from which its card reads what it works with. {ADVICE}"
            )

    assert output.out == hub.bot.report(
        [
            *differences,
            f"Dennis-Otto/new-thing has its website at {SITE}new-thing/, but "
            "projects.toml has no project for it. Add a `[[project]]` with "
            '`repo = "Dennis-Otto/new-thing"`.',
        ]
    )


@pytest.mark.parametrize(
    ("catalog", "items", "message"),
    [
        (True, None, "repositories.json"),
        (True, [], "The list of the repositories must be"),
        (False, [listed_repo("tool")], "projects.toml can't be read"),
    ],
)
def test_the_script_says_when_it_cant_tell(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    catalog: bool,
    items: list[dict[str, Any]] | None,
    message: str,
) -> None:
    if catalog:
        repository(tmp_path)
    if items is not None:
        lists(tmp_path, *items)

    path = tmp_path / "repositories.json"
    assert hooks.main(["--network", str(path)], tmp_path) == 2

    output = capsys.readouterr()
    assert output.out == ""
    assert message in output.err


def test_the_script_says_when_a_website_cant_be_reached(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    repository(tmp_path)

    def status(url: str) -> int:
        raise hub.web.CheckError(f"{url} can't be reached: timed out")

    monkeypatch.setattr(hub.web, "status", status)

    assert hooks.main(["--network", str(lists(tmp_path, *TODAY))], tmp_path) == 2
    assert capsys.readouterr() == (
        "",
        f"{SITE}homedarts-for-autodarts/de/ can't be reached: timed out\n",
    )
