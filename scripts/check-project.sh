#!/usr/bin/env bash
# The checks of this website alone, which scripts/check.sh runs last: the tests of
# the scripts of the website, docs/javascripts/projects.js with the live facts of the
# home pages and the scripts that its templates include inline from
# overrides/partials/, with every line, branch and function covered; the format and
# the rules of that JavaScript, which Biome checks with the settings of biome.jsonc;
# the tables of the projects in README.md and README.de.md against projects.toml; the
# format, the rules and the types of the Python, which Ruff checks with the settings
# of ruff.toml and mypy in its strict mode with those of mypy.ini; and the tests of
# the hooks of the website in .github/mkdocs_project.py and .github/hub/, with every
# line and branch covered.
#
# With --fix, it checks nothing and fixes what Biome and Ruff can fix instead, as the
# fix bot does on a pull request: bash scripts/check-project.sh --fix
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

fix=false
if [[ "${1:-}" == --fix ]]; then
  fix=true
fi

# Node 22.8 or newer, which runs the tests of the scripts and measures what they
# cover without a package to install.
node=false
if command -v node >/dev/null 2>&1 &&
  node -e 'const [major, minor] = process.versions.node.split(".").map(Number);
    process.exit(major > 22 || (major === 22 && minor >= 8) ? 0 : 1)' >/dev/null 2>&1; then
  node=true
fi

# Biome of the lock file of tests/lint/, which npm installs anew when the lock file
# changes, as scripts/check-site.sh installs the tool of the browser tests.
biome() {
  local lint=tests/lint
  local stamp="$lint/node_modules/.installed-from-package-lock.json"
  if ! cmp -s "$lint/package-lock.json" "$stamp"; then
    # The stamp only after a whole install: --fix calls this function on the left of
    # ||, where set -e stops nothing.
    npm ci --prefix "$lint" --ignore-scripts --no-audit --no-fund --loglevel=error || return 1
    cp "$lint/package-lock.json" "$stamp" || return 1
  fi
  "$lint/node_modules/.bin/biome" "$@"
}

# Python 3.11 or newer, for tomllib: python3, or python as on Windows.
python=""
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1 &&
    "$candidate" -c 'import sys; sys.exit(sys.version_info < (3, 11))' >/dev/null 2>&1; then
    python="$candidate"
    break
  fi
done
# The texts of the projects in every console, and no __pycache__ beside the code.
export PYTHONIOENCODING=utf-8 PYTHONDONTWRITEBYTECODE=1

# The hash-pinned tools of requirements-test.txt, in a virtual environment of their
# own: pytest and coverage, Ruff and mypy. It is made anew when the lock file changes,
# when another Python runs this script (another version, or Linux in a container on
# the same work tree), or when the Python that made it is gone.
venv=.cache/test-venv
bin=""
tools() {
  bin="$venv/$("$python" -c 'import sys; print("Scripts" if sys.platform == "win32" else "bin", end="")')"
  local stamp
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
}

if [[ "$fix" == true ]]; then
  # Each tool fixes what it can, and the next runs all the same; the script ends with
  # an error while a finding stays for a person, which the checks then name.
  status=0
  if [[ "$node" == true ]]; then
    biome check --write . || status=1
  else
    echo "Node 22.8 or newer is not installed here, which fixes the JavaScript with Biome."
  fi
  if [[ -n "$python" ]]; then
    tools
    "$bin/ruff" check --fix . || status=1
    "$bin/ruff" format . || status=1
  else
    echo "Python 3.11 or newer is not installed here, which fixes the Python with Ruff."
  fi
  exit "$status"
fi

printf '\n== %s\n' "Tests of the scripts of the website, with every line, branch and function covered"
# Node runs them with its own test runner and measures what they cover; a coverage
# below 100 % fails the step and names the lines of each file that no test runs. The
# runners of the CI have it, so there a missing one is an error.
if [[ "$node" == true ]]; then
  echo "Node $(node --version)"
  node --test --test-reporter=spec --experimental-test-coverage \
    --test-coverage-include='docs/javascripts/*.js' \
    --test-coverage-include='overrides/partials/*.js' \
    --test-coverage-lines=100 --test-coverage-branches=100 --test-coverage-functions=100 \
    tests/*.test.mjs
elif [[ -n "${CI:-}" ]]; then
  echo "Node 22.8 or newer is missing, which runs the tests of the scripts and measures what they cover." >&2
  exit 1
else
  echo "Node 22.8 or newer is not installed here; the CI runs the tests of the scripts, with every line, branch and function covered."
fi

printf '\n== %s\n' "The format and the rules of the JavaScript"
# Biome, with the settings of biome.jsonc: a warning fails as well, and in the CI each
# finding is an annotation at its line too.
if [[ "$node" == true ]]; then
  biome ci --error-on-warnings .
elif [[ -n "${CI:-}" ]]; then
  echo "Node 22.8 or newer is missing, which checks the JavaScript with Biome." >&2
  exit 1
else
  echo "Node 22.8 or newer is not installed here; the CI checks the format and the rules of the JavaScript."
fi

if [[ -z "$python" ]]; then
  # The runners of the CI have Python, so there a missing one is an error.
  if [[ -n "${CI:-}" ]]; then
    echo "Python 3.11 or newer is missing." >&2
    exit 1
  fi
  echo "Python 3.11 or newer is not installed here; the CI checks the projects and the Python and runs the tests."
  exit 0
fi

printf '\n== %s\n' "The projects of projects.toml in the READMEs"
"$python" -I .github/mkdocs_project.py --check

printf '\n== %s\n' "The format, the rules and the types of the Python"
# Ruff with the settings of ruff.toml, and mypy in its strict mode with those of
# mypy.ini. In the CI, each finding is an annotation at its line as well: Ruff writes
# its own, and blueprint.py annotate those of mypy.
tools
"$bin/ruff" format --check --diff .
if [[ "${GITHUB_ACTIONS:-}" == true ]]; then
  "$bin/ruff" check --output-format=github .
  "$bin/mypy" --no-pretty --show-error-end 2>&1 | "$bin/python" .github/blueprint.py annotate mypy
else
  "$bin/ruff" check .
  "$bin/mypy"
fi

printf '\n== %s\n' "Tests of the hooks of the website, with every line and branch covered"
export COVERAGE_FILE=.cache/coverage
# tests/test_catalog_pull_request.py runs scripts/catalog-pull-request.sh in bash
# with jq, as the job of the Catalog workflow does. The runners of the CI have jq, so
# there a missing one is an error; here it leaves only those tests to the CI.
others=()
if ! command -v jq >/dev/null 2>&1; then
  if [[ -n "${CI:-}" ]]; then
    echo "jq is missing, which the tests of scripts/catalog-pull-request.sh need." >&2
    exit 1
  fi
  echo "jq is not installed here; the CI runs tests/test_catalog_pull_request.py, the tests of scripts/catalog-pull-request.sh."
  others=(--ignore=tests/test_catalog_pull_request.py)
fi
"$bin/python" -m coverage run --branch -m pytest -p no:cacheprovider -W error "${others[@]}" tests
"$bin/python" -m coverage report --fail-under=100 --show-missing
