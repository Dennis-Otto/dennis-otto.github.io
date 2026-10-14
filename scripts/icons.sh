#!/usr/bin/env bash
# Makes the icons that browsers ask the root of the address for, from the logo in
# docs/assets/logo.svg: docs/favicon.ico with 16, 32 and 48 pixels, and
# docs/apple-touch-icon.png with 180, which MkDocs copies to the root of the
# website. Run it after a change of the logo:
#   bash scripts/icons.sh
# The same logo makes the same icons, byte for byte, so a run without a change of
# the logo changes nothing: git diff --exit-code docs/favicon.ico docs/apple-touch-icon.png
#
# It needs Docker, whose headless Chromium of Playwright's image renders
# .github/icons.html as scripts/social-preview.sh renders the social preview, and
# Pillow from the tools of the website in .venv-docs, which CONTRIBUTING.md sets up.
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
png="$(mktemp)"
log="$(mktemp)"
trap 'rm -f "$png" "$log"' EXIT

# Both icons side by side on a transparent page; the PNG leaves the container
# through stdout, so it belongs to whoever runs this. Git Bash on Windows keeps the
# paths of the container as they are.
if ! MSYS_NO_PATHCONV=1 docker run --rm --platform linux/amd64 --volume "$root:/work:ro" "$image" sh -c '
  /ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell \
    --no-sandbox --hide-scrollbars --force-device-scale-factor=1 --window-size=372,192 \
    --default-background-color=00000000 --virtual-time-budget=10000 \
    --screenshot=/tmp/icons.png file:///work/.github/icons.html >&2 && cat /tmp/icons.png' \
  >"$png" 2>"$log" || [[ ! -s "$png" ]]; then
  cat "$log" >&2
  echo "Rendering .github/icons.html failed." >&2
  exit 1
fi

"$python" -I -B - "$png" <<'PY'
import sys

from PIL import Image

with Image.open(sys.argv[1]) as page:
    page = page.convert("RGBA")
favicon = page.crop((0, 0, 192, 192))
favicon.save("docs/favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
# iOS shows black where an icon is transparent, so the touch icon has no alpha.
page.crop((192, 0, 372, 180)).convert("RGB").save("docs/apple-touch-icon.png")
PY
echo "Made docs/favicon.ico and docs/apple-touch-icon.png from docs/assets/logo.svg."
