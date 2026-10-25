"""Tests of the script that takes the pictures of the website, scripts/screenshots.py,
with a Chromium of their own, which answers on the pipe of the DevTools protocol as
the real one does. scripts/screenshots.sh runs the script with the real one."""

from __future__ import annotations

import base64
import importlib.util
import json
import re
import runpy
import subprocess
import sys
from collections.abc import Callable, Iterator
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "screenshots.py"


def load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("screenshots", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Data classes look their module up in sys.modules.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


screenshots = load()

Message = dict[str, Any]


class Pipe:
    """Both ends of the pipe of a Chromium of the tests: it reads each command that
    the script writes, keeps it in sent, and queues what answer returns for it, the
    answer and the events, each ended by a NUL byte. It hands them out a few bytes at
    a time, so that a message comes in pieces, as through a real pipe."""

    def __init__(self, answer: Callable[[Message], Iterator[Message]]) -> None:
        self.answer = answer
        self.sent: list[Message] = []
        self.queued = b""
        self.closed = False

    def write(self, data: bytes) -> None:
        assert data.endswith(b"\0")
        for part in data.split(b"\0")[:-1]:
            message = json.loads(part)
            self.sent.append(message)
            for reply in self.answer(message):
                self.queued += json.dumps(reply).encode() + b"\0"

    def flush(self) -> None:
        pass

    def read1(self, size: int) -> bytes:
        chunk, self.queued = self.queued[: min(size, 97)], self.queued[min(size, 97) :]
        return chunk

    def close(self) -> None:
        self.closed = True


def png(number: int) -> bytes:
    """The bytes of the screenshot with the number: what the tests check them by."""
    return f"PNG {number}".encode()


class Browser:
    """A Chromium that answers every command that the script sends, as the real one
    does: a browser context, a page and a session for each picture, an event of the
    loaded page after each navigation, with others around it, and a screenshot with
    a number that counts up. failing names a method whose command fails, and script a
    word of a script of the page that fails."""

    def __init__(self, failing: str = "", script: str = "", exception: bool = True) -> None:
        self.failing = failing
        self.script = script
        self.exception = exception
        self.pages = 0
        self.pictures = 0

    def __call__(self, message: Message) -> Iterator[Message]:
        method, params = message["method"], message["params"]
        session = message.get("sessionId", "")
        reply: Message = {"id": message["id"], "result": {}}
        if method == self.failing:
            reply = {"id": message["id"], "error": {"code": -32000, "message": "refused"}}
        elif method == "Target.createBrowserContext":
            self.pages += 1
            reply["result"] = {"browserContextId": f"context {self.pages}"}
        elif method == "Target.createTarget":
            reply["result"] = {"targetId": f"target {self.pages}"}
        elif method == "Target.attachToTarget":
            reply["result"] = {"sessionId": f"session {self.pages}"}
        elif method == "Page.navigate":
            # An event of the page before the answer, and after it the load event of
            # another page, of another kind, and then of this one.
            yield {"method": "Page.frameStartedLoading", "sessionId": session, "params": {}}
            yield reply
            yield {"method": "Page.loadEventFired", "sessionId": "elsewhere", "params": {}}
            yield {"method": "Page.domContentEventFired", "sessionId": session, "params": {}}
            yield {"method": "Page.loadEventFired", "sessionId": session, "params": {}}
            return
        elif method == "Runtime.evaluate" and self.script and self.script in params["expression"]:
            details: Message = {"text": "Uncaught"}
            if self.exception:
                details["exception"] = {"description": "Error: the page kept changing"}
            reply["result"] = {"result": {"type": "object"}, "exceptionDetails": details}
        elif method == "Runtime.evaluate":
            reply["result"] = {"result": {"type": "undefined"}}
        elif method == "Page.captureScreenshot":
            self.pictures += 1
            reply["result"] = {"data": base64.b64encode(png(self.pictures)).decode()}
        yield reply


class Process:
    """The process of Chromium: it ends when asked, or on the second time when slow."""

    def __init__(self, slow: bool = False) -> None:
        self.slow = slow
        self.waits = 0
        self.killed = False

    def wait(self, timeout: float | None = None) -> int:
        self.waits += 1
        if self.slow and not self.killed:
            raise subprocess.TimeoutExpired("chromium", timeout or 0)
        return 0

    def kill(self) -> None:
        self.killed = True


def run(
    monkeypatch: pytest.MonkeyPatch, folder: Path, browser: Browser, process: Process
) -> tuple[int, Pipe, list[list[str]]]:
    """Runs the script as scripts/screenshots.sh does, with the Chromium of the tests
    in place of the real one: what it returns, the pipe and the commands it ran."""
    pipe = Pipe(browser)
    started: list[list[str]] = []

    def popen(command: list[str], **options: Any) -> Process:
        assert options == {"stdin": subprocess.PIPE, "stdout": subprocess.PIPE}
        started.append(command)
        process.stdin = pipe  # type: ignore[attr-defined]
        process.stdout = pipe  # type: ignore[attr-defined]
        return process

    monkeypatch.setattr(subprocess, "Popen", popen)
    arguments = ["/ms-playwright/chromium", "http://127.0.0.1:8000/", str(folder)]
    status = screenshots.main(arguments)
    return status, pipe, started


def commands(pipe: Pipe, method: str) -> list[Message]:
    return [message for message in pipe.sent if message["method"] == method]


def test_every_picture_is_taken_in_both_color_schemes_in_its_size(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    status, pipe, _ = run(monkeypatch, tmp_path / "pictures", Browser(), Process())

    assert status == 0
    sizes = commands(pipe, "Emulation.setDeviceMetricsOverride")
    media = commands(pipe, "Emulation.setEmulatedMedia")
    pages = commands(pipe, "Page.navigate")
    expected = [
        (shot, scheme) for shot in screenshots.SHOTS for scheme in screenshots.SCHEMES
    ]
    assert len(sizes) == len(media) == len(pages) == len(expected)
    for (shot, scheme), size, features, page in zip(expected, sizes, media, pages, strict=True):
        assert size["params"] == {
            "width": shot.width,
            "height": shot.height,
            "deviceScaleFactor": 1,
            "mobile": shot.phone,
        }
        assert features["params"]["features"] == [
            {"name": "prefers-color-scheme", "value": scheme},
            {"name": "prefers-reduced-motion", "value": "reduce"},
        ]
        # Each page in a context of its own, which the script closes after it.
        assert size["sessionId"] == features["sessionId"] == page["sessionId"]
        assert page["params"]["url"] == "http://127.0.0.1:8000" + shot.page
    created = commands(pipe, "Target.createBrowserContext")
    closed = [
        message["params"]["browserContextId"]
        for message in commands(pipe, "Target.disposeBrowserContext")
    ]
    assert len(created) == len(closed) == len(expected)
    assert closed == [f"context {number}" for number in range(1, len(expected) + 1)]


def test_the_pictures_are_those_of_readme_and_the_about_pages() -> None:
    # README.md shows the home page on a desktop and on a phone, the Trust page and
    # the search, which the About pages show too, the German one that of the German
    # home page, by the name with .de that MkDocs serves on the German pages; and
    # README.de.md the German home page on a desktop, by the same name with .de.
    shots = {shot.name: shot for shot in screenshots.SHOTS}

    assert list(shots) == [
        "website-{scheme}",
        "website-phone-{scheme}",
        "website-trust-{scheme}",
        "search-{scheme}",
        "search-{scheme}.de",
        "website-{scheme}.de",
    ]
    website, phone, trust, search, german, home = screenshots.SHOTS
    assert (website.width, website.height, website.phone) == (1280, 800, False)
    assert (home.width, home.height, home.phone) == (1280, 800, False)
    assert (website.page, home.page) == ("/", "/de/")
    assert (phone.width, phone.height, phone.phone) == (375, 812, True)
    assert trust.page == "/trust.html"
    assert (search.page, german.page) == ("/", "/de/")
    assert search.query == german.query == "token"
    assert search.width == german.width == 1280
    assert not any((website.query, phone.query, trust.query, home.query))


def test_a_picture_is_the_png_of_its_page_once_it_has_settled(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    folder = tmp_path / "pictures"
    _, pipe, _ = run(monkeypatch, folder, Browser(), Process())

    assert (folder / "website-light.png").read_bytes() == png(1)
    assert (folder / "website-dark.png").read_bytes() == png(2)
    assert (folder / "website-phone-light.png").read_bytes() == png(3)
    assert (folder / "website-trust-dark.png").read_bytes() == png(6)
    # The first page: it settles after the load event, before its screenshot.
    session = [m for m in pipe.sent if m.get("sessionId") == "session 1"]
    methods = [m["method"] for m in session]
    assert methods == [
        "Page.enable",
        "Emulation.setDeviceMetricsOverride",
        "Emulation.setEmulatedMedia",
        "Page.navigate",
        "Runtime.evaluate",
        "Page.captureScreenshot",
    ]
    settle = session[4]["params"]
    assert settle["expression"] == (
        f"({screenshots.SETTLE})({screenshots.QUIET}, {screenshots.PATIENCE})"
    )
    assert settle["awaitPromise"] and settle["returnByValue"]
    assert session[5]["params"] == {"format": "png"}


def test_a_search_is_typed_a_letter_at_a_time_into_frames(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    folder = tmp_path / "pictures"
    _, pipe, _ = run(monkeypatch, folder, Browser(), Process())

    # The six pictures before it took the screenshots 1 to 6, so the light search
    # starts with 7: the empty search, a frame for each letter, and the chosen
    # result.
    shows = json.loads((folder / "search-light" / "frames.json").read_text(encoding="utf-8"))
    assert shows == [
        ["00.png", screenshots.EMPTY],
        ["01.png", screenshots.LETTER],
        ["02.png", screenshots.LETTER],
        ["03.png", screenshots.LETTER],
        ["04.png", screenshots.LETTER],
        ["05.png", screenshots.RESULTS],
        ["06.png", screenshots.CHOSEN],
    ]
    for number, (file, _) in enumerate(shows):
        assert (folder / "search-light" / file).read_bytes() == png(7 + number)
    # No still of the search: scripts/screenshots.sh makes it from the last frame.
    assert not (folder / "search-light.png").exists()
    german = folder / "search-dark.de"
    assert json.loads((german / "frames.json").read_text())[-1] == ["06.png", screenshots.CHOSEN]
    # The German one in the dark colors is the fourth search after the six pictures.
    assert (german / "06.png").read_bytes() == png(6 + 7 * 4)

    session = [m for m in pipe.sent if m.get("sessionId") == "session 7"]
    steps = []
    for message in session:
        if message["method"] == "Runtime.evaluate":
            expression = message["params"]["expression"]
            name = next(
                name
                for name in ("SETTLE", "OPEN_SEARCH", "WATCH", "CHANGED")
                if expression.startswith(f"({getattr(screenshots, name)})")
            )
            steps.append(name)
        elif message["method"] == "Input.dispatchKeyEvent":
            event = message["params"]
            steps.append(f"{event['type']} {event['key']} {event.get('text', '')}".strip())
        elif message["method"] == "Page.captureScreenshot":
            steps.append("picture")
    letters = []
    for letter in "token":
        letters += ["WATCH", f"keyDown {letter} {letter}", f"keyUp {letter}"]
        letters += ["CHANGED", "SETTLE", "picture"]
    assert steps == [
        "SETTLE",
        "OPEN_SEARCH",
        "SETTLE",
        "picture",
        *letters,
        "keyDown ArrowDown",
        "keyUp ArrowDown",
        "SETTLE",
        "picture",
    ]
    arrow = next(
        m["params"] for m in session if m["params"].get("key") == "ArrowDown"
    )
    assert arrow == {"type": "keyDown", "key": "ArrowDown", "windowsVirtualKeyCode": 40}


def test_the_scripts_of_the_page_get_their_numbers_as_json() -> None:
    pipe = Pipe(Browser())
    chromium = screenshots.Chromium(pipe, pipe)

    assert chromium.run("session", "(a, b) => a", 500, "token") is None
    assert pipe.sent[0]["params"]["expression"] == '((a, b) => a)(500, "token")'
    assert pipe.sent[0]["sessionId"] == "session"


def test_chromium_starts_with_its_protocol_on_the_pipe(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    process = Process()
    _, pipe, started = run(monkeypatch, tmp_path, Browser(), process)

    # The shell gives Chromium the pipe of the commands as its file descriptor 3 and
    # that of the answers as 4, as --remote-debugging-pipe expects them.
    assert started == [
        [
            "sh",
            "-c",
            'exec "$@" 3<&0 4>&1 </dev/null >&2',
            "sh",
            "/ms-playwright/chromium",
            "--no-sandbox",
            "--hide-scrollbars",
            "--remote-debugging-pipe",
            "about:blank",
        ]
    ]
    # Chromium ends once the pipe of its commands closes.
    assert pipe.closed
    assert process.waits == 1 and not process.killed


def test_chromium_is_killed_when_it_does_not_end(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    process = Process(slow=True)
    status, _, _ = run(monkeypatch, tmp_path, Browser(), process)

    assert status == 0
    assert process.killed
    assert process.waits == 2


@pytest.mark.parametrize(
    ("browser", "reason"),
    [
        (Browser(failing="Page.captureScreenshot"), "Page.captureScreenshot: refused"),
        (
            Browser(script="the search never got ready"),
            "A script failed in the page: Error: the page kept changing",
        ),
        (
            Browser(script="the page never loaded", exception=False),
            "A script failed in the page: Uncaught",
        ),
    ],
)
def test_a_failure_names_its_reason_and_stops_chromium(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    browser: Browser,
    reason: str,
) -> None:
    process = Process()
    status, pipe, _ = run(monkeypatch, tmp_path, browser, process)

    assert status == 1
    assert capsys.readouterr().err.endswith(f"Taking the pictures failed: {reason}\n")
    # The page that failed closes its context all the same.
    assert commands(pipe, "Target.disposeBrowserContext")
    assert pipe.closed and process.waits == 1


def test_a_page_that_cannot_open_fails() -> None:
    class Unreachable(Browser):
        def __call__(self, message: Message) -> Iterator[Message]:
            if message["method"] != "Page.navigate":
                yield from super().__call__(message)
                return
            error = "net::ERR_CONNECTION_REFUSED"
            yield {"id": message["id"], "result": {"frameId": "1", "errorText": error}}

    pipe = Pipe(Unreachable())
    page = screenshots.Page(screenshots.Chromium(pipe, pipe), screenshots.SHOTS[0], "light")

    with pytest.raises(screenshots.ChromiumError, match="ERR_CONNECTION_REFUSED"):
        page.open("http://127.0.0.1:8000/")


def test_a_chromium_that_ends_fails() -> None:
    pipe = Pipe(lambda message: iter(()))
    chromium = screenshots.Chromium(pipe, pipe)

    with pytest.raises(screenshots.ChromiumError, match="Chromium ended"):
        chromium.send("Browser.getVersion")


def test_the_events_of_a_closed_page_are_dropped() -> None:
    pipe = Pipe(Browser())
    chromium = screenshots.Chromium(pipe, pipe)
    page = screenshots.Page(chromium, screenshots.SHOTS[0], "dark")
    page.send("Page.navigate", {"url": "about:blank"})
    chromium.events.append({"method": "Target.targetCreated", "params": {}})

    page.close()

    # The events of other pages stay, those of the closed one are gone.
    assert chromium.events == [
        {"method": "Target.targetCreated", "params": {}},
        {"method": "Page.loadEventFired", "sessionId": "elsewhere", "params": {}},
    ]


def test_the_script_runs_as_a_program(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    pipe = Pipe(Browser())

    def popen(command: list[str], **options: Any) -> Process:
        process = Process()
        process.stdin = pipe  # type: ignore[attr-defined]
        process.stdout = pipe  # type: ignore[attr-defined]
        return process

    monkeypatch.setattr(subprocess, "Popen", popen)
    address = "http://127.0.0.1:8000"
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "chromium", address, str(tmp_path)])

    with pytest.raises(SystemExit) as stop:
        runpy.run_path(str(SCRIPT), run_name="__main__")

    assert stop.value.code == 0
    assert (tmp_path / "website-light.png").read_bytes() == png(1)


def test_the_script_needs_the_standard_library_alone() -> None:
    # The image of Playwright has Python, but none of its packages, and the
    # container no network to install one.
    text = SCRIPT.read_text(encoding="utf-8")
    imported = {
        line.split()[1].split(".")[0]
        for line in text.splitlines()
        if line.startswith(("import ", "from "))
    }

    assert imported <= set(sys.stdlib_module_names) | {"__future__"}


def test_the_shell_runs_the_script_with_the_chromium_of_the_image() -> None:
    text = (ROOT / "scripts" / "screenshots.sh").read_text(encoding="utf-8")

    assert "python3 -I -B /work/scripts/screenshots.py \\\n" in text
    assert "/chrome-headless-shell-linux64/chrome-headless-shell \\\n" in text
    # Without a network, from the website that the script built.
    assert "--network none" in text
    assert "http://127.0.0.1:8000 /tmp/pictures" in text


def webp(path: Path) -> tuple[int, int, bool]:
    """The width and the height of a WebP, and whether it is an animation: from
    the header of an extended WebP, or from that of a lossless one."""
    data = path.read_bytes()
    assert data[:4] == b"RIFF" and data[8:12] == b"WEBP", path
    if data[12:16] == b"VP8X":
        width = 1 + int.from_bytes(data[24:27], "little")
        height = 1 + int.from_bytes(data[27:30], "little")
        return width, height, bool(data[20] & 0x02)
    assert data[12:16] == b"VP8L" and data[20] == 0x2F, path
    bits = int.from_bytes(data[21:25], "little")
    return 1 + (bits & 0x3FFF), 1 + (bits >> 14 & 0x3FFF), False


def test_the_pictures_are_lossless_webps_of_their_size() -> None:
    # scripts/screenshots.sh turns every screenshot but the two at the top of
    # README.md into a lossless WebP, and the frames of a search into an animation
    # with its last frame as the still beside it.
    images = ROOT / "docs" / "images"
    for scheme in screenshots.SCHEMES:
        assert webp(images / f"website-{scheme}.de.webp") == (1280, 800, False)
        assert webp(images / f"website-phone-{scheme}.webp") == (375, 812, False)
        assert webp(images / f"website-trust-{scheme}.webp") == (1280, 800, False)
        for language in ("", ".de"):
            assert webp(images / f"search-{scheme}{language}.webp") == (1280, 800, True)
            assert webp(images / f"search-still-{scheme}{language}.webp") == (1280, 800, False)


def test_the_search_plays_once_and_stays_on_its_last_frame() -> None:
    # Motion that starts on its own must end within 5 s (WCAG 2.2.2): the ANIM
    # chunk of every search animation plays it once, and scripts/screenshots.sh
    # saves it that way.
    images = ROOT / "docs" / "images"
    for scheme in screenshots.SCHEMES:
        for language in ("", ".de"):
            data = (images / f"search-{scheme}{language}.webp").read_bytes()
            anim = data.find(b"ANIM")
            assert anim > 0
            assert int.from_bytes(data[anim + 12 : anim + 14], "little") == 1
    assert "loop=1," in (ROOT / "scripts" / "screenshots.sh").read_text(encoding="utf-8")


def pictures(text: str) -> list[str]:
    return re.findall(r"<picture>.*?</picture>", text, re.S)


def test_the_readme_shows_every_picture_in_both_color_schemes() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    shown = re.findall(r'(?:src|srcset)="docs/images/((?:website|search)[^"]*)"', readme)

    assert sorted(shown) == sorted(
        f"{name}-{scheme}.{ending}"
        for name, ending in (
            ("website", "png"),
            ("website-phone", "webp"),
            ("website-trust", "webp"),
            ("search", "webp"),
            ("search-still", "webp"),
        )
        for scheme in screenshots.SCHEMES
    )
    for name in shown:
        assert (ROOT / "docs" / "images" / name).is_file(), name
    # The browser takes the first source that fits: the still for a reader who
    # prefers reduced motion, in either scheme, before the animation.
    search = next(picture for picture in pictures(readme) if "search-light.webp" in picture)
    assert re.findall(r'<source media="([^"]+)"', search) == [
        "(prefers-reduced-motion: reduce) and (prefers-color-scheme: dark)",
        "(prefers-reduced-motion: reduce)",
        "(prefers-color-scheme: dark)",
    ]
    assert search.index("search-still-dark.webp") < search.index("search-still-light.webp")


@pytest.mark.parametrize("page", ["about.md", "about.de.md"])
def test_the_about_pages_show_the_search_in_the_scheme_and_motion_of_the_reader(
    page: str,
) -> None:
    # The hooks of the blueprint turn a <picture> with a source for each color
    # scheme into two pictures, which the website shows in the scheme the reader
    # picks, and drop every other source. So each scheme has a <picture> of its
    # own, whose one source is the still for a reader who prefers reduced motion,
    # and the plugin glightbox leaves them alone: a link around the picture would
    # take it out of its <picture>.
    text = (ROOT / "docs" / page).read_text(encoding="utf-8")
    search = [picture for picture in pictures(text) if "images/search-" in picture]

    assert len(search) == 2
    for picture, scheme in zip(search, screenshots.SCHEMES, strict=True):
        assert (
            '<source media="(prefers-reduced-motion: reduce)" '
            f'srcset="images/search-still-{scheme}.webp">'
        ) in picture
        assert f'<img src="images/search-{scheme}.webp#only-{scheme}" class="off-glb"' in picture
        assert re.search(r'alt="Animation: [^"]+"', picture)
    # The German page names the English pictures, and the website serves it the
    # German ones at their addresses, NAME.de.webp, as it does for every file of a
    # further language; the website leaves out only those of README.md alone.
    if page == "about.de.md":
        for scheme in screenshots.SCHEMES:
            for name in (f"search-{scheme}.de.webp", f"search-still-{scheme}.de.webp"):
                assert (ROOT / "docs" / "images" / name).is_file(), name
    config = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    excluded = re.search(r"^exclude_docs: \|\n((?:  .+\n)+)", config, re.M)
    assert excluded is not None
    assert not any("search" in pattern for pattern in excluded[1].split())
