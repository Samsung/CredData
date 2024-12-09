from argparse import ArgumentParser, Namespace

from benchmark.app import Benchmark

SCANNER_LIST = [
    "credsweeper", "credential_digger", "detect_secrets", "gitleaks", "shhgit", "trufflehog", "trufflehog3", "wraith"
]


def get_arguments() -> Namespace:
    parser = ArgumentParser(prog="python -m benchmark")
    parser.add_argument("--scanner",
                        nargs="?",
                        help=f"scanner name to benchmark (support: {SCANNER_LIST})",
                        dest="scanner",
                        metavar="SCANNER",
                        required=True)
    parser.add_argument("--load",
                        help=f"skip scan and use prepared output",
                        dest="load")
    parser.add_argument("--fix",
                        help=f"add/update markup for unknown credetials",
                        dest="fix")
    return parser.parse_args()


def main() -> None:
    args = get_arguments()
    benchmark = Benchmark()
    if args.scanner in SCANNER_LIST:
        benchmark.run(args.scanner, args.load, args.fix)
    else:
        print(f"Please check scanner name (support: {SCANNER_LIST})")


if __name__ == "__main__":
    main()
