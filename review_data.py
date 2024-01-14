import csv
import json
import os
import pathlib
import subprocess
import sys
from argparse import ArgumentParser
from typing import Dict, List, Optional

from colorama import Fore, Back, Style


def read_data(path, line_start, line_end, value_start, value_end, ground_truth, creds: Optional[List[dict]]):
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
        else:
            raise RuntimeError(f"Unknown type {ground_truth}")
        stripped_line = line.lstrip()
        offset = len(line) - len(stripped_line)

        line_found_in_cred = False
        correct_value_position = False
        if creds is not None:
            for i in creds:
                cred_path: str = i["line_data_list"][0]["path"]
                if cred_path.endswith(path):
                    cred_line_num = i["line_data_list"][0]["line_num"]
                    if line_start == cred_line_num:
                        line_found_in_cred = True
                        cred_value_start = i["line_data_list"][0]["value_start"]
                        strip_cred_value_start = cred_value_start - offset
                        cred_value_end = i["line_data_list"][0]["value_end"]
                        strip_cred_value_end = cred_value_end - offset
                        if 0 < value_start and value_start == strip_cred_value_start and value_end == strip_cred_value_end:
                            correct_value_position = True
                            break
                        else:
                            # print credentials found markup in the same line
                            print(f"{line_start}:{strip_cred_value_start},{strip_cred_value_end}:{Style.RESET_ALL}"
                                  f"{line[:cred_value_start]}{Fore.BLUE}{line[cred_value_start:cred_value_end]}"
                                  f"{Style.RESET_ALL}{line[cred_value_end:]}", flush=True)
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
            print("Markup was not found in creds in line", flush=True)
    print("\n\n")


def read_meta(meta_dir, data_dir) -> List[Dict[str, str]]:
    meta = []
    for root, dirs, files in os.walk(meta_dir):
        for file in files:
            with open(pathlib.Path(root) / file, newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # verify correctness of data
                    file_path = row["FilePath"]
                    if file_path.startswith("data/"):
                        row["FilePath"] = f"{data_dir}/{file_path[5:]}"
                    elif file_path.startswith("/"):
                        pass  # keep as is - absolute path
                    else:
                        raise RuntimeError(f"Invalid path:", row)
                    line_start, line_end = row["LineStart:LineEnd"].split(':')
                    row["LineStart"] = int(line_start) if line_start else -1
                    row["LineEnd"] = int(line_end) if line_end else -1
                    assert row["LineStart"] <= row["LineEnd"], row
                    value_start = row["ValueStart"]
                    row["ValueStart"] = int(float(value_start)) if value_start else -1
                    value_end = row["ValueEnd"]
                    row["ValueEnd"] = int(float(value_end)) if value_end else -1
                    meta.append(row)
    return meta


def main(meta_dir, data_dir, data_filter, load_json: Optional[str] = None):
    if not os.path.exists(meta_dir):
        raise FileExistsError(f"{meta_dir} directory does not exist.")
    if not os.path.exists(data_dir):
        raise FileExistsError(f"{data_dir} directory does not exist.")
    creds = []
    if load_json:
        with open(load_json, "r") as f:
            creds.extend(json.load(f))

    meta = read_meta(meta_dir, data_dir)
    meta.sort(key=lambda x: (x['FilePath'], x['LineStart:LineEnd']))
    displayed_rows = 0
    shown_rows = set()
    for row in meta:
        if not data_filter[row["GroundTruth"]]:
            continue

        displayed_rows += 1
        row_csv = ','.join([str(x) for x in row.values()])
        print(row_csv, flush=True)
        try:
            file_path = str(row["FilePath"])
            line_start = int(row["LineStart"])
            line_end = int(row["LineEnd"])
            value_start = int(row["ValueStart"])
            value_end = int(row["ValueEnd"])
            read_data(file_path,
                      line_start,
                      line_end,
                      value_start,
                      value_end,
                      row["GroundTruth"],
                      creds if load_json else None)
        except Exception as exc:
            print(f"Failure {row}", exc, flush=True)
            raise
        row_str = f"{file_path},{line_start}:{line_end}"
        if row_str in shown_rows:
            print(f"Duplicate row {row}", flush=True)
            break
        else:
            shown_rows.add(row_str)
    print(f"Shown {displayed_rows} of {len(meta)}", flush=True)


if __name__ == "__main__":
    parser = ArgumentParser(prog="python review_data.py",
                            description="Console script for review markup with colorization")

    parser.add_argument("meta_dir", help="Markup location", nargs='?', default="meta")
    parser.add_argument("data_dir", help="Dataset location", nargs='?', default="data")
    parser.add_argument("-T", help="Show TRUE markup", action="store_true")
    parser.add_argument("-F", help="Show FALSE markup", action="store_true")
    parser.add_argument("-t", help="Show Template markup", action="store_true")
    parser.add_argument("--load", help="Load json report from CredSweeper", nargs='?')
    _args = parser.parse_args()

    _data_filter = {"Other": False}
    if not _args.T and not _args.F and not _args.t:
        _data_filter["T"] = True
        _data_filter["F"] = True
        _data_filter["Template"] = True
    else:
        _data_filter["T"] = _args.T
        _data_filter["F"] = _args.F
        _data_filter["Template"] = _args.t
    exit_code = main(_args.meta_dir, _args.data_dir, _data_filter, _args.load)
    sys.exit(exit_code)

# use review with 'less'
# python review_data.py -t | less -R

