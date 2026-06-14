import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from aerobeam.cli import design_from_mapping, main


VALID_INPUT = {
    "aircraft": {
        "mass_kg": 12.5,
        "span_m": 2.4,
        "limit_load_factor": 4.4,
        "safety_factor": 1.5,
        "load_distribution": "elliptical",
    },
    "spar": {
        "width_m": 0.04,
        "height_m": 0.12,
        "min_wall_thickness_m": 0.0008,
        "manufacturing_increment_m": 0.0002,
    },
    "material": "6061-T6",
}


class CliTest(unittest.TestCase):
    def test_design_from_mapping_returns_result(self) -> None:
        result = design_from_mapping(VALID_INPUT)

        self.assertGreaterEqual(result.controlling_margin, 0.0)

    def test_main_prints_json_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "input.json"
            input_path.write_text(json.dumps(VALID_INPUT), encoding="utf-8")

            with patch("builtins.print") as print_mock:
                exit_code = main([str(input_path), "--format", "json"])

        self.assertEqual(exit_code, 0)
        payload = json.loads(print_mock.call_args.args[0])
        self.assertIn("geometry", payload)
        self.assertIn("margins", payload)

    def test_missing_required_field_exits_with_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "input.json"
            invalid_input = dict(VALID_INPUT)
            invalid_input.pop("material")
            input_path.write_text(json.dumps(invalid_input), encoding="utf-8")

            with patch("sys.stderr", new_callable=io.StringIO):
                with self.assertRaises(SystemExit) as caught:
                    main([str(input_path)])

        self.assertEqual(caught.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
