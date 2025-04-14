import binascii
import contextlib
import hashlib
import os
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Tuple, Dict, List, Any

import tabulate

from benchmark.common import GitService, LineStatus, Result, ScannerType
from benchmark.scanner.file_type_stat import FileTypeStat
from benchmark.scanner.true_false_counter import TrueFalseCounter
from meta_key import MetaKey
from meta_row import _get_source_gen, MetaRow


class Scanner(ABC):
    def __init__(self, scanner_type: ScannerType, scanner_url: str, working_dir: str, cred_data_dir: str,
                 preload: bool, fix: bool) -> None:
        self.scanner_type = scanner_type
        self.scanner_dir: str = GitService.set_scanner_up_to_date(working_dir, scanner_url, preload)
        self.cred_data_dir: str = cred_data_dir
        self.fix = fix
        self.line_checker: set = set()
        self.result_cnt: int = 0
        self.lost_cnt: int = 0
        self.true_cnt: int = 0
        self.false_cnt: int = 0
        self.result_dict: dict = {}
        self.total_true_cnt = 0
        self.total_false_cnt = 0
        self.total_template_cnt = 0
        self.rules_markup_counters: Dict[str, Tuple[int, int, int]] = {}  # category: true_cnt, false_cnt, template_cnt
        self.meta_next_id = 0  # used in suggestion
        self.file_types: Dict[str, FileTypeStat] = {}
        self.total_data_valid_lines = 0
        self.meta: Dict[MetaKey, List[MetaRow]] = {}
        self.reported: Dict[str, int] = {}  # counter of reported credentials by rules
        self._prepare_meta()

    @property
    @abstractmethod
    def output_dir(self) -> str:
        raise NotImplementedError()

    @output_dir.setter
    @abstractmethod
    def output_dir(self, output_dir: str) -> None:
        raise NotImplementedError()

    @staticmethod
    def _meta_checksum(meta_location) -> str:
        checksum = hashlib.md5(b'').digest()
        for root, dirs, files in os.walk(meta_location):
            for file in files:
                with open(os.path.join(root, file), "rb") as f:
                    cvs_checksum = hashlib.md5(f.read()).digest()
                checksum = bytes(a ^ b for a, b in zip(checksum, cvs_checksum))
        return binascii.hexlify(checksum).decode()

    def _prepare_meta(self):
        meta_path = Path(f"{self.cred_data_dir}/meta")
        for _row in _get_source_gen(meta_path):
            meta_row = MetaRow(_row)
            meta_key = MetaKey(meta_row)
            if meta_rows := self.meta.get(meta_key):
                meta_rows.append(meta_row)
            else:
                self.meta[meta_key] = [meta_row]
            # get file extension like in CredSweeper
            _, file_type = os.path.splitext(meta_row.FilePath)
            file_type_lower = file_type.lower()
            type_stat = self.file_types.get(file_type_lower, FileTypeStat(0, 0, 0, 0, 0))
            rules = meta_row.Category.split(':')
            for rule in rules:
                true_cnt, false_cnt, template_cnt = self.rules_markup_counters.get(rule, (0, 0, 0))
                if 'T' == meta_row.GroundTruth:
                    true_cnt += 1
                    self.total_true_cnt += 1
                    type_stat.true_markup += 1
                elif 'F' == meta_row.GroundTruth:
                    self.total_false_cnt += 1
                    false_cnt += 1
                    type_stat.false_markup += 1
                else:
                    # "Template" - correctness will be checked in MetaRow
                    self.total_template_cnt += 1
                    template_cnt += 1
                    type_stat.template_markup += 1
                self.rules_markup_counters[rule] = (true_cnt, false_cnt, template_cnt)
            self.file_types[file_type_lower] = type_stat
            if self.meta_next_id <= meta_row.Id:
                self.meta_next_id = meta_row.Id + 1

        data_checksum = hashlib.md5(b'').digest()
        # getting count of all not-empty lines
        data_dir = f"{self.cred_data_dir}/data"
        for root, dirs, files in os.walk(data_dir):
            for file in files:
                file_name, file_ext = os.path.splitext(str(file))
                file_ext_lower = file_ext.lower()
                file_type_stat = self.file_types.get(file_ext_lower, FileTypeStat(0, 0, 0, 0, 0))
                file_type_stat.files_number += 1
                self.file_types[file_ext_lower] = file_type_stat
                with open(os.path.join(root, file), "rb") as f:
                    data = f.read()
                    file_checksum = hashlib.md5(data).digest()
                    data_checksum = bytes(a ^ b for a, b in zip(data_checksum, file_checksum))
                    with contextlib.suppress(UnicodeDecodeError):
                        lines = data.decode().replace("\r\n", '\n').replace('\r', '\n').split('\n')
                        file_data_valid_lines = 0
                        for line in lines:
                            # minimal length of detection is 7 e.g. pw:X3d!
                            if 7 <= len(line.strip()):
                                file_data_valid_lines += 1
                        self.total_data_valid_lines += file_data_valid_lines
                        self.file_types[file_ext_lower].valid_lines += file_data_valid_lines

        print(f"META MD5 {self._meta_checksum(meta_path)}", flush=True)
        print(f"DATA MD5 {binascii.hexlify(data_checksum).decode()}", flush=True)
        print(f"DATA: {self.total_data_valid_lines} interested lines. MARKUP: {len(self.meta)} items", flush=True)
        types_headers = ["FileType", "FileNumber", "ValidLines", "Positives", "Negatives", "Templates"]
        types_rows = []
        check_files_number = 0
        check_data_valid_lines = 0
        check_true_cnt = 0
        check_false_cnt = 0
        check_template_cnt = 0
        for key, val in self.file_types.items():
            types_rows.append([key,
                               val.files_number or None,
                               val.valid_lines or None,
                               val.true_markup or None,
                               val.false_markup or None,
                               val.template_markup or None])
            check_files_number += val.files_number
            check_data_valid_lines += val.valid_lines
            check_true_cnt += val.true_markup
            check_false_cnt += val.false_markup
            check_template_cnt += val.template_markup
        types_rows.sort()
        types_rows.append(["TOTAL:",
                           check_files_number,
                           check_data_valid_lines,
                           check_true_cnt,
                           check_false_cnt,
                           check_template_cnt])
        print(tabulate.tabulate(types_rows, types_headers), flush=True)

    @property
    def scanner_type(self) -> ScannerType:
        return self._scanner_type

    @scanner_type.setter
    def scanner_type(self, scanner_type: ScannerType) -> None:
        self._scanner_type = scanner_type

    @property
    def scanner_dir(self) -> str:
        return self._scanner_dir

    @scanner_dir.setter
    def scanner_dir(self, scanner_dir: str) -> None:
        self._scanner_dir = scanner_dir

    @property
    def cred_data_dir(self) -> str:
        return self._cred_data_dir

    @cred_data_dir.setter
    def cred_data_dir(self, cred_data_dir: str) -> None:
        self._cred_data_dir = cred_data_dir

    @property
    def line_checker(self) -> set:
        return self._line_checker

    @line_checker.setter
    def line_checker(self, line_checker: set) -> None:
        self._line_checker = line_checker

    @property
    def result_cnt(self) -> int:
        return self._result_cnt

    @result_cnt.setter
    def result_cnt(self, result_cnt: int) -> None:
        self._result_cnt = result_cnt

    @property
    def lost_cnt(self) -> int:
        return self._lost_cnt

    @lost_cnt.setter
    def lost_cnt(self, lost_cnt: int) -> None:
        self._lost_cnt = lost_cnt

    @property
    def true_cnt(self) -> int:
        return self._true_cnt

    @true_cnt.setter
    def true_cnt(self, true_cnt: int) -> None:
        assert 0 <= true_cnt
        self._true_cnt = true_cnt

    @property
    def false_cnt(self) -> int:
        return self._false_cnt

    @false_cnt.setter
    def false_cnt(self, false_cnt: int) -> None:
        assert 0 <= false_cnt
        self._false_cnt = false_cnt

    @property
    def result_dict(self) -> Dict[str, TrueFalseCounter]:
        return self._result_dict

    @result_dict.setter
    def result_dict(self, result_dict: Dict[str, TrueFalseCounter]) -> None:
        self._result_dict = result_dict

    @abstractmethod
    def init_scanner(self) -> None:
        pass

    @abstractmethod
    def run_scanner(self) -> None:
        pass

    @abstractmethod
    def parse_result(self) -> None:
        pass

    def run_benchmark(self, is_output_given: bool) -> None:
        if not is_output_given:
            self.run_scanner()
        self.parse_result()
        self.analyze_result()

    @staticmethod
    def get_items_from_path(file_path: str) -> Tuple[str, str, str, str]:
        data_path = "data" + file_path.split("data", maxsplit=1)[-1]
        repo_name = file_path.split('/')[1]
        file_name = data_path.split('/')[-1]
        file_id = file_name.split('.')[0]
        return data_path, repo_name, file_name, file_id

    def check_line_from_meta(self,
                             file_path: str,
                             line_start: int,
                             line_end: int,
                             value_start: int = -1,
                             value_end: int = -1,
                             rule: str = "") -> Tuple[LineStatus, str, str]:
        self.result_cnt += 1
        data_path, repo_name, file_name, file_id = self.get_items_from_path(file_path)
        # by default the cred is false positive
        approximate = f"{self.meta_next_id},{file_id}" \
                      f",GitHub,{repo_name},{data_path}" \
                      f",{line_start},{line_end}" \
                      f",F,F,{value_start},{value_end}" \
                      f",F,F,,,,,0.0,0,F,F,F,{rule}"
        lost_meta = MetaRow({
            "Id": self.meta_next_id,
            "FileID": file_id,
            "Domain": "GitHub",
            "RepoName": repo_name,
            "FilePath": data_path,
            "LineStart": line_start,
            "LineEnd": line_end,
            "GroundTruth": 'F',
            "WithWords": 'F',
            "ValueStart": value_start,
            "ValueEnd": value_end,
            "InURL": 'F',
            "InRuntimeParameter": 'F',
            "CharacterSet": '',
            "CryptographyKey": '',
            "PredefinedPattern": '',
            "VariableNameType": '',
            "Entropy": 0.0,
            "Length": 0,
            "Base64Encode": 'F',
            "HexEncode": 'F',
            "URLEncode": 'F',
            "Category": rule
        })

        if not (rows := self.meta.get(MetaKey(data_path, line_start, line_end))):
            self.lost_cnt += 1
            print(f"NOT FOUND WITH KEY: {approximate}", flush=True)
            if self.fix:
                with open(f"{self.cred_data_dir}/meta/{repo_name}.csv", "a") as f:
                    f.write(f"{str(approximate)}\n")
                self.meta[MetaKey(data_path, line_start, line_end)] = [lost_meta]
            self.meta_next_id += 1
            return LineStatus.NOT_IN_DB, repo_name, file_id

        suggestion = "LOST:"
        for row in rows:
            # it means, all markups are the same file with line start-end
            if 0 > row.ValueStart and 0 > row.ValueEnd:
                # the markup is for whole line - any value_start, value_end match
                if 'T' == row.GroundTruth and row.LineStart == row.LineEnd:
                    # True markup has to be marked at least start value in single line
                    print(f"WARNING True markup for whole line: {row}", flush=True)
                pass
            elif row.ValueEnd < 0 <= row.ValueStart:
                # the markup points only start value position
                if 0 <= value_start and row.ValueStart != value_start:
                    # start position must be matched if was given from a scanner (value_start=-1 means it is not)
                    continue
            elif row.LineStart == row.LineEnd and 0 <= row.ValueStart < row.ValueEnd \
                    or row.LineStart < row.LineEnd and 0 <= row.ValueStart and 0 <= row.ValueEnd:
                # ! meta value_end may be less than start in multiline markup
                suggestion = f"UNMATCH {row.ValueStart, row.ValueEnd}:"
                # both markers are available
                if 0 <= value_start and row.ValueStart != value_start:
                    # given value_start does not match
                    continue
                else:
                    suggestion = f"ALMOST {row.ValueStart, row.ValueEnd} {row.Category}:"
                # or ...
                if 0 <= value_end and row.ValueEnd != value_end:
                    # for suggestion, padding for base64 encoded items
                    delta = 3
                    if row.ValueEnd - delta <= value_end <= row.ValueEnd + delta \
                            or value_end - delta <= row.ValueEnd <= value_end + delta:
                        suggestion = f"NEARBY {row.ValueStart, row.ValueEnd}"
                    # given value_end does not match
                    continue
                # all checks have passed - there is precisely matching value markup
            else:
                print(f"WARNING: check meta value start-end {row}", flush=True)
                continue

            code = (data_path, row.LineStart, row.LineEnd, row.ValueStart, row.ValueEnd, rule)
            if code in self.line_checker:
                self.result_cnt -= 1
                if 'T' == row.GroundTruth:
                    print(f"WARNING: Already checked True! Duplicate? {code}", flush=True)
                return LineStatus.CHECKED, repo_name, file_name
            else:
                self.line_checker.add(code)

            for meta_rule in row.Category.split(':'):
                # increase the counter only for corresponded rule mentioned in markup
                if meta_rule == rule:
                    if 'T' == row.GroundTruth:
                        self._increase_result_dict_cnt(meta_rule, True)
                        self.true_cnt += 1
                        return LineStatus.FALSE, repo_name, file_id
                    else:
                        # MetaRow class checks the correctness of row.GroundTruth = ['T', 'F', "Template"]
                        self._increase_result_dict_cnt(meta_rule, False)
                        self.false_cnt += 1
                        return LineStatus.TRUE, repo_name, file_id
            else:
                print(f"WARNING: '{rule}' is not mentioned in {row}")
                if self.fix:
                    subprocess.check_call(
                        ["sed", "-i",
                         f"s/{row.Id},\\(.*\\)/{row.Id},\\1:{rule}/",
                         f"{self.cred_data_dir}/meta/{row.RepoName}.csv"])
                    self.meta[MetaKey(data_path, line_start, line_end)].append(lost_meta)
                    lost_meta = None

        # meta has no markup for given credential
        self.lost_cnt += 1
        print(f"{suggestion} {approximate}", flush=True)
        self.meta_next_id += 1
        if lost_meta and self.fix:
            with open(f"{self.cred_data_dir}/meta/{repo_name}.csv", "a") as f:
                f.write(f"{str(approximate)}\n")
            self.meta[MetaKey(data_path, line_start, line_end)].append(lost_meta)
        return LineStatus.NOT_IN_DB, repo_name, file_id

    def analyze_result(self) -> None:
        print(
            f"{self.scanner_type} result_cnt : {self.result_cnt}, lost_cnt : {self.lost_cnt}"
            f", true_cnt : {self.true_cnt}, false_cnt : {self.false_cnt}"
        )

        header = ["Rules", "Positives", "Negatives", "Templates", "Reported",
                  "TP", "FP", "TN", "FN", "FPR", "FNR", "ACC", "PRC", "RCL", "F1"]
        rows: List[List[Any]] = []

        # augment empty scores counters for rules which were not reported
        for key in self.rules_markup_counters.keys():
            if key not in self.result_dict:
                self.result_dict[key] = TrueFalseCounter()

        # augment for reported but not markup rules
        for key in self.reported.keys():
            if key not in self.result_dict:
                self.result_dict[key] = TrueFalseCounter()

        reported_sum = tp_sum = fp_sum = tn_sum = fn_sum = 0
        for rule, value in self.result_dict.items():
            assert rule
            true_cnt = value.true_cnt
            false_cnt = value.false_cnt
            total_true_cnt, total_false_cnt = self._get_total_true_false_count(rule)
            result = Result(true_cnt, false_cnt, total_true_cnt, total_false_cnt)
            if rule not in self.rules_markup_counters:
                self.rules_markup_counters[rule] = (0, 0, 0)
            rows.append([
                rule,
                self.rules_markup_counters[rule][0],
                self.rules_markup_counters[rule][1],
                self.rules_markup_counters[rule][2],
                self.reported.get(rule),
                result.true_positive,
                result.false_positive,
                result.true_negative,
                result.false_negative,
                Result.round_micro(result.false_positive_rate),
                Result.round_micro(result.false_negative_rate),
                Result.round_micro(result.accuracy),
                Result.round_micro(result.precision),
                Result.round_micro(result.recall),
                Result.round_micro(result.f1),
            ])
            reported_sum += self.reported.get(rule, 0)
            tp_sum += result.true_positive
            fp_sum += result.false_positive
            tn_sum += result.true_negative
            fn_sum += result.false_negative
        # sort in rule alphabetical order
        rows.sort(key=lambda x: x[0])
        # summary row
        total_result = Result(self.true_cnt, self.false_cnt, self.total_true_cnt, self.total_false_cnt)
        rows.append([
            "",
            self.total_true_cnt,
            self.total_false_cnt,
            self.total_template_cnt,
            reported_sum,
            total_result.true_positive,
            total_result.false_positive,
            total_result.true_negative,
            total_result.false_negative,
            Result.round_micro(total_result.false_positive_rate),
            Result.round_micro(total_result.false_negative_rate),
            Result.round_micro(total_result.accuracy),
            Result.round_micro(total_result.precision),
            Result.round_micro(total_result.recall),
            Result.round_micro(total_result.f1),
        ])
        print(tabulate.tabulate(rows, header, floatfmt=".6f"))

    def _get_total_true_false_count(self, category: str) -> Tuple[int, int]:
        total_line_cnt = self._get_total_line_cnt(category)
        total_true_cnt = self._get_total_true_cnt(category)
        total_false_cnt = total_line_cnt - total_true_cnt
        return total_true_cnt, total_false_cnt

    def _get_total_line_cnt(self, rule: str) -> int:
        total_line_cnt = 0
        for rows in self.meta.values():
            for row in rows:
                if row and rule in row.Category.split(':'):
                    total_line_cnt += 1
        return total_line_cnt

    def _get_total_true_cnt(self, rule: str) -> int:
        total_true_cnt = 0
        for rows in self.meta.values():
            for row in rows:
                if row and 'T' == row.GroundTruth and rule in row.Category.split(':'):
                    total_true_cnt += 1
        return total_true_cnt

    def _increase_result_dict_cnt(self, rule: str, cnt_type: bool) -> None:
        if rule not in self.result_dict:
            self.result_dict[rule] = TrueFalseCounter()
        self.result_dict[rule].increase(cnt_type)
