import unittest
from unittest import mock

from benchmark.__main__ import main


class TestScannerArgument(unittest.TestCase):

    def _run(self, *argv):
        with (
            mock.patch("benchmark.__main__.Benchmark") as benchmark_mock,
            self.assertRaises(SystemExit) as ctx,
        ):
            main(["python -m benchmark", *argv])
        return benchmark_mock, ctx.exception.code

    def test_unknown_scanner_rejected_before_init(self):
        benchmark_mock, code = self._run("--scanner", "does_not_exist")
        self.assertEqual(2, code)
        benchmark_mock.assert_not_called()

    def test_missing_scanner_value_rejected_before_init(self):
        benchmark_mock, code = self._run("--scanner")
        self.assertEqual(2, code)
        benchmark_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
