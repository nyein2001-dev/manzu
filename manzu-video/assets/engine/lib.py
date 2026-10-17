"""Shared drawing helpers + Timeline for a manzu video (pycairo, 1280x720 design units).

Scene modules do `from lib import *` and expose:
    def draw(c, t, tl): ...          # REQUIRED. Pure function of time t (seconds since scene start).
    def sfx(tl): return [(sec, "ding"), ...]   # OPTIONAL. names: ding pop whoosh tick success

Background gradient, captions, hold-countdown ring and scene fades are drawn by the engine.
Keep content inside the SAFE AREA: x in [40, 1240], y in [40, 600]. (y>600 is the caption bar.)
"""
import math
import re

import cairo

W, H = 1280, 720
FPS = 30
FONT = "Arial Rounded MT Bold"
SAFE_TOP, SAFE_BOTTOM, SAFE_LEFT, SAFE_RIGHT = 40, 600, 40, 1240


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


# Palette. Give each recurring idea ONE colour for the whole video and never reuse it for something else
# (e.g. first quantity = CORAL, second quantity = SKY, key result = GOLD, success / "good" = GREEN), so the
# colours teach. Write your mapping in plan.md; scenes and reviewers check against it.
BG_TOP, BG_BOT = rgb("#2D2B55"), rgb("#1F1D40")
CORAL, SKY, GOLD, GREEN = rgb("#FF6B6B"), rgb("#4DABF7"), rgb("#FFD93D"), rgb("#6BCB77")
WHITE, DIM, PANEL, PANEL2 = rgb("#F8F7FF"), rgb("#8E8CC4"), rgb("#3B3970"), rgb("#4A4787")
PURPLE, INK, ORANGE = rgb("#B197FC"), rgb("#1F1D40"), rgb("#FFA94D")


# ---------------------------------------------------------------- math / easing
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def lerp(a, b, u):
    return a + (b - a) * u


def prog(t, t0, dur):
    """0..1 progress of a window that starts at t0 and lasts dur."""
    if dur <= 0:
        return 1.0 if t >= t0 else 0.0
    return clamp((t - t0) / dur)


def ease(u):
    return u * u * (3 - 2 * u)


def ease_out(u):
    return 1 - (1 - u) ** 3


def ease_back(u):
    """Overshoot pop-in: 0 -> ~1.1 -> 1."""
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * (u - 1) ** 3 + c1 * (u - 1) ** 2


def pulse(t, period=1.0):
    return 0.5 + 0.5 * math.sin(2 * math.pi * t / period)


def pop(t, t0, dur=0.45):
    """Scale factor 0 -> overshoot -> 1 starting at t0 (0 before t0)."""
    return 0.0 if t < t0 else ease_back(prog(t, t0, dur))


def fade(t, t0, dur=0.4):
    """Alpha 0 -> 1 starting at t0."""
    return ease_out(prog(t, t0, dur))


# ---------------------------------------------------------------- primitives
def _paint(c, fill, stroke, lw, alpha):
    if fill is not None:
        c.set_source_rgba(*fill, alpha)
        if stroke is not None:
            c.fill_preserve()
        else:
            c.fill()
    if stroke is not None:
        c.set_source_rgba(*stroke, alpha)
        c.set_line_width(lw)
        c.set_line_join(cairo.LINE_JOIN_ROUND)
        c.stroke()


def rrect_path(c, x, y, w, h, r):
    r = max(0.0, min(r, w / 2, h / 2))
    c.new_sub_path()
    c.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    c.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    c.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    c.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    c.close_path()


def rrect(c, x, y, w, h, r=16, fill=PANEL, stroke=None, lw=3, alpha=1.0):
    """Rounded rectangle, (x, y) = top-left."""
    rrect_path(c, x, y, w, h, r)
    _paint(c, fill, stroke, lw, alpha)


def rrect_c(c, cx, cy, w, h, r=16, fill=PANEL, stroke=None, lw=3, alpha=1.0):
    """Rounded rectangle centred on (cx, cy)."""
    rrect(c, cx - w / 2, cy - h / 2, w, h, r, fill, stroke, lw, alpha)


def circle(c, x, y, r, fill=PANEL, stroke=None, lw=3, alpha=1.0):
    if r <= 0:
        return
    c.new_sub_path()
    c.arc(x, y, r, 0, 2 * math.pi)
    _paint(c, fill, stroke, lw, alpha)


def ellipse(c, x, y, rx, ry, fill=PANEL, stroke=None, lw=3, alpha=1.0):
    if rx <= 0 or ry <= 0:
        return
    c.save()
    c.translate(x, y)
    c.scale(rx, ry)
    c.new_sub_path()
    c.arc(0, 0, 1, 0, 2 * math.pi)
    c.restore()
    _paint(c, fill, stroke, lw, alpha)


def line(c, x1, y1, x2, y2, color=WHITE, lw=4, alpha=1.0, dash=None):
    c.save()
    c.set_source_rgba(*color, alpha)
    c.set_line_width(lw)
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    if dash:
        c.set_dash(dash)
    c.move_to(x1, y1)
    c.line_to(x2, y2)
    c.stroke()
    c.restore()


def polyline(c, pts, color=WHITE, lw=4, alpha=1.0, closed=False, fill=None):
    c.save()
    c.move_to(*pts[0])
    for p in pts[1:]:
        c.line_to(*p)
    if closed:
        c.close_path()
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    _paint(c, fill, color if lw else None, lw, alpha)
    c.restore()


def arrow(c, x1, y1, x2, y2, color=WHITE, lw=5, head=18, alpha=1.0):
    ang = math.atan2(y2 - y1, x2 - x1)
    bx, by = x2 - head * 0.8 * math.cos(ang), y2 - head * 0.8 * math.sin(ang)
    line(c, x1, y1, bx, by, color, lw, alpha)
    pts = [(x2, y2),
           (x2 - head * math.cos(ang - 0.45), y2 - head * math.sin(ang - 0.45)),
           (x2 - head * math.cos(ang + 0.45), y2 - head * math.sin(ang + 0.45))]
    polyline(c, pts, color, 0, alpha, closed=True, fill=color)


def arc_path(c, x1, y1, x2, y2, height, steps=24):
    """Points of a parabola-like hop from (x1,y1) to (x2,y2) with apex `height` above the chord."""
    pts = []
    for i in range(steps + 1):
        u = i / steps
        pts.append((lerp(x1, x2, u), lerp(y1, y2, u) - 4 * height * u * (1 - u)))
    return pts


def hop_pos(x1, y1, x2, y2, height, u):
    """Position along a hop for u in 0..1."""
    return lerp(x1, x2, u), lerp(y1, y2, u) - 4 * height * u * (1 - u)


def glow(c, x, y, r, color=GOLD, alpha=0.5):
    if r <= 0 or alpha <= 0:
        return
    g = cairo.RadialGradient(x, y, 0, x, y, r)
    g.add_color_stop_rgba(0, *color, alpha)
    g.add_color_stop_rgba(1, *color, 0)
    c.save()
    c.set_source(g)
    c.new_sub_path()
    c.arc(x, y, r, 0, 2 * math.pi)
    c.fill()
    c.restore()


def star(c, x, y, r, fill=GOLD, alpha=1.0, rot=0.0, points=5, inner=0.45):
    pts = []
    for i in range(points * 2):
        rr = r if i % 2 == 0 else r * inner
        a = rot - math.pi / 2 + i * math.pi / points
        pts.append((x + rr * math.cos(a), y + rr * math.sin(a)))
    polyline(c, pts, fill, 0, alpha, closed=True, fill=fill)


# ---------------------------------------------------------------- text
def _face(c, size):
    c.select_font_face(FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
    c.set_font_size(size)


def text_width(c, s, size):
    c.save()
    _face(c, size)
    w = c.text_extents(s)[4]
    c.restore()
    return w


def text(c, s, x, y, size=40, color=WHITE, align="center", alpha=1.0, valign="middle"):
    """Draw text. align: left|center|right. valign: middle (digit-height centred) | baseline.
    Returns advance width. Scene text >= 24 px (labels), main numbers >= 44 px (see SCENE_RULES.md)."""
    if not s or alpha <= 0:
        return 0.0
    c.save()
    _face(c, size)
    xb, _, w, _, xa, _ = c.text_extents(s)
    if align == "center":
        px = x - (xb + w / 2)
    elif align == "right":
        px = x - (xb + w)
    else:
        px = x - xb
    if valign == "middle":
        _, yb, _, h, _, _ = c.text_extents("0")
        py = y - (yb + h / 2)
    else:
        py = y
    c.move_to(px, py)
    c.set_source_rgba(*color, alpha)
    c.show_text(s)
    c.restore()
    return xa


def wrap(c, s, size, maxw):
    c.save()
    _face(c, size)
    words, lines, cur = s.split(), [], ""
    for w_ in words:
        trial = (cur + " " + w_).strip()
        if c.text_extents(trial)[4] <= maxw or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w_
    if cur:
        lines.append(cur)
    c.restore()
    return lines


def tile(c, cx, cy, label, size=44, fill=CORAL, fg=INK, scale=1.0, alpha=1.0, w=None, h=None,
         stroke=None, lw=4):
    """Rounded number tile centred on (cx, cy); `scale` animates pop-in."""
    if scale <= 0 or alpha <= 0:
        return
    tw = text_width(c, label, size)
    w = w or max(size * 1.35, tw + size * 0.7)
    h = h or size * 1.35
    c.save()
    c.translate(cx, cy)
    c.scale(scale, scale)
    rrect_c(c, 0, 0, w, h, r=h * 0.28, fill=fill, stroke=stroke, lw=lw, alpha=alpha)
    text(c, label, 0, 0, size, fg, alpha=alpha)
    c.restore()


def badge(c, cx, cy, label, size=34, fill=GOLD, fg=INK, alpha=1.0, scale=1.0):
    tile(c, cx, cy, label, size, fill, fg, scale, alpha, h=size * 1.5)


def checkmark(c, x, y, s=24, color=GREEN, lw=7, alpha=1.0, u=1.0):
    if u <= 0 or alpha <= 0:
        return
    pts = [(x - s, y), (x - s * 0.35, y + s * 0.7), (x + s, y - s * 0.75)]
    # draw partial path by progress u
    total = math.dist(pts[0], pts[1]) + math.dist(pts[1], pts[2])
    d = total * clamp(u)
    c.save()
    c.set_source_rgba(*color, alpha)
    c.set_line_width(lw)
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    c.set_line_join(cairo.LINE_JOIN_ROUND)
    c.move_to(*pts[0])
    l1 = math.dist(pts[0], pts[1])
    if d <= l1:
        f = d / l1
        c.line_to(lerp(pts[0][0], pts[1][0], f), lerp(pts[0][1], pts[1][1], f))
    else:
        c.line_to(*pts[1])
        f = (d - l1) / (total - l1)
        c.line_to(lerp(pts[1][0], pts[2][0], f), lerp(pts[1][1], pts[2][1], f))
    c.stroke()
    c.restore()


def bg(c):
    g = cairo.LinearGradient(0, 0, 0, H)
    g.add_color_stop_rgb(0, *BG_TOP)
    g.add_color_stop_rgb(1, *BG_BOT)
    c.set_source(g)
    c.paint()


# ---------------------------------------------------------------- timeline
_TOKEN = re.compile(r"[A-Za-z0-9']+")
_ONES = ("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen "
         "sixteen seventeen eighteen nineteen").split()
_TENS = "zero ten twenty thirty forty fifty sixty seventy eighty ninety".split()


def _num_words(n):
    if n < 20:
        return _ONES[n]
    if n < 100:
        return _TENS[n // 10] + ("" if n % 10 == 0 else " " + _ONES[n % 10])
    if n < 1000:
        return _ONES[n // 100] + " hundred" + ("" if n % 100 == 0 else " " + _num_words(n % 100))
    return str(n)


def _spoken(s):
    """Approximate spoken form of a narration clause: numerals as words, ALL-CAPS acronyms spelled out."""
    import re
    s = re.sub(r"\b[A-Z]{2,5}\b", lambda m: " ".join(m.group()), s)
    return re.sub(r"\d+", lambda m: _num_words(int(m.group())), s)


def _spoken_fraction(clause, idx):
    """Fraction (0..1) of the clause's spoken length that comes before character index idx."""
    return len(_spoken(clause[:idx])) / max(1, len(_spoken(clause)))


class Timeline:
    """Start/end times (seconds since scene start) of every item in the scene's script list."""

    LEAD = 0.5   # silence before first item (fade-in)
    TAIL = 0.6   # silence after last item (fade-out)

    def __init__(self, items, durs, marks=None, words=None):
        """marks[i] = [(clause_text, start_rel, end_rel), ...] measured from the TTS audio of item i
        (None for silent Hold items); times are seconds from the start of that item.
        words[i] = [(token, start_rel, end_rel), ...] for every [A-Za-z0-9']+ token of the line, in
        order, when the voice backend can align words (Kokoro); else None (say() then estimates)."""
        self.items = items
        self._marks = marks or [None] * len(items)
        self._words = words or [None] * len(items)
        self._s, self._e = [], []
        t = self.LEAD
        for it, d in zip(items, durs):
            self._s.append(t)
            t += d
            self._e.append(t)
            t += getattr(it, "gap", 0.0)
        self.total = t + self.TAIL

    def start(self, i):
        return self._s[i]

    def end(self, i):
        return self._e[i]

    def dur(self, i):
        return self._e[i] - self._s[i]

    def at(self, t):
        """Index of the item whose [start, end) contains t, else None."""
        for i, (s, e) in enumerate(zip(self._s, self._e)):
            if s <= t < e:
                return i
        return None

    def u(self, i, t):
        """0..1 progress of item i at time t."""
        return prog(t, self.start(i), self.dur(i))

    def word_times(self, i):
        """[(char_end, abs_start), ...] for every [A-Za-z0-9']+ token of L item i's text, in order (cached).
        Exact with a word-aligned voice (Kokoro); otherwise estimated from measured clause onsets and spoken
        length (about +-0.2 s). The engine uses it to reveal burned-in captions word by word."""
        cache = self.__dict__.setdefault("_wt", {})
        if i in cache:
            return cache[i]
        text = self.items[i].text
        toks = list(_TOKEN.finditer(text))
        w = self._words[i]
        if w and len(w) == len(toks):
            out = [(m.end(), self._s[i] + w[k][1]) for k, m in enumerate(toks)]
        else:
            spans, pos, out = [], 0, []
            for tx, a, b in self.clauses(i):
                j = text.find(tx, pos)
                spans.append((j, tx, a, b))
                pos = j + len(tx)
            for m in toks:
                for j, tx, a, b in spans:
                    if j <= m.start() < j + len(tx):
                        out.append((m.end(), a + (b - a) * _spoken_fraction(tx, m.start() - j)))
                        break
                else:
                    out.append((m.end(), self._s[i]))
        cache[i] = out
        return out

    # -- voice-accurate sync -------------------------------------------------
    def clauses(self, i):
        """Spoken clauses of item i (split at , . : ; ! ?) as [(text, abs_start, abs_end)]."""
        m = self._marks[i]
        if not m:
            return []
        s = self._s[i]
        return [(tx, s + a, s + b) for tx, a, b in m]

    def _find(self, i, token, nth):
        import re
        pat = re.compile(rf"(?<![\w.]){re.escape(token)}(?![\w])", re.I)
        tokre = re.compile(r"[A-Za-z0-9']+")
        hits, before = [], 0
        for tx, a, b in self.clauses(i):
            for m in pat.finditer(tx):
                hits.append((tx, a, b, _spoken_fraction(tx, m.start()),
                             before + len(tokre.findall(tx[:m.start()]))))
            before += len(tokre.findall(tx))
        if len(hits) <= nth:
            raise ValueError(f"item {i}: token {token!r} (occurrence {nth}) not found in "
                             f"{[c[0] for c in self.clauses(i)]}")
        return hits[nth]

    def say(self, i, token, nth=0):
        """Absolute time at which the voice SAYS `token` (whole word/number, nth occurrence, 0-based)
        in item i. Exact when the backend aligns words (Kokoro); otherwise the clause onset from the
        audio refined by the token's position inside its clause.
        Use it to make a visual appear exactly when the narrator says it, e.g. tl.say(7, "36")."""
        _, a, b, f, ordinal = self._find(i, token, nth)
        w = self._words[i]
        if w and ordinal < len(w):
            return self._s[i] + w[ordinal][1]
        return a + (b - a) * f

    def say_end(self, i, token, nth=0):
        """Absolute time at which the clause containing `token` ends (voice finished the phrase)."""
        return self._find(i, token, nth)[2]
