"""Tests of .github/hub/releases.py: the Releases page and What's new, from the API
of GitHub.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from collections.abc import Mapping
from datetime import date
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
        date(2026, 10, 22),
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
    assert len(caplog.records) == 3


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
    # As release-please writes them: the section of the changelog, and then every
    # pull request of the release, with a heading of a higher level.
    assert hub.releases.notes_html(
        "<h3>Fixed</h3><h2>Every pull request</h2><h3>Bug fixes</h3>", "1"
    ) == ("<h4>Fixed</h4><h4>Every pull request</h4><h4>Bug fixes</h4>")


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
            "popup: hide the form until asked for",
        ),
        (
            "<p>Each release reaches the store. Google reviews it.</p>",
            "Each release reaches the store",
        ),
        ("<p>One sentence.</p>", "One sentence"),
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
    ("value", "day"),
    [
        ("2026-10-15T21:33:15Z", date(2026, 10, 15)),
        ("2026-10-15T21:33:15.120Z", date(2026, 10, 15)),
        ("2026-02-30T08:00:00Z", None),
        ("2026-10-15", None),
        (None, None),
        (20261015, None),
    ],
)
def test_a_release_was_published_on_the_day_that_the_api_names(
    value: object, day: date | None
) -> None:
    assert hub.releases.published(value) == day


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
        "All of One on GitHub</a></p>",
        # A project whose releases the build couldn't read links them on GitHub.
        "## The tool { #three }",
        '<div class="release-newer" data-repo="Dennis-Otto/three" data-releases=""'
        ' data-released=""></div>',
        '<p class="release-all"><a href="https://github.com/Dennis-Otto/three/'
        'releases">All of The tool on GitHub</a></p>',
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
    assert ">Alle von Werkzeug auf GitHub</a></p>" in markdown


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
