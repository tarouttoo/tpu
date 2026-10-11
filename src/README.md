# Models

| Script | Output | Purpose |
| --- | --- | --- |
| post.py | STEP/post.step | Стойка 3865.00.11, 16×90×90 (Hardox 450 plate) |
| crossbar.py | STEP/crossbar.step | Перемычка 3865.00.12, 135×90×16 |
| guide.py | STEP/guide.step | Направляющая 3865.00.10 — assembly of 2 posts + 1 crossbar, 156×90×106 |
| guide_drawing.py | PDF/guide_drawing.pdf | Dimensioned drawing (A3, 1:2.5, first angle) |

Build: `python src/guide.py` (builds the assembly and its parts).
Drawing: `python src/guide_drawing.py` after the assembly is built.
