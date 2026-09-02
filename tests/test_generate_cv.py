import json
import tempfile
import unittest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generate_cv import generate, latex


class GeneratorTests(unittest.TestCase):
    def test_latex_escape(self):
        self.assertEqual(latex("A&B_1"), r"A\&B\_1")

    def test_sections_and_editorial_split(self):
        fixture = Path(__file__).with_name("fixture.json")
        record = json.loads(fixture.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            generate(record, out, ("editor", "journal"))
            employment = (out / "employments.tex").read_text(encoding="utf-8")
            editorial = (out / "editorial-services.tex").read_text(encoding="utf-8")
            service = (out / "services.tex").read_text(encoding="utf-8")
            self.assertIn(r"Researcher \& Developer", employment)
            self.assertIn(r"R\&D\_1", employment)
            self.assertIn("Associate Editor", editorial)
            self.assertNotIn("Associate Editor", service)


if __name__ == "__main__":
    unittest.main()
