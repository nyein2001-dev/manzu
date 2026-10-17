#!/usr/bin/env python3
"""Check a rewritten narration against the sync contract of scenes that already exist.

    check_narration.py BASELINE_script.py CANDIDATE_script.py [--project DIR] [--free SCENE]...
                       [--allow SCENE:IDX]... [--forbid REGEX] [--render]

Scenes are animated against the BASELINE narration (clauses addressed by index, tl.say anchors by word), so a
rewrite may change wording freely but must keep the sync skeleton:
  C1  same scene keys; each non-free scene keeps its item count (ONE extra L item may be appended at the end)
  C2  item i has the same type (L / Hold); Holds keep kind and secs (captions are free)
  C3  every L item keeps its CLAUSE COUNT (clauses split at , . : ; ! ?) and, clause by clause, the same ordered
      numerals and ALL-CAPS acronyms (--allow SCENE:IDX exempts items you will re-sync on purpose)
  C4  every literal tl.say(i, "tok", nth) / tl.say_end(...) in PROJECT/scenes/*.py still resolves in the candidate
  C5  --forbid REGEX: no match allowed in any text or caption (e.g. words of a language you ban)
--free SCENE: scene is exempt from C1-C4 (it will be rebuilt) and skipped by --render.
--render: copy PROJECT to a temp dir, install the candidate as script.py, run `build.py render` on the non-free
scenes with the voice backend taken from the environment (EXPLAINER_TTS_CMD ...) and print the TTS total.
Exit 0 = all checks pass. Static checks never synthesize audio.
"""
import argparse
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def clauses(t):
    return [c for c in re.split(r"(?<=[,.:;!?])\s+", t.strip()) if c]


def sig(c):
    return re.findall(r"\d+|\b[A-Z]{2,5}\b", c)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("baseline")
    ap.add_argument("candidate")
    ap.add_argument("--project", default=".")
    ap.add_argument("--free", action="append", default=[])
    ap.add_argument("--allow", action="append", default=[])
    ap.add_argument("--forbid")
    ap.add_argument("--render", action="store_true")
    a = ap.parse_args()
    proj = Path(a.project).resolve()
    sys.path.insert(0, str(proj))   # a candidate may `from script import L, Hold`
    allow = {(s, int(i)) for s, i in (x.split(":") for x in a.allow)}
    base, cand = load(Path(a.baseline).resolve(), "base_script"), load(Path(a.candidate).resolve(), "cand_script")
    errs, warns = [], []

    for sid in base.SCENES:
        if sid not in cand.SCENES:
            errs.append(f"C1 missing scene {sid}")
    for sid in cand.SCENES:
        if sid not in base.SCENES:
            errs.append(f"C1 unknown scene {sid}")
    for sid, b in base.SCENES.items():
        c = cand.SCENES.get(sid)
        if c is None or sid in a.free:
            continue
        n = len(b)
        if not n <= len(c) <= n + 1:
            errs.append(f"C1 {sid}: {len(c)} items, expected {n} (+1 appended L allowed)")
            continue
        if len(c) == n + 1 and type(c[-1]).__name__ != "L":
            errs.append(f"C1 {sid}: appended item must be L")
        for i in range(n):
            bi, ci = b[i], c[i]
            if type(bi).__name__ != type(ci).__name__:
                errs.append(f"C2 {sid}[{i}] type {type(ci).__name__} != {type(bi).__name__}")
            elif type(bi).__name__ == "Hold":
                if (bi.secs, bi.kind) != (ci.secs, ci.kind):
                    errs.append(f"C2 {sid}[{i}] Hold must keep secs={bi.secs} kind={bi.kind}")
            elif (sid, i) not in allow:
                bc, cc = clauses(bi.text), clauses(ci.text)
                if len(bc) != len(cc):
                    errs.append(f"C3 {sid}[{i}] clause count {len(cc)} != {len(bc)}\n     base: {bc}\n     cand: {cc}")
                else:
                    for k, (x, y) in enumerate(zip(bc, cc)):
                        if sig(x) != sig(y):
                            errs.append(f"C3 {sid}[{i}] clause {k} numerals/acronyms {sig(y)} != {sig(x)}: {y!r}")
                    for cl in cc:
                        if len(cl.split()) > 24:
                            warns.append(f"long clause ({len(cl.split())} words) {sid}[{i}]: {cl[:70]}...")

    call = re.compile(r"tl\.say(?:_end)?\(\s*(\d+)\s*,\s*[\"']([^\"']+)[\"'](?:\s*,\s*(?:nth\s*=\s*)?(\d+))?\s*\)")
    for f in sorted((proj / "scenes").glob("*.py")):
        sid = f.stem
        if sid not in cand.SCENES or sid in a.free:
            continue
        seen = set()
        for m in call.finditer(f.read_text()):
            i, tok, nth = int(m.group(1)), m.group(2), int(m.group(3) or 0)
            if (i, tok, nth) in seen:
                continue
            seen.add((i, tok, nth))
            items = cand.SCENES[sid]
            if i >= len(items) or type(items[i]).__name__ != "L":
                errs.append(f"C4 {sid}: say({i}, {tok!r}) points at a missing / non-L item")
                continue
            pat = re.compile(rf"(?<![\w.]){re.escape(tok)}(?![\w])", re.I)
            hits = sum(len(pat.findall(cl)) for cl in clauses(items[i].text))
            if hits <= nth:
                errs.append(f"C4 {sid}: tl.say({i}, {tok!r}, {nth}) not found in {items[i].text!r}")

    if a.forbid:
        bad = re.compile(a.forbid, re.I)
        for sid, items in cand.SCENES.items():
            for i, it in enumerate(items):
                t = getattr(it, "text", "") + " " + getattr(it, "caption", "")
                for w in bad.findall(t):
                    errs.append(f"C5 {sid}[{i}] forbidden term {w!r}")

    print(f"candidate: {Path(a.candidate).resolve()}")
    for w in warns:
        print("WARN", w)
    for e in errs:
        print("FAIL", e)
    if errs:
        print(f"\n{len(errs)} contract violation(s)")
        sys.exit(1)
    print("contract: PASS (static)")

    if a.render:
        dst = Path(tempfile.mkdtemp(prefix="cand_"))
        shutil.rmtree(dst)
        shutil.copytree(proj, dst, ignore=shutil.ignore_patterns("__pycache__", ".git", ".cache", "out"))
        shutil.copy(Path(a.candidate).resolve(), dst / "script.py")
        work = Path(str(dst) + "_work")
        env = dict(os.environ, EXPLAINER_WORK=str(work), PYTHONDONTWRITEBYTECODE="1")
        ids = [s for s in cand.SCENES if s not in a.free]
        try:
            if ids:
                r = subprocess.run([sys.executable, "build.py", "render", *ids], cwd=dst, env=env,
                                   capture_output=True, text=True)
                print((r.stdout + r.stderr)[-1200:])
                if r.returncode:
                    print("RENDER: FAIL")
                    sys.exit(2)
            r = subprocess.run([sys.executable, "build.py", "tts"], cwd=dst, env=env, capture_output=True, text=True)
            print([l for l in r.stdout.splitlines() if "TOTAL" in l or l.startswith("==")])
            print("RENDER: PASS")
        finally:
            shutil.rmtree(dst, ignore_errors=True)
            shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
