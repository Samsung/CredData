#!/usr/bin/env python3

"""
The script generates ascii text with colorization only for markup lines
RED - false cases
GREEN - true
MAGENTA - templates
When value start-end defined - the text is marked
"""
import functools
import json
import os
import pathlib
import subprocess
import sys
from argparse import ArgumentParser
from typing import List, Optional, Tuple, Dict

from colorama import Fore, Back, Style

from constants import LABEL_OTHER, LABEL_FALSE, LABEL_TRUE, OTHER_CATEGORY, MULTI_LINE_RULES
from meta_cred import MetaCred
from meta_row import read_meta, MetaRow

EXIT_SUCCESS = 0
EXIT_FAILURE = 1

HUNK_SIZE = 120


@functools.cache
def get_excluding_extensions() -> set[str]:
    # copy of CredSweeper/secret/config.json
    with open("config.json") as f:
        result = json.load(f)
    return set(result["exclude"]["containers"] + result["exclude"]["documents"] + result["exclude"]["extension"])


@functools.cache
def read_cache(path) -> list[str]:
    with open(path, "r", encoding="utf8") as f:
        return f.read().replace("\r\n", '\n').replace('\r', '\n').split('\n')


def read_data(path: str,
              line_start: int,
              line_end: int,
              value_start: int,
              value_end: int,
              ground_truth: str,
              short_line: bool,
              creds: List[MetaCred]):
    lines = read_cache(path)
    if line_start == line_end:
        data_line = lines[line_start - 1]
        multiline_end_offset = 0
    elif line_start < line_end:
        data_line = '\n'.join(lines[line_start - 1:line_end])
        multiline_end_offset = len(data_line) - len(lines[line_end - 1])
    else:
        raise RuntimeError(f"Line start must be less than end. {path},{line_start},{line_end}")

    if LABEL_TRUE == ground_truth:
        fore_style = Fore.GREEN
    elif LABEL_FALSE == ground_truth:
        fore_style = Fore.RED
    elif LABEL_OTHER == ground_truth:
        fore_style = Fore.MAGENTA
    else:
        raise RuntimeError(f"Unknown type {ground_truth}")

    line_found_in_cred = False
    correct_value_position = False
    if creds:
        # only if review with credsweeper report
        for cred in creds:
            if cred.path == path:
                if line_start == cred.line_start and line_end == cred.line_start:
                    line_found_in_cred = True
                    # print all creds we found
                    colored_line = data_line[:cred.value_start] \
                                   + Fore.LIGHTYELLOW_EX \
                                   + data_line[cred.value_start:cred.value_end] \
                                   + Style.RESET_ALL \
                                   + data_line[cred.value_end:]
                    if 0 <= cred.variable_start and 0 <= cred.variable_end:
                        # variable is before value, so the line positions is untouched
                        colored_line = colored_line[:cred.variable_start] \
                                       + Fore.LIGHTBLUE_EX \
                                       + colored_line[cred.variable_start:cred.variable_end] \
                                       + Style.RESET_ALL \
                                       + colored_line[cred.variable_end:]
                    print(
                        f"{cred.rule},{line_start}:{cred.value_start},{cred.value_end}:{Style.RESET_ALL}"
                        + colored_line, flush=True)
                    if 0 <= value_start == cred.value_start and 0 <= value_end == cred.value_end:
                        correct_value_position = True
                    elif 0 <= value_start == cred.value_start:
                        correct_value_position = True
                    elif 0 > value_start:
                        # full line
                        correct_value_position = True
    else:
        line_found_in_cred = True
        correct_value_position = True

    if short_line:
        text_start = value_start - HUNK_SIZE if 0 < value_start - HUNK_SIZE else 0
        if 0 <= value_end and value_start <= multiline_end_offset + value_end:
            text_end = multiline_end_offset + value_end + HUNK_SIZE \
                if len(data_line) > multiline_end_offset + value_end + HUNK_SIZE \
                else len(data_line)
        elif value_end < 0 <= value_start:
            text_end = multiline_end_offset + value_start + HUNK_SIZE \
                if len(data_line) > multiline_end_offset + value_start + HUNK_SIZE \
                else len(data_line)
        elif 0 > value_start >= value_end:
            text_start = 0
            text_end = HUNK_SIZE if len(data_line) > HUNK_SIZE else len(data_line)
        else:
            raise ValueError(f"Cannot show {value_start} {value_end}")
    else:
        text_start = 0
        text_end = len(data_line)

    if line_start == line_end and 0 <= value_start <= value_end \
            or line_start < line_end and 0 <= value_start and 0 <= value_end:
        line = data_line[text_start:value_start] \
               + Back.LIGHTYELLOW_EX \
               + data_line[value_start:value_end + multiline_end_offset] \
               + Style.RESET_ALL \
               + fore_style \
               + data_line[value_end + multiline_end_offset:text_end]
    elif value_end < 0 <= value_start:
        line = data_line[text_start:value_start] \
               + Style.BRIGHT \
               + data_line[value_start:text_end]
    else:
        line = data_line[text_start:text_end]
    back_start_style = Back.LIGHTYELLOW_EX if Back.LIGHTYELLOW_EX in line else Style.RESET_ALL
    if line_start < line_end:
        line.replace('\n', Style.RESET_ALL + '\n' + fore_style + back_start_style)
    if '\n' in line:
        for n, i in enumerate(line.split('\n')):
            start_style = Style.RESET_ALL if 0 == n else back_start_style
            print(f"{n + line_start}:{start_style}{fore_style}{i}{Style.RESET_ALL}", flush=True)
    else:
        print(f"{line_start}:{Style.RESET_ALL}{fore_style}{line}{Style.RESET_ALL}", flush=True)
    if not correct_value_position:
        print("Possible wrong value markup", flush=True)
    if not line_found_in_cred:
        # todo: an activity to fine-tune markup
        print("Markup was not found in creds in line", flush=True)
        test_line = data_line.lower()
        if not any(
                x in test_line for x in
                ["api", "pass", "secret", "pw", "key", "credential", "token", "auth", "nonce", "salt"]
        ):
            repo_id = path.split('/')[1]
            subprocess.check_call(
                ["sed", "-i",
                 f"/.*{path.split('/')[-1]},{line_start},{line_end},.*/d",
                 f"meta/{repo_id}.csv"])

    print("\n\n", flush=True)


def review(meta_dir: str,
           data_dir: str,
           short_line: bool,
           check_only: bool,
           data_filter: dict,
           category: Optional[str] = None,
           load_json: Optional[str] = None,
           ) -> int:
    errors = 0
    duplicates = 0
    if not os.path.exists(meta_dir):
        raise FileExistsError(f"{meta_dir} directory does not exist.")
    if not os.path.exists(data_dir) and not check_only:
        raise FileExistsError(f"{data_dir} directory does not exist.")
    creds = []
    if load_json:
        with open(load_json, "r") as f:
            creds.extend([MetaCred(x) for x in json.load(f)])

    meta = read_meta(meta_dir)
    meta.sort(key=lambda x: (x.FilePath, x.LineStart, x.LineEnd, x.ValueStart, x.ValueEnd))
    displayed_rows = 0
    shown_whole_line: Dict[Tuple[str, int], MetaRow] = {}
    shown_markup: Dict[Tuple[str, int, int, int, int], MetaRow] = {}
    for row in meta:
        if not data_filter[row.GroundTruth]:
            continue
        if category and category not in row.Category.split(':'):
            continue

        if pathlib.Path(row.FilePath).suffix in get_excluding_extensions():
            # the file extension will be excluded during default scan
            print(f"File {row.FilePath} is excluded by default config with extension filter!", flush=True)
            errors += 1

        displayed_rows += 1
        if not check_only:
            print(str(row), flush=True)
            try:
                read_data(path=row.FilePath,
                          line_start=row.LineStart,
                          line_end=row.LineEnd,
                          value_start=row.ValueStart,
                          value_end=row.ValueEnd,
                          ground_truth=row.GroundTruth,
                          short_line=short_line,
                          creds=creds,
                          )
            except Exception as exc:
                print(f"Failure {row}", exc, flush=True)
                errors += 1
        if LABEL_TRUE == row.GroundTruth and row.LineStart == row.LineEnd:
            if 0 > row.ValueStart:
                print(f"Missed ValueStart for TRUE markup!\n{row}", flush=True)
                errors += 1
            if 0 < row.ValueEnd:
                categories = row.Category.split(':')
                min_length = 6
                if any(x in categories for x in ["Key"]) and 1 == len(categories):
                    min_length = 8
                if any(x in categories for x in ["Auth", "Token", "Salt", "Nonce"]):
                    # Secrets are like passwords
                    min_length = 8
                if any(x in categories for x in ["Secret", "CMD ConvertTo-SecureString"]):
                    # Secrets are like passwords
                    min_length = 5
                if any(x in categories for x in ["Password", "URL Credentials", "CMD Password", "SQL Password",
                                                 "CURL User Password"]):
                    # lost password may be simple but sensitive
                    min_length = 4
                if min_length > row.ValueEnd - row.ValueStart:
                    print(f"Too short {min_length} > {row.ValueEnd - row.ValueStart} value for TRUE markup!\n{row}",
                          flush=True)
                    errors += 1
            if 0 < row.ValueEnd and "Password" in row.Category and 64 < row.ValueEnd - row.ValueStart:
                print(f"Too long for Password TRUE markup!\n{row}", flush=True)
                errors += 1

        if row.LineStart != row.LineEnd and not any(x in row.Category.split(':') for x in MULTI_LINE_RULES):
            print(f"Check multiline markup - may be not suitable for the category!\n{row}", flush=True)
            errors += 1

        if row.FileID not in row.FilePath:
            print(f"FileID error!\n{row}", flush=True)
            errors += 1
        if row.RepoName not in row.FilePath:
            print(f"RepoName error!\n{row}", flush=True)
            errors += 1

        # collects all lines without start value positions - whole line
        if row.LineStart == row.LineEnd and -1 == row.ValueStart:
            whole_line_key = (row.FilePath, row.LineStart)
            if whole_line_key in shown_whole_line:
                print(f"Duplicate line markup!\nSHOWN:{shown_whole_line[whole_line_key]}\nTHIS:{row}", flush=True)
                duplicates += 1
            else:
                shown_whole_line[whole_line_key] = row

        markup_key = (row.FilePath, row.LineStart, row.LineEnd, row.ValueStart, row.ValueEnd)
        if markup_key in shown_markup:
            print(f"Duplicate markup!\nSHOWN:{shown_markup[markup_key]}\nTHIS:{row}", flush=True)
            duplicates += 1
        else:
            shown_markup[markup_key] = row
    for row in shown_markup.values():
        if row.LineStart == row.LineEnd and 0 <= row.ValueStart and (row.FilePath, row.LineStart) in shown_whole_line:
            print(f"Duplicate whole line!\n{row}", flush=True)
            duplicates += 1

    result = EXIT_SUCCESS if 0 == duplicates == errors else EXIT_FAILURE
    print(f"Shown {displayed_rows} of {len(meta)}, errors: {errors}, duplicates: {duplicates}, {result}", flush=True)
    return result


def main(argv) -> int:
    parser = ArgumentParser(prog="python review_data.py",
                            description="Console script for review markup with colorization")

    parser.add_argument("meta_dir", help="Markup location", nargs='?', default="meta")
    parser.add_argument("data_dir", help="Dataset location", nargs='?', default="data")
    parser.add_argument("--short_line", help="Reduce huge line in review", action='store_true')
    parser.add_argument("--check_only", help="Check meta markup only", action='store_true')
    parser.add_argument("-T", help="Show TRUE markup", action="store_true")
    parser.add_argument("-F", help="Show FALSE markup", action="store_true")
    parser.add_argument("-X", help="Show X markup", action="store_true")
    parser.add_argument("--load", help="Load json report from CredSweeper", nargs='?')
    parser.add_argument("--category", help="Filter only with the category", nargs='?')
    _args = parser.parse_args(argv[1:])

    _data_filter = {OTHER_CATEGORY: False}
    if not _args.T and not _args.F and not _args.X:
        _data_filter["T"] = True
        _data_filter["F"] = True
        _data_filter["X"] = True
    else:
        _data_filter["T"] = _args.T
        _data_filter["F"] = _args.F
        _data_filter["X"] = _args.X
    return review(meta_dir=_args.meta_dir,
                  data_dir=_args.data_dir,
                  short_line=bool(_args.short_line),
                  check_only=bool(_args.check_only),
                  data_filter=_data_filter,
                  load_json=_args.load,
                  category=_args.category)


if __name__ == """__main__""":
    sys.exit(main(sys.argv))

# review generation command
# .venv/bin/python review_data.py meta data >review.$(now).$(git rev-parse HEAD).txt

# use review with 'less'
# python review_data.py | less -R
