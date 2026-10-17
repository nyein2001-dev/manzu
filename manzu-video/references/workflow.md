# Workflow: from request to delivered video

Reference run: an 8-scene, 6:45 LCM/GCF explainer (Kokoro voice) and a 2-scene, about 40 s "What is a fraction?" cold-start test. The engine in
`assets/engine/` is the canonical, generalised result of the first; `assets/engine/scenes/s0_demo.py` is the smallest working scene.

## 1. Scaffold, then context and plan
Run `scripts/new_project.sh <dir>` FIRST: the next steps edit the files it creates. Then:
- Context: read whatever project brief or instructions the user points to; use only learner facts the user gave (age band, reading level, attention profile); add none.
- Teaching moves that worked: story, choices, prediction, reflection, short bursts, one idea at a time.
- Ask only what changes the video: audience age, the 1-3 abilities after watching, terminology rule, length ceiling, voice preference. Decide the rest, state the choice, proceed.
- Fill `plan.md` from the template. Order of ideas for a concept video: hook that names the key terms with their full forms -> prerequisite tool -> puzzle 1 with a prediction pause ->
  reveal and term -> second puzzle -> shortcut -> side-by-side recap with trigger words -> challenge with a reflection question. One idea per scene (about 20-70 s). Fix the colour mapping
  here and mark which spoken word triggers each visual. Runtime: 6-7 min is long for young viewers; name one chapter that can be cut without losing a concept.

## 2. Narration BEFORE scenes
Write `script.py` in the natural spoken style (`narration.md`) and settle the abbreviation introduction first. Rewriting narration after the scenes exist forces a re-sync of every scene
(it did once: a full extra worker wave). Then `python3 build.py tts` prints the timeline and TOTAL.

## 3. Foundation (orchestrator, not workers)
Write the FIRST scene yourself as the reference implementation (it proves the API on the real narration); smoke-render. Any change to `lib.py`/`engine.py` happens now:
workers must not edit shared files.

## 4. Scenes in parallel
Use file-disjoint subagents when the harness has them (max 4 concurrent); otherwise write scenes sequentially. One worker owns 1-2 scenes (about 45-70 s of video each), one file each.
Worker context = goal; project path (quote it); read-first list (`plan.md`, `SCENE_RULES.md`, `lib.py`, the reference scene, the `script.py` keys for their scenes); the contract (edit only
your file, timing rule, colours, safe area); the verification they MUST run (stills before/after each sync event, `--lines` sheet, `build.py render <scene>` exits 0, never `final`); a short
final-reply format. Give workers the voice wrapper (`./with_kokoro.sh ...`) so timings match the real voice. Worker output is evidence, not truth: you re-verify.

## 5. Integrate
`build.py final --out <dir>/draft.mp4` (scenes render in parallel; about 40 s for 6 min). Check duration, chapters, loudness, decode.

## 6. Review pool, then fix waves (`qa.md`)
One reviewer per lens, read-only, adversarial, evidence-backed. Fix by scene owner (file-disjoint again). Re-verify the RENDERED file, not the workers' claims. Repeat until only minors remain;
then one polish wave for the minors worth fixing. The first build needed four fix waves; the recurring defects were whole equations shown before they are spoken and estimate-based sync,
both addressed by the engine and `SCENE_RULES.md`. A short clip needs one review pass, not five lenses of ceremony: scale the review to the video.

## 7. Narration rewrite after the fact (only if asked)
Candidates by persona (coach / storyteller / Socratic) each passing `scripts/check_narration.py`, judged by a panel (naturalness, pedagogy + accuracy, TTS deliverability + runtime), merged by
scene, then a re-sync pool. Structural wishes (changing clause counts) are allowed per item (`--allow scene:idx`) when that scene is re-synced in the same wave.

## 8. Deliver
- Final `.mp4` + `.srt`; keep earlier versions beside it as `_v1_<what-changed>`; a `Voice-Audition/` folder (one sample of the chosen voice at least; a comparison pack when a neural voice
  was chosen among several); a builder README (rebuild commands, voice install note).
- No `__pycache__`, caches or model files in synced or committed folders.
- Update project tracking notes only if the user asked for that. Status wording: "draft for review", never "approved" or "sent".
- Posting publicly: run the public release check in `qa.md` on a neutral-name build; check the platform's video length limit (X: 140 s standard) and cut a part-1 version if needed.
- Final message: result first, what was verified, what was NOT (audio was not auditioned by ear), decisions left for the user.
