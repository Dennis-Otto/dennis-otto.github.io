#!/usr/bin/env bash
# The checks of this website alone on the website that MkDocs built, which the check
# docs runs after the strict build with the folder of the website, site: what the
# hooks of .github/mkdocs_project.py promise in the files that they alone write or
# change after the build, such as security.txt, robots.txt, the pages at the old
# addresses of a renamed project, the cards of the home pages and the search of every
# project. Each broken promise is a line with the file and the fix, and in the CI an
# annotation too. On your machine, after a build into site:
#   .venv-docs/bin/mkdocs build --strict
#   bash scripts/check-site.sh site
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: bash scripts/check-site.sh SITE, the folder of the built website, such as site." >&2
  exit 2
fi
hooks="$(dirname "${BASH_SOURCE[0]}")/../.github/mkdocs_project.py"

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
  echo "Python 3.11 or newer is not installed here; the CI checks the website."
  exit 0
fi
# The texts of the projects in every console, and no __pycache__ beside the code.
export PYTHONIOENCODING=utf-8 PYTHONDONTWRITEBYTECODE=1

# The standard library alone, as the hooks need nothing else to check the files.
"$python" -I "$hooks" --site "$1"
