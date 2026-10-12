"""Операционная карта направляющей 3865.00.10: операции 05, 10 и 15.

Проверяется то, что согласовано с человеком: номера операций с резервом, переходы сборки
с прихватками, режимы сварки, контроль — и то, что попадает на лист: служебные символы,
графы форм ЕСТД, обозначение документа на каждом листе, совпадение листов в SVG и PDF.
"""

import re
from pathlib import Path

import pytest

import operational_card as doc
from ekd.estd import EXECUTOR_ROWS, GRAPH1_W, REGIME, REGIME_HEADER

STAGE = Path("3865.00.10_SB") / "02_Операционная_карта"


@pytest.fixture(scope="module")
def sheets() -> list:
    """Листы собираются один раз: сборка листа считает метрики надписей — это долго."""
    return [card.sheet() for card in doc.cards()]


def columns(card, symbol: str) -> list[str]:
    """Записи строк с этим служебным символом: по строке на каждое появление."""
    return [line.cells[0] for line in card.rows if line.symbol == symbol]


def row_cells(card, symbol: str) -> list[tuple[str, ...]]:
    return [line.cells for line in card.rows if line.symbol == symbol]


# --- операции ------------------------------------------------------------------


def test_operations_ascend_with_a_reserve_of_numbers():
    numbers = [number for number, _ in doc.OPERATIONS]
    assert numbers == ["05", "10", "15"]
    assert [int(number) for number in numbers] == [5, 10, 15], (
        "номера операций назначают с резервом, шагом 5: в пропуск можно вставить операцию"
    )
    assert numbers == sorted(numbers), "операции идут по возрастанию"
    assert [card.sheet_number for card in doc.cards()] == [1, 2, 3]
    assert all(card.sheet_count == len(doc.OPERATIONS) for card in doc.cards())
    assert [card.first for card in doc.cards()] == [True, False, False], (
        "форма первого листа — только у первой операции"
    )


def test_each_sheet_carries_its_own_operation():
    for index, (number, title) in enumerate(doc.OPERATIONS):
        card = doc.card_for(index)
        row = row_cells(card, "А")[0]
        assert row[3] == number, f"лист {index + 1} — не операция {number}"
        assert row[4] == title
        assert number in card.sheet().texts(), f"на листе {index + 1} нет номера операции"


# --- операция 05 сборка --------------------------------------------------------


def test_assembly_operation_has_the_agreed_transitions():
    card = doc.card_for(0)
    transitions = columns(card, "О")
    assert len(transitions) == 3
    assert transitions[0].startswith("1. Установить заготовки")
    assert "обеспечивая зазор" in transitions[0]
    assert transitions[1].startswith("2. Закрепить заготовки в приспособлении")
    assert transitions[2].startswith("3. Прихватить")


def test_assembly_has_tack_welds_of_4_by_20_mm():
    card = doc.card_for(0)
    tacks = [text for text in columns(card, "О") if "прихват" in text.lower()]
    assert tacks, "в операции сборки нет перехода с прихватками"
    assert "4 × 20 мм" in tacks[0], "прихватки — 4 × 20 мм"
    assert "по две на каждый стык" in tacks[0]


def test_tack_welds_use_the_same_electrode_and_mode_as_welding():
    assembly, welding = doc.card_for(0), doc.card_for(1)
    assert row_cells(assembly, "М") == row_cells(welding, "М"), (
        "прихватки выполняют тем же электродом, что и сварку"
    )
    assert row_cells(assembly, "Р") == row_cells(welding, "Р"), (
        "режим прихваток — тот же, что на сварке"
    )
    assert "УОНИ-13/55" in row_cells(assembly, "М")[0][0]


# --- операция 10 сварка --------------------------------------------------------


def test_welding_modes_match_the_agreed_ones():
    card = doc.card_for(1)
    mode = row_cells(card, "Р")
    assert mode == [("В", "1", "О", "24–26 В", "90–100 А")], (
        "режим: положение В (вертикальное), один проход, обратная полярность, "
        "24–26 В, 90–100 А"
    )
    assert dict(zip(REGIME_HEADER, mode[0])) == {
        "ПС": "В", "НП": "1", "Пл": "О", "U": "24–26 В", "I": "90–100 А",
    }
    assert [graph.name for graph in REGIME] == list(REGIME_HEADER), (
        "заголовок блока режимов собирается из его граф"
    )
    assert doc.WELD_MODE == mode[0]


def test_welding_electrode_is_the_agreed_one():
    electrode = row_cells(doc.card_for(1), "М")[0]
    assert "УОНИ-13/55" in electrode[0]
    assert "Э50А" in electrode[0], "тип электрода — Э50А"
    assert "⌀3" in electrode[0], "диаметр электрода — ⌀3 мм"
    assert electrode[1] == "ГОСТ 9467-75"


def test_welding_is_direct_current_of_reverse_polarity():
    card = doc.card_for(1)
    equipment = " ".join(cells[0] for cells in row_cells(card, "Б"))
    assert "постоянный ток" in equipment, (
        "род сварочного тока записывают в графе оборудования (ГОСТ 3.1407-86, п. 2.8.1)"
    )
    polarity = dict(zip(REGIME_HEADER, row_cells(card, "Р")[0]))["Пл"]
    assert polarity == "О", "полярность — обратная"


def test_welding_transition_names_the_joint_and_the_leg():
    card = doc.card_for(1)
    first = columns(card, "О")[0]
    assert "У5" in first and "ГОСТ 5264-80" in first
    assert "k = 8 мм" in first, "катет углового шва — 8 мм"
    assert "по одному проходу" in first
    assert "четыре" in first.lower()
    second = columns(card, "О")[1]
    assert "Зачистить швы" in second


def test_position_of_welding_allows_working_without_turning_the_part():
    text = columns(doc.card_for(1), "О")[0]
    assert "на бок" in text and "без кантовки и перезакрепления" in text


# --- операция 15 контроль ------------------------------------------------------


def test_control_operation_is_visual_and_measuring():
    card = doc.card_for(2)
    title = row_cells(card, "А")[0][4]
    assert "Контроль" in title and "визуально-измерительный" in title
    transitions = " ".join(columns(card, "О"))
    assert "визуально-измерительный контроль сварных швов" in transitions
    assert "Измерить катет" in transitions and "k = 8 мм" in transitions


def test_control_operation_lists_measuring_instruments():
    card = doc.card_for(2)
    outfit = " ".join(columns(card, "Т"))
    assert outfit.startswith("СИ"), "средства измерений записывают последними (п. 2.10)"
    for instrument in ("лупа", "штангенциркуль", "УШС-3"):
        assert instrument in outfit, f"в контроле нет средства измерений «{instrument}»"


# --- служебные символы и графы -------------------------------------------------


def test_rows_use_only_the_service_symbols_of_the_estd_form():
    allowed = {"А", "Б", "К", "М", "О", "Т", "Р", "РС1"}
    for card in doc.cards():
        used = {line.symbol for line in card.rows if line.symbol}
        assert used <= allowed, f"чужие служебные символы: {sorted(used - allowed)}"


def test_every_line_of_the_sheet_has_a_symbol_and_a_number(sheets):
    """Графа 1: служебный символ с порядковым номером строки; продолжение — с одним номером."""
    edge = sheets[0].frame_rect[0] + GRAPH1_W
    for number, (card, sheet) in enumerate(zip(doc.cards(), sheets), start=1):
        marks = [label.text for label in sheet.labels()
                 if label.x <= edge and re.fullmatch(r"[А-Я]+(?:/[А-Я]+)?\d{2}|\d{2}", label.text)]
        assert marks[0] == "А01", f"лист {number}: первая строка операции — не А01"
        assert len(marks) >= len(card.lines()), (
            f"лист {number}: пронумерованных строк меньше, чем строк операции"
        )
        numbers = [mark[-2:] for mark in marks]
        assert numbers == sorted(numbers), f"лист {number}: номера строк идут не по порядку"
        assert len(set(numbers)) == len(numbers), f"лист {number}: номера строк повторяются"


def test_rows_of_the_blocks_and_of_the_materials_carry_their_graphs():
    for number, card in enumerate(doc.cards(), start=1):
        equipment = row_cells(card, "Б")
        assert equipment, f"лист {number}: не заполнена строка Б — оборудование операции"
        for row in equipment:
            assert row[0].strip(), f"лист {number}: строка Б без наименования оборудования"
            assert all(row[1:6]), (
                f"лист {number}: в строке Б пусты графы СМ, Проф., Р, УТ или КР"
            )


def test_the_mass_of_the_product_is_counted_from_the_model():
    """МЗ — масса изделия по конструкторскому документу: 2 стойки и перемычка из 09Г2С."""
    volume_mm3 = (2 * 16 * 90 * 90) + 135 * 90 * 16
    assert doc.mass_kg() == pytest.approx(volume_mm3 * 1e-9 * doc.STEEL_DENSITY, rel=1e-9)
    assert doc.mass_text() == "3,56 кг"
    for card in doc.cards():
        assert row_cells(card, "А")[0][-1] == doc.mass_text()


# --- листы документа -----------------------------------------------------------


def test_every_sheet_carries_the_designation_of_the_document(sheets):
    for number, sheet in enumerate(sheets, start=1):
        assert doc.DESIGNATION in sheet.texts(), f"лист {number} без обозначения документа"
        assert doc.PRODUCT in sheet.texts() and doc.NAME in sheet.texts()


def test_first_sheet_has_the_executors_and_the_others_do_not(sheets):
    for executor in EXECUTOR_ROWS:
        assert executor in sheets[0].texts(), f"на первом листе нет строки «{executor}»"
        for later in sheets[1:]:
            assert executor not in later.texts(), (
                f"на последующих листах нет блока состава исполнителей, а «{executor}» есть"
            )


def test_nothing_is_drawn_outside_the_frame(sheets):
    for number, sheet in enumerate(sheets, start=1):
        x0, y0, x1, y1 = sheet.frame_rect
        bx0, by0, bx1, by1 = sheet.bounds()
        assert bx0 >= x0 - 0.01 and by0 >= y0 - 0.01, f"лист {number} вышел за рамку"
        assert bx1 <= x1 + 0.01 and by1 <= y1 + 0.01


# --- артефакт этапа ------------------------------------------------------------


def test_build_writes_svg_and_pdf_into_the_stage_folder(tmp_path):
    pymupdf = pytest.importorskip("pymupdf")
    written = doc.build(out_dir=tmp_path)
    stage = tmp_path / STAGE
    assert {path.parent for path in written} == {stage}
    svg = sorted(path for path in written if path.suffix == ".svg")
    pdf = [path for path in written if path.suffix == ".pdf"]
    assert len(svg) == len(doc.OPERATIONS), "на каждый лист — свой SVG"
    assert len(pdf) == 1, "весь документ — один PDF"
    assert all(path.stat().st_size > 1000 for path in written)

    document = pymupdf.open(pdf[0])
    assert document.page_count == len(doc.OPERATIONS)
    for page in document:
        assert page.rect.width * 25.4 / 72 == pytest.approx(297.0, abs=0.5)
        assert page.rect.height * 25.4 / 72 == pytest.approx(210.0, abs=0.5)


def test_pdf_pages_carry_the_same_records_as_the_sheets(tmp_path):
    """Листы согласованы: страница PDF несёт записи своего листа, и ничьи больше."""
    pymupdf = pytest.importorskip("pymupdf")
    pdf = [path for path in doc.build(out_dir=tmp_path) if path.suffix == ".pdf"][0]
    document = pymupdf.open(pdf)
    for index, (number, title) in enumerate(doc.OPERATIONS):
        text = document[index].get_text()
        assert title in text, f"страница {index + 1}: нет операции {number}"
        assert doc.DESIGNATION in text
        for other, other_title in doc.OPERATIONS[:index] + doc.OPERATIONS[index + 1:]:
            assert other_title not in text, (
                f"страница {index + 1} несёт ещё и операцию {other}"
            )


def test_the_document_repeats_itself(tmp_path):
    first = doc.build(out_dir=tmp_path / "a")
    second = doc.build(out_dir=tmp_path / "b")
    for a, b in zip(first, second):
        assert a.name == b.name
        assert a.read_bytes() == b.read_bytes(), f"{a.name} меняется от запуска к запуску"
