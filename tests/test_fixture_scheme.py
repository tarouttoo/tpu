"""Принципиальная схема приспособления 3865.00.10: плита, опоры, упоры и зажимы.

Проверяется инженерное содержание схемы (состав знаков и их положение — то же, что в
расчёте размерных цепей) и то, что попадает на лист: подписи, размеры с допусками,
читаемость листа и артефакт этапа (SVG + PDF из одного запуска).
"""

from pathlib import Path

import pytest

import dimensional_chains as calc
import fixture_scheme as doc
from ekd.dimensions import LinearDimension
from ekd.primitives import CenterLine, FilledPolygon
from ekd.symbols import (
    SURFACE_FLAT,
    SURFACE_SPHERICAL,
    ClampSide,
    SurfaceMark,
    SupportSide,
    SupportTop,
)

STEP = Path(__file__).resolve().parent.parent / "STEP" / "guide.step"


@pytest.fixture(scope="module")
def sheet():
    """Лист собирается один раз: сборка читает STEP и проецирует изделие — это долго."""
    return doc.build_sheet()


def front(x: float, z: float) -> tuple[float, float]:
    """Как точка изделия (X, Z) ложится на главный вид."""
    return (doc.VIEW_X + x, doc.Z0_Y + z)


def top(x: float, y: float) -> tuple[float, float]:
    """Как точка изделия (X, Y) ложится на вид сверху."""
    return (doc.VIEW_X + x, doc.PLAN_Y0 + y)


# --- состав схемы -------------------------------------------------------------


def test_every_element_of_the_calculation_is_on_the_sheet(sheet):
    """Опора, упор и зажим из расчёта размерных цепей — со знаком на листе."""
    sides = [p for p in sheet.symbols() if isinstance(p, SupportSide)]
    circles = [p for p in sheet.symbols() if isinstance(p, SupportTop)]
    clamps = [p for p in sheet.symbols() if isinstance(p, ClampSide)]
    assert (len(sides), len(circles), len(clamps)) == (9, 3, 5), (
        "опоры: знак 1, 2 (точки приложения совпадают на главном виде) и 3, упоры 4–10 — "
        "семь знаков; на виде сверху три окружности ⌀6; зажимы: З1 и З2 показаны одним "
        "знаком, всего пять знаков на шесть зажимов"
    )
    assert calc.elements() and calc.clamps()


def test_supports_stand_where_the_calculation_puts_them(sheet):
    """Опоры 1–3 — по координатам расчёта: под Стойками, на установочной плоскости."""
    expected = {(-calc.POST_X, -calc.SUPPORT_Y), (-calc.POST_X, calc.SUPPORT_Y),
                (calc.POST_X, 0.0)}
    circles = [p for p in sheet.symbols() if isinstance(p, SupportTop)]
    assert {(c.x - doc.VIEW_X, c.y - doc.PLAN_Y0) for c in circles} == expected
    sides = {p for p in sheet.symbols() if isinstance(p, SupportSide)}
    assert front(-calc.POST_X, 0.0) in {(p.x, p.y) for p in sides}, "знак опор 1 и 2"
    assert front(calc.POST_X, 0.0) in {(p.x, p.y) for p in sides}, "знак опоры 3"


def test_stops_stand_on_the_contact_planes_of_the_calculation(sheet):
    sides = {(p.x, p.y): p for p in sheet.symbols() if isinstance(p, SupportSide)}
    # Задний упор 4–5: контактная плоскость Y = −45 на виде сверху.
    for number, x in ((4, -calc.POST_X), (5, calc.POST_X)):
        assert top(x, calc.REAR_STOP_Y) in sides, f"упор {number}"
    # Упор 6 — торец правой Стойки, упоры 7 и 8 — внутренние плоскости Стоек.
    assert top(calc.END_STOP_X, 0.0) in sides, "упор 6"
    contact_z = calc.INNER_STOP_HEIGHT / 2
    assert front(-calc.INNER_STOP_X, contact_z) in sides, "упор 7"
    assert front(calc.INNER_STOP_X, contact_z) in sides, "упор 8"
    # Упоры 9 и 10 — на плоскости торцов Перемычки.
    assert {p.x for p in sides.values() if abs(p.x - top(calc.BAR_STOP_X, 0.0)[0]) < 1e-9}


def test_clamps_sit_over_the_supports_or_on_their_axes(sheet):
    """Зажимы — над опорами или на их осях: опрокидывающего момента нет."""
    clamps = [p for p in sheet.symbols() if isinstance(p, ClampSide)]
    assert front(-calc.POST_X, calc.POST_HEIGHT) in {(c.x, c.y) for c in clamps}, "З1, З2"
    assert front(calc.POST_X, calc.POST_HEIGHT) in {(c.x, c.y) for c in clamps}, "З3"
    assert front(calc.END_STOP_X, calc.CLAMP_Z) in {(c.x, c.y) for c in clamps}, "З5"
    assert top(-calc.END_STOP_X, 0.0) in {(c.x, c.y) for c in clamps}, "З4"
    assert top(0.0, calc.OVERALL_WIDTH / 2) in {(c.x, c.y) for c in clamps}, "З6"

    # Точки приложения силы зажимов З1…З3 — на осях опор 1–3 (в плане вида сверху).
    supports = {(element["координаты"]["X"]["номинал"], element["координаты"]["Y"]["номинал"])
                for element in calc.elements()[:3]}
    for clamp in calc.clamps()[:3]:
        point = clamp["точка_приложения"]
        assert (point["X"], point["Y"]) in supports, clamp["номер"]
        assert point["Z"] == doc.POST_HEIGHT, "зажим давит на верхние торцы Стоек"


def test_side_clamps_have_the_shoulder_of_the_calculation(sheet):
    """Плечо двойного зажима — расстояние между точками приложения силы."""
    spans = {c.spacing for c in sheet.symbols() if isinstance(c, ClampSide)}
    assert doc.CLAMP_SPAN_SIDE in spans, "З4 — по опорам 1 и 2 (76 мм)"
    assert doc.CLAMP_SPAN in spans, "З6 — по обеим Стойкам (140 мм)"
    assert None in spans, "есть одиночные зажимы"


def test_plate_carries_the_whole_fixture(sheet):
    """Плита показана в обоих видах и перекрывает все точки установки и закрепления."""
    front_plate = [p for p in sheet.primitives if getattr(p, "closed", False)]
    assert len(front_plate) >= 2, "плита: контур на главном виде и на виде сверху"
    for element in calc.elements():
        for axis in ("X", "Y"):
            place = element["координаты"].get(axis)
            if isinstance(place, dict) and "номинал" in place:
                limit = doc.PLATE_X if axis == "X" else doc.PLATE_Y
                assert abs(place["номинал"]) <= limit, element["номер"]
    assert doc.PLATE_TOP_Z < 0, "верх плиты — ниже установочной плоскости: знаки опор стоят на ней"


# --- обозначения по ГОСТ 3.1107-81 -------------------------------------------


def test_every_sign_carries_the_form_of_its_working_surface(sheet):
    """Форма рабочей поверхности — слева от обозначения (ГОСТ 3.1107-81, п. 11)."""
    marks = [p for p in sheet.symbols() if isinstance(p, SurfaceMark)]
    signs = [p for p in sheet.symbols()
             if isinstance(p, (SupportSide, SupportTop, ClampSide))]
    assert len(marks) == len(signs), "у каждого знака своя форма рабочей поверхности"
    for sign in signs:
        standoff = sign.mark_standoff + 1.0 + 3.0 / 2.0
        expected = (sign.x - standoff, sign.y)
        assert any(abs(m.x - expected[0]) < 1e-9 and abs(m.y - expected[1]) < 1e-9
                   for m in marks), f"нет знака формы слева от {sign.kind} в {sign.x:.1f}"


def test_supports_are_spherical_and_stops_are_flat(sheet):
    spherical = [m for m in sheet.symbols() if isinstance(m, SurfaceMark)
                 and m.form == SURFACE_SPHERICAL]
    flat = [m for m in sheet.symbols() if isinstance(m, SurfaceMark) and m.form == SURFACE_FLAT]
    assert len(spherical) == 5, "опоры 1, 2, 3 — на главном виде и на виде сверху"
    assert len(flat) == 12, "семь упоров и пять знаков зажимов — с плоской поверхностью"


def test_unknown_surface_form_is_refused():
    with pytest.raises(ValueError, match="форма рабочей поверхности"):
        SurfaceMark(10.0, 10.0, "рифленая")


def test_shoulder_of_a_double_clamp_must_be_positive():
    with pytest.raises(ValueError, match="плечо"):
        ClampSide(10.0, 10.0, 0.0, 0.0)


# --- размеры -------------------------------------------------------------------


def test_dimensions_come_from_the_dimensional_chains(sheet):
    """Размеры расположения опор и упоров — с допусками из расчёта размерных цепей."""
    texts = sheet.texts()
    for row in calc.fixture_dimensions():
        number, _, deviation = row["размер_приспособления"].partition(" ")
        assert number in texts, row["обозначение"]
        assert deviation in texts, row["обозначение"]
    for coordinate in (f"{calc.num(calc.POST_X)}", f"{calc.num(calc.SUPPORT_Y)}"):
        assert coordinate in texts


def test_every_dimension_is_linear_and_has_arrows(sheet):
    dimensions = [p for p in sheet.primitives if isinstance(p, LinearDimension)]
    assert len(dimensions) == 6, "три размера по длине, три по высоте"
    for dimension in dimensions:
        assert len(dimension.polygons()) == 2, "на концах размерной линии — стрелки"
        assert len(dimension.labels()) >= 1


def test_dimension_labels_keep_the_deviation_next_to_the_number(sheet):
    """Отклонение — меньшим шрифтом, как требует ГОСТ 2.307."""
    labels = [t for p in sheet.primitives if isinstance(p, LinearDimension) for t in p.labels()]
    small = [t for t in labels if t.height == 2.5]
    assert small, "отклонения набраны шрифтом 2,5 мм"
    assert any(t.text.startswith(("+", "−", "±")) for t in small)


# --- лист ----------------------------------------------------------------------


def test_plate_and_axes_are_drawn_with_the_right_lines(sheet):
    centres = [p for p in sheet.primitives if isinstance(p, CenterLine)]
    assert len(centres) == 3, "ось изделия на главном виде и две оси на виде сверху"
    assert all(segment.dash for centre in centres for segment in centre.segments())


def test_notes_name_the_standard_and_the_removable_stops(sheet):
    text = " ".join(sheet.texts())
    for fragment in ("ГОСТ 3.1107-81", "откидные", "сферическая", "плоская",
                     "опрокидывающего момента", "регулируемый", "плита"):
        assert fragment in text, f"на листе нет «{fragment}»"


def test_symbols_and_text_stay_inside_the_frame(sheet):
    x0, y0, x1, y1 = sheet.frame_rect
    for primitive in sheet.symbols():
        points = [(s.x1, s.y1) for s in primitive.segments()]
        points += [(s.x2, s.y2) for s in primitive.segments()]
        points += [(c.x, c.y) for c in primitive.circles()]
        for x, y in points:
            assert x0 < x < x1 and y0 < y < y1, (
                f"знак {primitive.kind} вышел за рамку в ({x:.1f}, {y:.1f})")


def test_labels_do_not_overlap_and_stay_inside_the_frame(sheet):
    """Читаемость листа: подписи не налезают друг на друга и не выходят за рамку."""
    from ekd.sheet import text_box

    x0, y0, x1, y1 = sheet.frame_rect
    bx0, by0, bx1, by1 = sheet.title_block_rect
    labels = [(label.text, text_box(label)) for label in sheet.labels()]

    def in_title_block(box):
        return box[0] >= bx0 - 0.1 and box[2] <= bx1 + 0.1 and box[1] >= by0 - 0.1 \
            and box[3] <= by1 + 0.1

    for text, box in labels:
        if in_title_block(box):
            continue
        if box[2] < x0:
            continue        # графы 19–23 стоят в поле подшивки, левее рамки
        assert box[0] >= x0 - 0.01 and box[1] >= y0 - 0.01, f"«{text}» вышло за рамку слева/снизу"
        assert box[2] <= x1 + 0.01 and box[3] <= y1 + 0.01, f"«{text}» вышло за рамку справа/сверху"

    inside = [(text, box) for text, box in labels if box[2] >= x0]
    for index, (text, box) in enumerate(inside):
        for other, other_box in inside[index + 1:]:
            if in_title_block(box) and in_title_block(other_box):
                continue
            overlap_x = min(box[2], other_box[2]) - max(box[0], other_box[0])
            overlap_y = min(box[3], other_box[3]) - max(box[1], other_box[1])
            assert not (overlap_x > 0.6 and overlap_y > 0.3), f"«{text}» налезает на «{other}»"


def test_notes_do_not_get_into_the_title_block(sheet):
    """Примечания заканчиваются выше штампа: иначе их не прочесть на подлиннике."""
    from ekd.sheet import text_box

    bx0, by0, bx1, by1 = sheet.title_block_rect
    for label in sheet.labels():
        box = text_box(label)
        inside = box[0] >= bx0 - 0.1 and box[2] <= bx1 + 0.1 and box[1] >= by0 - 0.1 \
            and box[3] <= by1 + 0.1
        if inside:
            continue
        hit = min(box[2], bx1) - max(box[0], bx0) > 0.6 and min(box[3], by1) - max(box[1], by0) > 0.3
        assert not hit, f"«{label.text}» заходит на штамп"


# --- артефакт этапа ------------------------------------------------------------


def test_build_writes_svg_and_pdf_into_the_stage_folder(tmp_path):
    svg, pdf = doc.build(out_dir=tmp_path)
    stage = tmp_path / "3865.00.10_SB" / "03_Принципиальная_схема"
    assert svg.parent == stage and pdf.parent == stage
    assert svg.name == "Принципиальная_схема.svg" and pdf.name == "Принципиальная_схема.pdf"
    assert svg.stat().st_size > 1000 and pdf.stat().st_size > 1000

    pymupdf = pytest.importorskip("pymupdf")
    text = pymupdf.open(pdf)[0].get_text()
    for fragment in ("Схема принципиальная", "124", "0,2", "ГОСТ 3.1107-81"):
        assert fragment in text, fragment


def test_committed_artifact_is_up_to_date(tmp_path):
    """Пересборка даёт те же файлы: SVG и PDF не расходятся с исходником этапа."""
    doc.build(out_dir=tmp_path)
    stage = tmp_path / "3865.00.10_SB" / "03_Принципиальная_схема"
    for name in (doc.SVG_NAME, doc.PDF_NAME):
        assert (stage / name).read_bytes() == (doc.OUT_DIR / name).read_bytes(), name
