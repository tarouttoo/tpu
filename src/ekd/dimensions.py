"""Размеры на листе: выносные и размерные линии со стрелками (ГОСТ 2.307).

Размер ставится между двумя точками: от них к размерной линии идут выносные линии, на
концах размерной линии — зачернённые стрелки, над линией — число. Отклонения пишут
шрифтом на ступень меньше числа (ГОСТ 2.307, ГОСТ 2.304), поэтому подпись размера
разбирается на две части: «124 +0,2» → число «124» и отклонение «+0,2».

Размер по длине (``along_x``) ведёт выносные линии вверх или вниз и пишет число над
размерной линией; размер по высоте ведёт выносные линии в сторону и пишет число слева
от размерной линии, повернув его на 90° — как на чертеже.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import ClassVar

from ekd.primitives import (
    TEXT_2_5,
    TEXT_3_5,
    THIN,
    FilledPolygon,
    Primitive,
    Segment,
    Text,
    text_extent,
)

#: Стрелка (ГОСТ 2.307): длина и ширина зачернённого треугольника.
ARROW_LENGTH = 4.0
ARROW_WIDTH = 1.2
#: Зазор между контуром и выносной линией.
EXTENSION_GAP = 1.0
#: Выход выносной линии за размерную.
EXTENSION_OVERSHOOT = 2.0
#: Зазор между размерной линией и числом.
TEXT_GAP = 0.8
#: Зазор между числом и отклонением в подписи размера.
DEVIATION_GAP = 0.4


def split_label(label: str) -> tuple[str, str]:
    """Разобрать подпись размера: «124 +0,2» → («124», «+0,2»); «45» → («45», «»)."""
    number, _, deviation = label.partition(" ")
    return number, deviation.strip()


@dataclass(frozen=True)
class LinearDimension(Primitive):
    """Линейный размер между двумя точками листа.

    ``at`` — координата размерной линии по нормали (Y для размера по длине, X — по
    высоте); ``label`` — подпись с отклонениями, например «124 +0,2».
    """

    start: tuple[float, float]
    end: tuple[float, float]
    at: float
    label: str
    along_x: bool = True
    width: float = THIN
    number_height: float = TEXT_3_5
    deviation_height: float = TEXT_2_5
    kind: ClassVar[str] = "линейный размер"

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise ValueError("у размера нет подписи")
        if self.along_x and math.isclose(self.start[0], self.end[0]):
            raise ValueError("размер по длине не может быть нулевым")
        if not self.along_x and math.isclose(self.start[1], self.end[1]):
            raise ValueError("размер по высоте не может быть нулевым")

    # -- координаты на листе ---------------------------------------------------

    def _ends(self) -> tuple[tuple[float, float], tuple[float, float]]:
        """Концы размерной линии."""
        if self.along_x:
            return (self.start[0], self.at), (self.end[0], self.at)
        return (self.at, self.start[1]), (self.at, self.end[1])

    def _extension(self, point: tuple[float, float]) -> tuple[Segment, ...]:
        """Выносная линия от точки контура до размерной линии с выходом за неё."""
        normal = point[1] if self.along_x else point[0]
        direction = 1.0 if self.at >= normal else -1.0
        if self.along_x:
            first = (point[0], point[1] + direction * EXTENSION_GAP)
            second = (point[0], self.at + direction * EXTENSION_OVERSHOOT)
        else:
            first = (point[0] + direction * EXTENSION_GAP, point[1])
            second = (self.at + direction * EXTENSION_OVERSHOOT, point[1])
        return (Segment(*first, *second, self.width),)

    def _arrow(self, tip: tuple[float, float], direction: float) -> FilledPolygon:
        """Стрелка размерной линии: остриё в ``tip``, хвост в ``direction`` (по линии)."""
        if self.along_x:
            points = ((tip[0], tip[1]),
                      (tip[0] + direction * ARROW_LENGTH, tip[1] + ARROW_WIDTH / 2.0),
                      (tip[0] + direction * ARROW_LENGTH, tip[1] - ARROW_WIDTH / 2.0))
        else:
            points = ((tip[0], tip[1]),
                      (tip[0] + ARROW_WIDTH / 2.0, tip[1] + direction * ARROW_LENGTH),
                      (tip[0] - ARROW_WIDTH / 2.0, tip[1] + direction * ARROW_LENGTH))
        return FilledPolygon(points)

    # -- примитивы -------------------------------------------------------------

    def segments(self) -> tuple[Segment, ...]:
        first, second = self._ends()
        out = [Segment(*first, *second, self.width)]
        out += list(self._extension(self.start))
        out += list(self._extension(self.end))
        return tuple(out)

    def polygons(self) -> tuple[tuple[tuple[float, float], ...], ...]:
        first, second = self._ends()
        return tuple(
            arrow.polygons()[0] for arrow in (self._arrow(first, 1.0), self._arrow(second, -1.0))
        )

    def labels(self) -> tuple[Text, ...]:
        """Число и отклонение: у размера по длине — над линией, у размера по высоте — слева."""
        number, deviation = split_label(self.label)
        number_width = text_extent(number, self.number_height)[0]
        deviation_width = text_extent(deviation, self.deviation_height)[0] if deviation else 0.0
        gap = DEVIATION_GAP if deviation else 0.0
        total = number_width + gap + deviation_width
        first, second = self._ends()
        if self.along_x:
            centre = (first[0] + second[0]) / 2.0
            x = centre - total / 2.0
            y = self.at + TEXT_GAP
            out = [Text(x, y, number, self.number_height, "start", "bottom")]
            if deviation:
                out.append(Text(x + number_width + gap, y, deviation, self.deviation_height,
                                "start", "bottom"))
            return tuple(out)
        centre = (first[1] + second[1]) / 2.0
        x = self.at - TEXT_GAP
        y = centre - total / 2.0
        out = [Text(x, y, number, self.number_height, "start", "bottom", 90.0)]
        if deviation:
            out.append(Text(x, y + number_width + gap, deviation, self.deviation_height,
                            "start", "bottom", 90.0))
        return tuple(out)


def horizontal(sheet, start, end, *, at: float, label: str, **kwargs) -> LinearDimension:
    """Размер по длине: между ``start`` и ``end``, размерная линия на уровне ``at``."""
    return sheet.add(LinearDimension((float(start[0]), float(start[1])),
                                     (float(end[0]), float(end[1])), at, label,
                                     along_x=True, **kwargs))


def vertical(sheet, start, end, *, at: float, label: str, **kwargs) -> LinearDimension:
    """Размер по высоте: между ``start`` и ``end``, размерная линия на уровне ``at``."""
    return sheet.add(LinearDimension((float(start[0]), float(start[1])),
                                     (float(end[0]), float(end[1])), at, label,
                                     along_x=False, **kwargs))
