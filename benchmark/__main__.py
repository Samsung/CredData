from argparse import ArgumentParser
from benchmark.app import Benchmark

SCANNER_LIST = ["credsweeper", "detect_secrets", "gitleaks", "shhgit", "credential_digger", "wraith", "trufflehog3"]


def get_arguments() -> ArgumentParser.parse_args:
    parser = ArgumentParser(prog="python -m benchmark")
    parser.add_argument("--scanner",
                        nargs="?",
                        help=f"scanner name to benchmark (support: {SCANNER_LIST})",
                        dest="scanner",
                        metavar="SCANNER",
                        required=True)
    return parser.parse_args()


def main() -> None:
    args = get_arguments()
    benchmark = Benchmark()
    if args.scanner in SCANNER_LIST:
        benchmark.run(args.scanner)
    else:
        print(f"Please check scanner name (support: {SCANNER_LIST})")


if __name__ == "__main__":
    main()
