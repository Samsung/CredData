#!/usr/bin/env python3

"""
The script updates dataset with rules
Run the script with report obtained without ML and filters
"""
import copy
import json
import os
import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import Tuple, Dict, List

from meta_cred import MetaCred
from meta_row import MetaRow, _get_source_gen


def prepare_meta(meta_dir) -> Dict[Tuple[str, int, int], List[MetaRow]]:
    meta_dict = {}

    for row in _get_source_gen(Path(meta_dir)):
        meta_row = MetaRow(row)
        meta_key = (meta_row.FilePath, meta_row.LineStart, meta_row.LineEnd)
        if meta_list := meta_dict.get(meta_key):
            meta_list.append(meta_row)
            meta_dict[meta_key] = meta_list
        else:
            meta_dict[meta_key] = [meta_row]

    return meta_dict


def main(output_json, meta_dir):
    if not os.path.exists(output_json) or not os.path.isfile(output_json):
        raise FileExistsError(f"{output_json} report does not exist.")
    if not os.path.exists(meta_dir) or not os.path.isdir(meta_dir):
        raise FileExistsError(f"{meta_dir} directory does not exist.")

    meta_dict = prepare_meta(meta_dir)
    next_meta_id = 1 + max(max(y.Id for y in x) for x in meta_dict.values())

    with open(output_json, "r") as f:
        creds = json.load(f)
    incorrect = 0
    notfound = 0
    for cred in creds:
        meta_cred = MetaCred(cred)
        cred_line_key = (meta_cred.path, meta_cred.line_start, meta_cred.line_end)
        meta_list = meta_dict.get(cred_line_key)
        if not meta_list:
            notfound += 1
            print(f"not found {str(cred)}")
            continue
        if 1 == len(meta_list):
            m = copy.deepcopy(meta_list[0])
            if m.LineStart == m.LineEnd and m.ValueStart >= 0 and m.ValueStart != meta_cred.strip_value_start \
                    and 1 == len(cred["line_data_list"]):
                # one line markup
                print(f"check\n{str(meta_cred)}\n{chr(0x0A).join(str(x) for x in meta_list)}\n\n")
                # if "IPv4" == meta_cred.rule:
                #     subprocess.run(
                #         ["sed", "-i",
                #          "s|"
                #          f"{m.FilePath},{m.LineStart},{m.LineEnd},{m.GroundTruth},{m.WithWords},,"
                #          "|"
                #          f"{m.FilePath},{m.LineStart},{m.LineEnd},{m.GroundTruth},{m.WithWords},{meta_cred.strip_value_start},"
                #          "|",
                #          f"meta/{m.RepoName}.csv"])
                m.ValueStart = meta_cred.strip_value_start
                m.ValueEnd = meta_cred.strip_value_end
                m.Category = meta_cred.rule
                m.GroundTruth = 'T'  # to be obfuscated
                m.Id = next_meta_id
                next_meta_id += 1
                with open(f"meta/{m.RepoName}.csv", "a") as f:
                    f.write(f"{str(m)}\n")
                incorrect += 1
                meta_list.append(m)
        elif 1 < len(meta_list):
            print(f"Multiple markup \n{str(meta_cred)}\n{chr(0x0A).join(str(x) for x in meta_list)}\n\n")
            # for i in meta_list:
            #     if i.LineStart == meta_cred.line_start and i.LineEnd == meta_cred.line_end:
            #         if i.ValueStart == meta_cred.strip_value_start:
            #             i.Category = meta_cred.rule
            #             break
            #         # , \                    f"{cred},\n{chr(0x0A).join(str(x) for x in meta_list)}"
            # else:
            #     notfound += 1
            #     m = copy.deepcopy(meta_list[0])
            #     m.ValueStart = meta_cred.strip_value_start
            #     m.ValueEnd = meta_cred.strip_value_end
            #     m.Category = meta_cred.rule
            #     m.Id = next_meta_id
            #     next_meta_id += 1
            #     if meta_cred.rule.startswith("IP"):
            #         m.PredefinedPattern = "Info"
            #     else:
            #         m.GroundTruth = 'F'
            #     with open(f"meta/{m.RepoName}.csv", "a") as f:
            #         f.write(f"{str(m)}\n")
            #     meta_list.append(m)
            #     print(f"not found\n{str(meta_cred)}\n{chr(0x0A).join(str(x) for x in meta_list)}\n\n")
        else:
            raise RuntimeError(str(cred))
    print(f"not found {notfound} incorrect {incorrect}")
    return 0


if __name__ == "__main__":
    parser = ArgumentParser(prog="python update_meta.py",
                            description="Console script for update dataset category with rules list")

    parser.add_argument("load_report", help="Load json report from CredSweeper")
    parser.add_argument("meta_dir", help="Markup location", nargs='?', default="meta")

    _args = parser.parse_args()
    exit_code = main(_args.load_report, _args.meta_dir)
    sys.exit(exit_code)
