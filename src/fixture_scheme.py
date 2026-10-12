"""Принципиальная схема приспособления для Направляющей 3865.00.10 (SVG + PDF).

На листе — изделие с условными обозначениями мест установки и закрепления: плита,
неподвижные сферические опоры по черновым поверхностям, постоянные упоры по двум смежным
сторонам и откидные для съёма изделия, механические винтовые зажимы над опорами и вблизи
них. Размеры расположения опор и упоров — с допусками из расчёта размерных цепей
(`src/dimensional_chains.py`): числа берутся из него, а не переписываются на лист.

Обозначения — по ГОСТ 3.1107-81: опоры и упоры — табл. 1, поз. 1 (треугольник с углом 60°
при вершине, высота 5, основание 10 × 5), зажимы — табл. 2 (тот же треугольник, стержень и
плечо; у двойного зажима плечо l соединяет две точки приложения силы), формы рабочих
поверхностей — табл. 4, поз. 1 и 2, слева от обозначения (п. 11). Устройство зажима —
ручное, поэтому буква по табл. 5 (п. 15) не ставится: табл. 5, поз. 6 «прочее» —
без обозначения.

За один запуск выходят и SVG, и PDF с одного и того же листа:

    uv run python src/fixture_scheme.py
"""

from __future__ import annotations

from pathlib import Path

import dimensional_chains as calc
from guide import OVERALL_HEIGHT, OVERALL_WIDTH
from post import POST_HEIGHT

from ekd.dimensions import horizontal, vertical
from ekd.primitives import centre_line
from ekd.projection import View
from ekd.sheet import THICK, Sheet
from ekd.symbols import (
    BASE_HEIGHT,
    BASE_WIDTH,
    CLAMP_ARM,
    NECK,
    SURFACE_FLAT,
    SURFACE_SPHERICAL,
    clamp_side,
    support_side,
    support_top,
    surface_mark_left,
)

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parent
STEP = _REPO / "STEP" / "guide.step"

#: Артефакт этапа — в папке этапа внутри 3865.00.10_SB/.
OUT_DIR = _REPO / "3865.00.10_SB" / "03_Принципиальная_схема"
SVG_NAME = "Принципиальная_схема.svg"
PDF_NAME = "Принципиальная_схема.pdf"

DESIGNATION = "3865.00.10 СБ"
NAME = "Направляющая"
DOCUMENT = "Схема принципиальная"
SCALE = "1:1"
LETTER = "У"

# --- Размеры приспособления: только из расчёта размерных цепей ----------------
POST_X = calc.POST_X                    # 70 — ось Стойки, здесь же оси опор 1, 2 и 3
SUPPORT_Y = calc.SUPPORT_Y              # 38 — опоры 1 и 2 по ширине изделия
REAR_STOP_Y = calc.REAR_STOP_Y          # −45 — контактная плоскость заднего упора 4–5
END_STOP_X = calc.END_STOP_X            # +78 — торец правой Стойки, упор 6
INNER_STOP_X = calc.INNER_STOP_X        # 62 — внутренние плоскости Стоек, упоры 7 и 8
BAR_STOP_X = calc.BAR_STOP_X            # 67,5 — торцы Перемычки, упоры 9 и 10
CLAMP_Z = calc.CLAMP_Z                  # 45 — оси боковых зажимов З4 и З5
INNER_STOP_HEIGHT = calc.INNER_STOP_HEIGHT   # 30 — высота площадки внутренних упоров
POSITION_PLAN = calc.POSITION_PLAN      # ±0,1 — положение в плане
CLAMP_SPAN = 2 * POST_X                 # 140 — плечо зажима З6: две Стойки сразу
CLAMP_SPAN_SIDE = 2 * SUPPORT_Y         # 76 — плечо зажима З4: опоры 1 и 2

#: Размеры приспособления из расчёта: B1 — между внутренними упорами, B2 — от заднего упора
#: до зажимов З6, B3 — между упорами Перемычки, B4 — оси торцевых зажимов по высоте.
FIXTURE_DIMS = {row["обозначение"]: row["размер_приспособления"]
                for row in calc.fixture_dimensions()}

# --- Конструктивные размеры плиты ---------------------------------------------
#
# Плита на схеме нужна как основание: по ней видно, что опоры, упоры и зажимы стоят
# на одной плите. Её габарит — не результат расчёта размерных цепей, а конструктивный
# размер, поэтому на листе он справочный: от крайних элементов оставлен запас 15 мм.

PLATE_MARGIN = 15.0
PLATE_X = END_STOP_X + PLATE_MARGIN                      # ±93 — половина длины плиты
PLATE_Y = OVERALL_WIDTH / 2 + PLATE_MARGIN               # ±60 — половина ширины плиты
PLATE_THICK = 20.0
#: Верх плиты — установочная плоскость опор: знак опоры высотой 10 мм встаёт на неё.
PLATE_TOP_Z = -(NECK + BASE_HEIGHT)

# --- Компоновка листа A3 в масштабе 1:1, мм листа -----------------------------
VIEW_X = 128.0          # ось изделия по X — общая для главного вида и вида сверху
Z0_Y = 177.0            # где окажется z = 0 на главном виде (верх плиты)
PLAN_Y0 = 72.0          # где окажется y = 0 на виде сверху
NOTES_X = 245.0         # левый край примечаний
NOTES_TOP_Y = 280.0     # верх примечаний
NOTES_WIDTH = 165.0     # предельная ширина строки примечаний


def _plus_minus(value: float, tolerance: float) -> str:
    """«70» и 0,1 → «70 ±0,1»: координата с допуском в записи ЕСКД."""
    return f"{calc.num(value)} ±{calc.num(tolerance)}"


#: Примечания на листе (ГОСТ 2.316). Числа — из расчёта размерных цепей.
NOTES: tuple[str, ...] = (
    f"Основание — плита {calc.num(2 * PLATE_X)} × {calc.num(2 * PLATE_Y)} × "
    f"{calc.num(PLATE_THICK)} мм; размеры плиты справочные, выбраны конструктивно.",
    "Опоры 1–3 и упоры — неподвижные; знаки по ГОСТ 3.1107-81, табл. 1, поз. 1; "
    "форма рабочей поверхности — слева от знака: у опор сферическая (табл. 4, поз. 2), "
    "у упоров и зажимов плоская (табл. 4, поз. 1).",
    f"Опоры 1 и 2 — под левой Стойкой, опора 3 — под правой; координата Z каждой опоры "
    f"0 ±{calc.num(calc.POSITION_HEIGHT)} мм — это установочная плоскость, детали "
    f"прижимать к базам до прихватки.",
    f"Упоры 4 и 5 — задняя плоскость Стоек, упор 6 — торец правой Стойки: постоянные "
    f"упоры по двум смежным сторонам. Упор 6 регулируемый, ход "
    f"{calc.num(calc.REGULATED_TRAVEL)} мм.",
    f"Упоры 7 и 8 задают зазор {FIXTURE_DIMS['B1']} мм между Стойками, упоры 9 и 10 — "
    f"положение Перемычки по длине ({FIXTURE_DIMS['B3']} мм) и перекрытие "
    f"{calc.chain_crossbar().result.label()} мм.",
    "Упоры 8, 9, 10 и зажимы З1, З2, З3 — откидные: откидываются перед сваркой угловых "
    "швов и для съёма изделия.",
    "Зажимы З1…З6 — винтовые механические, ручные: буквенное обозначение устройства "
    "зажима не ставят (ГОСТ 3.1107-81, табл. 5, поз. 6, п. 15); на схеме З — зажим.",
    "Зажимы З1, З2 и З3 стоят над опорами 1, 2 и 3; точки приложения зажимов З4 и З5 "
    "лежат на осях опор 1, 2 и 3 (по ширине изделия) — опрокидывающего момента при "
    "зажатии не возникает.",
    "Порядок закрепления: к заднему упору 4–5 (зажим З6) → к установочной базе (зажимы "
    "З1, З2, З3) → к внутренним упорам 7 и 8 (зажимы З4 и З5); зажим З6 затягивают после "
    "укладки и прихватки Перемычки.",
    f"Размеры с допусками — из расчёта размерных цепей "
    f"({FIXTURE_DIMS['B1']}, {FIXTURE_DIMS['B2']}, {FIXTURE_DIMS['B3']}, "
    f"{FIXTURE_DIMS['B4']}; 3865.00.10_SB/Размерные_цепи): допуски приспособления жёстче "
    f"допусков изделия в {calc.num(calc.TIGHTENING_RATIO)} раза.",
)

def _notes(sheet: Sheet) -> None:
    """Примечания по ГОСТ 2.316 — раскладкой самого листа."""
    sheet.add_notes(NOTES, x=NOTES_X, top=NOTES_TOP_Y, width=NOTES_WIDTH)


def _plate(sheet: Sheet, front: View, top: View) -> None:
    """Плита основания: главный вид — толщина, вид сверху — контур."""
    front_points = [
        front.to_sheet(point) for point in (
            (-PLATE_X, 0.0, PLATE_TOP_Z), (PLATE_X, 0.0, PLATE_TOP_Z),
            (PLATE_X, 0.0, PLATE_TOP_Z - PLATE_THICK), (-PLATE_X, 0.0, PLATE_TOP_Z - PLATE_THICK),
        )
    ]
    sheet.add_polyline(front_points, width=THICK, closed=True)
    top_points = [
        top.to_sheet(point) for point in (
            (-PLATE_X, -PLATE_Y, 0.0), (PLATE_X, -PLATE_Y, 0.0),
            (PLATE_X, PLATE_Y, 0.0), (-PLATE_X, PLATE_Y, 0.0),
        )
    ]
    sheet.add_polyline(top_points, width=THICK, closed=True)


def _axes(sheet: Sheet, front: View, top: View) -> None:
    """Оси симметрии изделия: от них проставлены координаты опор и упоров."""
    # Главный вид — ось изделия по длине: от низа плиты до верха вида.
    low = front.to_sheet((0.0, 0.0, PLATE_TOP_Z - PLATE_THICK))
    high = front.to_sheet((0.0, 0.0, OVERALL_HEIGHT + 8.0))
    centre_line(sheet, *low, *high)
    # Вид сверху — оси по длине и по ширине изделия.
    back = top.to_sheet((0.0, -PLATE_Y - 4.0, 0.0))
    forward = top.to_sheet((0.0, PLATE_Y + 4.0, 0.0))
    centre_line(sheet, *back, *forward)
    left = top.to_sheet((-PLATE_X - 4.0, 0.0, 0.0))
    right = top.to_sheet((PLATE_X + 4.0, 0.0, 0.0))
    centre_line(sheet, *left, *right)


def _supports(sheet: Sheet, front: View, top: View) -> None:
    """Опоры 1–3: на главном виде — знак опоры со сферической поверхностью, сверху — ⌀6."""
    front_symbol = support_side(sheet, *front.to_sheet((-POST_X, -SUPPORT_Y, 0.0)),
                                label="1, 2")
    surface_mark_left(sheet, front_symbol, form=SURFACE_SPHERICAL)
    front_symbol = support_side(sheet, *front.to_sheet((POST_X, 0.0, 0.0)), label="3")
    surface_mark_left(sheet, front_symbol, form=SURFACE_SPHERICAL)

    for number, point in ((1, (-POST_X, -SUPPORT_Y, 0.0)), (2, (-POST_X, SUPPORT_Y, 0.0)),
                          (3, (POST_X, 0.0, 0.0))):
        symbol = support_top(sheet, *top.to_sheet(point), label=str(number))
        surface_mark_left(sheet, symbol, form=SURFACE_SPHERICAL)


def _stops(sheet: Sheet, front: View, top: View) -> None:
    """Упоры 4–10: постоянные по двум смежным сторонам и откидные для съёма изделия."""
    # Упоры 4 и 5 — задняя плоскость Стоек: вид сверху, знак отходит от изделия назад.
    for number in (4, 5):
        x = -POST_X if number == 4 else POST_X
        symbol = support_side(sheet, *top.to_sheet((x, REAR_STOP_Y, 0.0)), label=str(number))
        surface_mark_left(sheet, symbol, form=SURFACE_FLAT)

    # Упор 6 — торец правой Стойки: знак отходит от изделия вправо.
    symbol = support_side(sheet, *top.to_sheet((END_STOP_X, 0.0, 0.0)), angle=90.0, label="6")
    surface_mark_left(sheet, symbol, form=SURFACE_FLAT)

    # Упоры 7 и 8 — внутренние плоскости Стоек: знаки отходят в зазор между Стойками.
    contact_z = INNER_STOP_HEIGHT / 2.0
    symbol = support_side(sheet, *front.to_sheet((-INNER_STOP_X, 0.0, contact_z)),
                          angle=90.0, label="7")
    surface_mark_left(sheet, symbol, form=SURFACE_FLAT)
    symbol = support_side(sheet, *front.to_sheet((INNER_STOP_X, 0.0, contact_z)),
                          angle=-90.0, label="8")
    surface_mark_left(sheet, symbol, form=SURFACE_FLAT)

    # Упоры 9 и 10 — торцы Перемычки: откидные, стоят в зоне площадки шва. Знаки ставят
    # на контактной плоскости вне оси изделия: на оси они попадают на знак опоры 3.
    for label, x, angle, y in (("9", -BAR_STOP_X, -90.0, 25.0), ("10", BAR_STOP_X, 90.0, 25.0)):
        symbol = support_side(sheet, *top.to_sheet((x, y, 0.0)), angle=angle, label=label)
        surface_mark_left(sheet, symbol, form=SURFACE_FLAT)


def _clamps(sheet: Sheet, front: View, top: View) -> None:
    """Зажимы З1…З6: над опорами 1–3, по осям опор 1, 2 и 3 и к заднему упору."""
    # З1 и З2 — над опорами 1 и 2: на главном виде точки приложения совпадают.
    symbol = clamp_side(sheet, *front.to_sheet((-POST_X, -SUPPORT_Y, POST_HEIGHT)),
                        arm=-1.0, label="З1, З2")
    surface_mark_left(sheet, symbol, form=SURFACE_FLAT)
    # З3 — над опорой 3.
    symbol = clamp_side(sheet, *front.to_sheet((POST_X, 0.0, POST_HEIGHT)), label="З3")
    surface_mark_left(sheet, symbol, form=SURFACE_FLAT)
    # З4 — двойной, прижимает левую Стойку к внутреннему упору 7: вид сверху.
    symbol = clamp_side(sheet, *top.to_sheet((-END_STOP_X, 0.0, 0.0)), angle=90.0,
                        spacing=CLAMP_SPAN_SIDE, label="З4")
    surface_mark_left(sheet, symbol, form=SURFACE_FLAT)
    # З5 — одиночный, прижимает правую Стойку к внутреннему упору 8: главный вид.
    symbol = clamp_side(sheet, *front.to_sheet((END_STOP_X, 0.0, CLAMP_Z)), angle=-90.0,
                        label="З5")
    surface_mark_left(sheet, symbol, form=SURFACE_FLAT)
    # З6 — двойной с плечом 140, прижимает обе Стойки к заднему упору 4–5: вид сверху.
    symbol = clamp_side(sheet, *top.to_sheet((0.0, OVERALL_WIDTH / 2, 0.0)),
                        spacing=CLAMP_SPAN, label="З6")
    surface_mark_left(sheet, symbol, form=SURFACE_FLAT)


def _dimensions(sheet: Sheet, front: View, top: View) -> None:
    """Размеры расположения опор и упоров — с допусками из расчёта размерных цепей."""
    # 70 ±0,1 — от оси симметрии изделия до осей опор 1, 2 и 3 (в плите, под изделием).
    horizontal(sheet, front.to_sheet((0.0, 0.0, PLATE_TOP_Z)),
               front.to_sheet((-POST_X, 0.0, PLATE_TOP_Z)),
               at=Z0_Y - 22.0, label=_plus_minus(POST_X, POSITION_PLAN))
    # 124 +0,2 — между контактными плоскостями внутренних упоров 7 и 8.
    horizontal(sheet, front.to_sheet((-INNER_STOP_X, 0.0, INNER_STOP_HEIGHT)),
               front.to_sheet((INNER_STOP_X, 0.0, INNER_STOP_HEIGHT)),
               at=Z0_Y + 50.0, label=FIXTURE_DIMS["B1"])
    # 135 ±0,2 — между упорами Перемычки 9 и 10.
    horizontal(sheet, front.to_sheet((-BAR_STOP_X, 0.0, OVERALL_HEIGHT)),
               front.to_sheet((BAR_STOP_X, 0.0, OVERALL_HEIGHT)),
               at=Z0_Y + OVERALL_HEIGHT + 1.0, label=FIXTURE_DIMS["B3"])
    # 45 ±0,2 — высота осей торцевых зажимов З4 и З5 от установочной плоскости.
    vertical(sheet, front.to_sheet((PLATE_X, 0.0, 0.0)),
             front.to_sheet((END_STOP_X + CLAMP_ARM, 0.0, CLAMP_Z)),
             at=VIEW_X + PLATE_X + 11.0, label=FIXTURE_DIMS["B4"])
    # 38 ±0,1 — от оси симметрии по ширине до осей опор 1 и 2.
    vertical(sheet, top.to_sheet((-POST_X - BASE_WIDTH / 2, 0.0, 0.0)),
             top.to_sheet((-POST_X - BASE_WIDTH / 2, -SUPPORT_Y, 0.0)),
             at=VIEW_X - 45.0, label=_plus_minus(SUPPORT_Y, POSITION_PLAN))
    # 90 −0,2 — от заднего упора 4–5 до осей прижимов З6.
    vertical(sheet, top.to_sheet((-END_STOP_X, REAR_STOP_Y, 0.0)),
             top.to_sheet((-POST_X, OVERALL_WIDTH / 2, 0.0)),
             at=VIEW_X - PLATE_X - 3.0, label=FIXTURE_DIMS["B2"])


def _notes(sheet: Sheet) -> None:
    """Примечания по ГОСТ 2.316 — раскладкой самого листа: нумерация и перенос строк."""
    sheet.add_notes(NOTES, x=NOTES_X, top=NOTES_TOP_Y, width=NOTES_WIDTH)


def build_sheet() -> Sheet:
    """Собрать лист «Принципиальная схема приспособления»."""
    import cadgen

    part = cadgen.read_step(STEP)

    sheet = Sheet("A3", scale=1.0)
    sheet.add_frame()
    sheet.add_extra_graphs()
    sheet.add_title_block(
        designation=DESIGNATION,
        name=NAME,
        document=DOCUMENT,
        scale=SCALE,
        letter=LETTER,
    )

    # Главный вид (вид спереди) и вид сверху — в проекционной связи по X.
    front = View(sheet, part, "front", at=(VIEW_X, Z0_Y + OVERALL_HEIGHT / 2))
    top = View(sheet, part, "top", at=(VIEW_X, PLAN_Y0))

    _plate(sheet, front, top)
    _axes(sheet, front, top)
    _supports(sheet, front, top)
    _stops(sheet, front, top)
    _clamps(sheet, front, top)
    _dimensions(sheet, front, top)
    _notes(sheet)
    return sheet


def build(out_dir: Path | str | None = None) -> tuple[Path, Path]:
    """Собрать этап: один запуск — и SVG, и PDF в папке этапа."""
    stage = OUT_DIR if out_dir is None else Path(out_dir) / OUT_DIR.relative_to(_REPO)
    sheet = build_sheet()
    svg, pdf = sheet.save(svg=stage / SVG_NAME, pdf=stage / PDF_NAME)
    return Path(svg), Path(pdf)


if __name__ == "__main__":
    for path in build():
        print(f"{path} — {path.stat().st_size} байт")
