#!/usr/bin/env bash
# Makes the picture on top of each card of the home page from the social preview of
# the project's repository: its .github/social-preview.png on main, 1280×640 pixels,
# becomes a WebP of 640×320 at the place in docs/ that projects.toml names, with a
# .license file beside it that names the license of the repository, which is that
# of the picture too. Run it when a project has a new social preview, and describe
# the new picture in the alt texts of projects.toml:
#   bash scripts/project-pictures.sh
# The same previews make the same pictures, byte for byte, so a run without a new
# preview changes nothing: git diff --exit-code docs/images/projects
#
# It needs curl and Pillow from the tools of the website in .venv-docs, which
# CONTRIBUTING.md sets up.
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

# The repository, the picture and the license of every card with a repository, with
# the line ends of Unix, which Python on Windows writes as CR LF.
pictures="$("$python" -I -B .github/mkdocs_project.py --pictures | tr -d '\r')"
preview="$(mktemp)"
trap 'rm -f "$preview"' EXIT
while read -r repo picture license; do
  [[ -n "$repo" ]] || continue
  url="https://raw.githubusercontent.com/$repo/main/.github/social-preview.png"
  curl --fail --silent --show-error --location --retry 3 --connect-timeout 10 --max-time 60 --output "$preview" "$url"
  mkdir -p "$(dirname "$picture")"
  # Cut to the proportions of a card, scaled down sharply, as a lossy WebP of
  # quality 80 with the slowest and smallest encoding, and without metadata.
  "$python" -I -B - "$preview" "$picture" <<'PY'
import sys

from PIL import Image, ImageOps

sys.path.insert(0, ".github")
from mkdocs_project import PICTURE

preview, picture = sys.argv[1:]
with Image.open(preview) as image:
    card = ImageOps.fit(image.convert("RGB"), PICTURE, Image.Resampling.LANCZOS)
card.save(picture, "WEBP", quality=80, method=6)
PY
  # REUSE-IgnoreStart
  printf 'SPDX-FileCopyrightText: Dennis Otto and the contributors to %s\nSPDX-License-Identifier: %s\n' \
    "$repo" "$license" >"$picture.license"
  # REUSE-IgnoreEnd
  echo "$picture ($(wc -c <"$picture") bytes) from $url"
done <<<"$pictures"
