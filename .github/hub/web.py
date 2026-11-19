"""How the hooks and the bots ask the web: a download of the build, which its
callers survive, and the status and the content of a page or of a file for the catalog
bot, which stops when it can't tell.
"""

from __future__ import annotations

import http.client
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from datetime import datetime
from email.message import Message
from email.utils import parsedate_to_datetime
from typing import TypeVar
from urllib.parse import urlsplit

from .catalog import SITE

# A file of a repository, at a tag or on the default branch, from
# raw.githubusercontent.com, which needs no token.
RAW = "https://raw.githubusercontent.com/{}/{}/{}"
DEFAULT_BRANCH = "HEAD"

# How many seconds the catalog bot waits for a website, and the answers of a
# website that is gone.
TIMEOUT = 30
GONE = frozenset({404, 410})

# How many seconds a download of the build may take, and how many times it is
# tried.
SEARCH_TIMEOUT = 10
TRIES = 2

# How many seconds a download of the build waits before it tries again, at least;
# the most that an answer may ask it to wait, as the API of GitHub does when its
# limit of requests is used up, beyond which the build doesn't wait and goes on
# without the file; and how many seconds the downloads of one build wait together
# at most, so that the build ends well within the five minutes of its step.
PAUSE = 2.0
LONGEST_WAIT = 30.0
WAITING = 120.0

# What waits and what tells the time, which the tests replace.
sleep = time.sleep
clock = time.time


class SearchError(Exception):
    """The search index of a project website can't be downloaded, or isn't one."""


class Patience:
    """How many seconds the downloads of one build may still wait for their next
    tries together, which the threads that download at once share."""

    def __init__(self, seconds: float) -> None:
        self.left = seconds
        self.lock = threading.Lock()

    def take(self, seconds: float) -> bool:
        """Whether the downloads may wait seconds more, which it then counts."""
        with self.lock:
            if seconds > self.left:
                return False
            self.left -= seconds
            return True


PATIENCE = Patience(WAITING)


def asked_wait(headers: Message | None, now: float) -> float | None:
    """How many seconds an answer with headers asks a client to wait at the moment
    now, in seconds since the epoch, before it asks again, as the API of GitHub does:
    its Retry-After, in seconds or as a date, or else the moment x-ratelimit-reset
    when x-ratelimit-remaining is 0. None when it asks for no wait."""
    if headers is None:
        return None
    after = (headers.get("Retry-After") or "").strip()
    if after.isdigit():
        return float(after)
    if after:
        try:
            moment: datetime | None = parsedate_to_datetime(after)
        # No date that HTTP knows.
        except ValueError:
            moment = None
        if moment is not None:
            return max(0.0, moment.timestamp() - now)
    reset = (headers.get("x-ratelimit-reset") or "").strip()
    if (headers.get("x-ratelimit-remaining") or "").strip() == "0" and reset.isdigit():
        return max(0.0, int(reset) - now)
    return None


def download(url: str | urllib.request.Request) -> bytes:
    """The content of url, or of the address of a request with its headers, tried
    TRIES times before SearchError. Between its tries it waits PAUSE seconds, or as
    long as the answer asks, unless that is longer than LONGEST_WAIT or than the
    PATIENCE of the build has left: then it gives up at once."""
    address = url.full_url if isinstance(url, urllib.request.Request) else url
    for attempt in range(1, TRIES + 1):
        try:
            with urllib.request.urlopen(url, timeout=SEARCH_TIMEOUT) as response:
                return bytes(response.read())
        except urllib.error.HTTPError as error:
            error.close()
            problem = str(error)
            wait = max(PAUSE, asked_wait(error.headers, clock()) or 0.0)
        # As in status: a broken answer is no OSError, and urllib raises a
        # ValueError for an address that it can't ask.
        except (OSError, http.client.HTTPException, ValueError) as error:
            problem, wait = str(error), PAUSE
        if attempt < TRIES:
            if wait > LONGEST_WAIT:
                problem += f", and it asks to wait {round(wait)} seconds"
                break
            if not PATIENCE.take(wait):
                problem += ", and the build has waited long enough for its downloads"
                break
            sleep(wait)
    raise SearchError(f"{address} can't be downloaded: {problem}")


# What the catalog bot asks the web.


class CheckError(Exception):
    """The catalog bot can't tell whether the catalog is current: the list of the
    repositories is broken, or a website can't be reached or answers oddly."""


class Unreachable(CheckError):
    """A website can't be reached for the moment: it can't be connected to, its
    answer breaks off, or it answers with a status of an outage, which a short
    outage of GitHub Pages gives and a later try may not."""


# The answers of a website that may be a short outage and say nothing about the page:
# too many requests, and every error of the server, such as 503.
TOO_MANY_REQUESTS = 429
SERVER_ERROR = 500


def outage(code: int) -> bool:
    """Whether a website that answers with the status code may answer otherwise a
    moment later."""
    return code == TOO_MANY_REQUESTS or code >= SERVER_ERROR


# How the catalog bot and its watch ask again for an address that can't be reached
# for the moment: the seconds of the pause before each further try, so that it is
# tried once more than it pauses, and how many seconds after its start a run may
# still pause, its tries included, of which each may take TIMEOUT, so that the watch
# ends well within the 10 minutes of its job, of which the wait for Harden-Runner
# takes up to four.
CHECK_PAUSES = (PAUSE, 10.0)
CHECK_TRIES = len(CHECK_PAUSES) + 1
CHECK_DEADLINE = 180.0

Answer = TypeVar("Answer")


def patient(ask: Callable[[str], Answer], since: float) -> Callable[[str], Answer]:
    """ask, such as fetched or status, which asks once, tried CHECK_TRIES times for
    an address that can't be reached for the moment, with the pauses of
    CHECK_PAUSES, while a pause ends within CHECK_DEADLINE of the moment since, by
    the clock. Its last answer or error stays as it is, so that a real outage stops
    the bot as a single try does: the watch asks well over a hundred addresses every
    day, and a short outage of one is no finding. Every other answer and error is
    final, and asked once."""

    def waits(pause: float) -> bool:
        return clock() + pause <= since + CHECK_DEADLINE

    def again(url: str) -> Answer:
        for pause in CHECK_PAUSES:
            try:
                answer = ask(url)
            except Unreachable:
                if not waits(pause):
                    raise
            else:
                lost = isinstance(answer, int) and outage(answer)
                if not lost or not waits(pause):
                    return answer
            sleep(pause)
        return ask(url)

    return again


def address(url: str) -> str:
    """url as the bot compares addresses: with https://, its host in lowercase and
    its path ending in a slash, as GitHub Pages serves the folder of a website."""
    parts = urlsplit(url.strip())
    return f"https://{parts.netloc.lower()}{parts.path.rstrip('/')}/"


def at_site(url: str) -> bool:
    """Whether url is the address of a website in a folder of SITE, as that of a
    project is: neither this website at its root nor one elsewhere."""
    found = address(url)
    return found.startswith(SITE) and found != SITE


def within(url: str, website: str) -> bool:
    """Whether url is website or a page of it, such as its setup.html: an address
    in its folder, which GitHub Pages serves from that website alone, so that no
    other repository can have its own website there. A website at the root of SITE
    holds no other: every repository's website is in a folder of it."""
    folder = address(website)
    return folder != SITE and address(url).startswith(folder)


def status(url: str) -> int:
    """The HTTP status with which url answers a HEAD request, after its redirects."""
    request = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return int(response.status)
    except urllib.error.HTTPError as error:
        error.close()
        return error.code
    # http.client.HTTPException, such as a broken status line, is no OSError, and
    # urllib raises a ValueError for an address that it can't ask, which no later
    # try can.
    except (OSError, http.client.HTTPException) as error:
        raise Unreachable(f"{url} can't be reached: {error}") from error
    except ValueError as error:
        raise CheckError(f"{url} can't be reached: {error}") from error


def fetched(url: str) -> bytes | None:
    """The content of url, after its redirects, or None when it answers 404 or 410:
    a file that is gone."""
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT) as response:
            return bytes(response.read())
    except urllib.error.HTTPError as error:
        error.close()
        if error.code in GONE:
            return None
        odd = Unreachable if outage(error.code) else CheckError
        raise odd(
            f"{url} answers {error.code}, where the catalog bot expects 200 or 404; "
            "start it again later."
        ) from error
    # As in status.
    except (OSError, http.client.HTTPException) as error:
        raise Unreachable(f"{url} can't be reached: {error}") from error
    except ValueError as error:
        raise CheckError(f"{url} can't be reached: {error}") from error


def exists(probe: Callable[[str], int], url: str) -> bool:
    """Whether the website at url is there, by the status that probe gives: 200 is
    a website, 404 and 410 none, and anything else no answer to rely on."""
    code = probe(url)
    if code == 200:
        return True
    if code in GONE:
        return False
    raise CheckError(
        f"{url} answers {code}, where the catalog bot expects 200 or 404; "
        "start it again later."
    )
