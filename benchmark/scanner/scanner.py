import dataclasses
import os
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Tuple, Dict, List, Any

import tabulate

from benchmark.common import GitService, LineStatus, Result, ScannerType
from benchmark.scanner.true_false_counter import TrueFalseCounter
from meta_key import MetaKey
from meta_row import _get_source_gen, MetaRow


@dataclasses.dataclass
class TypeStat:
    files_number: int
    valid_lines: int
    true_markup: int
    false_markup: int
    template_markup: int


class Scanner(ABC):
    def __init__(self, scanner_type: ScannerType, scanner_url: str, working_dir: str, cred_data_dir: str) -> None:
        self.scanner_type = scanner_type
        self.scanner_dir: str = GitService.set_scanner_up_to_date(working_dir, scanner_url)
        self.cred_data_dir: str = cred_data_dir
        self.line_checker: set = set()
        self.result_cnt: int = 0
        self.lost_cnt: int = 0
        self.true_cnt: int = 0
        self.false_cnt: int = 0
        self.result_dict: dict = {}
        self.total_true_cnt = 0
        self.total_false_cnt = 0
        self.total_template_cnt = 0
        self.rules_markup_counters: Dict[
            str, Tuple[int, int, int]] = {}  # category: (true_cnt, false_cnt, template_cnt)
        self.next_id = 0
        self.file_types: Dict[str, TypeStat] = {}
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

    def _prepare_meta(self):

        for _row in _get_source_gen(Path(f"{self.cred_data_dir}/meta")):
            meta_row = MetaRow(_row)
            meta_key = MetaKey(meta_row.FilePath, meta_row.LineStart, meta_row.LineEnd)
            if m := self.meta.get(meta_key):
                m.append(meta_row)
            else:
                self.meta[meta_key] = [meta_row]
            _, file_type = os.path.splitext(meta_row.FilePath)
            file_type_lower = file_type.lower()
            type_stat = self.file_types.get(file_type_lower, TypeStat(0, 0, 0, 0, 0))
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
            if self.next_id < meta_row.Id:
                self.next_id = meta_row.Id + 1

        # getting count of all not-empty lines
        data_dir = f"{self.cred_data_dir}/data"
        valid_dir_list = ["src", "test", "other"]
        for root, dirs, files in os.walk(data_dir):
            if root.split("/")[-1] in valid_dir_list:
                for file in files:
                    _, file_ext = os.path.splitext(str(file))
                    file_ext_lower = file_ext.lower()
                    # the type must be in dictionary
                    self.file_types[file_ext_lower].files_number += 1
                    with open(os.path.join(root, file), "r", encoding="utf8") as f:
                        lines = f.read().split('\n')
                        file_data_valid_lines = 0
                        for line in lines:
                            # minimal length of IPv4 detection is 7 e.g. 8.8.8.8
                            if 7 <= len(line.strip()):
                                file_data_valid_lines += 1
                        self.total_data_valid_lines += file_data_valid_lines
                        self.file_types[file_ext_lower].valid_lines += file_data_valid_lines

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

    def check_line_from_meta(self,
                             file_path: str,
                             line_start: int,
                             line_end: int,
                             value_start: int = -1,
                             value_end: int = -1,
                             rule: str = "") -> Tuple[LineStatus, str, str]:
        self.result_cnt += 1
        repo_name = file_path.split('/')[-3]
        data_path = "data/" + '/'.join(file_path.split('/')[-3:])
        project_id = repo_name
        file_name = data_path.split('/')[-1]
        file_id = file_name.split('.')[0]

        # by default the cred is false positive
        approximate = f"{self.next_id},{file_id}" \
                      f",GitHub,{project_id},{data_path}" \
                      f",{line_start},{line_end}" \
                      f",F,F,{value_start},{value_end}" \
                      f",F,F,,,,,0.0,0,F,F,F,{rule}"

        if not (rows := self.meta.get(MetaKey(data_path, line_start, line_end))):
            self.lost_cnt += 1
            self.next_id += 1
            print(f"NOT FOUND WITH KEY: {approximate}", flush=True)
            return LineStatus.NOT_IN_DB, project_id, file_id

        suggestion = "LOST:"
        for meta_row in rows:
            # it means, all markup in the file with markup lines
            if 0 > meta_row.ValueStart and 0 > meta_row.ValueEnd:
                # markup for line only
                pass
            elif meta_row.ValueEnd < 0 <= meta_row.ValueStart:
                # only start value in markup
                if 0 <= value_start and meta_row.ValueStart != value_start:
                    continue
            elif meta_row.LineStart == meta_row.LineEnd and 0 <= meta_row.ValueStart < meta_row.ValueEnd \
                    or meta_row.LineStart < meta_row.LineEnd and 0 <= meta_row.ValueStart and 0 <= meta_row.ValueEnd:
                # ! meta value_end may be less than start in multiline markup
                suggestion = f"UNMATCH {meta_row.ValueStart, meta_row.ValueEnd}:"
                # both markers are available
                if 0 <= value_start and meta_row.ValueStart != value_start:
                    # given value_start does not match
                    continue
                else:
                    suggestion = f"ALMOST {meta_row.ValueStart, meta_row.ValueEnd} {meta_row.Category}:"
                # or ...
                if 0 <= value_end and meta_row.ValueEnd != value_end:
                    # suggest, padding for base64 encoded items
                    delta = 3
                    if meta_row.ValueEnd - delta <= value_end <= meta_row.ValueEnd + delta \
                            or value_end - delta <= meta_row.ValueEnd <= value_end + delta:
                        suggestion = f"NEARBY {meta_row.ValueStart, meta_row.ValueEnd}"
                    # given value_end does not match
                    continue
                # precisely matching
            else:
                print(f"WARNING: check meta value start-end {meta_row}")
                continue

            # dbg correction
            if rule not in meta_row.Category.split(':'):
                # subprocess.run(
                #     ["sed", "-i",
                #      f"s|^{meta_row.Id},\\(.*\\),{meta_row.Category}$|{meta_row.Id},\\1,{meta_row.Category}:{rule}|",
                #      f"meta/{repo_name}.csv"])
                print(f"WARNING: '{rule}' not in {meta_row.Category}")

            code = f'{project_id},{file_id},{meta_row.LineStart},{meta_row.LineEnd}' \
                   f',{meta_row.ValueStart},{meta_row.ValueEnd},{rule}'
            if code in self.line_checker:
                self.result_cnt -= 1
                return LineStatus.CHECKED, project_id, file_id
            else:
                self.line_checker.add(code)

            for meta_rule in meta_row.Category.split(':'):
                if meta_rule == rule:
                    if 'T' == meta_row.GroundTruth:
                        self._increase_result_dict_cnt(meta_rule, True)
                        self.true_cnt += 1
                        return LineStatus.FALSE, project_id, file_id
                    elif 'F' == meta_row.GroundTruth or "Template" == meta_row.GroundTruth:
                        self._increase_result_dict_cnt(meta_rule, False)
                        self.false_cnt += 1
                        return LineStatus.TRUE, project_id, file_id
            else:
                print(f"WARNING: '{rule}' is not mentioned in {meta_row}")

        self.lost_cnt += 1
        print(f"{suggestion} {approximate}", flush=True)
        self.next_id += 1
        return LineStatus.NOT_IN_DB, project_id, file_id

    def analyze_result(self) -> None:
        print(
            f"{self.scanner_type} result_cnt : {self.result_cnt}, lost_cnt : {self.lost_cnt}"
            f", true_cnt : {self.true_cnt}, false_cnt : {self.false_cnt}"
        )

        header = ["Rules", "Positives", "Negatives", "Templates", "Reported",
                  "TP", "FP", "TN", "FN", "FPR", "FNR", "ACC", "PRC", "RCL", "F1"]
        rows: List[List[Any]] = []

        # append empty scores for absent rules
        for key in self.rules_markup_counters.keys():
            if key not in self.result_dict:
                self.result_dict[key] = TrueFalseCounter()

        # append for reported but not markup rules
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
        rows.sort(key=lambda x: x[0])

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
                if rule in row.Category.split(':'):
                    total_line_cnt += 1
        return total_line_cnt

    def _get_total_true_cnt(self, rule: str) -> int:
        total_true_cnt = 0
        for rows in self.meta.values():
            for row in rows:
                if 'T' == row.GroundTruth and rule in row.Category.split(':'):
                    total_true_cnt += 1
        return total_true_cnt

    def _increase_result_dict_cnt(self, rule: str, cnt_type: bool) -> None:
        if rule not in self.result_dict:
            self.result_dict[rule] = TrueFalseCounter()
        self.result_dict[rule].increase(cnt_type)
