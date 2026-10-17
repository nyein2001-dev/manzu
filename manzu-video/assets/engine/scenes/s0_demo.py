"""Demo scene = reference implementation of the sync patterns. Replace it with real scenes.

Patterns shown:
  * title pops at the start of the first line
  * an object appears exactly when the narrator SAYS its number: tl.say(item, "2")
  * a hold item: the engine draws the countdown ring; the scene keeps the top-right corner clear
  * celebration + sfx on a spoken word
sfx(tl) must use the SAME moments as the visuals.
"""
from lib import *

NUMS = ["1", "2", "3"]


def _t(tl, k):
    """Moment the narrator says the k-th number of item 1 (word-exact with Kokoro, estimated with `say`)."""
    return tl.say(1, NUMS[k])


def draw(c, t, tl):
    s = pop(t, tl.start(0) + 0.1, 0.6)
    if s > 0:
        c.save()
        c.translate(640, 110)
        c.scale(s, s)
        text(c, "Counting together", 0, 0, 72, WHITE)
        c.restore()

    for k, n in enumerate(NUMS):
        when = _t(tl, k)
        # appear up to 0.1 s BEFORE the word so the pop lands on it; never earlier than 0.15 s before
        tile(c, 400 + 240 * k, 330, n, 96, (CORAL, SKY, GOLD)[k], INK, scale=pop(t, when - 0.1, 0.45))

    # hold item 3: pulsing prompt; top-right corner (x>1090, y<200) stays clear for the countdown ring
    a = fade(t, tl.start(3), 0.3) * (1 - fade(t, tl.end(3), 0.3))
    if a > 0:
        text(c, "Count out loud!", 640, 500, 44, GOLD, alpha=a * (0.7 + 0.3 * pulse(t, 1.0)))

    # celebration on the word "Great"
    g = tl.say(4, "Great")
    for i in range(8):
        u = prog(t, g, 1.8)
        if u > 0:
            star(c, 200 + 125 * i, 150 + 380 * ease(u) * (0.6 + 0.4 * (i % 3) / 2), 16, GOLD, alpha=1 - u, rot=u * 3 + i)


def sfx(tl):
    return [(_t(tl, k) - 0.1, "pop") for k in range(len(NUMS))] + [(tl.say(4, "Great"), "success")]
