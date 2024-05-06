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
from typing import List, Optional

from colorama import Fore, Back, Style

from meta_cred import MetaCred
from meta_row import read_meta


def read_data(path, line_start, line_end, value_start, value_end, ground_truth, creds: List[MetaCred]):
    with open(path, "r", encoding="utf8") as f:
        lines = f.readlines()
    if line_start == line_end:
        line = lines[line_start - 1]
    else:
        line = ''.join(lines[line_start - 1:line_end])
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
    stripped_line = line.lstrip()

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
                        f"{line[:cred.value_start]}{Back.LIGHTRED_EX}{line[cred.value_start:cred.value_end]}"
                        f"{Style.RESET_ALL}{line[cred.value_end:]}", flush=True)
                    if 0 <= value_start == cred.strip_value_start and 0 <= value_end == cred.strip_value_end:
                        correct_value_position = True
                    elif 0 <= value_start == cred.strip_value_start:
                        correct_value_position = True
    else:
        line_found_in_cred = True
        correct_value_position = True

    if 0 <= value_start and 0 <= value_end:
        line = stripped_line[:value_start] + Back.LIGHTYELLOW_EX + \
               stripped_line[value_start:value_end] + Style.RESET_ALL + \
               fore_style + stripped_line[value_end:]
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
                 f"/.*{path.split('/')[-1]},{line_start}:{line_end},.*/d",
                 f"meta/{repo_id}.csv"])

    print("\n\n")


def main(meta_dir, data_dir, data_filter, load_json: Optional[str] = None, category: Optional[str] = None):
    if not os.path.exists(meta_dir):
        raise FileExistsError(f"{meta_dir} directory does not exist.")
    if not os.path.exists(data_dir):
        raise FileExistsError(f"{data_dir} directory does not exist.")
    creds = []
    if load_json:
        with open(load_json, "r") as f:
            creds.extend([MetaCred(x) for x in json.load(f)])

    sorted_meta_rows = read_meta(meta_dir)
    sorted_meta_rows.sort(key=lambda x: (x.FilePath, x.LineStart, x.LineEnd, x.ValueStart, x.ValueEnd))
    displayed_rows = 0
    shown_rows = set()
    for meta_row in sorted_meta_rows:
        if not data_filter[meta_row.GroundTruth]:
            continue
        if category and not category == meta_row.Category:
            continue

        displayed_rows += 1
        print(meta_row, flush=True)
        try:
            read_data(meta_row.FilePath,
                      meta_row.LineStart,
                      meta_row.LineEnd,
                      meta_row.ValueStart,
                      meta_row.ValueEnd,
                      meta_row.GroundTruth,
                      creds)
        except Exception as exc:
            print(f"Failure {meta_row}", exc, flush=True)
            raise
        cred_pos_uniq_str = f"{meta_row.FilePath}" \
                            f" {meta_row.LineStart}:{meta_row.LineEnd}" \
                            f" {meta_row.ValueStart}:{meta_row.ValueEnd}"
        if cred_pos_uniq_str in shown_rows:
            raise RuntimeError(f"Duplicate row {meta_row}")
        else:
            shown_rows.add(cred_pos_uniq_str)
    print(f"Shown {displayed_rows} of {len(sorted_meta_rows)}", flush=True)


if __name__ == "__main__":
    parser = ArgumentParser(prog="python review_data.py",
                            description="Console script for review markup with colorization")

    parser.add_argument("meta_dir", help="Markup location", nargs='?', default="meta")
    parser.add_argument("data_dir", help="Dataset location", nargs='?', default="data")
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
    exit_code = main(_args.meta_dir, _args.data_dir, _data_filter, _args.load, _args.category)
    sys.exit(exit_code)

# use review with 'less'
# python review_data.py | less -R
