# SENTINEL cinematic rebuild

This is a new 172-second edit. The rejected film and all original footage, models, narration and compositions are preserved.

## Files

- `SENTINEL_Cinematic_Rebuild_1080p.mp4`: rebuilt final cut, after QA.
- `STORYBOARD.md`: complete timed visual/narration/evidence plan.
- `NARRATION-RECORDING-SCRIPT.md`: final copy and pronunciation guide.
- `VOICE-AUDITION-REPORT.md`: three voice auditions, measured checks and limitations.
- `SKILL-USAGE-AUDIT.md`: installed/read/applied distinctions and rejected-cut diagnosis.
- `BRANDING-REFERENCE.md` and `BRANDING-PROVENANCE.json`: deployed brand source.
- `MOTION-IMPLEMENTATION.md`: animation and transition implementation.
- `FEATURE-EVIDENCE-MATRIX.md`: footage and truth boundaries.
- `VISUAL-QA-REPORT.md`: completed final review record.

## Editable project

The new entry point is `src/rebuild-entry.tsx`; composition `SentinelCinematicRebuild` is 1920×1080 at 30fps, 5160 frames. Scene implementation is `src/Rebuild.tsx`, timing/copy `rebuild/storyboard.json`, media under `public/rebuild` and original font assets under `public/production`.

Use the original pinned studio package.json/package-lock.json and `npm ci`, then:

```sh
npx remotion studio src/rebuild-entry.tsx
node rebuild/render.mjs intro
node rebuild/render.mjs body
python rebuild/finalize.py
```

The renderer uses the official bundled Chrome downloaded with curl through the environment proxy. The editable archive uses automatic bundled-browser selection; set REMOTION_BROWSER_EXECUTABLE only when supplying an explicit local bundled browser. Install Python requirements from rebuild/requirements-rebuild.txt and provide FFmpeg/ffprobe on PATH. No local credentials, provider keys, database data or production settings belong in the editable archive. Source captures are provided, so rerendering does not require new provider calls.

Narration is AI-generated using local Kokoro `bf_emma`, not the rejected `am_michael` voice. Three audition WAVs are included separately. Model weights are not duplicated into the source archive. No paid inference was called. Voice naturalness remains a creative judgment; technical measurements are not presented as human approval.

## Resource limits and segmented rendering

In a constrained cloud machine, use the capped-cache sequential scene renderer instead of unbounded concurrent jobs. The full body renderer now also caps media caches. During production one earlier unbounded concurrent render exceeded 8 GiB. Its complete first 92 seconds were recovered from the already encoded frames and decode-checked; remaining scenes were rendered separately without removing their motion. No provider output was recreated or changed to repair that container.

The production assembly script uses the recovered 22–92 second prefix and completed scene segments. For a fresh rerender, run `node rebuild/render.mjs intro`, `node rebuild/render.mjs body`, and `python rebuild/finalize.py`; that path does not require any recovery artifact.
