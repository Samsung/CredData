#!/usr/bin/env python3

"""
The script generates ascii text with colorization only for markup lines
RED - false cases
GREEN - true
MAGENTA - templates
When value start-end defined - the text is marked
"""

import json
import os
import subprocess
import sys
from argparse import ArgumentParser
from functools import cache
from typing import List, Optional, Tuple, Dict

from colorama import Fore, Back, Style

from meta_cred import MetaCred
from meta_row import read_meta, MetaRow

EXIT_SUCCESS = 0
EXIT_FAILURE = 1


@cache
def read_cache(path) -> list[str]:
    with open(path, "r", encoding="utf8") as f:
        return f.read().split('\n')


def read_data(path, line_start, line_end, value_start, value_end, ground_truth, creds: List[MetaCred]):
    lines = read_cache(path)
    if line_start == line_end:
        cred_line = lines[line_start - 1]
        stripped_line = cred_line.strip()
        end_offset = 0
    elif line_start < line_end:
        # todo: move the line to MetaCred class
        cred_line = '\n'.join(lines[line_start - 1:line_end])
        stripped_line = '\n'.join(x.strip() for x in lines[line_start - 1:line_end - 1])
        end_offset = len(stripped_line) + 1  # +1 for line feed
        stripped_line = '\n'.join([stripped_line, lines[line_end - 1].strip()])
    else:
        raise RuntimeError(f"Line start must be less than end. {path},{line_start},{line_end}")

    if 'T' == ground_truth:
        fore_style = Fore.GREEN
    elif 'F' == ground_truth:
        fore_style = Fore.RED
    elif 'Template' == ground_truth:
        fore_style = Fore.MAGENTA
    elif 'X' == ground_truth:
        fore_style = Fore.LIGHTRED_EX
    else:
        raise RuntimeError(f"Unknown type {ground_truth}")

    line_found_in_cred = False
    correct_value_position = False
    if creds:
        for cred in creds:
            if cred.path == path:
                if line_start == cred.line_start:
                    line_found_in_cred = True
                    # print all creds we found
                    print(
                        f"{cred.rule},{line_start}:{cred.strip_value_start},{cred.strip_value_end}:{Style.RESET_ALL}"
                        f"{cred_line[:cred.value_start]}{Back.LIGHTRED_EX}{cred_line[cred.value_start:cred.value_end]}"
                        f"{Style.RESET_ALL}{cred_line[cred.value_end:]}", flush=True)
                    if 0 <= value_start == cred.strip_value_start and 0 <= value_end == cred.strip_value_end:
                        correct_value_position = True
                    elif 0 <= value_start == cred.strip_value_start:
                        correct_value_position = True
    else:
        line_found_in_cred = True
        correct_value_position = True

    if 0 <= value_start and 0 <= value_end:
        line = stripped_line[:value_start] + Back.LIGHTYELLOW_EX + \
               stripped_line[value_start:value_end + end_offset] + Style.RESET_ALL + \
               fore_style + stripped_line[value_end + end_offset:]
    else:
        line = stripped_line
    print(f"{line_start}:{Style.RESET_ALL}{fore_style}{line}{Style.RESET_ALL}", flush=True)
    if not correct_value_position:
        print("Possible wrong value markup", flush=True)
    if not line_found_in_cred:
        # todo: an activity to fine-tune markup
        print("Markup was not found in creds in line", flush=True)
        test_line = stripped_line.lower()
        if not any(
                x in test_line for x in
                ["api", "pass", "secret", "pw", "key", "credential", "token", "auth", "nonce", "salt", "cert"]
        ):
            repo_id = path.split('/')[1]
            subprocess.run(
                ["sed", "-i",
                 f"/.*{path.split('/')[-1]},{line_start},{line_end},.*/d",
                 f"meta/{repo_id}.csv"])

    print("\n\n")


def main(meta_dir: str,
         data_dir: str,
         check_only: bool,
         data_filter: dict,
         load_json: Optional[str] = None,
         category: Optional[str] = None) -> int:
    errors = 0
    duplicates = 0
    if not os.path.exists(meta_dir):
        raise FileExistsError(f"{meta_dir} directory does not exist.")
    if not os.path.exists(data_dir):
        raise FileExistsError(f"{data_dir} directory does not exist.")
    creds = []
    if load_json:
        with open(load_json, "r") as f:
            creds.extend([MetaCred(x) for x in json.load(f)])

    meta = read_meta(meta_dir)
    meta.sort(key=lambda x: (x.FilePath, x.LineStart, x.LineEnd, x.ValueStart, x.ValueEnd))
    displayed_rows = 0
    shown_markup: Dict[Tuple[str, int, int, int, int], MetaRow] = {}
    for row in meta:
        if not data_filter[row.GroundTruth]:
            continue
        if category and category not in row.Category:
            continue

        displayed_rows += 1
        if not check_only:
            print(str(row), flush=True)
            try:
                read_data(row.FilePath,
                          row.LineStart,
                          row.LineEnd,
                          row.ValueStart,
                          row.ValueEnd,
                          row.GroundTruth,
                          creds)
            except Exception as exc:
                print(f"Failure {row}", exc, flush=True)
                errors += 1
        if 'T' == row.GroundTruth and row.LineStart == row.LineEnd:
            if 0 > row.ValueStart:
                print(f"Missed ValueStart for TRUE markup!\n{row}", flush=True)
                errors += 1
            elif 0 < row.ValueEnd and 4 > row.ValueEnd - row.ValueStart:
                print(f"Too short value for TRUE markup!\n{row}", flush=True)
                errors += 1

        markup_key = (row.FilePath, row.LineStart, row.LineEnd, row.ValueStart, row.ValueEnd)
        if markup_key in shown_markup:
            print(f"Duplicate markup!\nSHOWN:{shown_markup[markup_key]}\nTHIS:{row}", flush=True)
            duplicates += 1
        else:
            shown_markup[markup_key] = row
    result = EXIT_SUCCESS if 0 == duplicates == errors else EXIT_FAILURE
    print(f"Shown {displayed_rows} of {len(meta)}, errors: {errors}, duplicates: {duplicates}, {result}", flush=True)
    return result


if __name__ == "__main__":
    parser = ArgumentParser(prog="python review_data.py",
                            description="Console script for review markup with colorization")

    parser.add_argument("meta_dir", help="Markup location", nargs='?', default="meta")
    parser.add_argument("data_dir", help="Dataset location", nargs='?', default="data")
    parser.add_argument("--check_only", help="Check meta markup only", action='store_true')
    parser.add_argument("-T", help="Show TRUE markup", action="store_true")
    parser.add_argument("-F", help="Show FALSE markup", action="store_true")
    parser.add_argument("-t", help="Show Template markup", action="store_true")
    parser.add_argument("-X", help="Show X markup", action="store_true")
    parser.add_argument("--load", help="Load json report from CredSweeper", nargs='?')
    parser.add_argument("--category", help="Filter only with the category", nargs='?')
    _args = parser.parse_args()

    _data_filter = {"Other": False}
    if not _args.T and not _args.F and not _args.t and not _args.X:
        _data_filter["T"] = True
        _data_filter["F"] = True
        _data_filter["Template"] = True
        _data_filter["X"] = True
    else:
        _data_filter["T"] = _args.T
        _data_filter["F"] = _args.F
        _data_filter["Template"] = _args.t
        _data_filter["X"] = _args.X
    exit_code = main(_args.meta_dir, _args.data_dir, bool(_args.check_only), _data_filter, _args.load, _args.category)
    sys.exit(exit_code)

# review generation command
# .venv/bin/python review_data.py meta data >review.$(now).$(git rev-parse HEAD).txt

# use review with 'less'
# python review_data.py | less -R
