"""What a project works with. The card of a project that says it, requires
in projects.toml, gets a line about it above its buttons, such as "Works with Home
Assistant 2026.8.0 or newer": a text of the catalog, or one with the values that the
hooks read from a file of the repository at the tag of its latest release, such as
homeassistant of hacs.json, from raw.githubusercontent.com, which needs no token. A file
or a value that can't be read leaves the line off the card until the next build, which
passes. The table of the README names the file, and the structured data the
requirements.
"""

from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import PurePosixPath
from typing import Any
from xml.etree import ElementTree

from . import web
from .catalog import PLACEHOLDER, Catalog, Project, Source, log
from .releases import Release, notes_of

# The key of config.extra that keeps what every project works with for the build of
# each language.
WORKS = "works_with"
# A value of such a file, a version such as 2026.8.0 or 33, which a text of Markdown
# holds as it is.
VERSION = re.compile(r"[0-9][0-9A-Za-z.+-]{0,31}", re.ASCII)


class RequirementError(Exception):
    """A file of a repository doesn't hold what its project reads from it as what it
    works with: its message says what is wrong, after the name of the file."""


def json_value(data: object, field: str) -> str | None:
    """The value at field of data, a JSON document, by its keys with a dot between
    two: a text as it is, any other value as JSON, or None when it has none."""
    for key in field.split("."):
        if not isinstance(data, dict) or key not in data:
            return None
        data = data[key]
    return data if isinstance(data, str) else json.dumps(data)


def yaml_value(text: str, field: str) -> str | None:
    """The value of field, a key at the top of text, a YAML document, on the line of
    the key: plain or between quotes, without a comment after it, or None when the
    document has no such line. The standard library reads no YAML, and a file such
    as copier.yml may hold tags that no reader of YAML knows."""
    found = re.search(
        rf"^{re.escape(field)}[ \t]*:[ \t]+"
        r"(?:\"([^\"\n]*)\"|'([^'\n]*)'|([^\s\"'#][^\n#]*?))[ \t]*(?:#[^\n]*)?$",
        "\n".join(text.splitlines()),
        re.MULTILINE,
    )
    if found is None:
        return None
    return next(value for value in found.groups() if value is not None)


def xml_value(root: ElementTree.Element, field: str) -> str | None:
    """The value at field of root, the root of an XML document: the attribute after
    @ of the element at the path before it, or the text of that element without
    one, or None when the document has none."""
    path, _, attribute = field.partition("@")
    element = root.find(path)
    if element is None:
        return None
    value = element.get(attribute) if attribute else element.text
    return None if value is None else value.strip()


def values_in(source: Source, content: bytes) -> dict[str, str]:
    """The value of every field of source in content, its file, by its name: each a
    version, or RequirementError."""
    kind = PurePosixPath(source.file).suffix
    try:
        if kind == ".json":
            data = json.loads(content)
            found = {name: json_value(data, at) for name, at in source.fields.items()}
        elif kind == ".xml":
            # The files of the projects' own releases, read by expat, which expands no
            # external entity and stops an expansion that grows out of proportion.
            root = ElementTree.fromstring(content)
            found = {name: xml_value(root, at) for name, at in source.fields.items()}
        else:
            text = content.decode("utf-8-sig")
            found = {name: yaml_value(text, at) for name, at in source.fields.items()}
    # A broken JSON document, or a file that isn't UTF-8, is a ValueError, and a
    # broken XML document a SyntaxError.
    except (ValueError, SyntaxError) as error:
        raise RequirementError(f"can't be read: {error}") from error
    for name, value in found.items():
        field = source.fields[name]
        if value is None:
            raise RequirementError(f"has no field {field}")
        if not VERSION.fullmatch(value):
            raise RequirementError(f"holds {value!r} in {field}, which is no version")
    return {name: str(value) for name, value in found.items()}


def filled(text: str, values: dict[str, str]) -> str:
    """text with the value of values in the place of each, {} for that of the name
    ""."""
    return PLACEHOLDER.sub(lambda place: values[place[1]], text)


def requirements(
    catalog: Catalog, notes: dict[str, tuple[Release, ...]]
) -> dict[str, dict[str, str]]:
    """What every project of the catalog with requires works with, by its slug, in
    every language: its text, or the text of its source with the values that the
    build reads from its file at the tag of the latest release of notes. A project
    whose release or file can't be read, or whose file lacks a value, has none, which
    the log says without a warning, so that the strict build passes."""
    works = {
        project.slug: project.requires
        for project in catalog.projects
        if isinstance(project.requires, dict)
    }
    sources = [
        (project, project.requires)
        for project in catalog.projects
        if isinstance(project.requires, Source)
    ]
    if not sources:
        return works

    def read(pair: tuple[Project, Source]) -> dict[str, str] | None:
        project, source = pair
        releases = notes.get(str(project.repo))
        why = "The card of %s leaves out what it works with until the next build: %s"
        if not releases:
            log.info(why, project.slug, f"the build has no release of {project.repo}")
            return None
        tag = releases[0].tag
        try:
            values = values_in(
                source, web.download(web.RAW.format(project.repo, tag, source.file))
            )
        except web.SearchError as error:
            log.info(why, project.slug, error)
            return None
        except RequirementError as error:
            where = f"{source.file} of {project.repo} at {tag}"
            log.info(why, project.slug, f"{where} {error}")
            return None
        return {
            language: filled(text, values) for language, text in source.text.items()
        }

    with ThreadPoolExecutor(max_workers=len(sources)) as pool:
        found = list(pool.map(read, sources))
    for (project, _), texts in zip(sources, found, strict=True):
        if texts is not None:
            works[project.slug] = texts
    return works


def requirements_of(config: Any) -> dict[str, dict[str, str]]:
    """What every project works with, of requirements, read once for the build of
    every language, with the releases of notes_of when a project reads it from a
    file."""
    if WORKS not in config.extra:
        catalog: Catalog = config.extra["catalog"]
        read = any(isinstance(project.requires, Source) for project in catalog.projects)
        config.extra[WORKS] = requirements(catalog, notes_of(config) if read else {})
    found: dict[str, dict[str, str]] = config.extra[WORKS]
    return found
