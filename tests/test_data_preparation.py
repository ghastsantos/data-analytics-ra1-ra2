"""Casos pequenos para proteger as decisões de recorte e rastreabilidade."""
import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from data_preparation import prepare_data


def record(**changes):
    row = dict(InvoiceNo="100001", StockCode="12345A", Description=" PRODUCT ",
               Quantity=2, InvoiceDate="2011-01-01 10:00:00", UnitPrice=2.50,
               CustomerID=12345, Country="United Kingdom")
    row.update(changes)
    return row


class PreparationTests(unittest.TestCase):
    def test_keeps_missing_customer_exact_repetitions_and_large_valid_sale(self):
        raw = pd.DataFrame([record(CustomerID=None), record(CustomerID=None),
                            record(Quantity=10000)])
        clean, excluded, summary = prepare_data(raw)
        self.assertEqual(len(clean), 3)
        self.assertEqual(len(excluded), 0)
        self.assertEqual(clean.CustomerID.isna().sum(), 2)
        self.assertEqual(clean.SourceRow.tolist(), [2, 3, 4])
        self.assertEqual(clean.Description.tolist(), ["PRODUCT"] * 3)
        self.assertEqual(summary["exact_duplicate_rows_kept"], 1)
        self.assertTrue(clean.SourceRow.is_unique)

    def test_exclusions_are_disjoint_and_reconcile_with_original_rows(self):
        raw = pd.DataFrame([
            record(), record(InvoiceNo="C100002", Quantity=-2),
            record(StockCode="POST"), record(Quantity=0), record(UnitPrice=0),
            record(InvoiceDate="bad date"), record(Description=" "),
        ])
        clean, excluded, summary = prepare_data(raw)
        self.assertEqual(len(clean), 1)
        self.assertEqual(len(excluded), 6)
        self.assertEqual(set(excluded.ExclusionReason), {
            "cancellation", "non_merchandise_code", "non_positive_quantity",
            "non_positive_price", "invalid_required_fields", "missing_description",
        })
        self.assertEqual(len(clean) + len(excluded), len(raw))
        self.assertFalse(set(clean.SourceRow) & set(excluded.SourceRow))
        self.assertEqual(summary["input_rows"], 7)

    def test_rejects_fractional_quantities_and_keeps_identifiers_as_text(self):
        raw = pd.DataFrame([record(InvoiceNo=100001, StockCode=12345),
                            record(Quantity=1.5)])
        clean, excluded, _ = prepare_data(raw)
        self.assertEqual(clean.InvoiceNo.iloc[0], "100001")
        self.assertEqual(clean.StockCode.iloc[0], "12345")
        self.assertEqual(str(clean.Quantity.dtype), "Int64")
        self.assertEqual(excluded.ExclusionReason.tolist(), ["invalid_required_fields"])

    def test_missing_columns_are_reported_clearly(self):
        with self.assertRaisesRegex(ValueError, "Country"):
            prepare_data(pd.DataFrame([record()]).drop(columns="Country"))

    def test_keeps_merchandise_with_unusual_codes_and_excludes_vouchers(self):
        raw = pd.DataFrame([record(StockCode="DCGSSBOY"), record(StockCode="PADS"),
                            record(StockCode="gift_0001_10"), record(StockCode="m")])
        clean, excluded, _ = prepare_data(raw)
        self.assertEqual(clean.StockCode.tolist(), ["DCGSSBOY", "PADS"])
        self.assertEqual(excluded.ExclusionReason.tolist(), ["non_merchandise_code"] * 2)


if __name__ == "__main__":
    unittest.main()
