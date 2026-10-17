#!/bin/bash
# Install the local neural voice Kokoro-82M (Apache-2.0) into DISPOSABLE folders under /tmp.
#   install_kokoro.sh --authorized      # only after the user said yes to exactly this
# Without --authorized the script prints the plan and exits 0 without touching anything.
#
# What it does (nothing system-wide, no narration text sent anywhere; only downloads, about 450 MB in total):
#   1. uv venv --python 3.12 $KOKORO_VENV                       (default /tmp/kokoro-venv; uses an EXISTING Python 3.12, never downloads one)
#   2. uv pip install kokoro-onnx==0.6.1 soundfile scipy         (into that venv; ~100 MB incl. onnxruntime; uv cache kept in $KOKORO_UV_CACHE)
#   3. curl kokoro-v1.0.onnx (325,505,369 B) + voices-v1.0.bin (28,214,398 B) from the kokoro-onnx GitHub release
#      into $KOKORO_DIR (default /tmp/kokoro-models), skipping files already present
#   4. sha256-verify both model files and import-test kokoro_onnx
# Python must be >=3.10,<3.14 (3.12 here). Undo: rm -rf $KOKORO_VENV $KOKORO_DIR $KOKORO_UV_CACHE
set -euo pipefail
VENV="${KOKORO_VENV:-/tmp/kokoro-venv}"
DIR="${KOKORO_DIR:-/tmp/kokoro-models}"
export UV_CACHE_DIR="${KOKORO_UV_CACHE:-/tmp/kokoro-uv-cache}"
export UV_PYTHON_DOWNLOADS=never
UV="$(command -v uv || echo "$HOME/.local/bin/uv")"
REL="https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1"
SHA_ONNX="beb0d1848dee9a49da392cc3df26958d46cfa35d321edf434f52949153f0df3a"
SHA_VOICES="bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d"

if [ "${1:-}" != "--authorized" ]; then
  cat <<EOF
DRY RUN (no changes). With the user's explicit authorization, run again with --authorized to:
  UV_CACHE_DIR=$UV_CACHE_DIR UV_PYTHON_DOWNLOADS=never $UV venv --python 3.12 $VENV
  $UV pip install --python $VENV/bin/python 'kokoro-onnx==0.6.1' soundfile scipy
  curl -fL --retry 3 $REL/kokoro-v1.0.onnx  -> $DIR/   (325 MB, skipped if present)
  curl -fL --retry 3 $REL/voices-v1.0.bin   -> $DIR/   (28 MB, skipped if present)
  then sha256-verify both files and import-test kokoro_onnx
Undo: rm -rf $VENV $DIR $UV_CACHE_DIR
EOF
  exit 0
fi

[ -x "$UV" ] || { echo "uv not found; ask the user before installing it" >&2; exit 1; }
"$UV" venv --python 3.12 "$VENV" || { echo "No Python 3.12 found (this script never downloads one). Install it or set UV_PYTHON." >&2; exit 1; }
"$UV" pip install --python "$VENV/bin/python" 'kokoro-onnx==0.6.1' soundfile scipy
mkdir -p "$DIR"
[ -s "$DIR/kokoro-v1.0.onnx" ] || curl -fL --retry 3 -o "$DIR/kokoro-v1.0.onnx" "$REL/kokoro-v1.0.onnx"
[ -s "$DIR/voices-v1.0.bin" ]  || curl -fL --retry 3 -o "$DIR/voices-v1.0.bin"  "$REL/voices-v1.0.bin"
echo "$SHA_ONNX  $DIR/kokoro-v1.0.onnx"  | shasum -a 256 -c -
echo "$SHA_VOICES  $DIR/voices-v1.0.bin" | shasum -a 256 -c -
"$VENV/bin/python" - <<PY
from kokoro_onnx import Kokoro
k = Kokoro("$DIR/kokoro-v1.0.onnx", "$DIR/voices-v1.0.bin")
print("kokoro ok; voices:", len(k.get_voices()), "; has_timings:", k.has_timings)
PY
echo "Done. Use: ./with_kokoro.sh python3 build.py final --out out/video.mp4"
