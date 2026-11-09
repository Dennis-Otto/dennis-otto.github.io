"""The pictures of the cards: the list of those that
scripts/project-pictures.sh makes from the social preview of each repository, in the
first language, and the pages from which it draws those of the other languages that
have a picture of their own, with the icon of a card from Material for MkDocs when it
needs one.
"""

from __future__ import annotations

from html import escape
from pathlib import Path, PurePosixPath
from string import Template

from . import web
from .catalog import Catalog

# The page from which scripts/project-pictures.sh draws the picture of a card in a
# language after the first, beside a screenshot of the repository of its project in
# that language, where the social preview of the repository makes that of the first.
DRAWING = ".github/card-picture.html"


def pictures(catalog: Catalog) -> str:
    """The pictures of the cards that come from the social preview of a repository,
    those of the first language, one per line for scripts/project-pictures.sh: the
    repository, the file in the repository that the picture goes to, and the
    license of the repository, which is that of the picture too."""
    return "".join(
        f"{project.repo} docs/{project.picture.src[catalog.default]} "
        f"{project.license}\n"
        for project in catalog.projects
        if project.repo is not None and project.picture is not None
    )


class DrawingError(Exception):
    """A picture that the hub draws lacks the icon of its card."""


def theme_icons() -> Path | None:
    """The folder of the icons of Material for MkDocs, which the tools of the website
    in .venv-docs install, or None without them."""
    try:
        import material  # only the tools of the website have it
    except ImportError:
        return None
    return Path(str(material.__file__)).parent / "templates" / ".icons"


def icon_svg(icon: str, icons: Path | None) -> str:
    """The SVG of icon, a name of Material for MkDocs such as material-file-tree, from
    the folder icons of the theme, where its set and its name make its path, such as
    material/file-tree.svg or fontawesome/brands/github.svg."""
    if icons is None:
        raise DrawingError(
            f"Drawing the icon {icon} needs Material for MkDocs: set up the tools of "
            "the website in .venv-docs, as CONTRIBUTING.md describes."
        )
    for parts in (1, 2):
        *folders, name = icon.split("-", parts)
        path = icons.joinpath(*folders, f"{name}.svg")
        if path.is_file():
            return path.read_text(encoding="utf-8").strip()
    raise DrawingError(f"Material for MkDocs has no icon {icon} in {icons}.")


def drawings(catalog: Catalog, folder: Path, template: str, icons: Path | None) -> str:
    """Write into folder the page of every picture that the hub draws, from template,
    the page of DRAWING, and list each, one per line for scripts/project-pictures.sh:
    the repository, the file in the repository that the picture goes to, the license
    of the repository, the page, and the address and the file in folder of its
    screenshot and of its logo, or - for both without a logo, where the page shows
    the icon of the card from the folder icons of the theme.

    The page names the files by their names alone, since they are beside it, and
    holds the name and the tagline of the project in the language of the picture,
    the tagline without the name when it starts with it, as in a social preview, and
    the place of the screenshot: hanging from the top for a drawing that hangs, and
    framed otherwise."""
    lines = []
    folder.mkdir(parents=True, exist_ok=True)
    for project in catalog.projects:
        image = project.picture
        if project.repo is None or image is None or image.drawing is None:
            continue
        drawing = image.drawing
        logo = ["-", "-"]
        if drawing.logo is not None:
            file = f"{project.slug}.logo{PurePosixPath(drawing.logo).suffix}"
            logo = [
                web.RAW.format(project.repo, web.DEFAULT_BRANCH, drawing.logo),
                (folder / file).as_posix(),
            ]
            mark = f'<img class="logo" src="{escape(file)}" alt="">'
        else:
            mark = f'<div class="logo icon">{icon_svg(project.icon, icons)}</div>'
        for language, screenshot in drawing.screenshot.items():
            base = f"{project.slug}.{language}"
            shot = f"{base}.screenshot{PurePosixPath(screenshot).suffix}"
            name = project.name[language]
            page = folder / f"{base}.html"
            page.write_text(
                Template(template).substitute(
                    lang=escape(language),
                    name=escape(name),
                    tagline=escape(project.tagline[language].removeprefix(f"{name}: ")),
                    accent=drawing.accent,
                    logo=mark,
                    screenshot=escape(shot),
                    place="hanging" if drawing.hangs else "framed",
                ),
                encoding="utf-8",
                newline="\n",
            )
            fields = [
                project.repo,
                f"docs/{image.src[language]}",
                str(project.license),
                page.as_posix(),
                web.RAW.format(project.repo, web.DEFAULT_BRANCH, screenshot),
                (folder / shot).as_posix(),
                *logo,
            ]
            lines.append(" ".join(fields) + "\n")
    return "".join(lines)
