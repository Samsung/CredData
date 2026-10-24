import unittest

from benchmark.__main__ import get_arguments


class TestScannerArgument(unittest.TestCase):

    def test_unknown_scanner_rejected(self):
        with self.assertRaises(SystemExit) as ctx:
            get_arguments(["--scanner", "does_not_exist"])

        self.assertEqual(2, ctx.exception.code)

    def test_supported_scanner_accepted(self):
        args = get_arguments(["--scanner", "credsweeper"])

        self.assertEqual("credsweeper", args.scanner)


if __name__ == "__main__":
    unittest.main()
