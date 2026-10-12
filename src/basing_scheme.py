"""Схема базирования направляющей 3865.00.10 — схема УНО (SVG + PDF).

Изделие лишается шести степеней свободы: установочная база — нижние кромки стоек
(три опорные точки), направляющая — задние плоскости стоек (две), опорная — торец
(одна). Точки нумеруют, начиная с базы, имеющей наибольшее количество опорных точек,
а совпадающие в проекции точки показывают одним знаком с номерами обеих
(Хайдарова А. А. Сборочно-сварочные приспособления. Этапы проектирования, п. 2.1–2.2;
базирование и базы — по ГОСТ 21495-76).

За один запуск выходят и SVG, и PDF с одного и того же листа:

    uv run python src/basing_scheme.py
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from crossbar import BAR_LEN, BAR_THICK, BAR_WIDTH
from guide import OVERALL_HEIGHT, OVERALL_LEN, OVERALL_WIDTH
from post import POST_HEIGHT, POST_THICK, POST_WIDTH

from ekd.projection import View
from ekd.sheet import TEXT_5, Sheet, dot
from ekd.symbols import support_side, support_top

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parent
STEP = _REPO / "STEP" / "guide.step"

#: Артефакт этапа — в папке этапа внутри 3865.00.10_SB/.
OUT_DIR = _REPO / "3865.00.10_SB" / "01_Схема_базирования"
SVG_NAME = "Схема_базирования.svg"
PDF_NAME = "Схема_базирования.pdf"

DESIGNATION = "3865.00.10 СБ"
SCHEME = "УНО"

#: Ось стойки: стойки стоят на ребре, каждая отстоит на 70 мм от середины изделия.
X_POST = OVERALL_LEN / 2 - POST_THICK / 2


@dataclass(frozen=True)
class Base:
    """База: состав опорных точек, поверхности и сколько степеней свободы она отнимает."""

    name: str
    letter: str
    points: tuple[int, ...]
    dof: int
    surfaces: str


#: Опорные точки (X, Y, Z), мм; начало координат — центр изделия по X и Y, низ по Z.
#: Эти же координаты читает расчёт размерных цепей (tests/test_dimensional_chains.py),
#: поэтому таблица остаётся плоскими кортежами: одно место координат на оба этапа.
POINTS: dict[int, tuple[float, float, float]] = {
    # 1–3 — установочная база: нижние кромки стоек (две отдельные площадки 16 × 90),
    # разложены 2 + 1, чтобы центр тяжести изделия был внутри треугольника опор.
    1: (-X_POST, -38.0, 0.0),
    2: (-X_POST, 38.0, 0.0),
    3: (X_POST, 0.0, 0.0),
    # 4–5 — направляющая база: задние плоскости стоек, разнесены по длине изделия.
    4: (-X_POST, -OVERALL_WIDTH / 2, POST_HEIGHT / 2),
    5: (X_POST, -OVERALL_WIDTH / 2, POST_HEIGHT / 2),
    # 6 — опорная база: торец правой стойки.
    6: (OVERALL_LEN / 2, 0.0, POST_HEIGHT / 2),
}

BASES: tuple[Base, ...] = (
    Base("установочная", "У", (1, 2, 3), 3, "нижние кромки стоек"),
    Base("направляющая", "Н", (4, 5), 2, "задние плоскости стоек"),
    Base("опорная", "О", (6,), 1, "торец"),
)

#: Точки, которые на главном виде приходятся одна на другую: показываются одним знаком.
COINCIDENT_FRONT: dict[int, tuple[int, ...]] = {1: (1, 2)}

#: (точка, угол знака) на главном виде: 0° — знак под изделием, 90° — справа от изделия.
FRONT_SYMBOLS: tuple[tuple[int, float], ...] = ((1, 0.0), (3, 0.0), (6, 90.0))

#: То же на виде сверху: ось этих опор лежит в плоскости вида.
TOP_SYMBOLS: tuple[tuple[int, float], ...] = ((4, 0.0), (5, 0.0))

#: Точки установочной базы на виде сверху — окружности ⌀6 с точкой (ГОСТ 3.1107-81, табл. 1).
TOP_CIRCLES: tuple[int, ...] = (1, 2, 3)

#: Нумерация баз на листе и слова для числа отнимаемых ими степеней свободы.
_ROMAN = ("I", "II", "III", "IV")
_DOF_PHRASE = {1: "одну степень", 2: "две степени", 3: "три степени"}


def _point_label(number: int) -> str:
    """Номер точки на листе: у совпадающих точек — номера обеих («1,2»)."""
    return ",".join(str(n) for n in COINCIDENT_FRONT.get(number, (number,)))


def _base_note(index: int, base: Base) -> str:
    points = (f"точка {base.points[0]}" if len(base.points) == 1
              else "точки " + ", ".join(str(number) for number in base.points))
    return (f"База {_ROMAN[index]} — {base.name} ({base.letter}): {base.surfaces}, {points}; "
            f"отнимает {_DOF_PHRASE[base.dof]} свободы.")


#: Примечания на листе (ГОСТ 2.316). Состав баз берётся из BASES, а не переписывается.
NOTES: tuple[str, ...] = (
    "Опоры — неподвижные; знаки по ГОСТ 3.1107-81, табл. 1.",
    *(_base_note(index, base) for index, base in enumerate(BASES)),
    f"Схема базирования — {SCHEME} (ГОСТ 21495-76); изделие лишено шести степеней свободы.",
    "Точки 1 и 2 на главном виде совпадают — показаны одним обозначением.",
)

# Компоновка листа A3 в масштабе 1:1, мм листа.
VIEW_X = 130.0          # ось изделия по X
FRONT_Z0_Y = 160.0      # где окажется z = 0 на главном виде
TOP_TOP_Y = 132.0       # где окажется y = +45 (верхняя кромка вида сверху)
NOTES_X = 245.0         # левый край примечаний
NOTES_TOP_Y = 152.0     # верх примечаний
NOTES_WIDTH = 165.0     # предельная ширина строки примечаний
LABEL_X = 40.0          # где стоят номера баз I и II


def centre_of_mass() -> tuple[float, float, float]:
    """Центр тяжести изделия (мм): две стойки и перемычка как однородные тела."""
    post_volume = POST_THICK * POST_WIDTH * POST_HEIGHT
    solids = (
        (post_volume, (-X_POST, 0.0, POST_HEIGHT / 2)),
        (post_volume, (X_POST, 0.0, POST_HEIGHT / 2)),
        (BAR_LEN * BAR_WIDTH * BAR_THICK, (0.0, 0.0, POST_HEIGHT + BAR_THICK / 2)),
    )
    total = sum(volume for volume, _ in solids)
    return tuple(  # type: ignore[return-value]
        sum(volume * centre[axis] for volume, centre in solids) / total for axis in range(3)
    )


def _leader(sheet: Sheet, start: tuple[float, float], shelf: tuple[float, float], text: str, *,
            anchor: str, mark: bool = True) -> None:
    """Номер базы на линии-выноске: точка на поверхности, полка и номер.

    ``mark`` ставит залитую точку на поверхности базы; там, где рядом уже стоит знак
    опоры (опорная база), точка не нужна.
    """
    sheet.add_line(*start, *shelf)
    if mark:
        sheet.add(dot(*start))
    sheet.add_text(*shelf, text, height=TEXT_5, anchor=anchor, valign="center")


def _leaders(sheet: Sheet, front: View, top: View) -> None:
    """Базы I, II, III на листе: выноска на поверхность базы и её номер."""
    # I — установочная база: нижняя кромка левой стойки на главном виде.
    start = front.to_sheet((-OVERALL_LEN / 2, 0.0, 0.0))
    _leader(sheet, start, (LABEL_X + 2.0, start[1] - 10.0), "I", anchor="end")

    # II — направляющая база: задняя плоскость стоек на виде сверху (нижняя кромка вида).
    start = top.to_sheet((-OVERALL_LEN / 2, -OVERALL_WIDTH / 2, 0.0))
    _leader(sheet, start, (LABEL_X + 2.0, start[1] - 10.0), "II", anchor="end")

    # III — опорная база: торец правой стойки, та же точка, что у знака «6».
    start = front.to_sheet(POINTS[6])
    _leader(sheet, start, (start[0] + 14.0, start[1] - 13.0), "III", anchor="start", mark=False)


def build_sheet() -> Sheet:
    """Собрать лист «Схема базирования направляющей»."""
    import cadgen

    part = cadgen.read_step(STEP)

    sheet = Sheet("A3", scale=1.0)
    sheet.add_frame()
    sheet.add_extra_graphs()
    sheet.add_title_block(
        designation=DESIGNATION,
        name="Направляющая",
        document="Схема базирования",
        scale="1:1",
        letter="У",
    )

    # Главный вид (вид спереди) и вид сверху — в проекционной связи по X.
    front = View(sheet, part, "front", at=(VIEW_X, FRONT_Z0_Y + OVERALL_HEIGHT / 2))
    top = View(sheet, part, "top", at=(VIEW_X, TOP_TOP_Y - OVERALL_WIDTH / 2))

    # Базы I, II, III.
    _leaders(sheet, front, top)

    # Опоры: знак не зависит от масштаба — размеры по ГОСТ 3.1107-81.
    for number, angle in FRONT_SYMBOLS:
        support_side(sheet, *front.to_sheet(POINTS[number]), angle=angle, label=_point_label(number))
    for number, angle in TOP_SYMBOLS:
        support_side(sheet, *top.to_sheet(POINTS[number]), angle=angle, label=_point_label(number))
    for number in TOP_CIRCLES:
        support_top(sheet, *top.to_sheet(POINTS[number]), label=str(number))

    # Примечания.
    sheet.add_notes(NOTES, x=NOTES_X, top=NOTES_TOP_Y, width=NOTES_WIDTH, gap=2.0)
    return sheet


def build(out_dir: Path | str | None = None) -> tuple[Path, Path]:
    """Собрать этап: один запуск — и SVG, и PDF в папке этапа.

    ``out_dir`` подменяет корень репозитория (тесты собирают этап в свой каталог).
    """
    stage = OUT_DIR if out_dir is None else Path(out_dir) / OUT_DIR.relative_to(_REPO)
    sheet = build_sheet()
    svg, pdf = sheet.save(svg=stage / SVG_NAME, pdf=stage / PDF_NAME)
    return Path(svg), Path(pdf)


if __name__ == "__main__":
    for path in build():
        print(f"{path} — {path.stat().st_size} байт")
