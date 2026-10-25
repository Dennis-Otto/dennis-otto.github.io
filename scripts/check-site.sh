#!/usr/bin/env bash
# The checks of this website alone on the website that MkDocs built, which the check
# docs runs after the strict build with the folder of the website, site. First what the
# hooks of .github/mkdocs_project.py promise in the files that they alone write or
# change after the build, such as security.txt, robots.txt, the pages at the old
# addresses of a renamed project, the cards of the home pages and the search of every
# project. Then the hub in a browser: tests/e2e/hub.mjs opens the website in Chrome at
# the width of a phone and of a desktop and uses its search across every project, its
# old addresses, the suggestions of its 404 page, its live facts and its language
# switch. Each broken promise and each failed scenario is a line with what broke and
# where, and in the CI an annotation too; both parts run, so that a run names everything
# to fix. On your machine, after a build into site:
#   .venv-docs/bin/mkdocs build --strict
#   bash scripts/check-site.sh site
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: bash scripts/check-site.sh SITE, the folder of the built website, such as site." >&2
  exit 2
fi
root="$(dirname "${BASH_SOURCE[0]}")/.."
status=0

printf '\n== %s\n' "What the hooks of this website promise in its files"
# Python 3.11 or newer, for tomllib: python3, or python as on Windows.
python=""
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1 &&
    "$candidate" -c 'import sys; sys.exit(sys.version_info < (3, 11))' >/dev/null 2>&1; then
    python="$candidate"
    break
  fi
done
if [[ -n "$python" ]]; then
  # The standard library alone, as the hooks need nothing else to check the files;
  # the texts of the projects in every console, and no __pycache__ beside the code.
  PYTHONIOENCODING=utf-8 PYTHONDONTWRITEBYTECODE=1 \
    "$python" -I "$root/.github/mkdocs_project.py" --site "$1" || status=1
elif [[ -n "${CI:-}" ]]; then
  # The runners of the CI have Python, so there a missing one is an error.
  echo "Python 3.11 or newer is missing." >&2
  status=1
else
  echo "Python 3.11 or newer is not installed here; the CI checks the files of the website."
fi

printf '\n== %s\n' "The hub in a browser"
# Node 20 or newer, which playwright-core needs, with the tool of the lock file of
# tests/e2e/, which npm installs anew when the lock file changes; the scenarios drive
# the Google Chrome of the runner. The runners of the CI have both, so there a missing
# Node is an error, and so is a missing Chrome, which tests/e2e/hub.mjs names.
e2e="$root/tests/e2e"
if node -e 'process.exit(Number(process.versions.node.split(".")[0]) >= 20 ? 0 : 1)' >/dev/null 2>&1; then
  stamp="$e2e/node_modules/.installed-from-package-lock.json"
  if ! cmp -s "$e2e/package-lock.json" "$stamp"; then
    npm ci --prefix "$e2e" --ignore-scripts --no-audit --no-fund --loglevel=error
    cp "$e2e/package-lock.json" "$stamp"
  fi
  node "$e2e/hub.mjs" "$1" || status=1
elif [[ -n "${CI:-}" ]]; then
  echo "Node 20 or newer is missing, which runs the browser tests of the hub." >&2
  status=1
else
  echo "Node 20 or newer is not installed here; the CI runs the browser tests of the hub."
fi
exit "$status"
