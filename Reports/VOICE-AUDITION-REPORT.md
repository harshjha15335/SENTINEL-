# Narration audition and production record

AI-generated speech. No paid API calls. Previous narrator am_michael is not reused. Three distinct Kokoro voices were generated with the same documentary-style passage, using the already installed local model. The local Whisper model was downloaded from the official Systran Hugging Face distribution for intelligibility checks.

| Voice | Pace | Pause/silence share | Pronunciation check | Decision |
|---|---|---|---|---|
| bf_emma | 131 wpm | 28% | SENTINEL and Gemini correctly recognized; no clipped samples | Selected: composed British documentary delivery, balanced pace and pause share |
| bm_george | 119 wpm | 24% | SENTINEL and Gemini correctly recognized; no clipped samples | Alternative audition retained |
| af_heart | 120 wpm | 27% | SENTINEL and Gemini correctly recognized; no clipped samples | Alternative audition retained |

## Evaluated dimensions

- Pronunciation: all three local ASR passes recover the source text and key names; new script spells XGBoost, ROC, PDF and Supabase for pronunciation where needed. This is supporting evidence, not proof of human preference.
- Pacing: measured, distinct 119–131 wpm audition passages. The selected voice runs at 1.01 model speed in the final recording. No atempo/time compression is applied.
- Pauses: each full sentence has its model punctuation plus a 180ms editorial breath. Every scene has additional tail room; timings.json records exact duration.
- Emphasis/energy: sentence-length contrast, punctuation, waveform energy and pitch-range measurements are retained in audition-prosody.json. The script is rewritten rather than passed as a dense technical specification.
- Emotion: this local model has no explicit emotional style controller. A composed documentary tone was selected through voice identity and writing. We do not claim these numeric measurements prove natural emotion, or that a human listening panel approved it.

## Sound design

An original 112 BPM felt-key ostinato and warm sustained harmony replaces the old simple drone. Original transition gestures, low impacts, a restrained logo chord and automatic score ducking support the voice. The final target is -16 LUFS and -1.5 dBTP, with stereo 48kHz audio. Music/effects and narration stems are separately deliverable.

## Voice alternatives

All three WAV files, common audition text, timing and ASR evidence are retained under rebuild/audio. The selected narration is bf_emma; it is a distinct voice from the rejected am_michael recording.
