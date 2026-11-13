"""Tests of scripts/catalog-pull-request.sh, the shell of the job catalog-pull-request
of .github/workflows/catalog.yml, which opens, updates or closes the one pull request
of the catalog bot. The script runs in bash against a fake gh on the PATH, which
answers as GitHub does, keeps the branches of the repository in a folder and puts
its answers through the --jq of each call with the real jq, so the filters of the
script run as they do on GitHub. Each run that the workflow can make has its test:
a new pull request, an update of an open one, an open one with a commit of a person,
one of a fork, a file outside the allow-list, and no edits with and without an open
pull request (#205)."""

from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from hub_helpers import ROOT

SCRIPT = ROOT / "scripts/catalog-pull-request.sh"
REPOSITORY = "Dennis-Otto/dennis-otto.github.io"
# The app and the id of its account, as GitHub names them for the release app.
SLUG = "dennis-otto-release-automation"
BOT_ID = 321826887
BRANCH = "bot/catalog"
HEADLINE = "docs: bring the project catalog up to date"
SHA = "4f2a0c3e9b8d7a6f5e4d3c2b1a0f9e8d7c6b5a49"
URL = f"https://github.com/{REPOSITORY}/actions/runs/1234"
# The commit that createCommitOnBranch makes, by the fake gh.
COMMIT = "c0ffee0000000000000000000000000000000042"
PULL_REQUEST = "The catalog bot fixes what it can.\n"

# The fake gh. Each call goes into a file of its own in calls/, its arguments
# separated by NUL, and the file of --input or --body-file beside it; a branch of the
# repository is a file in refs/ with its commit, its name with % for /.
FAKE_GH = r"""#!/usr/bin/env bash
set -euo pipefail
shopt -s nullglob
made=("$FAKE_GH"/calls/*.args)
call="$FAKE_GH/calls/${#made[@]}"
printf '%s\0' "$@" >"$call.args"
filter=""
args=()
while (($#)); do
  case "$1" in
    --jq) filter="$2"; shift 2 ;;
    --input | --body-file) cp "$2" "$call.input"; args+=("$1" "$2"); shift 2 ;;
    *) args+=("$1"); shift ;;
  esac
done
ref() { printf '%s/refs/%s' "$FAKE_GH" "${1//\//%}"; }
answer() {
  case "${args[0]} ${args[1]}" in
    "pr list") cat "$FAKE_GH/pr-list.json" ;;
    "pr view") cat "$FAKE_GH/pr-view.json" ;;
    "pr create") echo "https://github.com/$GH_REPO/pull/42" ;;
    "pr edit" | "pr close") ;;
    "api graphql") echo '{"data":{"createCommitOnBranch":{"commit":{"oid":"'"$COMMIT"'"}}}}' ;;
    "api users/$APP_SLUG[bot]") cat "$FAKE_GH/user.json" ;;
    "api repos/$GH_REPO/git/ref/heads/"*)
      if [[ ! -e "$(ref "${args[1]#*/git/ref/heads/}")" ]]; then
        echo '{"message":"Not Found","status":"404"}'
        echo "gh: Not Found (HTTP 404)" >&2
        exit 1
      fi
      echo '{}'
      ;;
    "api --method")
      case "${args[2]} ${args[3]}" in
        "POST repos/$GH_REPO/git/refs")
          name="${args[5]#ref=refs/heads/}"
          if [[ -e "$(ref "$name")" ]]; then
            echo "gh: Reference already exists (HTTP 422)" >&2
            exit 1
          fi
          printf '%s' "${args[7]#sha=}" >"$(ref "$name")"
          ;;
        "PATCH repos/$GH_REPO/git/refs/heads/"*)
          name="${args[3]#*/git/refs/heads/}"
          [[ -e "$(ref "$name")" ]] || exit 1
          printf '%s' "${args[5]#sha=}" >"$(ref "$name")"
          ;;
        "DELETE repos/$GH_REPO/git/refs/heads/"*)
          rm "$(ref "${args[3]#*/git/refs/heads/}")"
          ;;
        *) echo "The fake gh doesn't know: ${args[*]}" >&2; exit 2 ;;
      esac
      echo '{}'
      ;;
    *) echo "The fake gh doesn't know: ${args[*]}" >&2; exit 2 ;;
  esac
}
if [[ -n "$filter" ]]; then
  answer | jq --raw-output "$filter"
else
  answer
fi
"""


@dataclass
class Run:
    """What one run of the script did."""

    code: int
    log: str
    commands: list[str]
    inputs: list[str]
    refs: dict[str, str]
    output: str
    summary: str


def pull(number: int, *, login: str = f"app/{SLUG}", fork: bool = False) -> Any:
    """A pull request from the branch of the bot, as gh pr list lists it."""
    return {
        "author": {"is_bot": login.startswith("app/"), "login": login},
        "isCrossRepository": fork,
        "number": number,
    }


def commit(headline: str, login: str = f"{SLUG}[bot]") -> Any:
    """A commit of the pull request, as gh pr view shows it."""
    return {
        "authors": [
            {
                "email": f"{BOT_ID}+{login}@users.noreply.github.com",
                "id": "BOT_kgDOEy6wRw",
                "login": login,
                "name": login,
            }
        ],
        "messageHeadline": headline,
    }


def run(
    tmp_path: Path,
    edits: dict[str, str] | None,
    *,
    pulls: tuple[Any, ...] = (),
    commits: tuple[Any, ...] = (),
    refs: tuple[str, ...] = (),
    files: str | None = None,
) -> Run:
    """Runs the script as the step does, with the edits that the job catalog kept, or
    none, and the pull requests, the commits of the open one and the branches that
    GitHub has. files replaces the list of the paths of the edits."""
    fake = tmp_path / "fake"
    for folder in ("bin", "calls", "refs"):
        (fake / folder).mkdir(parents=True)
    gh = fake / "bin/gh"
    gh.write_text(FAKE_GH, encoding="utf-8", newline="\n")
    gh.chmod(0o755)
    (fake / "pr-list.json").write_text(json.dumps(list(pulls)), encoding="utf-8")
    (fake / "pr-view.json").write_text(
        json.dumps({"commits": list(commits)}), encoding="utf-8"
    )
    (fake / "user.json").write_text(
        json.dumps({"id": BOT_ID, "login": f"{SLUG}[bot]", "type": "Bot"}),
        encoding="utf-8",
    )
    for name in refs:
        (fake / "refs" / name.replace("/", "%")).write_text(SHA, encoding="utf-8")
    temp = tmp_path / "runner"
    kept = temp / "edits"
    (kept / "files").mkdir(parents=True)
    if edits is not None:
        for path, text in edits.items():
            (kept / "files" / path).parent.mkdir(parents=True, exist_ok=True)
            (kept / "files" / path).write_bytes(text.encode())
        listed = "".join(f"{path}\n" for path in edits) if files is None else files
        (kept / "files.txt").write_bytes(listed.encode())
        (kept / "pull-request.md").write_bytes(PULL_REQUEST.encode())
    output = temp / "output"
    summary = temp / "summary.md"
    environment = {
        **os.environ,
        "PATH": f"{fake / 'bin'}{os.pathsep}{os.environ['PATH']}",
        "FAKE_GH": str(fake),
        "COMMIT": COMMIT,
        "GH_TOKEN": "token-of-the-test",
        "GH_REPO": REPOSITORY,
        "APP_SLUG": SLUG,
        "BRANCH": BRANCH,
        "HEADLINE": HEADLINE,
        "EDITS": "true" if edits is not None else "",
        "ISSUE": "5",
        "SHA": SHA,
        "URL": URL,
        "RUNNER_TEMP": str(temp),
        "GITHUB_OUTPUT": str(output),
        "GITHUB_STEP_SUMMARY": str(summary),
    }
    bash = shutil.which("bash")
    assert bash is not None, "the tests of the script need bash"
    done = subprocess.run(
        [bash, str(SCRIPT)],
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    calls = sorted(
        (fake / "calls").glob("*.args"), key=lambda path: int(path.name.split(".")[0])
    )
    commands: list[str] = []
    inputs: list[str] = []
    for call in calls:
        args = call.read_text(encoding="utf-8").split("\0")[:-1]
        if "--jq" in args:
            del args[args.index("--jq") : args.index("--jq") + 2]
        commands.append(
            " ".join(
                "$RUNNER_TEMP" + arg[len(str(temp)) :].replace("\\", "/")
                if arg.startswith(str(temp))
                else arg
                for arg in args
            )
        )
        given = call.with_suffix(".input")
        inputs.append(given.read_text(encoding="utf-8") if given.exists() else "")
    return Run(
        code=done.returncode,
        log=done.stdout + done.stderr,
        commands=commands,
        inputs=inputs,
        refs={
            path.name.replace("%", "/"): path.read_text(encoding="utf-8")
            for path in (fake / "refs").iterdir()
        },
        output=output.read_text(encoding="utf-8") if output.exists() else "",
        summary=summary.read_text(encoding="utf-8") if summary.exists() else "",
    )


LIST = f"pr list --head {BRANCH} --state open --json number,isCrossRepository,author"
VIEW = "pr view 7 --json commits"
NEXT = f"{BRANCH}-next"
# The commit, the move of the branch and the end of the scratch branch, after the
# commands that differ.
COMMIT_ON_SCRATCH = [
    f"api --method POST repos/{REPOSITORY}/git/refs -f ref=refs/heads/{NEXT} -f sha={SHA}",
    f"api users/{SLUG}[bot]",
    "api graphql --input $RUNNER_TEMP/commit.json",
    f"api repos/{REPOSITORY}/git/ref/heads/{BRANCH}",
]
EDITS = {"projects.toml": 'slug = "tool"\n', "README.de.md": "# Größen\n"}


def test_the_bot_opens_a_pull_request_with_one_commit_of_its_edits(
    tmp_path: Path,
) -> None:
    done = run(tmp_path, EDITS)

    assert done.code == 0, done.log
    assert done.commands == [
        LIST,
        f"api repos/{REPOSITORY}/git/ref/heads/{NEXT}",
        *COMMIT_ON_SCRATCH,
        f"api --method POST repos/{REPOSITORY}/git/refs -f ref=refs/heads/{BRANCH} -f sha={COMMIT}",
        f"api --method DELETE repos/{REPOSITORY}/git/refs/heads/{NEXT}",
        f"pr create --base main --head {BRANCH} --title {HEADLINE} "
        "--body-file $RUNNER_TEMP/body.md",
    ]
    # The commit starts from the commit that was compared, on the scratch branch,
    # holds every edited file byte for byte and is signed off by the app's account.
    request = json.loads(done.inputs[4])
    assert request["query"] == (
        "mutation ($input: CreateCommitOnBranchInput!) "
        "{ createCommitOnBranch(input: $input) { commit { oid } } }"
    )
    assert request["variables"]["input"] == {
        "branch": {"repositoryNameWithOwner": REPOSITORY, "branchName": NEXT},
        "expectedHeadOid": SHA,
        "message": {
            "headline": HEADLINE,
            "body": f"Made by the catalog bot on {SHA}: {URL}\n\nSigned-off-by: "
            f"{SLUG}[bot] <{BOT_ID}+{SLUG}[bot]@users.noreply.github.com>",
        },
        "fileChanges": {
            "additions": [
                {"path": path, "contents": base64.b64encode(text.encode()).decode()}
                for path, text in EDITS.items()
            ]
        },
    }
    assert done.inputs[-1] == (
        f"{PULL_REQUEST}\nThe issue #5 lists every difference, those that need a "
        f"person too. This run made the commit: {URL}\n"
    )
    # Only the branch of the pull request is left, at the new commit.
    assert done.refs == {BRANCH: COMMIT}
    assert done.output == "number=42\n"
    assert done.summary == (
        f"The pull request of the catalog, #42 from {BRANCH}, has the commit {COMMIT}.\n"
    )


def test_the_bot_moves_its_open_pull_request_to_a_new_commit(tmp_path: Path) -> None:
    # The merge commit of the button "Update branch" names the person who clicked it,
    # and finishes nothing.
    commits = (
        commit(HEADLINE),
        commit("Merge branch 'main' into bot/catalog", "Dennis-Otto"),
    )

    done = run(tmp_path, EDITS, pulls=(pull(7),), commits=commits, refs=(BRANCH,))

    assert done.code == 0, done.log
    assert done.commands == [
        LIST,
        VIEW,
        f"api repos/{REPOSITORY}/git/ref/heads/{NEXT}",
        *COMMIT_ON_SCRATCH,
        f"api --method PATCH repos/{REPOSITORY}/git/refs/heads/{BRANCH} -f sha={COMMIT} -F force=true",
        f"api --method DELETE repos/{REPOSITORY}/git/refs/heads/{NEXT}",
        f"pr edit 7 --title {HEADLINE} --body-file $RUNNER_TEMP/body.md",
    ]
    assert done.refs == {BRANCH: COMMIT}
    assert done.output == "number=7\n"


@pytest.mark.parametrize("edits", [EDITS, None])
def test_the_bot_leaves_a_pull_request_with_a_commit_of_a_person_alone(
    tmp_path: Path, edits: dict[str, str] | None
) -> None:
    commits = (commit(HEADLINE), commit("Move the website of tool", "Dennis-Otto"))

    done = run(tmp_path, edits, pulls=(pull(7),), commits=commits, refs=(BRANCH,))

    assert done.code == 0, done.log
    # It neither commits nor closes, and the issue still names the pull request.
    assert done.commands == [LIST, VIEW]
    assert done.refs == {BRANCH: SHA}
    assert done.output == "number=7\n"
    assert done.summary == (
        "#7 has a commit of a person, so the bot leaves it as it is.\n"
    )


def test_the_bot_closes_its_pull_request_when_main_needs_no_edit(
    tmp_path: Path,
) -> None:
    done = run(tmp_path, None, pulls=(pull(7),), commits=(commit(HEADLINE),))

    assert done.code == 0, done.log
    assert done.commands == [
        LIST,
        VIEW,
        f"pr close 7 --delete-branch --comment `main` needs none of these edits any "
        f"more: {URL}",
    ]
    assert done.output == ""
    assert done.summary == "main needs no edit; closed #7.\n"


def test_without_edits_and_pull_request_the_bot_does_nothing(tmp_path: Path) -> None:
    done = run(tmp_path, None)

    assert done.code == 0, done.log
    assert done.commands == [LIST]
    assert done.output == ""
    assert done.summary == ""


def test_a_pull_request_of_a_fork_or_a_person_isnt_the_bots(tmp_path: Path) -> None:
    # A fork may open one from a branch of the same name, and a person from this
    # repository: the bot neither closes nor edits them, and opens its own.
    pulls = (pull(8, fork=True), pull(9, login="Dennis-Otto"))

    left = run(tmp_path / "left", None, pulls=pulls)
    opened = run(tmp_path / "opened", EDITS, pulls=pulls)

    assert left.code == 0, left.log
    assert left.commands == [LIST]
    assert opened.code == 0, opened.log
    assert opened.commands[1] != VIEW
    assert opened.commands[-1].startswith(f"pr create --base main --head {BRANCH} ")
    assert opened.output == "number=42\n"


def test_a_branch_that_a_failed_run_left_behind_starts_anew(tmp_path: Path) -> None:
    done = run(tmp_path, EDITS, refs=(NEXT,))

    assert done.code == 0, done.log
    assert done.commands[1:4] == [
        f"api repos/{REPOSITORY}/git/ref/heads/{NEXT}",
        f"api --method DELETE repos/{REPOSITORY}/git/refs/heads/{NEXT}",
        COMMIT_ON_SCRATCH[0],
    ]
    assert done.refs == {BRANCH: COMMIT}


@pytest.mark.parametrize(
    "path",
    [
        ".github/workflows/catalog.yml",
        "docs/decisions/README.md",
        "scripts/check.sh",
        "projects.toml.orig",
    ],
)
def test_an_edit_of_a_file_outside_the_allow_list_stops_the_bot(
    tmp_path: Path, path: str
) -> None:
    done = run(tmp_path, {**EDITS, path: "anything\n"}, refs=(BRANCH,))

    assert done.code == 1
    assert done.log == (
        f"{path}\n"
        "::error::The edits of the catalog bot hold the files above, which it never "
        "edits.\n"
    )
    # Nothing reaches the repository.
    assert done.commands == [LIST]
    assert done.refs == {BRANCH: SHA}
    assert done.output == ""


def test_edits_without_a_file_stop_the_bot(tmp_path: Path) -> None:
    done = run(tmp_path, {}, files="")

    assert done.code == 1
    assert done.log == (
        "::error::The catalog bot kept edits but names no file of them.\n"
    )
    assert done.commands == [LIST]
