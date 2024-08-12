#!/usr/bin/env python3

"""
The script performs updating CredSweeper report with according markup
currently the row from meta is placed to "api_validation" to keep the value at the position
"""

import json
import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import Dict, List, Tuple

from meta_cred import MetaCred
from meta_row import MetaRow, _get_source_gen


def prepare_meta(meta_dir) -> Dict[Tuple[str, int, int, int, int], List[MetaRow]]:
    meta_dict: Dict[Tuple[str, int, int, int, int], List[MetaRow]] = {}

    for row in _get_source_gen(Path(meta_dir)):
        meta_row = MetaRow(row)
        markup_key = (meta_row.FilePath, meta_row.LineStart, meta_row.LineEnd, meta_row.ValueStart, meta_row.ValueEnd)
        if meta_list := meta_dict.get(markup_key):
            meta_list.append(meta_row)
            meta_dict[markup_key] = meta_list
        else:
            meta_dict[markup_key] = [meta_row]

    return meta_dict


def main(report_file: str, meta_dir: str):
    errors = 0

    with open(report_file, "r") as f:
        creds = json.load(f)

    meta_dict = prepare_meta(meta_dir)

    for cred in creds:
        meta_cred = MetaCred(cred)
        key_variants = [
            # exactly match
            (meta_cred.path, meta_cred.line_start, meta_cred.line_end, meta_cred.value_start, meta_cred.value_end),
            # meta markup only with start position
            (meta_cred.path, meta_cred.line_start, meta_cred.line_end, meta_cred.value_start, -1),
            # markup for whole line
            (meta_cred.path, meta_cred.line_start, meta_cred.line_end, -1, -1)
        ]
        for key in key_variants:
            if rows := meta_dict.get(key):
                cred["api_validation"] = ';'.join(str(x) for x in rows)
                break
        else:
            cred["api_validation"] = "not found in meta"
            # something was wrong
            errors += 1

    with open(f"{report_file}", "w") as f:
        json.dump(creds, f, indent=4)

    return errors


if __name__ == "__main__":
    parser = ArgumentParser(prog="python markup_report.py",
                            description="Console script for markup report file from credsweeper")

    parser.add_argument("load_report", help="Load json report from CredSweeper")
    parser.add_argument("meta_dir", help="Markup location", nargs='?', default="meta")

    _args = parser.parse_args()
    exit_code = main(_args.load_report, _args.meta_dir)
    sys.exit(exit_code)
