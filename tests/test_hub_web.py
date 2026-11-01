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
from hub_helpers import Download, HACS, SITE, raw


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
def test_a_failed_download_is_tried_again(
    monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    urlopen = Download(error, b"{}")
    monkeypatch.setattr(urllib.request, "urlopen", urlopen)

    assert hub.web.download(f"{SITE}tool/search/search_index.json") == b"{}"
    assert len(urlopen.requests) == hub.web.TRIES == 2


def test_a_download_gives_up_after_its_tries(monkeypatch: pytest.MonkeyPatch) -> None:
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
