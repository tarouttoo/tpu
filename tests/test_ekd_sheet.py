"""Лист ЕСКД: рамка, основная надпись; один источник — SVG и PDF.

Проверяется то, что видно на листе: размеры рамки и штампа, вынос текста за рамку,
одинаковость листа в обоих файлах и повторяемость сборки.
"""

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from ekd import sheet as ekd

SVG = "{http://www.w3.org/2000/svg}"
MM_PER_PT = 25.4 / 72.0


# --- рамка и основная надпись -------------------------------------------------


def test_frame_margins_follow_gost_2_301():
    s = ekd.Sheet("A3")
    s.add_frame()
    x0, y0, x1, y1 = s.frame_rect
    assert (x0, y0) == (20.0, 5.0), "поле подшивки 20 мм слева, остальные 5 мм"
    assert (x1, y1) == (415.0, 292.0)


def test_title_block_is_gost_2_104_form_1():
    s = ekd.Sheet("A3")
    s.add_frame()
    s.add_title_block(designation="3865.00.10 СБ", name="Направляющая", scale="1:1")
    bx0, by0, bx1, by1 = s.title_block_rect
    assert (bx1 - bx0, by1 - by0) == (185.0, 55.0), "форма 1 — 185 × 55 мм"
    assert (bx1, by0) == (s.frame_rect[2], s.frame_rect[1]), "штамп в правом нижнем углу рамки"


def test_title_block_fields_reach_the_paper():
    s = ekd.Sheet("A3")
    s.add_frame()
    s.add_title_block(
        designation="3865.00.10 СБ",
        name="Направляющая",
        document="Схема базирования",
        scale="1:1",
        letter="У",
    )
    text = s.texts()
    assert "3865.00.10 СБ" in text
    assert "Направляющая" in text
    assert "Схема базирования" in text
    assert "1:1" in text


def test_nothing_is_drawn_outside_the_frame():
    s = ekd.Sheet("A3")
    s.add_frame()
    s.add_title_block(designation="3865.00.10 СБ", name="Направляющая")
    s.add_text(60, 200, "Установочная база — точки 1, 2, 3", height=3.5)
    x0, y0, x1, y1 = s.frame_rect
    bx0, by0, bx1, by1 = s.bounds()
    assert bx0 >= x0 - 0.01 and by0 >= y0 - 0.01
    assert bx1 <= x1 + 0.01 and by1 <= y1 + 0.01


def test_long_name_shrinks_but_stays_inside_its_cell():
    s = ekd.Sheet("A3")
    s.add_frame()
    s.add_title_block(designation="3865.00.10 СБ", name="Направляющая", document="Схема базирования")
    bx0 = s.title_block_rect[0]
    for label in s.labels():
        if label.text in ("Направляющая", "Схема базирования"):
            x0, _, x1, _ = ekd.text_box(label)
            assert bx0 + 65.0 <= x0 and x1 <= bx0 + 135.0, (
                f"«{label.text}» вылезло из графы 1 шрифтом {label.height} мм"
            )


def test_name_that_cannot_fit_is_refused():
    s = ekd.Sheet("A3")
    s.add_frame()
    with pytest.raises(ValueError, match="не помещается"):
        s.add_title_block(designation="3865.00.10 СБ", name="Н" * 60)


def test_text_height_is_the_cap_height_of_gost_2_304():
    s = ekd.Sheet("A3")
    s.add_text(100, 100, "Н", height=5.0)
    _, y0, _, y1 = s.bounds(primitives="text")
    assert y1 - y0 == pytest.approx(5.0, abs=0.1), "высота прописной буквы — 5 мм"
    assert y0 == pytest.approx(100.0, abs=0.1), "надпись стоит на своей базовой линии"


def test_unknown_anchor_is_refused_at_the_sheet():
    """Выключка — из словаря модуля: опечатка видна при сборке листа, а не при печати."""
    s = ekd.Sheet("A3")
    with pytest.raises(ValueError, match="anchor"):
        s.add_text(10, 10, "надпись", anchor="centre")
    with pytest.raises(ValueError, match="valign"):
        s.add_text(10, 10, "надпись", valign="centre")


# --- один источник, два файла -------------------------------------------------


def _demo_sheet() -> ekd.Sheet:
    s = ekd.Sheet("A3")
    s.add_frame()
    s.add_title_block(designation="3865.00.10 СБ", name="Направляющая")
    s.add_line(40, 40, 200, 40)
    s.add_circle(120, 200, 20)
    s.add_text(40, 240, "Схема базирования — УНО", height=7.0)
    return s


def test_one_run_writes_both_svg_and_pdf(tmp_path):
    svg, pdf = _demo_sheet().save(svg=tmp_path / "s.svg", pdf=tmp_path / "s.pdf")
    assert svg.exists() and svg.stat().st_size > 1000
    assert pdf.exists() and pdf.stat().st_size > 1000


def test_both_files_are_the_same_a3_sheet(tmp_path):
    svg, pdf = _demo_sheet().save(svg=tmp_path / "s.svg", pdf=tmp_path / "s.pdf")
    root = ET.parse(svg).getroot()
    assert root.get("width") == "420mm", "физический размер листа задан в миллиметрах"
    assert root.get("height") == "297mm"
    view_box = [float(v) for v in root.get("viewBox").split()]
    assert view_box[2] / view_box[3] == pytest.approx(420.0 / 297.0, abs=1e-3)
    assert view_box[0] == 0.0 and view_box[1] == 0.0

    page = _pdf_page(pdf)
    assert page.rect.width * MM_PER_PT == pytest.approx(420.0, abs=0.5)
    assert page.rect.height * MM_PER_PT == pytest.approx(297.0, abs=0.5)


def test_both_files_show_the_same_ink(tmp_path):
    svg, pdf = _demo_sheet().save(svg=tmp_path / "s.svg", pdf=tmp_path / "s.pdf")
    assert _svg_ink_bbox(svg) == pytest.approx(_pdf_ink_bbox(pdf), abs=1.0)


def test_the_run_repeats_bit_for_bit(tmp_path):
    first = _demo_sheet().save(svg=tmp_path / "a.svg", pdf=tmp_path / "a.pdf")
    second = _demo_sheet().save(svg=tmp_path / "b.svg", pdf=tmp_path / "b.pdf")
    for a, b in zip(first, second):
        assert a.read_bytes() == b.read_bytes(), f"{a.name} меняется от запуска к запуску"


def test_pdf_carries_selectable_text(tmp_path):
    _, pdf = _demo_sheet().save(svg=tmp_path / "s.svg", pdf=tmp_path / "s.pdf")
    assert "Схема базирования" in _pdf_page(pdf).get_text()


# --- залитые многоугольники и штрихпунктирные линии ---------------------------


def test_filled_polygons_and_dashes_reach_both_files(tmp_path):
    """Стрелки размеров и осевые линии одинаково попадают в SVG и PDF."""
    from ekd.dimensions import ARROW_LENGTH, ARROW_WIDTH, horizontal
    from ekd.primitives import CenterLine

    sheet = ekd.Sheet("A3")
    sheet.add_frame()
    horizontal(sheet, (40.0, 100.0), (160.0, 100.0), at=80.0, label="124 +0,2")
    sheet.add(CenterLine(200.0, 40.0, 200.0, 250.0))
    svg, pdf = sheet.save(svg=tmp_path / "s.svg", pdf=tmp_path / "s.pdf")

    assert "stroke-dasharray" in svg.read_text(encoding="utf-8"), "осевая линия — штрихпунктир"
    page = _pdf_page(pdf)
    arrows = [item["rect"] for item in page.get_drawings()
              if item.get("fill") and item["rect"].width < 20 and item["rect"].height < 20]
    assert len(arrows) == 2, "две зачернённые стрелки"
    for rect in arrows:
        assert rect.width * MM_PER_PT == pytest.approx(ARROW_LENGTH, abs=0.1)
        assert rect.height * MM_PER_PT == pytest.approx(ARROW_WIDTH, abs=0.1)


def test_filled_polygon_primitive_is_drawn_but_keeps_its_shape():
    from ekd.primitives import FilledPolygon

    sheet = ekd.Sheet("A3")
    sheet.add(FilledPolygon(((10.0, 10.0), (20.0, 10.0), (15.0, 20.0))))
    segments, circles, polygons, labels = sheet.geometry()
    assert segments == [] and circles == [] and labels == []
    assert polygons == [((10.0, 10.0), (20.0, 10.0), (15.0, 20.0))]
    assert sheet.bounds() == (10.0, 10.0, 20.0, 20.0), "габарит учитывает залитый многоугольник"


# --- помощники проверки -------------------------------------------------------


def _pdf_page(pdf: Path):
    pymupdf = pytest.importorskip("pymupdf")
    return pymupdf.open(pdf)[0]


_TRANSFORM = re.compile(r"(translate|scale|matrix)\(([^)]*)\)")


def _apply(transform: list[float], x: float, y: float) -> tuple[float, float]:
    a, b, c, d, e, f = transform
    return a * x + c * y + e, b * x + d * y + f


def _compose(transform: list[float], op: str, values: list[float]) -> list[float]:
    if op == "translate":
        dx, dy = (values + [0.0])[:2]
        new = [1.0, 0.0, 0.0, 1.0, dx, dy]
    elif op == "scale":
        sx, sy = (values + [values[0]])[:2]
        new = [sx, 0.0, 0.0, sy, 0.0, 0.0]
    else:
        new = (values + [1.0, 0.0, 0.0, 1.0, 0.0, 0.0])[:6]
    a, b, c, d, e, f = transform
    na, nb, nc, nd, ne, nf = new
    return [a * na + c * nb, b * na + d * nb, a * nc + c * nd, b * nc + d * nd,
            a * ne + c * nf + e, b * ne + d * nf + f]


_NUM = re.compile(r"-?\d*\.?\d+(?:e-?\d+)?")


def _svg_ink_bbox(svg: Path) -> tuple[float, float, float, float]:
    """Чернила SVG в миллиметрах листа: координаты всех путей с накопленной матрицей.

    matplotlib пишет координаты в пунктах и разворачивает ось Y группой `scale(1,-1)`,
    поэтому результат приводится к системе листа: миллиметры, Y вверх от нижнего края.
    """
    root = ET.parse(svg).getroot()
    xs: list[float] = []
    ys: list[float] = []

    def walk(node, transform: list[float]) -> None:
        local = list(transform)
        for op, values in _TRANSFORM.findall(node.get("transform", "")):
            numbers = [float(v) for v in re.split(r"[,\s]+", values.strip()) if v]
            local = _compose(local, op, numbers)
        d = node.get("d")
        if d:
            numbers = [float(v) for v in _NUM.findall(d)]
            for i in range(0, len(numbers) - 1, 2):
                x, y = _apply(local, numbers[i], numbers[i + 1])
                xs.append(x * MM_PER_PT)
                ys.append(y * MM_PER_PT)
        for child in node:
            walk(child, local)

    walk(root, [1.0, 0.0, 0.0, 1.0, 0.0, 0.0])
    return (min(xs), 297.0 - max(ys), max(xs), 297.0 - min(ys))


def _pdf_ink_bbox(pdf: Path) -> tuple[float, float, float, float]:
    page = _pdf_page(pdf)
    box = [float("inf"), float("inf"), float("-inf"), float("-inf")]
    for item in page.get_drawings():
        rect = item["rect"]
        corners = [(rect.x0, rect.y0), (rect.x1, rect.y1)]
        for x, y in corners:
            box[0] = min(box[0], x)
            box[1] = min(box[1], y)
            box[2] = max(box[2], x)
            box[3] = max(box[3], y)
    for block in page.get_text("blocks"):
        x0, y0, x1, y1 = block[:4]
        box[0] = min(box[0], x0)
        box[1] = min(box[1], y0)
        box[2] = max(box[2], x1)
        box[3] = max(box[3], y1)
    mm = [v * MM_PER_PT for v in box]
    return (mm[0], 297.0 - mm[3], mm[2], 297.0 - mm[1])
