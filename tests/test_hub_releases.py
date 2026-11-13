"""Tests of .github/hub/releases.py: the Releases page and What's new, from the API
of GitHub.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import hub.reader
import hub.releases
import hub.render
import hub.web
from hub_helpers import (
    Download,
    catalog_data,
    entry,
    hooks,
    page,
    release,
    without_repo,
)

# The releases of the projects: What's new and the Releases page.


def release_data(tag: str | None = "v1.0.0", **changes: Any) -> dict[str, Any]:
    """A release as the API of GitHub lists it, with its notes as the HTML that
    GitHub makes of their Markdown."""
    data: dict[str, Any] = {
        "tag_name": tag,
        "name": tag,
        "draft": False,
        "prerelease": False,
        "published_at": "2026-10-23T19:04:13Z",
        "html_url": f"https://github.com/Dennis-Otto/tool/releases/tag/{tag}",
        "body_html": "<h3>Features</h3>\n<ul>\n<li><strong>Dark mode:</strong> the "
        "settings<br>\nfollow the system.</li>\n</ul>",
    }
    data.update(changes)
    return data


def releases_api(answers: Mapping[str, object], asked: list[Any] | None = None) -> Any:
    """A stand-in for download: the releases of each repository by its name, as the
    API lists them, or the error that its download raises; asked keeps every
    request."""

    def download(request: Any) -> bytes:
        if asked is not None:
            asked.append(request)
        address = request.full_url.removeprefix("https://api.github.com/repos/")
        answer = answers[address.partition("/releases?")[0]]
        if isinstance(answer, Exception):
            raise answer
        return answer if isinstance(answer, bytes) else json.dumps(answer).encode()

    return download


@pytest.mark.usefixtures("no_token")
def test_the_build_reads_the_latest_releases_of_every_project_from_github(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asked: list[Any] = []
    listed = [
        release_data("v2.0.0-beta.1", prerelease=True),
        release_data("v1.9.0", draft=True),
        release_data("v1.8.0", published_at="2026-10-22T08:00:00Z"),
        "no release",
        release_data("not a tag!"),
        release_data(None),
        release_data("v1.7.1", published_at="yesterday"),
        release_data("v1.7.0", published_at="2026-02-30T08:00:00Z"),
        release_data("v1.6.0", body_html=None),
        *(release_data(f"v1.{minor}.0") for minor in (5, 4, 3, 2)),
    ]
    answers = {"Dennis-Otto/tool": listed, "Dennis-Otto/two": []}
    monkeypatch.setattr(hub.web, "download", releases_api(answers, asked))
    catalog = hub.reader.read(
        catalog_data(entry(), entry("two"), without_repo(entry("three")))
    )

    found = hub.releases.release_notes(catalog)

    # Neither a draft nor a prerelease, nor one without a tag or a day.
    assert list(found) == ["Dennis-Otto/tool", "Dennis-Otto/two"]
    assert found["Dennis-Otto/two"] == ()
    releases = found["Dennis-Otto/tool"]
    assert [item.tag for item in releases] == [
        "v1.8.0",
        "v1.6.0",
        "v1.5.0",
        "v1.4.0",
        "v1.3.0",
    ]
    assert releases[0] == hub.releases.Release(
        "v1.8.0",
        "https://github.com/Dennis-Otto/tool/releases/tag/v1.8.0",
        datetime(2026, 10, 22, 8, tzinfo=UTC),
        "<h4>Features</h4>\n<ul>\n<li><strong>Dark mode:</strong> the settings\n"
        "\nfollow the system.</li>\n</ul>",
        "Dark mode",
    )
    assert (releases[1].notes, releases[1].headline) == ("", "")
    # One request of each repository, for the releases with their notes as HTML,
    # and without a token, which isn't set.
    assert sorted(request.full_url for request in asked) == [
        "https://api.github.com/repos/Dennis-Otto/tool/releases?per_page=20",
        "https://api.github.com/repos/Dennis-Otto/two/releases?per_page=20",
    ]
    for request in asked:
        assert request.get_header("Accept") == "application/vnd.github.html+json"
        assert request.get_header("X-github-api-version") == "2022-11-28"
        assert not request.has_header("Authorization")


@pytest.mark.parametrize(
    ("variables", "token"),
    [
        ({"GITHUB_TOKEN": "of-the-workflow", "GH_TOKEN": "of-gh"}, "of-the-workflow"),
        ({"GITHUB_TOKEN": "", "GH_TOKEN": "of-gh"}, "of-gh"),
    ],
)
def test_a_token_of_the_workflow_goes_to_the_api_alone(
    monkeypatch: pytest.MonkeyPatch, variables: dict[str, str], token: str
) -> None:
    for name, value in variables.items():
        monkeypatch.setenv(name, value)

    request = hub.releases.releases_request("Dennis-Otto/tool")

    assert request.get_header("Authorization") == f"Bearer {token}"
    # Not among the headers that urllib takes along when the API sends the request
    # on to another host.
    assert "Authorization" not in request.headers
    assert request.unredirected_hdrs == {"Authorization": f"Bearer {token}"}


@pytest.mark.usefixtures("no_token")
def test_a_project_whose_releases_cant_be_read_has_none(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    answers = {
        "Dennis-Otto/tool": hub.web.SearchError("HTTP Error 403: rate limit exceeded"),
        "Dennis-Otto/two": b"<html>",
        "Dennis-Otto/three": {"message": "Not Found"},
    }
    monkeypatch.setattr(hub.web, "download", releases_api(answers))
    caplog.set_level(logging.INFO, logger="mkdocs.hooks.project")
    catalog = hub.reader.read(catalog_data(entry(), entry("two"), entry("three")))

    assert hub.releases.release_notes(catalog) == {}
    # Without a warning, which would fail the strict build while the API is away.
    assert {record.levelno for record in caplog.records} == {logging.INFO}
    assert len(caplog.records) == 4
    assert caplog.messages[-1] == (
        "The Releases page and What's new have the releases of 0 of the 3 "
        "repositories of the catalog."
    )


@pytest.mark.usefixtures("no_token")
def test_the_build_writes_the_releases_of_every_project_into_its_summary(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    summary = tmp_path / "summary.md"
    summary.write_text("Before\n", encoding="utf-8")
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    refused = hub.web.SearchError("HTTP Error 403: rate limit | exceeded")
    answers = {
        "Dennis-Otto/tool": [release_data("v1.1.0"), release_data("v1.0.0")],
        "Dennis-Otto/two": [],
        "Dennis-Otto/three": refused,
        "Dennis-Otto/four": {"message": "Not Found"},
    }
    monkeypatch.setattr(hub.web, "download", releases_api(answers))
    catalog = hub.reader.read(
        catalog_data(entry(), entry("two"), entry("three"), entry("four"))
    )

    hub.releases.release_notes(catalog)

    github = "https://github.com/Dennis-Otto"
    assert summary.read_text(encoding="utf-8") == "\n".join(
        [
            "Before",
            "### The releases of every project",
            "",
            "The Releases page and What's new have the releases of 2 of the 4 "
            "repositories of the catalog.",
            "",
            "| Repository | Releases on the page |",
            "| --- | --- |",
            f"| [Dennis-Otto/tool]({github}/tool/releases) | 2 |",
            f"| [Dennis-Otto/two]({github}/two/releases) | 0 |",
            f"| [Dennis-Otto/three]({github}/three/releases) | none: HTTP Error "
            "403: rate limit \\| exceeded |",
            f"| [Dennis-Otto/four]({github}/four/releases) | none: the API of GitHub "
            "sent no list of releases |",
            "",
        ]
    )


def test_a_project_without_a_release_yet_has_releases_that_were_read() -> None:
    catalog = hub.reader.read(catalog_data())
    notes: dict[str, tuple[hub.releases.Release, ...]] = {"Dennis-Otto/tool": ()}

    markdown = hub.releases.release_history(catalog, "en", notes)

    assert ' data-released=""></div>' in markdown
    assert "data-unread" not in markdown


def test_the_build_asks_for_no_releases_without_a_project_with_a_repo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(hub.web, "download", lambda url: pytest.fail(str(url)))

    catalog = hub.reader.read(catalog_data(without_repo(entry())))

    assert hub.releases.release_notes(catalog) == {}


def test_a_failed_download_of_a_request_names_its_address(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    error = urllib.error.URLError("timed out")
    monkeypatch.setattr(urllib.request, "urlopen", Download(error, error))

    with pytest.raises(hub.web.SearchError) as raised:
        hub.web.download(hub.releases.releases_request("Dennis-Otto/tool"))

    assert str(raised.value) == (
        "https://api.github.com/repos/Dennis-Otto/tool/releases?per_page=20 can't be "
        "downloaded: <urlopen error timed out>"
    )


@pytest.mark.parametrize(
    ("html", "kept"),
    [
        ('<p>Run <script>alert("x")</script>it</p>', "<p>Run it</p>"),
        ('<p onclick="steal()" style="color: red">Text</p>', "<p>Text</p>"),
        ('<img src="https://example.org/x.png" onerror="steal()">', ""),
        # A picture with its link to the full size, as GitHub writes it.
        (
            '<p><a href="https://camo.example.org/x"><img src="x.png"></a> </p>after',
            "after",
        ),
        (
            '<a href="https://x.org/"><code>x</code></a>',
            '<a href="https://x.org/"><code>x</code></a>',
        ),
        ('<a href="javascript:steal()">a link</a>', "a link"),
        (
            '<a href="https://github.com/x" data-hovercard-url="/x" onclick="s()">x</a>',
            '<a href="https://github.com/x">x</a>',
        ),
        (
            '<a href="https://example.org/?a=&quot;b&quot;">q</a>',
            '<a href="https://example.org/?a=&quot;b&quot;">q</a>',
        ),
        ('<a href="http://example.org/">plain</a>', "plain"),
        ('<a href="https://exa mple.org/">space</a>', "space"),
        ("<a>no address</a>", "no address"),
        ("<div><span>Text</span> &lt;script&gt;</div>", "Text &lt;script&gt;"),
        ("<svg><text>drawn</text></svg><p>after</p>", "<p>after</p>"),
        ("<object><svg><text>x</text></svg>y</object>z", "z"),
        ("<iframe src='https://example.org'></iframe><p>p</p>", "<p>p</p>"),
        (
            "<b>bold</b> <i>it</i> <tt>code</tt> <strike>old</strike>",
            "<strong>bold</strong> <em>it</em> <code>code</code> <del>old</del>",
        ),
        ("<ul><li>open", "<ul><li>open</li></ul>"),
        ("<p>one</em> two</p></ul>", "<p>one two</p>"),
        ("<ul><li><p>item</ul>", "<ul><li><p>item</p></li></ul>"),
        (
            "<p><a href='https://x.org/'>link</p> after",
            '<p><a href="https://x.org/">link</a></p> after',
        ),
        ("line<br>\nbreak<br/>end", "line\n\nbreak\nend"),
        ("<!-- a comment --><p>x</p>", "<p>x</p>"),
        ("<hr><hr/>", "<hr><hr>"),
        (
            "<table><tr><td align='left'>cell</td></tr></table>",
            "<table><tr><td>cell</td></tr></table>",
        ),
        ("<input type='checkbox' checked> done", "done"),
    ],
)
def test_the_notes_keep_text_lists_code_and_links_to_https_alone(
    html: str, kept: str
) -> None:
    assert hub.releases.notes_html(html, "1.0.0") == kept


def test_the_headings_of_the_notes_stand_below_the_heading_of_their_release() -> None:
    assert hub.releases.notes_html(
        "<h2>All</h2><h3>Features</h3><h5>Small</h5>", "1"
    ) == ("<h4>All</h4><h5>Features</h5><h6>Small</h6>")
    assert hub.releases.notes_html("<h3>Features</h3><H4>More</H4>", "1") == (
        "<h4>Features</h4><h5>More</h5>"
    )
    assert hub.releases.notes_html("<h1>Big</h1><h6>Tiny</h6>", "1") == (
        "<h4>Big</h4><h6>Tiny</h6>"
    )
    # As the release bot writes them: the section of the changelog, and then every
    # pull request of the release, with a heading of a higher level, which the
    # page leaves out.
    assert hub.releases.notes_html(
        hub.releases.for_users(
            "<h3>Fixed</h3><ul><li>A fix.</li></ul>"
            "<h2>Every pull request of this release</h2><h3>Bug fixes</h3>"
        ),
        "1",
    ) == ("<h4>Fixed</h4><ul><li>A fix.</li></ul>")


@pytest.mark.parametrize(
    ("html", "expected"),
    [
        # The notes of a release of the blueprint's release bot: the list of every
        # pull request goes, with the link to the comparison below it.
        (
            "<h3>Features</h3>\n<ul>\n<li>Dark mode.</li>\n</ul>\n"
            "<h2>Every pull request of this release</h2>\n<h3>Features</h3>\n<ul>\n"
            '<li>dark mode (<a href="https://github.com/x/issues/9">#9</a>)</li>\n'
            '</ul>\n<p><a href="https://github.com/x/compare/v1...v2">Compare with '
            "the previous release</a></p>",
            "<h3>Features</h3>\n<ul>\n<li>Dark mode.</li>\n</ul>\n",
        ),
        # With the attributes of a heading and the space and case of its text.
        (
            '<p>Text</p><H2 dir="auto">Every  pull request\nof this release</H2><p>x',
            "<p>Text</p>",
        ),
        # Notes without that heading, such as those of an older release, and a
        # heading that only begins like it.
        (
            "<h3>Fixed</h3><ul><li>A fix.</li></ul>",
            "<h3>Fixed</h3><ul><li>A fix.</li></ul>",
        ),
        (
            "<h2>Every pull request of this release and more</h2>",
            "<h2>Every pull request of this release and more</h2>",
        ),
        ("", ""),
    ],
)
def test_the_page_shows_the_notes_for_users_without_every_pull_request(
    html: str, expected: str
) -> None:
    assert hub.releases.for_users(html) == expected


def test_the_notes_leave_out_a_heading_in_front_that_names_their_version() -> None:
    html = (
        '<h2><a href="https://github.com/x/compare/v1.0.5...v1.0.6">1.0.6</a> '
        "(2026-10-23)</h2>\n<h3>Bug fixes</h3>"
    )

    assert hub.releases.notes_html(html, "1.0.6") == "<h4>Bug fixes</h4>"
    assert hub.releases.notes_html(html, "1.0.7") == (
        '<h4><a href="https://github.com/x/compare/v1.0.5...v1.0.6">1.0.6</a> '
        "(2026-10-23)</h4>\n<h5>Bug fixes</h5>"
    )
    assert hub.releases.notes_html("<p>1.0.6</p><h2>1.0.6</h2>", "1.0.6") == (
        "<p>1.0.6</p><h4>1.0.6</h4>"
    )
    assert hub.releases.notes_html("<h2>Notes</h2>", "") == "<h4>Notes</h4>"


# The notes of two releases of maintenance, as the page keeps them: one of
# issue-assistant with the update of a dependency alone, and one of
# homedarts-for-autodarts whose only pull request fixes the project's own jobs in
# GitHub Actions, which a person describes too.
ISSUE_ASSISTANT_1_10_6 = (
    "<h4>Bug fixes</h4>\n<ul>\n<li><strong>deps:</strong> update the other engines (<a"
    ' href="https://github.com/Dennis-Otto/issue-assistant/issues/311">#311</a>) (<a'
    ' href="https://github.com/Dennis-Otto/issue-assistant/commit/759bfb1">759bfb1</a>)'
    "</li>\n</ul>"
)
HOMEDARTS_2_3_1 = (
    "<h4>Bug fixes</h4>\n<ul>\n<li>The end-to-end tests, the visual check, <em>Same"
    " images</em>, the translation bot and the comment of the visual check stop when"
    " Harden-Runner can't block.</li>\n</ul>\n<h5>Every pull request of this"
    " release</h5>\n<h4>Bug fixes</h4>\n<ul>\n<li><strong>ci:</strong> the project's"
    " own jobs stop when Harden-Runner doesn't block (<a"
    ' href="https://github.com/Dennis-Otto/homedarts-for-autodarts/issues/651">#651</a>)'
    ' (<a href="https://github.com/Dennis-Otto/homedarts-for-autodarts/commit/0ed9b07">'
    "0ed9b07</a>)</li>\n</ul>\n<p><a"
    ' href="https://github.com/Dennis-Otto/homedarts-for-autodarts/compare/v2.3.0...'
    'v2.3.1">Compare with the previous release</a></p>'
)
# A pull request of each kind, as release-please lists it.
PULL = (
    '<li><strong>{}:</strong> a change (<a href="https://github.com/x/pull/9">#9</a>)'
    ' (<a href="https://github.com/x/commit/3fb0bf5">3fb0bf5</a>)</li>'
)
UNSCOPED = '<li>a change for users (<a href="https://github.com/x/pull/8">#8</a>)</li>'
TOLD = "<li>The Copilot engine works with version 1.0.103 of its command line.</li>"


@pytest.mark.parametrize(
    ("notes", "expected"),
    [
        (
            "<h4>Features</h4><ul><li><strong>Dark mode:</strong> the settings.</li>",
            "Dark mode",
        ),
        ("<ul><li><strong>Dark mode</strong>: the settings.</li></ul>", "Dark mode"),
        (
            "<ul><li>\n<p><strong>A loose item:</strong> its text</p></li></ul>",
            "A loose item",
        ),
        (
            '<ul><li><strong>popup:</strong> hide the form until asked for (<a href="'
            'https://github.com/x/pull/4">#4</a>) (<a href="https://github.com/x/'
            'commit/84ffac1">84ffac1</a>)</li></ul>',
            "Hide the form until asked for",
        ),
        # The scope of a commit, a bold lead of one word, as in the notes of
        # issue-assistant v1.10.6, is no part of the headline.
        (ISSUE_ASSISTANT_1_10_6, "Update the other engines"),
        (
            "<ul><li><strong>Dark</strong>: the settings follow.</li></ul>",
            "The settings follow",
        ),
        (
            "<p>Each release reaches the store. Google reviews it.</p>",
            "Each release reaches the store",
        ),
        ("<p>One sentence.</p>", "One sentence"),
        ("<ul><li><strong>Alone</strong></li></ul>", "Alone"),
        ("<p>" + "word " * 40 + "</p>", " ".join(["word"] * 24) + "…"),
        ("<h4>Only a heading</h4>", ""),
        ("", ""),
    ],
)
def test_what_s_new_tells_a_release_by_the_headline_of_its_notes(
    notes: str, expected: str
) -> None:
    assert hub.releases.headline(notes) == expected


@pytest.mark.parametrize(
    ("notes", "expected"),
    [
        # Of a dependency alone, and of the project's own jobs alone, though a
        # person describes it.
        (ISSUE_ASSISTANT_1_10_6, True),
        (HOMEDARTS_2_3_1, True),
        (f"<ul>{PULL.format('build')}{PULL.format('TEST')}</ul>", True),
        (f"<ul>{PULL.format('docs')}{PULL.format('chore')}</ul>", True),
        # A dependency or the documentation that a person describes in the words
        # of a user, such as a fix of an engine that the update brings.
        (f"<ul>{TOLD}</ul><ul>{PULL.format('deps')}</ul>", False),
        (f"<ul>{TOLD}</ul><ul>{PULL.format('docs')}</ul>", False),
        # A pull request of the project itself, with a scope or without.
        (f"<ul>{PULL.format('ci')}{PULL.format('overlay')}</ul>", False),
        (f"<ul>{PULL.format('ci')}{UNSCOPED}</ul>", False),
        (f"<ul>{PULL.format('ci').replace(':', '')}</ul>", False),
        (f"<ul>{PULL.format('two words')}</ul>", False),
        # Notes without a pull request tell nothing of it.
        (f"<ul>{TOLD}</ul>", False),
        ("<p>Each release reaches the store.</p>", False),
        ("", False),
    ],
)
def test_a_release_of_maintenance_alone_is_known_by_the_scopes_of_its_pulls(
    notes: str, expected: bool
) -> None:
    assert hub.releases.maintenance(notes) is expected


@pytest.mark.parametrize(
    ("value", "moment"),
    [
        ("2026-10-15T21:33:15Z", datetime(2026, 10, 15, 21, 33, 15, tzinfo=UTC)),
        (
            "2026-10-15T21:33:15.120Z",
            datetime(2026, 10, 15, 21, 33, 15, 120000, tzinfo=UTC),
        ),
        ("2026-02-30T08:00:00Z", None),
        ("2026-10-15", None),
        (None, None),
        (20261015, None),
    ],
)
def test_a_release_was_published_at_the_moment_that_the_api_names(
    value: object, moment: datetime | None
) -> None:
    assert hub.releases.published(value) == moment


def test_a_release_has_an_anchor_from_its_project_and_its_tag() -> None:
    project = hub.reader.read(catalog_data()).projects[0]
    tagged = release("v2.0.1-beta.1+build_7", "2026-10-01")

    assert hub.releases.release_anchor(project, tagged) == "tool-v2-0-1-beta-1-build-7"


def test_what_s_new_lists_the_latest_release_of_every_project_newest_first() -> None:
    quoted = {"en": 'The "two" <tool>', "de": "Zwei"}
    catalog = hub.reader.read(
        catalog_data(
            entry("one"),
            entry("two", name=quoted),
            entry("three"),
            without_repo(entry("four")),
            entry("five"),
        )
    )
    notes = {
        "Dennis-Otto/one": (
            release("v1.0.0", "2026-10-20", "Dark mode"),
            release("v0.9.0", "2026-10-01", "Older"),
        ),
        "Dennis-Otto/two": (release("v2.0.0", "2026-10-22", 'A "quoted" <b>'),),
        "Dennis-Otto/three": (release("v3.0.0", "2026-10-20"),),
        "Dennis-Otto/five": (),
    }

    html = hub.releases.news(catalog, "en", notes)

    # Four projects with a repo, the count of the script; the newest first, and of a
    # day in the order of the catalog, each with the tags of every release that the
    # build read; five without a release has none.
    assert html == (
        '<div class="project-news" data-count="4"><ul class="project-news__list">'
        '<li data-repo="Dennis-Otto/two" data-release="v2.0.0"'
        ' data-released="2026-10-22" data-releases="v2.0.0">'
        '<a href="releases.html#two-v2-0-0">'
        "The &quot;two&quot; &lt;tool&gt; v2.0.0</a>"
        ' <time datetime="2026-10-22" data-ago>2026-10-22</time>'
        '<span class="project-news__headline" lang="en">'
        "A &quot;quoted&quot; &lt;b&gt;</span></li>"
        '<li data-repo="Dennis-Otto/one" data-release="v1.0.0"'
        ' data-released="2026-10-20" data-releases="v1.0.0 v0.9.0">'
        '<a href="releases.html#one-v1-0-0">'
        "The tool v1.0.0</a>"
        ' <time datetime="2026-10-20" data-ago>2026-10-20</time>'
        '<span class="project-news__headline" lang="en">Dark mode</span></li>'
        '<li data-repo="Dennis-Otto/three" data-release="v3.0.0"'
        ' data-released="2026-10-20" data-releases="v3.0.0">'
        '<a href="releases.html#three-v3-0-0">'
        "The tool v3.0.0</a>"
        ' <time datetime="2026-10-20" data-ago>2026-10-20</time></li>'
        "</ul></div>"
    )
    assert ">Zwei v2.0.0</a>" in hub.releases.news(catalog, "de", notes)


def test_what_s_new_tells_a_release_of_maintenance_in_the_language_of_the_page() -> (
    None
):
    catalog = hub.reader.read(catalog_data(entry("one")))
    notes: dict[str, tuple[hub.releases.Release, ...]] = {
        "Dennis-Otto/one": (
            release(
                "v1.0.1", "2026-10-20", "Update the other engines", maintenance=True
            ),
        )
    }

    # The text of the facts, in the language of the page, which the span names by
    # no language of its own, in place of the headline of the notes in English.
    assert hub.releases.news(catalog, "en", notes).endswith(
        '<time datetime="2026-10-20" data-ago>2026-10-20</time>'
        '<span class="project-news__headline">Upkeep</span></li></ul></div>'
    )
    assert '<span class="project-news__headline">Pflege</span>' in (
        hub.releases.news(catalog, "de", notes)
    )


def test_the_build_tells_a_release_of_maintenance_by_its_notes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pulls = (
        '<ul><li><strong>ci:</strong> the own jobs (<a href="https://github.com/x/'
        'pull/7">#7</a>)</li></ul>'
    )
    listed = [release_data("v1.0.1", body_html=pulls), release_data("v1.0.0")]
    monkeypatch.setattr(hub.web, "download", releases_api({"Dennis-Otto/tool": listed}))

    found = hub.releases.release_notes(hub.reader.read(catalog_data(entry())))

    assert [item.maintenance for item in found["Dennis-Otto/tool"]] == [True, False]


def test_the_build_shows_the_notes_for_users_once_and_tells_by_all_of_them(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The notes of homedarts-for-autodarts v2.3.1, as GitHub makes them of their
    # Markdown, and those of a release with nothing above the list of its pull
    # requests, which the page keeps.
    told = (
        "<h3>Bug fixes</h3>\n<ul>\n<li>The end-to-end tests stop when Harden-Runner"
        " can't block.</li>\n</ul>\n"
    )
    pulls = (
        "<h2>Every pull request of this release</h2>\n<h3>Bug fixes</h3>\n<ul>\n"
        "<li><strong>ci:</strong> the project's own jobs stop (<a"
        ' href="https://github.com/x/issues/651">#651</a>)</li>\n</ul>\n'
    )
    listed = [
        release_data("v2.3.1", body_html=told + pulls),
        release_data("v2.3.0", body_html=pulls),
    ]
    monkeypatch.setattr(hub.web, "download", releases_api({"Dennis-Otto/tool": listed}))

    found = hub.releases.release_notes(hub.reader.read(catalog_data(entry())))

    fixed, only_pulls = found["Dennis-Otto/tool"]
    assert fixed.notes == (
        "<h4>Bug fixes</h4>\n<ul>\n<li>The end-to-end tests stop when Harden-Runner"
        " can't block.</li>\n</ul>"
    )
    # What's new still knows it by the scopes of its pull requests.
    assert fixed.maintenance
    assert fixed.headline == "The end-to-end tests stop when Harden-Runner can't block"
    assert only_pulls.notes.startswith(
        "<h4>Every pull request of this release</h4>\n<h5>Bug fixes</h5>"
    )


def test_what_s_new_without_releases_leaves_its_place_to_the_script() -> None:
    catalog = hub.reader.read(catalog_data(entry(), entry("two")))

    assert hub.releases.news(catalog, "en", {}) == (
        '<div class="project-news" data-count="2"></div>'
    )


def test_the_releases_page_has_the_releases_of_every_project_with_a_repo() -> None:
    catalog = hub.reader.read(
        catalog_data(
            entry("one", short={"en": "One", "de": "Eins"}),
            without_repo(entry("two")),
            entry("three"),
        )
    )
    notes: dict[str, tuple[hub.releases.Release, ...]] = {
        "Dennis-Otto/one": (
            release("v1.0.0", "2026-10-20"),
            release("v0.9_1", "2026-10-01"),
        ),
    }

    nav, *parts = hub.releases.release_history(catalog, "en", notes).split("\n\n")

    # The list of the projects tells the script where the data is.
    assert nav == (
        '<nav class="release-filter" aria-label="Projects"'
        f'{hub.render.script_data(catalog, "en")}><ul><li><a href="#one">One</a></li>'
        '<li><a href="#three">The tool</a></li></ul></nav>'
    )
    meta = (
        '<p class="release-meta"><time datetime="{0}" data-ago>{0}</time> · '
        '<a href="https://github.com/Dennis-Otto/one/releases/tag/{1}">On GitHub</a></p>'
    )
    assert parts == [
        "## The tool { #one }",
        '<div class="release-newer" data-repo="Dennis-Otto/one"'
        ' data-releases="v1.0.0 v0.9_1" data-released="2026-10-20"></div>',
        "### One v1.0.0 { #one-v1-0-0 }",
        meta.format("2026-10-20", "v1.0.0"),
        '<div class="release-notes" data-release="Dennis-Otto/one@v1.0.0"></div>',
        "### One v0.9\\_1 { #one-v0-9-1 }",
        meta.format("2026-10-01", "v0.9_1"),
        '<div class="release-notes" data-release="Dennis-Otto/one@v0.9_1"></div>',
        '<p class="release-all"><a href="https://github.com/Dennis-Otto/one/releases">'
        "All of One on GitHub</a> · "
        '<a href="https://github.com/Dennis-Otto/one/releases.atom"'
        ' type="application/atom+xml">Feed of One</a></p>',
        # A project whose releases the build couldn't read links them on GitHub.
        "## The tool { #three }",
        '<div class="release-newer" data-repo="Dennis-Otto/three" data-releases=""'
        ' data-released="" data-unread></div>',
        '<p class="release-all"><a href="https://github.com/Dennis-Otto/three/'
        'releases">All of The tool on GitHub</a> · '
        '<a href="https://github.com/Dennis-Otto/three/releases.atom"'
        ' type="application/atom+xml">Feed of The tool</a></p>',
    ]


def test_the_german_releases_page_has_the_texts_in_german() -> None:
    catalog = hub.reader.read(
        catalog_data(entry(short={"en": "Tool", "de": "Werkzeug"}))
    )
    notes: dict[str, tuple[hub.releases.Release, ...]] = {
        "Dennis-Otto/tool": (release("v1.0.0", "2026-10-20", repo="x/y"),)
    }

    markdown = hub.releases.release_history(catalog, "de", notes)

    assert 'aria-label="Projekte" data-facts=' in markdown
    assert ' data-locale="de"' in markdown
    assert "## Das Werkzeug { #tool }" in markdown
    assert "### Werkzeug v1.0.0 { #tool-v1-0-0 }" in markdown
    assert ">Auf GitHub</a></p>" in markdown
    assert ">Alle von Werkzeug auf GitHub</a> · " in markdown
    assert ">Feed von Werkzeug</a></p>" in markdown


@pytest.mark.usefixtures("no_token")
def test_the_releases_are_read_once_for_both_pages_and_every_language(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asked: list[Any] = []
    answers = {"Dennis-Otto/tool": [release_data("v1.0.0")]}
    monkeypatch.setattr(hub.web, "download", releases_api(answers, asked))
    settings = SimpleNamespace(extra={"catalog": hub.reader.read(catalog_data())})
    markdown = "## News\n\n<!-- releases -->\t\n\nSee the `<!-- releases -->`.\n"

    news = hooks.on_page_markdown(markdown, page("de"), settings, None)
    history = hooks.on_page_markdown(
        "# Releases\n\n<!-- release-notes -->\n", page("en"), settings, None
    )

    assert len(asked) == 1
    assert news.startswith(
        '## News\n\n<div class="project-news" data-count="1"><ul class="project-'
    )
    assert news.endswith("</ul></div>\n\nSee the `<!-- releases -->`.\n")
    assert '<a href="releases.html#tool-v1-0-0">Das Werkzeug v1.0.0</a>' in news
    assert "\n\n### The tool v1.0.0 { #tool-v1-0-0 }\n\n" in history
    # A page without the markers asks for nothing.
    assert hooks.on_page_markdown("# Security\n", page("en"), settings, None)
    assert len(asked) == 1


@pytest.mark.usefixtures("no_token")
def test_without_the_api_both_pages_link_the_releases_on_github(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    offline = hub.web.SearchError("api.github.com can't be downloaded: offline")
    monkeypatch.setattr(
        hub.web, "download", releases_api({"Dennis-Otto/tool": offline})
    )
    settings = SimpleNamespace(extra={"catalog": hub.reader.read(catalog_data())})

    news = hooks.on_page_markdown("<!-- releases -->\n", page("en"), settings, None)
    history = hooks.on_page_markdown(
        "<!-- release-notes -->\n", page("en"), settings, None
    )
    html = hooks.on_page_content(history, page("en"), settings, None)

    assert news == '<div class="project-news" data-count="1"></div>\n'
    assert "###" not in history
    assert html == history
    assert (
        '<a href="https://github.com/Dennis-Otto/tool/releases">All of The tool on '
        "GitHub</a>" in history
    )


@pytest.mark.parametrize("locale", ["en", "de", None])
def test_the_notes_take_the_place_of_their_placeholders_in_the_html(
    locale: str | None,
) -> None:
    notes = {"Dennis-Otto/tool": (release("v1.0.0", "2026-10-20"),)}
    catalog = hub.reader.read(catalog_data())
    settings = SimpleNamespace(extra={"catalog": catalog, hub.releases.NOTES: notes})
    html = (
        '<h3 id="tool-v1-0-0">The tool v1.0.0</h3>\n'
        '<div class="release-notes" data-release="Dennis-Otto/tool@v1.0.0"></div>\n'
        '<div class="release-notes" data-release="Dennis-Otto/tool@v0.1.0"></div>'
    )

    result = hooks.on_page_content(html, page(locale), settings, None)

    # In English, as the notes are, on the page of every language, so that the
    # search index of each language holds them. A release without notes gets none.
    attributes = ' lang="en"'
    assert result == (
        '<h3 id="tool-v1-0-0">The tool v1.0.0</h3>\n'
        f'<div class="release-notes"{attributes}><p>Notes</p></div>\n'
        f'<div class="release-notes"{attributes}></div>'
    )


class Dates:
    """The plugin git-revision-date-localized, which writes the date of a page into
    its meta, in the language of its file, and keeps every date that it was asked."""

    def __init__(self) -> None:
        self.asked: list[tuple[str, str, str, str, int]] = []

    def _get_locale(self, page: Any) -> str:
        locale: str = page.file.locale
        return locale

    def _render_date(
        self,
        markdown: str,
        page: Any,
        locale: str,
        variable: str,
        commit_hash: str,
        commit_timestamp: int,
    ) -> str:
        self.asked.append((markdown, locale, variable, commit_hash, commit_timestamp))
        page.meta[variable] = f"{locale} {commit_timestamp}"
        return markdown


# The HTML of the pages that show the releases of the build, as news() and
# release_history() write them.
NEWS_HTML = '<div class="project-news" data-count="2"><ul></ul></div>'
HISTORY_HTML = '<div class="release-newer" data-repo="Dennis-Otto/tool"></div>'
# Two projects, whose latest releases came out after the last commit of the
# Markdown of the page, on COMMITTED of hub_helpers, the newest of them at noon.
LATER = {
    "Dennis-Otto/tool": (
        release("v1.1.0", "2026-11-10"),
        release("v1.0.0", "2026-11-12"),
    ),
    "Dennis-Otto/two": (release("v2.0.0", "2026-11-11"),),
}
NOON = int(datetime(2026, 11, 10, 12, tzinfo=UTC).timestamp())


@pytest.mark.parametrize("html", [NEWS_HTML, HISTORY_HTML])
def test_a_page_with_the_releases_is_dated_by_the_newest_of_them(html: str) -> None:
    dates = Dates()
    settings = SimpleNamespace(
        extra={"catalog": hub.reader.read(catalog_data()), hub.releases.NOTES: LATER},
        plugins={hub.releases.DATES: dates},
    )
    shown = page("de")
    shown.meta[hub.releases.REVISION] = "24. Oktober 2026"

    assert hooks.on_page_content(html, shown, settings, None) == html

    # By the latest release of each project, the newest of them, in the sitemap
    # and in the date of its last change, which the plugin writes in the language
    # of the page, without a commit.
    assert shown.update_date == "2026-11-11"
    assert dates.asked == [("", "de", "git_revision_date_localized", "", NOON + 86400)]
    assert shown.meta[hub.releases.REVISION] == f"de {NOON + 86400}"


@pytest.mark.parametrize(
    ("committed", "notes", "html"),
    [
        # The Markdown changed on the day of the newest release, or after it.
        ("2026-11-11", LATER, HISTORY_HTML),
        ("2026-11-12", LATER, NEWS_HTML),
        # The build read no release.
        ("2026-10-24", {}, HISTORY_HTML),
        ("2026-10-24", {"Dennis-Otto/tool": ()}, NEWS_HTML),
        # The page shows no release.
        ("2026-10-24", LATER, "<p>Text</p>"),
    ],
)
def test_a_page_keeps_the_date_of_its_markdown_when_no_release_came_out_later(
    committed: str, notes: dict[str, Any], html: str
) -> None:
    dates = Dates()
    settings = SimpleNamespace(
        extra={"catalog": hub.reader.read(catalog_data()), hub.releases.NOTES: notes},
        plugins={hub.releases.DATES: dates},
    )
    shown = page("en")
    shown.update_date = committed

    hooks.on_page_content(html, shown, settings, None)

    assert shown.update_date == committed
    assert dates.asked == []


@pytest.mark.parametrize("plugins", [{}, {hub.releases.DATES: Dates()}])
def test_without_the_date_of_the_plugin_only_the_sitemap_follows_the_releases(
    plugins: dict[str, Any],
) -> None:
    # Without the plugin, or on a page that it doesn't date.
    settings = SimpleNamespace(
        extra={"catalog": hub.reader.read(catalog_data()), hub.releases.NOTES: LATER},
        plugins=plugins,
    )
    shown = page("en")

    hooks.on_page_content(HISTORY_HTML, shown, settings, None)

    assert shown.update_date == "2026-11-11"
    assert shown.meta == {}
    assert all(not dates.asked for dates in plugins.values())


def test_a_page_without_the_placeholder_of_notes_asks_for_no_release(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(hub.web, "download", lambda url: pytest.fail(str(url)))
    settings = SimpleNamespace(extra={"catalog": hub.reader.read(catalog_data())})

    assert hooks.on_page_content("<p>Text</p>", page("en"), settings, None) == (
        "<p>Text</p>"
    )


@pytest.mark.usefixtures("no_token")
def test_no_script_or_picture_of_a_release_reaches_the_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    body = (
        '<p onmouseover="steal()">Fixed</p><script>steal()</script>'
        '<img src="https://example.org/track.gif" onerror="steal()">'
        '<a href="javascript:steal()">link</a><style>p { display: none }</style>'
        '<iframe src="https://example.org/"></iframe><svg onload="steal()"></svg>'
    )
    answers = {"Dennis-Otto/tool": [release_data("v1.0.0", body_html=body)]}
    monkeypatch.setattr(hub.web, "download", releases_api(answers))
    settings = SimpleNamespace(extra={"catalog": hub.reader.read(catalog_data())})
    markdown = hooks.on_page_markdown(
        "<!-- release-notes -->\n", page("en"), settings, None
    )

    html = hooks.on_page_content(markdown, page("en"), settings, None)

    notes = html[html.index('<div class="release-notes"') :].split("\n\n")[0]
    assert notes == '<div class="release-notes" lang="en"><p>Fixed</p>link</div>'
    for word in ("<script", "<img", "<style", "<iframe", "<svg", "steal", "javascript"):
        assert word not in html, word
