# Scene rules (read before writing or editing any scene)

Every scene is `scenes/<scene_id>.py` exposing a pure function of time. The engine owns the gradient background,
captions, the hold countdown ring, fades in/out and audio. `scenes/s0_demo.py` is the reference implementation.

```python
from lib import *
def draw(c, t, tl): ...        # REQUIRED. c = cairo context in 1280x720 units; t = seconds since scene start
def sfx(tl): return [(seconds, "pop"|"ding"|"whoosh"|"tick"|"success"), ...]   # OPTIONAL, same moments as visuals
```

## Timing contract (the part that decides whether the video feels right)
- `tl.start(i) / tl.end(i) / tl.dur(i)`: item `i` of the scene's list in `script.py`.
- `tl.say(i, "36", nth=0)`: moment the narrator says that whole word/number (nth = 0-based occurrence). With a
  word-aligned voice (Kokoro) it is exact; with macOS `say` it is estimated from clause timing (about +-0.2 s).
  `tl.clauses(i)[k] = (text, abs_start, abs_end)` are measured clause onsets; `tl.say_end(i, tok)` = end of the clause.
  `python3 preview.py <scene>` prints the measured `voice` rows: that is your sync sheet.
- A number, answer or label must NOT be on screen before the narrator says it. Allowed: appear up to 0.15 s before the
  word so the pop lands on it (answer cards: 0.1 s). Should appear no later than about 0.4 s after. A moving object
  (hop, slide) may start earlier but must LAND on the word.
- A spoken equation or list appears PIECE BY PIECE on its own words ("24", then "x 4", then "= 96"). Showing the whole
  label at the clause start is the most frequent defect in review.
- Never spread beats evenly over a line (`start + dur*k/n`): it ignores lead-in words and drifts 1-3 s.
- Offsets like `- 0.3` compensate for late estimates; with exact word times they make visuals EARLY.
- `tl.say` raises ValueError when the token is not in the line: fix the token or use the clause index.

## Layout and motion
- Safe area x 40..1240, y 40..600. The caption bar sits at the bottom (top edge y = 640 for a one-line caption, 600 for two lines): keep narration lines to two caption lines (about 130 characters). Text >= 24 px (labels), main numbers >= 44 px.
- The engine draws burned-in captions: narration lines reveal word by word as spoken (so a caption cannot show an answer early; `EXPLAINER_CAPTIONS=line` shows whole lines),
  `Hold` captions show whole. Do not draw your own subtitles.
- During `Hold` items keep the top-right corner (x > 1090, y < 200) empty: the engine draws the countdown ring there.
- Nothing static for more than ~3 s while narration continues: idle bob, glow, pulse (but never a shared pulse that
  implies a false fact, e.g. two lights blinking together before the answer).
- Switch panels with 0.25 s cross-fades, not instant `if/elif` swaps (single-frame whole-screen cuts were flagged).
- Do not let outgoing and incoming text overlap during a cross-fade: delay the incoming element by the fade length.
- Pop-in with `pop()`, fades with `fade()`, eased moves with `ease()`/`ease_out()`. Hold the final state; the engine fades out.

## Colour
One colour per recurring idea for the whole video, defined in `plan.md`; never reuse a colour for a second meaning.
Palette constants: CORAL, SKY, GOLD, GREEN, PURPLE, ORANGE, WHITE, DIM, PANEL, PANEL2, INK.

## Glyphs (Arial Rounded MT Bold on macOS)
Available: ASCII plus x-sign (U+00D7), division sign, >=, <=, not-equal (U+2260), bullet, em dash, ellipsis. NOT available (render as empty boxes):
arrows, check marks, stars, middle dot, minus sign (U+2212: use ASCII '-'), emoji. Draw them: `arrow()`, `checkmark()`, `star()`. Draw props (animals, bulbs, fruit,
bags) from cairo shapes.

## Process rules for a scene worker
- Edit only your assigned scene file(s); never `script.py`, `lib.py`, `engine.py`, `build.py`, `preview.py`, other scenes.
  If a narration line looks wrong, say so in your final reply.
- Verify with stills: render at (event_time - 0.2) and (event_time + 0.4) for every synced event and read them: the thing
  must be absent before and present after. Then `--lines` sheet, then `python3 build.py render <scene>` must exit 0.
  Never run `build.py final`.
- Use the project's wrapper if one is named in the task (for example `./with_kokoro.sh python3 preview.py ...`), so the
  voice cache is warm and timings match the real voice.
