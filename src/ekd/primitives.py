"""Примитивы листа и метрики надписей: из них собирается любой лист ЕСКД.

Примитив раскладывается на три вещи, которые умеет нарисовать любой вывод: отрезки,
окружности и надписи. SVG и PDF получают одно и то же разложение, поэтому лист в них
совпадает по геометрии, линиям и тексту.

Единицы — миллиметры листа, начало координат в левом нижнем углу, Y вверх (как на
чертеже). Толщины линий по ГОСТ 2.303, высота надписей — по ГОСТ 2.304 (высота
прописных букв, не кегль).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import ClassVar, Sequence

#: Толщины линий по ГОСТ 2.303: сплошная толстая основная и сплошная тонкая.
THICK = 0.7
THIN = 0.25

#: Шрифт: наклонный, как ГОСТ 2.304, тип А; кириллицу покрывает DejaVu Sans.
FONT = "DejaVu Sans"
FONT_STYLE = "italic"

#: Высоты надписей по ГОСТ 2.304, применяемые на этих листах.
TEXT_2_5 = 2.5
TEXT_3_5 = 3.5
TEXT_5 = 5.0
TEXT_7 = 7.0
#: Шрифты ГОСТ 2.304 в порядке убывания — из них выбирается подходящий по месту.
TEXT_SIZES = (TEXT_7, TEXT_5, TEXT_3_5, TEXT_2_5)

#: Выключка надписи по горизонтали: как её понимает модуль и что ставит matplotlib.
ANCHOR_HA = {"start": "left", "middle": "center", "end": "right"}
#: Доля ширины надписи, на которую она сдвигается влево от точки привязки.
_ANCHOR_SHIFT = {"start": 0.0, "middle": 0.5, "end": 1.0}
#: Выключка по вертикали: от базовой линии, от нижней/средней/верхней линии габарита.
VALIGN_VA = {"baseline": "baseline", "bottom": "bottom", "center": "center", "top": "top"}


#: Штрихпунктирная тонкая линия (ГОСТ 2.303, осевые и центровые линии): штрих 5 мм,
#: промежуток 2 мм, точка. Шаблон задаётся в толщинах линии — так его понимает вывод.
DASH_CENTRE = (20.0, 8.0, 0.4, 8.0)


@dataclass(frozen=True)
class Segment:
    """Отрезок листа. ``dash`` — шаблон штрихов в толщинах линии (пусто — сплошная)."""

    x1: float
    y1: float
    x2: float
    y2: float
    width: float = THIN
    dash: tuple[float, ...] | None = None


@dataclass(frozen=True)
class CircleMark:
    """Окружность листа; ``filled`` — залитый круг (точка в центре знака ⌀6)."""

    x: float
    y: float
    diameter: float
    width: float = THIN
    filled: bool = False


class Primitive:
    """Примитив листа: раскладывается на отрезки, окружности и надписи."""

    kind: ClassVar[str] = "примитив"
    #: Условный знак (опора, зажим…), а не линия листа: их считает :meth:`Sheet.symbols`.
    is_symbol: ClassVar[bool] = False

    def segments(self) -> tuple[Segment, ...]:
        return ()

    def circles(self) -> tuple[CircleMark, ...]:
        return ()

    def polygons(self) -> tuple[tuple[tuple[float, float], ...], ...]:
        """Залитые многоугольники: стрелки размеров, зачернённые части знаков."""
        return ()

    def labels(self) -> tuple["Text", ...]:
        return ()


@dataclass(frozen=True)
class Line(Primitive):
    x1: float
    y1: float
    x2: float
    y2: float
    width: float = THIN
    kind: ClassVar[str] = "линия"

    def segments(self) -> tuple[Segment, ...]:
        return (Segment(self.x1, self.y1, self.x2, self.y2, self.width),)


@dataclass(frozen=True)
class Polyline(Primitive):
    points: tuple[tuple[float, float], ...]
    width: float = THIN
    closed: bool = False
    kind: ClassVar[str] = "полилиния"

    def segments(self) -> tuple[Segment, ...]:
        pts = list(self.points) + ([self.points[0]] if self.closed else [])
        return tuple(
            Segment(a[0], a[1], b[0], b[1], self.width) for a, b in zip(pts, pts[1:])
        )


@dataclass(frozen=True)
class Circle(Primitive):
    x: float
    y: float
    diameter: float
    width: float = THIN
    filled: bool = False
    kind: ClassVar[str] = "окружность"

    def circles(self) -> tuple[CircleMark, ...]:
        return (CircleMark(self.x, self.y, self.diameter, self.width, self.filled),)


def dot(x: float, y: float, diameter: float = 1.4) -> Circle:
    """Залитая точка: центр знака ⌀6, конец линии-выноски."""
    return Circle(x, y, diameter, THIN, filled=True)


@dataclass(frozen=True)
class FilledPolygon(Primitive):
    """Залитый многоугольник: стрелка линейного размера и другие зачернённые части."""

    points: tuple[tuple[float, float], ...]
    kind: ClassVar[str] = "залитый многоугольник"

    def polygons(self) -> tuple[tuple[tuple[float, float], ...], ...]:
        return (self.points,)


@dataclass(frozen=True)
class CenterLine(Primitive):
    """Осевая (центровая) линия — штрихпунктирная тонкая по ГОСТ 2.303.

    Осями симметрии на схеме проставляют координаты от центра изделия: без видимой
    осевой линии размер от неё читается как размер от воздуха.
    """

    x1: float
    y1: float
    x2: float
    y2: float
    width: float = THIN
    kind: ClassVar[str] = "осевая линия"

    def segments(self) -> tuple[Segment, ...]:
        return (Segment(self.x1, self.y1, self.x2, self.y2, self.width, DASH_CENTRE),)


def centre_line(sheet, x1: float, y1: float, x2: float, y2: float) -> CenterLine:
    """Провести осевую линию (штрихпунктирную)."""
    return sheet.add(CenterLine(x1, y1, x2, y2))


@dataclass(frozen=True)
class Text(Primitive):
    """Надпись. ``height`` — высота прописных букв по ГОСТ 2.304, мм."""

    x: float
    y: float
    text: str
    height: float = TEXT_3_5
    anchor: str = "start"
    valign: str = "baseline"
    rotation: float = 0.0
    kind: ClassVar[str] = "надпись"

    def __post_init__(self) -> None:
        # Имена выключки — ключи карт: их читает и метрика, и вывод. Опечатка в них
        # иначе всплыла бы ошибкой ключа при отрисовке, а не при сборке листа.
        if self.anchor not in ANCHOR_HA:
            raise ValueError(f"anchor — один из {sorted(ANCHOR_HA)}, а не {self.anchor!r}")
        if self.valign not in VALIGN_VA:
            raise ValueError(f"valign — один из {sorted(VALIGN_VA)}, а не {self.valign!r}")
        if not self.height > 0:
            raise ValueError(f"высота надписи должна быть положительной, а не {self.height!r}")

    def labels(self) -> tuple["Text", ...]:
        return (self,)


# --- метрики надписей ---------------------------------------------------------


def _font_properties():
    from matplotlib.font_manager import FontProperties

    return FontProperties(family=FONT, style=FONT_STYLE)


def cap_ratio() -> float:
    """Отношение кегля к высоте прописной буквы: у DejaVu Sans ≈ 0.73."""
    from matplotlib.textpath import TextPath

    path = TextPath((0, 0), "Н", size=100.0, prop=_font_properties())
    return path.get_extents().height / 100.0


_CAP_RATIO: float | None = None


def font_size_mm(height: float) -> float:
    """Кегль (мм), при котором прописные буквы выходят высотой ``height`` мм."""
    global _CAP_RATIO
    if _CAP_RATIO is None:
        _CAP_RATIO = cap_ratio()
    return height / _CAP_RATIO


def text_extent(text: str, height: float) -> tuple[float, float, float]:
    """(ширина, от baseline вниз, от baseline вверх) надписи в мм.

    Пустая надпись — нулевой габарит: у неё нет контура, а `get_extents()` на пустом
    пути падает.
    """
    if not text:
        return (0.0, 0.0, 0.0)
    from matplotlib.textpath import TextPath

    path = TextPath((0, 0), text, size=font_size_mm(height), prop=_font_properties())
    box = path.get_extents()
    return box.width, box.y0, box.y1


def _anchor_shift(anchor: str, width: float) -> float:
    return -_ANCHOR_SHIFT[anchor] * width


def _valign_shift(valign: str, down: float, up: float) -> float:
    if valign == "baseline":
        return 0.0
    if valign == "bottom":
        return -down
    if valign == "center":
        return -(down + up) / 2.0
    return -up  # "top"


def fit_height(text: str, limit: float, sizes: Sequence[float] = TEXT_SIZES) -> float:
    """Высота шрифта по ГОСТ 2.304, при которой надпись влезает в ``limit`` мм.

    Берётся наибольший размер, которым подпись ещё помещается в свою графу: так на
    чертеже и делают, а не вылезают за линию графы. Если не помещается даже самым
    мелким — это ошибка автора, и она должна быть видна сразу, а не на печати.
    """
    for height in sizes:
        if text_extent(text, height)[0] <= limit:
            return height
    raise ValueError(
        f"надпись {text!r} не помещается в {limit:g} мм даже шрифтом {sizes[-1]:g} мм"
    )


def text_box(label: Text) -> tuple[float, float, float, float]:
    """Прямоугольник надписи на листе: (x0, y0, x1, y1)."""
    width, down, up = text_extent(label.text, label.height)
    x = label.x + _anchor_shift(label.anchor, width)
    y = label.y + _valign_shift(label.valign, down, up)
    if abs(label.rotation) > 1e-9:
        angle = math.radians(label.rotation)
        corners = ((x, y + down), (x + width, y + down), (x + width, y + up), (x, y + up))
        rotated = [
            (label.x + (cx - label.x) * math.cos(angle) - (cy - label.y) * math.sin(angle),
             label.y + (cx - label.x) * math.sin(angle) + (cy - label.y) * math.cos(angle))
            for cx, cy in corners
        ]
        return (min(p[0] for p in rotated), min(p[1] for p in rotated),
                max(p[0] for p in rotated), max(p[1] for p in rotated))
    return (x, y + down, x + width, y + up)
