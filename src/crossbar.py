"""Перемычка — 3865.00.12. Лист 09Г2С по ГОСТ 19281-2014, 16 мм, 135 × 90 × 16."""

from cadgen import build123d as bd
from cadgen import step

BAR_LEN = 135.0   # X
BAR_WIDTH = 90.0  # Y
BAR_THICK = 16.0  # Z


@step(out="../STEP/crossbar.step")
def crossbar():
    b = bd.Box(BAR_LEN, BAR_WIDTH, BAR_THICK)
    b.label = "peremychka"
    return b


if __name__ == "__main__":
    crossbar()
