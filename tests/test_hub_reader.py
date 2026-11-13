"""Tests of .github/hub/reader.py and of the data classes of .github/hub/catalog.py:
how projects.toml is read and how its problems are named.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest

import hub.catalog
import hub.reader
from hub_helpers import (
    ROOT,
    SITE,
    catalog_data,
    drawing_data,
    drawn,
    entry,
    group_data,
    own_pictures,
    problems,
    without_card,
    without_repo,
)

# Reading projects.toml.


def test_a_valid_catalog_is_read_with_an_address_in_every_language() -> None:
    catalog = hub.reader.read(catalog_data(entry(docs="https://example.org/docs/")))

    project = catalog.projects[0]
    assert catalog.default == "en"
    assert project.repo == "Dennis-Otto/tool"
    assert project.start == hub.catalog.Link(
        "material-download",
        {"en": "Install", "de": "Installieren"},
        {"en": "https://example.org/install", "de": "https://example.org/install"},
    )
    assert project.docs == hub.catalog.Link(
        "material-book",
        {"en": "Documentation", "de": "Dokumentation"},
        {"en": "https://example.org/docs/", "de": "https://example.org/docs/"},
    )


def test_a_language_without_its_own_address_takes_that_of_the_first() -> None:
    data = catalog_data(entry(docs={"en": "https://example.org/docs/"}))

    project = hub.reader.read(data).projects[0]

    assert project.docs is not None
    assert project.docs.url == {
        "en": "https://example.org/docs/",
        "de": "https://example.org/docs/",
    }


def test_repo_and_docs_may_be_left_out() -> None:
    project = without_repo(entry())
    del project["docs"]

    read = hub.reader.read(catalog_data(project)).projects[0]

    assert read.repo is None
    assert read.license is None
    assert read.platform is None
    assert read.docs is None


def test_a_project_with_a_repo_names_its_license_and_its_platform() -> None:
    project = entry()
    del project["license"], project["platform"]

    assert problems(catalog_data(project)) == [
        "tool: license is missing.",
        "tool: platform is missing.",
    ]


def test_license_and_platform_are_for_a_project_with_a_repo() -> None:
    project = entry()
    del project["repo"]

    assert problems(catalog_data(project)) == [
        "tool: license is for a project with a repo.",
        "tool: platform is for a project with a repo.",
    ]


@pytest.mark.parametrize("spdx", ["MIT", "MIT-0", "AGPL-3.0-or-later", "Apache-2.0"])
def test_a_license_is_an_spdx_identifier(spdx: str) -> None:
    assert (
        hub.reader.read(catalog_data(entry(license=spdx))).projects[0].license == spdx
    )


@pytest.mark.parametrize("spdx", ["MIT License", "MIT OR Apache-2.0", "-MIT", "GPL/2"])
def test_a_license_that_is_no_spdx_identifier_is_named(spdx: str) -> None:
    assert problems(catalog_data(entry(license=spdx))) == [
        "tool: license must be the SPDX identifier of a license, such as MIT or "
        f"AGPL-3.0-or-later, not {spdx!r}."
    ]


def test_the_website_of_a_project_is_its_documentation_or_its_start() -> None:
    plain = entry("plain")
    del plain["docs"]

    tool, plain_project = hub.reader.read(catalog_data(entry(), plain)).projects

    assert tool.website == {
        "en": "https://dennis-otto.github.io/tool/",
        "de": "https://dennis-otto.github.io/tool/de/",
    }
    assert plain_project.website == {
        "en": "https://example.org/install",
        "de": "https://example.org/install",
    }


@pytest.mark.parametrize(
    "languages",
    [None, "en", [], ["en", 1], ["en", "Deutsch"], ["en", "de", "en"]],
)
def test_the_languages_must_be_a_list_of_distinct_codes(languages: Any) -> None:
    data = catalog_data()
    data["languages"] = languages

    with pytest.raises(
        hub.catalog.CatalogError, match="languages must list the language"
    ):
        hub.reader.read(data)


def test_a_missing_german_text_is_named_with_its_project() -> None:
    project = entry("homedarts-for-autodarts")
    del project["summary"]["de"]

    assert problems(catalog_data(project)) == [
        "homedarts-for-autodarts: summary.de is missing."
    ]


def test_every_problem_of_the_catalog_is_named_at_once() -> None:
    first = entry("one", icon="Material Tools", sumary="typo")
    first["name"] = "Only English"
    second = entry("two", repo="two", docs={"de": "http://example.org"})
    second["start"]["label"]["fr"] = "Installer"
    data = catalog_data(first, second)
    data["colors"] = "blue"

    assert problems(data) == [
        "colors is unknown; known are languages, documentation, facts, trust, "
        "requirements, group, project.",
        "one: sumary is unknown; known are slug, repo, license, platform, "
        "bestpractices, asset, requires, group, icon, name, short, tagline, summary, "
        "image, alt, drawing, start, docs, former, second.",
        "one: icon must be an icon of Material for MkDocs, such as material-download,"
        " not 'Material Tools'.",
        "one: name needs a text in every language: name.en, name.de.",
        "two: repo must be a repository on GitHub, such as "
        "Dennis-Otto/homedarts-for-autodarts, not 'two'.",
        "two: start.label.fr is in a language that languages doesn't list (en, de).",
        "two: docs.en is missing; the other languages take it when they have no "
        "address.",
        "two: docs.de must be an address with https:// and without spaces or "
        "parentheses, not 'http://example.org'.",
    ]


@pytest.mark.parametrize(
    ("value", "message"),
    [
        (7, "must be a text on one line"),
        ("  ", "must be a text on one line"),
        ("Two\nlines", "must be a text on one line"),
    ],
)
def test_a_text_must_be_a_text_on_one_line(value: object, message: str) -> None:
    project = entry()
    project["summary"]["en"] = value

    assert problems(catalog_data(project)) == [f"tool: summary.en {message}."]


def test_an_address_must_hold_no_spaces_or_parentheses() -> None:
    project = entry()
    project["start"]["url"] = "https://example.org/a (b)"

    assert problems(catalog_data(project)) == [
        "tool: start.url must be an address with https:// and without spaces or "
        "parentheses, not 'https://example.org/a (b)'."
    ]


def test_a_missing_or_wrong_table_is_named_once() -> None:
    first = entry("one")
    del first["start"]
    second = entry("two", start="https://example.org")
    data = catalog_data(first, second)
    del data["documentation"]

    assert problems(data) == [
        "documentation is missing.",
        "one: start is missing.",
        "two: start must be a table.",
    ]


def test_a_project_without_a_valid_slug_is_named_by_its_number() -> None:
    nameless = entry()
    del nameless["slug"]

    bad = entry(
        "Bad Slug",
        repo="Dennis-Otto/bad",
        docs="https://example.org/",
        image="images/bad.webp",
    )

    assert problems(catalog_data(entry(), "tool", nameless, bad)) == [
        "project 2 must be a table.",
        "project 3: slug is missing.",
        "project 4: slug must be lowercase letters, digits and hyphens, such as "
        "homedarts-for-autodarts, not 'Bad Slug'.",
    ]


@pytest.mark.parametrize("projects", [None, [], {"slug": "tool"}])
def test_the_catalog_must_list_projects(projects: object) -> None:
    data = catalog_data()
    data["project"] = projects

    assert problems(data) == [
        "project must list the projects as [[project]] tables.",
        "group tools has no project.",
    ]


@pytest.mark.parametrize("groups", [None, [], {"id": "tools"}])
def test_the_catalog_must_list_groups(groups: object) -> None:
    data = catalog_data()
    data["group"] = groups

    assert problems(data) == [
        "group must list the groups as [[group]] tables.",
        "tool: group must be the id of a group of the catalog (none), not 'tools'.",
    ]


def test_a_group_has_a_heading_and_may_have_a_note() -> None:
    note = {"en": "[Both](#tool) work together.", "de": "[Beide](#tool) zusammen."}
    data = catalog_data(entry(), entry("other", group="more"))
    data["group"].append(group_data("more", note=note))

    catalog = hub.reader.read(data)

    assert catalog.groups == (
        hub.catalog.Group("tools", {"en": "Tools", "de": "Werkzeuge"}, None),
        hub.catalog.Group("more", {"en": "Tools", "de": "Werkzeuge"}, note),
    )
    assert [[p.slug for p in catalog.members(group)] for group in catalog.groups] == [
        ["tool"],
        ["other"],
    ]


def test_a_project_may_name_the_folders_where_its_website_lived_before() -> None:
    catalog = hub.reader.read(
        catalog_data(entry(former=["old-tool", "older-tool"]), entry("two"))
    )
    moved, other = catalog.projects

    assert moved.former == ("old-tool", "older-tool")
    assert other.former == ()
    assert catalog.moves() == {
        "old-tool": f"{SITE}tool/",
        "older-tool": f"{SITE}tool/",
    }
    # read alone reads no file: load adds the pages of the former websites.
    assert catalog.former_pages == {}


def test_the_new_folder_is_that_of_the_website_in_the_default_language() -> None:
    docs = {"en": f"{SITE}new/guide.html", "de": f"{SITE}de/"}
    project = entry(former=["old"], docs=docs)

    assert hub.reader.read(catalog_data(project)).moves() == {"old": f"{SITE}new/"}


@pytest.mark.parametrize(
    ("former", "message"),
    [
        (
            "old",
            "must list the folders of the address where its website lived before, "
            'such as ["ha-autodarts"]',
        ),
        (
            [],
            "must list the folders of the address where its website lived before, "
            'such as ["ha-autodarts"]',
        ),
        (
            ["Old Tool"],
            "must be lowercase letters, digits and hyphens, such as "
            "homedarts-for-autodarts, not 'Old Tool'",
        ),
        ([7], "must be a text on one line"),
        (["old", "older", "old"], "names 'old' more than once"),
    ],
)
def test_former_lists_folders_of_the_address(former: object, message: str) -> None:
    assert problems(catalog_data(entry(former=former))) == [f"tool: former {message}."]


@pytest.mark.parametrize(
    "docs",
    [
        None,
        "https://elsewhere.example.org/tool/",
        hub.catalog.SITE,
        f"{hub.catalog.SITE}index.html",
    ],
)
def test_former_needs_a_website_in_a_folder_of_the_address(docs: str | None) -> None:
    project = entry(former=["old"], docs=docs)
    if docs is None:
        del project["docs"]

    assert problems(catalog_data(project)) == [
        f"tool: former is for a project whose docs are a website in a folder of {SITE},"
        " where the old addresses lead."
    ]


def test_former_names_no_folder_or_anchor_that_is_in_use() -> None:
    data = catalog_data(
        entry(former=["de", "tools", "two", "docs-of-two", "elsewhere", "shared"]),
        entry("two", docs=f"{SITE}docs-of-two/guide.html", former=["shared"]),
        # Its website is elsewhere, so it takes no folder of the address.
        entry("three", docs="https://elsewhere.example.org/elsewhere/"),
    )
    in_use = (
        "which the address or the home page uses already: as a language, the folder "
        "of a website, a slug or the id of a group."
    )

    assert problems(data) == [
        f"tool: former names 'de', {in_use}",
        f"tool: former names 'tools', {in_use}",
        f"tool: former names 'two', {in_use}",
        f"tool: former names 'docs-of-two', {in_use}",
        "tool: former names 'shared', which another project names too.",
        "two: former names 'shared', which another project names too.",
    ]


def test_the_pages_of_a_former_website_are_read_from_its_list(tmp_path: Path) -> None:
    catalog = hub.reader.read(catalog_data(entry(former=["old-tool", "older-tool"])))
    (tmp_path / "former").mkdir()
    (tmp_path / "former" / "old-tool.txt").write_text(
        "# The pages of the old website.\n\nindex.html\n  de/games.html  \n"
        "decisions/0001-a_b.c.html\nindex.html\n",
        encoding="utf-8",
    )
    (tmp_path / "former" / "older-tool.txt").write_text(
        "guide.html\n", encoding="utf-8"
    )

    assert hub.reader.former_pages(catalog, tmp_path) == {
        "old-tool": ("index.html", "de/games.html", "decisions/0001-a_b.c.html"),
        "older-tool": ("guide.html",),
    }


def test_every_problem_of_the_lists_of_the_former_websites_is_named(
    tmp_path: Path,
) -> None:
    catalog = hub.reader.read(
        catalog_data(entry(former=["broken", "empty", "missing"]))
    )
    (tmp_path / "former").mkdir()
    (tmp_path / "former" / "broken.txt").write_text(
        "games.html\n/index.html\n../up.html\n.hidden/page.html\npicture.png\n"
        "a page.html\nde/\n",
        encoding="utf-8",
    )
    (tmp_path / "former" / "empty.txt").write_text("# Nothing yet.\n", encoding="utf-8")

    with pytest.raises(hub.catalog.CatalogError) as error:
        hub.reader.former_pages(catalog, tmp_path)

    lines = str(error.value).splitlines()
    page = (
        "must be the path of a page from the folder of the website, such as "
        "games.html or de/index.html"
    )
    assert lines[0] == "The pages of the former websites have 8 problem(s):"
    assert lines[1:7] == [
        f"  former/broken.txt:{number} {page}, not {line!r}."
        for number, line in [
            (2, "/index.html"),
            (3, "../up.html"),
            (4, ".hidden/page.html"),
            (5, "picture.png"),
            (6, "a page.html"),
            (7, "de/"),
        ]
    ]
    assert lines[7] == "  former/empty.txt lists no page of the former website."
    assert lines[8].startswith(
        "  former/missing.txt, the pages of the former website of tool, can't be read: "
    )
    assert lines[9] == "The comments at the top of projects.toml describe former."


def test_the_catalog_needs_the_lists_of_its_former_websites(tmp_path: Path) -> None:
    shutil.copyfile(ROOT / "projects.toml", tmp_path / "projects.toml")

    with pytest.raises(
        hub.catalog.CatalogError, match=r"former/ha-autodarts\.txt, the"
    ):
        hub.reader.load(tmp_path)


def test_a_project_may_have_a_short_name_in_every_language() -> None:
    short = {"en": "Tool", "de": "Werkzeug"}
    catalog = hub.reader.read(catalog_data(entry(short=short), entry("plain")))

    assert [project.short for project in catalog.projects] == [short, None]


@pytest.mark.parametrize(
    ("short", "problem"),
    [
        ({"en": "Tool"}, "tool: short.de is missing."),
        ("Tool", "tool: short needs a text in every language: short.en, short.de."),
    ],
)
def test_a_short_name_needs_every_language(short: object, problem: str) -> None:
    assert problems(catalog_data(entry(short=short))) == [problem]


def test_every_problem_of_a_group_is_named() -> None:
    data = catalog_data(entry(), entry("other", group="Bad Id"))
    nameless = group_data(heading={"en": "Only English"}, colour="red")
    del nameless["id"]
    data["group"] += [
        nameless,
        "more",
        group_data("Bad Id"),
        group_data("tools", note="One language"),
        group_data("empty"),
    ]

    assert problems(data) == [
        "group 2: colour is unknown; known are id, heading, note.",
        "group 2: id is missing.",
        "group 2: heading.de is missing.",
        "group 3 must be a table.",
        "group 4: id must be lowercase letters, digits and hyphens, such as "
        "homedarts-for-autodarts, not 'Bad Id'.",
        "group tools: note needs a text in every language: note.en, note.de.",
        "other: group must be lowercase letters, digits and hyphens, such as "
        "homedarts-for-autodarts, not 'Bad Id'.",
        "group tools: id names more than one group.",
        "group empty has no project.",
    ]


def test_a_project_names_a_group_of_the_catalog() -> None:
    assert problems(catalog_data(entry(), entry("other", group="toys"))) == [
        "other: group must be the id of a group of the catalog (tools), not 'toys'.",
    ]


def test_a_card_needs_a_picture_with_a_text_for_those_who_cant_see_it() -> None:
    project = entry()
    del project["image"], project["alt"]

    assert problems(catalog_data(project)) == [
        "tool: image is missing.",
        "tool: alt needs a text in every language: alt.en, alt.de.",
    ]


@pytest.mark.parametrize(
    "image", ["images/tool.webp", "tool.png", "a/b-c/d_e.svg", "x.jpg", "x.avif"]
)
def test_a_picture_is_a_file_in_docs(image: str) -> None:
    # One made by hand, for a project without a repo, can be of any of these kinds.
    project = without_repo(entry(image=image))
    picture = hub.reader.read(catalog_data(project)).projects[0].picture

    assert picture == hub.catalog.Picture(
        {"en": image, "de": image},
        {"en": "The tool at work", "de": "Das Werkzeug bei der Arbeit"},
    )


@pytest.mark.parametrize(
    "image",
    [
        "/images/tool.webp",
        "../tool.webp",
        "images/tool.gif",
        "a b.png",
        # mkdocs-static-i18n would publish it as the German images/tool.webp.
        "images/tool.de.webp",
    ],
)
def test_a_picture_outside_docs_or_of_another_kind_is_named(image: str) -> None:
    assert problems(catalog_data(entry(image=image))) == [
        "tool: image must be a picture in docs/, such as "
        f"images/projects/homedarts-for-autodarts.webp, not {image!r}."
    ]


@pytest.mark.parametrize("image", ["tool.png", "a/b-c/d_e.svg", "x.jpg", "x.avif"])
def test_the_picture_of_a_project_with_a_repo_is_a_webp(image: str) -> None:
    # scripts/project-pictures.sh writes a WebP, whatever the name of the file says.
    assert problems(catalog_data(entry(image=image))) == [
        "tool: image must be a WebP for a project with a repo, which "
        f"scripts/project-pictures.sh makes, not {image!r}."
    ]


def test_a_picture_may_have_a_file_in_each_language() -> None:
    picture = hub.reader.read(catalog_data(drawn())).projects[0].picture

    assert picture == hub.catalog.Picture(
        own_pictures(),
        {"en": "The tool at work", "de": "Das Werkzeug bei der Arbeit"},
        hub.catalog.Drawing(
            {"de": "docs/images/de/shot.png"}, "docs/logo.svg", "#14b8a6"
        ),
    )


def test_a_language_without_a_picture_of_its_own_takes_that_of_the_first() -> None:
    project = entry(image={"en": "images/projects/tool.webp"})
    picture = hub.reader.read(catalog_data(project)).projects[0].picture

    assert picture is not None
    assert picture.src == dict.fromkeys(("en", "de"), "images/projects/tool.webp")
    # The social preview makes it in every language, so the hub draws none.
    assert picture.drawing is None


def test_the_picture_of_the_first_language_is_needed() -> None:
    project = without_repo(entry(image={"de": "images/de/tool.png"}))

    assert problems(catalog_data(project)) == [
        "tool: image.en is missing; the other languages take it when they have no "
        "picture."
    ]


def test_every_picture_of_a_project_with_a_repo_is_a_webp() -> None:
    project = drawn(image={"en": "images/tool.png", "de": "images/de/tool.png"})

    assert problems(catalog_data(project)) == [
        f"tool: image.{language} must be a WebP for a project with a repo, which "
        f"scripts/project-pictures.sh makes, not {image!r}."
        for language, image in (("en", "images/tool.png"), ("de", "images/de/tool.png"))
    ]


def test_the_hub_draws_the_picture_of_its_own_in_a_further_language() -> None:
    # The social preview of the repository speaks the first language alone.
    project = drawn()
    del project["drawing"]

    assert problems(catalog_data(project)) == [
        "tool: drawing is missing, with which the hub draws image.de."
    ]


def test_a_drawing_is_for_a_picture_of_its_own_of_a_project_with_a_repo() -> None:
    # A picture of a project without a repo is made by hand, in every language.
    board = without_repo(drawn("board"))

    assert problems(catalog_data(entry(drawing=drawing_data()), board)) == [
        "tool: drawing is for a project with a repo whose image has a file of its "
        "own in a language after the first, such as image.de.",
        "board: drawing is for a project with a repo.",
    ]


@pytest.mark.parametrize(
    ("drawing", "problem"),
    [
        ("docs/images/de/shot.png", "drawing must be a table."),
        (
            drawing_data(size=2),
            "drawing.size is unknown; known are screenshot, logo, accent, hangs.",
        ),
        ({"accent": "#14b8a6"}, "drawing.screenshot is missing."),
        (
            drawing_data(screenshot=".github/shot.png"),
            "drawing.screenshot must be the path of a JPEG, PNG, SVG or WebP of the "
            "repository, such as docs/images/de/card.png, not '.github/shot.png'.",
        ),
        (
            # Chromium would catch an animation at any frame.
            drawing_data(screenshot="docs/images/de/demo.gif"),
            "drawing.screenshot must be the path of a JPEG, PNG, SVG or WebP of the "
            "repository, such as docs/images/de/card.png, not "
            "'docs/images/de/demo.gif'.",
        ),
        (
            drawing_data(logo="../logo.svg"),
            "drawing.logo must be the path of a JPEG, PNG, SVG or WebP of the "
            "repository, such as docs/branding/icon.svg, not '../logo.svg'.",
        ),
        (
            drawing_data(accent="#14B8A6"),
            "drawing.accent must be a color of six lowercase hexadecimal digits, "
            "such as #14b8a6, not '#14B8A6'.",
        ),
        (
            {"screenshot": "docs/images/de/shot.png"},
            "drawing.accent is missing.",
        ),
        (
            drawing_data(hangs="yes"),
            "drawing.hangs must be true or false, not 'yes'.",
        ),
    ],
)
def test_a_drawing_names_each_of_its_problems(drawing: object, problem: str) -> None:
    assert problems(catalog_data(drawn(drawing=drawing))) == [f"tool: {problem}"]


def test_a_drawing_may_have_a_screenshot_in_each_language_that_it_draws() -> None:
    project = drawn(drawing=drawing_data(screenshot={"de": "docs/de/shot.webp"}))
    picture = hub.reader.read(catalog_data(project)).projects[0].picture

    assert picture is not None
    assert picture.drawing == hub.catalog.Drawing(
        {"de": "docs/de/shot.webp"}, "docs/logo.svg", "#14b8a6"
    )


def test_a_drawing_frames_its_screenshot_unless_it_hangs() -> None:
    # A screenshot cut at its foot already, such as a popup below the toolbar of a
    # browser, hangs from the top of the picture and runs off its bottom edge.
    pictures = [
        hub.reader.read(catalog_data(drawn(drawing=drawing))).projects[0].picture
        for drawing in (drawing_data(), drawing_data(hangs=True))
    ]

    assert [
        picture.drawing.hangs
        for picture in pictures
        if picture is not None and picture.drawing is not None
    ] == [False, True]


def test_a_drawing_has_a_screenshot_for_each_language_that_it_draws_alone() -> None:
    screenshot = {"en": "docs/en/shot.png", "fr": "docs/fr/shot.png"}
    project = drawn(drawing=drawing_data(screenshot=screenshot))

    assert problems(catalog_data(project)) == [
        "tool: drawing.screenshot.fr is in a language that languages doesn't list "
        "(en, de).",
        "tool: drawing.screenshot.en is for a language whose picture the hub doesn't "
        "draw; it draws only those of de.",
        "tool: drawing.screenshot.de is missing.",
    ]


def test_picture_and_second_are_for_a_project_with_a_group() -> None:
    project = entry()
    del project["group"]
    project["second"] = "tool"

    assert problems(catalog_data(project, entry("other"))) == [
        "tool: image is for a project with a group.",
        "tool: alt is for a project with a group.",
        "tool: second is for a project with a group.",
        "tool is on no card of the home page: give it a group, or name it as the "
        "second of a project with one.",
    ]


def test_a_project_without_a_card_is_the_second_button_of_another() -> None:
    board = without_card(without_repo(entry("board")))
    catalog = hub.reader.read(catalog_data(entry(second="board"), board))

    tool, board_project = catalog.projects

    assert tool.second == "board"
    assert board_project.group is None
    assert board_project.picture is None
    assert catalog.second(tool) == board_project.start
    assert catalog.second(board_project) == board_project.docs


@pytest.mark.parametrize(
    ("second", "message"),
    [
        ("tool", "second names no other project of the catalog, not 'tool'"),
        ("toy", "second names no other project of the catalog, not 'toy'"),
        (
            "A Toy",
            "second must be lowercase letters, digits and hyphens, such as "
            "homedarts-for-autodarts, not 'A Toy'",
        ),
    ],
)
def test_the_second_of_a_card_is_another_project(second: str, message: str) -> None:
    assert problems(catalog_data(entry(second=second))) == [f"tool: {message}."]


def test_every_project_is_on_a_card_of_the_home_page() -> None:
    # The dashboard of this catalog without the card of the blueprint.
    board = without_card(without_repo(entry("board")))

    assert problems(catalog_data(entry(), board)) == [
        "board is on no card of the home page: give it a group, or name it as the "
        "second of a project with one.",
    ]


def test_two_projects_may_not_share_a_slug() -> None:
    data = catalog_data(entry("tool"), entry("tool"), entry("other"))

    assert problems(data) == ["tool: slug names more than one project."]


def test_a_missing_catalog_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(hub.catalog.CatalogError, match=r"projects\.toml can't be read"):
        hub.reader.load(tmp_path)


def test_a_catalog_that_is_no_toml_is_an_error(tmp_path: Path) -> None:
    (tmp_path / "projects.toml").write_text("languages = [", encoding="utf-8")

    with pytest.raises(
        hub.catalog.CatalogError, match=r"projects\.toml isn't valid TOML"
    ):
        hub.reader.load(tmp_path)


# The live facts.


def test_a_project_may_name_its_project_at_bestpractices_dev() -> None:
    catalog = hub.reader.read(catalog_data(entry(bestpractices=14935)))

    assert catalog.projects[0].bestpractices == 14935
    assert hub.reader.read(catalog_data()).projects[0].bestpractices is None


@pytest.mark.parametrize("number", [0, -1, "14935", True, 1.5, None])
def test_the_project_at_bestpractices_dev_is_a_number(number: object) -> None:
    assert problems(catalog_data(entry(bestpractices=number))) == [
        "tool: bestpractices must be the number of the project at bestpractices.dev, "
        f"as in the address of its badge, such as 14935, not {number!r}."
    ]


def test_bestpractices_is_for_a_project_with_a_repo() -> None:
    project = without_repo(entry(bestpractices=14935))

    assert problems(catalog_data(project)) == [
        "tool: bestpractices is for a project with a repo."
    ]


def test_the_catalog_needs_the_texts_of_the_facts() -> None:
    data = catalog_data()
    del data["facts"]

    assert problems(data) == ["facts is missing."]


def test_every_problem_of_the_facts_is_named() -> None:
    data = catalog_data()
    facts = data["facts"]
    facts["colour"] = "blue"
    del facts["passing"]
    facts["released"]["de"] = "erschienen"
    facts["coverage"]["en"] = "{} of {}"
    facts["answer"] = "in {}"
    # The name of the list holds no value.
    facts["label"] = {"en": "Facts {}", "de": "Fakten {}"}

    assert problems(data) == [
        "facts.colour is unknown; known are label, released, coverage, mutation, "
        "scorecard, answer, bestpractices, passing, silver, gold, projects, github, "
        "releases, maintenance.",
        "facts.answer needs a text in every language: facts.answer.en, "
        "facts.answer.de.",
        "facts.passing needs a text in every language: facts.passing.en, "
        "facts.passing.de.",
        "facts.released.de must hold {} once, where the script writes the value, not "
        "'erschienen'.",
        "facts.coverage.en must hold {} once, where the script writes the value, not "
        "'{} of {}'.",
    ]


def test_the_facts_must_be_a_table() -> None:
    data = catalog_data()
    data["facts"] = ["released {}"]

    assert problems(data) == ["facts must be a table."]


# The Trust page.


def test_a_project_with_a_repo_may_name_the_file_that_its_users_install() -> None:
    catalog = hub.reader.read(catalog_data(entry(asset="homedarts.zip"), entry("two")))
    first, second = catalog.projects

    assert first.asset == "homedarts.zip"
    assert first.download == "homedarts.zip"
    assert first.verified == "homedarts.zip"
    # Without one, the commands take the SBOM that every release carries.
    assert second.asset is None
    assert second.verified == "two.spdx.json"


@pytest.mark.parametrize(
    ("asset", "verified"),
    [
        ("tool-*.zip", "tool.zip"),
        ("tool_*.tar.gz", "tool.tar.gz"),
        ("tool.*.json", "tool.json"),
        ("tool-*-linux.zip", "tool-linux.zip"),
        ("tool*", "tool"),
    ],
)
def test_an_asset_with_the_version_in_its_name_is_a_pattern(
    asset: str, verified: str
) -> None:
    (project,) = hub.reader.read(catalog_data(entry(asset=asset))).projects

    # The commands download the file that the pattern matches, and save it under
    # the name that they verify.
    assert project.download == asset
    assert project.verified == verified


@pytest.mark.parametrize(
    "asset",
    [
        "a b.zip",
        "../tool.zip",
        "*.zip",
        "-tool.zip",
        "x;y",
        "tool-*-*.zip",
        "tool-**.zip",
        "tool-?.zip",
        "tool-[0-9].zip",
    ],
)
def test_an_asset_is_the_name_of_a_file_or_its_pattern(asset: str) -> None:
    assert problems(catalog_data(entry(asset=asset))) == [
        "tool: asset must be the name of a file of its releases, such as "
        "homedarts.zip, or its pattern with a * for the version, such as "
        f"tool-*.zip, not {asset!r}."
    ]


def test_asset_is_for_a_project_with_a_repo() -> None:
    project = without_repo(entry(asset="tool.zip"))

    assert problems(catalog_data(project)) == [
        "tool: asset is for a project with a repo."
    ]


def test_the_catalog_needs_the_texts_of_the_trust_page() -> None:
    data = catalog_data()
    del data["trust"]

    assert problems(data) == ["trust is missing."]


def test_the_texts_of_the_trust_page_must_be_a_table() -> None:
    data = catalog_data()
    data["trust"] = ["Guarantee"]

    assert problems(data) == ["trust must be a table."]


def test_every_problem_of_the_texts_of_the_trust_page_is_named() -> None:
    data = catalog_data()
    trust = data["trust"]
    trust["colour"] = "blue"
    del trust["numbers"]
    trust["release"] = {"en": "Latest release"}
    trust["tag"] = "gitsign"
    trust["sbom"]["kind"] = "SPDX"
    del trust["vex"]["value"]
    del trust["policy"]
    trust["report"]["value"]["de"] = "vertraulich"

    assert problems(data) == [
        "trust.colour is unknown; known are tag, provenance, immutable, sbom, vex, "
        "policy, report, numbers, project, release, coverage, mutation, scorecard, "
        "bestpractices, note.",
        "trust.tag must be a table.",
        "trust.sbom.kind is unknown; known are label, value.",
        "trust.vex.value needs a text in every language: trust.vex.value.en, "
        "trust.vex.value.de.",
        "trust.policy is missing.",
        "trust.report.value.de must hold {} once, where the links to every project "
        "go, not 'vertraulich'.",
        "trust.numbers needs a text in every language: trust.numbers.en, "
        "trust.numbers.de.",
        "trust.release.de is missing.",
    ]
