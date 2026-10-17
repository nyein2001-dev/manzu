# Narration craft and the clause contract

## Write it to be spoken
- Contractions (let's, you'll, it's), direct questions to the viewer, short reactions ("Look at that."), 4-14 words per sentence, varied rhythm.
- No parentheses, ellipses, emoji, e.g./i.e., or dashes: a dash makes an unmeasured pause the animation cannot address.
- No hollow praise ("You thought it through!" when nothing was seen), no baby talk, no culture-specific idioms, no sarcasm.
- Avoid utterances under about 4 words standing alone before silence ("Detectives without hats!"): neural voices read them thin or clipped.
- Repeat key terms with different carrier sentences. Watch tics: "Let's" opened 10 lines and "Now" 5 in one merged draft.
- Seams: the last line of scene N leads into scene N+1 (an appended transition line is allowed: "Now let's use factors to share some fruit.").
- Prediction moments: ask ("What's your guess?"), then a `Hold(..., "think")`. Movement break for children: `Hold(8, "move")` after a line that
  tells them what to do ("Stand up, jump, and say ... I'll wait."). Multi-step challenge: 15 s plus the line "Pause the video if you need more time."
  Observed minimums: guess 5-6 s, movement 8 s, four-list challenge 15 s.
- Runtime check: `python3 build.py tts` prints TOTAL. Target <= the plan's ceiling; cut wordy carriers first.

## Terminology
- Language rule (for example "English terms only"): name the banned local-language terms once in `plan.md`, never in narration, captions or scene text
  (`check_narration.py --forbid "term1|term2"`).
- Abbreviations: say the abbreviation, then "stands for", then the full form, in the first 30 s ("Detective LCM. That stands for Least Common
  Multiple."), and show the full form on screen word by word as spoken. Repeat the full form once when the term is formally defined.
- Define a term before using it; use one name per idea for the whole video.

## The clause contract (why punctuation is frozen)
The engine splits each `L` line at `, . : ; ! ?` into clauses and measures each clause's real onset in the audio. Scene code addresses
`tl.clauses(i)[k]` or `tl.say(i, "word")`. A rewrite that adds or removes one of those marks, or changes a numeral, silently desyncs
the scene. Keep: item count, item types, Hold secs/kind, clause count per line, ordered numerals/acronyms per clause.
`scripts/check_narration.py BASELINE CANDIDATE --project DIR` enforces this; `--allow scene:idx` marks items you will re-sync on purpose.
Digits stay digits ("12", not "twelve"). Acronyms: put the respelling in `SPOKEN_FIX` ({"LCM": "L C M"}).

## Words and phrases TTS mishears (found by transcribing each cached line again with whisper)
- "Stand up, hop, and say" -> heard "pop": use "jump". A name placed right after "up," ("You're up, <Name>!") was heard with a glued consonant (the /p/ carried into the name): reword so
  the name does not follow a word ending in a plosive ("Your turn, <Name>!").
- "1 and itself" -> "one in itself": "and" is squeezed to ~0.08 s. Rewording did not help; a comma did: "1, and the number itself."
- Check every acronym, number list and name this way: transcribe the isolated line wav, not the mixed track (sound effects confuse whisper).
- Pace: Kokoro `speed=0.92` and `sentence_pause=0.35`, `clause_pause=0.2` suited a children's video (average 163 wpm). Lines of 200+ wpm articulation
  were dense definitions; split them or add a comma.

## Accuracy traps seen in educational scripts (run an accuracy lens on every statement)
- A slogan can contradict the example it summarises ("GCF = biggest fair share" while 6 bags is the SMALLEST share per bag): phrase the rule
  in the quantity the puzzle maximises ("the biggest number of equal groups").
- "Multiple means skip counting" confuses a number with an action: "a number you land on when you skip count".
- Prime: "exactly two factors: 1 and the number itself" (not "divisible by 1 and itself", which fits 1).
- Keyword shortcuts ("if you hear share ... use GCF") over-generalise: qualify ("share evenly", "the most equal groups").
- Say what "first time together" excludes (the shared start), and state domains ("any two counting numbers").
- Never show a result before it is said; a result shown early also gives away the prediction the viewer is supposed to make.
