import contextlib
import csv
import dataclasses
import os
from abc import ABC, abstractmethod
from typing import Optional, Tuple, Dict, List, Any

import colorama
import tabulate
from colorama import Fore
from colorama import Style

import tabulate

import tabulate

from benchmark.common import GitService, LineStatus, Result
from benchmark.scanner.true_false_counter import TrueFalseCounter


@dataclasses.dataclass
class TypeStat:
    files_number: int
    valid_lines: int
    true_markup: int
    false_markup: int
    template_markup: int


class Scanner(ABC):
    def __init__(self, scanner_type: str, scanner_url: str, working_dir: str, cred_data_dir: str) -> None:
        self.scanner_type: str = scanner_type
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
        self.categories: Dict[str, Tuple[int, int, int]] = {}  # category: (true_cnt, false_cnt, template_cnt)
        self.next_id = 0
        self.file_types: Dict[str, TypeStat] = {}
        self.total_data_valid_lines = 0
        self.meta: List[Dict[str, Any]] = []
        self._read_meta()

    def _read_meta(self):
        for root, dirs, files in os.walk(f"{self.cred_data_dir}/meta"):
            for file in files:
                with open(f"{root}/{file}", newline="") as f:
                    if not file.endswith(".csv"):
                        # git garbage files *.orig
                        continue
                    reader = csv.DictReader(f)
                    for row in reader:
                        _, file_type = os.path.splitext(row["FilePath"])
                        file_type_lower = file_type.lower()
                        if file_type_lower in self.file_types:
                            type_stat = self.file_types[file_type_lower]
                        else:
                            type_stat = TypeStat(0, 0, 0, 0, 0)
                        if not row["Category"]:
                            # all unmarked categories are Other
                            row["Category"] = "Other"
                        if row["Category"] not in self.categories:
                            # init the counters
                            self.categories[row["Category"]] = (0, 0, 0)
                        true_cnt, false_cnt, template_cnt = self.categories[row["Category"]]
                        if row["GroundTruth"] == "T":
                            true_cnt += 1
                            self.total_true_cnt += 1
                            type_stat.true_markup += 1
                        elif row["GroundTruth"] == "F":
                            self.total_false_cnt += 1
                            false_cnt += 1
                            type_stat.false_markup += 1
                        elif row["GroundTruth"] == "Template":
                            self.total_template_cnt += 1
                            template_cnt += 1
                            type_stat.template_markup += 1
                        else:
                            # wrong markup should be detected
                            assert False, f"[WRONG MARKUP] {row}"
                        self.categories[row["Category"]] = (true_cnt, false_cnt, template_cnt)
                        self.meta.append(row)
                        self.file_types[file_type_lower] = type_stat
        # use next_id for printing lost markup
        self.next_id = 1 + max(int(x["Id"]) for x in self.meta)

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
                        lines = f.readlines()
                        file_data_valid_lines = 0
                        for line in lines:
                            if line.strip() != "":
                                file_data_valid_lines += 1
                        self.total_data_valid_lines += file_data_valid_lines
                        self.file_types[file_ext_lower].valid_lines += file_data_valid_lines
        print(f"DATA: {self.total_data_valid_lines} valid lines. MARKUP: {len(self.meta)} items", flush=True)
        # f"T:{self.total_true_cnt} F:{self.total_false_cnt}"
        header = ["Category", "Positives", "Negatives", "Template"]
        rows: List[List[Any]] = []
        for key, val in self.categories.items():
            rows.append([key, val[0] or None, val[1] or None, val[2] or None])
        rows.sort(key=lambda x: x[0])
        rows.append(["TOTAL:", self.total_true_cnt, self.total_false_cnt, self.total_template_cnt])
        print(tabulate.tabulate(rows, header), flush=True)

        types_headers = ["FileType", "FileNumber", "ValidLines", "Positives", "Negatives", "Template"]
        types_rows: List[List[Any]] = []
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
    def scanner_type(self) -> str:
        return self._scanner_type

    @scanner_type.setter
    def scanner_type(self, scanner_type: str) -> None:
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

    def run_benchmark(self, output: Optional[str] = None) -> None:
        if not output:
            self.run_scanner(output)
        self.parse_result()
        self.analyze_result()

    def check_line_from_meta(self,
                             file_path: str,
                             line_num: int,
                             value_start: int = -1,
                             value_end: int = -1,
                             rule: str = "",
                             value: str = "") -> Tuple[LineStatus, str, str]:
        self.result_cnt += 1
        repo_name = file_path.split("/")[-3]
        path = "data/" + "/".join(file_path.split("/")[-3:])
        project_id = repo_name
        file_id = ""
        approximate = ""

        # todo: use str(line_num) for comparison or integer values in meta
        for row in self.meta:
            if row["FilePath"] == path:
                file_id = row["FileID"]
                # by default the cred is false positive
                approximate = f"{self.next_id},{file_id},GitHub,{project_id},{path}" \
                              f",{line_num}:{line_num},F,F,{value_start},{value_end},F,F,,,Info,,0,0,F,F,F,{rule}"
                meta_start_num, meta_end_num = [int(x) for x in row["LineStart:LineEnd"].split(':')]

                # check line position
                if meta_start_num == meta_end_num:
                    # single line markup
                    if line_num != meta_start_num:
                        # not the line
                        continue
                elif meta_start_num < meta_end_num:
                    # multiline markup
                    if not meta_start_num <= line_num <= meta_end_num:
                        # checked line does not belong to the markup
                        continue
                else:
                    # wrong markup
                    print(f"MARKUP ERROR (LineStart:LineEnd): {row}", flush=True)
                    continue

                # check value position if possible. multiline may be without start-end
                meta_value_start = int(row["ValueStart"]) if row["ValueStart"] else -1
                meta_value_end = int(row["ValueEnd"]) if row["ValueEnd"] else -1

                if 0 <= meta_value_start and 0 <= value_start and 0 <= value_end:
                    # meta has value markup and the position should be checked if not multiline case
                    if meta_start_num == meta_end_num and not value_start <= meta_value_start <= value_end:
                        continue

                # unique id from meta for single markup (or use just id?)
                code = f"{project_id};{file_id};{meta_start_num};{meta_end_num};{meta_value_start};{meta_value_end}"
                if code in self.line_checker:
                    self.result_cnt -= 1
                    return LineStatus.CHECKED, project_id, file_id
                else:
                    self.line_checker.add(code)
                if row["GroundTruth"] == "T":
                    self.true_cnt += 1
                    self._increase_result_dict_cnt(row["Category"], True)
                    self._print_row_val(row, style=Fore.GREEN)
                    return LineStatus.TRUE, project_id, file_id
                elif row["GroundTruth"] == "F" or row["GroundTruth"] == "Template":
                    self.false_cnt += 1
                    self._increase_result_dict_cnt(row["Category"], False)
                    return LineStatus.FALSE, project_id, file_id
                else:
                    self._print_row_val(row, style=Fore.MAGENTA, value=value)
        self.lost_cnt += 1
        print(f"LOST: {approximate}", flush=True)
        self._print_cred_val(file_path, line_num)
        self.next_id += 1
        return LineStatus.NOT_IN_DB, project_id, file_id

    def analyze_result(self) -> None:
        print(
            f"{self.scanner_type} result_cnt : {self.result_cnt}, lost_cnt : {self.lost_cnt}"
            f", true_cnt : {self.true_cnt}, false_cnt : {self.false_cnt}"
        )
        header = ["Category", "TP", "FP", "TN", "FN", "FPR", "FNR", "ACC", "PRC", "RCL", "F1"]
        rows: List[List[Any]] = []

        for category, value in self.result_dict.items():
            if category == "":
                continue
            true_cnt = value.true_cnt
            false_cnt = value.false_cnt
            total_true_cnt, total_false_cnt = self._get_total_true_false_count(category)
            result = Result(true_cnt, false_cnt, total_true_cnt, total_false_cnt)
            rows.append([
                category,
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
        rows.sort(key=lambda x: x[0])

        total_result = Result(self.true_cnt, self.false_cnt, self.total_true_cnt,
                              self.total_data_valid_lines - self.total_true_cnt)
        rows.append([
            "",
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
        print(Fore.RED + "MISSED VALUES (FALSE NEGATIVES)" + Style.RESET_ALL)
        for row in self.meta:
            if not row["GroundTruth"] == "T":
                continue
            # code = str(row["RepoName"]) + str(row["FileID"]) + str(row["LineStart:LineEnd"])
            meta_start_num, meta_end_num = [int(x) for x in row["LineStart:LineEnd"].split(':')]
            meta_value_start = int(row["ValueStart"]) if row["ValueStart"] else -1
            meta_value_end = int(row["ValueEnd"]) if row["ValueEnd"] else -1
            code = f'{row["RepoName"]};{row["FileID"]};{meta_start_num};{meta_end_num};{meta_value_start};{meta_value_end}'
            if code not in self.line_checker:
                self._print_row_val(row, style=Fore.CYAN)

    @staticmethod
    def _print_row_val(row, style, value=None):
        with open(row["FilePath"], 'r') as f:
            lines = f.readlines()
        line_start_end = row["LineStart:LineEnd"]
        # FilePath, LineStart: LineEnd, GroundTruth, WithWords, ValueStart, ValueEnd
        print(style +  # Fore.LIGHTBLACK_EX
              f'{row["Id"]},{row["FileID"]},{row["Domain"]},{row["RepoName"]},'
              f'{row["FilePath"]},{line_start_end},{row["GroundTruth"]},{row["WithWords"]},'
              f'{row["ValueStart"]},{row["ValueEnd"]},'
              f'{row["InURL"]},{row["InRuntimeParameter"]},{row["CharacterSet"]},{row["CryptographyKey"]},'
              f'{row["PredefinedPattern"]},{row["VariableNameType"]},{row["Entropy"]},{row["Length"]},'
              f'{row["Base64Encode"]},{row["HexEncode"]},{row["URLEncode"]},{row["Category"]}'
              + Style.RESET_ALL)
        line_start, line_end = line_start_end.split(':')
        if line_start == line_end:
            line = lines[int(line_start) - 1]
            value_start = value_end = None
            with contextlib.suppress(Exception):
                value_start = int(row["ValueStart"])
                value_end = int(row["ValueEnd"])
            if isinstance(value_start, int) and isinstance(value_end, int):
                line = line.strip()
                line1 = line[:value_start]
                line2 = line[value_start:value_end]
                line3 = line[value_end:]
                line = line1 + Fore.LIGHTYELLOW_EX + line2 + Style.RESET_ALL + line3
            if value:
                line = line.replace(value, colorama.ansi.CSI + "4m" + value + colorama.ansi.CSI + "0m")
            print(line)
        else:
            for line in lines[int(line_start) - 1: int(line_end)]:
                print(line.rstrip())

    @staticmethod
    def _print_cred_val(file_path, line_num, value_start=None, value_end=None):
        with open(file_path, 'r') as f:
            lines = f.readlines()
        print(Fore.RED + f'{file_path}:{line_num}' + Style.RESET_ALL)
        line = lines[line_num - 1]
        if value_start is not None and value_end is not None:
            line1 = line[:value_start]
            line2 = line[value_start:value_end]
            line3 = line[value_end:]
            print(line1 + Fore.RED + line2 + Style.RESET_ALL + line3)
        else:
            print(line)

    def _get_total_true_false_count(self, category: str) -> Tuple[int, int]:
        total_line_cnt = self._get_total_line_cnt(category)
        total_true_cnt = self._get_total_true_cnt(category)
        total_false_cnt = total_line_cnt - total_true_cnt
        return total_true_cnt, total_false_cnt

    def _get_total_line_cnt(self, category: str) -> int:
        total_line_cnt = 0
        for row in self.meta:
            if row["Category"] == category:
                total_line_cnt += 1
        return total_line_cnt

    def _get_total_true_cnt(self, category: str = None) -> int:
        total_true_cnt = 0
        for row in self.meta:
            if row["Category"] == category and row["GroundTruth"] == "T":
                total_true_cnt += 1
        return total_true_cnt

    def _increase_result_dict_cnt(self, category: str, cnt_type: bool) -> None:
        if category not in self.result_dict:
            self.result_dict[category] = TrueFalseCounter()
        self.result_dict[category].increase(cnt_type)


class TestSweeper(Scanner):

    def __init__(self, working_dir: str, cred_data_dir: str) -> None:
        super().__init__("Test", "TeSt", working_dir, cred_data_dir)

    def init_scanner(self) -> None:
        pass

    def run_scanner(self) -> None:
        pass

    def parse_result(self) -> None:
        pass


if __name__ == "__main__":
    t = TestSweeper('.', '.')
