"""Стойка — 3865.00.11. Hardox 450 plate, 16 mm thick, 90 × 90 × 16."""

from cadgen import build123d as bd
from cadgen import step

POST_THICK = 16.0   # X
POST_WIDTH = 90.0   # Y
POST_HEIGHT = 90.0  # Z


@step(out="../STEP/post.step")
def post():
    p = bd.Box(POST_THICK, POST_WIDTH, POST_HEIGHT)
    p.label = "stoyka"
    return p


if __name__ == "__main__":
    post()
