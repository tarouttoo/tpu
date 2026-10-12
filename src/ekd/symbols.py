"""Условные обозначения опор по ГОСТ 3.1107-81.

Табл. 1, поз. 1 — неподвижная опора. На виде спереди и сбоку это знак с точкой контакта
в вершине: две риски, сходящиеся под углом 60° при вершине, высота 5 мм от точки контакта
до верхней грани основания, и прямоугольное основание 10 × 5 мм, на котором риски стоят
(их нижние концы — на расстоянии 2·5·tg 30° = 5,77 мм друг от друга, внутри 10-мм
основания — так это нарисовано и в таблице 1). На виде сверху — окружность ⌀6 с точкой
в центре.

Точка контакта знака ставится на контур изделия, основание отходит наружу. ``angle``
поворачивает знак вокруг точки контакта (0° — опора под изделием, 90° — опора справа
от изделия). Обозначения выполняют сплошной тонкой линией по ГОСТ 2.303-68
(ГОСТ 3.1107-81, п. 2).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import ClassVar

from ekd.primitives import THIN, TEXT_3_5, CircleMark, Primitive, Segment, Text

#: Угол между рисками при вершине (ГОСТ 3.1107-81, табл. 1).
APEX_ANGLE = 60.0
#: Риски доходят до ±5 мм — основание знака 10 мм.
REACH = 5.0
#: От точки контакта до верхней грани основания.
NECK = 5.0
#: Основание опоры.
BASE_WIDTH = 10.0
BASE_HEIGHT = 5.0
#: Обозначение на виде сверху: окружность ⌀6 с точкой в центре.
TOP_DIAMETER = 6.0
TOP_DOT = 1.4
#: Отступ номера точки от знака.
LABEL_GAP = 3.0


def _half_angle_tangent() -> float:
    return math.tan(math.radians(APEX_ANGLE / 2.0))


def _placed(point: tuple[float, float], angle: float, x: float, y: float) -> tuple[float, float]:
    radians = math.radians(angle)
    cos, sin = math.cos(radians), math.sin(radians)
    return (x + point[0] * cos - point[1] * sin, y + point[0] * sin + point[1] * cos)


@dataclass(frozen=True)
class SupportSide(Primitive):
    """Неподвижная опора на виде спереди (сбоку): точка контакта в (x, y)."""

    x: float
    y: float
    angle: float = 0.0
    label: str = ""
    width: float = THIN
    label_height: float = TEXT_3_5
    kind: ClassVar[str] = "опора, вид спереди/сбоку"
    is_symbol: ClassVar[bool] = True

    def segments(self) -> tuple[Segment, ...]:
        """Треугольник 60° высотой 5 мм и основание 10 × 5 мм — только снаружи изделия.

        В таблице 1 ГОСТ 3.1107-81 риски продолжены и выше точки контакта, но там знак
        нарисован отдельно от изделия. На схеме верхние половины рисок оказались бы
        внутри контура изделия, поэтому рисуется нижняя половина знака: треугольник с
        углом 60° при вершине (высота 5, основание 10) и прямоугольное основание.
        """
        foot = NECK * _half_angle_tangent()
        local = (
            ((0.0, 0.0), (foot, -NECK)),
            ((0.0, 0.0), (-foot, -NECK)),
            ((-BASE_WIDTH / 2, -NECK), (BASE_WIDTH / 2, -NECK)),
            ((BASE_WIDTH / 2, -NECK), (BASE_WIDTH / 2, -NECK - BASE_HEIGHT)),
            ((BASE_WIDTH / 2, -NECK - BASE_HEIGHT), (-BASE_WIDTH / 2, -NECK - BASE_HEIGHT)),
            ((-BASE_WIDTH / 2, -NECK - BASE_HEIGHT), (-BASE_WIDTH / 2, -NECK)),
        )
        return tuple(
            Segment(*_placed(a, self.angle, self.x, self.y), *_placed(b, self.angle, self.x, self.y),
                    self.width)
            for a, b in local
        )

    def labels(self) -> tuple[Text, ...]:
        if not self.label:
            return ()
        offset = _placed((REACH + LABEL_GAP, -(NECK + BASE_HEIGHT) / 2.0), self.angle, self.x, self.y)
        return (Text(offset[0], offset[1], self.label, self.label_height, "start", "center"),)


@dataclass(frozen=True)
class SupportTop(Primitive):
    """Неподвижная опора на виде сверху: окружность ⌀6 с точкой в центре."""

    x: float
    y: float
    label: str = ""
    width: float = THIN
    label_height: float = TEXT_3_5
    kind: ClassVar[str] = "опора, вид сверху"
    is_symbol: ClassVar[bool] = True

    def circles(self) -> tuple[CircleMark, ...]:
        return (
            CircleMark(self.x, self.y, TOP_DIAMETER, self.width),
            CircleMark(self.x, self.y, TOP_DOT, self.width, filled=True),
        )

    def labels(self) -> tuple[Text, ...]:
        """Номер точки — над знаком: справа он налезал бы на контур у кромки изделия."""
        if not self.label:
            return ()
        return (Text(self.x, self.y + TOP_DIAMETER / 2.0 + LABEL_GAP, self.label,
                     self.label_height, "middle", "bottom"),)


def support_side(sheet, x: float, y: float, *, angle: float = 0.0, label: str = "",
                 width: float = THIN) -> SupportSide:
    """Поставить знак неподвижной опоры (вид спереди/сбоку) точкой контакта в (x, y)."""
    return sheet.add(SupportSide(x, y, angle, label, width))


def support_top(sheet, x: float, y: float, *, label: str = "", width: float = THIN) -> SupportTop:
    """Поставить знак неподвижной опоры (вид сверху) точкой контакта в (x, y)."""
    return sheet.add(SupportTop(x, y, label, width))
