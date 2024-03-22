import csv
import json
import os
import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import Dict, List


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
        self.line = line_data_list[0]["line"]


# # print all creds we found
# print(f"{cred.rule},{line_start}:{cred.strip_value_start},{cred.strip_value_end}:{Style.RESET_ALL}"
#       f"{line[:cred.value_start]}{Back.LIGHTRED_EX}{line[cred.value_start:cred.value_end]}"
#       f"{Style.RESET_ALL}{line[cred.value_end:]}", flush=True)


def read_meta(meta_dir, data_dir) -> List[Dict[str, str]]:
    meta = []
    for root, dirs, files in os.walk(meta_dir):
        root_path = Path(root)
        for file in files:
            if not file.endswith(".csv"):
                # *.csv.orig artefacts after git merge
                continue
            with open(root_path / file, newline="") as f:
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


def main(output_json, meta_dir, data_dir, data_filter):
    if not os.path.exists(output_json):
        raise FileExistsError(f"{output_json} report does not exist.")
    if not os.path.exists(meta_dir):
        raise FileExistsError(f"{meta_dir} directory does not exist.")
    if not os.path.exists(data_dir):
        raise FileExistsError(f"{data_dir} directory does not exist.")
    creds = []
    with open(output_json, "r") as f:
        creds.extend([Cred(x) for x in json.load(f)])

    meta = read_meta(meta_dir, data_dir)
    # meta.sort(key=lambda x: (x['FilePath'], x['LineStart:LineEnd']))

    grouped_creds = {}

    for cred in creds:
        cred_found_count = 0
        for row in meta:
            file_path = row["FilePath"]
            line_start = row["LineStart"]
            line_end = row["LineEnd"]
            value_start = row["ValueStart"]
            value_end = row["ValueEnd"]
            if file_path == cred.path and line_start == cred.line_start:
                if not data_filter[row["GroundTruth"]]:
                    continue
                row_csv = ','.join([str(x) for x in row.values()])
                cred_found_count += 1
        if 0 == cred_found_count:
            split_path = cred.path.split('/')
            if 4 != len(split_path):
                raise FileExistsError(f"wrong path {cred}")
            repo_id = split_path[1]
            file_id = split_path[3].split('.')[0]
            cred_key = f"{file_id},GitHub,{repo_id},{cred.path},{cred.line_start}:{cred.line_end},F,F,,,F,F,,,,,0,0,F,F,F,"
            # 5369,1f643046,GitHub,0f133e09,data/0f133e09/test/1f643046.txt,10:10,F,F,,,F,F,,,,,0,0,F,F,F,
            if upd_cred := grouped_creds.get(cred_key):
                grouped_creds[cred_key] = f"{cred.rule},{cred.strip_value_start},{cred.strip_value_end} + {upd_cred}"
            else:
                grouped_creds[cred_key] = f"{cred.rule},{cred.strip_value_start},{cred.strip_value_end} \n{cred.line}"

    meta_next_id = 1 + max(int(x["Id"]) for x in meta)
    for k, v in grouped_creds.items():
        if "Password" in v:
            category = "Password"
        elif "Secret" in v:
            category = "Generic Secret"
        elif "Auth" in v:
            category = "Authentication Key & Token"
        elif "Salt" in v or "Token" in v or "Nonce" in v:
            category = '"Seed, Salt, Token"'
        elif "URL Credentials" in v or "API" in v or "Certificate" in v:
            category = 'Predefined Token'
        elif "Key" in v or "Credential" in v:
            category = "Other"
        else:
            category = ""
            print(f"missed: {k}  {v}")
        meta_file = f"meta/{k.split(',')[2]}.csv"
        with open(meta_file, "a") as f:
            f.write(f"{meta_next_id},{k}{category}\n")
            meta_next_id += 1

    print(f"total: {len(grouped_creds)}")


if __name__ == "__main__":
    parser = ArgumentParser(prog="python review_data.py",
                            description="Console script for review markup with colorization")

    parser.add_argument("output", help="Load json report from CredSweeper")
    parser.add_argument("meta_dir", help="Markup location", nargs='?', default="meta")
    parser.add_argument("data_dir", help="Dataset location", nargs='?', default="data")
    parser.add_argument("-T", help="Show TRUE markup", action="store_true")
    parser.add_argument("-F", help="Show FALSE markup", action="store_true")
    parser.add_argument("-t", help="Show Template markup", action="store_true")
    parser.add_argument("-X", help="Show X markup", action="store_true")

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
    exit_code = main(_args.output, _args.meta_dir, _args.data_dir, _data_filter)
    sys.exit(exit_code)

# use review with 'less'
# python review_data.py -t | less -R
