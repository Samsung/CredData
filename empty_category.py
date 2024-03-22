import csv
import os
import re
import subprocess
import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import Dict, List

# colorama may be not included in older pip, so install it separately

secret_line = re.compile("[\w_/+-]{31,80}")


def process_line(row):
    line_start, line_end = row["LineStart:LineEnd"].split(':')
    line_start = int(line_start) if line_start else -1
    line_end = int(line_end) if line_end else -1
    assert line_start <= line_end, row
    # value_start = row["ValueStart"]
    # row["ValueStart"] = int(float(value_start)) if value_start else -1
    # value_end = row["ValueEnd"]
    # row["ValueEnd"] = int(float(value_end)) if value_end else -1
    file_path = str(row["FilePath"])
    repo_id = file_path.split('/')[1]
    row_csv = ','.join([str(x) for x in row.values()])
    with open(file_path, "r", encoding="utf8") as f:
        lines = f.readlines()
        if line_start == line_end:
            line = lines[line_start - 1]
        else:
            line = ''.join(lines[line_start - 1:line_end])
        lower_stripped_line = line.lstrip().lower()
    if any(x in lower_stripped_line for x in ["password", "pass", "pwd"]):
        category = "Password"
    elif "token" in lower_stripped_line:
        category = "Generic Token"
    elif any(x in lower_stripped_line for x in ["seed", "salt", "nonce"]):
        category = '"Seed, Salt, Nonce"'
    elif any(x in lower_stripped_line for x in ["secret", "key", "integrity", "secure"]) or secret_line.search(
            line):
        category = "Generic Secret"
    elif any(x in lower_stripped_line for x in ["eyj", "api"]):
        category = "Predefined Pattern"
    elif any(x in lower_stripped_line for x in ["auth", "cookie"]):
        category = "Authentication Key \\& Token"
    elif True or any(x in lower_stripped_line for x in
                     ["login", "user", "name", "email", "nideshop_comment", "string: !!binary", "body: !!binary",
                      "rfc",
                      "iso"]):
        row_csv_d = row_csv.replace('/', '\/')
        subprocess.run(
            ["sed", "-i",
             f"/{row_csv_d}/d",
             f"meta/{repo_id}.csv"])
        return
    else:
        print(row, '\n', line)
        return
    subprocess.run(
        ["sed", "-i",
         f"s|{row_csv}|{row_csv}{category}|",
         f"meta/{repo_id}.csv"])


def process_multilines(row):
    line_start, line_end = row["LineStart:LineEnd"].split(':')
    line_start = int(line_start) if line_start else -1
    line_end = int(line_end) if line_end else -1
    assert line_start <= line_end, row
    file_path = str(row["FilePath"])
    repo_id = file_path.split('/')[1]
    row_csv = ','.join([str(x) for x in row.values()])
    with open(file_path, "r", encoding="utf8") as f:
        lines = f.readlines()
        line = ''.join(lines[line_start - 1:line_end])
    if "-----BEGIN" in line:
        category = "Private Key"
    elif False:
        row_csv_d = row_csv.replace('/', '\/')
        subprocess.run(
            ["sed", "-i",
             f"/{row_csv_d}/d",
             f"meta/{repo_id}.csv"])
        return
    else:
        category = "Other"
    subprocess.run(
        ["sed", "-i",
         f"s|{row_csv}|{row_csv}{category}|",
         f"meta/{repo_id}.csv"])


def read_meta(meta_dir, data_dir) -> List[Dict[str, str]]:
    meta = []
    ids = set()
    dups = []
    for root, dirs, files in os.walk(meta_dir):
        root_path = Path(root)
        for file in files:
            if 12 != len(file) or not all('0' <= x <= '9' or 'a' <= x <= 'f' for x in file[:8]):
                # git garbage case
                continue
            with open(root_path / file, newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    assert 22 == len(row), row
                    # verify correctness of data
                    file_path = row["FilePath"]
                    if file_path.startswith("data/"):
                        row["FilePath"] = f"{data_dir}/{file_path[5:]}"  # todo: check slicing
                    elif file_path.startswith("/"):
                        pass  # keep as is - absolute path
                    else:
                        raise RuntimeError(f"Invalid path:", row)
                    meta.append(row)
                    if row["Id"] in ids:
                        row_csv = ','.join([str(x) for x in row.values()])
                        dups.append(row_csv)
                        print(f"Check id duplication: {row_csv}")
                    else:
                        ids.add(row["Id"])
    assert not dups, '\n'.join(dups)
    return meta


def main(meta_dir, data_dir):
    if not os.path.exists(meta_dir):
        raise FileExistsError(f"{meta_dir} directory does not exist.")
    if not os.path.exists(data_dir):
        raise FileExistsError(f"{data_dir} directory does not exist.")

    meta = read_meta(meta_dir, data_dir)
    # meta.sort(key=lambda x: (x['FilePath'], x['LineStart:LineEnd']))
    for row in meta:
        if row["Category"]:
            # process only empty categories
            continue
        # assume, there only false types left
        assert row["GroundTruth"] == "F", row
        try:
            line_start, line_end = row["LineStart:LineEnd"].split(':')
            # if line_end == line_start:
            # process_line(row)
            if line_end != line_start:
                process_multilines(row)
        except Exception as exc:
            print(f"Failure {row}", exc, flush=True)
            raise


if __name__ == "__main__":
    parser = ArgumentParser(prog="python review_data.py",
                            description="Console script for review markup with colorization")

    parser.add_argument("meta_dir", help="Markup location", nargs='?', default="meta")
    parser.add_argument("data_dir", help="Dataset location", nargs='?', default="data")
    _args = parser.parse_args()

    exit_code = main(_args.meta_dir, _args.data_dir)
    sys.exit(exit_code)
