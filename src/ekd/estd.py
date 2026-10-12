"""Формы ЕСТД: бланк операционной карты и его заполнение.

Операционную карту (ОК) заполняют построчно, и каждому типу строки соответствует
служебный символ: он условно выражает состав информации в графах этой строки
(ГОСТ 3.1118-82, табл. 2; ГОСТ 3.1407-86, п. 2.8). Для ОК с горизонтальным расположением
поля подшивки это символы А, Б, К/М, О, Т, Р, причём строку режимов предваряет
строка-заголовок блока: в ней стоит сокращённое обозначение блока (РС1 — блок режимов
дуговой сварки) и наименования граф блока, а сами значения режима записывают в строках со
служебным символом Р (ГОСТ 3.1407-86, приложение 1, п. 3).

Первый (заглавный) лист несёт адресный блок и блок состава исполнителей, последующие —
только адресный: обозначение документа сохраняется на каждом листе
(ГОСТ 3.1407-86, формы 1 и 1а).

Габарит граф — по разработчику: ГОСТ 3.1407-86 (табл. 2, приложение 1, п. 2) задаёт
состав граф и их назначение, а размеры граф ручного заполнения устанавливает разработчик
документов. Здесь ширины выбраны так, чтобы записи этой карты помещались в свои графы,
а вертикальные линии строк К/М и блока режимов, по возможности, совпадали.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

from ekd.primitives import (
    TEXT_2_5,
    TEXT_3_5,
    THICK,
    THIN,
    text_extent,
)
from ekd.sheet import Sheet

__all__ = [
    # геометрия бланка — по ней проверяются графы и собираются листы
    "BAND_ROW_H", "HEAD_ROW_H", "ROW_H", "BOTTOM_ROW_H", "GRAPH1_W", "PAD", "VPAD",
    "CENTER_LIMIT", "CONTENT_W", "BAND_LABEL_W", "BAND_FORM_W", "BAND_NAME_W", "BAND_SIGN_W",
    "BAND_DATE_W",
    # бланк и его заполнение
    "Graph", "GRAPHS", "REGIME", "REGIME_HEADER", "REGIME_BLOCK", "CHANGE_GRAPHS",
    "EXECUTOR_ROWS", "DOCUMENT_ROW", "CONTENT_SIZES", "MARK_SIZES",
    "Cell", "Line", "OperationalCard", "graphs_for", "fit_in", "wrap_text", "card_document",
]

# --- геометрия бланка ---------------------------------------------------------

#: Высота строк адресного блока и шапки таблицы, мм.
BAND_ROW_H = 5.0
HEAD_ROW_H = 5.0
#: Высота строк содержания операции, мм (на бланке их вмещает целое число).
ROW_H = 7.0
#: Нижняя строка бланка — вид документа («ОК | Операционная карта»).
BOTTOM_ROW_H = 5.0
#: Графа 1 (ГОСТ 3.1407-86, табл. 2, ширина 13 мм): обозначение служебного символа и
#: порядковый номер строки. Запись выполняют на уровне одной строки, например А01, М03;
#: на последующих строках одной и той же операции символ не проставляют (ГОСТ 3.1118-82, п. 3.3).
GRAPH1_W = 13.0
#: Отступ записи от линии графы, мм: по горизонтали и по вертикали.
PAD = 1.5
VPAD = 0.75
#: Графы уже этого размера выключаются по центру: в них стоят коды, числа и знаки.
CENTER_LIMIT = 30.0
#: Ширина граф строки: лист A4 (297) минус поля (20 + 5) и графа 1 (13). Графы каждой
#: строки обязаны занимать её целиком — суммы проверяются при сборке листа.
CONTENT_W = 259.0
#: Графы адресного блока и состава исполнителей, мм (ГОСТ 3.1103-82, блоки Б2 и Б1).
BAND_LABEL_W = 22.0     # подпись строки: Разраб., Пров., Утв., Дубл. …
BAND_FORM_W = 52.0      # форма документа: ГОСТ 3.1407-86 Форма 1 (1а)
BAND_NAME_W = 50.0      # фамилия исполнителя
BAND_SIGN_W = 22.0      # подпись исполнителя
BAND_DATE_W = 21.0      # дата подписания


@dataclass(frozen=True)
class Graph:
    """Графа строки: ширина, мм, и её наименование на бланке."""

    width: float
    name: str = ""


#: Графы строк по служебным символам: состав — по ГОСТ 3.1407-86, табл. 2.
GRAPHS: dict[str, tuple[Graph, ...]] = {
    # Строка А — где и что выполняется: цех, участок, рабочее место, номер и наименование
    # операции, обозначения применяемых документов, масса изделия.
    "А": (Graph(11.0, "Цех"), Graph(11.0, "Уч."), Graph(11.0, "РМ"), Graph(13.0, "Опер."),
          Graph(84.0, "Код, наименование операции"), Graph(107.0, "Обозначение документа"),
          Graph(22.0, "МЗ")),
    # Строка Б — оборудование, степень механизации, профессия, разряд, условия труда,
    # количество исполнителей и трудозатраты.
    "Б": (Graph(114.0, "Код, наименование оборудования"), Graph(13.0, "СМ"),
          Graph(18.0, "Проф."), Graph(10.0, "Р"), Graph(12.0, "УТ"), Graph(10.0, "КР"),
          Graph(18.0, "КОИД"), Graph(12.0, "ЕН"), Graph(12.0, "ОП"), Graph(14.0, "Кшт."),
          Graph(14.0, "Тпз."), Graph(12.0, "Тшт.")),
    # Строки К и М — комплектующие детали и материалы операции.
    "К/М": (Graph(142.0, "Наименование детали, сб. единицы или материала"),
            Graph(55.0, "Обозначение, код"), Graph(12.0, "ОПП"), Graph(10.0, "ЕВ"),
            Graph(10.0, "ЕН"), Graph(10.0, "КИ"), Graph(20.0, "Н.расх.")),
    # Строки О и Т — содержание операции и технологическая оснастка: запись идёт по всей
    # длине строки, с переносом на последующие строки (ГОСТ 3.1407-86, пп. 2.9, 2.10.1).
    "О": (Graph(CONTENT_W),),
    "Т": (Graph(CONTENT_W),),
}

#: Типовой блок режимов сварки РС1 (ГОСТ 3.1407-86, приложение 1, черт. 1) — в составе граф,
#: относящихся к ручной дуговой сварке. Графы механизированных способов (Dc — диаметр сопла,
#: lc, lэ — вылет электрода, Vc, qоз, qдз…) в карту не входят: записывают только параметры
#: принятого способа сварки (ГОСТ 3.1407-86, приложение 1, п. 2; лекция 1, § 5).
REGIME: tuple[Graph, ...] = (Graph(45.0, "ПС"), Graph(40.0, "НП"), Graph(40.0, "Пл"),
                             Graph(67.0, "U"), Graph(67.0, "I"))

#: Служебные символы, у которых своя раскладка граф: К и М записывают в графы строки К/М,
#: Р — в графы блока режимов сварки.
_SYMBOL_GRAPHS: dict[str, str] = {"К": "К/М", "М": "К/М", "Р": "РС1"}

#: Обозначение блока режимов сварки в графе 1: строка-заголовок блока не нумеруется.
REGIME_BLOCK = "РС1"
#: Наименования граф блока режимов — только для чтения: по ним собирается строка-заголовок.
REGIME_HEADER = tuple(graph.name for graph in REGIME)

#: Раскладки граф: строки форм ЕСТД и блок режимов сварки — одна карта на все раскладки.
_LAYOUTS: dict[str, tuple[Graph, ...]] = {**GRAPHS, REGIME_BLOCK: REGIME}

#: Наименования граф адресного блока и состава исполнителей (ГОСТ 3.1103-82, блоки Б1–Б5).
CHANGE_GRAPHS = ("Изм.", "Лист", "№ докум.", "Подп.", "Дата")
EXECUTOR_ROWS = ("Разраб.", "Пров.", "Т.контр.", "Н.контр.", "Утв.")
#: Строка бланка, которой подписывают вид документа.
DOCUMENT_ROW = ("ОК", "Операционная карта")


def graphs_for(symbol: str) -> tuple[Graph, ...]:
    """Графы строки с этим служебным символом (ГОСТ 3.1407-86, табл. 2)."""
    try:
        return _LAYOUTS[_SYMBOL_GRAPHS.get(symbol, symbol)]
    except KeyError:
        raise ValueError(
            f"неизвестный служебный символ {symbol!r}; известные: "
            f"{sorted(set(GRAPHS) | set(_SYMBOL_GRAPHS))}"
        ) from None


def wrap_text(text: str, limit: float) -> list[str]:
    """Разложить запись по строкам бланка, не выходя за ``limit`` мм.

    Перенос записи на последующие строки — штатный приём ЕСТД: строки бланка нумеруются,
    а служебный символ ставится только на первой (ГОСТ 3.1407-86, п. 2.9).
    """
    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if current and text_extent(candidate, TEXT_2_5)[0] > limit:
            lines.append(current)
            current = word
        else:
            current = candidate
    lines.append(current)
    return lines


#: Размеры шрифта: записи граф — по ГОСТ 2.304, графа 1 и вид документа — крупнее.
CONTENT_SIZES = (TEXT_2_5,)
MARK_SIZES = (TEXT_3_5, TEXT_2_5)


def fit_in(text: str, width: float, room: float, sizes: Sequence[float] = CONTENT_SIZES) -> float:
    """Размер шрифта из ``sizes``, при котором запись влезает в графу и по высоте строки.

    :func:`ekd.primitives.fit_height` смотрит только на ширину графы — запись, подобранная
    им, может не влезть в строку по высоте: над строкой и под ней стоят линии бланка.
    Размер берётся наибольший из допустимых, а если не помещается самый мелкий — это
    ошибка автора карты, и она должна быть видна сразу, а не на печати.
    """
    for size in sizes:
        text_width, down, up = text_extent(text, size)
        if text_width <= width and up - down <= room:
            return size
    raise ValueError(
        f"«{text}» не помещается в графу {width:g} × {room:g} мм "
        f"шрифтом {min(sizes):g} мм"
    )


@dataclass(frozen=True)
class Cell:
    """Ячейка адресного блока: ширина, запись и выключка.

    ``align`` — выключка записи: ``middle`` по центру графы, ``start`` от левого края,
    ``auto`` — по ширине графы (узкие графы выключаются по центру, широкие — от края).
    """

    width: float
    text: str = ""
    align: str = "middle"


@dataclass(frozen=True)
class Line:
    """Строка бланка: запись графы 1, раскладка граф и их значения.

    ``layout`` — служебный символ, графы которого занимает строка: у строки-продолжения и у
    свободной строки символ не печатается, но разметка граф сохраняется. ``header`` — строка
    с обозначением блока режимов: она не нумеруется (ГОСТ 3.1407-86, приложение 1, п. 3).
    """

    symbol: str
    layout: str
    cells: tuple[str, ...]
    header: bool = False

    def mark(self, number: str = "") -> str:
        """Запись графы 1: символ и номер строки, например «А01»."""
        return f"{self.symbol}{number}"


@dataclass
class OperationalCard:
    """Лист операционной карты: адресный блок, состав исполнителей и строки операции."""

    designation: str
    product: str
    name: str
    organisation: str
    letter: str
    first: bool = True
    sheet_number: int = 1
    sheet_count: int = 1
    rows: list[Line] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.sheet_number < 1 or self.sheet_count < self.sheet_number:
            raise ValueError(
                f"лист {self.sheet_number} из {self.sheet_count}: номер листа должен быть "
                "не меньше единицы и не больше числа листов"
            )

    # -- строки операции -------------------------------------------------------

    def add(self, symbol: str, *cells: str) -> Line:
        """Добавить строку: символ задаёт и служебную роль строки, и раскладку её граф."""
        graphs = graphs_for(symbol)
        if len(cells) > len(graphs):
            raise ValueError(
                f"строка {symbol}: записей {len(cells)}, а граф {len(graphs)}"
            )
        line = Line(symbol, symbol, tuple(cells) + ("",) * (len(graphs) - len(cells)),
                    header=symbol == REGIME_BLOCK)
        self.rows.append(line)
        return line

    def blank(self, symbol: str = "О") -> Line:
        """Оставить строку свободной — под возможные изменения (ГОСТ 3.1407-86, п. 2.8.2)."""
        line = Line("", symbol, tuple("" for _ in graphs_for(symbol)))
        self.rows.append(line)
        return line

    def lines(self) -> list[Line]:
        """Разложить строки по строкам бланка: длинная запись переносится на следующие.

        Строка с одной графой (содержание операции, оснастка) переносится по словам;
        в многографных строках запись обязана помещаться в свою графу, и если она не
        помещается — это ошибка автора карты, а не повод печатать её поверх линии.
        """
        lines: list[Line] = []
        for row in self.rows:
            graphs = graphs_for(row.layout)
            if len(graphs) == 1:
                text = row.cells[0]
                if not text:
                    lines.append(row)
                    continue
                for index, part in enumerate(wrap_text(text, graphs[0].width - 2 * PAD)):
                    lines.append(Line(row.symbol if index == 0 else "", row.layout, (part,),
                                      row.header))
                continue
            for graph, value in zip(graphs, row.cells):
                if value and text_extent(value, TEXT_2_5)[0] > graph.width - 2 * PAD:
                    raise ValueError(
                        f"«{value}» не помещается в графу {graph.name!r} "
                        f"({graph.width:g} мм) шрифтом {TEXT_2_5:g} мм"
                    )
            lines.append(row)
        return lines

    # -- бланк ------------------------------------------------------------------

    def band(self) -> tuple[tuple[Cell, ...], ...]:
        """Строки адресного блока: изменения, состав исполнителей и адресная информация.

        Состав — по ГОСТ 3.1103-82: блок дополнительной информации Б4 (Дубл., Взам., Подл.),
        блок изменений Б3, блок состава исполнителей Б2 и адресный блок Б1. На последующих
        листах блока состава исполнителей нет (ГОСТ 3.1407-86, форма 1а), но обозначение
        документа и изделия остаются.
        """
        changes = (Cell(16.0, CHANGE_GRAPHS[0]), Cell(16.0, CHANGE_GRAPHS[1]),
                   Cell(40.0, CHANGE_GRAPHS[2]), Cell(24.0, CHANGE_GRAPHS[3]),
                   Cell(28.0, CHANGE_GRAPHS[4]))
        form = Cell(BAND_FORM_W, "ГОСТ 3.1407-86 Форма 1" if self.first
                    else "ГОСТ 3.1407-86 Форма 1а")
        rest = CONTENT_W - BAND_LABEL_W - BAND_FORM_W - sum(c.width for c in changes)
        header = (Cell(BAND_LABEL_W, "Дубл."), Cell(rest)) + changes + (form,)
        support = (Cell(BAND_LABEL_W),) + tuple(Cell(c.width) for c in (Cell(rest), *changes)) \
            + (Cell(form.width),)
        rows = [header, (Cell(BAND_LABEL_W, "Взам."), *support[1:]),
                (Cell(BAND_LABEL_W, "Подл."), *support[1:])]
        if not self.first:
            # Адресный блок последующего листа (ГОСТ 3.1103-82, блок Б1): организация, изделие,
            # обозначение документа и литера — те же, что на первом листе, плюс номер листа.
            rows.append((Cell(20.0, "Лист"), Cell(24.0, str(self.sheet_number)),
                         Cell(20.0, "Листов"), Cell(24.0, str(self.sheet_count)),
                         Cell(26.0, self.organisation), Cell(42.0, self.product),
                         Cell(48.0, self.designation), Cell(19.0, self.letter),
                         Cell(36.0, self.name, align="start")))
            return tuple(rows)

        address = (Cell(30.0, self.organisation, align="start"), Cell(44.0, self.product),
                   Cell(50.0, self.designation), Cell(20.0, self.letter))
        wide = CONTENT_W - BAND_LABEL_W - BAND_NAME_W - BAND_SIGN_W - BAND_DATE_W
        for index, executor in enumerate(EXECUTOR_ROWS):
            if index == 0:
                right = address
            elif index == 1:
                right = (Cell(wide - 70.0, self.name, align="start"),
                         Cell(50.0, f"Лист {self.sheet_number}"),
                         Cell(20.0, f"Листов {self.sheet_count}"))
            else:
                right = (Cell(wide),)
            rows.append((Cell(BAND_LABEL_W, executor), Cell(BAND_NAME_W), Cell(BAND_SIGN_W),
                         Cell(BAND_DATE_W)) + right)
        return tuple(rows)

    def sheet(self) -> Sheet:
        """Собрать лист операционной карты."""
        sheet = Sheet("A4", scale=1.0)
        sheet.add_frame()
        x0, y0, x1, y1 = sheet.frame_rect
        width = x1 - x0
        top = y1
        for cells in self.band():
            self._band_row(sheet, x0, top, cells, width)
            top -= BAND_ROW_H

        for symbol in ("А", "Б", "К/М"):
            graphs = graphs_for(symbol)
            self._table_row(sheet, x0, top, top - HEAD_ROW_H, graphs, symbol,
                            tuple(graph.name for graph in graphs), width, head=True)
            top -= HEAD_ROW_H

        bottom = y0 + BOTTOM_ROW_H
        capacity = max(1, int((top - bottom) // ROW_H))
        height = (top - bottom) / capacity
        lines = self.lines()
        if len(lines) > capacity:
            raise ValueError(
                f"строк {len(lines)}, а на листе {self.sheet_number} помещается {capacity} "
                "— сократите записи или разнесите операцию по листам"
            )

        number = 1
        for index in range(capacity):
            row_top = top - index * height
            row_bottom = row_top - height
            line = lines[index] if index < len(lines) else None
            graphs = (graphs_for(line.layout) if line
                      else (Graph(width - GRAPH1_W),))
            cells = line.cells if line else ("",)
            if line is not None and line.header:
                mark = line.symbol
            else:
                mark = (line or Line("", "О", ())).mark(f"{number:02d}")
                number += 1
            self._table_row(sheet, x0, row_top, row_bottom, graphs, mark, cells, width)

        # Нижняя строка бланка: вид документа.
        self._table_row(sheet, x0, bottom, y0, (Graph(width - GRAPH1_W),),
                        DOCUMENT_ROW[0], DOCUMENT_ROW[1:], width, sizes=MARK_SIZES)
        return sheet

    # -- отрисовка -------------------------------------------------------------

    def _spans(self, x0: float, graphs: Sequence[Graph]) -> list[tuple[float, float]]:
        """Полосы граф строки: (левый край, правый край), мм."""
        spans: list[tuple[float, float]] = []
        x = x0 + GRAPH1_W
        for graph in graphs:
            spans.append((x, x + graph.width))
            x += graph.width
        return spans

    def _table_row(self, sheet: Sheet, x0: float, y_top: float, y_bottom: float,
                   graphs: Sequence[Graph], mark: str, cells: Sequence[str], width: float,
                   *, head: bool = False, sizes: Sequence[float] = CONTENT_SIZES) -> None:
        """Строка бланка: графа 1, линии граф и записи (``head`` — наименования граф)."""
        self._assert_width(graphs, width, f"строки {mark or '—'!r}")
        x1 = x0 + width
        sheet.add_line(x0, y_bottom, x1, y_bottom, width=THIN)
        sheet.add_line(x0, y_bottom, x0, y_top, width=THICK)
        sheet.add_line(x0 + GRAPH1_W, y_bottom, x0 + GRAPH1_W, y_top, width=THIN)
        centre = (y_top + y_bottom) / 2.0
        room = y_top - y_bottom
        if mark:
            sheet.add_text(x0 + GRAPH1_W / 2.0, centre, mark,
                           height=fit_in(mark, GRAPH1_W - 1.0, room - 2 * VPAD, MARK_SIZES),
                           anchor="middle", valign="center")
        for (left, right), cell in zip(self._spans(x0, graphs), cells):
            if right < x1:
                sheet.add_line(right, y_bottom, right, y_top, width=THIN)
            self._label(sheet, (left, right), centre, cell, room,
                        align="middle" if head else "auto", sizes=sizes)

    def _band_row(self, sheet: Sheet, x0: float, y_top: float, cells: Sequence[Cell],
                  width: float) -> None:
        """Строка адресного блока: подписи граф по ГОСТ 3.1103-82."""
        self._assert_width(cells, width, "адресного блока")
        y_bottom = y_top - BAND_ROW_H
        sheet.add_line(x0, y_bottom, x0 + width, y_bottom, width=THIN)
        sheet.add_line(x0, y_bottom, x0, y_top, width=THICK)
        sheet.add_line(x0 + GRAPH1_W, y_bottom, x0 + GRAPH1_W, y_top, width=THIN)
        for (left, right), cell in zip(self._spans(x0, cells), cells):
            if right < x0 + width:
                sheet.add_line(right, y_bottom, right, y_top, width=THIN)
            self._label(sheet, (left, right), (y_top + y_bottom) / 2.0, cell.text,
                        y_top - y_bottom, cell.align)

    def _label(self, sheet: Sheet, span: tuple[float, float], y: float, text: str,
               room: float, align: str = "auto",
               sizes: Sequence[float] = CONTENT_SIZES) -> None:
        """Запись в графе: подбор размера шрифта и выключка по ширине графы.

        ``align="auto"`` — выключка по ширине графы: в узких графах (коды, числа, знаки)
        запись идёт по центру, в широких — от левого края.
        """
        if not text:
            return
        width = span[1] - span[0]
        height = fit_in(text, width - 2 * PAD, room - 2 * VPAD, sizes)
        if align == "auto":
            align = "middle" if width <= CENTER_LIMIT else "start"
        x = (span[0] + span[1]) / 2.0 if align == "middle" else span[0] + PAD
        sheet.add_text(x, y, text, height=height, anchor=align, valign="center")

    def _assert_width(self, cells: Sequence[Cell | Graph], width: float, what: str) -> None:
        """Графы строки должны занимать лист целиком — иначе бланк поедет."""
        total = sum(cell.width for cell in cells) + GRAPH1_W
        if abs(total - width) > 1e-9:
            raise ValueError(f"графы {what} занимают {total:g} мм, а лист даёт {width:g} мм")



def card_document(cards: Sequence[OperationalCard], *, folder: Path | str,
                  svg_prefix: str = "Операционная_карта_лист",
                  pdf_name: str = "Операционная_карта.pdf") -> tuple[Path, ...]:
    """Записать документ целиком: SVG на каждый лист и один PDF со всеми листами."""
    from ekd.sheet import save_document

    folder = Path(folder)
    svg = [folder / f"{svg_prefix}_{card.sheet_number}.svg" for card in cards]
    return save_document([card.sheet() for card in cards], svg=svg, pdf=folder / pdf_name)
