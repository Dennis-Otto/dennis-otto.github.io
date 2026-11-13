"""Tests of .github/hub/web.py: how the hooks and the bots ask the web."""

from __future__ import annotations

import email.message
import http.client
import io
import urllib.error
import urllib.request
from typing import Any

import pytest

import hub.web
from hub_helpers import HACS, SITE, Download, raw


def not_found() -> Any:
    """The error of urllib for an index that a website doesn't have."""
    return urllib.error.HTTPError(
        f"{SITE}tool/search/search_index.json",
        404,
        "Not Found",
        email.message.Message(),
        io.BytesIO(b"Not Found"),
    )


def test_an_index_is_downloaded_with_a_time_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    urlopen = Download(b"{}")
    monkeypatch.setattr(urllib.request, "urlopen", urlopen)

    assert hub.web.download(f"{SITE}tool/search/search_index.json") == b"{}"
    assert urlopen.requests == [(f"{SITE}tool/search/search_index.json", 10)]


@pytest.mark.parametrize(
    "error",
    [
        urllib.error.URLError("timed out"),
        http.client.RemoteDisconnected("closed"),
        ValueError("unknown url type"),
    ],
)
def test_a_failed_download_is_tried_again_after_a_pause(
    monkeypatch: pytest.MonkeyPatch, error: Exception, waits: list[float]
) -> None:
    urlopen = Download(error, b"{}")
    monkeypatch.setattr(urllib.request, "urlopen", urlopen)

    assert hub.web.download(f"{SITE}tool/search/search_index.json") == b"{}"
    assert len(urlopen.requests) == hub.web.TRIES == 2
    assert waits == [hub.web.PAUSE] == [2]


def test_a_download_gives_up_after_its_tries(
    monkeypatch: pytest.MonkeyPatch, waits: list[float]
) -> None:
    errors = [not_found(), not_found()]
    monkeypatch.setattr(urllib.request, "urlopen", Download(*errors))

    with pytest.raises(hub.web.SearchError) as error:
        hub.web.download(f"{SITE}tool/search/search_index.json")

    assert str(error.value) == (
        f"{SITE}tool/search/search_index.json can't be downloaded: "
        "HTTP Error 404: Not Found"
    )
    # The answers of the errors are closed, as an answer without an error is.
    assert all(answer.fp.closed for answer in errors)
    # No wait after the last try.
    assert waits == [2]


# The moment of the downloads of the tests of the limit of the API, in seconds since
# the epoch: 2026-11-12T06:00:00Z.
NOW = 1_794_463_200
RELEASES = "https://api.github.com/repos/Dennis-Otto/tool/releases?per_page=20"


def refused(**headers: str) -> Any:
    """The error of urllib for an answer of the API of GitHub that refuses a request,
    with headers."""
    message = email.message.Message()
    for name, value in headers.items():
        message[name.replace("_", "-")] = value
    return urllib.error.HTTPError(
        RELEASES, 403, "rate limit exceeded", message, io.BytesIO(b"")
    )


@pytest.mark.parametrize(
    ("headers", "wait"),
    [
        # Retry-After, in seconds or as a date, as for the secondary limits.
        ({"Retry-After": "5"}, 5),
        ({"Retry-After": "Thu, 12 Nov 2026 06:00:12 GMT"}, 12),
        ({"Retry-After": "Thu, 12 Nov 2026 05:59:00 GMT"}, 2),
        # The moment at which the primary limit resets, once it is used up.
        ({"x_ratelimit_remaining": "0", "x_ratelimit_reset": f"{NOW + 7}"}, 7),
        ({"x_ratelimit_remaining": "0", "x_ratelimit_reset": f"{NOW - 7}"}, 2),
        # No wait that the answer asks for: the pause.
        ({}, 2),
        ({"Retry-After": "soon"}, 2),
        ({"x_ratelimit_remaining": "12", "x_ratelimit_reset": f"{NOW + 7}"}, 2),
        ({"x_ratelimit_remaining": "0", "x_ratelimit_reset": "soon"}, 2),
    ],
)
def test_a_download_waits_as_long_as_the_api_asks(
    monkeypatch: pytest.MonkeyPatch,
    waits: list[float],
    headers: dict[str, str],
    wait: float,
) -> None:
    monkeypatch.setattr(urllib.request, "urlopen", Download(refused(**headers), b"[]"))
    monkeypatch.setattr(hub.web, "clock", lambda: NOW)

    assert hub.web.download(urllib.request.Request(RELEASES)) == b"[]"
    assert waits == [wait]


def test_an_answer_without_headers_asks_for_no_wait(
    monkeypatch: pytest.MonkeyPatch, waits: list[float]
) -> None:
    # urllib makes an error without headers for an answer that it can't read, which
    # its stubs don't allow.
    headers: Any = None
    error = urllib.error.HTTPError(RELEASES, 502, "Bad Gateway", headers, None)
    monkeypatch.setattr(urllib.request, "urlopen", Download(error, b"[]"))

    assert hub.web.download(RELEASES) == b"[]"
    assert waits == [hub.web.PAUSE]


def test_a_download_doesnt_wait_for_a_limit_that_lasts_long(
    monkeypatch: pytest.MonkeyPatch, waits: list[float]
) -> None:
    error = refused(x_ratelimit_remaining="0", x_ratelimit_reset=f"{NOW + 1800}")
    urlopen = Download(error)
    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(hub.web, "clock", lambda: NOW)

    with pytest.raises(hub.web.SearchError) as raised:
        hub.web.download(urllib.request.Request(RELEASES))

    # One try, which tells why the build goes on without the file.
    assert str(raised.value) == (
        f"{RELEASES} can't be downloaded: HTTP Error 403: rate limit exceeded, and it "
        "asks to wait 1800 seconds"
    )
    assert len(urlopen.requests) == 1
    assert waits == []
    assert hub.web.LONGEST_WAIT == 30


def test_the_downloads_of_a_build_wait_a_while_together_at_most(
    monkeypatch: pytest.MonkeyPatch, waits: list[float]
) -> None:
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        Download(*(refused(Retry_After="30") for _ in range(9))),
    )

    for _ in range(5):
        with pytest.raises(hub.web.SearchError) as raised:
            hub.web.download(RELEASES)

    # 120 seconds: four waits of 30, so the fifth download tries once.
    assert hub.web.WAITING == 120
    assert waits == [30, 30, 30, 30]
    assert str(raised.value).endswith(
        "403: rate limit exceeded, and the build has waited long enough for its "
        "downloads"
    )


def test_the_patience_of_a_build_is_counted_once_for_every_wait() -> None:
    patience = hub.web.Patience(10)

    assert patience.take(4)
    assert patience.take(6)
    assert not patience.take(0.5)
    assert patience.left == 0


class Response:
    """A stand-in for the answer of urllib.request.urlopen."""

    status = 200

    def __enter__(self) -> Response:
        return self

    def __exit__(self, *exception: object) -> None:
        return None


def test_the_status_of_a_website_comes_from_a_head_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[tuple[Any, float]] = []

    def urlopen(request: Any, timeout: float) -> Response:
        requests.append((request, timeout))
        return Response()

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)

    assert hub.web.status(f"{SITE}tool/de/") == 200
    [(request, timeout)] = requests
    assert (request.full_url, request.get_method()) == (f"{SITE}tool/de/", "HEAD")
    assert timeout == hub.web.TIMEOUT == 30


def test_a_website_that_is_gone_answers_with_its_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    errors: list[Any] = []

    def urlopen(request: Any, timeout: float) -> Response:
        error = urllib.error.HTTPError(
            request.full_url, 404, "Not Found", email.message.Message(), None
        )
        errors.append(error)
        raise error

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)

    assert hub.web.status(f"{SITE}tool/de/") == 404
    # The answer of the website is closed, as an answer without an error is.
    assert errors[0].fp.closed


def test_a_website_that_cant_be_reached_stops_the_bot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def urlopen(request: Any, timeout: float) -> Response:
        raise urllib.error.URLError("timed out")

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)

    with pytest.raises(hub.web.CheckError) as error:
        hub.web.status(f"{SITE}tool/de/")

    assert str(error.value) == (
        f"{SITE}tool/de/ can't be reached: <urlopen error timed out>"
    )


def test_a_file_comes_with_a_time_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    url = raw("Dennis-Otto/tool", "HEAD", "hacs.json")
    urlopen = Download(HACS)
    monkeypatch.setattr(urllib.request, "urlopen", urlopen)

    assert hub.web.fetched(url) == HACS
    assert urlopen.requests == [(url, hub.web.TIMEOUT)]


@pytest.mark.parametrize("code", [404, 410])
def test_a_file_that_is_gone_has_no_content(
    monkeypatch: pytest.MonkeyPatch, code: int
) -> None:
    url = raw("Dennis-Otto/tool", "HEAD", "hacs.json")
    error = urllib.error.HTTPError(
        url, code, "Gone", email.message.Message(), io.BytesIO(b"")
    )
    monkeypatch.setattr(urllib.request, "urlopen", Download(error))

    assert hub.web.fetched(url) is None
    # The answer is closed, as an answer without an error is.
    assert error.fp.closed


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (
            urllib.error.HTTPError(
                "https://raw.githubusercontent.com/",
                503,
                "Unavailable",
                email.message.Message(),
                io.BytesIO(b""),
            ),
            "answers 503, where the catalog bot expects 200 or 404; start it again "
            "later.",
        ),
        (
            urllib.error.URLError("timed out"),
            "can't be reached: <urlopen error timed out>",
        ),
    ],
)
def test_a_file_that_cant_be_read_stops_the_bot(
    monkeypatch: pytest.MonkeyPatch, error: Exception, message: str
) -> None:
    url = raw("Dennis-Otto/tool", "HEAD", "hacs.json")
    monkeypatch.setattr(urllib.request, "urlopen", Download(error))

    with pytest.raises(hub.web.CheckError) as stopped:
        hub.web.fetched(url)

    assert str(stopped.value) == f"{url} {message}"
