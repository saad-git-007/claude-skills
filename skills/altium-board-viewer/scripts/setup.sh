#!/usr/bin/env bash
# Check every requirement and install what is missing. Safe to re-run: present items are skipped.
#
#   setup.sh            2D viewer + PDF needs: uv, Python 3.12, altium_monkey venv, Chrome check
#   setup.sh --3d       also the 3D needs: cadquery-ocp + numpy venv (~600 MB) and three.js files
#   setup.sh --check    report only, install nothing
#   setup.sh --clean    delete venvs, downloaded models and build files (keeps your outputs)
#
# Everything goes into $ABV_WORK (default ~/.cache/altium-board-viewer), never into the project.
set -euo pipefail
WORK="${ABV_WORK:-$HOME/.cache/altium-board-viewer}"
MODE="${1:-}"
ALTIUM_MONKEY_REPO="https://github.com/wavenumber-eng/altium_monkey"
THREE_VER="0.128.0"   # r128: the last release that ships examples/js (non-module) builds

ok()   { printf '  \033[32mok\033[0m    %s\n' "$*"; }
miss() { printf '  \033[33mmissing\033[0m %s\n' "$*"; }
step() { printf '\n\033[1m%s\033[0m\n' "$*"; }
CHECK=0; [ "$MODE" = "--check" ] && CHECK=1

if [ "$MODE" = "--clean" ]; then
  du -sh "$WORK" 2>/dev/null || true
  rm -rf "$WORK/venv-altium" "$WORK/venv-3d" "$WORK/models" "$WORK/out3d" "$WORK/build" "$WORK/src"
  echo "cleaned $WORK (vendor JS kept: $(du -sh "$WORK/vendor" 2>/dev/null | cut -f1))"
  exit 0
fi
[ $CHECK = 1 ] || mkdir -p "$WORK"

step "Disk"
df -h "$WORK" | awk 'NR==2{print "  free on " $6 ": " $4}'
echo "  needs: ~150 MB for 2D/PDF, ~800 MB more for --3d (deletable afterwards with --clean)"

step "Tools"
for t in git curl python3; do
  if command -v "$t" >/dev/null; then ok "$t"; else miss "$t (install with your package manager, e.g. sudo apt install $t)"; [ $CHECK = 1 ] || exit 1; fi
done
if ! command -v uv >/dev/null && [ -x "$HOME/.local/bin/uv" ]; then export PATH="$HOME/.local/bin:$PATH"; fi
if command -v uv >/dev/null; then ok "uv $(uv --version | cut -d' ' -f2)"
elif [ $CHECK = 1 ]; then miss "uv"
else
  echo "  installing uv (user-local, no sudo)…"
  curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null
  export PATH="$HOME/.local/bin:$PATH"; ok "uv $(uv --version | cut -d' ' -f2)"
fi

CHROME=""
for b in google-chrome google-chrome-stable chromium chromium-browser; do command -v $b >/dev/null && { CHROME=$b; break; }; done
[ -z "$CHROME" ] && [ -x "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" ] && CHROME="Google Chrome.app"
if [ -n "$CHROME" ]; then ok "browser for PDF: $CHROME"
else miss "Chrome/Chromium (PDF step only). Ask the user, then: sudo snap install chromium  |  sudo apt install chromium  |  brew install --cask google-chrome"; fi

step "altium_monkey (Python 3.12 venv)"
if "$WORK/venv-altium/bin/python" -c "import altium_monkey" 2>/dev/null; then ok "venv-altium"
elif [ $CHECK = 1 ]; then miss "venv-altium"
else
  # The repo's own `uv sync` needs a recent uv; a plain venv + pip install works with any uv.
  uv python install 3.12 -q 2>/dev/null || true
  uv venv -q --python 3.12 "$WORK/venv-altium"
  rm -rf "$WORK/src/altium_monkey"; mkdir -p "$WORK/src"
  git clone -q --depth 1 "$ALTIUM_MONKEY_REPO" "$WORK/src/altium_monkey"
  VIRTUAL_ENV="$WORK/venv-altium" uv pip install -q "$WORK/src/altium_monkey"
  rm -rf "$WORK/src"   # installed non-editable, the clone is no longer needed
  "$WORK/venv-altium/bin/python" -c "import altium_monkey" && ok "venv-altium installed"
fi

if [ "$MODE" = "--3d" ] || [ $CHECK = 1 ]; then
  step "3D (cadquery-ocp + numpy, three.js r128)"
  if "$WORK/venv-3d/bin/python" -c "import OCP, numpy" 2>/dev/null; then ok "venv-3d"
  elif [ $CHECK = 1 ]; then miss "venv-3d (setup.sh --3d)"
  else
    uv venv -q --python 3.12 "$WORK/venv-3d"
    VIRTUAL_ENV="$WORK/venv-3d" uv pip install -q cadquery-ocp numpy
    "$WORK/venv-3d/bin/python" -c "import OCP, numpy" && ok "venv-3d installed"
  fi
  mkdir -p "$WORK/vendor"
  for pair in "three.min.js|https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js" \
              "OrbitControls.js|https://cdn.jsdelivr.net/npm/three@$THREE_VER/examples/js/controls/OrbitControls.js" \
              "GLTFLoader.js|https://cdn.jsdelivr.net/npm/three@$THREE_VER/examples/js/loaders/GLTFLoader.js"; do
    f="${pair%%|*}"; u="${pair#*|}"
    if [ -s "$WORK/vendor/$f" ]; then ok "$f"
    elif [ $CHECK = 1 ]; then miss "$f"
    else curl -sSfL -o "$WORK/vendor/$f" "$u" && ok "$f downloaded"; fi
  done
fi

step "Work folder"
echo "  $WORK  ($(du -sh "$WORK" 2>/dev/null | cut -f1))"
