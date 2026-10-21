"""Regressão do diagnóstico exibido pelo notebook em uma coluna de tipo misto."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

import pandas as pd


class NotebookQualityTests(unittest.TestCase):
    def test_numeric_description_is_not_counted_as_outer_whitespace(self):
        root = Path(__file__).resolve().parents[1]
        notebook = json.loads((root / "projeto_data_analytics.ipynb").read_text(encoding="utf-8"))
        sources = ["".join(cell["source"]) for cell in notebook["cells"]
                   if cell["cell_type"] == "code"]
        source = next(value for value in sources if 'quality = pd.DataFrame([' in value)
        raw = pd.DataFrame([
            {"InvoiceNo": "100001", "StockCode": "12345", "Description": description,
             "Quantity": 1, "UnitPrice": 2.0, "InvoiceDate": pd.Timestamp("2011-01-01"),
             "CustomerID": 12345, "Country": "United Kingdom"}
            for description in ["PRODUCT", " PRODUCT ", 123, None]
        ])
        work = root / ".work"
        work.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=work) as temporary:
            temporary_root = Path(temporary)
            (temporary_root / "evidence").mkdir()
            namespace = {"pd": pd, "raw": raw, "ROOT": temporary_root,
                         "display": lambda *args: None}
            with contextlib.redirect_stdout(io.StringIO()):
                exec(compile(source, "notebook-quality-cell", "exec"), namespace)
            quality = namespace["quality"].set_index("ID")
            self.assertEqual(int(quality.loc["Q7", "Quantidade"]), 1)


if __name__ == "__main__":
    unittest.main()
