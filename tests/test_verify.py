import json
import tempfile
import unittest
from pathlib import Path

from scripts.verify import verify


ROOT = Path(__file__).resolve().parents[1]


class VerifySkillTest(unittest.TestCase):
    def copy_fixture(self) -> Path:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        target = Path(temporary.name)
        for name in ("SKILL.md", "catalog-receipt.json"):
            (target / name).write_bytes((ROOT / name).read_bytes())
        (target / "references").mkdir()
        for source in (ROOT / "references").iterdir():
            (target / "references" / source.name).write_bytes(source.read_bytes())
        return target

    def test_repository_passes(self) -> None:
        verify(ROOT)

    def test_stale_receipt_fails(self) -> None:
        target = self.copy_fixture()
        receipt_path = target / "catalog-receipt.json"
        receipt = json.loads(receipt_path.read_text())
        receipt["schemaVersion"] = "treeseed.skill-catalog-receipt/v1"
        receipt_path.write_text(json.dumps(receipt))
        with self.assertRaisesRegex(ValueError, "stale"):
            verify(target)

    def test_invalid_catalog_digest_fails(self) -> None:
        target = self.copy_fixture()
        receipt_path = target / "catalog-receipt.json"
        receipt = json.loads(receipt_path.read_text())
        receipt["sdk"]["contractBundle"]["digest"] = "sha256:not-a-digest"
        receipt_path.write_text(json.dumps(receipt))
        with self.assertRaisesRegex(ValueError, "digest is invalid"):
            verify(target)


if __name__ == "__main__":
    unittest.main()
