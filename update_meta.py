#!/usr/bin/env python3

"""
The script is developed to update meta with absolute positions of value instead from stripped line
"""
import json
import os
import subprocess
import sys
from argparse import ArgumentParser
from functools import cache
from typing import Dict, Tuple, List

from meta_cred import MetaCred
from meta_row import read_meta

EXIT_SUCCESS = 0
EXIT_FAILURE = 1


@cache
def read_cache(path) -> list[str]:
    with open(path, "r", encoding="utf8") as f:
        return f.read().replace("\r\n", '\n').replace('\r', '\n').split('\n')


def main(meta_dir: str, data_dir: str, report_file: str) -> int:
    errors = 0
    updated_rows = 0

    if not os.path.exists(meta_dir):
        raise FileExistsError(f"{meta_dir} directory does not exist.")
    if not os.path.exists(data_dir):
        raise FileExistsError(f"{data_dir} directory does not exist.")
    creds: Dict[Tuple[str, int, int], List[MetaCred]] = {}
    with open(report_file, 'r') as f:
        for i in json.load(f):
            cred = MetaCred(i)
            multi_cred_key = (cred.path, cred.line_start, cred.line_end)
            if multi_cred_key in creds:
                creds[multi_cred_key].append(cred)
            else:
                creds[multi_cred_key] = [cred]

    meta = read_meta(meta_dir)
    meta.sort(key=lambda x: (x.FilePath, x.LineStart, x.LineEnd, x.ValueStart, x.ValueEnd))
    for row in meta:
        categories = set(row.Category.split(':'))
        if "Secret" in categories:
            meta_key = (row.FilePath, row.LineStart, row.LineEnd)
            possible_creds = creds.get(meta_key)
            if not possible_creds:
                row.Category = "Other"
                errors += subprocess.call(
                    ["sed", "-i",
                     f"s|^{row.Id},{row.FileID},.*$|" + str(row) + "|",
                     f"{meta_dir}/{row.RepoName}.csv"])
                updated_rows += 1
                continue

            if 0 > row.ValueStart:
                # has markup for whole line
                if any("Secret" == x.rule for x in possible_creds):
                    # ok
                    continue
                if 1 == len(categories):
                    # should be changed
                    categories = set(x.rule for x in possible_creds)
                else:
                    categories.remove("Secret")
            else:
                if any("Secret" == x.rule for x in possible_creds if x.value_start == row.ValueStart):
                    # ok
                    continue
                else:
                    # wrong position in markup - must be skipped
                    if 1 == len(categories):
                        # should be changed
                        categories = set(x.rule for x in possible_creds if x.value_start == row.ValueStart and (
                                    x.value_end == row.ValueEnd or 0 > row.ValueEnd))
                        if not categories:
                            continue # later...
                            # wrong end position
                            categories = set(x.rule for x in possible_creds if x.value_start == row.ValueStart)
                            row.ValueEnd = -1
                            assert row.GroundTruth == 'F' or row.GroundTruth == 'Template', row
                            row.GroundTruth = 'F'
                    else:
                        categories.remove("Secret")

            if not categories:
                categories.add("Other")
                continue # later...
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

    parser.add_argument("report_file", help="Credentials report from CredSweeper")
    parser.add_argument("meta_dir", help="Markup location", nargs='?', default="meta")
    parser.add_argument("data_dir", help="Dataset location", nargs='?', default="data")
    _args = parser.parse_args()

    exit_code = main(_args.meta_dir, _args.data_dir, _args.report_file)
    sys.exit(exit_code)
