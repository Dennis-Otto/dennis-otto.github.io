"""Tests of .github/hub/pictures.py: the pictures of the cards and the pages from which
the hub draws them.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import hub.pictures
import hub.reader
from hub_helpers import (
    ROOT,
    catalog_data,
    drawing_data,
    drawn,
    entry,
    hooks,
    repository,
    without_repo,
    write,
)

# A page of the drawn pictures with every placeholder of DRAWING.
TEMPLATE = "${lang}|${name}|${tagline}|${accent}|${logo}|${screenshot}|${place}"


def test_the_hub_writes_the_page_of_every_picture_that_it_draws(
    tmp_path: Path,
) -> None:
    # The tagline without the name, which the picture shows above it.
    tagline = {"en": "The tool: a tool", "de": "Das Werkzeug: Ein <Werkzeug> & mehr"}
    plain = entry("plain")
    board = without_repo(entry("board", image={"en": "b.png", "de": "de/b.png"}))
    catalog = hub.reader.read(catalog_data(drawn(tagline=tagline), plain, board))
    folder = tmp_path / "pages"

    listed = hub.pictures.drawings(catalog, folder, TEMPLATE, None)

    assert listed == (
        "Dennis-Otto/tool docs/images/projects/de/tool.webp MIT "
        f"{folder.as_posix()}/tool.de.html "
        "https://raw.githubusercontent.com/Dennis-Otto/tool/HEAD/docs/images/de/shot.png "
        f"{folder.as_posix()}/tool.de.screenshot.png "
        "https://raw.githubusercontent.com/Dennis-Otto/tool/HEAD/docs/logo.svg "
        f"{folder.as_posix()}/tool.logo.svg\n"
    )
    assert (folder / "tool.de.html").read_text(encoding="utf-8") == (
        "de|Das Werkzeug|Ein &lt;Werkzeug&gt; &amp; mehr|#14b8a6|"
        '<img class="logo" src="tool.logo.svg" alt="">|tool.de.screenshot.png|framed'
    )
    assert sorted(path.name for path in folder.iterdir()) == ["tool.de.html"]


def test_a_drawn_picture_hangs_a_screenshot_that_is_cut_at_its_foot(
    tmp_path: Path,
) -> None:
    # Such as a popup below the toolbar of a browser: from the top of the picture to
    # its bottom edge, larger than inside the margins of a frame.
    catalog = hub.reader.read(catalog_data(drawn(drawing=drawing_data(hangs=True))))

    hub.pictures.drawings(catalog, tmp_path, "${place}", None)

    assert (tmp_path / "tool.de.html").read_text(encoding="utf-8") == "hanging"


def test_a_drawn_picture_without_a_logo_shows_the_icon_of_its_card(
    tmp_path: Path,
) -> None:
    write(tmp_path / "icons/material/tools.svg", "<svg>tools</svg>\n")
    drawing = drawing_data()
    del drawing["logo"]
    catalog = hub.reader.read(catalog_data(drawn(drawing=drawing)))

    listed = hub.pictures.drawings(
        catalog, tmp_path / "pages", "${logo}", tmp_path / "icons"
    )

    assert listed.split()[-2:] == ["-", "-"]
    assert (tmp_path / "pages/tool.de.html").read_text(encoding="utf-8") == (
        '<div class="logo icon"><svg>tools</svg></div>'
    )


def test_an_icon_of_a_set_with_styles_is_in_their_folders(tmp_path: Path) -> None:
    write(tmp_path / "fontawesome/brands/github.svg", "<svg>github</svg>")

    assert (
        hub.pictures.icon_svg("fontawesome-brands-github", tmp_path)
        == "<svg>github</svg>"
    )


def test_an_icon_that_the_theme_lacks_is_named(tmp_path: Path) -> None:
    with pytest.raises(hub.pictures.DrawingError) as error:
        hub.pictures.icon_svg("material-nothing-here", tmp_path)

    assert str(error.value) == (
        f"Material for MkDocs has no icon material-nothing-here in {tmp_path}."
    )


def test_the_icons_come_from_the_theme_that_the_tools_of_the_website_install(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    theme = SimpleNamespace(__file__=str(tmp_path / "material" / "__init__.py"))
    monkeypatch.setitem(sys.modules, "material", theme)

    assert hub.pictures.theme_icons() == tmp_path / "material" / "templates" / ".icons"


def test_without_the_tools_of_the_website_there_are_no_icons(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(sys.modules, "material", None)

    assert hub.pictures.theme_icons() is None
    with pytest.raises(hub.pictures.DrawingError) as error:
        hub.pictures.icon_svg("material-tools", None)
    assert str(error.value) == (
        "Drawing the icon material-tools needs Material for MkDocs: set up the tools "
        "of the website in .venv-docs, as CONTRIBUTING.md describes."
    )


def test_the_script_writes_the_pages_of_the_pictures_that_the_hub_draws(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    repository(tmp_path).unlink()
    write(
        tmp_path / hub.pictures.DRAWING,
        (ROOT / hub.pictures.DRAWING).read_text(encoding="utf-8"),
    )
    write(tmp_path / "icons/material/bell-ring.svg", '<svg id="bell"/>')
    write(tmp_path / "icons/material/file-tree.svg", "<svg/>")
    monkeypatch.setattr(hooks, "theme_icons", lambda: tmp_path / "icons")
    monkeypatch.chdir(tmp_path)

    assert hooks.main(["--drawings", "pages"], tmp_path) == 0

    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 7
    assert [line.split()[:4] for line in lines[-2:]] == [
        [
            "Dennis-Otto/repo-pager",
            "docs/images/projects/de/repo-pager.webp",
            "MIT",
            "pages/repo-pager.de.html",
        ],
        [
            "Dennis-Otto/repo-blueprint",
            "docs/images/projects/de/repo-blueprint.webp",
            "MIT-0",
            "pages/repo-blueprint.de.html",
        ],
    ]
    page = (tmp_path / "pages/repo-blueprint.de.html").read_text(encoding="utf-8")
    assert '<div class="logo icon"><svg/></div>' in page
    # A diagram of the project is a still picture too, which the page shows as it is.
    pager = (tmp_path / "pages/repo-pager.de.html").read_text(encoding="utf-8")
    assert '<div class="logo icon"><svg id="bell"/></div>' in pager
    assert '<img src="repo-pager.de.screenshot.svg" alt="">' in pager


def test_a_picture_that_the_hub_cannot_draw_stops_the_script(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    repository(tmp_path).unlink()
    write(tmp_path / hub.pictures.DRAWING, TEMPLATE)
    monkeypatch.setattr(hooks, "theme_icons", lambda: None)
    monkeypatch.chdir(tmp_path)

    assert hooks.main(["--drawings", "pages"], tmp_path) == 1

    assert capsys.readouterr() == (
        "",
        "Drawing the icon material-bell-ring needs Material for MkDocs: set up the "
        "tools of the website in .venv-docs, as CONTRIBUTING.md describes.\n",
    )


def test_a_card_without_a_repository_has_no_picture_to_make() -> None:
    board = without_repo(entry("board"))

    assert hub.pictures.pictures(hub.reader.read(catalog_data(entry(), board))) == (
        "Dennis-Otto/tool docs/images/projects/tool.webp MIT\n"
    )


def test_the_script_writes_what_a_console_cannot_show_as_escapes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository(tmp_path)
    console = io.TextIOWrapper(io.BytesIO(), encoding="ascii")
    monkeypatch.setattr(sys, "stdout", console)
    monkeypatch.setattr(sys, "stderr", io.StringIO())

    assert hooks.main(["--check"], tmp_path) == 0
    assert console.errors == "backslashreplace"
