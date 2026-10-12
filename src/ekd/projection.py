"""Проекции изделия на лист: удаление невидимых линий и отображение модели в мм листа.

Вид строится kernel'ом (OCCT, HLR через build123d), поэтому контуры на листе —
это контуры самой модели: изменится STEP, изменится и схема. Отображение модели в
миллиметры листа — то же, что применил kernel при проецировании (ортогонально,
масштаб 1, начало в центре габарита изделия), поэтому точка модели, поданная в
:meth:`View.to_sheet`, попадает ровно на то место листа, где её нарисовал бы kernel.
"""

from __future__ import annotations

import math
from typing import Any

from ekd import sheet as ekd

#: Куда стоит наблюдатель (направление от центра изделия) и куда направлен верх вида.
VIEW_DIRECTIONS: dict[str, tuple[tuple[float, float, float], tuple[float, float, float]]] = {
    "front": ((0.0, -1.0, 0.0), (0.0, 0.0, 1.0)),
    "back": ((0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
    "left": ((-1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
    "right": ((1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
    "top": ((0.0, 0.0, 1.0), (0.0, 1.0, 0.0)),
    "bottom": ((0.0, 0.0, -1.0), (0.0, -1.0, 0.0)),
}

#: Наблюдатель стоит далеко: проекция ортогональная, расстояние на результат не влияет.
_DISTANCE = 1000.0


def _cross(a, b) -> tuple[float, float, float]:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _dot(a, b) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _unit(v) -> tuple[float, float, float]:
    length = math.sqrt(_dot(v, v))
    return (v[0] / length, v[1] / length, v[2] / length)


def view_axes(name: str) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    """Оси вида на листе: (вправо, вверх) в координатах модели."""
    if name not in VIEW_DIRECTIONS:
        raise ValueError(f"неизвестный вид {name!r}; известные: {sorted(VIEW_DIRECTIONS)}")
    direction, up = VIEW_DIRECTIONS[name]
    right = _cross(up, direction)
    if _dot(right, right) < 1e-12:
        raise ValueError(f"у вида {name!r} не определена горизонтальная ось")
    return _unit(right), _unit(up)


def _samples(edge: Any) -> list[tuple[float, float]]:
    """Точки проекции ребра: у прямой — концы, у кривой — по длине."""
    kind = getattr(edge, "geom_type", None)
    count = 2 if getattr(kind, "name", str(kind)) == "LINE" else 33
    return [
        (edge.position_at(i / (count - 1)).X, edge.position_at(i / (count - 1)).Y)
        for i in range(count)
    ]


class View:
    """Ортогональный вид изделия на листе.

    ``at`` — где на листе окажется центр габарита изделия (мм листа); ``scale`` —
    масштаб вида (по умолчанию масштаб листа). Точки модели переводятся в мм листа
    методом :meth:`to_sheet`.
    """

    def __init__(self, sheet: ekd.Sheet, shape: Any, name: str, at: tuple[float, float], *,
                 scale: float | None = None, width: float = ekd.THICK):
        self.sheet = sheet
        self.name = name
        self.shape = shape
        self.at = (float(at[0]), float(at[1]))
        self.scale = float(sheet.scale if scale is None else scale)
        self.width = width
        centre = shape.bounding_box().center()
        self.centre = (centre.X, centre.Y, centre.Z)
        self.axes = view_axes(name)
        sheet.views.append(self)
        self.draw()

    # -- отображение модели в лист ---------------------------------------------

    def to_sheet(self, point) -> tuple[float, float]:
        """Точка модели (x, y, z) — в координаты листа."""
        relative = (point[0] - self.centre[0], point[1] - self.centre[1], point[2] - self.centre[2])
        right, up = self.axes
        return (self.at[0] + _dot(right, relative) * self.scale,
                self.at[1] + _dot(up, relative) * self.scale)

    # -- контуры изделия -------------------------------------------------------

    def edges(self) -> list[list[tuple[float, float]]]:
        """Контуры изделия на листе: списки точек в мм листа."""
        from build123d import Vector

        direction, up = VIEW_DIRECTIONS[self.name]
        origin = Vector(*self.centre) + Vector(*direction).normalized() * _DISTANCE
        visible, _hidden = self.shape.project_to_viewport(
            viewport_origin=origin, viewport_up=up, look_at=Vector(*self.centre)
        )
        outlines: list[list[tuple[float, float]]] = []
        for edge in visible:
            points = _samples(edge)
            if len(points) < 2:
                continue
            start, end = points[0], points[-1]
            if abs(start[0] - end[0]) < 1e-9 and abs(start[1] - end[1]) < 1e-9:
                continue
            outlines.append([(self.at[0] + x * self.scale, self.at[1] + y * self.scale) for x, y in points])
        return outlines

    def draw(self) -> None:
        for outline in self.edges():
            self.sheet.add_polyline(outline, width=self.width)
