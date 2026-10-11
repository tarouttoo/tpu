"""Направляющая — 3865.00.10 (assembly: 2 × Стойка + 1 × Перемычка).

Two posts stand on edge; the crossbar sits on top, centred, so each post
protrudes 10.5 mm past the crossbar's ends. Envelope 156 × 90 × 106.
"""

from cadgen import build123d as bd
from cadgen import step

from post import post, POST_THICK, POST_WIDTH, POST_HEIGHT
from crossbar import crossbar, BAR_LEN, BAR_WIDTH, BAR_THICK

PROTRUDE = 10.5
OVERALL_LEN = BAR_LEN + 2 * PROTRUDE          # 156
OVERALL_WIDTH = BAR_WIDTH                       # 90
OVERALL_HEIGHT = POST_HEIGHT + BAR_THICK        # 106


@step(out="../STEP/guide.step")
def guide():
    x_post = OVERALL_LEN / 2 - POST_THICK / 2

    left = bd.Pos(-x_post, 0, POST_HEIGHT / 2) * post()
    left.label = "stoyka_left"
    right = bd.Pos(x_post, 0, POST_HEIGHT / 2) * post()
    right.label = "stoyka_right"

    bar = bd.Pos(0, 0, POST_HEIGHT + BAR_THICK / 2) * crossbar()
    bar.label = "peremychka"

    return bd.Compound(children=[left, right, bar], label="napravlyayushchaya")


if __name__ == "__main__":
    guide()
