"""Narration for the video. Single source of truth for every spoken word.

L(text, gap)   one spoken line; `gap` = silence after it (seconds, on top of ~0.4 s of trailing silence in the wav).
Hold(secs, kind, caption)  silent pause for the viewer; kind "think" or "move"; the engine draws a countdown ring
               in the top-right corner (keep x>1090, y<200 clear in scenes) and shows `caption`.

Scene code addresses items by LIST INDEX: tl.start(i), tl.say(i, "36"), tl.clauses(i)[k]. Therefore:
  * never insert / reorder items after scenes exist (append only), and
  * keep the punctuation marks `, . : ; ! ?` of a line: a clause is the text between them, and scene code
    may address clauses by index. Changing the mark count changes the clause count and breaks sync.
Digits stay digits ("12", not "twelve"): scenes sync on the numeral token.

SPOKEN_FIX maps tokens the voice would read badly to a speakable respelling (applied to the text sent to TTS only,
captions keep the original). Spell acronyms letter by letter here.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class L:
    text: str
    gap: float = 0.5


@dataclass(frozen=True)
class Hold:
    secs: float
    kind: str = "think"  # "think" | "move"
    caption: str = ""


VIDEO_TITLE = "Counting together"          # file title metadata
SPOKEN_FIX = {}                             # e.g. {"LCM": "L C M"}

SCENES = {
    # ------------------------------------------------------------------ 0   (demo scene: replace)
    "s0_demo": [
        L("Hi! Let's count together.", 0.5),                                  # 0
        L("Count with me: 1, 2, 3.", 0.4),                                    # 1  clauses: 'Count with me:' | '1,' | '2,' | '3.'
        L("Your turn. Count to 3 again, out loud.", 0.3),                     # 2
        Hold(4, "move", "Count out loud: 1, 2, 3!"),                          # 3
        L("Great job!"),                                                      # 4
    ],
}

TITLES = {                                  # chapter titles in the mp4
    "s0_demo": "Counting",
}
