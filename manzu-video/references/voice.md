# Voice: free-first ladder, backends, Kokoro, authorization

Default stance: free resources first. Installs, downloads and any upload of narration need the user's explicit authorization for that action.

## The ladder
1. **Installed, offline, free:** macOS `say` (default backend, `EXPLAINER_VOICE`, `EXPLAINER_RATE`). A default macOS install ships compact/Eloquence voices (for example Samantha,
   Flo, Sandy, Shelley, Eddy, Reed, Rocko, Karen, Moira, Daniel); check yours with `say -v '?'`. Robotic; fine for drafts and smoke tests.
2. **Free local download (ask first):**
   - **Kokoro-82M** (Apache-2.0, ONNX on CPU, offline, no text leaves the Mac): the recommended neural voice. `scripts/install_kokoro.sh` (dry run without
     `--authorized`). Installs into `/tmp/kokoro-venv` + `/tmp/kokoro-models` only (kokoro-onnx 0.6.1, Python 3.12; NOT 3.14), 325 MB + 28 MB,
     sha256-checked. Undo = delete the two folders. /tmp is cleared sometimes: re-run the installer.
   - Apple Enhanced/Premium voices (Zoe, Ava, Samantha Enhanced, Evan...): free, System Settings > Accessibility > Read & Speak > System voice > info.
     License (macOS SLA 2F) allows personal/non-commercial use only; Siri voices and Personal Voice cannot be rendered to files. Names/availability: confirm
     with `say -v '?'` after the download. Works through the same `EXPLAINER_VOICE`.
   - Piper (`piper-tts`, GPL engine, plain audiobook voice) is the conservative fallback; heavier models (Qwen3-TTS, Chatterbox, F5-TTS, Orpheus, Dia)
     were judged impractical for ~60 short lines; F5-TTS weights are non-commercial.
3. **Online (needs explicit authorization, sends the sentences out):** edge-tts (unofficial Microsoft endpoint, no SLA, unclear commercial terms), Azure Speech F0
   (account + card), Google Cloud TTS (billing account), Amazon Polly, gTTS (Google Translate voice). Strip personal names before any upload.
4. Paid: last.

Authorization wording to propose (one action, exact scope): "I authorize installing Kokoro-82M in /tmp/kokoro-venv and /tmp/kokoro-models
(kokoro-onnx 0.6.1; about 450 MB download: ~354 MB model files from github.com/thewh1teagle/kokoro-onnx plus ~100 MB of Python packages). No narration text is sent anywhere."

## Backend contract (`EXPLAINER_TTS_CMD`)
Command line receives `<in1.txt> <out1.wav> [<in2.txt> <out2.wav> ...]`: UTF-8 text in, wav out (any rate; ffmpeg converts to 44.1 kHz mono). The engine passes
ALL missing lines of a scene in ONE call so a model loads once (63 lines of Kokoro = 86 s). Optional sidecar `<out>.timings.json` =
`{"t": [[phoneme, start_s, end_s], ...], "k": [[token, phonemes_of_that_token_alone], ...]}` turns on exact word alignment: the engine aligns the audio phoneme
string to the per-token phoneme strings with difflib, so it survives espeak merging words ("in the" -> one word) and "216" -> "two hundred sixteen".
Counting phoneme words per token fails for exactly those cases. Without a sidecar (macOS `say`) clauses are located from silences and `tl.say` estimates inside
a clause (+-0.2 s, worse for long numbers and spelled acronyms).
The cache key hashes the backend command, the backend script's bytes and every `KOKORO_*` variable, so changing voice, speed or script re-synthesises.
Never edit cached wavs by hand.

## Kokoro settings that worked
`af_heart` (warm US female, upstream grade A; alternatives af_bella, af_sarah, bf_emma), `KOKORO_SPEED=0.92`, `KOKORO_SENTENCE_PAUSE=0.35`,
`KOKORO_CLAUSE_PAUSE=0.2`. Upstream warns that very short utterances sound weak. Its level is about 8 dB below `say` (the engine level-matches each
line to a common speech RMS before mixing). Run with `./with_kokoro.sh <command>` (sets the cache dir, the command and `PYTHONDONTWRITEBYTECODE`).

## Audition (the audio cannot be judged by ear in an automated run: the user decides)
Always ship one ~20 s sample of the chosen voice (hook + one number list) as `Voice-Audition/<voice>.m4a` (`ffmpeg -c:a aac -b:a 128k`), even for the default `say` voice. When a neural
voice was chosen among several, ship the same read in each candidate plus the old voice for comparison, and a README line on how to rebuild with another voice. State plainly that the
audio was not auditioned by ear; a whisper intelligibility transcript of the sample is the only automatic check.
