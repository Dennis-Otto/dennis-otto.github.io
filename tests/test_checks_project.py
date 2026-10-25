"""Tests of the explanation of the checks of this website in
.github/checks.project.toml: the PR coach shows it when scripts/check-project.sh
fails, and the fix bot runs its autofix, which writes the tables of the projects in
README.md and README.de.md anew."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXPLANATIONS = ROOT / ".github/checks.project.toml"
SCRIPT = ROOT / "scripts/check-project.sh"
# The check docs runs this script on the built website, and it runs the browser tests.
SITE_SCRIPT = ROOT / "scripts/check-site.sh"
BROWSER_TESTS = ROOT / "tests/e2e/hub.mjs"
HOOKS = ROOT / ".github/mkdocs_project.py"
STEP = "Checks of this project"
# In a command of autofix, the Python that runs the fix bot.
PYTHON = "{python}"


def explanation() -> dict[str, Any]:
    """The explanation of the step of scripts/check.sh that runs check-project.sh."""
    steps = tomllib.loads(EXPLANATIONS.read_text(encoding="utf-8"))["step"]
    return steps[STEP]


def text(entry: dict[str, Any], name: str) -> str:
    """A text of the explanation as the coach shows it, on one line."""
    return " ".join(entry[name].split())


def headings(script: Path = SCRIPT) -> list[str]:
    """The headings that a script prints after ==, such as one for each check of
    scripts/check-project.sh."""
    return re.findall(
        r"""^printf '\\n== %s\\n' "([^"]+)"$""",
        script.read_text(encoding="utf-8"),
        re.M,
    )


def docs() -> dict[str, Any]:
    """The explanation of the check docs, which runs scripts/check-site.sh."""
    checks = tomllib.loads(EXPLANATIONS.read_text(encoding="utf-8"))["check"]
    return checks["docs"]


def scenarios() -> list[str]:
    """The titles of the scenarios of the browser tests, in the order that they run."""
    return re.findall(
        r'^  \{ id: "[a-z-]+", title: "([^"]+)", run: \w+ \},$',
        BROWSER_TESTS.read_text(encoding="utf-8"),
        re.M,
    )


def write_command() -> str:
    """The command that writes the table of the projects, as the check names it."""
    found = re.search(
        r'^WRITE = "([^"]+)"$', HOOKS.read_text(encoding="utf-8"), re.M
    )
    assert found is not None
    return found[1]


def outside_the_ci() -> dict[str, str]:
    """The environment of a command that writes neither the summary of the job nor
    its annotations, as on your machine."""
    return {
        **{
            name: value
            for name, value in os.environ.items()
            if name not in {"GITHUB_ACTIONS", "GITHUB_STEP_SUMMARY"}
        },
        "PYTHONIOENCODING": "utf-8",
        "PYTHONDONTWRITEBYTECODE": "1",
    }


def test_the_script_has_three_checks() -> None:
    assert headings() == [
        "Tests of the scripts of the website, with every line, branch and function "
        "covered",
        "The projects of projects.toml in the READMEs",
        "Tests of the hooks of the website, with every line and branch covered",
    ]


@pytest.mark.parametrize("heading", headings())
def test_the_explanation_names_each_check_by_its_heading(heading: str) -> None:
    assert f"*{heading}*:" in text(explanation(), "problem")


def test_the_explanation_says_how_many_checks_there_are() -> None:
    assert text(explanation(), "problem").startswith(
        "One of the three checks of this website in `scripts/check-project.sh` failed"
    )


def test_the_table_fixes_itself_with_the_command_that_the_check_names() -> None:
    command = write_command()

    assert command == "python3 -I .github/mkdocs_project.py --write"
    assert explanation()["autofix"] == [command.replace("python3", PYTHON, 1)]
    assert explanation()["commands"] == [command, "bash scripts/check-project.sh"]


def test_the_explanation_leads_to_its_section_of_the_readme() -> None:
    docs = explanation()["docs"]
    page, anchor = docs.split("#")
    titles = re.findall(r"^#+ (.+)$", (ROOT / page).read_text(encoding="utf-8"), re.M)

    assert page == "README.md"
    assert anchor in {title.lower().replace(" ", "-") for title in titles}


def test_the_autofix_writes_a_table_that_differs_and_then_changes_nothing(
    tmp_path: Path,
) -> None:
    # A copy of the repository with the script, whose root is the folder above it.
    (tmp_path / ".github").mkdir()
    shutil.copyfile(HOOKS, tmp_path / ".github/mkdocs_project.py")
    for name in ("projects.toml", "README.md", "README.de.md"):
        shutil.copyfile(ROOT / name, tmp_path / name)
    shutil.copytree(ROOT / "former", tmp_path / "former")
    readme = tmp_path / "README.md"
    current = readme.read_bytes()
    catalog = tmp_path / "projects.toml"
    # The English tagline of the first project, whatever it says today, with a
    # marker added, as an edit of projects.toml without --write leaves it.
    text = catalog.read_text(encoding="utf-8")
    tagline = tomllib.loads(text)["project"][0]["tagline"]["en"]
    changed = f"{tagline} (changed)"
    assert f'"{tagline}"' in text
    catalog.write_text(
        text.replace(f'"{tagline}"', f'"{changed}"', 1),
        encoding="utf-8",
        newline="\n",
    )
    # The command as the fix bot runs it, with the Python that runs the bot.
    [autofix] = explanation()["autofix"]
    python, *arguments = autofix.split()
    assert python == PYTHON

    def run(*arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, *arguments],
            cwd=tmp_path,
            env=outside_the_ci(),
            capture_output=True,
            encoding="utf-8",
            check=False,
        )

    assert run(*arguments).returncode == 0
    fixed = readme.read_bytes()
    assert fixed != current
    assert changed.encode() in fixed
    assert run("-I", ".github/mkdocs_project.py", "--check").returncode == 0
    again = run(*arguments)
    assert again.returncode == 0
    assert again.stdout == (
        "README.md has the current table of the projects of projects.toml.\n"
        "README.de.md has the current table of the projects of projects.toml.\n"
    )
    assert readme.read_bytes() == fixed


def test_the_coach_explains_the_step_in_the_words_of_this_project() -> None:
    explained = subprocess.run(
        [sys.executable, ".github/blueprint.py", "coach", "explain", "--step", STEP],
        cwd=ROOT,
        env=outside_the_ci(),
        capture_output=True,
        encoding="utf-8",
        check=True,
    )
    shown = " ".join(explained.stdout.split())

    assert "*The projects of projects.toml in the READMEs*" in shown
    assert "python3 -I .github/mkdocs_project.py --write" in shown
    assert "README.md#the-checks-of-this-website" in shown


def test_the_check_of_the_built_website_has_two_parts() -> None:
    assert headings(SITE_SCRIPT) == [
        "What the hooks of this website promise in its files",
        "The hub in a browser",
    ]


def test_the_browser_tests_have_five_scenarios() -> None:
    assert scenarios() == [
        "The search finds a project website",
        "The old addresses lead to the new folder",
        "The 404 page suggests a project",
        "The live facts fill the cards and the Trust table",
        "The language switch leads to the German home page",
    ]


@pytest.mark.parametrize("heading", headings(SITE_SCRIPT))
def test_the_explanation_of_docs_names_each_part_by_its_heading(heading: str) -> None:
    assert f"*{heading}*:" in text(docs(), "problem")


@pytest.mark.parametrize("title", scenarios())
def test_the_explanation_of_docs_names_each_scenario_by_its_title(title: str) -> None:
    assert f"*{title}*" in text(docs(), "problem")


def test_the_explanation_of_docs_checks_the_website_as_the_check_does() -> None:
    page, anchor = docs()["docs"].split("#")
    titles = re.findall(r"^#+ (.+)$", (ROOT / page).read_text(encoding="utf-8"), re.M)

    assert docs()["commands"][-1] == "bash scripts/check-site.sh site"
    assert page == "README.md"
    assert anchor in {title.lower().replace(" ", "-") for title in titles}


# The explanation of docs replaces the one of the blueprint as a whole, so it keeps
# what the blueprint tells about the parts of the check that this website shares.
BLUEPRINT_PHRASES = [
    ("problem", "1,200 KB"),
    ("problem", "also those written in HTML"),
    ("problem", "the cache of the week"),
    ("fix", "bash scripts/diagrams.sh --extract"),
]


@pytest.mark.parametrize(("name", "phrase"), BLUEPRINT_PHRASES)
def test_the_explanation_of_docs_keeps_what_the_blueprint_tells(name: str, phrase: str) -> None:
    blueprint = tomllib.loads((ROOT / ".github/checks.toml").read_text(encoding="utf-8"))

    assert phrase in text(blueprint["check"]["docs"], name)
    assert phrase in text(docs(), name)


def test_the_coach_explains_the_check_docs_in_the_words_of_this_project() -> None:
    explained = subprocess.run(
        [sys.executable, ".github/blueprint.py", "coach", "explain", "docs"],
        cwd=ROOT,
        env=outside_the_ci(),
        capture_output=True,
        encoding="utf-8",
        check=True,
    )
    shown = " ".join(explained.stdout.split())

    assert "*The hub in a browser*" in shown
    assert "bash scripts/check-site.sh site" in shown
    assert "README.md#the-hub-in-a-browser" in shown
