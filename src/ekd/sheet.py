"""Лист ЕСКД: рамка, основная надпись, дополнительные графы и вывод в SVG и PDF.

Лист собирается как список примитивов в миллиметрах и рисуется один раз, из одного и
того же разложения на отрезки, окружности и надписи — в SVG и в PDF. Поэтому оба файла
показывают один и тот же лист, и ни один формат не получает своей копии.

Рамка — по ГОСТ 2.301, основная надпись — по ГОСТ 2.104 (форма 1), дополнительные
графы 19–23 — по ГОСТ 2.104. Примитивы и метрики надписей — в :mod:`ekd.primitives`.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

from ekd.primitives import (
    ANCHOR_HA,
    DASH_CENTRE,
    FONT,
    FONT_STYLE,
    TEXT_2_5,
    TEXT_3_5,
    TEXT_5,
    TEXT_7,
    TEXT_SIZES,
    THICK,
    THIN,
    VALIGN_VA,
    CenterLine,
    Circle,
    CircleMark,
    FilledPolygon,
    Line,
    Polyline,
    Primitive,
    Segment,
    Text,
    centre_line,
    dot,
    fit_height,
    font_size_mm,
    text_box,
    text_extent,
)

__all__ = [
    "SHEET_SIZES", "MARGIN_LEFT", "MARGIN", "TITLE_W", "TITLE_H", "MM_PER_PT", "Sheet",
    # примитивы и метрики — через этот модуль: лист их и держит
    "ANCHOR_HA", "VALIGN_VA", "FONT", "FONT_STYLE", "THICK", "THIN", "TEXT_2_5", "TEXT_3_5",
    "TEXT_5", "TEXT_7", "TEXT_SIZES", "Circle", "CircleMark", "CenterLine", "DASH_CENTRE",
    "FilledPolygon", "Line", "Polyline", "Primitive", "Segment", "Text", "centre_line", "dot",
    "fit_height", "font_size_mm", "text_box", "text_extent",
]

MM_PER_PT = 25.4 / 72.0

#: Форматы по ГОСТ 2.301, горизонтальные, мм: A3 — документы этапов, A4 — карты ЕСТД.
SHEET_SIZES = {
    "A4": (297.0, 210.0),
    "A3": (420.0, 297.0),
    "A2": (594.0, 420.0),
}

#: Поле подшивки 20 мм слева, остальные поля 5 мм (ГОСТ 2.301).
MARGIN_LEFT = 20.0
MARGIN = 5.0

#: Основная надпись, форма 1 (ГОСТ 2.104): 185 × 55 мм в правом нижнем углу рамки.
TITLE_W = 185.0
TITLE_H = 55.0


@dataclass
class Sheet:
    """Лист с рамкой, основной надписью, проекциями и условными знаками."""

    size: str = "A3"
    scale: float = 1.0
    primitives: list[Primitive] = field(default_factory=list)
    views: list = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.size not in SHEET_SIZES:
            raise ValueError(f"неизвестный формат {self.size!r}; известные: {sorted(SHEET_SIZES)}")
        if not self.scale > 0:
            raise ValueError("масштаб должен быть положительным")

    # -- размеры листа ---------------------------------------------------------

    @property
    def width(self) -> float:
        return SHEET_SIZES[self.size][0]

    @property
    def height(self) -> float:
        return SHEET_SIZES[self.size][1]

    @property
    def frame_rect(self) -> tuple[float, float, float, float]:
        """Рамка по ГОСТ 2.301: (x0, y0, x1, y1)."""
        return (MARGIN_LEFT, MARGIN, self.width - MARGIN, self.height - MARGIN)

    @property
    def title_block_rect(self) -> tuple[float, float, float, float]:
        """Основная надпись по ГОСТ 2.104, форма 1 — в правом нижнем углу рамки."""
        x0, y0, x1, _ = self.frame_rect
        return (x1 - TITLE_W, y0, x1, y0 + TITLE_H)

    # -- примитивы -------------------------------------------------------------

    def add(self, primitive: Primitive | Iterable[Primitive]) -> Primitive | tuple[Primitive, ...]:
        if isinstance(primitive, Primitive) or hasattr(primitive, "segments"):
            self.primitives.append(primitive)
            return primitive
        added = tuple(primitive)
        self.primitives.extend(added)
        return added

    def add_line(self, x1, y1, x2, y2, *, width: float = THIN) -> Line:
        return self.add(Line(x1, y1, x2, y2, width))

    def add_polyline(self, points, *, width: float = THIN, closed: bool = False) -> Polyline:
        return self.add(Polyline(tuple((float(x), float(y)) for x, y in points), width, closed))

    def add_circle(self, x, y, diameter, *, width: float = THIN, filled: bool = False) -> Circle:
        return self.add(Circle(x, y, diameter, width, filled))

    def add_text(self, x, y, text, *, height: float = TEXT_3_5, anchor: str = "start",
                 valign: str = "baseline", rotation: float = 0.0) -> Text:
        return self.add(Text(x, y, text, height, anchor, valign, rotation))

    def symbols(self) -> list[Primitive]:
        """Условные знаки (опоры, зажимы, установочные устройства) — без линий листа."""
        return [p for p in self.primitives if p.is_symbol]

    def texts(self) -> list[str]:
        return [label.text for label in self.labels()]

    def labels(self) -> list[Text]:
        return [label for p in self.primitives for label in p.labels()]

    def geometry(
        self,
    ) -> tuple[list[Segment], list[CircleMark], list[tuple[tuple[float, float], ...]], list[Text]]:
        """Разложение листа на отрезки, окружности, залитые многоугольники и надписи.

        Общее для SVG и PDF: оба формата получают одно и то же разложение.
        """
        segments = [s for p in self.primitives for s in p.segments()]
        circles = [c for p in self.primitives for c in p.circles()]
        polygons = [polygon for p in self.primitives for polygon in p.polygons()]
        labels = [t for p in self.primitives for t in p.labels()]
        return segments, circles, polygons, labels

    def bounds(self, *, primitives: str | None = None) -> tuple[float, float, float, float]:
        """Габарит всего нарисованного: (x0, y0, x1, y1), мм.

        ``primitives="text"`` оставляет в габарите только надписи.
        """
        segments, circles, polygons, labels = self.geometry()
        if primitives == "text":
            segments, circles, polygons = [], [], []
        xs: list[float] = []
        ys: list[float] = []
        for s in segments:
            xs += [s.x1, s.x2]
            ys += [s.y1, s.y2]
        for c in circles:
            xs += [c.x - c.diameter / 2, c.x + c.diameter / 2]
            ys += [c.y - c.diameter / 2, c.y + c.diameter / 2]
        for polygon in polygons:
            xs += [x for x, _ in polygon]
            ys += [y for _, y in polygon]
        for label in labels:
            x0, y0, x1, y1 = text_box(label)
            xs += [x0, x1]
            ys += [y0, y1]
        if not xs:
            return (math.inf, math.inf, -math.inf, -math.inf)
        return (min(xs), min(ys), max(xs), max(ys))

    # -- рамка и основная надпись ----------------------------------------------

    def add_frame(self) -> None:
        """Рамка листа по ГОСТ 2.301."""
        x0, y0, x1, y1 = self.frame_rect
        self.add_polyline([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], width=THICK, closed=True)

    def add_extra_graphs(self) -> None:
        """Дополнительные графы 19–23 (ГОСТ 2.104) вдоль левой стороны рамки.

        Их ставят в поле подшивки — так же, как на исходном сборочном чертеже курсового.
        """
        x0 = MARGIN
        x1 = MARGIN_LEFT
        divider = x0 + 8.0
        _, y0, _, y1 = self.frame_rect
        rows = (
            ("Перв. примен.", 0.22),
            ("Справ. №", 0.20),
            ("Подп. и дата", 0.116),
            ("Инв. № дубл.", 0.116),
            ("Взам. инв. №", 0.116),
            ("Подп. и дата", 0.116),
            ("Инв. № подл.", 0.116),
        )
        self.add_line(x0, y0, x0, y1, width=THICK)
        self.add_line(x1, y0, x1, y1, width=THICK)
        self.add_line(divider, y0, divider, y1, width=THIN)
        cursor = y1
        for label, share in rows:
            height = (y1 - y0) * share
            self.add_line(x0, cursor - height, x1, cursor - height, width=THIN)
            self.add_text(divider - 2.0, cursor - height / 2.0, label,
                          height=TEXT_2_5, anchor="middle", valign="center", rotation=90.0)
            cursor -= height

    def add_title_block(
        self,
        *,
        designation: str,
        name: str,
        document: str = "",
        material: str = "",
        scale: str = "1:1",
        letter: str = "У",
        mass: str = "",
        sheet_number: str = "1",
        sheet_count: str = "1",
        organisation: str = "",
        signature_rows: Sequence[str] = ("Разраб.", "Пров.", "Т.контр.", "Н.контр.", "Утв.", ""),
    ) -> None:
        """Основная надпись по ГОСТ 2.104, форма 1 (185 × 55 мм).

        Надписи граф подбираются по размеру графы (ГОСТ 2.304): длинное наименование
        печатается мельче, но не вылезает за линию графы.
        """
        bx0, by0, bx1, by1 = self.title_block_rect

        def v(x: float, y0: float = by0, y1: float = by1, width: float = THIN) -> None:
            self.add_line(bx0 + x, y0, bx0 + x, y1, width=width)

        def h(y: float, x0: float = 0.0, x1: float = TITLE_W, width: float = THIN) -> None:
            self.add_line(bx0 + x0, by0 + y, bx0 + x1, by0 + y, width=width)

        self.add_polyline([(bx0, by0), (bx1, by0), (bx1, by1), (bx0, by1)], width=THICK, closed=True)

        # Таблица изменений (графы 14–18) — 65 мм сверху слева, 5 строк по 5 мм.
        # Ширины граф выбраны так, чтобы их подписи помещались при шрифте 2,5 мм.
        for column in (9.0, 18.0, 38.0, 55.0):
            v(column, by0 + 30.0, by1)
        for row in range(1, 5):
            h(30.0 + row * 5.0, 0.0, 65.0)
        h(30.0, 0.0, 65.0, THICK)
        for label, x in (("Изм.", 4.5), ("Лист", 13.5), ("№ докум.", 28.0), ("Подп.", 46.5), ("Дата", 60.0)):
            self.add_text(bx0 + x, by0 + 32.5, label, height=TEXT_2_5, anchor="middle", valign="center")

        # Графа 2 — обозначение документа: 120 × 15 мм сверху справа.
        h(40.0, 65.0)
        v(65.0, by0 + 40.0, by1, THICK)
        self.add_text(bx0 + 125.0, by0 + 47.5, designation, height=fit_height(designation, 114.0),
                      anchor="middle", valign="center")

        # Графа 1 — наименование изделия и документа: 70 × 40 мм.
        v(65.0, by0, by0 + 40.0)
        v(135.0, by0, by1)
        self.add_text(bx0 + 100.0, by0 + 30.0, name, height=fit_height(name, 64.0),
                      anchor="middle", valign="center")
        if document:
            self.add_text(bx0 + 100.0, by0 + 21.0, document, height=fit_height(document, 64.0),
                          anchor="middle", valign="center")
        if material:
            self.add_text(bx0 + 100.0, by0 + 10.0, material, height=fit_height(material, 64.0),
                          anchor="middle", valign="center")

        # Графы 4–6: литера, масса, масштаб — 50 × 15 мм.
        h(25.0, 135.0)
        for column, label, x in ((142.0, "Лит.", 138.5), (167.0, "Масса", 154.5), (None, "Масштаб", 176.0)):
            if column is not None:
                v(column, by0 + 25.0, by0 + 40.0)
            self.add_text(bx0 + x, by0 + 39.0, label, height=TEXT_2_5, anchor="middle", valign="top")
        self.add_text(bx0 + 138.5, by0 + 30.0, letter, height=TEXT_5, anchor="middle", valign="center")
        self.add_text(bx0 + 154.5, by0 + 30.0, mass, height=TEXT_5, anchor="middle", valign="center")
        self.add_text(bx0 + 176.0, by0 + 30.0, scale, height=TEXT_5, anchor="middle", valign="center")

        # Графы 7–8: лист и листов — 50 × 15 мм.
        h(10.0, 135.0)
        v(155.0, by0 + 10.0, by0 + 25.0)
        self.add_text(bx0 + 145.0, by0 + 24.0, "Лист", height=TEXT_2_5, anchor="middle", valign="top")
        self.add_text(bx0 + 170.0, by0 + 24.0, "Листов", height=TEXT_2_5, anchor="middle", valign="top")
        self.add_text(bx0 + 145.0, by0 + 14.0, sheet_number, height=TEXT_5, anchor="middle", valign="center")
        self.add_text(bx0 + 170.0, by0 + 14.0, sheet_count, height=TEXT_5, anchor="middle", valign="center")

        # Графа 9 — организация — и строки подписей (графы 10–13).
        if organisation:
            self.add_text(bx0 + 160.0, by0 + 5.0, organisation, height=fit_height(organisation, 46.0),
                          anchor="middle", valign="center")
        v(17.0, by0, by0 + 30.0)
        v(40.0, by0, by0 + 30.0)
        v(55.0, by0, by0 + 30.0)
        for row, label in enumerate(signature_rows):
            y = 30.0 - row * 5.0
            if row:
                h(y, 0.0, 65.0)
            if label:
                self.add_text(bx0 + 1.5, by0 + y - 2.5, label, height=TEXT_2_5, valign="center")

    # -- вывод -----------------------------------------------------------------

    def _figure(self):
        import matplotlib

        matplotlib.use("Agg")
        matplotlib.rcParams["svg.fonttype"] = "path"
        matplotlib.rcParams["svg.hashsalt"] = "3865.00.10"
        matplotlib.rcParams["pdf.fonttype"] = 42
        import matplotlib.pyplot as plt

        fig = plt.figure(figsize=(self.width / 25.4, self.height / 25.4))
        ax = fig.add_axes((0.0, 0.0, 1.0, 1.0))
        ax.set_xlim(0.0, self.width)
        ax.set_ylim(0.0, self.height)
        ax.set_axis_off()

        segments, circles, polygons, labels = self.geometry()
        for s in segments:
            ax.plot([s.x1, s.x2], [s.y1, s.y2], color="black", linewidth=s.width / MM_PER_PT,
                    linestyle="-" if s.dash is None else (0, s.dash),
                    solid_capstyle="butt", zorder=2)
        for c in circles:
            radius = c.diameter / 2.0
            if c.filled:
                ax.add_patch(plt.Circle((c.x, c.y), radius, color="black", zorder=3))
            else:
                ax.add_patch(plt.Circle((c.x, c.y), radius, fill=False, edgecolor="black",
                                        linewidth=c.width / MM_PER_PT, zorder=2))
        for polygon in polygons:
            ax.add_patch(plt.Polygon(polygon, closed=True, facecolor="black",
                                     edgecolor="none", zorder=3))
        for label in labels:
            ax.text(label.x, label.y, label.text, fontsize=font_size_mm(label.height) / MM_PER_PT,
                    ha=ANCHOR_HA[label.anchor], va=VALIGN_VA[label.valign],
                    rotation=label.rotation, rotation_mode="anchor",
                    family=FONT, style=FONT_STYLE, color="black", zorder=4)
        return fig

    def save(self, *, svg: Path | str | None = None, pdf: Path | str | None = None) -> tuple[Path, ...]:
        """Один лист — два файла: SVG и PDF из одного и того же разложения примитивов."""
        if svg is None and pdf is None:
            raise ValueError("укажите хотя бы один из путей: svg= или pdf=")
        written: list[Path] = []
        fig = self._figure()
        try:
            # Date/CreationDate=None: файл не меняется от запуска к запуску.
            if svg is not None:
                path = Path(svg)
                path.parent.mkdir(parents=True, exist_ok=True)
                fig.savefig(path, format="svg", metadata={"Date": None})
                _svg_in_millimetres(path, self.width, self.height)
                written.append(path)
            if pdf is not None:
                path = Path(pdf)
                path.parent.mkdir(parents=True, exist_ok=True)
                fig.savefig(path, format="pdf", metadata={"CreationDate": None})
                written.append(path)
        finally:
            import matplotlib.pyplot as plt

            plt.close(fig)
        return tuple(written)


_SVG_TAG = re.compile(r"<svg[^>]*>")
_WIDTH = re.compile(r'width="[^"]*"')
_HEIGHT = re.compile(r'height="[^"]*"')


def save_document(
    sheets: Sequence[Sheet],
    *,
    svg: Sequence[Path | str] | None = None,
    pdf: Path | str | None = None,
) -> tuple[Path, ...]:
    """Документ из нескольких листов: SVG на каждый лист и один PDF со всеми листами.

    Оба формата получают одно и то же разложение примитивов, поэтому страница PDF с
    номером *i* — тот же лист, что и файл ``svg[i]``. SVG многостраничным не бывает,
    поэтому лист документа — это один файл SVG и одна страница PDF.
    """
    sheets = list(sheets)
    if svg is None and pdf is None:
        raise ValueError("укажите хотя бы один из путей: svg= или pdf=")
    if not sheets:
        raise ValueError("в документе нет ни одного листа")
    paths = [] if svg is None else [Path(path) for path in svg]
    if svg is not None and len(paths) != len(sheets):
        raise ValueError(f"листов {len(sheets)}, а путей SVG — {len(paths)}")

    written: list[Path] = []
    for sheet, path in zip(sheets, paths):
        written.extend(sheet.save(svg=path))
    if pdf is not None:
        from matplotlib.backends.backend_pdf import PdfPages
        import matplotlib.pyplot as plt

        path = Path(pdf)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Один PDF на документ: страницы добавляет только PdfPages — лист рисуется тем же
        # разложением примитивов, но `Figure.savefig` пишет файл на один лист.
        # CreationDate=None: файл не меняется от запуска к запуску.
        with PdfPages(path, metadata={"CreationDate": None}) as pages:
            for sheet in sheets:
                figure = sheet._figure()
                try:
                    pages.savefig(figure)
                finally:
                    plt.close(figure)
        written.append(path)
    return tuple(written)


def _svg_in_millimetres(path: Path, width: float, height: float) -> None:
    """Проставить в SVG физический размер листа в миллиметрах.

    matplotlib пишет `width`/`height` в пунктах (`width="1190.55pt"`), а `viewBox` — в
    пользовательских единицах. SVG, у которого физический размер задан в мм, печатается
    на A3 без пересчёта: печатающая программа берёт размер из самого файла.
    """
    text = path.read_text(encoding="utf-8")
    match = _SVG_TAG.search(text)
    if match is None:
        return
    tag = match.group(0)
    tag = _WIDTH.sub(f'width="{width:g}mm"', tag, count=1)
    tag = _HEIGHT.sub(f'height="{height:g}mm"', tag, count=1)
    path.write_text(text[:match.start()] + tag + text[match.end():], encoding="utf-8")
