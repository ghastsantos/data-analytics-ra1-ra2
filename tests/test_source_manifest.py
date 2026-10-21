"""Reprodução após o notebook baixar a fonte sem o manifesto do perfil."""
import hashlib
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import profile_source


class ReachedExcelReader(Exception):
    pass


class SourceManifestTests(unittest.TestCase):
    def test_existing_verified_archive_without_manifest_reaches_excel_reader(self):
        work = Path(__file__).resolve().parents[1] / ".work"
        work.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=work) as temp:
            raw = Path(temp) / "raw"
            raw.mkdir()
            archive = raw / "online_retail_uci.zip"
            with zipfile.ZipFile(archive, "w") as z:
                z.writestr(profile_source.MEMBER_NAME, b"test payload never parsed as Excel")
            expected_hash = hashlib.sha256(archive.read_bytes()).hexdigest()
            with patch.object(profile_source, "RAW", raw), \
                 patch.object(profile_source, "EVIDENCE", Path(temp) / "evidence"), \
                 patch.object(profile_source, "EXPECTED_ARCHIVE_SHA256", expected_hash, create=True), \
                 patch.object(profile_source.pd, "ExcelFile", side_effect=ReachedExcelReader):
                with self.assertRaises(ReachedExcelReader):
                    profile_source.main()
            manifest = json.loads((raw / "download_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["archive_sha256"], expected_hash)
            self.assertIsNone(manifest["downloaded_at_utc"])
            self.assertIn("verified_at_utc", manifest)


if __name__ == "__main__":
    unittest.main()
