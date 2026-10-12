"""Бланк операционной карты по формам ЕСТД: графы, служебные символы, формы листов.

Проверяется то, что видно на бланке: графы каждой строки занимают лист целиком, служебные
символы стоят с номерами строк, запись переносится на последующие строки, обозначение
документа есть на каждом листе, и листы документа совпадают в SVG и PDF.
"""

from pathlib import Path

import pytest

from ekd import estd
from ekd.sheet import MARGIN, MARGIN_LEFT, SHEET_SIZES
# Помощники сравнения SVG и PDF — из теста листа ЕСКД: лист собирается одним и тем же
# разложением примитивов, поэтому и проверять совпадение форматов нужно одним способом.
from test_ekd_sheet import _pdf_ink_bbox, _svg_ink_bbox

#: Ширина граф строки: лист A4 минус поля и графа 1.
CONTENT_W = SHEET_SIZES["A4"][0] - MARGIN_LEFT - MARGIN - estd.GRAPH1_W


def card(**kwargs) -> estd.OperationalCard:
    fields = dict(designation="ФЮРА.60190.00001", product="3865.00.10 СБ",
                  name="Направляющая", organisation="ФЮРА (ТПУ)", letter="У", sheet_count=2)
    fields.update(kwargs)
    return estd.OperationalCard(**fields)


# --- графы строк ---------------------------------------------------------------


def test_every_row_kind_fills_the_sheet():
    """Графы любой строки должны занимать ширину листа целиком — иначе бланк поедет."""
    for kind in (*estd.GRAPHS, "Р"):
        graphs = estd.graphs_for(kind)
        assert sum(graph.width for graph in graphs) == pytest.approx(CONTENT_W), (
            f"графы строки {kind!r} не занимают лист: {sum(g.width for g in graphs)} мм"
        )


def test_regime_block_keeps_only_the_graphs_of_manual_arc_welding():
    """В блоке РС1 — графы принятого способа; графы механизированных способов не входят."""
    assert estd.REGIME_HEADER == ("ПС", "НП", "Пл", "U", "I")
    for other in ("DC", "lc", "lэ", "Vc", "qоз", "qдз"):
        assert other not in estd.REGIME_HEADER


def test_unknown_symbol_is_refused():
    with pytest.raises(ValueError, match="служебный символ"):
        estd.graphs_for("Щ")


def test_alias_symbols_take_the_graphs_of_their_row_kind():
    assert estd.graphs_for("К") == estd.graphs_for("К/М")
    assert estd.graphs_for("М") == estd.graphs_for("К/М")
    assert estd.graphs_for("Р") == estd.graphs_for("РС1")


# --- строки операции -----------------------------------------------------------


def test_line_1_keeps_the_symbol_with_the_row_number():
    c = card()
    c.add("А", "1", "1", "1", "05", "88, Сборка", "ГОСТ 5264-80", "3,56 кг")
    c.blank()
    c.add("О", "Установить заготовки.")
    assert [line.mark(f"{n:02d}") for n, line in enumerate(c.lines(), start=1)] == [
        "А01", "02", "О03",
    ], "символ ставится только на строке, где запись начинается; свободная строка — с номером"


def test_regime_block_header_is_not_numbered():
    """Строка с обозначением блока режимов идёт без номера (ГОСТ 3.1407-86, прил. 1, п. 3)."""
    c = card()
    c.add("РС1", *estd.REGIME_HEADER)
    c.add("Р", "В", "1", "О", "24–26 В", "90–100 А")
    lines = c.lines()
    assert lines[0].symbol == "РС1" and lines[0].header
    assert not lines[1].header and lines[1].symbol == "Р"


def test_long_record_wraps_to_the_following_rows():
    c = card()
    c.add("О", "Сварить " + "четыре угловых шва У5 по ГОСТ 5264-80 " * 4)
    lines = c.lines()
    assert len(lines) > 1, "длинная запись должна переноситься на последующие строки"
    assert lines[0].symbol == "О" and all(not line.symbol for line in lines[1:])


def test_record_that_does_not_fit_its_graph_is_refused():
    """Запись, которая не помещается в свою графу, — ошибка автора, а не повод печатать её."""
    c = card()
    c.add("А", "1", "1", "1", "05", "Сборка", "Слишком длинное обозначение документа, "
                                              "которое не влезет в графу никак", "3,56 кг")
    with pytest.raises(ValueError, match="не помещается в графу"):
        c.lines()


def test_too_many_rows_for_one_sheet_are_refused():
    c = card()
    for _ in range(40):
        c.add("О", "Переход.")
    with pytest.raises(ValueError, match="помещается"):
        c.sheet()


def test_unknown_executor_sheet_number_is_refused():
    with pytest.raises(ValueError, match="номер листа"):
        card(sheet_number=3, sheet_count=2)


# --- лист ----------------------------------------------------------------------


def test_form_of_the_first_sheet_has_executors_and_later_ones_do_not():
    first = card().band()
    later = card(first=False, sheet_number=2).band()
    assert len(first) == len(later) + 4, "на последующих листах нет блока состава исполнителей"
    flat_first = [cell.text for row in first for cell in row]
    for executor in estd.EXECUTOR_ROWS:
        assert executor in flat_first
    flat_later = [cell.text for row in later for cell in row]
    for executor in estd.EXECUTOR_ROWS:
        assert executor not in flat_later


def test_every_sheet_carries_the_designation_and_the_form_number():
    for first, number, form in ((True, 1, "Форма 1"), (False, 2, "Форма 1а")):
        row = " ".join(cell.text for cells in card(first=first, sheet_number=number).band()
                       for cell in cells)
        assert "ФЮРА.60190.00001" in row, "обозначение документа есть на каждом листе"
        assert form in row, f"на листе не указана форма документа ({form})"


def test_every_sheet_carries_the_product_and_its_letter():
    """Адресный блок есть на каждом листе: изделие, его обозначение и литера — везде."""
    for first in (True, False):
        row = " ".join(cell.text for cells in card(first=first).band() for cell in cells)
        for value in ("3865.00.10 СБ", "Направляющая", "ФЮРА (ТПУ)", "У"):
            assert value in row, f"на листе нет адресной графы «{value}»"


def test_nothing_is_drawn_outside_the_frame():
    c = card()
    c.add("А", "1", "1", "1", "05", "Сборка", "ГОСТ 5264-80", "3,56 кг")
    c.add("О", "Установить заготовки в приспособление.")
    c.add("РС1", *estd.REGIME_HEADER)
    c.add("Р", "В", "1", "О", "24–26 В", "90–100 А")
    sheet = c.sheet()
    x0, y0, x1, y1 = sheet.frame_rect
    bx0, by0, bx1, by1 = sheet.bounds()
    assert bx0 >= x0 - 0.01 and by0 >= y0 - 0.01
    assert bx1 <= x1 + 0.01 and by1 <= y1 + 0.01


def test_sheet_shows_the_columns_and_the_document_row():
    c = card()
    c.add("А", "1", "1", "1", "05", "Сборка", "ГОСТ 5264-80", "3,56 кг")
    c.add("РС1", *estd.REGIME_HEADER)
    text = " ".join(c.sheet().texts())
    for name in ("Цех", "Уч.", "РМ", "Опер.", "Код, наименование операции",
                 "Обозначение документа", "Код, наименование оборудования", "СМ", "Проф.",
                 "Наименование детали, сб. единицы или материала", "Обозначение, код",
                 "Н.расх."):
        assert name in text, f"на бланке нет графы «{name}»"
    for letter in estd.REGIME_HEADER:
        assert letter in text, f"на бланке нет графы блока режимов «{letter}»"
    assert "ОК" in c.sheet().texts() and "Операционная карта" in c.sheet().texts()


# --- один документ, два формата ------------------------------------------------


def _two_sheets() -> list:
    cards = [card(sheet_number=1), card(first=False, sheet_number=2)]
    for c, number in zip(cards, ("05", "10")):
        c.add("А", "1", "1", "1", number, "Сборка", "ГОСТ 5264-80", "3,56 кг")
        c.add("О", f"Операция {number}.")
    return [c.sheet() for c in cards]


def test_one_pdf_for_the_whole_document_and_an_svg_per_sheet(tmp_path):
    from ekd.sheet import save_document

    pymupdf = pytest.importorskip("pymupdf")
    svg = [tmp_path / "лист_1.svg", tmp_path / "лист_2.svg"]
    written = save_document(_two_sheets(), svg=svg, pdf=tmp_path / "карта.pdf")
    assert set(written) == {*svg, tmp_path / "карта.pdf"}
    document = pymupdf.open(tmp_path / "карта.pdf")
    assert document.page_count == 2, "лист документа — страница PDF"
    for page in document:
        assert page.rect.width * 25.4 / 72 == pytest.approx(297.0, abs=0.5)
        assert page.rect.height * 25.4 / 72 == pytest.approx(210.0, abs=0.5)


def test_pdf_page_and_svg_show_the_same_sheet(tmp_path):
    """Страница PDF и SVG того же листа — один лист: сверяются и текст, и чернила."""
    from ekd.sheet import save_document

    pymupdf = pytest.importorskip("pymupdf")
    sheets = _two_sheets()
    svg = [tmp_path / "лист_1.svg", tmp_path / "лист_2.svg"]
    save_document(sheets, svg=svg, pdf=tmp_path / "карта.pdf")
    document = pymupdf.open(tmp_path / "карта.pdf")
    for index, (sheet, path) in enumerate(zip(sheets, svg)):
        alone = tmp_path / f"лист_{index + 1}.pdf"
        save_document([sheet], pdf=alone)
        page = document[index]
        single = pymupdf.open(alone)[0]
        assert page.get_text() == single.get_text(), f"страница {index + 1} — не тот лист"
        assert _svg_ink_bbox(path) == pytest.approx(_pdf_ink_bbox(alone), abs=1.0), (
            f"лист {index + 1} в SVG и PDF не совпадает"
        )


def test_the_document_repeats_bit_for_bit(tmp_path):
    from ekd.sheet import save_document

    def once(folder: Path):
        folder.mkdir(parents=True, exist_ok=True)
        return save_document(_two_sheets(), svg=[folder / "л1.svg", folder / "л2.svg"],
                             pdf=folder / "карта.pdf")

    first = once(tmp_path / "a")
    second = once(tmp_path / "b")
    for a, b in zip(first, second):
        assert a.read_bytes() == b.read_bytes(), f"{a.name} меняется от запуска к запуску"


def test_mismatched_number_of_svg_paths_is_refused(tmp_path):
    from ekd.sheet import save_document

    with pytest.raises(ValueError, match="путей SVG"):
        save_document(_two_sheets(), svg=[tmp_path / "один.svg"], pdf=None)
