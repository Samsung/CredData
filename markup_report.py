#!/usr/bin/env python3

"""
The script performs updating CredSweeper report with according markup
currently the row from meta is placed to "api_validation" to keep the value at the position
"""

import json
import os
import sys
from argparse import ArgumentParser
from typing import Dict, List

from meta_cred import MetaCred
from meta_key import MetaKey
from meta_row import MetaRow, read_meta


def prepare_meta(meta_dir) -> Dict[MetaKey, List[MetaRow]]:
    meta_dict = {}
    for meta_row in read_meta(meta_dir):
        meta_key = MetaKey(meta_row)
        if meta_row in meta_dict:
            meta_dict[meta_key].append(meta_row)
        else:
            meta_dict[meta_key] = [meta_row]
    return meta_dict


def main(output_json, meta_dir):
    if not os.path.exists(output_json) or not os.path.isfile(output_json):
        raise FileExistsError(f"{output_json} report does not exist.")
    if not os.path.exists(meta_dir) or not os.path.isdir(meta_dir):
        raise FileExistsError(f"{meta_dir} directory does not exist.")

    with open(output_json, "r") as f:
        creds = json.load(f)

    meta_dict = prepare_meta(meta_dir)

    # processed_creds = []

    for cred in creds:
        meta_cred = MetaCred(cred)
        cred_key = MetaKey(meta_cred.path, meta_cred.line_start, meta_cred.line_end)
        if meta_rows := meta_dict.get(cred_key):
            cred["api_validation"] = ''.join(str(x) for x in meta_rows)
        else:
            cred["api_validation"] = "not found in meta"

    with open(f"{output_json}", "w") as f:
        json.dump(creds, f, indent=4)


if __name__ == "__main__":
    parser = ArgumentParser(prog="python markup_report.py",
                            description="Console script for markup report file from credsweeper")

    parser.add_argument("load_report", help="Load json report from CredSweeper")
    parser.add_argument("meta_dir", help="Markup location", nargs='?', default="meta")

    _args = parser.parse_args()
    exit_code = main(_args.load_report, _args.meta_dir)
    sys.exit(exit_code)
