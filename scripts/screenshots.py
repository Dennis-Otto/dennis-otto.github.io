"""The pictures of the website for README.md, README.de.md and the About pages,
taken in the
headless Chromium of Playwright's image. scripts/screenshots.sh runs it in that
image, with the website that it built, served on the loopback of the container
without a network:

    python3 scripts/screenshots.py CHROMIUM ADDRESS FOLDER

Every picture of SHOTS opens its page in a browser context of its own, as a new
reader would, in its size, in the light and in the dark colors and with reduced
motion, and is taken once the page has settled: loaded, its fonts and the pictures
in sight drawn, and nothing in it changing for a moment. A picture with a query is
the search of the website as a reader uses it: it clicks into the search box once
the search is ready, types the query a letter at a time, takes a frame after each
letter, once its results are there, and last chooses the first result with the
arrow key. The caret of the search box is hidden, because it blinks.

It writes the PNG of every picture into FOLDER as NAME.png, such as
website-light.png, and the frames of a search as NAME/NN.png with frames.json
beside them, which lists them with the milliseconds that each shows.
scripts/screenshots.sh makes the WebPs from them: an animation of the frames, and
its last frame as the still for a reader who prefers reduced motion.

The image has the browsers of Playwright, but not its package, and the container has
no network to install one, so this script drives Chromium itself, with the standard
library alone: through the DevTools protocol on the pipe of --remote-debugging-pipe.
tests/test_screenshots.py runs it with a Chromium of its own, which answers as the
real one does.
"""

from __future__ import annotations

import base64
import io
import json
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMES = ("light", "dark")
# How long a page may take to load and settle, and the search to get ready and to
# show its results, in milliseconds.
PATIENCE = 30_000
# How long nothing in a page may change before it counts as settled, in
# milliseconds.
QUIET = 500
# How long each frame of a search shows, in milliseconds: the empty search box, each
# letter as it is typed, the results of the whole query, and its first result once
# the arrow key chose it, before the animation starts again.
EMPTY = 900
LETTER = 180
RESULTS = 1500
CHOSEN = 3200


@dataclass(frozen=True)
class Shot:
    """A picture of a page: its name, in which {scheme} stands for the color scheme,
    the page, the size of the window in CSS pixels, whether the window is a phone's,
    and the query that a search types."""

    name: str
    page: str
    width: int = 1280
    height: int = 800
    phone: bool = False
    query: str = ""


# Every picture. README.md shows the home page on a desktop and on a phone, the
# Trust page and the search, which the About pages show as well: the German one that
# of the German home page, whose name ends in .de as MkDocs wants it, so that the
# website serves it in place of the English one on the German pages. README.de.md
# shows the German home page on a desktop, by the same name with .de.
SHOTS = (
    Shot("website-{scheme}", "/"),
    Shot("website-phone-{scheme}", "/", width=375, height=812, phone=True),
    Shot("website-trust-{scheme}", "/trust.html"),
    Shot("search-{scheme}", "/", query="token"),
    Shot("search-{scheme}.de", "/de/", query="token"),
    Shot("website-{scheme}.de", "/de/"),
)

# Resolves once the page has loaded, its fonts are ready, the pictures in sight are
# drawn, and neither the page nor an animation has changed for QUIET milliseconds;
# fails after PATIENCE. Runtime.evaluate calls it with both numbers.
SETTLE = """async (quiet, patience) => {
  const end = performance.now() + patience;
  const later = () => new Promise((go) => setTimeout(go, 50));
  while (document.readyState !== "complete") {
    if (performance.now() > end) throw new Error("the page never loaded");
    await later();
  }
  await document.fonts.ready;
  const inSight = (image) => {
    const box = image.getBoundingClientRect();
    return box.bottom > 0 && box.top < innerHeight && box.right > 0 && box.left < innerWidth;
  };
  await Promise.all([...document.images].filter(inSight).map((image) => image.decode().catch(() => {})));
  let changed = performance.now();
  const observer = new MutationObserver(() => { changed = performance.now(); });
  observer.observe(document, { subtree: true, childList: true, attributes: true, characterData: true });
  try {
    while (performance.now() - changed < quiet ||
        document.getAnimations().some((animation) => animation.playState === "running")) {
      if (performance.now() > end) throw new Error("the page kept changing");
      await later();
    }
  } finally {
    observer.disconnect();
  }
}"""

# Hides the caret, opens the search the way a click into its box does, and resolves
# once Material for MkDocs has its index and shows its placeholder.
OPEN_SEARCH = """async (patience) => {
  const end = performance.now() + patience;
  const style = document.createElement("style");
  style.textContent = "* { caret-color: transparent !important; }";
  document.head.append(style);
  const box = document.querySelector(".md-search__input");
  box.focus();
  box.click();
  const config = JSON.parse(document.getElementById("__config").textContent);
  const ready = config.translations["search.result.placeholder"];
  const meta = document.querySelector(".md-search-result__meta");
  while (meta.textContent.trim() !== ready) {
    if (performance.now() > end) throw new Error("the search never got ready");
    await new Promise((go) => setTimeout(go, 50));
  }
}"""

# Counts the changes of the results from here on, so that RESULTS can wait for those
# of the letter that comes next.
WATCH = """() => {
  window.__results = 0;
  const observer = new MutationObserver(() => { window.__results += 1; });
  observer.observe(document.querySelector(".md-search-result"),
    { subtree: true, childList: true, characterData: true });
}"""

# Resolves once the results have changed since WATCH.
CHANGED = """async (patience) => {
  const end = performance.now() + patience;
  while (window.__results === 0) {
    if (performance.now() > end) throw new Error("the search showed no results");
    await new Promise((go) => setTimeout(go, 50));
  }
}"""


class ChromiumError(RuntimeError):
    """Chromium refused a command, a script in a page failed, or Chromium ended."""


class Chromium:
    """A Chromium driven through its DevTools protocol on the pipe of
    --remote-debugging-pipe: each message a JSON object that a NUL byte ends, the
    commands on its file descriptor 3 and its answers and events on 4. Its events
    wait in a list until a command asks for one."""

    def __init__(self, answers: io.BufferedIOBase, commands: io.BufferedIOBase) -> None:
        self.answers = answers
        self.commands = commands
        self.received = b""
        self.events: list[dict[str, Any]] = []
        self.last = 0

    def send(
        self, method: str, params: dict[str, Any] | None = None, session: str = ""
    ) -> dict[str, Any]:
        """Sends a command, to a page when session names it, and returns the
        result of its answer."""
        self.last += 1
        message: dict[str, Any] = {"id": self.last, "method": method, "params": params or {}}
        if session:
            message["sessionId"] = session
        self.commands.write(json.dumps(message).encode() + b"\0")
        self.commands.flush()
        while True:
            answer = self.receive()
            if answer.get("id") != self.last:
                self.events.append(answer)
            elif "error" in answer:
                raise ChromiumError(f"{method}: {answer['error'].get('message')}")
            else:
                return answer.get("result", {})

    def receive(self) -> dict[str, Any]:
        """The next message from Chromium."""
        while b"\0" not in self.received:
            chunk = self.answers.read1(65536)
            if not chunk:
                raise ChromiumError("Chromium ended")
            self.received += chunk
        message, self.received = self.received.split(b"\0", 1)
        return json.loads(message)

    def wait(self, method: str, session: str) -> dict[str, Any]:
        """Waits for an event of a page and returns it, out of the events that
        wait."""
        while True:
            for event in self.events:
                if event.get("method") == method and event.get("sessionId") == session:
                    self.events = [other for other in self.events if other is not event]
                    return event
            self.events.append(self.receive())

    def run(self, session: str, script: str, *arguments: object) -> Any:
        """Runs a function of JavaScript in a page with the arguments, awaits what
        it returns and returns its value."""
        call = f"({script})({', '.join(json.dumps(argument) for argument in arguments)})"
        result = self.send(
            "Runtime.evaluate",
            {"expression": call, "awaitPromise": True, "returnByValue": True},
            session,
        )
        if "exceptionDetails" in result:
            details = result["exceptionDetails"]
            reason = details.get("exception", {}).get("description") or details.get("text")
            raise ChromiumError(f"A script failed in the page: {reason}")
        return result["result"].get("value")


class Page:
    """A page in a browser context of its own, in the size, the color scheme and
    the reduced motion of a picture."""

    def __init__(self, chromium: Chromium, shot: Shot, scheme: str) -> None:
        self.chromium = chromium
        self.context = chromium.send("Target.createBrowserContext")["browserContextId"]
        target = chromium.send(
            "Target.createTarget", {"url": "about:blank", "browserContextId": self.context}
        )["targetId"]
        self.session = chromium.send(
            "Target.attachToTarget", {"targetId": target, "flatten": True}
        )["sessionId"]
        self.send("Page.enable")
        self.send(
            "Emulation.setDeviceMetricsOverride",
            {
                "width": shot.width,
                "height": shot.height,
                "deviceScaleFactor": 1,
                "mobile": shot.phone,
            },
        )
        self.send(
            "Emulation.setEmulatedMedia",
            {
                "features": [
                    {"name": "prefers-color-scheme", "value": scheme},
                    {"name": "prefers-reduced-motion", "value": "reduce"},
                ]
            },
        )

    def send(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.chromium.send(method, params, self.session)

    def run(self, script: str, *arguments: object) -> Any:
        return self.chromium.run(self.session, script, *arguments)

    def open(self, address: str) -> None:
        """Opens the page and waits until it has loaded and settled."""
        result = self.send("Page.navigate", {"url": address})
        if result.get("errorText"):
            raise ChromiumError(f"{address}: {result['errorText']}")
        self.chromium.wait("Page.loadEventFired", self.session)
        self.settle()

    def settle(self) -> None:
        self.run(SETTLE, QUIET, PATIENCE)

    def press(self, key: str, text: str = "", code: int = 0) -> None:
        """Presses a key, as a keyboard does: down, with the text it types, and up."""
        down: dict[str, Any] = {"type": "keyDown", "key": key}
        if text:
            down["text"] = text
        if code:
            down["windowsVirtualKeyCode"] = code
        self.send("Input.dispatchKeyEvent", down)
        self.send("Input.dispatchKeyEvent", {"type": "keyUp", "key": key})

    def picture(self) -> bytes:
        """The PNG of what the window shows."""
        data = self.send("Page.captureScreenshot", {"format": "png"})["data"]
        return base64.b64decode(data)

    def close(self) -> None:
        """Closes the page with its context, and drops the events that it left."""
        self.chromium.send("Target.disposeBrowserContext", {"browserContextId": self.context})
        self.chromium.events = [
            event for event in self.chromium.events if event.get("sessionId") != self.session
        ]


def search(page: Page, query: str) -> list[tuple[bytes, int]]:
    """The frames of a search, each with the milliseconds that it shows."""
    page.run(OPEN_SEARCH, PATIENCE)
    page.settle()
    frames = [(page.picture(), EMPTY)]
    for letter in query:
        page.run(WATCH)
        page.press(letter, text=letter)
        page.run(CHANGED, PATIENCE)
        page.settle()
        frames.append((page.picture(), LETTER))
    frames[-1] = (frames[-1][0], RESULTS)
    page.press("ArrowDown", code=40)
    page.settle()
    frames.append((page.picture(), CHOSEN))
    return frames


def take(chromium: Chromium, address: str, folder: Path, shot: Shot, scheme: str) -> None:
    """Takes a picture in one color scheme, or for a search its frames."""
    name = shot.name.format(scheme=scheme)
    page = Page(chromium, shot, scheme)
    try:
        page.open(address.rstrip("/") + shot.page)
        frames = search(page, shot.query) if shot.query else [(page.picture(), 0)]
    finally:
        page.close()
    if not shot.query:
        (folder / f"{name}.png").write_bytes(frames[0][0])
        return
    (folder / name).mkdir()
    shows = []
    for number, (frame, milliseconds) in enumerate(frames):
        file = f"{number:02}.png"
        (folder / name / file).write_bytes(frame)
        shows.append([file, milliseconds])
    (folder / name / "frames.json").write_text(json.dumps(shows), encoding="utf-8")


def launch(program: str) -> tuple[subprocess.Popen[bytes], Chromium]:
    """Starts Chromium with its DevTools protocol on a pipe: the shell gives it the
    pipe of commands as its file descriptor 3 and the pipe of answers as 4, and its
    standard output goes to the standard error, with its log."""
    process = subprocess.Popen(
        [
            "sh",
            "-c",
            'exec "$@" 3<&0 4>&1 </dev/null >&2',
            "sh",
            program,
            "--no-sandbox",
            "--hide-scrollbars",
            "--remote-debugging-pipe",
            "about:blank",
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )
    assert process.stdin is not None and process.stdout is not None  # both are pipes
    return process, Chromium(process.stdout, process.stdin)


def main(arguments: Sequence[str] | None = None) -> int:
    program, address, folder = sys.argv[1:] if arguments is None else arguments
    pictures = Path(folder)
    pictures.mkdir(parents=True, exist_ok=True)
    process, chromium = launch(program)
    try:
        for shot in SHOTS:
            for scheme in SCHEMES:
                take(chromium, address, pictures, shot, scheme)
                print(f"Took {shot.name.format(scheme=scheme)}.", file=sys.stderr)
    except ChromiumError as error:
        print(f"Taking the pictures failed: {error}", file=sys.stderr)
        return 1
    finally:
        # Chromium ends once the pipe of its commands closes.
        chromium.commands.close()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
    return 0


if __name__ == "__main__":
    sys.exit(main())
