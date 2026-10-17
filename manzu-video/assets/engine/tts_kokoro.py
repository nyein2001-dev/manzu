#!/usr/bin/env python3
"""Kokoro-82M (Apache-2.0) local neural TTS for the video engine. Runs in the isolated venv:

    /tmp/kokoro-venv/bin/python tts_kokoro.py in1.txt out1.wav [in2.txt out2.wav ...]

The engine calls it through EXPLAINER_TTS_CMD (quote paths that contain spaces); `with_kokoro.sh` sets it.

Env: KOKORO_DIR (model dir, default /tmp/kokoro-models), KOKORO_VOICE (default af_heart),
KOKORO_SPEED (default 0.92), KOKORO_SENTENCE_PAUSE / KOKORO_CLAUSE_PAUSE (seconds).
Model load happens once per call; the engine passes every missing line of a scene in one call.
Besides each wav it writes `<out>.timings.json` = {"t": [[phoneme, start_s, end_s], ...],
"k": [[token, phonemes_of_that_token_alone], ...]} so the engine can align every word to the audio.
Nothing leaves the machine: model + voices are local files.
"""
import json
import os
import re
import sys

import soundfile as sf
from kokoro_onnx import Kokoro

DIR = os.environ.get("KOKORO_DIR", "/tmp/kokoro-models")
VOICE = os.environ.get("KOKORO_VOICE", "af_heart")
SPEED = float(os.environ.get("KOKORO_SPEED", "0.92"))
SENT_PAUSE = float(os.environ.get("KOKORO_SENTENCE_PAUSE", "0.35"))
CLAUSE_PAUSE = float(os.environ.get("KOKORO_CLAUSE_PAUSE", "0.2"))


def main():
    args = sys.argv[1:]
    if not args or len(args) % 2:
        sys.exit("usage: tts_kokoro.py in.txt out.wav [in.txt out.wav ...]")
    k = Kokoro(f"{DIR}/kokoro-v1.0.onnx", f"{DIR}/voices-v1.0.bin")
    for src, dst in zip(args[::2], args[1::2]):
        with open(src, encoding="utf-8") as f:
            text = f.read().strip()
        audio, sr, timings = k.create_timed(text, voice=VOICE, speed=SPEED, lang="en-us",
                                            sentence_pause=SENT_PAUSE, clause_pause=CLAUSE_PAUSE)
        sf.write(dst, audio, sr, subtype="PCM_16")
        side = {"t": [[t.phoneme, round(t.start, 4), round(t.end, 4)] for t in timings],
                "k": [[w, k.tokenizer.phonemize(w, "en-us")] for w in re.findall(r"[A-Za-z0-9']+", text)]}
        with open(dst + ".timings.json", "w", encoding="utf-8") as f:
            json.dump(side, f)


if __name__ == "__main__":
    main()
