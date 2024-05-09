import csv
import dataclasses
import os
from abc import ABC, abstractmethod
from typing import Tuple, Dict, List, Any

import tabulate

from benchmark.common import GitService, LineStatus, Result, ScannerType
from benchmark.scanner.true_false_counter import TrueFalseCounter


@dataclasses.dataclass
class TypeStat:
    files_number: int
    valid_lines: int
    true_markup: int
    false_markup: int
    template_markup: int


# temporally meta key - file_path,line_start,line_stop
meta_file_lines_key = Tuple[str, int, int]


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
        self.categories: Dict[str, Tuple[int, int, int]] = {}  # category: (true_cnt, false_cnt, template_cnt)
        self.next_id = 0
        self.file_types: Dict[str, TypeStat] = {}
        self.total_data_valid_lines = 0
        self.meta: Dict[meta_file_lines_key, List[Dict[str, Any]]] = {}
        self._read_meta()

    @property
    @abstractmethod
    def output_dir(self) -> str:
        raise NotImplementedError()

    @output_dir.setter
    @abstractmethod
    def output_dir(self, output_dir: str) -> None:
        raise NotImplementedError()

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
                        line_start = int(row["LineStart"])
                        row["LineStart"] = line_start
                        line_end = int(row["LineEnd"])
                        row["LineEnd"] = line_end
                        row["ValueStart"] = int(row["ValueStart"]) if row["ValueStart"] else -1
                        row["ValueEnd"] = int(row["ValueEnd"]) if row["ValueEnd"] else -1
                        k = (row["FilePath"], row["LineStart"], row["LineEnd"])
                        if m := self.meta.get(k):
                            m.append(row)
                        else:
                            self.meta[k] = [row]
                        self.file_types[file_type_lower] = type_stat

                        meta_id = int(row["Id"])
                        if meta_id > self.next_id:
                            # use next_id for printing lost markup
                            self.next_id = meta_id + 1

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

        if not (rows := self.meta.get((data_path, line_start, line_end))):
            self.lost_cnt += 1
            self.next_id += 1
            print(f"NOT FOUND WITH KEY: {approximate}", flush=True)
            return LineStatus.NOT_IN_DB, project_id, file_id

        suggestion = "LOST:"
        for row in rows:
            if row["FilePath"] == data_path:
                if self._check_line_num(row["LineStart"], row["LineEnd"], line_start, line_end):
                    meta_value_start = int(row.get("ValueStart", -1))
                    meta_value_end = int(row.get("ValueEnd", -1))
                    if meta_value_end < 0 <= meta_value_start:
                        # only start value in markup
                        if 0 <= value_start and meta_value_start != value_start:
                            continue
                    elif 0 <= meta_value_start < meta_value_end:
                        suggestion = f"UNMATCH {meta_value_start, meta_value_end}:"
                        # both markers are available
                        if 0 <= value_start and meta_value_start != value_start:
                            continue
                        else:
                            suggestion = f"ALMOST {meta_value_start, meta_value_end}:"
                        # or ...
                        if 0 <= value_end and meta_value_end != value_end:
                            # todo: add check for padding chars eyJ...x== - value_end may be different for some creds
                            continue
                    elif 0 > meta_value_end and 0 > meta_value_start:
                        # meta markup for whole line
                        pass
                    else:
                        print(f"WARNING: check meta value start-end {row}")
                        continue
                    code = str(project_id) + str(file_id) + str(row["LineStart"]) + str(row["LineEnd"]) + str(row["ValueStart"]) + str(row["ValueEnd"])
                    if code in self.line_checker:
                        self.result_cnt -= 1
                        return LineStatus.CHECKED, project_id, file_id
                    else:
                        self.line_checker.add(code)

                    if row["GroundTruth"] == "T":
                        self.true_cnt += 1
                        self._increase_result_dict_cnt(row["Category"], True)
                        # print(f"TRUE:{file_path},{line_start},{line_end},{value_start},{value_end},{rule}   {row}")
                        return LineStatus.TRUE, project_id, file_id
                    elif row["GroundTruth"] == "F" or row["GroundTruth"] == "Template":
                        self.false_cnt += 1
                        self._increase_result_dict_cnt(row["Category"], False)
                        # print(f"FALSE:{file_path},{line_start},{line_end},{value_start},{value_end},{rule}   {row}")
                        return LineStatus.FALSE, project_id, file_id
        self.lost_cnt += 1
        print(f"{suggestion} {approximate}", flush=True)
        with open(data_path, "r", encoding="utf8") as f:
            lines=f.read().split('\n')
        print('\n'.join(x.strip() for x in lines[line_start-1:line_end]))
        if suggestion.startswith("UNMATCH"):
            with open(f"meta/{repo_name}.csv", 'a') as f:
                f.write(f"{approximate}\n")


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

    def _get_total_true_false_count(self, category: str) -> Tuple[int, int]:
        total_line_cnt = self._get_total_line_cnt(category)
        total_true_cnt = self._get_total_true_cnt(category)
        total_false_cnt = total_line_cnt - total_true_cnt
        return total_true_cnt, total_false_cnt

    def _get_total_line_cnt(self, category: str) -> int:
        total_line_cnt = 0
        for rows in self.meta.values():
            for row in rows:
                if row["Category"] == category:
                    total_line_cnt += 1
        return total_line_cnt

    def _get_total_true_cnt(self, category: str = None) -> int:
        total_true_cnt = 0
        for rows in self.meta.values():
            for row in rows:
                if row["Category"] == category and row["GroundTruth"] == "T":
                    total_true_cnt += 1
        return total_true_cnt

    @staticmethod
    def _check_line_num(meta_line_start: int,
                        meta_line_end: int,
                        line_start: int,
                        line_end: int) -> bool:
        if 0 <= line_end:
            # CredSweeper report must contain the value
            if meta_line_start == line_start and meta_line_end == line_end:
                return True
        else:
            if meta_line_start <= line_start <= meta_line_end:
                return True
        return False

    def _increase_result_dict_cnt(self, category: str, cnt_type: bool) -> None:
        if category not in self.result_dict:
            self.result_dict[category] = TrueFalseCounter()
        self.result_dict[category].increase(cnt_type)
