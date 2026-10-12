# Transcripts

Machine transcripts (Russian, lightly punctuated) of the three course
screencasts that explain this coursework: the principle layout of the fixture
(принципиальная схема приспособления) and a walkthrough of the ОК development.

| Transcript | Source video (in `ABDM/Videos`) | Duration | Segments | Words |
| --- | --- | --- | --- | --- |
| `01_Пояснение к разработке ОК.*` | `Пояснение к разработке ОК.mp4` | 32:33 | 297 | 3 624 |
| `02_принципиальная схема ч1.*` | `принципиальная схема ч1.mp4` | 32:07 | 294 | 3 589 |
| `03_Принципиальная схема ч2.*` | `Принципиальная ч.2.mp4` | 36:15 | 296 | 3 778 |

Four files per transcript:

| Suffix | Contents |
| --- | --- |
| `.plain.txt` | Continuous text, no timings — the one to read |
| `.txt` | One line per segment, prefixed with its start time |
| `.srt` | Subtitles for the source video |
| `.json` | Segments with `start`/`end` in seconds, plus model and language metadata |

## How they were produced

faster-whisper 1.2.1 (`small`, int8, CPU) on 2026-10-12. Audio extracted with
ffmpeg to 16 kHz mono, silence removed with VAD, language forced to `ru` with a
domain prompt (базирование, опоры, сборочный чертёж, допуски, посадка).

Accuracy is ASR-grade. Student surnames are unreliable — the ASR renders them
as `Киреев`, `Кузьменка`, `Метрохин`, `Навицкий`, `Опенькомы`,
`Калаганскому`, `Юдину` — check them against the group list before quoting.
Rare technical terms are wrong in places, and segment boundaries come from VAD
pauses, not from punctuation, so the text needs light editing to be readable as
prose. No hallucination loops were detected (no sentence repeats anywhere), but
none of this replaces checking a passage against the video when it matters.
Timings are accurate to roughly half a second.
