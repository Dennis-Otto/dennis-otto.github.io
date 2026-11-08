"""Tests of .github/mkdocs_project.py, what MkDocs loads and what the scripts and the
workflows run: its options, and that it needs nothing but the standard library.
"""

from __future__ import annotations

import re
import runpy
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import hub
import hub.events
from hub_helpers import HOOKS, hooks, repository

# The most lines of a module of the package.
MOST_LINES = 750


def test_check_passes_when_the_table_is_current(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repository(tmp_path)

    assert hooks.main(["--check"], tmp_path) == 0
    assert capsys.readouterr().out == (
        "README.md has the current table of the projects of projects.toml.\n"
        "README.de.md has the current table of the projects of projects.toml.\n"
    )


def test_check_shows_a_table_edited_by_hand_and_the_command_that_fixes_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    readme = repository(tmp_path)
    text = readme.read_text(encoding="utf-8")
    edited = text.replace("local and in realtime", "für Dart")
    readme.write_text(edited, encoding="utf-8", newline="\n")

    assert hooks.main(["--check"], tmp_path) == 1

    output = capsys.readouterr()
    assert "--- README.md\n+++ README.md, from projects.toml\n" in output.out
    assert (
        "-| [homedarts-for-autodarts]"
        "(https://github.com/Dennis-Otto/homedarts-for-autodarts) | "
    ) in output.out
    tagline = "HomeDarts for Autodarts: Autodarts boards in Home Assistant, für Dart"
    assert f"| {tagline} |" in output.out
    assert output.err == (
        "README.md differs from projects.toml; write its table with\n"
        "  python3 -I .github/mkdocs_project.py --write\n"
    )
    assert readme.read_text(encoding="utf-8") == edited
    assert output.out.endswith(
        "README.de.md has the current table of the projects of projects.toml.\n"
    )


def test_check_shows_a_german_table_edited_by_hand(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repository(tmp_path)
    german = tmp_path / "README.de.md"
    text = german.read_text(encoding="utf-8")
    edited = text.replace("lokal und in Echtzeit", "local and in realtime")
    assert edited != text
    german.write_text(edited, encoding="utf-8", newline="\n")

    assert hooks.main(["--check"], tmp_path) == 1

    output = capsys.readouterr()
    assert output.out.startswith(
        "README.md has the current table of the projects of projects.toml.\n"
        "--- README.de.md\n+++ README.de.md, from projects.toml\n"
    )
    assert "+| [homedarts-for-autodarts]" in output.out
    assert "lokal und in Echtzeit |" in output.out
    assert output.err == (
        "README.de.md differs from projects.toml; write its table with\n"
        "  python3 -I .github/mkdocs_project.py --write\n"
    )
    assert german.read_text(encoding="utf-8") == edited


def test_write_brings_the_table_up_to_date_once(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repository(tmp_path)
    texts = {}
    for name in ("README.md", "README.de.md"):
        readme = tmp_path / name
        text = readme.read_text(encoding="utf-8")
        start = text.index("<!-- projects:start -->") + len("<!-- projects:start -->")
        emptied = text[:start] + "\n" + text[text.index("<!-- projects:end") :]
        readme.write_text(emptied, encoding="utf-8", newline="\n")
        texts[name] = text

    assert hooks.main(["--write"], tmp_path) == 0
    assert hooks.main(["--write"], tmp_path) == 0

    for name, text in texts.items():
        assert (tmp_path / name).read_bytes() == text.encode(), name
    assert capsys.readouterr().out == (
        "README.md has the table of the projects of projects.toml now.\n"
        "README.de.md has the table of the projects of projects.toml now.\n"
        "README.md has the current table of the projects of projects.toml.\n"
        "README.de.md has the current table of the projects of projects.toml.\n"
    )


def test_a_missing_german_text_fails_the_check(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repository(tmp_path)
    catalog = tmp_path / "projects.toml"
    text = catalog.read_text(encoding="utf-8")
    start = text.index('summary.de = "Die OCR')
    removed = text[:start] + text[text.index("\n", start) + 1 :]
    catalog.write_text(removed, encoding="utf-8", newline="\n")

    assert hooks.main(["--check"], tmp_path) == 1
    assert capsys.readouterr().err == (
        "projects.toml has 1 problem(s):\n"
        "  paperless-unified-search: summary.de is missing.\n"
        "The comments at the top of projects.toml describe every key.\n"
    )


def test_a_missing_readme_fails_the_check(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repository(tmp_path).unlink()

    assert hooks.main(["--write"], tmp_path) == 1
    assert "README.md" in capsys.readouterr().err


def test_a_missing_german_readme_fails_the_check(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repository(tmp_path)
    (tmp_path / "README.de.md").unlink()

    assert hooks.main(["--check"], tmp_path) == 1
    output = capsys.readouterr()
    assert "README.de.md" in output.err
    assert output.out == ""


def test_a_german_readme_without_its_markers_leaves_both_readmes_alone(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    readme = repository(tmp_path)
    english = readme.read_text(encoding="utf-8")
    readme.write_text(
        english.replace("Paperless-ngx documents", "Documents"), encoding="utf-8"
    )
    edited = readme.read_bytes()
    (tmp_path / "README.de.md").write_text("# Dennis Otto\n", encoding="utf-8")

    assert hooks.main(["--write"], tmp_path) == 1

    assert capsys.readouterr().err == (
        "README.de.md needs the lines <!-- projects:start --> and "
        "<!-- projects:end -->, in this order; the table of the projects goes "
        "between them.\n"
    )
    assert readme.read_bytes() == edited


def test_the_script_needs_check_or_write(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as stop:
        hooks.main([])

    assert stop.value.code == 2
    assert (
        "one of the arguments --write --check --pictures --drawings --network --watch "
        "--site is required" in capsys.readouterr().err
    )


def test_the_script_lists_the_pictures_for_the_script_that_makes_them(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Without a README, which the list doesn't need.
    repository(tmp_path).unlink()

    assert hooks.main(["--pictures"], tmp_path) == 0

    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == (
        "Dennis-Otto/homedarts-for-autodarts "
        "docs/images/projects/homedarts-for-autodarts.webp MIT"
    )
    assert lines[2] == (
        "Dennis-Otto/paperless-sync docs/images/projects/paperless-sync.webp "
        "AGPL-3.0-or-later"
    )
    assert lines[5] == (
        "Dennis-Otto/repo-pager docs/images/projects/repo-pager.webp MIT"
    )
    assert len(lines) == 7


def test_a_broken_catalog_lists_no_pictures(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert hooks.main(["--pictures"], tmp_path) == 1

    output = capsys.readouterr()
    assert output.out == ""
    assert "projects.toml can't be read" in output.err


def test_the_script_runs_as_a_program(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "argv", [str(HOOKS), "--check"])

    with pytest.raises(SystemExit) as stop:
        runpy.run_path(str(HOOKS), run_name="__main__")

    assert stop.value.code == 0
    assert "current table" in capsys.readouterr().out


def copy_of_the_script(root: Path) -> Path:
    """The file of the hooks with its package, in a copy of the repository at root."""
    repository(root)
    script = root / ".github" / "mkdocs_project.py"
    script.parent.mkdir()
    shutil.copyfile(HOOKS, script)
    shutil.copytree(HOOKS.parent / "hub", script.parent / "hub")
    return script


def test_the_script_needs_the_standard_library_alone(tmp_path: Path) -> None:
    script = copy_of_the_script(tmp_path)

    result = subprocess.run(
        [sys.executable, "-I", "-S", str(script), "--check"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )

    assert (result.returncode, result.stderr) == (0, "")


def test_the_script_finds_its_package_from_any_folder_and_leaves_no_bytecode(
    tmp_path: Path,
) -> None:
    # python3 -I leaves the folder of a script off sys.path, and ignores
    # PYTHONDONTWRITEBYTECODE. The bots commit what a fix changes, so a __pycache__
    # beside the code would go into their pull requests.
    script = copy_of_the_script(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()

    result = subprocess.run(
        [sys.executable, "-I", str(script), "--check"],
        cwd=elsewhere,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )

    assert (result.returncode, result.stderr) == (0, "")
    assert not list(tmp_path.rglob("__pycache__"))


def test_mkdocs_finds_every_event_hook_of_the_package_in_the_file_that_it_loads() -> (
    None
):
    events = {
        name: value
        for name, value in vars(hub.events).items()
        if name.startswith("on_") and callable(value)
    }

    assert len(events) == 9
    for name, event in events.items():
        assert getattr(hooks, name) is event


@pytest.mark.parametrize(
    "module",
    sorted(path.name for path in (HOOKS.parent / "hub").glob("*.py")),
)
def test_no_module_of_the_package_grows_past_what_a_reader_keeps_in_view(
    module: str,
) -> None:
    # A module that grows this long holds a second concern: give it a module of its
    # own, and a line in the docstring of hub/__init__.py.
    text = (HOOKS.parent / "hub" / module).read_text(encoding="utf-8")

    assert text.count("\n") <= MOST_LINES


def test_the_package_lists_each_of_its_modules_in_the_order_of_its_imports() -> None:
    listed = re.findall(r"^    (\w+) {2,}", hub.__doc__ or "", re.MULTILINE)
    files = {path.stem for path in (HOOKS.parent / "hub").glob("*.py")} - {"__init__"}

    assert set(listed) == files
    for place, name in enumerate(listed):
        imported = re.findall(
            r"^from (?:\.(\w+) import|\. import (\w+))",
            (HOOKS.parent / "hub" / f"{name}.py").read_text(encoding="utf-8"),
            re.MULTILINE,
        )
        assert {first or second for first, second in imported} <= set(listed[:place])
