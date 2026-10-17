---
name: manzu-video
description: "Use when asked for a manzu animated video: voice synced word by word to drawn scenes, built offline with pycairo, ffmpeg and a system or local neural voice. Not for LaTeX-typeset maths (use Manim), slide decks, or live-action editing."
license: MIT
metadata:
  version: 1.1.0
  tags: [video, explainer, narration, tts, kokoro, pycairo, ffmpeg, education, animation]
---

# Manzu video

Build an explainer of any length (a 40 s concept clip up to a ~7 min lesson) where every picture appears on the spoken word that explains it.
Stack: pycairo scenes, ffmpeg, macOS `say` or a local neural voice (Kokoro), whisper for QA. No LaTeX, Manim, browser or network service is needed.
Proven on an 8-scene, 6:45 maths explainer and re-proven cold by a fresh agent on a 40 s, 2-scene clip.

## Use / do not use
- Use for a concept video with a script, drawn scenes, prediction pauses and captions, where timing to the voice matters.
- Typeset maths with Manim and LaTeX available: use a Manim workflow instead. Slide decks or screen recordings: other tools.
- The viewer is a child and the user did not ask for a screen activity: offer a no-screen game first; build the video only because it was requested.

## Start
```bash
bash <skill>/scripts/new_project.sh ~/videos/<name>       # engine + 15 s demo scene + plan.md + SCENE_RULES.md; checks pycairo, numpy, pillow, ffmpeg
cd ~/videos/<name>
export EXPLAINER_WORK="$PWD/.cache" PYTHONDONTWRITEBYTECODE=1   # default cache is /tmp/explainer_work; keep caches out of synced folders
python3 build.py final --out out/demo.mp4                  # smoke test with macOS say (about 10 s)
```
Missing Python modules or ffmpeg: report them; install nothing without the user's go-ahead. Add `.cache/` and `out/` to `.gitignore` if the project is a repo.

## Boundaries (conditions, not tone)
- Do without asking: scaffold, write scripts and scenes, render, use macOS `say`, run ffmpeg and an ALREADY CACHED whisper model locally, run subagent pools for scenes and reviews.
- Needs the user's explicit authorization naming the action: installing anything (the Kokoro venv plus about 450 MB of downloads = `scripts/install_kokoro.sh --authorized`), downloading a
  model (check `ls ~/.cache/whisper` first: an uncached whisper model downloads), sending narration to any online TTS, uploading, publishing or posting the video, giving it to the learner.
  Until then the status is "draft for review".
- Personal data: a learner's name never goes into narration, captions, on-screen text, file names or mp4 metadata unless the user asked for it. Before anything is posted publicly, build a
  neutral-name version and prove it clean (`references/qa.md`, "Public release check").
- You cannot listen: say so. Ship at least one sample of the chosen voice (`Voice-Audition/`); ship a comparison pack when choosing among voices. The user chooses the voice.

## Workflow (open the file named when you reach that step)
1. Scaffold, then context and `plan.md` (audience, abilities, arc, colour mapping): `references/workflow.md`.
2. Narration FIRST, spoken style, abbreviations introduced with their full forms in the first 30 s: `references/narration.md`.
3. Voice (free-first ladder, Kokoro, authorization wording, audition): `references/voice.md`.
4. First scene yourself, the rest by file-disjoint workers; every scene follows `SCENE_RULES.md` (copied into the project): `references/workflow.md`.
5. Independent review lenses on the rendered file, fix waves, sync audit with whisper: `references/qa.md`.
6. Deliver `.mp4` + `.srt`, keep earlier versions as `_v1_...`, builder README with rebuild commands.

## Contracts that decide quality
- Timing: a number, answer or label appears at most 0.15 s before the narrator says it and within ~0.4 s after (design target; audit tolerance is in `qa.md`). Spoken equations and lists
  appear piece by piece. Use `tl.say(i, "36")` / `tl.clauses(i)`; no evenly spread beats; no `- 0.3` fudge offsets once timing is exact.
  With a word-aligned voice (Kokoro) `tl.say` is exact; with macOS `say` it is estimated (about +-0.2 s): treat `say` timing as provisional and say so in the report.
- Burned-in captions reveal word by word (they cannot spoil an answer); the `.srt` carries whole-line cues, so say that on prediction lines it can show an answer early.
- Clause contract: the number of clause marks (`, . : ; ! ?`) per line, item order, Hold timing and numerals in `script.py` are frozen once scenes exist. `scripts/check_narration.py` enforces it.
- One colour = one meaning for the whole video. Nothing static > 3 s. Top-right corner clear during Holds. Fades, not hard cuts. Safe area y <= 600.
- Pauses: guess 5-6 s, movement 8 s, multi-step challenge 15 s plus "Pause the video if you need more time." Respect the requested runtime; scenes of 20-70 s.
- Every claim in the script gets an accuracy check; a slogan must describe what the example maximises.

## Done means
`.mp4` decodes without error, 1280x720, chapters = scenes, about -18 LUFS (true peak <= -1 dB); `.srt` text equals the script; a whisper sync audit of the rendered file covers EVERY meaningful
synced event (a 6-min video has 100+, a 40 s clip about ten) with no answer shown > 0.15 s early; the last independent review pass reports no blocker or major; one voice sample shipped;
the builder README lists rebuild commands; no `__pycache__` or caches in synced folders; the final message says what was verified and what was not (audio by ear).

## Pitfalls
- Rewriting narration after scenes exist costs a full re-sync wave: do the natural-narration pass first.
- Whisper timestamps alone mislead (early bias, silence absorption): calibrate against acoustic onsets of the clean TTS wavs.
- Parallel scene workers must not edit `lib.py`/`engine.py`/`script.py`; warm the TTS cache serially (the engine already does) before any parallel render.
- macOS `say` numbers/acronyms: add `SPOKEN_FIX`; for any voice, re-transcribe suspicious lines in isolation.
- The font lacks arrows, check marks, stars and emoji: use `arrow()`, `checkmark()`, `star()`.
- Python 3.14 cannot run kokoro-onnx; the installer uses 3.12.
- Platform limits for posting: X allows 140 s for standard accounts (Premium far longer): cut a part-1 version if the account is standard.
