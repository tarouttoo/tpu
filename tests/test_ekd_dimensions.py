"""Линейные размеры на листе: выносные линии, стрелки и подпись с отклонениями.

Проверяется геометрия размера (выносные линии идут от контура к размерной линии, стрелки
стоят на её концах) и подпись: число и отклонение — разными шрифтами, как требует
ГОСТ 2.307.
"""

import pytest

from ekd.dimensions import (
    ARROW_LENGTH,
    EXTENSION_GAP,
    EXTENSION_OVERSHOOT,
    LinearDimension,
    horizontal,
    split_label,
    vertical,
)
from ekd.sheet import Sheet


def test_label_is_split_into_number_and_deviation():
    assert split_label("124 +0,2") == ("124", "+0,2")
    assert split_label("90 −0,2") == ("90", "−0,2")
    assert split_label("45") == ("45", "")


def test_horizontal_dimension_has_two_extension_lines_and_a_dimension_line():
    sheet = Sheet("A3")
    dimension = horizontal(sheet, (40.0, 100.0), (160.0, 100.0), at=80.0, label="124 +0,2")
    segments = dimension.segments()
    assert len(segments) == 3, "размерная линия и две выносные"
    assert {(round(s.x1, 1), round(s.y1, 1), round(s.x2, 1), round(s.y2, 1))
            for s in segments[1:]} == {(40.0, 99.0, 40.0, 78.0), (160.0, 99.0, 160.0, 78.0)}, (
        "выносные линии начинаются с зазором от контура и выходят за размерную линию"
    )
    assert (segments[0].x1, segments[0].y1, segments[0].x2, segments[0].y2) == (40.0, 80.0,
                                                                              160.0, 80.0)
    assert EXTENSION_GAP == 1.0 and EXTENSION_OVERSHOOT == 2.0


def test_arrows_are_filled_triangles_at_the_ends():
    sheet = Sheet("A3")
    dimension = horizontal(sheet, (40.0, 100.0), (160.0, 100.0), at=80.0, label="124 +0,2")
    arrows = dimension.polygons()
    assert len(arrows) == 2
    for arrow, tip in zip(arrows, (40.0, 160.0)):
        assert len(arrow) == 3, "стрелка — треугольник"
        assert arrow[0] == (tip, 80.0), "остриё стрелки — на выносной линии"
        assert abs(arrow[1][0] - tip) == pytest.approx(ARROW_LENGTH)


def test_vertical_dimension_puts_its_text_to_the_left_rotated():
    sheet = Sheet("A3")
    dimension = vertical(sheet, (200.0, 60.0), (200.0, 105.0), at=220.0, label="45 ±0,2")
    number, deviation = dimension.labels()
    assert number.rotation == 90.0 and deviation.rotation == 90.0
    assert number.x < 220.0, "число — слева от размерной линии"
    assert (number.text, deviation.text) == ("45", "±0,2")
    assert number.height > deviation.height, "отклонение — шрифтом на ступень меньше"


def test_horizontal_dimension_puts_its_text_above_the_line():
    sheet = Sheet("A3")
    dimension = horizontal(sheet, (40.0, 100.0), (160.0, 100.0), at=80.0, label="135 ±0,2")
    number, deviation = dimension.labels()
    assert number.y > 80.0 and number.valign == "bottom"
    assert number.anchor == "start" and deviation.x > number.x


def test_dimension_without_a_label_is_refused():
    with pytest.raises(ValueError, match="подписи"):
        LinearDimension((10.0, 10.0), (50.0, 10.0), 5.0, "  ")


def test_zero_length_dimension_is_refused():
    with pytest.raises(ValueError, match="нулевым"):
        LinearDimension((10.0, 10.0), (10.0, 40.0), 5.0, "30")
    with pytest.raises(ValueError, match="нулевым"):
        vertical(Sheet("A3"), (10.0, 10.0), (40.0, 10.0), at=5.0, label="30")


def test_dimensions_reach_the_sheet_as_segments_and_polygons():
    sheet = Sheet("A3")
    horizontal(sheet, (40.0, 100.0), (160.0, 100.0), at=80.0, label="124 +0,2")
    segments, circles, polygons, labels = sheet.geometry()
    assert len(segments) == 3 and len(polygons) == 2 and len(labels) == 2
    assert circles == []
