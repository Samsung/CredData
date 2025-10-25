#!/usr/bin/env python3

"""
The script performs updating CredSweeper report with according markup
currently the row from meta is placed to "ml_validation" to keep the value at the position
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

from meta_cred import MetaCred
from meta_row import MetaRow, _get_source_gen


def prepare_meta(meta_dir: Path) -> Dict[Tuple[str, int, int, int, int], List[MetaRow]]:
    meta_dict: Dict[Tuple[str, int, int, int, int], List[MetaRow]] = {}

    for row in _get_source_gen(meta_dir):
        meta_row = MetaRow(row)
        markup_key = (meta_row.FilePath, meta_row.LineStart, meta_row.LineEnd, meta_row.ValueStart, meta_row.ValueEnd)
        if meta_list := meta_dict.get(markup_key):
            meta_list.append(meta_row)
            meta_dict[markup_key] = meta_list
        else:
            meta_dict[markup_key] = [meta_row]

    return meta_dict


def markup(report_file: Path, meta_dir: Path):
    errors = 0

    with open(report_file) as f:
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
                # to easy review true/false/template
                cred["severity"] = ';'.join(x.GroundTruth for x in rows)
                # full info will be placed above "line_data_list"
                cred["confidence"] = ';'.join(str(x) for x in rows)
                break
        else:
            cred["confidence"] = "not found in meta"
            # something was wrong
            errors += 1

    with open(report_file, mode='w') as f:
        json.dump(creds, f, indent=4)

    return errors


def main(argv) -> int:
    meta_dir = Path(__file__).parent / "meta"
    reports = []
    for n, arg in enumerate(argv[1:]):
        arg_path = Path(arg)
        if arg_path.is_dir() and arg_path.exists():
            print(f"Use specific meta dir: {arg_path}", flush=True)
            meta_dir = arg_path
        elif arg_path.is_file() and arg_path.exists():
            reports.append(arg_path)
        else:
            print(f"Unrecognized {n + 1} argument: '{arg}'", flush=True)
    if not (meta_dir.is_dir() and meta_dir.exists()):
        print(f"Not exists meta dir: '{meta_dir.absolute()}'", flush=True)
        return 1
    error_code = os.EX_OK
    for report_file in reports:
        try:
            if errors := markup(report_file, meta_dir):
                print(f"{errors} candidates were not found in {meta_dir} markup", flush=True)
                error_code = 1
        except Exception as exc:
            print(f"{report_file} - failure: {exc}")
            error_code = 1
    return error_code

if __name__ == "__main__":
    sys.exit(main(sys.argv))
