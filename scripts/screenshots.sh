#!/usr/bin/env bash
# Renews the pictures of the cards and takes those of the website that README.md and
# the About pages show. First, scripts/project-pictures.sh makes the picture of every
# card anew from the social preview of its repository on main, so that a card follows
# the preview of its project. Then scripts/screenshots.py takes, in the light and in
# the dark colors, each as a reader first sees it:
# - the home page at 1280×800 pixels, docs/images/website-light.png and
#   website-dark.png, at the top of README.md;
# - the home page on a phone, 375×812, docs/images/website-phone-*.webp, and the
#   Trust page, docs/images/website-trust-*.webp, which README.md shows as well;
# - the search of every project, docs/images/search-*.webp: an animation of a reader
#   who types token into the search box of the home page, whose results come from
#   the websites of several projects, and chooses the first of them, with its last
#   frame as a still, search-still-*.webp, for a reader who prefers reduced motion.
#   search-*.de.webp are the same of the German home page, which the website shows
#   on the German About page in place of the English ones. README.md and the About
#   pages show them.
# README.md and the pages show the picture of the reader's color scheme. The
# screenshot bot runs this script every week, after every release, on demand and
# after a change of main that touches a file of .github/screenshots-paths.txt, and
# its pull request from bot/screenshots brings every picture whose pixels changed.
# Run it yourself to see what a change of the website, of its projects or of the
# theme changes, and describe what the pictures show in their alt texts, which a
# test checks against the first group of the home page:
#   bash scripts/screenshots.sh
# The same previews and the same website make the same pictures, byte for byte, so a
# run without such a change changes nothing:
#   git diff --exit-code docs/images
#
# It fetches the social previews from GitHub with curl and Pillow, builds the website
# strictly, as the check docs does, with MkDocs, and turns the screenshots into WebPs
# with Pillow: all from the tools of the website in .venv-docs, which CONTRIBUTING.md
# sets up. And it needs Docker: a web server and the headless Chromium of
# Playwright's image, which scripts/social-preview.sh uses too, show the website
# without a network, so that no other server can change a picture, and without
# motion.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

mkdocs=""
for candidate in .venv-docs/bin/mkdocs .venv-docs/Scripts/mkdocs.exe; do
  if [[ -x "$candidate" ]]; then
    mkdocs="$candidate"
    break
  fi
done
python=""
for candidate in .venv-docs/bin/python .venv-docs/Scripts/python.exe; do
  if [[ -x "$candidate" ]]; then
    python="$candidate"
    break
  fi
done
if [[ -z "$mkdocs" || -z "$python" ]] || ! "$python" -c 'import PIL' >/dev/null 2>&1; then
  echo "MkDocs or Pillow is missing: set up the tools of the website in .venv-docs, as CONTRIBUTING.md describes." >&2
  exit 1
fi

# The image of scripts/social-preview.sh, which Renovate keeps current. Docker runs
# its amd64 build on every machine, emulated on ARM, because the Chromium of its
# arm64 build draws other bytes and lives in another folder.
image="$(sed -n 's/^FROM //p' .github/social-preview/Dockerfile)"
# Git Bash on Windows mounts the Windows path.
root="$(pwd -W 2>/dev/null || pwd)"
# The website goes to a folder that git ignores, inside the one the container mounts.
site=.cache/screenshots
shots="$(mktemp -d)"
archive="$(mktemp)"
log="$(mktemp)"
trap 'rm -rf "$site" "$shots" "$archive" "$log"' EXIT

# The pictures of the cards first, so that the pictures below show them as the
# website will.
bash scripts/project-pictures.sh

rm -rf "$site"
NO_MKDOCS_2_WARNING=true "$mkdocs" build --strict --quiet --site-dir "$site"

# A web server on the loopback of the container serves the website, as GitHub Pages
# does, and scripts/screenshots.py takes every picture with the Chromium of the
# image. The PNGs leave the container as a tar archive through stdout, so they
# belong to whoever runs this. Git Bash on Windows keeps the paths of the container
# as they are.
if ! MSYS_NO_PATHCONV=1 docker run --rm --platform linux/amd64 --network none --volume "$root:/work:ro" "$image" sh -c '
  cd "/work/$1" && python3 -m http.server --bind 127.0.0.1 8000 >/dev/null 2>&1 &
  tries=0
  until python3 -c "import urllib.request; urllib.request.urlopen(\"http://127.0.0.1:8000/\")" 2>/dev/null; do
    tries=$((tries + 1))
    [ "$tries" -lt 100 ] || exit 1
    sleep 0.1
  done
  python3 -I -B /work/scripts/screenshots.py \
    /ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell \
    http://127.0.0.1:8000 /tmp/pictures >&2 &&
    tar -C /tmp/pictures -cf - .' sh "$site" >"$archive" 2>"$log" || [[ ! -s "$archive" ]]; then
  cat "$log" >&2
  echo "Taking the pictures of the website failed." >&2
  exit 1
fi
tar -xf "$archive" -C "$shots"

# The pictures from the PNGs of Chromium: the two at the top of README.md as they
# are, every other one as a lossless WebP, about half the size of its PNG, and the
# frames of a search as an animated WebP that loops, with its last frame as the
# still beside it. Lossless, so that the text stays sharp and the pixels are those
# of the screenshots, with the slowest and smallest encoding and without metadata.
"$python" -I -B - "$shots" docs/images <<'PY'
import json
import sys
from pathlib import Path

from PIL import Image

shots, images = (Path(argument) for argument in sys.argv[1:])
PNG = {"website-light.png", "website-dark.png"}
WEBP = {"format": "WEBP", "lossless": True, "quality": 100, "method": 6}


def took(picture):
    print(f"Took {picture.as_posix()} ({picture.stat().st_size} bytes).")


for shot in sorted(shots.glob("*.png")):
    name = shot.name
    picture = images / name
    if name in PNG:
        picture.write_bytes(shot.read_bytes())
    else:
        picture = picture.with_suffix(".webp")
        with Image.open(shot) as image:
            image.convert("RGB").save(picture, **WEBP)
    took(picture)

for listing in sorted(shots.glob("*/frames.json")):
    shows = json.loads(listing.read_text(encoding="utf-8"))
    frames = []
    for file, _ in shows:
        with Image.open(listing.parent / file) as frame:
            frames.append(frame.convert("RGB"))
    name = listing.parent.name
    animation = images / f"{name}.webp"
    # The still of search-light.de is search-still-light.de.webp.
    stem, _, scheme = name.rpartition("-")
    still = images / f"{stem}-still-{scheme}.webp"
    frames[0].save(
        animation,
        save_all=True,
        append_images=frames[1:],
        duration=[milliseconds for _, milliseconds in shows],
        loop=0,
        **WEBP,
    )
    frames[-1].save(still, **WEBP)
    took(animation)
    took(still)
PY
