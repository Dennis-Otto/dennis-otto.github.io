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


# How the catalog bot and its watch ask again for an address that can't be reached
# for the moment, as GitHub Pages answered 503 for a moment on 2026-11-18.

PAGE = f"{SITE}homedarts-for-autodarts/glossary.html"


def failed(code: int) -> urllib.error.HTTPError:
    """The error of urllib for an answer with the status code."""
    return urllib.error.HTTPError(
        PAGE, code, "Odd", email.message.Message(), io.BytesIO(b"")
    )


def methods(urlopen: Download) -> list[tuple[str, str]]:
    """The method and the address of every request of urlopen, in turn."""
    return [
        (request.get_method(), request.full_url)
        if isinstance(request, urllib.request.Request)
        else ("GET", request)
        for request, _ in urlopen.requests
    ]


def probe() -> Any:
    """The status of an address as the catalog bot asks for it, from now on."""
    return hub.web.patient(hub.web.status, hub.web.clock())


def fetch() -> Any:
    """The content of an address as the catalog bot asks for it, from now on."""
    return hub.web.patient(hub.web.fetched, hub.web.clock())


OUTAGES = [
    pytest.param(lambda: failed(503), id="503"),
    pytest.param(lambda: failed(500), id="500"),
    pytest.param(lambda: failed(429), id="429"),
    pytest.param(lambda: TimeoutError("timed out"), id="timeout"),
    pytest.param(lambda: urllib.error.URLError("refused"), id="refused"),
    pytest.param(lambda: http.client.RemoteDisconnected("closed"), id="closed"),
]


@pytest.mark.parametrize("outage", OUTAGES)
def test_a_page_with_a_short_outage_is_there_after_a_pause(
    monkeypatch: pytest.MonkeyPatch, outage: Any, waits: list[float]
) -> None:
    urlopen = Download(outage(), b"")
    monkeypatch.setattr(urllib.request, "urlopen", urlopen)

    assert hub.web.exists(probe(), PAGE)

    assert methods(urlopen) == [("HEAD", PAGE)] * 2
    assert waits == [hub.web.PAUSE] == [2]


@pytest.mark.parametrize("outage", OUTAGES)
def test_a_file_with_a_short_outage_is_read_after_a_pause(
    monkeypatch: pytest.MonkeyPatch, outage: Any, waits: list[float]
) -> None:
    urlopen = Download(outage(), HACS)
    monkeypatch.setattr(urllib.request, "urlopen", urlopen)

    assert fetch()(PAGE) == HACS

    assert methods(urlopen) == [("GET", PAGE)] * 2
    assert waits == [2]


def test_a_page_with_a_real_outage_stops_the_bot_as_today(
    monkeypatch: pytest.MonkeyPatch, waits: list[float]
) -> None:
    urlopen = Download(failed(503), failed(503), failed(503))
    monkeypatch.setattr(urllib.request, "urlopen", urlopen)

    with pytest.raises(hub.web.CheckError) as stopped:
        hub.web.exists(probe(), PAGE)

    assert str(stopped.value) == (
        f"{PAGE} answers 503, where the catalog bot expects 200 or 404; start it "
        "again later."
    )
    assert methods(urlopen) == [("HEAD", PAGE)] * hub.web.CHECK_TRIES
    assert hub.web.CHECK_TRIES == 3
    # A longer pause before the last try, and none after it.
    assert waits == list(hub.web.CHECK_PAUSES) == [2, 10]


@pytest.mark.parametrize(
    ("outage", "message"),
    [
        (
            lambda: failed(503),
            "answers 503, where the catalog bot expects 200 or 404; start it again "
            "later.",
        ),
        (
            lambda: urllib.error.URLError("timed out"),
            "can't be reached: <urlopen error timed out>",
        ),
    ],
)
def test_a_file_with_a_real_outage_stops_the_bot_as_today(
    monkeypatch: pytest.MonkeyPatch, outage: Any, message: str, waits: list[float]
) -> None:
    urlopen = Download(outage(), outage(), outage())
    monkeypatch.setattr(urllib.request, "urlopen", urlopen)

    with pytest.raises(hub.web.Unreachable) as stopped:
        fetch()(PAGE)

    assert str(stopped.value) == f"{PAGE} {message}"
    assert methods(urlopen) == [("GET", PAGE)] * 3
    assert waits == [2, 10]


@pytest.mark.parametrize("answer", [b"", failed(404), failed(410)])
def test_a_page_that_answers_is_asked_once(
    monkeypatch: pytest.MonkeyPatch, answer: bytes | Exception, waits: list[float]
) -> None:
    urlopen = Download(answer)
    monkeypatch.setattr(urllib.request, "urlopen", urlopen)

    assert hub.web.exists(probe(), PAGE) is isinstance(answer, bytes)
    assert methods(urlopen) == [("HEAD", PAGE)]
    assert waits == []


@pytest.mark.parametrize("answer", [HACS, failed(404), failed(410)])
def test_a_file_that_answers_is_asked_once(
    monkeypatch: pytest.MonkeyPatch, answer: bytes | Exception, waits: list[float]
) -> None:
    urlopen = Download(answer)
    monkeypatch.setattr(urllib.request, "urlopen", urlopen)

    assert fetch()(PAGE) == (answer if isinstance(answer, bytes) else None)
    assert methods(urlopen) == [("GET", PAGE)]
    assert waits == []


@pytest.mark.parametrize("code", [301, 400, 403])
def test_an_odd_answer_of_a_page_is_final(
    monkeypatch: pytest.MonkeyPatch, code: int, waits: list[float]
) -> None:
    urlopen = Download(failed(code))
    monkeypatch.setattr(urllib.request, "urlopen", urlopen)

    with pytest.raises(hub.web.CheckError) as stopped:
        hub.web.exists(probe(), PAGE)

    assert str(stopped.value) == (
        f"{PAGE} answers {code}, where the catalog bot expects 200 or 404; start it "
        "again later."
    )
    assert methods(urlopen) == [("HEAD", PAGE)]
    assert waits == []


@pytest.mark.parametrize(
    ("answer", "message"),
    [
        (
            failed(403),
            "answers 403, where the catalog bot expects 200 or 404; start it again "
            "later.",
        ),
        (
            failed(400),
            "answers 400, where the catalog bot expects 200 or 404; start it again "
            "later.",
        ),
        (ValueError("unknown url type"), "can't be reached: unknown url type"),
    ],
)
def test_an_odd_answer_of_a_file_is_final(
    monkeypatch: pytest.MonkeyPatch,
    answer: Exception,
    message: str,
    waits: list[float],
) -> None:
    urlopen = Download(answer)
    monkeypatch.setattr(urllib.request, "urlopen", urlopen)

    with pytest.raises(hub.web.CheckError) as stopped:
        fetch()(PAGE)

    assert str(stopped.value) == f"{PAGE} {message}"
    assert not isinstance(stopped.value, hub.web.Unreachable)
    assert methods(urlopen) == [("GET", PAGE)]
    assert waits == []


def test_an_address_that_cant_be_asked_is_final(
    monkeypatch: pytest.MonkeyPatch, waits: list[float]
) -> None:
    urlopen = Download(ValueError("unknown url type"))
    monkeypatch.setattr(urllib.request, "urlopen", urlopen)

    with pytest.raises(hub.web.CheckError) as stopped:
        probe()(PAGE)

    assert str(stopped.value) == f"{PAGE} can't be reached: unknown url type"
    assert not isinstance(stopped.value, hub.web.Unreachable)
    assert len(urlopen.requests) == 1
    assert waits == []


@pytest.mark.parametrize(
    ("moments", "tries"),
    [
        # The pause before the second try would end after the deadline.
        ([179.0], 1),
        # The second try ends so late that the longer pause would.
        ([0.0, 171.0], 2),
        # Each pause ends just at the deadline or before it.
        ([0.0, 170.0], 3),
    ],
)
def test_no_try_starts_after_the_deadline(
    monkeypatch: pytest.MonkeyPatch,
    moments: list[float],
    tries: int,
    waits: list[float],
) -> None:
    assert hub.web.CHECK_DEADLINE == 180
    # A page answers 503 to a HEAD request, from the moment 0.
    monkeypatch.setattr(hub.web, "clock", iter(moments).__next__)
    pages = Download(*[failed(503) for _ in range(tries)])
    monkeypatch.setattr(urllib.request, "urlopen", pages)

    with pytest.raises(hub.web.CheckError, match="answers 503"):
        hub.web.exists(hub.web.patient(hub.web.status, 0.0), PAGE)

    assert len(pages.requests) == tries
    assert waits == [2, 10][: tries - 1]

    # A file can't be reached.
    waits.clear()
    monkeypatch.setattr(hub.web, "clock", iter(moments).__next__)
    files = Download(*[TimeoutError("timed out") for _ in range(tries)])
    monkeypatch.setattr(urllib.request, "urlopen", files)

    with pytest.raises(hub.web.Unreachable, match="can't be reached: timed out"):
        hub.web.patient(hub.web.fetched, 0.0)(PAGE)

    assert len(files.requests) == tries
    assert waits == [2, 10][: tries - 1]
