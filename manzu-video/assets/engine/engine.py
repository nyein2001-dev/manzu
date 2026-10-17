"""Voice backends (macOS `say` or any command), word/clause alignment, scene compositing, SFX, audio mix, SRT."""
import difflib
import hashlib
import importlib
import json
import math
import os
import re
import shlex
import subprocess
import sys
import wave
from pathlib import Path

import cairo
import numpy as np

import lib
from lib import BG_BOT, DIM, FPS, GOLD, H, INK, W, WHITE, Timeline, circle, clamp, prog, rrect, text, wrap
import script
from script import Hold

HERE = Path(__file__).resolve().parent
WORK = Path(os.environ.get("EXPLAINER_WORK", "/tmp/explainer_work"))   # caches stay out of synced folders
# Voice backend. Default: macOS `say`. EXPLAINER_VOICE / EXPLAINER_RATE pick the `say` voice and speed (an
# installed Enhanced/Premium voice works the same way). EXPLAINER_TTS_CMD = command line that takes
# `<in1.txt> <out1.wav> [<in2.txt> <out2.wav> ...]` (UTF-8 text in, wav out; writes optional
# `<out>.timings.json` sidecars, see tts_kokoro.py) and replaces `say` (Kokoro, Piper, ...).
VOICE = os.environ.get("EXPLAINER_VOICE", "Samantha")
RATE = int(os.environ.get("EXPLAINER_RATE", "165"))
TTS_CMD = os.environ.get("EXPLAINER_TTS_CMD", "")
# Burned-in captions: "progressive" reveals a narration line word by word as it is spoken (cannot spoil an answer or a
# prediction); "line" shows the whole line when it starts. The .srt always carries whole-line cues.
CAPTIONS = os.environ.get("EXPLAINER_CAPTIONS", "progressive")
SR = 44100
FADE = 0.35

WORK.mkdir(parents=True, exist_ok=True)
(WORK / "tts").mkdir(exist_ok=True)
(WORK / "seg").mkdir(exist_ok=True)


# ------------------------------------------------------------------ TTS
def spoken(s):
    for k, v in script.SPOKEN_FIX.items():
        s = re.sub(rf"\b{re.escape(k)}\b", v, s)
    return s


def _backend_ident():
    """Identity of the voice backend: changes whenever the command, its script content or its KOKORO_* settings change."""
    if not TTS_CMD:
        return f"say:{VOICE}|{RATE}"
    h = hashlib.sha1()
    for part in shlex.split(TTS_CMD):
        if part.endswith(".py") and os.path.exists(part):
            h.update(Path(part).read_bytes())
    env = sorted((k, v) for k, v in os.environ.items() if k.startswith("KOKORO_"))
    return f"cmd:{TTS_CMD}|{h.hexdigest()[:10]}|{env}"


def _tts_key(line):
    ident = _backend_ident()
    return hashlib.sha1(f"{ident}|{spoken(line.text)}".encode()).hexdigest()[:16]


def ensure_tts(lines):
    """Synthesize every not-yet-cached line. A TTS_CMD backend gets ALL missing lines in one call
    (`cmd in1.txt out1.wav in2.txt out2.wav ...`) so the model loads once."""
    todo = {}
    for ln in lines:
        key = _tts_key(ln)
        if not (WORK / "tts" / f"{key}.wav").exists():
            todo[key] = ln
    if not todo:
        return
    raws = {k: WORK / "tts" / f"{k}.src.{'wav' if TTS_CMD else 'aiff'}" for k in todo}
    if TTS_CMD:
        args = []
        for k, ln in todo.items():
            txt = WORK / "tts" / f"{k}.txt"
            txt.write_text(spoken(ln.text), encoding="utf-8")
            args += [str(txt), str(raws[k])]
        try:
            subprocess.run([*shlex.split(TTS_CMD), *args], check=True)
        finally:
            for k in todo:
                (WORK / "tts" / f"{k}.txt").unlink(missing_ok=True)
    else:
        for k, ln in todo.items():
            subprocess.run(["say", "-v", VOICE, "-r", str(RATE), "-o", str(raws[k]), spoken(ln.text)], check=True)
    for k, raw in raws.items():
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw), "-ar", str(SR), "-ac", "1",
                        str(WORK / "tts" / f"{k}.wav")], check=True)
        side = Path(str(raw) + ".timings.json")
        if side.exists():
            side.rename(WORK / "tts" / f"{k}.timings.json")
        raw.unlink()


def tts_wav(line):
    """Cached 44.1 kHz mono wav of one line. Returns (path, seconds)."""
    ensure_tts([line])
    wav = WORK / "tts" / f"{_tts_key(line)}.wav"
    with wave.open(str(wav)) as w:
        return wav, w.getnframes() / w.getframerate()


def _clauses(text_):
    return [c for c in re.split(r"(?<=[,.:;!?])\s+", text_.strip()) if c]


def _speech_segments(wav, minsil):
    """Speech spans (start, end) in seconds, separated by pauses >= minsil seconds."""
    with wave.open(str(wav)) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32)
    hop = SR // 100
    n = len(x) // hop
    rms = np.sqrt((x[: n * hop].reshape(n, hop) ** 2).mean(axis=1))
    active = rms > rms.max() * 0.04
    segs, i = [], 0
    while i < n:
        if active[i]:
            j = i
            while j < n and active[j]:
                j += 1
            segs.append([i, j])
            i = j
        else:
            i += 1
    merged = [segs[0]]
    for s in segs[1:]:
        if (s[0] - merged[-1][1]) * 0.01 < minsil:
            merged[-1][1] = s[1]
        else:
            merged.append(s)
    return [(a * 0.01, b * 0.01) for a, b in merged]


def speech_marks(wav, text_):
    """[(clause, start, end)] seconds from line start. Exact when the audio pauses match the
    punctuation (the usual case). Otherwise the (n_clauses - 1) longest pauses are taken as the
    clause boundaries; if the audio has fewer pauses than that, clauses share the speech span by
    character count. Returns (marks, exact)."""
    toks = speech_words(wav, text_)
    if toks:
        out, idx = [], 0
        for c in _clauses(text_):
            n = len(_TOK.findall(c))
            if n == 0:
                break
            out.append((c, toks[idx][1], toks[idx + n - 1][2]))
            idx += n
        else:
            return out, True
    cl = _clauses(text_)
    for minsil in (0.06, 0.08, 0.10, 0.12, 0.15, 0.18, 0.22, 0.28, 0.35):
        segs = _speech_segments(wav, minsil)
        if len(segs) == len(cl):
            return [(c, a, b) for c, (a, b) in zip(cl, segs)], True
    fine = _speech_segments(wav, 0.06)
    if len(fine) >= len(cl):
        gaps = [(fine[k + 1][0] - fine[k][1], k) for k in range(len(fine) - 1)]
        cuts = sorted(k for _, k in sorted(gaps, reverse=True)[: len(cl) - 1])
        groups, lo = [], 0
        for k in cuts + [len(fine) - 1]:
            groups.append((fine[lo][0], fine[k][1]))
            lo = k + 1
        return [(c, a, b) for c, (a, b) in zip(cl, groups)], False
    segs = _speech_segments(wav, 0.35)
    a0, b0 = segs[0][0], segs[-1][1]
    tot = sum(len(c) for c in cl)
    out, pos = [], a0
    for c in cl:
        d = (b0 - a0) * len(c) / tot
        out.append((c, pos, pos + d))
        pos += d
    return out, False

_TOK = re.compile(r"[A-Za-z0-9']+")
_PUNCT = ",.:;!?"


def speech_words(wav, text_):
    """Word-level alignment from the backend's phoneme timings (Kokoro writes <key>.timings.json):
    [(token, start, end)] for every [A-Za-z0-9']+ token of the ORIGINAL narration text, or None when
    there is no sidecar or the alignment is poor.
    Method: the audio's phoneme string is aligned (difflib) to the concatenated phonemes of each spoken
    token phonemized alone; token boundaries are carried across the alignment. This survives espeak
    merging words ('in the' -> one word) and numbers spoken as several words."""
    side = Path(wav).with_suffix(".timings.json")
    if not side.exists():
        return None
    d = json.loads(side.read_text())
    chars = [(ch, s, e) for p, s, e in d["t"] if p != " " and p not in _PUNCT for ch in p]
    a_str = "".join(c for c, _, _ in chars)
    e_str, bounds = "", []
    for _, ph in d["k"]:
        ph = "".join(ch for ch in ph if ch != " " and ch not in _PUNCT)
        bounds.append((len(e_str), len(e_str) + len(ph)))
        e_str += ph
    if not chars or not e_str:
        return None
    sm = difflib.SequenceMatcher(None, e_str, a_str, autojunk=False)
    xs, ys = [], []
    for i, j, n in sm.get_matching_blocks():
        xs += range(i, i + n)
        ys += range(j, j + n)
    if len(xs) < 0.8 * len(e_str):
        return None

    def amap(i):
        return int(round(float(np.interp(i, xs, ys))))

    spans = []
    for b0, b1 in bounds:
        spans.append(None if b1 <= b0 else (chars[amap(b0)][1], chars[amap(b1 - 1)][2]))
    out, idx = [], 0
    for tok in _TOK.findall(text_):
        n = len(_TOK.findall(spoken(tok)))
        part = [s for s in spans[idx: idx + n] if s]
        if idx + n > len(spans) or not part:
            return None
        out.append((tok, part[0][0], part[-1][1]))
        idx += n
    return out if idx == len(spans) else None


def build_timeline(scene_id):
    items = script.SCENES[scene_id]
    ensure_tts([it for it in items if not isinstance(it, Hold)])
    durs, wavs, marks, words = [], [], [], []
    for it in items:
        if isinstance(it, Hold):
            durs.append(it.secs)
            wavs.append(None)
            marks.append(None)
            words.append(None)
        else:
            p, d = tts_wav(it)
            durs.append(d)
            wavs.append(p)
            marks.append(speech_marks(p, it.text)[0])
            words.append(speech_words(p, it.text))
    return Timeline(items, durs, marks, words), wavs


def load_scene(scene_id):
    return importlib.import_module(f"scenes.{scene_id}")


# ------------------------------------------------------------------ compositing
def _hold_overlay(c, tl, t):
    i = tl.at(t)
    if i is None or not isinstance(tl.items[i], Hold):
        return
    h = tl.items[i]
    u = tl.u(i, t)
    cx, cy, r = 1170, 105, 46
    circle(c, cx, cy, r + 14, fill=INK, alpha=0.6)
    c.save()
    c.set_line_width(10)
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    c.set_source_rgba(*DIM, 0.45)
    c.arc(cx, cy, r, 0, 2 * math.pi)
    c.stroke()
    c.set_source_rgba(*GOLD, 1)
    c.arc(cx, cy, r, -math.pi / 2, -math.pi / 2 + 2 * math.pi * (1 - u))
    c.stroke()
    c.restore()
    text(c, str(max(1, math.ceil(h.secs * (1 - u)))), cx, cy, 44, WHITE)
    text(c, "THINK" if h.kind == "think" else "MOVE!", cx, cy + 82, 26, GOLD)


def _revealed_chars(tl, i, s, t):
    """How many characters of narration line i are spoken by time t (including punctuation that follows the last word)."""
    n = 0
    for end, ts in tl.word_times(i):
        if t < ts - 0.03:
            break
        n = end
    while 0 < n < len(s) and s[n] in ",.:;!?":
        n += 1
    return n


def _caption(c, tl, t):
    i = tl.at(t)
    if i is None:
        # keep the previous line visible through short gaps
        for j in range(len(tl.items) - 1, -1, -1):
            if tl.end(j) <= t < tl.end(j) + getattr(tl.items[j], "gap", 0.0):
                i = j
                break
    if i is None:
        return
    it = tl.items[i]
    s = it.caption if isinstance(it, Hold) else it.text
    if not s:
        return
    shown = len(s) if (isinstance(it, Hold) or CAPTIONS == "line") else _revealed_chars(tl, i, s, t)
    if shown <= 0:
        return
    size = 30
    lines = wrap(c, s, size, 1060)                 # layout comes from the FULL line so the box never resizes
    lh = 40
    bh = lh * len(lines) + 22
    top = H - 18 - bh
    rrect(c, 70, top, W - 140, bh, r=20, fill=INK, alpha=0.78)
    cursor = 0
    for k, ln in enumerate(lines):
        off = s.find(ln, cursor)
        cursor = off + len(ln)
        part = ln[: max(0, min(len(ln), shown - off))].rstrip()
        if part:
            x0 = W / 2 - lib.text_width(c, ln, size) / 2   # same x for every frame: words appear in place
            text(c, part, x0, top + 11 + lh * (k + 0.5), size, WHITE, align="left")


def render_frame(c, mod, tl, t):
    lib.bg(c)
    mod.draw(c, t, tl)
    _hold_overlay(c, tl, t)
    _caption(c, tl, t)
    a = 1 - min(prog(t, 0.0, FADE), prog(tl.total - t, 0.0, FADE))
    if a > 0:
        c.set_source_rgba(*BG_BOT, clamp(a))
        c.paint()


# ------------------------------------------------------------------ video
def render_scene(scene_id):
    """Render one scene to WORK/seg/<id>.mp4 (silent). Returns path."""
    tl, _ = build_timeline(scene_id)
    mod = load_scene(scene_id)
    n = int(math.ceil(tl.total * FPS))
    out = WORK / "seg" / f"{scene_id}.mp4"
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(surf)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
           "-pix_fmt", "yuv420p", "-r", str(FPS), str(out)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for k in range(n):
        c.save()
        render_frame(c, mod, tl, k / FPS)
        c.restore()
        surf.flush()
        p.stdin.write(surf.get_data())
    p.stdin.close()
    if p.wait() != 0:
        raise RuntimeError(f"ffmpeg failed for {scene_id}")
    return str(out)


def render_still(scene_id, t, path):
    tl, _ = build_timeline(scene_id)
    mod = load_scene(scene_id)
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(surf)
    render_frame(c, mod, tl, t)
    surf.write_to_png(str(path))
    return tl


# ------------------------------------------------------------------ audio
def _sfx(name):
    def env(n, decay):
        x = np.arange(n) / SR
        return np.exp(-x * decay)
    if name == "ding":
        n = int(SR * 0.9)
        x = np.arange(n) / SR
        y = (np.sin(2 * np.pi * 880 * x) + 0.5 * np.sin(2 * np.pi * 1320 * x)) * env(n, 5)
    elif name == "pop":
        n = int(SR * 0.14)
        x = np.arange(n) / SR
        f = 500 - 2500 * x
        y = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 25)
    elif name == "whoosh":
        n = int(SR * 0.45)
        rng = np.random.default_rng(1)
        y = np.convolve(rng.standard_normal(n), np.ones(40) / 40, mode="same")
        y *= np.sin(np.linspace(0, np.pi, n)) ** 2
    elif name == "tick":
        n = int(SR * 0.05)
        x = np.arange(n) / SR
        y = np.sin(2 * np.pi * 1400 * x) * env(n, 90)
    elif name == "success":
        parts = []
        for k, f in enumerate((523.25, 659.25, 783.99, 1046.5)):
            n = int(SR * 0.5)
            x = np.arange(n) / SR
            seg = np.sin(2 * np.pi * f * x) * env(n, 6)
            parts.append(np.concatenate([np.zeros(int(SR * 0.11 * k)), seg]))
        m = max(len(p) for p in parts)
        y = sum(np.pad(p, (0, m - len(p))) for p in parts)
    else:
        raise ValueError(f"unknown sfx {name}")
    return (y / (np.max(np.abs(y)) + 1e-9)).astype(np.float32)


def _speech_level(a, target_rms=0.11, peak=0.9):
    """Gain one narration line to a common speech RMS (measured on the active samples only), capped at `peak`.
    Backends differ a lot in level (Kokoro is ~8 dB quieter than macOS `say`) and lines differ from each other."""
    act = np.abs(a) > 0.02 * max(float(np.max(np.abs(a))), 1e-6)
    rms = float(np.sqrt(np.mean(a[act] ** 2))) if act.any() else 1.0
    g = min(target_rms / max(rms, 1e-6), 12.0)
    return np.clip(a * g, -peak, peak).astype(np.float32)


def scene_audio(scene_id):
    """Mixed mono float32 audio for one scene, length == tl.total."""
    tl, wavs = build_timeline(scene_id)
    buf = np.zeros(int(math.ceil(tl.total * SR)) + SR, dtype=np.float32)
    for i, w in enumerate(wavs):
        if w is None:
            continue
        with wave.open(str(w)) as f:
            a = np.frombuffer(f.readframes(f.getnframes()), dtype=np.int16).astype(np.float32) / 32768
        s = int(tl.start(i) * SR)
        buf[s:s + len(a)] += _speech_level(a)
    mod = load_scene(scene_id)
    if hasattr(mod, "sfx"):
        for ts, name in mod.sfx(tl):
            a = _sfx(name) * 0.13
            s = int(ts * SR)
            buf[s:s + len(a)] += a[: len(buf) - s]
    return buf[: int(math.ceil(tl.total * FPS) / FPS * SR)], tl


def write_srt(scene_ids, path):
    def ts(x):
        h, r = divmod(x, 3600)
        m, s = divmod(r, 60)
        return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int((s % 1) * 1000):03d}"
    out, n, off = [], 1, 0.0
    for sid in scene_ids:
        tl, _ = build_timeline(sid)
        for i, it in enumerate(tl.items):
            s = it.caption if isinstance(it, Hold) else it.text
            if s:
                end = tl.end(i)
                cl = tl.clauses(i)
                if cl:   # Kokoro's last-word end runs ~0.1 s past the acoustic end and the wav carries ~0.4 s of trailing silence
                    end = min(end, cl[-1][2] + 0.05)
                out.append(f"{n}\n{ts(off + tl.start(i))} --> {ts(off + end)}\n{s}\n")
                n += 1
        off += math.ceil(tl.total * FPS) / FPS
    Path(path).write_text("\n".join(out), encoding="utf-8")
