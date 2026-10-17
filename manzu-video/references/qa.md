# QA: review lenses, sync audit, audio checks

Reviewers are read-only, run in parallel (one pool), and write scratch only under `/tmp/verify_<name>/`. They must not run `build.py` (shared cache),
edit the project, or trust earlier worker claims. Every finding: severity (blocker/major/minor), scene + scene-time and video-time, evidence (still path
or measured number), minimal fix; unverified = `[INFERENCE]`. Finish with "Verified fixed" and "Checked and clean" lines.

## Lenses for the first review (pass the rendered draft, the project path, and the plan's design rules)
1. **Math / factual accuracy:** every number, set and claim on screen and in the script, recomputed in code (`math.lcm`, etc.), not eyeballed; hop landings vs tick
   marks; counts of props; rules such as "never smaller than". The first pass found no wrong numbers but did find misleading cues and wording.
2. **Language and pedagogy:** language rule from `plan.md`, reading level, definitions before use, idea order, pause lengths, TTS hazards, caption length, redundancy.
3. **Visual QA per scene group** (about 4 scenes each): contact sheets `--every 2` and `--lines`, full-size stills at animation midpoints; overlaps, clipping, text
   < 24 px, top-right corner during Holds, static stretches > 3 s, colour mapping, visuals before/after their narration line, props recognisable, glyph boxes.
4. **Sync audit on the FINAL mp4:** below.
5. **Speech and audio audit:** below.
Later waves: re-run 3-5 on the new file plus a regression look at every claimed fix. The last wave found only minors.

## Sync audit method (what made the measurements trustworthy)
- Prove the mp4 equals the engine first: cross-correlate each chapter's audio with `engine.scene_audio()` (lag 0) and diff a few frames against
  `engine.render_still` at k/30 s.
- Whisper word timestamps are noisy: segment-initial words absorb the lead-in silence (-0.6 to -1.3 s), spelled acronyms and long numbers drift, and there is
  a global bias (about -0.1 s). Calibrate with the median offset, and settle disputes with the ACOUSTIC onset measured on the clean TTS wav. Engine word times
  vs acoustic onsets: median +0.05 s, max 0.18 s with Kokoro alignment.
- For EVERY meaningful synced event (every list item, answer, badge, full-form word, hop landing, chip: about 100 in a 6-min video, about 10 in a 40 s clip; do not pad a short clip to 100):
  map the event to its trigger in the scene code, extract frames at (word - 0.25 s) and (word + 0.45 s) with `ffmpeg -ss T -i file.mp4 -frames:v 1`, and classify.
  Design target (scenes): at most 0.15 s early, ~0.4 s late. Audit tolerance (includes about +-0.1-0.2 s of measurement noise): FAIL when EARLY > 0.3 s (answers > 0.15 s) or LATE > 0.7 s.
  With macOS `say` the engine's word times are estimates: label the result provisional and report the spread instead of claiming exactness.
  Report counts per scene. Visual onset can also be measured by diffing a screen region frame by frame (rendered video trails scene code by about +0.04 to +0.08 s).
- Whisper is slow and, if the model is not cached, downloads it (a download needing authorization): check `ls ~/.cache/whisper` (or the `--model_dir`) first; if `small.en`/`base.en`
  are absent, state the blocker instead of fetching. Chunk per scene (`whisper x.wav --model small.en --language en --fp16 False --word_timestamps True --output_format json`) and
  run chunks in the background.

## Speech and audio audit
- Transcript diff against `script.py` with numbers normalised; distinguish recognition noise from mispronunciation by re-transcribing the isolated cached wav with
  two models (`small.en`, `base.en`). Homophones (Hi/High) and normalisation (24 vs twenty-four) are noise.
- Pace per line from the voice's word spans; flag lines > 190 wpm; no pause inside a sentence > 0.8 s.
- `ffmpeg -i f.mp4 -map 0:a -af ebur128=peak=true -f null -`: target -18 LUFS integrated, true peak <= -1 dB after AAC (loudnorm aims at -1.5; it falls back to dynamic mode when the speech peak
  forbids pure gain: expected). Per-scene loudness within 0.3 LU. No clipping; SFX must not mask words (separate stems: SFX RMS vs word RMS, all words still recognised).
- Joins: wavs start/end ~0, scene joins are digital silence. A/V lengths equal; chapters match scene offsets (`ffprobe -show_chapters`).
- SRT: one cue per spoken line and Hold caption; starts within 0.1 s of speech; cue ends close to the last word. Whole-line cues can show an answer before it is spoken (burned-in
  captions are progressive, the .srt is not): mention it on prediction lines.
- Static-stretch scan: frame-difference of the region above the caption bar at 10 fps; no stretch > 3 s outside Hold countdowns.

## Defect catalogue from the first build (check these first)
Whole equation/label shown at the clause start (should be piece by piece on each spoken number); evenly spread beats; offsets compensating for late estimates (early
once timing is exact); hard whole-screen cuts instead of 0.25 s cross-fades; incoming text drawn over fading outgoing text; a shared pulse on two lights that
implies "they blink together"; labels covered by moving props; text left-bearing swallowing a leading space (`lib.text(align="left")` draws at x minus bearing: place
pieces at explicit x from `text_width`); `checkmark(u=0)` leaving a dot; matching numbers in different columns across two rows (use value columns); appended
spoken lines left over a static final state; glyphs missing from the font (arrows, check, star).

## Public release check (before anything is posted or pushed)
1. Build a SEPARATE neutral-name version; never edit the private one. Replace personal names in narration lines (keep punctuation, so the clause contract still holds), on-screen
   strings (grep `scenes/*.py`), docstrings, `VIDEO_TITLE`, chapter titles and file names.
2. Prove it clean with command output, for every file that will be shared: `ffprobe -v error -show_format -show_chapters f.mp4` (tags), `strings -a f.mp4 | grep -iE "<names>|/Users/"`,
   `grep -iE "<names>" f.srt`, a whisper transcript of the audio, and stills of every screen that used to show a name. `build.py` writes `script.VIDEO_TITLE` into the mp4 `title` tag: check it.
3. Platform length limits: X allows 140 s for standard accounts (Premium longer). Cut a "part 1" at a natural item end plus ~0.8 s, fade picture and sound out over 0.7 s,
   `-map_metadata -1 -map_chapters -1 -metadata title=...`, and write a matching .srt clipped to the cut.
4. Keep shared files in their own folder with a README saying which files to upload; the private files (name in file name, metadata, captions) stay out of it.
5. Repositories: scan for names, absolute home paths, tokens and AI-attribution trailers before the first commit; commit with a no-reply identity; read `git log --format=full` afterwards.

## Stop rule
Done when the last independent pass over the rendered file reports no blocker/major in any lens and the remaining minors are listed or consciously dropped.
