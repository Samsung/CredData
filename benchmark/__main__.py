import sys
from argparse import ArgumentParser, Namespace

from benchmark.app import Benchmark

SCANNER_LIST = [
    "credsweeper", "credential_digger", "detect_secrets", "gitleaks", "shhgit", "trufflehog", "trufflehog3", "wraith"
]


def get_arguments(argv: list[str]) -> Namespace:
    parser = ArgumentParser(prog="python -m benchmark")
    parser.add_argument("--scanner",
                        choices=SCANNER_LIST,
                        help=f"scanner name to benchmark (support: {SCANNER_LIST})",
                        dest="scanner",
                        metavar="SCANNER",
                        required=True)
    parser.add_argument("--load",
                        help=f"skip scan and use prepared output",
                        dest="load")
    parser.add_argument("--fix",
                        help=f"add/update markup for unknown credetials",
                        action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str]) -> None:
    args = get_arguments(argv[1:])
    benchmark = Benchmark()
    benchmark.run(args.scanner, args.load, args.fix)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
