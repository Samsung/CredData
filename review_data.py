import csv
import json
import os
import subprocess
import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import Dict, List, Optional

from pip._vendor.colorama import Fore, Back, Style
# colorama may be not included in older pip, so install it separately


class Cred:
    def __init__(self, cs_cred: dict):
        self.rule = cs_cred["rule"]
        line_data_list = cs_cred["line_data_list"]
        path = Path(line_data_list[0]["path"])
        self.path = '/'.join([str(x) for x in path.parts[-4:]])
        if not self.path.startswith('data/'):
            # license files ...
            self.path = '/'.join([str(x) for x in path.parts[-3:]])
        assert self.path.startswith('data/'), cs_cred
        self.line_start = line_data_list[0]["line_num"]
        self.line_end = line_data_list[-1]["line_num"]
        self.value_start = line_data_list[0]["value_start"]
        self.value_end = line_data_list[0]["value_end"]
        offset = len(line_data_list[0]["line"]) - len(line_data_list[0]["line"].lstrip())
        self.strip_value_start = self.value_start - offset
        self.strip_value_end = self.value_end - offset


def read_data(path, line_start, line_end, value_start, value_end, ground_truth, creds: List[Cred]):
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
            # replace wrong markup if necessary
            if 'Template' == ground_truth:
                repo_id = path.split('/')[1]
                subprocess.run(
                    ["sed", "-i",
                     f"s|,{path},{line_start}:{line_end},Template,|,{path},{line_start}:{line_end},X,|",
                     f"meta/{repo_id}.csv"])
        if not line_found_in_cred:
            print("Markup was not found in creds in line", flush=True)
            # assert 0

    print("\n\n")


def read_meta(meta_dir, data_dir) -> List[Dict[str, str]]:
    meta = []
    for root, dirs, files in os.walk(meta_dir):
        root_path = Path(root)
        for file in files:
            with open(root_path / file, newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # verify correctness of data
                    file_path = row["FilePath"]
                    if file_path.startswith("data/"):
                        row["FilePath"] = f"{data_dir}/{file_path[5:]}"  # todo: check slicing
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
            creds.extend([Cred(x) for x in json.load(f)])

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
                      creds)
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
    parser.add_argument("-X", help="Show X markup", action="store_true")
    parser.add_argument("--load", help="Load json report from CredSweeper", nargs='?')
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
    exit_code = main(_args.meta_dir, _args.data_dir, _data_filter, _args.load)
    sys.exit(exit_code)

# use review with 'less'
# python review_data.py | less -R
