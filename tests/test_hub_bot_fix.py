"""Tests of the fix of the catalog bot in .github/hub/bot.py, with --fix: the edits
that it makes and those that it leaves to a person.
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

import pytest

import hub.bot
import hub.catalog
import hub.reader
import hub.render
import hub.web
from hub_helpers import (
    ADVICE,
    Files,
    GERMAN_SITES,
    HACS,
    INFO,
    ROOT,
    SITE,
    TODAY,
    Websites,
    catalog_data,
    drawing_data,
    drift,
    entry,
    found,
    guarded,
    hooks,
    listed_repo,
    lists,
    network_files,
    nextcloud,
    one_language,
    own_pictures,
    page,
    raw,
    repository,
    source,
    without_repo,
    write,
)

# What the bot fixes itself.


def toml_of(data: dict[str, Any]) -> str:
    """data, the tables of a projects.toml, as that file writes them, with dotted keys
    and a header for each table."""

    def pairs(table: dict[str, Any], prefix: str = "") -> list[str]:
        lines = []
        for key, value in table.items():
            if isinstance(value, dict):
                lines += pairs(value, f"{prefix}{key}.")
            else:
                lines.append(f"{prefix}{key} = {json.dumps(value, ensure_ascii=False)}")
        return lines

    lines = [f"languages = {json.dumps(data['languages'])}", ""]
    for name, value in data.items():
        if isinstance(value, dict):
            lines += [f"[{name}]", *pairs(value), ""]
        elif name != "languages":
            for item in value:
                lines += [f"[[{name}]]", *pairs(item), ""]
    return "\n".join(lines)


def small_repository(root: Path, *projects: dict[str, Any]) -> str:
    """A repository at root with a catalog of projects, with its comments around the
    address of the last, and READMEs with their markers: the text of the catalog."""
    text = re.sub(
        r"^(docs(?:\.en)? = .*\n)",
        r"# The comment above the address.\n\1# The comment below it.\n",
        toml_of(catalog_data(*projects)),
        flags=re.MULTILINE,
    )
    write(root / "projects.toml", text)
    for name in ("README.md", "README.de.md"):
        write(
            root / name, f"# Tool\n\n{hub.render.TABLE_START}\n{hub.render.TABLE_END}\n"
        )
    (root / hub.bot.NOT_FOUND_FIXTURE).parent.mkdir(parents=True)
    return text


def run_fix(
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
    alive: list[str],
    *items: dict[str, Any],
) -> tuple[int, Path]:
    """The exit code of --network --fix in root, for the repositories items and with
    alive the addresses that answer on the web, and the file for the text of the pull
    request."""
    monkeypatch.setattr(hub.web, "status", Websites(dict.fromkeys(alive, 200)))
    monkeypatch.setattr(hub.web, "fetched", Files())
    body = root / "pull-request.md"
    code = hooks.main(["--network", str(lists(root, *items)), "--fix", str(body)], root)
    return code, body


def addresses(root: Path, slug: str = "tool") -> dict[str, str]:
    """The address of the website of the project slug of the catalog in root, in every
    language, as the catalog reads it back."""
    projects = {project.slug: project for project in hub.reader.load(root).projects}
    return projects[slug].docs.url


def test_the_fix_of_a_german_website_that_appeared_changes_only_its_address(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    before = small_repository(tmp_path, one_language())
    first, german = f"{SITE}tool/", f"{SITE}tool/de/"

    code, body = run_fix(
        tmp_path, monkeypatch, [first, german], listed_repo("tool", first)
    )
    out = capsys.readouterr().out

    assert code == hub.catalog.DIFFERS
    written = (tmp_path / "projects.toml").read_text(encoding="utf-8")
    assert written == before.replace(
        f'docs = "{first}"\n', f'docs.en = "{first}"\ndocs.de = "{german}"\n'
    )
    assert "# The comment above the address.\ndocs.en" in written
    assert f'docs.de = "{german}"\n# The comment below it.\n' in written
    # The file reads back as the wanted catalog, whose tables and data follow.
    assert addresses(tmp_path) == {"en": first, "de": german}
    assert hooks.main(["--check"], tmp_path) == 0
    assert german in (tmp_path / "README.de.md").read_text(encoding="utf-8")
    catalog = hub.reader.load(tmp_path)
    assert json.loads(
        (tmp_path / hub.bot.NOT_FOUND_FIXTURE).read_text(encoding="utf-8")
    ) == {"moves": catalog.moves(), "projects": catalog.directory()}
    assert body.read_text(encoding="utf-8") == (
        "The catalog bot compared projects.toml with the websites of the projects and "
        "found differences with one correct edit, which it makes here:\n"
        "\n"
        f"- `tool`: the German home page leads to {german} now, not to {first}.\n"
        "\n"
        "The bot asked the web first: each new address answers 200, and each one that "
        "it took away answers 404 or 410. The tables of the READMEs, the links of the "
        "pages of the website and `tests/fixtures/not-found-data.json` follow.\n"
    )
    # The issue is that of main, with the difference that the edit fixes marked.
    difference = (
        f"`tool`: it has a German website at {german} now. Write "
        f'`docs.en = "{first}"` and `docs.de = "{german}"` in place of `docs`, so '
        "that the German home page leads there."
    )
    assert out == hub.bot.report([difference], [difference])


def test_the_fix_of_a_german_website_that_is_gone_leaves_one_address(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    before = small_repository(tmp_path, entry())
    first, german = f"{SITE}tool/", f"{SITE}tool/de/"

    code, body = run_fix(tmp_path, monkeypatch, [first], listed_repo("tool", first))

    assert code == hub.catalog.DIFFERS
    written = (tmp_path / "projects.toml").read_text(encoding="utf-8")
    assert written == before.replace(
        f'docs.en = "{first}"\n# The comment below it.\ndocs.de = "{german}"\n',
        f'docs = "{first}"\n# The comment below it.\n',
    )
    assert addresses(tmp_path) == {"en": first, "de": first}
    assert hooks.main(["--check"], tmp_path) == 0
    assert f"the German home page leads to {first} now, not to {german}." in (
        body.read_text(encoding="utf-8")
    )


@pytest.mark.parametrize(
    ("project", "alive", "wanted", "lines"),
    [
        (
            "two",
            [f"{SITE}new/", f"{SITE}new/de/"],
            {"en": f"{SITE}new/", "de": f"{SITE}new/de/"},
            f'docs.en = "{SITE}new/"\n# The comment below it.\n'
            f'docs.de = "{SITE}new/de/"\n',
        ),
        (
            "two",
            [f"{SITE}new/"],
            {"en": f"{SITE}new/", "de": f"{SITE}new/"},
            f'docs = "{SITE}new/"\n# The comment below it.\n',
        ),
        (
            "one",
            [f"{SITE}new/"],
            {"en": f"{SITE}new/", "de": f"{SITE}new/"},
            f'docs = "{SITE}new/"\n# The comment below it.\n',
        ),
        (
            "one",
            [f"{SITE}new/", f"{SITE}new/de/"],
            {"en": f"{SITE}new/", "de": f"{SITE}new/de/"},
            f'docs.en = "{SITE}new/"\ndocs.de = "{SITE}new/de/"\n'
            "# The comment below it.\n",
        ),
    ],
)
def test_the_fix_of_a_website_in_another_folder_follows_its_repository(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    project: str,
    alive: list[str],
    wanted: dict[str, str],
    lines: str,
) -> None:
    before = small_repository(tmp_path, entry() if project == "two" else one_language())
    old = (
        f'docs.en = "{SITE}tool/"\n# The comment below it.\n'
        f'docs.de = "{SITE}tool/de/"\n'
        if project == "two"
        else f'docs = "{SITE}tool/"\n# The comment below it.\n'
    )

    # The repository may write its website as a person does.
    homepage = "https://Dennis-Otto.github.io/new"
    code, body = run_fix(tmp_path, monkeypatch, alive, listed_repo("tool", homepage))

    assert code == hub.catalog.DIFFERS
    assert (tmp_path / "projects.toml").read_text(encoding="utf-8") == before.replace(
        old, lines
    )
    assert addresses(tmp_path) == wanted
    assert body.read_text(encoding="utf-8").endswith(
        f"- `tool`: readers who still come to {SITE}tool/ find nothing. To lead them "
        "along, name its folder in `former` and its pages in `former/<folder>.txt`. "
        "The tests that name its folder fail until they name the new one. Push both "
        "onto this branch: the bot leaves a pull request with a commit of a person "
        "alone.\n"
    )


@pytest.mark.parametrize(
    ("project", "alive", "homepage"),
    [
        # Two websites answer: only a person knows which the project means.
        (one_language(), [f"{SITE}tool/", f"{SITE}new/"], f"{SITE}new/"),
        # The website that the repository names doesn't answer.
        (one_language(), [f"{SITE}tool/"], f"{SITE}new/"),
        # A page in a folder is no website.
        (one_language(), [f"{SITE}new/guide/"], f"{SITE}new/guide/"),
        # The website of the catalog is elsewhere: more than its folder differs.
        (
            entry(docs="https://example.org/tool/"),
            [f"{SITE}new/"],
            f"{SITE}new/",
        ),
        # A German website is gone beside an English one that answers: here the
        # website is away, and the bot can't tell why.
        (entry(), [], f"{SITE}tool/"),
    ],
)
def test_a_difference_that_only_a_person_can_tell_stays_in_the_issue(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    project: dict[str, Any],
    alive: list[str],
    homepage: str,
) -> None:
    before = small_repository(tmp_path, project)

    code, body = run_fix(tmp_path, monkeypatch, alive, listed_repo("tool", homepage))

    assert code == hub.catalog.DIFFERS
    assert (tmp_path / "projects.toml").read_text(encoding="utf-8") == before
    assert not body.exists()
    out = capsys.readouterr().out
    assert hub.bot.FIXED not in out
    assert hub.bot.FIX_BRANCH not in out


@pytest.mark.parametrize(
    "item",
    [
        listed_repo("tool", f"{SITE}tool/", archived=True),
        listed_repo("tool", f"{SITE}tool/", private=True),
        # A repository that was renamed takes its website along.
        listed_repo("other"),
    ],
)
def test_a_repository_that_needs_a_person_keeps_every_difference_of_its_project(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    item: dict[str, Any],
) -> None:
    before = small_repository(tmp_path, entry())

    # The German website looks gone, but the bot doesn't remove it.
    code, body = run_fix(tmp_path, monkeypatch, [f"{SITE}tool/"], item)

    assert code == hub.catalog.DIFFERS
    assert (tmp_path / "projects.toml").read_text(encoding="utf-8") == before
    assert not body.exists()
    out = capsys.readouterr().out
    assert f"`tool`: the German website {SITE}tool/de/ is gone." in out
    assert hub.bot.FIXED not in out


def test_the_issue_marks_only_the_differences_that_the_edits_fix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    small_repository(tmp_path, one_language(), one_language("old"))

    code, _ = run_fix(
        tmp_path,
        monkeypatch,
        [f"{SITE}tool/", f"{SITE}tool/de/"],
        listed_repo("tool", f"{SITE}tool/"),
        listed_repo("old", f"{SITE}old/", archived=True),
    )

    assert code == hub.catalog.DIFFERS
    fixes = (
        f"`tool`: it has a German website at {SITE}tool/de/ now. Write "
        f'`docs.en = "{SITE}tool/"` and `docs.de = "{SITE}tool/de/"` in place of '
        "`docs`, so that the German home page leads there."
    )
    stays = (
        "`old`: Dennis-Otto/old is archived. Remove the project, or unarchive the "
        "repository."
    )
    assert capsys.readouterr().out == hub.bot.report([fixes, stays], [fixes])
    assert addresses(tmp_path, "old") == {"en": f"{SITE}old/", "de": f"{SITE}old/"}


def test_the_issue_says_what_the_bot_keeps_in_its_pull_request() -> None:
    assert hub.bot.report(["`tool`: one.", "`app`: two."], ["`app`: two."]) == (
        "The catalog bot compares projects.toml with the repositories on GitHub, with "
        "the websites of the projects in every language and with the files that say "
        "what they work with every week, and found 2 difference(s):\n"
        "\n"
        "- `tool`: one.\n"
        "- `app`: two. *The bot makes this edit.*\n"
        "\n"
        "Change projects.toml, whose comments describe every key, and write the "
        "tables of the READMEs with\n"
        "\n"
        "```sh\n"
        "python3 -I .github/mkdocs_project.py --write\n"
        "```\n"
        "\n"
        "A new card needs its picture too, which `bash scripts/project-pictures.sh` "
        "makes. The next run closes this issue once the catalog is current; start "
        "the Catalog workflow by hand to check sooner.\n"
        "\n"
        "The bot keeps the edits that this list marks in one pull request from the "
        "branch `bot/catalog`. Without the pull request, make them as the list says, "
        "or with `python3 -I .github/mkdocs_project.py --network repositories.json "
        "--fix pull-request.md`.\n"
    )


@pytest.mark.parametrize(
    ("lines", "message"),
    [
        # A comment on its line, which the bot would lose.
        (f'docs = "{SITE}tool/" # The website.\n', "a comment on its line"),
        # A form that the bot doesn't edit.
        (f'docs = {{ en = "{SITE}tool/" }}\n', "an inline table"),
    ],
)
def test_an_address_in_another_form_stays_in_the_issue(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    lines: str,
    message: str,
) -> None:
    small = small_repository(tmp_path, one_language())
    edited = small.replace(f'docs = "{SITE}tool/"\n', lines)
    write(tmp_path / "projects.toml", edited)

    code, body = run_fix(
        tmp_path,
        monkeypatch,
        [f"{SITE}tool/", f"{SITE}tool/de/"],
        listed_repo("tool", f"{SITE}tool/"),
    )

    assert code == hub.catalog.DIFFERS, message
    assert (tmp_path / "projects.toml").read_text(encoding="utf-8") == edited
    assert not body.exists()
    assert hub.bot.FIXED not in capsys.readouterr().out


def test_an_edit_that_doesnt_read_back_as_meant_isnt_made(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A second line of the German address that the bot doesn't see, in a form that it
    # leaves alone, beside the one address that it would write.
    small = small_repository(tmp_path, entry())
    edited = small.replace(
        f'docs.de = "{SITE}tool/de/"\n', f'docs.de = "{SITE}tool/de/" # German\n'
    )
    write(tmp_path / "projects.toml", edited)

    code, body = run_fix(
        tmp_path, monkeypatch, [f"{SITE}tool/"], listed_repo("tool", f"{SITE}tool/")
    )

    assert code == hub.catalog.DIFFERS
    assert (tmp_path / "projects.toml").read_text(encoding="utf-8") == edited
    assert not body.exists()


def test_an_address_in_a_folder_that_former_names_isnt_written(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    before = small_repository(tmp_path, one_language(former=["new"]))
    write(tmp_path / "former/new.txt", "index.html\n")

    code, body = run_fix(
        tmp_path, monkeypatch, [f"{SITE}new/"], listed_repo("tool", f"{SITE}new/")
    )

    assert code == hub.catalog.DIFFERS
    assert (tmp_path / "projects.toml").read_text(encoding="utf-8") == before
    assert not body.exists()


def test_only_the_catalog_that_was_meant_reads_back() -> None:
    catalog = hub.reader.read(catalog_data(one_language()))
    text = toml_of(catalog_data(one_language()))

    assert hub.bot.reads_back(text, catalog)
    assert not hub.bot.reads_back(text.replace("tool/", "other/"), catalog)
    assert not hub.bot.reads_back("docs =", catalog)


@pytest.mark.parametrize(
    "text",
    [
        "no project here\n",
        f'[[project]]\nslug = "other"\ndocs = "{SITE}other/"\n',
        '[[project]]\nslug = "tool"\nname = "A tool"\n',
    ],
)
def test_a_catalog_without_the_address_of_the_project_gets_no_edit(text: str) -> None:
    edit = hub.bot.Edit(
        "tool",
        {"en": f"{SITE}tool/", "de": f"{SITE}tool/"},
        hub.catalog.Link("", {}, {"en": f"{SITE}new/", "de": f"{SITE}new/"}),
    )

    assert hub.bot.with_docs(text, edit, ("en", "de")) is None


def test_the_edit_keeps_every_other_project_and_table() -> None:
    other = f'[[project]]\nslug = "other"\ndocs = "{SITE}other/"\n\n'
    tail = '[trust]\ndocs = "not the address of a project"\n'
    edit = hub.bot.Edit(
        "tool",
        {"en": f"{SITE}tool/", "de": f"{SITE}tool/"},
        hub.catalog.Link("", {}, {"en": f"{SITE}tool/", "de": f"{SITE}tool/de/"}),
    )

    assert hub.bot.with_docs(
        f'{other}[[project]]\nslug = "tool"\ndocs = "{SITE}tool/"\nname = "A tool"\n\n'
        f"{tail}",
        edit,
        ("en", "de"),
    ) == (
        f'{other}[[project]]\nslug = "tool"\ndocs.en = "{SITE}tool/"\n'
        f'docs.de = "{SITE}tool/de/"\nname = "A tool"\n\n{tail}'
    )


def test_the_address_of_a_german_website_elsewhere_stays_while_it_answers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    elsewhere = f"{SITE}werkzeug/"
    small_repository(tmp_path, entry(docs={"en": f"{SITE}tool/", "de": elsewhere}))

    # It stays when the website moved, and follows nothing.
    run_fix(
        tmp_path,
        monkeypatch,
        [f"{SITE}new/", elsewhere],
        listed_repo("tool", f"{SITE}new/"),
    )

    assert addresses(tmp_path) == {"en": f"{SITE}new/", "de": elsewhere}


def test_a_project_without_a_repository_gets_its_german_website_too(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    small_repository(tmp_path, without_repo(one_language()), one_language("app"))

    code, _ = run_fix(
        tmp_path,
        monkeypatch,
        [f"{SITE}tool/de/"],
        listed_repo("app", f"{SITE}app/"),
    )

    assert code == hub.catalog.DIFFERS
    assert addresses(tmp_path) == {"en": f"{SITE}tool/", "de": f"{SITE}tool/de/"}


def test_a_project_without_a_website_gets_no_edit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    board = entry("board")
    del board["docs"]
    before = small_repository(tmp_path, board, one_language())

    code, body = run_fix(
        tmp_path,
        monkeypatch,
        [f"{SITE}tool/"],
        listed_repo("board", f"{SITE}board/"),
        listed_repo("tool", f"{SITE}tool/"),
    )

    assert code == hub.catalog.DIFFERS
    assert (tmp_path / "projects.toml").read_text(encoding="utf-8") == before
    assert not body.exists()


def test_the_pages_of_the_website_follow_the_edit_in_their_language(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    small_repository(tmp_path, entry())
    first, german = f"{SITE}tool/", f"{SITE}tool/de/"
    links = f"[Tool]({first}), [German]({german}), [Guide]({german}guide/)\n"
    for name in ("about.md", "about.de.md"):
        write(tmp_path / "docs" / name, links)
    write(tmp_path / "docs/plain.de.md", "No link.\n")
    write(
        tmp_path / "README.de.md",
        f"[German]({german})\n{hub.render.TABLE_START}\n{hub.render.TABLE_END}\n",
    )

    code, _ = run_fix(tmp_path, monkeypatch, [first], listed_repo("tool", first))

    assert code == hub.catalog.DIFFERS
    # Only a link of its language to the very address: a page of a website that is
    # gone is for the check of the links to name.
    assert (tmp_path / "docs/about.md").read_text(encoding="utf-8") == links
    assert (tmp_path / "docs/about.de.md").read_text(encoding="utf-8") == (
        f"[Tool]({first}), [German]({first}), [Guide]({german}guide/)\n"
    )
    assert (tmp_path / "docs/plain.de.md").read_text(encoding="utf-8") == "No link.\n"
    assert f"[German]({first})\n" in (tmp_path / "README.de.md").read_text(
        encoding="utf-8"
    )


def test_the_fix_follows_the_catalog_of_the_repository_and_comes_to_rest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository(tmp_path)
    for page in (ROOT / "docs").glob("*.md"):
        shutil.copyfile(page, tmp_path / "docs" / page.name)
    catalog = hub.reader.load(ROOT)
    # Every German website is gone, and the English ones answer.
    alive = [
        project.docs.url["en"]
        for project in catalog.projects
        if project.docs is not None
    ]
    monkeypatch.setattr(hub.web, "status", Websites(dict.fromkeys(alive, 200)))
    monkeypatch.setattr(hub.web, "fetched", Files(network_files()))
    body = tmp_path / "pull-request.md"
    arguments = ["--network", str(lists(tmp_path, *TODAY)), "--fix", str(body)]

    assert hooks.main(arguments, tmp_path) == hub.catalog.DIFFERS

    for url in GERMAN_SITES:
        assert url in body.read_text(encoding="utf-8")
    fixed = hub.reader.load(tmp_path)
    assert [project.slug for project in fixed.projects] == [
        project.slug for project in catalog.projects
    ]
    for project in fixed.projects:
        assert len(set(project.website.values())) == 1, project.slug
    # What the checks of the pull request ask: the tables, the data of the 404 script
    # and the links of the Security page.
    assert hooks.main(["--check"], tmp_path) == 0
    assert json.loads(
        (tmp_path / hub.bot.NOT_FOUND_FIXTURE).read_text(encoding="utf-8")
    ) == {"moves": fixed.moves(), "projects": fixed.directory()}
    security = (tmp_path / "docs/security.de.md").read_text(encoding="utf-8")
    for project in fixed.projects:
        assert f"]({project.website['de']})" in security, project.slug
    # The next run finds nothing more to edit, and asks each address once.
    body.unlink()
    websites = Websites(dict.fromkeys(alive, 200))
    monkeypatch.setattr(hub.web, "status", websites)

    assert hooks.main(arguments, tmp_path) == 0
    assert not body.exists()
    assert len(websites.asked) == len(set(websites.asked))


def test_the_catalog_of_the_repository_needs_no_edit_today(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    repository(tmp_path)
    monkeypatch.setattr(hub.web, "status", Websites(GERMAN_SITES))
    monkeypatch.setattr(hub.web, "fetched", Files(network_files()))
    body = tmp_path / "pull-request.md"

    assert (
        hooks.main(
            ["--network", str(lists(tmp_path, *TODAY)), "--fix", str(body)], tmp_path
        )
        == 0
    )

    assert not body.exists()
    for name in (
        "projects.toml",
        "README.md",
        "README.de.md",
        hub.bot.NOT_FOUND_FIXTURE,
    ):
        assert (tmp_path / name).read_bytes() == (ROOT / name).read_bytes(), name
    assert "projects.toml is current" in capsys.readouterr().out


def test_a_readme_without_its_markers_stops_the_fix_before_it_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    before = small_repository(tmp_path, one_language())
    write(tmp_path / "README.de.md", "# Werkzeug\n")

    code, body = run_fix(
        tmp_path,
        monkeypatch,
        [f"{SITE}tool/", f"{SITE}tool/de/"],
        listed_repo("tool", f"{SITE}tool/"),
    )

    assert code == 2
    assert (tmp_path / "projects.toml").read_text(encoding="utf-8") == before
    assert not (tmp_path / hub.bot.NOT_FOUND_FIXTURE).exists()
    assert not body.exists()
    output = capsys.readouterr()
    assert output.out == ""
    assert "README.de.md needs the lines" in output.err


def test_the_fix_goes_with_the_comparison(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as stop:
        hooks.main(["--check", "--fix", "pull-request.md"])

    assert stop.value.code == 2
    assert "--fix goes with --network" in capsys.readouterr().err


def pull_request_job() -> str:
    """The job of catalog.yml that holds the release app."""
    workflow = (ROOT / ".github/workflows/catalog.yml").read_text(encoding="utf-8")
    return workflow[
        workflow.index("\n  catalog-pull-request:\n") : workflow.index("\n  rebuild:\n")
    ]


def test_the_pull_request_of_the_bot_comes_from_a_job_with_the_release_app() -> None:
    job = pull_request_job()

    assert f"      BRANCH: {hub.bot.FIX_BRANCH}\n" in job
    # A title that needs no entry of the changelog and makes no release.
    assert '      HEADLINE: "docs: ' in job
    assert "    needs: catalog\n" in job
    # Only main may use the environment with the key of the app.
    assert (
        "    if: vars.RELEASE_AUTOMATION_CLIENT_ID != '' && "
        "github.ref == 'refs/heads/main'\n"
    ) in job
    assert "    environment:\n      name: release\n      deployment: false\n" in job
    # It writes the issue with the token of the workflow, and takes from the app only
    # what the branch and the pull request need.
    assert re.findall(r"^ +([a-z-]+): (read|write)\b", job, re.MULTILINE) == [
        ("issues", "write"),
        ("permission-contents", "write"),
        ("permission-pull-requests", "write"),
        ("permission-workflows", "write"),
    ]
    # It checks out and runs nothing of the job that made the edits.
    assert "actions/checkout" not in job
    assert "mkdocs_project.py" not in job
    # No merge without a person.
    assert "gh pr merge" not in job
    assert "gh issue edit" in job
    assert guarded(job) == [
        "api.github.com:443",
        "results-receiver.actions.githubusercontent.com:443",
    ]


def test_the_commit_of_the_bot_holds_only_the_files_that_it_edits() -> None:
    job = pull_request_job()
    allowed = re.search(r"^ +edited='(.+)'$", job, re.MULTILINE)
    assert allowed is not None
    catalog = hub.reader.load(ROOT)
    paths = [
        hub.catalog.CATALOG,
        hub.bot.NOT_FOUND_FIXTURE,
        *hub.render.readmes(catalog).values(),
        *(f"docs/{page.name}" for page in (ROOT / "docs").glob("*.md")),
    ]

    for path in paths:
        assert re.fullmatch(allowed[1], path), path
    for path in (
        ".github/workflows/catalog.yml",
        ".github/mkdocs_project.py",
        "docs/decisions/README.md",
        "scripts/check.sh",
    ):
        assert not re.fullmatch(allowed[1], path), path
    # A person may finish the edits on the branch.
    assert 'select(. != \\"${APP_SLUG}[bot]\\")' in job
    # The button "Update branch" is no such commit, though a person clicked it.
    assert 'select(.messageHeadline | startswith(\\"Merge branch\\") | not)' in job


def test_the_job_of_the_comparison_keeps_the_edits_for_the_pull_request() -> None:
    workflow = (ROOT / ".github/workflows/catalog.yml").read_text(encoding="utf-8")
    job = workflow[
        workflow.index("\n  catalog:\n") : workflow.index("\n  catalog-pull-request:\n")
    ]

    assert (
        'python3 -I .github/mkdocs_project.py --network "$REPOSITORIES" '
        '--fix "$PULL_REQUEST" >"$REPORT"'
    ) in job
    assert "if: steps.keep.outputs.edits == 'true'\n" in job
    assert "actions/upload-artifact@" in job
    # The job holds no key, and only the job of the pull request names the artifact.
    assert "secrets.RELEASE_AUTOMATION_PRIVATE_KEY" not in job
    assert "name: catalog-edits\n" in job
    assert "name: catalog-edits\n" in pull_request_job()


def test_the_bot_reads_what_a_project_works_with_on_its_default_branch() -> None:
    url = raw("Dennis-Otto/tool", "HEAD", "hacs.json")
    files = Files({url: HACS})

    assert (
        drift(
            one_language(requires=source()),
            repositories=found(listed_repo("tool")),
            files=files,
        )
        == []
    )
    assert files.asked == [url]


def test_a_file_that_is_gone_from_the_default_branch_is_named() -> None:
    assert drift(
        one_language(requires=source()), repositories=found(listed_repo("tool"))
    ) == [
        "`tool`: Dennis-Otto/tool has no hacs.json any more, from which its card "
        f"reads what it works with. {ADVICE}"
    ]


def test_a_file_without_its_value_on_the_default_branch_is_named() -> None:
    url = raw("Dennis-Otto/tool", "HEAD", "appinfo/info.xml")
    files = Files({url: INFO.replace(b' max-version="35"', b"")})

    assert drift(
        one_language(requires=nextcloud()),
        repositories=found(listed_repo("tool")),
        files=files,
    ) == [
        "`tool`: appinfo/info.xml of Dennis-Otto/tool has no field "
        "dependencies/nextcloud@max-version, and its card reads what it works with "
        f"from there. {ADVICE}"
    ]


def test_the_bot_checks_the_files_from_which_the_hub_draws_a_picture() -> None:
    shot = raw("Dennis-Otto/tool", "HEAD", "docs/images/de/shot.png")
    logo = raw("Dennis-Otto/tool", "HEAD", "docs/logo.svg")
    files = Files({shot: b"RIFF"})

    assert drift(
        one_language(image=own_pictures(), drawing=drawing_data()),
        repositories=found(listed_repo("tool")),
        files=files,
    ) == [
        "`tool`: Dennis-Otto/tool has no docs/logo.svg any more, from which the hub "
        "draws a picture of its card. Correct `drawing` with a file of the "
        "repository."
    ]
    assert files.asked == [shot, logo]


def test_a_project_that_says_what_it_works_with_in_texts_has_no_file() -> None:
    files = Files()

    assert (
        drift(
            one_language(requires={"en": "Any computer", "de": "Jeder Computer"}),
            repositories=found(listed_repo("tool")),
            files=files,
        )
        == []
    )
    assert files.asked == []
