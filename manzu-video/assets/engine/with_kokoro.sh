#!/bin/bash
# Run any project command with the local Kokoro voice (caches in /tmp, outside synced folders).
#   ./with_kokoro.sh python3 build.py final --out out/video.mp4
#   ./with_kokoro.sh python3 preview.py s0_demo --lines
# Needs the isolated install made by the skill's scripts/install_kokoro.sh (venv + model files; installing is
# a step that needs the user's explicit authorization). Overrides:
#   KOKORO_VENV (default /tmp/kokoro-venv)  KOKORO_DIR (default /tmp/kokoro-models)
#   KOKORO_VOICE (default af_heart)  KOKORO_SPEED (default 0.92)  EXPLAINER_WORK (cache dir)
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="${KOKORO_VENV:-/tmp/kokoro-venv}"
export KOKORO_DIR="${KOKORO_DIR:-/tmp/kokoro-models}"
if [ -z "${EXPLAINER_TTS_CMD:-}" ]; then
  if [ ! -x "$VENV/bin/python" ] || [ ! -s "$KOKORO_DIR/kokoro-v1.0.onnx" ] || [ ! -s "$KOKORO_DIR/voices-v1.0.bin" ]; then
    echo "Kokoro is not installed (venv: $VENV, models: $KOKORO_DIR)." >&2
    echo "Run the skill's scripts/install_kokoro.sh (a dry run prints the plan; --authorized needs the user's OK)," >&2
    echo "or run without this wrapper to use the macOS 'say' voice." >&2
    exit 1
  fi
  export EXPLAINER_TTS_CMD="$VENV/bin/python '$HERE/tts_kokoro.py'"
fi
export EXPLAINER_WORK="${EXPLAINER_WORK:-/tmp/explainer_kokoro}"
export PYTHONDONTWRITEBYTECODE=1
cd "$HERE" && exec "$@"
