#!/usr/bin/env python3

"""
The script is developed to update meta with absolute positions of value instead from stripped line
"""
import copy
import os
import subprocess
import sys
from argparse import ArgumentParser
from functools import cache

from meta_row import read_meta

EXIT_SUCCESS = 0
EXIT_FAILURE = 1


@cache
def read_cache(path) -> list[str]:
    with open(path, "r", encoding="utf8") as f:
        return f.read().replace("\r\n", '\n').replace('\r', '\n').split('\n')


def main(meta_dir: str, data_dir: str) -> int:
    errors = 0
    updated_rows = 0

    if not os.path.exists(meta_dir):
        raise FileExistsError(f"{meta_dir} directory does not exist.")
    if not os.path.exists(data_dir):
        raise FileExistsError(f"{data_dir} directory does not exist.")

    meta = read_meta(meta_dir)
    meta.sort(key=lambda x: (x.FilePath, x.LineStart, x.LineEnd, x.ValueStart, x.ValueEnd))
    for i in meta:
        categories = set(i.Category.split(':'))
        if "Secret" in categories:
            lines = read_cache(i.FilePath)
            line = lines[i.LineStart - 1].lower()
            if "secret" not in line:
                # there is no the keyword in the line
                row=copy.deepcopy(i)
                categories.remove("Secret")
                if 0 <= row.ValueStart:
                    line = line[:row.ValueStart]
                if 160 < len(line):
                    line = line[:-160]

                for keyword, category in [
                    ("credential", "Credential"),
                    ("cert", "Certificate"),
                    ("://", "URL Credentials"),
                    ("pass", "Password"),
                    ("pw", "Password"),
                    ("key","Key"),
                    ("token", "Token"),
                    ("nonce", "Nonce"),
                    ("salt", "Salt"),
                    ("api", "API"),
                    ("auth", "Auth"),
                ]:
                    if keyword in line:
                        categories.add(category)

                if not categories:
                    categories.add("Other")
                row.Category = ':'.join(categories)
                errors += subprocess.call(
                    ["sed", "-i",
                     f"s|^{row.Id},{row.FileID},.*$|" + str(row) + "|",
                     f"{meta_dir}/{row.RepoName}.csv"])
                updated_rows += 1

    result = EXIT_SUCCESS if 0 == errors else EXIT_FAILURE
    print(f"Updated {updated_rows} of {len(meta)}, errors: {errors}, {result}", flush=True)
    return result


if __name__ == "__main__":
    parser = ArgumentParser(prog=f"python {os.path.basename(__file__)}",
                            description="Temporally console script for update meta with Secret category to Other")

    parser.add_argument("meta_dir", help="Markup location", nargs='?', default="meta")
    parser.add_argument("data_dir", help="Dataset location", nargs='?', default="data")
    _args = parser.parse_args()

    exit_code = main(_args.meta_dir, _args.data_dir)
    sys.exit(exit_code)
