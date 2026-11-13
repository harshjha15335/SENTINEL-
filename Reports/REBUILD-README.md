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

The renderer uses the official bundled Chrome downloaded with curl through the environment proxy. Set its executable location in rebuild/render.mjs when rendering elsewhere. No local credentials, provider keys, database data or production settings belong in the editable archive. Source captures are provided, so rerendering does not require new provider calls.

Narration is AI-generated using local Kokoro `bf_emma`, not the rejected `am_michael` voice. Three audition WAVs are included separately. Model weights are not duplicated into the source archive. No paid inference was called. Voice naturalness remains a creative judgment; technical measurements are not presented as human approval.
