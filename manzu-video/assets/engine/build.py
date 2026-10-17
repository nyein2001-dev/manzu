#!/usr/bin/env python3
"""Build the explainer video described by script.py + scenes/.

    python3 build.py tts                 # synthesize narration, print timeline table
    python3 build.py render [scene ...]  # render silent scene segments (default: all that have a scene module)
    python3 build.py final [--out F.mp4] # render all, mix audio, concat, mux, write .srt next to output

Caches (tts wavs, segments, mix) live in $EXPLAINER_WORK (default /tmp/explainer_work), outside synced folders.
Chapter titles = script.TITLES[scene_id]; file title = script.VIDEO_TITLE (optional).
"""
import argparse
import json
import math
import subprocess
import sys
import wave
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

import engine
import script
from engine import FPS, SR, WORK


def _have(scene_id):
    return (Path(__file__).parent / "scenes" / f"{scene_id}.py").exists()


def cmd_tts(ids):
    total = 0.0
    for sid in ids:
        tl, _ = engine.build_timeline(sid)
        print(f"\n== {sid}  ({tl.total:.1f}s)")
        for i, it in enumerate(tl.items):
            label = getattr(it, "text", None) or f"<{it.kind} hold> {it.caption}"
            print(f"  [{i:2d}] {tl.start(i):6.2f}-{tl.end(i):6.2f}  {label[:90]}")
        total += math.ceil(tl.total * FPS) / FPS
    print(f"\nTOTAL {total:.1f}s = {int(total // 60)}:{int(total % 60):02d}")


def cmd_render(ids):
    for sid in ids:
        engine.build_timeline(sid)   # synthesize narration serially: workers must only read the cache
    with ProcessPoolExecutor(max_workers=4) as ex:
        for sid, out in zip(ids, ex.map(engine.render_scene, ids)):
            print("rendered", sid, out)


def _loudnorm(src, dst, target=-18.0, tp=-1.5):
    """Two-pass EBU R128 normalisation to -18 LUFS integrated, true peak <= -1.5 dB. Pure gain when the peak
    allows it; otherwise loudnorm falls back to dynamic mode (a few dB of peak limiting), which is expected."""
    probe = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(src), "-af",
                            f"loudnorm=I={target}:TP={tp}:LRA=11:print_format=json", "-f", "null", "-"],
                           capture_output=True, text=True).stderr
    m = json.loads(probe[probe.rindex("{"): probe.rindex("}") + 1])
    af = (f"loudnorm=I={target}:TP={tp}:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-af", af, "-ar", str(SR), "-ac", "1",
                    str(dst)], check=True)


def cmd_final(ids, out):
    cmd_render(ids)
    chunks = [engine.scene_audio(sid)[0] for sid in ids]
    pcm = (np.clip(np.concatenate(chunks), -1, 1) * 32767).astype(np.int16)
    wav = WORK / "mix.wav"
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    wavn = WORK / "mix_norm.wav"
    _loudnorm(wav, wavn)
    wav = wavn
    lst = WORK / "concat.txt"
    lst.write_text("".join(f"file '{WORK / 'seg' / (s + '.mp4')}'\n" for s in ids))
    vid = WORK / "video.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy",
                    str(vid)], check=True)
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    meta, off = [";FFMETADATA1", f"title={getattr(script, 'VIDEO_TITLE', 'Explainer')}"], 0.0
    for sid in ids:
        d = math.ceil(engine.build_timeline(sid)[0].total * FPS) / FPS
        meta += ["[CHAPTER]", "TIMEBASE=1/1000", f"START={int(off * 1000)}", f"END={int((off + d) * 1000)}",
                 f"title={script.TITLES[sid]}"]
        off += d
    chap = WORK / "chapters.txt"
    chap.write_text("\n".join(meta) + "\n", encoding="utf-8")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(vid), "-i", str(wav), "-i", str(chap),
                    "-map", "0:v", "-map", "1:a", "-map_metadata", "2", "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "192k", "-movflags", "+faststart", "-shortest", str(out)], check=True)
    engine.write_srt(ids, out.with_suffix(".srt"))
    print("wrote", out, out.with_suffix(".srt"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["tts", "render", "final"])
    ap.add_argument("scenes", nargs="*")
    ap.add_argument("--out", default=str(WORK / "explainer.mp4"))
    a = ap.parse_args()
    ids = a.scenes or [s for s in script.SCENES if _have(s)]
    if a.cmd == "tts":
        cmd_tts(a.scenes or list(script.SCENES))
    elif a.cmd == "render":
        cmd_render(ids)
    else:
        missing = [s for s in script.SCENES if not _have(s)]
        if missing and not a.scenes:
            sys.exit(f"missing scene modules: {missing}")
        cmd_final(ids, a.out)


if __name__ == "__main__":
    main()
