"""Направляющая 3865.00.10 — engineering drawing (A3, 1:2.5, first angle)."""

from pathlib import Path

import cadgen
from cadgen.eng_drawing import Sheet, eng_drawing

from post import POST_THICK, POST_WIDTH, POST_HEIGHT
from crossbar import BAR_LEN, BAR_WIDTH, BAR_THICK
from guide import PROTRUDE, OVERALL_LEN, OVERALL_WIDTH, OVERALL_HEIGHT

_HERE = Path(__file__).resolve().parent

# X where a post and the crossbar overlap vertically (post below, crossbar
# above), so an overall-height witness lands on stacked geometry.
_X_OV = (OVERALL_LEN / 2 - POST_THICK + BAR_LEN / 2) / 2


@eng_drawing(out="../PDF/guide_drawing.pdf")
def guide_drawing():
    part = cadgen.read_step(_HERE / "../STEP/guide.step")

    sheet = Sheet(
        "A3",
        title="НАПРАВЛЯЮЩАЯ",
        part_number="3865.00.10",
        material="Hardox 450",
        revision="",
        author="",
        projection="FIRST ANGLE",
        scale=0.4,  # 1:2.5
        general_tolerance="ISO 2768-m",
    )

    top, front, right, iso = sheet.three_views(part, iso=True)

    # Top view (X–Y): overall length, crossbar length.
    top.dim((-OVERALL_LEN / 2, OVERALL_WIDTH / 2, POST_HEIGHT),
            (OVERALL_LEN / 2, OVERALL_WIDTH / 2, POST_HEIGHT))               # 156
    top.dim((-BAR_LEN / 2, -BAR_WIDTH / 2, OVERALL_HEIGHT),
            (BAR_LEN / 2, -BAR_WIDTH / 2, OVERALL_HEIGHT), tol=0.5)         # 135 ±0.5

    # Front view (X–Z): plate thickness, protrusion.
    front.dim((0, BAR_WIDTH / 2, POST_HEIGHT),
              (0, BAR_WIDTH / 2, OVERALL_HEIGHT))                           # 16
    front.dim((-OVERALL_LEN / 2, OVERALL_WIDTH / 2, POST_HEIGHT),
              (-BAR_LEN / 2, OVERALL_WIDTH / 2, POST_HEIGHT))               # 10.5

    # Right view (Y–Z): overall width, overall height.
    right.dim((OVERALL_LEN / 2, -OVERALL_WIDTH / 2, POST_HEIGHT / 2),
              (OVERALL_LEN / 2, OVERALL_WIDTH / 2, POST_HEIGHT / 2), tol=0.5)  # 90 ±0.5
    right.dim((_X_OV, -OVERALL_WIDTH / 2, 0),
              (_X_OV, -OVERALL_WIDTH / 2, OVERALL_HEIGHT))                  # 106

    return sheet


if __name__ == "__main__":
    guide_drawing()
