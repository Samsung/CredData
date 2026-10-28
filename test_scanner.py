"""Regression tests for Scanner.check_line_from_meta().

Run from the CredData repository root with:
    python -m unittest -v test_scanner.py
"""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from benchmark.common import LineStatus
from benchmark.scanner.scanner import Scanner
from constants import LABEL_FALSE, LABEL_TRUE, OTHER_CATEGORY
from meta_key import MetaKey


DATA_PATH = "data/repo/file.py"
FILE_PATH = "data/repo/file.py"


class _DummyScanner(Scanner):
    """Minimal concrete Scanner; tests bypass __init__ to avoid downloads."""

    @property
    def output_dir(self):
        return ""

    @output_dir.setter
    def output_dir(self, output_dir):
        pass

    def init_scanner(self):
        pass

    def run_scanner(self):
        pass

    def parse_result(self):
        pass


def _make_row(category="Password", ground_truth=LABEL_TRUE, value_start=-1, value_end=-1):
    """Build a metadata-like row without needing a dataset CSV."""
    return SimpleNamespace(
        Id=1,
        FileID="file",
        Domain="GitHub",
        RepoName="repo",
        FilePath=DATA_PATH,
        LineStart=10,
        LineEnd=10,
        GroundTruth=ground_truth,
        ValueStart=value_start,
        ValueEnd=value_end,
        CryptographyKey="",
        PredefinedPattern="",
        Category=category,
    )


def _make_scanner(cred_data_dir, rows=None, fix=False):
    # Bypass Scanner.__init__: it downloads scanners and loads the full benchmark data.
    scanner = object.__new__(_DummyScanner)
    scanner.scanner_type = None
    scanner.scanner_dir = ""
    scanner.cred_data_dir = str(cred_data_dir)
    scanner.fix = fix
    scanner.line_checker = set()
    scanner.result_cnt = 0
    scanner.lost_cnt = 0
    scanner.true_cnt = 0
    scanner.false_cnt = 0
    scanner.result_dict = {}
    scanner.total_true_cnt = 0
    scanner.total_false_cnt = 0
    scanner.rules_markup_counters = {}
    scanner.meta_next_id = 10
    scanner.file_types = {}
    scanner.total_data_valid_lines = 0
    scanner.meta = {}
    scanner.reported = {}
    if rows:
        scanner.meta[MetaKey(DATA_PATH, 10, 10)] = list(rows)

    counted = []
    scanner._increase_result_dict_cnt = lambda rule, is_true: counted.append((rule, is_true))
    scanner._test_counted = counted
    return scanner


class RulelessScannerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.scanner = _make_scanner(self.temp_dir.name, [_make_row()])

    def test_ruleless_detection_with_existing_metadata_is_not_scored(self):
        row = _make_row(category="Password:Token", ground_truth=LABEL_TRUE)
        self.scanner.meta[MetaKey(DATA_PATH, 10, 10)] = [row]

        status, repo_name, file_id = self.scanner.check_line_from_meta(FILE_PATH, 10, 10)

        self.assertEqual(status, LineStatus.NOT_IN_DB)
        self.assertEqual((repo_name, file_id), ("repo", "file"))
        self.assertEqual(self.scanner.true_cnt, 0)
        self.assertEqual(self.scanner.false_cnt, 0)
        self.assertEqual(self.scanner._test_counted, [])
        self.assertEqual(self.scanner.lost_cnt, 1)
        self.assertEqual(self.scanner.result_cnt, 1)
        # A line-level finding must not be attributed to every category on the row.
        self.assertEqual(self.scanner.meta[MetaKey(DATA_PATH, 10, 10)], [row])

    def test_ruleless_detection_without_metadata_returns_not_in_db(self):
        self.scanner.meta = {}

        status, _, _ = self.scanner.check_line_from_meta(FILE_PATH, 10, 10)

        self.assertEqual(status, LineStatus.NOT_IN_DB)
        self.assertEqual(self.scanner.lost_cnt, 1)
        self.assertEqual(self.scanner.result_cnt, 1)
        self.assertEqual(self.scanner.true_cnt, 0)
        self.assertEqual(self.scanner.false_cnt, 0)
        self.assertEqual(self.scanner.meta, {})

    def test_duplicate_ruleless_findings_do_not_inflate_counts(self):
        first_status, _, _ = self.scanner.check_line_from_meta(FILE_PATH, 10, 10)
        second_status, _, _ = self.scanner.check_line_from_meta(FILE_PATH, 10, 10)

        self.assertEqual(first_status, LineStatus.NOT_IN_DB)
        self.assertEqual(second_status, LineStatus.CHECKED)
        self.assertEqual(self.scanner.result_cnt, 1)
        self.assertEqual(self.scanner.lost_cnt, 1)
        self.assertEqual(self.scanner.true_cnt, 0)
        self.assertEqual(self.scanner.false_cnt, 0)
        self.assertEqual(self.scanner._test_counted, [])

    def test_existing_rule_based_matching_is_unchanged(self):
        status, repo_name, file_id = self.scanner.check_line_from_meta(
            FILE_PATH, 10, 10, rule="Password"
        )

        self.assertEqual(status, LineStatus.FALSE)
        self.assertEqual((repo_name, file_id), ("repo", "file"))
        self.assertEqual(self.scanner.true_cnt, 1)
        self.assertEqual(self.scanner._test_counted, [("Password", True)])

    def test_ruleless_fix_mode_queues_unseen_line_as_other(self):
        root = Path(self.temp_dir.name)
        meta_dir = root / "meta"
        meta_dir.mkdir(parents=True, exist_ok=True)
        meta_file = meta_dir / "repo.csv"
        meta_file.write_text("", encoding="utf-8")
        scanner = _make_scanner(root, rows=None, fix=True)

        status, _, _ = scanner.check_line_from_meta(FILE_PATH, 10, 10)

        self.assertEqual(status, LineStatus.NOT_IN_DB)
        row = scanner.meta[MetaKey(DATA_PATH, 10, 10)][0]
        self.assertEqual(row.Category, OTHER_CATEGORY)
        self.assertEqual(row.GroundTruth, "X")
        saved_metadata = meta_file.read_text(encoding="utf-8").strip()
        self.assertTrue(saved_metadata)
        self.assertEqual(saved_metadata.split(",")[7], "X")
        self.assertEqual(saved_metadata.split(",")[12], OTHER_CATEGORY)

    def test_ruleless_fix_mode_does_not_modify_existing_metadata(self):
        root = Path(self.temp_dir.name)
        meta_dir = root / "meta"
        meta_dir.mkdir(parents=True, exist_ok=True)
        meta_file = meta_dir / "repo.csv"
        original = "existing metadata\n"
        meta_file.write_text(original, encoding="utf-8")
        row = _make_row(category="Password:Token", ground_truth=LABEL_TRUE)
        scanner = _make_scanner(root, rows=[row], fix=True)

        status, _, _ = scanner.check_line_from_meta(FILE_PATH, 10, 10)

        self.assertEqual(status, LineStatus.NOT_IN_DB)
        self.assertEqual(meta_file.read_text(encoding="utf-8"), original)
        self.assertEqual(scanner.meta[MetaKey(DATA_PATH, 10, 10)], [row])
        self.assertEqual(scanner._test_counted, [])


if __name__ == "__main__":
    unittest.main()
