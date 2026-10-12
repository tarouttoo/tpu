"""Проверки расчёта размерных цепей (src/dimensional_chains.py).

Запуск: `python -m unittest discover -s tests -v`

Проверяется не устройство скрипта, а результат расчёта: сходимость цепей,
правило жёсткости 2…3, справочность габаритов 156 и 106, геометрия координат
(опоры под Стойками, центр тяжести внутри треугольника опор, зазор 124 между
внутренними упорами) и воспроизводимость документа этапа.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

spec = importlib.util.spec_from_file_location("dimensional_chains", SRC / "dimensional_chains.py")
dc = importlib.util.module_from_spec(spec)
sys.modules["dimensional_chains"] = dc
spec.loader.exec_module(dc)


def evaluate_constants(path: Path, names: dict | None = None) -> dict[str, float]:
    """Числовые константы модуля без его импорта (импорт тянет cadgen).

    Вычисляются только выражения из констант и имён: `16.0`, `BAR_LEN + 2 * PROTRUDE`.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    env: dict = dict(names or {})
    for node in tree.body:
        if isinstance(node, ast.Assign):
            target = node.targets[0]
            value_node = node.value
        elif isinstance(node, ast.AnnAssign):
            target = node.target
            value_node = node.value
        else:
            continue
        if not isinstance(target, ast.Name) or value_node is None:
            continue
        try:
            value = eval(compile(ast.Expression(value_node), "<const>", "eval"),
                         {"__builtins__": {}}, env)
        except Exception:
            continue
        if isinstance(value, (int, float)):
            env[target.id] = float(value)
        else:
            env[target.id] = value
    return env


class TestSourceData(unittest.TestCase):
    """Исходные размеры — те же, что в CAD-моделях и на чертеже."""

    def test_part_nominals_match_cad_scripts(self):
        post = evaluate_constants(SRC / "post.py")
        bar = evaluate_constants(SRC / "crossbar.py")
        guide = evaluate_constants(SRC / "guide.py", {**post, **bar})

        self.assertEqual(post["POST_THICK"], dc.POST_THICK)
        self.assertEqual(post["POST_WIDTH"], dc.POST_WIDTH)
        self.assertEqual(post["POST_HEIGHT"], dc.POST_HEIGHT)
        self.assertEqual(bar["BAR_LEN"], dc.BAR_LEN)
        self.assertEqual(bar["BAR_WIDTH"], dc.BAR_WIDTH)
        self.assertEqual(bar["BAR_THICK"], dc.BAR_THICK)
        self.assertEqual(guide["PROTRUDE"], dc.PROTRUDE)
        self.assertEqual(guide["OVERALL_LEN"], dc.OVERALL_LEN)
        self.assertEqual(guide["OVERALL_WIDTH"], dc.OVERALL_WIDTH)
        self.assertEqual(guide["OVERALL_HEIGHT"], dc.OVERALL_HEIGHT)

    def test_geometry_closes(self):
        # 156 = 135 + 2 × 10,5; 124 = 156 − 2 × 16; 106 = 90 + 16
        self.assertEqual(dc.OVERALL_LEN, dc.BAR_LEN + 2 * dc.PROTRUDE)
        self.assertEqual(dc.POST_CLEARANCE, dc.OVERALL_LEN - 2 * dc.POST_THICK)
        self.assertEqual(dc.OVERALL_HEIGHT, dc.POST_HEIGHT + dc.BAR_THICK)

    def test_tolerances_come_from_the_agreed_list(self):
        self.assertEqual((dc.CLEARANCE.es, dc.CLEARANCE.ei), (+0.5, 0.0))
        self.assertEqual((dc.WIDTH.es, dc.WIDTH.ei), (0.0, -0.5))
        self.assertEqual((dc.HEIGHT.es, dc.HEIGHT.ei), (+0.5, -0.5))
        self.assertEqual((dc.THICKNESS.es, dc.THICKNESS.ei), (+0.2, -0.8))


class TestChains(unittest.TestCase):
    def test_reference_dims_carry_no_tolerance(self):
        for link in (dc.REFERENCE_LEN, dc.REFERENCE_HEIGHT):
            self.assertTrue(link.reference)
            self.assertEqual(link.tolerance, 0.0)
        # ...и ни один базовый размер приспособления по ним не считается
        for row in dc.fixture_dimensions():
            self.assertNotIn(row["размер_изделия"], (dc.REFERENCE_LEN.label(),
                                                     dc.REFERENCE_HEIGHT.label()))

    def test_chain_a_derives_the_overall_length(self):
        chain = dc.chain_length()
        self.assertEqual(chain.result.nominal, 156.0)
        self.assertEqual(chain.result.label(), "156 +0,9/−1,6")
        self.assertEqual(chain.result.tolerance,
                         dc.max_min_field([link.tolerance for link in chain.links]))

    def test_chain_b_derives_the_overall_height(self):
        chain = dc.chain_height()
        self.assertEqual(chain.result.nominal, 106.0)
        self.assertEqual(chain.result.label(), "106 +0,7/−1,3")

    def test_reference_dims_are_the_closing_links(self):
        self.assertTrue(dc.chain_length().closing.reference)
        self.assertTrue(dc.chain_height().closing.reference)

    def test_clearance_is_named_as_the_compensating_link(self):
        text = dc.chain_length().note
        self.assertIn("Компенсирующее звено", text)
        self.assertIn("зазор между Стойками", text)

    def test_fixture_chain_is_built_as_m3_plus_two_basing_errors(self):
        chain = dc.chain_fixture_length()
        self.assertEqual(len(chain.links), 3)
        self.assertEqual(chain.links[0].code, "M3")
        self.assertEqual(chain.links[0].nominal, dc.POST_CLEARANCE)
        self.assertEqual(chain.links[1].title, dc.BASING.title)
        self.assertEqual(chain.links[1].title, chain.links[2].title)

    def test_clearance_chain_needs_the_probabilistic_method(self):
        chain = dc.chain_fixture_length()
        tolerances = [link.tolerance for link in chain.links]
        self.assertGreater(dc.max_min_field(tolerances), chain.closing.tolerance)
        self.assertLessEqual(dc.probabilistic_field(tolerances), chain.closing.tolerance)

    def test_width_chain_passes_both_methods(self):
        chain = dc.chain_fixture_width()
        tolerances = [link.tolerance for link in chain.links]
        self.assertLessEqual(dc.max_min_field(tolerances), chain.closing.tolerance)
        self.assertLessEqual(dc.probabilistic_field(tolerances), chain.closing.tolerance)

    def test_checks_report_both_methods(self):
        checks = {check["цепь"]: check for check in dc.checks()}
        self.assertEqual(checks["M"]["итог_вероятностный"], "проходит")
        self.assertEqual(checks["M"]["итог_максимум_минимум"], "не проходит")
        self.assertEqual(checks["M′"]["итог_максимум_минимум"], "проходит")

    def test_without_clamping_to_the_bases_the_chain_does_not_close(self):
        check = dc.checks()[-1]
        self.assertIn("без прижима", check["цепь"])
        self.assertEqual(check["итог_максимум_минимум"], "не проходит")
        self.assertEqual(check["итог_вероятностный"], "не проходит")

    def test_chain_result_is_the_max_min_sum_of_its_links(self):
        """Замыкающее звено проектной цепи — сумма составляющих, а не копия исходного."""
        for chain in (dc.chain_length(), dc.chain_height(), dc.chain_fixture_width()):
            tolerances = [link.tolerance for link in chain.links]
            self.assertEqual(chain.result.tolerance, dc.max_min_field(tolerances),
                             chain.code)


class TestFixtureTolerance(unittest.TestCase):
    def test_every_fixture_dim_is_2_to_3_times_tighter(self):
        for row in dc.fixture_dimensions():
            self.assertGreaterEqual(row["во_сколько_раз_жёстче"], 2.0, row["обозначение"])
            self.assertLessEqual(row["во_сколько_раз_жёстче"], 3.0, row["обозначение"])

    def test_base_dimensions(self):
        rows = {row["обозначение"]: row for row in dc.fixture_dimensions()}
        self.assertEqual(rows["B1"]["размер_приспособления"], "124 +0,2")
        self.assertEqual(rows["B2"]["размер_приспособления"], "90 −0,2")
        self.assertEqual(rows["B3"]["размер_приспособления"], "135 ±0,2")
        self.assertEqual(rows["B4"]["размер_приспособления"], "45 ±0,2")

    def test_clamp_travel_covers_part_tolerance_and_basing(self):
        self.assertGreaterEqual(dc.CLAMP_TRAVEL, dc.WIDTH.tolerance + dc.BASING.es)


class TestCoordinates(unittest.TestCase):
    def setUp(self):
        self.elements = {str(element["номер"]): element for element in dc.elements()}
        self.cad_names = {**evaluate_constants(SRC / "post.py"),
                          **evaluate_constants(SRC / "crossbar.py")}
        self.cad_names.update(evaluate_constants(SRC / "guide.py", self.cad_names))

    def plane(self, number: str, key: str) -> float:
        return self.elements[number]["координаты"][key]["номинал"]

    def test_supports_lie_under_the_posts(self):
        # торцы Стоек: X ∈ [−78, −62] и [62, 78], Y ∈ [−45, 45]
        for number, expected_x in (("1", -70.0), ("2", -70.0), ("3", 70.0)):
            x = self.plane(number, "X")
            self.assertTrue(-78.0 <= x <= -62.0 or 62.0 <= x <= 78.0, number)
            self.assertAlmostEqual(x, expected_x, places=6)
            self.assertTrue(-45.0 <= self.plane(number, "Y") <= 45.0, number)
            self.assertEqual(self.plane(number, "Z"), 0.0)

    def test_supports_match_the_basing_scheme_points(self):
        """Координаты — те же, что на схеме базирования (этап 1): один источник.

        Проверка включается, когда в дереве есть src/basing_scheme.py: до этого
        этап 1 ещё не сдан, и сверять не с чем.
        """
        scheme_path = SRC / "basing_scheme.py"
        if not scheme_path.exists():
            self.skipTest("src/basing_scheme.py ещё нет (этап 1 не сдан)")
        points = evaluate_constants(scheme_path, self.cad_names)["POINTS"]
        for number in ("1", "2", "3"):
            self.assertEqual((self.plane(number, "X"), self.plane(number, "Y"), 0.0),
                             tuple(points[int(number)]), number)
        # задний упор: точки 4 и 5 лежат на его контактной плоскости
        rear = self.elements["4, 5"]["координаты"]
        for point in (4, 5):
            self.assertEqual(points[point][1], rear["контактная_плоскость"]["номинал"])
            self.assertLessEqual(points[point][2], rear["высота_планки"])
        # опорный упор: точка 6 — торец правой Стойки
        stop = self.elements["6"]["координаты"]
        self.assertEqual(points[6][0], stop["контактная_плоскость"]["номинал"])
        self.assertLessEqual(points[6][2], stop["высота_упорной_площадки"])

    def test_supports_are_coplanar_within_the_assigned_tolerance(self):
        heights = [self.elements[n]["координаты"]["Z"] for n in ("1", "2", "3")]
        self.assertEqual({height["номинал"] for height in heights}, {0.0})
        for height in heights:
            self.assertLessEqual(height["допуск"], 1.0 / dc.TIGHTENING_RATIO)

    def test_centre_of_gravity_is_inside_the_support_triangle(self):
        points = [(self.plane(n, "X"), self.plane(n, "Y")) for n in ("1", "2", "3")]
        (ax, ay), (bx, by), (cx, cy) = points
        gx = gy = 0.0                       # изделие симметрично
        total = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        u = ((by - cy) * (gx - cx) + (cx - bx) * (gy - cy)) / total
        v = ((cy - ay) * (gx - cx) + (ax - cx) * (gy - cy)) / total
        self.assertGreater(u, 0.0)
        self.assertGreater(v, 0.0)
        self.assertLess(u + v, 1.0)

    def test_rear_stop_defines_the_narrow_base(self):
        self.assertEqual(self.plane("4, 5", "контактная_плоскость"), -45.0)
        span = self.elements["4, 5"]["координаты"]["по_длине"]
        self.assertEqual((span["от"], span["до"]), (-78.0, 78.0))

    def test_inner_stops_are_124_apart(self):
        left = self.plane("7", "контактная_плоскость")
        right = self.plane("8", "контактная_плоскость")
        self.assertAlmostEqual(right - left, dc.POST_CLEARANCE, places=6)
        rows = {row["обозначение"]: row for row in dc.fixture_dimensions()}
        self.assertEqual(rows["B1"]["размер_приспособления"],
                         f"124 +{dc.fixture_tolerance(dc.CLEARANCE.tolerance):g}".replace(".", ","))

    def test_crossbar_stops_are_135_apart_and_give_5_5_overlap(self):
        stops = self.elements["9, 10"]["координаты"]
        left, right = stops["контактные_плоскости"]["номиналы"]
        self.assertAlmostEqual(right - left, dc.BAR_LEN, places=6)
        self.assertEqual(stops["размер_между_упорами"], "135 ±0,2")
        overlap = dc.chain_crossbar().result
        self.assertAlmostEqual(overlap.nominal, 5.5, places=6)
        self.assertAlmostEqual(overlap.nominal, (dc.BAR_LEN - dc.POST_CLEARANCE) / 2, places=6)
        self.assertEqual(overlap.label(), "5,5 ±0,15")

    def test_crossbar_stops_stand_in_the_weld_zone_and_are_removable(self):
        stop = self.elements["9, 10"]
        self.assertIn("откидные", stop["вид"])
        self.assertIn("перед сваркой", stop["примечание"])

    def test_regulated_stop_travel_covers_the_sheet_tolerance(self):
        travel = self.elements["6"]["координаты"]["ход_регулировки"]
        self.assertGreaterEqual(travel, dc.THICKNESS.tolerance)

    def test_vertical_clamps_sit_over_the_supports(self):
        supports = {(self.plane(n, "X"), self.plane(n, "Y")) for n in ("1", "2", "3")}
        for clamp in dc.clamps():
            if clamp["вид"].startswith("зажим винтовой откидной"):
                point = clamp["точка_приложения"]
                self.assertIn((point["X"], point["Y"]), supports, clamp["номер"])

    def test_side_clamps_press_against_the_stops(self):
        clamped = " ".join(clamp["прижимает"] for clamp in dc.clamps())
        for target in ("внутреннему упору 7", "внутреннему упору 8", "заднему упору 4–5"):
            self.assertIn(target, clamped)


class TestFormatting(unittest.TestCase):
    def test_numbers_are_written_the_russian_way(self):
        self.assertEqual(dc.num(10.5), "10,5")
        self.assertEqual(dc.num(45.0), "45")
        self.assertEqual(dc.num(120.0), "120")
        self.assertEqual(dc.num(-67.5), "-67,5")

    def test_deviations_are_written_the_eskd_way(self):
        self.assertEqual(dc.deviation(+0.2, -0.8), "+0,2/−0,8")
        self.assertEqual(dc.deviation(+0.5, -0.5), "±0,5")
        self.assertEqual(dc.deviation(0.0, -0.5), "−0,5")
        self.assertEqual(dc.deviation(+0.5, 0.0), "+0,5")


class TestArtifact(unittest.TestCase):
    def test_one_run_gives_the_document_and_the_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            doc, payload = dc.write(Path(tmp))
            self.assertTrue(doc.exists())
            self.assertTrue(payload.exists())
            json.loads(payload.read_text(encoding="utf-8"))

    def test_committed_artifact_is_up_to_date(self):
        """Числа воспроизводимы: пересборка даёт те же файлы."""
        with tempfile.TemporaryDirectory() as tmp:
            doc, payload = dc.write(Path(tmp))
            self.assertEqual(doc.read_text(encoding="utf-8"),
                             (dc.OUT_DIR / dc.DOC_NAME).read_text(encoding="utf-8"))
            self.assertEqual(payload.read_text(encoding="utf-8"),
                             (dc.OUT_DIR / dc.JSON_NAME).read_text(encoding="utf-8"))

    def test_payload_carries_the_coordinates_for_the_next_stage(self):
        data = dc.report()
        self.assertEqual(data["единицы"], "мм")
        self.assertEqual(len(data["элементы"]), 8)
        self.assertEqual(len(data["зажимы"]), 6)
        first = data["элементы"][0]
        self.assertEqual(first["координаты"]["X"], {"номинал": -70.0, "допуск": 0.1})

    def test_document_names_the_closing_and_compensating_links(self):
        text = dc.render_markdown(dc.report())
        for fragment in ("Компенсирующее звено", "156 — справочный размер",
                         "106 — справочный размер", "124 +0,2", "90 −0,2",
                         "135 ±0,2", "5,5 ±0,15", "Допуск приспособления",
                         "Координаты опор, упоров и зажимов", "Сверка с теорией",
                         "совпадают с опорными точками 1–6"):
            self.assertIn(fragment, text, fragment)

    def test_stage_readme_numbers_match_the_generated_document(self):
        """Числа в рукописном README этапа должны подтверждаться расчётом."""
        readme = (dc.OUT_DIR / "README.md").read_text(encoding="utf-8")
        document = dc.render_markdown(dc.report())
        for fragment in ("124 +0,2", "90 −0,2", "135 ±0,2", "45 ±0,2",
                         "0,42", "0,08", "5,5 ±0,15", "2,5"):
            self.assertIn(fragment, readme, f"README: {fragment}")
            self.assertIn(fragment, document, f"пересчитанный документ: {fragment}")

    def test_reference_sizes_are_not_normed_in_the_document(self):
        text = dc.render_markdown(dc.report())
        self.assertIn("справочный, без допуска", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
