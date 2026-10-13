#!/usr/bin/env bash
# The checks of this website alone, which scripts/check.sh runs last: the table of
# the projects in README.md against projects.toml, and the tests of the hooks of the
# website in .github/mkdocs_project.py, with every line and branch covered.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

# Python 3.11 or newer, for tomllib: python3, or python as on Windows.
python=""
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1 &&
    "$candidate" -c 'import sys; sys.exit(sys.version_info < (3, 11))' >/dev/null 2>&1; then
    python="$candidate"
    break
  fi
done
if [[ -z "$python" ]]; then
  # The runners of the CI have Python, so there a missing one is an error.
  if [[ -n "${CI:-}" ]]; then
    echo "Python 3.11 or newer is missing." >&2
    exit 1
  fi
  echo "Python 3.11 or newer is not installed here; the CI checks the projects and runs the tests."
  exit 0
fi
# The texts of the projects in every console, and no __pycache__ beside the code.
export PYTHONIOENCODING=utf-8 PYTHONDONTWRITEBYTECODE=1

printf '\n== %s\n' "The projects of projects.toml in README.md"
"$python" -I .github/mkdocs_project.py --check

printf '\n== %s\n' "Tests of the hooks of the website, with every line and branch covered"
# The hash-pinned tools of requirements-test.txt, in a virtual environment of their
# own that is made anew when the lock file changes.
venv=.cache/test-venv
fresh=false
if ! cmp -s requirements-test.txt "$venv/requirements-test.txt"; then
  rm -rf "$venv"
  "$python" -m venv "$venv"
  fresh=true
fi
bin="$venv/bin"
if [[ -d "$venv/Scripts" ]]; then
  bin="$venv/Scripts"
fi
if [[ "$fresh" == true ]]; then
  "$bin/python" -m pip install --quiet --disable-pip-version-check --no-input \
    --require-hashes -r requirements-test.txt
  cp requirements-test.txt "$venv/requirements-test.txt"
fi
export COVERAGE_FILE=.cache/coverage
"$bin/python" -m coverage run --branch -m pytest -p no:cacheprovider -W error tests
"$bin/python" -m coverage report --fail-under=100 --show-missing
