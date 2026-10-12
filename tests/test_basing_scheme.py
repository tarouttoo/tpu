"""Схема базирования направляющей 3865.00.10: шесть опорных точек по схеме УНО.

Проверяется инженерное содержание схемы (точки лежат на изделии, их состав и
нумерация — по базам) и то, что попадает на лист: подписи точек, базы, ГОСТы.
"""

from pathlib import Path

import pytest

import basing_scheme as doc

STEP = Path(__file__).resolve().parent.parent / "STEP" / "guide.step"


@pytest.fixture(scope="module")
def part():
    cadgen = pytest.importorskip("cadgen")
    return cadgen.read_step(STEP)


@pytest.fixture(scope="module")
def sheet():
    """Лист собирается один раз: сборка читает STEP и проецирует изделие — это долго."""
    return doc.build_sheet()


# --- состав схемы -------------------------------------------------------------


def test_six_points_numbered_from_the_biggest_base():
    assert sorted(doc.POINTS) == [1, 2, 3, 4, 5, 6]
    assert [b.points for b in doc.BASES] == [(1, 2, 3), (4, 5), (6,)], (
        "нумерация начинается с базы, имеющей наибольшее число опорных точек"
    )
    assert [b.dof for b in doc.BASES] == [3, 2, 1]
    assert sum(b.dof for b in doc.BASES) == 6, "правило шести точек"


def test_bases_are_the_agreed_ones():
    assert [b.letter for b in doc.BASES] == ["У", "Н", "О"]
    assert [b.name for b in doc.BASES] == ["установочная", "направляющая", "опорная"]
    assert doc.SCHEME == "УНО"


def test_points_sit_on_the_agreed_faces():
    # Установочная база — нижние кромки стоек (Z = 0).
    assert {doc.POINTS[n][2] for n in (1, 2, 3)} == {0.0}
    # Направляющая база — задние плоскости стоек на одном уровне.
    assert {doc.POINTS[n][1] for n in (4, 5)} == {-45.0}
    assert len({doc.POINTS[n][0] for n in (4, 5)}) == 2, "две точки разнесены по длине"
    # Опорная база — торец.
    assert doc.POINTS[6][0] == 78.0


def test_every_point_lies_on_the_part(part):
    from build123d import Vertex

    for number, point in sorted(doc.POINTS.items()):
        vertex = Vertex(*point)
        distance = part.distance_to(vertex)
        assert distance == pytest.approx(0.0, abs=1e-6), (
            f"точка {number} в {point} не лежит на изделии (расстояние {distance:.3f} мм)"
        )


def test_centre_of_mass_falls_inside_the_support_triangle():
    x, y = doc.centre_of_mass()[:2]
    triangle = [doc.POINTS[n][:2] for n in (1, 2, 3)]
    for i in range(3):
        a, b = triangle[i], triangle[(i + 1) % 3]
        side = (b[0] - a[0]) * (y - a[1]) - (b[1] - a[1]) * (x - a[0])
        assert side < 0, "центр тяжести должен лежать внутри треугольника опорных точек"


def test_symbols_stay_outside_the_part():
    """Риски знака не заходят внутрь изделия: знак рисуется только снаружи контура.

    В таблице 1 ГОСТ 3.1107-81 риски продолжены и выше точки контакта — там знак
    нарисован отдельно от изделия; на схеме верхние половины рисок оказались бы внутри
    контура изделия.
    """
    from ekd.symbols import SupportSide

    for _number, angle in doc.FRONT_SYMBOLS:
        symbol = SupportSide(10.0, 20.0, angle)
        for segment in symbol.segments():
            if angle == 0.0:
                assert max(segment.y1, segment.y2) <= 20.0, "знак зашёл выше точки контакта"
            else:
                assert min(segment.x1, segment.x2) >= 10.0, "знак зашёл левее точки контакта"


# --- лист ---------------------------------------------------------------------


def test_notes_say_the_agreed_thing():
    """Формулировки примечаний — то, что согласовано с человеком; они под проверкой."""
    assert doc.NOTES == (
        "Опоры — неподвижные; знаки по ГОСТ 3.1107-81, табл. 1.",
        "База I — установочная (У): нижние кромки стоек, точки 1, 2, 3; "
        "отнимает три степени свободы.",
        "База II — направляющая (Н): задние плоскости стоек, точки 4, 5; "
        "отнимает две степени свободы.",
        "База III — опорная (О): торец, точка 6; отнимает одну степень свободы.",
        "Схема базирования — УНО (ГОСТ 21495-76); изделие лишено шести степеней свободы.",
        "Точки 1 и 2 на главном виде совпадают — показаны одним обозначением.",
    )


def test_sheet_numbers_every_locating_point(sheet):
    labels = sheet.texts()
    assert "1,2" in labels, "совпадающие в проекции точки 1 и 2 показаны одним номером"
    for number in ("3", "4", "5", "6"):
        assert number in labels


def test_sheet_has_the_two_projections_that_show_all_six_points(sheet):
    assert [v.name for v in sheet.views] == ["front", "top"]


def test_sheet_speaks_the_agreed_terms(sheet):
    text = " ".join(sheet.texts())
    for term in ("УНО", "установочная", "направляющая", "опорная",
                 "ГОСТ 3.1107-81", "ГОСТ 21495-76", "степен"):
        assert term in text, f"на листе нет «{term}»"


def test_points_are_drawn_as_gost_symbols(sheet):
    assert len(sheet.symbols()) == 8, (
        "пять знаков опор на видах спереди/сбоку (1, 2 — одним знаком, 3, 4, 5, 6) "
        "и три знака на виде сверху (1, 2, 3)"
    )


def test_symbols_stay_inside_the_frame(sheet):
    """Знак опоры стоит там, где точка: на контуре изделия, но не за рамкой листа."""
    x0, y0, x1, y1 = sheet.frame_rect
    for primitive in sheet.symbols():
        points = [(s.x1, s.y1) for s in primitive.segments()] + [(s.x2, s.y2) for s in primitive.segments()]
        for mark in primitive.circles():
            points += [(mark.x - mark.diameter / 2, mark.y - mark.diameter / 2),
                       (mark.x + mark.diameter / 2, mark.y + mark.diameter / 2)]
        for x, y in points:
            assert x0 < x < x1 and y0 < y < y1, (
                f"знак опоры {primitive.label!r} вышел за рамку в ({x:.1f}, {y:.1f})"
            )


# --- артефакт этапа -----------------------------------------------------------


def test_build_writes_svg_and_pdf_into_the_stage_folder(tmp_path):
    svg, pdf = doc.build(out_dir=tmp_path)
    stage = tmp_path / "3865.00.10_SB" / "01_Схема_базирования"
    assert svg.parent == stage and pdf.parent == stage
    assert svg.name == "Схема_базирования.svg" and pdf.name == "Схема_базирования.pdf"
    assert svg.stat().st_size > 1000 and pdf.stat().st_size > 1000

    pymupdf = pytest.importorskip("pymupdf")
    text = pymupdf.open(pdf)[0].get_text()
    assert "Схема базирования" in text
    assert "УНО" in text
