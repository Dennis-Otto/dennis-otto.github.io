#!/usr/bin/env bash
# Takes the pictures of the website at the top of README.md: its home page as a
# reader first sees it, 1280×800 pixels, in the light colors as
# docs/images/website-light.png and in the dark ones as docs/images/website-dark.png.
# README.md shows the one of the reader's color scheme. Run it after a change of the
# home page, of its projects or of the theme, and describe what the pictures show in
# the alt of the picture in README.md, which a test checks against the first group:
#   bash scripts/screenshots.sh
# The same website makes the same pictures, byte for byte, so a run without such a
# change changes nothing: git diff --exit-code docs/images/website-*.png
#
# It builds the website strictly, as the check docs does, with MkDocs from the tools
# of the website in .venv-docs, which CONTRIBUTING.md sets up. And it needs Docker:
# a web server and the headless Chromium of Playwright's image, which
# scripts/social-preview.sh uses too, show the website without a network, so that no
# other server can change a picture, and without motion.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

mkdocs=""
for candidate in .venv-docs/bin/mkdocs .venv-docs/Scripts/mkdocs.exe; do
  if [[ -x "$candidate" ]]; then
    mkdocs="$candidate"
    break
  fi
done
if [[ -z "$mkdocs" ]]; then
  echo "MkDocs is missing: set up the tools of the website in .venv-docs, as CONTRIBUTING.md describes." >&2
  exit 1
fi

# The image of scripts/social-preview.sh, which Renovate keeps current.
image="$(sed -n 's/^FROM //p' .github/social-preview/Dockerfile)"
# Git Bash on Windows mounts the Windows path.
root="$(pwd -W 2>/dev/null || pwd)"
# The website goes to a folder that git ignores, inside the one the container mounts.
site=.cache/screenshots
png="$(mktemp)"
log="$(mktemp)"
trap 'rm -rf "$site" "$png" "$log"' EXIT

rm -rf "$site"
NO_MKDOCS_2_WARNING=true "$mkdocs" build --strict --quiet --site-dir "$site"

# shoot <picture> <scheme>: the home page in the color scheme that Chromium tells the
# page the reader prefers, 0 for dark and 1 for light, as the theme follows it. A web
# server on the loopback of the container serves the website, as GitHub Pages does,
# and the PNG leaves the container through stdout, so it belongs to whoever runs
# this. Git Bash on Windows keeps the paths of the container as they are.
shoot() {
  local picture="$1" scheme="$2"
  if ! MSYS_NO_PATHCONV=1 docker run --rm --network none --volume "$root:/work:ro" "$image" sh -c '
    cd "/work/$1" && python3 -m http.server --bind 127.0.0.1 8000 >/dev/null 2>&1 &
    tries=0
    until python3 -c "import urllib.request; urllib.request.urlopen(\"http://127.0.0.1:8000/\")" 2>/dev/null; do
      tries=$((tries + 1))
      [ "$tries" -lt 100 ] || exit 1
      sleep 0.1
    done
    /ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell \
      --no-sandbox --hide-scrollbars --force-device-scale-factor=1 --window-size=1280,800 \
      --blink-settings=preferredColorScheme="$2" --force-prefers-reduced-motion \
      --virtual-time-budget=10000 --screenshot=/tmp/website.png http://127.0.0.1:8000/ >&2 &&
      cat /tmp/website.png' sh "$site" "$scheme" >"$png" 2>"$log" || [[ ! -s "$png" ]]; then
    cat "$log" >&2
    echo "Taking $picture failed." >&2
    exit 1
  fi
  cp "$png" "$picture"
  echo "Took $picture ($(wc -c <"$picture") bytes)."
}

mkdir -p docs/images
shoot docs/images/website-light.png 1
shoot docs/images/website-dark.png 0
