"""The hooks of this website, beside those that every website shares in
.github/mkdocs_blueprint.py, and its script; mkdocs.yml names both files.

This file is what MkDocs loads and what the scripts and the workflows run, with nothing
but the standard library. The code is in the package .github/hub/ beside it, a module
for each concern; hub/__init__.py lists them. Run as a script, this file writes the
table of the projects in README.md and in the German README.de.md, or checks that both
tables are current, as scripts/check-project.sh does; it lists the pictures of the cards
that scripts/project-pictures.sh makes from the social preview of each repository, in
the first language, and writes the pages from which it draws those of the other
languages that have a picture of their own, with the icon of a card from Material for
MkDocs when it needs one:

    python3 -I .github/mkdocs_project.py --write
    python3 -I .github/mkdocs_project.py --check
    python3 -I .github/mkdocs_project.py --pictures
    python3 -I .github/mkdocs_project.py --drawings .cache/pictures

Every week the catalog bot, .github/workflows/catalog.yml, compares the catalog with
GitHub and the websites of the projects, makes the edits with one correct form with
--fix, and every day it watches what the published website depends on after its build:

    python3 -I .github/mkdocs_project.py --network repositories.json
    python3 -I .github/mkdocs_project.py --network repositories.json --fix pull-request.md
    python3 -I .github/mkdocs_project.py --watch

After the real build, the check docs runs scripts/check-site.sh with the folder of the
website, which checks there what the hooks promise:

    python3 -I .github/mkdocs_project.py --site site
"""

from __future__ import annotations

import argparse
import difflib
import io
import sys
from pathlib import Path

# The code of the hooks is in the package hub beside this file. python3 -I leaves the
# folder of a script off sys.path, and MkDocs takes it off again after it loaded a hook.
# The bots commit what a fix changes, so nothing that runs this file may leave a
# __pycache__ in the repository.
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.dont_write_bytecode = True

# Every on_* of hub/events.py stands here for MkDocs, which looks for them in this file.
from hub.bot import FIELDS
from hub.catalog import CATALOG, DIFFERS, ROOT, SITE, CatalogError
from hub.events import (
    on_config,
    on_files,
    on_page_content,
    on_page_context,
    on_page_markdown,
    on_post_build,
    on_post_page,
    on_pre_page,
    on_serve,
)
from hub.fix import network
from hub.pictures import DRAWING, DrawingError, drawings, pictures, theme_icons
from hub.reader import load
from hub.render import README, WRITE, readme, readmes
from hub.sitecheck import site_check
from hub.watch import DASHBOARD_FIELDS, watch

# The hooks that MkDocs takes from this file; nothing here calls them.
__all__ = [
    "on_config",
    "on_files",
    "on_page_content",
    "on_page_context",
    "on_page_markdown",
    "on_post_build",
    "on_post_page",
    "on_pre_page",
    "on_serve",
]


def main(argv: list[str] | None = None, root: Path = ROOT) -> int:
    """Write or check the table of the projects in every README, list the pictures of
    the cards, write the pages of those that the hub draws, compare the catalog with
    GitHub and the websites of the projects for the catalog bot, watch the live
    websites, or check the built website."""
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            # The console of Windows may lack a character of the README.
            stream.reconfigure(errors="backslashreplace")
    parser = argparse.ArgumentParser(
        description="Write or check the table of the projects in every README, "
        f"from {CATALOG}, list the pictures of the cards, write the pages of "
        f"those that the hub draws, compare {CATALOG} "
        "with GitHub and the websites of the projects, watch the live websites, or "
        "check the built website."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--write",
        action="store_true",
        help=f"write the table into {README} and the README of every other language",
    )
    mode.add_argument(
        "--check",
        action="store_true",
        help=f"check {CATALOG}, and that every README has its table",
    )
    mode.add_argument(
        "--pictures",
        action="store_true",
        help="list the repository, the picture and the license of every card "
        "whose picture comes from a repository, for scripts/project-pictures.sh",
    )
    mode.add_argument(
        "--drawings",
        metavar="FOLDER",
        type=Path,
        help=f"write the page of {DRAWING} for every picture of a card that the "
        "hub draws into FOLDER, and list the repository, the picture, the license, "
        "the page, and the address and the file of its screenshot and of its logo "
        "of each, for scripts/project-pictures.sh",
    )
    mode.add_argument(
        "--network",
        metavar="REPOSITORIES",
        type=Path,
        help=f"compare {CATALOG} with the repositories of the file REPOSITORIES, "
        f"which gh repo list --json {','.join(FIELDS)} writes, with the websites "
        "of the projects in every language and with the files that say what they "
        "work with, and print what differs as "
        "the issue of the catalog bot: exit 0 when nothing differs, "
        f"{DIFFERS} when something does, and 2 when it can't tell",
    )
    mode.add_argument(
        "--watch",
        action="store_true",
        help=f"ask the live websites at {SITE} for what this website depends on "
        "after its build: the data of the dashboard, against "
        f"{DASHBOARD_FIELDS}, the search index of every project website, "
        "security.txt, robots.txt, the sitemap and the old addresses, and print "
        "what needs attention as the issue of the catalog bot: exit 0 when nothing "
        f"does, {DIFFERS} when something does, and 2 when it can't tell",
    )
    mode.add_argument(
        "--site",
        metavar="SITE",
        type=Path,
        help="check the website that MkDocs built in the folder SITE, such as site, "
        "for what the hooks promise in the files that they alone write: "
        "security.txt, robots.txt, llms.txt, the sitemaps, the old addresses, the 404 "
        "page, the home pages and the search; exit 1 with a line for each broken "
        "promise",
    )
    parser.add_argument(
        "--fix",
        metavar="PULL_REQUEST",
        type=Path,
        help=f"with --network: make the edits with one correct form in {CATALOG}, the "
        "tables of the READMEs, the data of the tests of the 404 script and the links of "
        "the pages of the website, and write "
        "the text of their pull request into the file PULL_REQUEST; without such an "
        "edit, nothing is written",
    )
    arguments = parser.parse_args(argv)
    if arguments.fix is not None and arguments.network is None:
        parser.error("--fix goes with --network")
    if arguments.network is not None:
        return network(arguments.network, root, arguments.fix)
    if arguments.watch:
        return watch(root)
    if arguments.site is not None:
        return site_check(arguments.site, root)
    try:
        catalog = load(root)
        if arguments.pictures:
            sys.stdout.write(pictures(catalog))
            return 0
        if arguments.drawings is not None:
            template = (root / DRAWING).read_text(encoding="utf-8")
            listed = drawings(catalog, arguments.drawings, template, theme_icons())
            sys.stdout.write(listed)
            return 0
        # Every README is read and its table made before one is written, so that
        # a README without its markers leaves the others as they are.
        texts = {}
        for language, name in readmes(catalog).items():
            current = (root / name).read_text(encoding="utf-8")
            texts[name] = (current, readme(current, catalog, language))
    except (CatalogError, DrawingError, OSError) as error:
        print(error, file=sys.stderr)
        return 1
    differs = False
    for name, (current, wanted) in texts.items():
        if wanted == current:
            print(f"{name} has the current table of the projects of {CATALOG}.")
        elif arguments.write:
            (root / name).write_text(wanted, encoding="utf-8", newline="\n")
            print(f"{name} has the table of the projects of {CATALOG} now.")
        else:
            sys.stdout.writelines(
                difflib.unified_diff(
                    current.splitlines(keepends=True),
                    wanted.splitlines(keepends=True),
                    name,
                    f"{name}, from {CATALOG}",
                )
            )
            print(
                f"{name} differs from {CATALOG}; write its table with\n  {WRITE}",
                file=sys.stderr,
            )
            differs = True
    return 1 if differs else 0


if __name__ == "__main__":
    sys.exit(main())
