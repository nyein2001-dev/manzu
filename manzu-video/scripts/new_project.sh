#!/bin/bash
# Scaffold a new manzu-video project from the skill's engine template.
#   new_project.sh <dest-dir>
# <dest-dir> must not exist or must be empty. Nothing is installed, downloaded or sent anywhere.
set -euo pipefail
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/../assets/engine" && pwd)"
DEST="${1:-}"
[ -n "$DEST" ] || { echo "usage: new_project.sh <dest-dir>" >&2; exit 2; }
if [ -e "$DEST" ] && [ -n "$(ls -A "$DEST" 2>/dev/null)" ]; then
  echo "refusing: $DEST exists and is not empty" >&2; exit 1
fi
mkdir -p "$DEST"
rsync -a --exclude '__pycache__' --exclude '.DS_Store' "$SRC/" "$DEST/"
chmod +x "$DEST"/build.py "$DEST"/preview.py "$DEST"/tts_kokoro.py "$DEST"/with_kokoro.sh

missing=""
python3 - <<'PY' || missing="python packages"
import importlib.util, sys
bad = [m for m in ("cairo", "numpy", "PIL") if importlib.util.find_spec(m) is None]
if bad:
    print("missing python modules:", ", ".join(bad), "(pycairo, numpy, pillow). Do not pip install without the owner's go-ahead.", file=sys.stderr)
    sys.exit(1)
PY
command -v ffmpeg >/dev/null || { echo "missing: ffmpeg" >&2; missing="$missing ffmpeg"; }
command -v say >/dev/null || echo "note: macOS 'say' not found; set EXPLAINER_TTS_CMD to another TTS command" >&2

cat <<EOF
Created $DEST
Next:
  cd "$DEST"
  export EXPLAINER_WORK="\$PWD/.cache" PYTHONDONTWRITEBYTECODE=1   # default cache is /tmp/explainer_work
  python3 build.py tts                         # synthesize the demo narration (macOS say), print the timeline
  python3 build.py final --out out/demo.mp4    # smoke-render the demo scene
  edit plan.md, script.py, scenes/  (read SCENE_RULES.md first)
EOF
[ -z "$missing" ] || { echo "WARNING: missing:$missing" >&2; exit 3; }
