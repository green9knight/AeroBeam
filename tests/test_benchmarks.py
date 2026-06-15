import json
import math
import unittest
from pathlib import Path

from wing_stress_analyzer import WingStressAnalyzer


ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "benchmarks" / "cases"
EXPECTED = ROOT / "benchmarks" / "expected"


def output_value(analyzer: WingStressAnalyzer, key: str) -> float:
    mapping = {
        "V_root": analyzer.pos["V_root"],
        "M_root": analyzer.pos["M_root"],
        "M_front_root": analyzer.pos["M_front"][0],
    }
    return float(mapping[key])


class BenchmarkTest(unittest.TestCase):
    def test_benchmark_cases(self):
        case_files = sorted(CASES.glob("*.aerobeam"))
        self.assertGreater(len(case_files), 0, "no benchmark cases found")

        for case_path in case_files:
            expected_path = EXPECTED / f"{case_path.stem}.json"
            with self.subTest(case=case_path.name):
                self.assertTrue(expected_path.exists(), f"missing {expected_path}")
                inputs = json.loads(case_path.read_text())
                expected = json.loads(expected_path.read_text())

                analyzer = WingStressAnalyzer(inputs)
                analyzer.analyze()

                for key, spec in expected["checks"].items():
                    actual = output_value(analyzer, key)
                    target = float(spec["value"])
                    rtol = float(spec.get("rtol", 1e-6))
                    atol = float(spec.get("atol", 0.0))
                    allowed = max(atol, abs(target) * rtol)
                    self.assertLessEqual(
                        abs(actual - target),
                        allowed,
                        f"{key}: actual={actual}, expected={target}, allowed={allowed}, basis={spec.get('basis')}",
                    )


if __name__ == "__main__":
    unittest.main()
