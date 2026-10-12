"""Условные обозначения опор, упоров и зажимов по ГОСТ 3.1107-81.

**Опоры и упоры** (табл. 1, поз. 1 — неподвижная опора). На виде спереди и сбоку это знак
с точкой контакта в вершине: две риски, сходящиеся под углом 60° при вершине, высота 5 мм
от точки контакта до верхней грани основания, и прямоугольное основание 10 × 5 мм, на
котором риски стоят (их нижние концы — на расстоянии 2·5·tg 30° = 5,77 мм друг от друга,
внутри 10-мм основания — так это нарисовано и в таблице 1). На виде сверху — окружность
⌀6 с точкой в центре.

**Зажимы** (табл. 2): тот же треугольник с углом 60° при вершине, но вершина — точка
приложения силы зажима, а от основания отходит стержень 5 мм и плечо; у двойного зажима
плечо соединяет две точки приложения на расстоянии ``l``, которое задаёт разработчик.

**Формы рабочих поверхностей** (табл. 4, поз. 1 и 2) наносят слева от обозначения
(п. 11): плоская — перпендикуляр к поверхности, сферическая — дуга R1,5.

Точка контакта (приложения силы) ставится на контур изделия, знак отходит наружу. ``angle``
поворачивает знак вокруг этой точки (0° — опора под изделием, 90° — опора справа от
изделия). Обозначения выполняют сплошной тонкой линией по ГОСТ 2.303-68
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


class LocatedSymbol(Primitive):
    """Знак, привязанный к точке изделия: точка привязки, поворот и место знака формы.

    Общий предок опоры, упора и зажима — тем, что нужно знаку формы рабочей поверхности:
    знать, вокруг какой точки его поворачивать и на сколько отойти влево.
    """

    x: float
    y: float
    #: Поворот знака вокруг точки привязки; у знака сверху поворот не имеет смысла.
    angle: float = 0.0

    @property
    def mark_standoff(self) -> float:
        """На сколько знак формы рабочей поверхности отстоит влево от точки привязки."""
        return BASE_WIDTH / 2.0


@dataclass(frozen=True)
class SupportSide(LocatedSymbol):
    """Неподвижная опора (упор) на виде спереди или сбоку: точка контакта в (x, y)."""

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
class SupportTop(LocatedSymbol):
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

    @property
    def mark_standoff(self) -> float:
        """От точки привязки до левой кромки окружности ⌀6."""
        return TOP_DIAMETER / 2.0


def support_side(sheet, x: float, y: float, *, angle: float = 0.0, label: str = "",
                 width: float = THIN) -> SupportSide:
    """Поставить знак неподвижной опоры (вид спереди/сбоку) точкой контакта в (x, y)."""
    return sheet.add(SupportSide(x, y, angle, label, width))


def support_top(sheet, x: float, y: float, *, label: str = "", width: float = THIN) -> SupportTop:
    """Поставить знак неподвижной опоры (вид сверху) точкой контакта в (x, y)."""
    return sheet.add(SupportTop(x, y, label, width))


# --- Формы рабочих поверхностей (табл. 4) ------------------------------------
#
# Обозначение формы рабочей поверхности наносят слева от обозначения опоры, зажима или
# установочного устройства (ГОСТ 3.1107-81, п. 11): без него знак зажима и знак упора
# на листе неразличимы — оба треугольники с углом 60° при вершине.

#: Плоская рабочая поверхность (табл. 4, поз. 1): перпендикуляр к поверхности, 3 мм.
SURFACE_FLAT = "плоская"
#: Сферическая рабочая поверхность (табл. 4, поз. 2): дуга R1,5 на поверхности.
SURFACE_SPHERICAL = "сферическая"
#: Высота знака плоской рабочей поверхности (табл. 4, поз. 1).
SURFACE_STROKE = 3.0
#: Длина линии рабочей поверхности у знака плоской поверхности.
SURFACE_TICK = 3.0
#: Радиус сферической рабочей поверхности (табл. 4, поз. 2).
SURFACE_RADIUS = 1.5
#: Отступ знака формы от самого обозначения.
SURFACE_GAP = 1.0
#: Точки дуги сферической поверхности: полуокружность R1,5, разложенная на отрезки.
_ARC_POINTS = 8


@dataclass(frozen=True)
class SurfaceMark(Primitive):
    """Знак формы рабочей поверхности (ГОСТ 3.1107-81, табл. 4).

    Стоит на рабочей поверхности, в местной системе — вдоль оси +Y; ``angle``
    поворачивает знак вместе с обозначением, у которого он стоит.
    """

    x: float
    y: float
    form: str = SURFACE_FLAT
    angle: float = 0.0
    width: float = THIN
    kind: ClassVar[str] = "форма рабочей поверхности"
    is_symbol: ClassVar[bool] = True

    def __post_init__(self) -> None:
        if self.form not in (SURFACE_FLAT, SURFACE_SPHERICAL):
            raise ValueError(
                f"неизвестная форма рабочей поверхности {self.form!r}; "
                f"известные: {SURFACE_FLAT!r}, {SURFACE_SPHERICAL!r}"
            )

    def segments(self) -> tuple[Segment, ...]:
        if self.form == SURFACE_FLAT:
            local = (
                ((-SURFACE_TICK / 2.0, 0.0), (SURFACE_TICK / 2.0, 0.0)),
                ((0.0, 0.0), (0.0, SURFACE_STROKE)),
            )
        else:
            local = tuple(
                (self._arc(i), self._arc(i + 1)) for i in range(_ARC_POINTS)
            )
        return tuple(
            Segment(*_placed(a, self.angle, self.x, self.y), *_placed(b, self.angle, self.x, self.y),
                    self.width)
            for a, b in local
        )

    @staticmethod
    def _arc(index: int) -> tuple[float, float]:
        """Точка дуги R1,5: от (−R, 0) через верх до (+R, 0)."""
        angle = math.pi * (1.0 - index / _ARC_POINTS)
        return (SURFACE_RADIUS * math.cos(angle), SURFACE_RADIUS * math.sin(angle))


def surface_mark_left(sheet, symbol: LocatedSymbol, *, form: str,
                      gap: float = SURFACE_GAP) -> SurfaceMark:
    """Поставить знак формы рабочей поверхности слева от обозначения (п. 11).

    Знак отходит от рабочей поверхности в сторону изделия — так его ставят в примерах
    приложения 2 стандарта: у опоры под изделием знак уходит вверх, у зажима над
    изделием — вниз.
    """
    x = symbol.x - (symbol.mark_standoff + gap + SURFACE_TICK / 2.0)
    return sheet.add(SurfaceMark(x, symbol.y, form, symbol.angle + 180.0))


# --- Зажимы (табл. 2) ---------------------------------------------------------

#: Стержень зажима: от основания треугольника до плеча (табл. 2).
CLAMP_STEM = 5.0
#: Длина плеча одиночного зажима (табл. 2, поз. 1).
CLAMP_ARM = 10.0


@dataclass(frozen=True)
class ClampSide(LocatedSymbol):
    """Зажим на виде спереди или сбоку (ГОСТ 3.1107-81, табл. 2).

    Знак: треугольник с углом 60° при вершине (вершина — точка приложения силы),
    стержень и плечо. ``spacing`` делает зажим двойным: две точки приложения на
    расстоянии плеча ``l``, соединённые общим плечом. ``angle`` поворачивает знак
    вокруг середины точек приложения (0° — зажим над изделием, тело вверх).
    """

    x: float
    y: float
    angle: float = 0.0
    spacing: float | None = None
    arm: float = 1.0
    label: str = ""
    width: float = THIN
    label_height: float = TEXT_3_5
    kind: ClassVar[str] = "зажим, вид спереди/сбоку"
    is_symbol: ClassVar[bool] = True

    def __post_init__(self) -> None:
        if self.spacing is not None and self.spacing <= 0:
            raise ValueError("плечо двойного зажима должно быть положительным")

    @property
    def points(self) -> tuple[float, ...]:
        """Точки приложения силы зажима в местной системе (X)."""
        if self.spacing is None:
            return (0.0,)
        return (-self.spacing / 2.0, self.spacing / 2.0)

    def segments(self) -> tuple[Segment, ...]:
        foot = NECK * _half_angle_tangent()
        arm_y = NECK + CLAMP_STEM
        local: list[tuple[tuple[float, float], tuple[float, float]]] = []
        for point in self.points:
            local += [
                ((point, 0.0), (point + foot, NECK)),
                ((point, 0.0), (point - foot, NECK)),
                ((point - BASE_WIDTH / 2.0, NECK), (point + BASE_WIDTH / 2.0, NECK)),
                ((point, NECK), (point, arm_y)),
            ]
        if self.spacing is None:
            local.append(((0.0, arm_y), (self.arm * CLAMP_ARM, arm_y)))
        else:
            local.append(((self.points[0], arm_y), (self.points[-1], arm_y)))
        return tuple(
            Segment(*_placed(a, self.angle, self.x, self.y), *_placed(b, self.angle, self.x, self.y),
                    self.width)
            for a, b in local
        )

    def labels(self) -> tuple[Text, ...]:
        """Обозначение зажима — за концом плеча, от изделия."""
        if not self.label:
            return ()
        tip = (self.points[-1] if self.arm > 0 else self.points[0], NECK + CLAMP_STEM)
        direction = _placed((self.arm, 0.0), self.angle, 0.0, 0.0)
        x, y = _placed(tip, self.angle, self.x, self.y)
        if abs(direction[0]) < abs(direction[1]):
            # Плечо стоит вдоль листа: подпись — сбоку от него, а не на нём.
            return (Text(x + LABEL_GAP, y, self.label, self.label_height, "start", "center"),)
        x += direction[0] * LABEL_GAP
        anchor = "start" if direction[0] > 0 else "end"
        return (Text(x, y, self.label, self.label_height, anchor, "bottom"),)


def clamp_side(sheet, x: float, y: float, *, angle: float = 0.0, spacing: float | None = None,
               arm: float = 1.0, label: str = "", width: float = THIN) -> ClampSide:
    """Поставить знак зажима точкой приложения силы в (x, y)."""
    return sheet.add(ClampSide(x, y, angle, spacing, arm, label, width))

