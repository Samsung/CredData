#!/usr/bin/env python3

"""
The script is developed to update meta with absolute positions of value instead from stripped line
"""

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
    for row in meta:
        offset = offset_aux = 0
        if 0 <= row.ValueStart:
            lines = read_cache(row.FilePath)
            line = lines[row.LineStart - 1]
            offset = len(line) - len(line.lstrip())
            row.ValueStart += offset
            if 0 <= row.ValueEnd:
                if row.LineStart == row.LineEnd:
                    row.ValueEnd += offset
                else:
                    line_aux = lines[row.LineEnd - 1]
                    offset_aux = len(line_aux) - len(line_aux.lstrip())
                    row.ValueEnd += offset_aux
            if 0 > offset or 0 > offset_aux:
                errors += 1
        if 0 < (offset + offset_aux):
            subprocess.run(
                ["sed", "-i",
                 "s|^" + str(row.Id) + ",.*|" + str(row) + "|",
                 f"{meta_dir}/{row.RepoName}.csv"])

    result = EXIT_SUCCESS if 0 == errors else EXIT_FAILURE
    print(f"Updated {updated_rows} of {len(meta)}, errors: {errors}, {result}", flush=True)
    return result


if __name__ == "__main__":
    parser = ArgumentParser(prog=f"python {os.path.basename(__file__)}",
                            description="Temporally console script for update meta with absolute positions of values")

    parser.add_argument("meta_dir", help="Markup location", nargs='?', default="meta")
    parser.add_argument("data_dir", help="Dataset location", nargs='?', default="data")
    _args = parser.parse_args()

    exit_code = main(_args.meta_dir, _args.data_dir)
    sys.exit(exit_code)
