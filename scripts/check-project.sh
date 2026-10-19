#!/usr/bin/env bash
# The checks of this website alone, which scripts/check.sh runs last: the tests of
# the script of the live facts of the home pages, docs/javascripts/projects.js, the
# table of the projects in README.md against projects.toml, and the tests of the
# hooks of the website in .github/mkdocs_project.py, with every line and branch
# covered.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

printf '
== %s
' "Tests of the script of the live facts"
# Node 20 or newer runs them with its own test runner, without a package to install.
# The runners of the CI have it, so there a missing one is an error.
if command -v node >/dev/null 2>&1 &&
  node -e 'process.exit(Number(process.versions.node.split(".")[0]) < 20 ? 1 : 0)' >/dev/null 2>&1; then
  node --test --test-reporter=spec tests/*.test.mjs
elif [[ -n "${CI:-}" ]]; then
  echo "Node 20 or newer is missing." >&2
  exit 1
else
  echo "Node 20 or newer is not installed here; the CI runs the tests of the script."
fi

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
# own. It is made anew when the lock file changes, when another Python runs this
# script (another version, or Linux in a container on the same work tree), or when
# the Python that made it is gone.
venv=.cache/test-venv
bin="$venv/$("$python" -c 'import sys; print("Scripts" if sys.platform == "win32" else "bin", end="")')"
stamp="$(
  cat requirements-test.txt
  "$python" -c 'import sys; print(sys.version, sys.platform, sys.executable, end="")'
)"
if [[ "$stamp" != "$(cat "$venv/stamp" 2>/dev/null)" ]] || ! "$bin/python" -c '' >/dev/null 2>&1; then
  rm -rf "$venv"
  "$python" -m venv "$venv"
  "$bin/python" -m pip install --quiet --disable-pip-version-check --no-input \
    --require-hashes -r requirements-test.txt
  printf '%s\n' "$stamp" >"$venv/stamp"
fi
export COVERAGE_FILE=.cache/coverage
"$bin/python" -m coverage run --branch -m pytest -p no:cacheprovider -W error tests
"$bin/python" -m coverage report --fail-under=100 --show-missing
