"""How the hooks and the bots ask the web: a download of the build, which its
callers survive, and the status and the content of a page or of a file for the catalog
bot, which stops when it can't tell.
"""

from __future__ import annotations

import http.client
import urllib.error
import urllib.request
from collections.abc import Callable
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


class SearchError(Exception):
    """The search index of a project website can't be downloaded, or isn't one."""


def download(url: str | urllib.request.Request) -> bytes:
    """The content of url, or of the address of a request with its headers, tried
    TRIES times before SearchError."""
    problem: Exception | None = None
    for _ in range(TRIES):
        try:
            with urllib.request.urlopen(url, timeout=SEARCH_TIMEOUT) as response:
                return bytes(response.read())
        except urllib.error.HTTPError as error:
            error.close()
            problem = error
        # As in status: a broken answer is no OSError, and urllib raises a
        # ValueError for an address that it can't ask.
        except (OSError, http.client.HTTPException, ValueError) as error:
            problem = error
    address = url.full_url if isinstance(url, urllib.request.Request) else url
    raise SearchError(f"{address} can't be downloaded: {problem}")


# What the catalog bot asks the web.


class CheckError(Exception):
    """The catalog bot can't tell whether the catalog is current: the list of the
    repositories is broken, or a website can't be reached or answers oddly."""


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
    # urllib raises a ValueError for an address that it can't ask.
    except (OSError, http.client.HTTPException, ValueError) as error:
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
        raise CheckError(
            f"{url} answers {error.code}, where the catalog bot expects 200 or 404; "
            "start it again later."
        ) from error
    # As in status.
    except (OSError, http.client.HTTPException, ValueError) as error:
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
