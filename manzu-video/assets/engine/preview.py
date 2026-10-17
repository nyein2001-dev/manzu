#!/usr/bin/env python3
"""Render stills of a scene for visual QA.

    python3 preview.py s0_demo 5,10.5,20     # PNG per time (scene seconds) -> $EXPLAINER_WORK/preview/
    python3 preview.py s0_demo --every 2     # contact sheet (3 columns) of the whole scene every 2 s
    python3 preview.py s0_demo --lines       # one still per script item, taken 85% into the item (settled state)

Prints the output path(s) and the timeline table. Open PNGs with the `read` tool to look at them.
"""
import argparse
import math
import os

from PIL import Image, ImageDraw

import engine
from engine import WORK


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scene")
    ap.add_argument("times", nargs="?", default="")
    ap.add_argument("--every", type=float)
    ap.add_argument("--lines", action="store_true")
    a = ap.parse_args()
    out = WORK / "preview"
    out.mkdir(exist_ok=True)
    tl, _ = engine.build_timeline(a.scene)
    print(f"{a.scene}: total {tl.total:.2f}s")
    for i, it in enumerate(tl.items):
        label = getattr(it, "text", None) or f"<{it.kind} hold> {it.caption}"
        print(f"  [{i:2d}] {tl.start(i):6.2f}-{tl.end(i):6.2f}  {label[:80]}")
        for tx, ca, cb in tl.clauses(i):
            print(f"         voice {ca:6.2f}-{cb:6.2f}  {tx}")
    if a.every or a.lines:
        if a.lines:
            ts = [tl.start(i) + 0.85 * tl.dur(i) for i in range(len(tl.items))]
        else:
            ts = [k * a.every for k in range(int(tl.total / a.every) + 1)]
        w, h = 640, 360
        cols = 3
        rows = math.ceil(len(ts) / cols)
        sheet = Image.new("RGB", (cols * w, rows * h), "black")
        d = ImageDraw.Draw(sheet)
        for k, t in enumerate(ts):
            p = out / f"_tmp_{os.getpid()}.png"
            engine.render_still(a.scene, min(t, tl.total - 0.05), p)
            im = Image.open(p).convert("RGB").resize((w, h))
            sheet.paste(im, ((k % cols) * w, (k // cols) * h))
            d.text(((k % cols) * w + 8, (k // cols) * h + 6), f"t={t:.1f}", fill="white")
        path = out / f"{a.scene}_sheet.png"
        sheet.save(path)
        print(path)
    for tok in filter(None, a.times.split(",")):
        path = out / f"{a.scene}_{float(tok):06.2f}.png"
        engine.render_still(a.scene, float(tok), path)
        print(path)


if __name__ == "__main__":
    main()
