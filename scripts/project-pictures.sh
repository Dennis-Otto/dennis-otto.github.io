#!/usr/bin/env bash
# Makes the picture on top of each card of the home page, in every language, as a
# WebP of 640×320 pixels at the place in docs/ that image of projects.toml names,
# with a .license file beside it that names the license of the repository of the
# project, which is that of the picture too:
# - The picture of the first language comes from the social preview of the
#   repository, its .github/social-preview.png on main, 1280×640 pixels.
# - The social preview speaks the first language alone, so the hub draws the
#   picture of every other language that has an image of its own:
#   .github/card-picture.html with the name and the tagline of the project in that
#   language beside the screenshot of its repository that drawing of projects.toml
#   names, which the Chromium of scripts/social-preview.sh renders at 1280×640.
# scripts/screenshots.sh runs it first, so the screenshot bot renews every picture
# whose preview or screenshot changed, every week, after every release and on
# demand; the alt texts of projects.toml say what every picture keeps, so they stay
# true. Run it yourself for the pictures of a new card:
#   bash scripts/project-pictures.sh
# The same previews and screenshots make the same pictures, byte for byte, so a run
# without a new one changes nothing: git diff --exit-code docs/images/projects
#
# It needs curl and Pillow from the tools of the website in .venv-docs, which
# CONTRIBUTING.md sets up, and Docker for the pictures that the hub draws.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

python=""
for candidate in .venv-docs/bin/python .venv-docs/Scripts/python.exe; do
  if [[ -x "$candidate" ]]; then
    python="$candidate"
    break
  fi
done
if [[ -z "$python" ]] || ! "$python" -c 'import PIL' >/dev/null 2>&1; then
  echo "Pillow is missing: set up the tools of the website in .venv-docs, as CONTRIBUTING.md describes." >&2
  exit 1
fi

# The image of scripts/social-preview.sh, which Renovate keeps current. Docker runs
# its amd64 build on every machine, emulated on ARM, because the Chromium of its
# arm64 build draws other bytes and lives in another folder.
image="$(sed -n 's/^FROM //p' .github/social-preview/Dockerfile)"
# Git Bash on Windows mounts the Windows path.
root="$(pwd -W 2>/dev/null || pwd)"
# The pages of the drawn pictures with their screenshots and logos go to a folder
# that git ignores, inside the one the container mounts.
work=.cache/pictures
png="$(mktemp)"
log="$(mktemp)"
trap 'rm -rf "$work" "$png" "$log"' EXIT

# fetch <address> <file>: a file of a repository, or a failure that names it.
fetch() {
  curl --fail --silent --show-error --location --retry 3 --connect-timeout 10 --max-time 60 --output "$2" "$1"
}

# card <png> <picture> <repo> <license>: the PNG of 1280×640 as the picture of a
# card, with the .license file that names the license of the repository.
card() {
  mkdir -p "$(dirname "$2")"
  # Cut to the proportions of a card, scaled down sharply, as a lossy WebP of
  # quality 80 with the slowest and smallest encoding, and without metadata.
  "$python" -I -B - "$1" "$2" <<'PY'
import sys

from PIL import Image, ImageOps

sys.path.insert(0, ".github")
from mkdocs_project import PICTURE

source, picture = sys.argv[1:]
with Image.open(source) as image:
    card = ImageOps.fit(image.convert("RGB"), PICTURE, Image.Resampling.LANCZOS)
card.save(picture, "WEBP", quality=80, method=6)
PY
  # REUSE-IgnoreStart
  printf 'SPDX-FileCopyrightText: Dennis Otto and the contributors to %s\nSPDX-License-Identifier: %s\n' \
    "$3" "$4" >"$2.license"
  # REUSE-IgnoreEnd
}

# The pictures of the first language: the repository, the picture and the license
# of every card with a repository, with the line ends of Unix, which Python on
# Windows writes as CR LF.
pictures="$("$python" -I -B .github/mkdocs_project.py --pictures | tr -d '\r')"
while read -r repo picture license; do
  [[ -n "$repo" ]] || continue
  url="https://raw.githubusercontent.com/$repo/main/.github/social-preview.png"
  fetch "$url" "$png"
  card "$png" "$picture" "$repo" "$license"
  echo "$picture ($(wc -c <"$picture") bytes) from $url"
done <<<"$pictures"

# The pictures that the hub draws: the hooks write the page of each into the work
# folder and list it with the address and the file of its screenshot and of its
# logo, or - for both where the page shows the icon of the card.
rm -rf "$work"
drawings="$("$python" -I -B .github/mkdocs_project.py --drawings "$work" | tr -d '\r')"
while read -r repo picture license page screenshot shot logo mark; do
  [[ -n "$repo" ]] || continue
  fetch "$screenshot" "$shot"
  if [[ "$logo" != - ]]; then
    fetch "$logo" "$mark"
  fi
  # The page, 1280×640 like a social preview, with the fonts of the previews from
  # Google Fonts; the PNG leaves the container through stdout, so it belongs to
  # whoever runs this. Git Bash on Windows keeps the paths of the container as
  # they are.
  if ! MSYS_NO_PATHCONV=1 docker run --rm --platform linux/amd64 --volume "$root:/work:ro" "$image" sh -c '
    /ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell \
      --no-sandbox --hide-scrollbars --force-device-scale-factor=1 --window-size=1280,640 \
      --virtual-time-budget=10000 --screenshot=/tmp/picture.png "file:///work/$1" >&2 &&
      cat /tmp/picture.png' sh "$page" >"$png" 2>"$log" || [[ ! -s "$png" ]]; then
    cat "$log" >&2
    echo "Drawing $picture from $page failed." >&2
    exit 1
  fi
  card "$png" "$picture" "$repo" "$license"
  echo "$picture ($(wc -c <"$picture") bytes) drawn with $screenshot"
done <<<"$drawings"
