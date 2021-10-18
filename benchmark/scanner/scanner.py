import csv
import os
from abc import ABC, abstractmethod
from typing import Tuple

from benchmark.common import GitService, LineStatus, Result


class Scanner(ABC):
    def __init__(self, scanner_type: str, scanner_url: str, working_dir: str, cred_data_dir: str) -> None:
        self.scanner_type: str = scanner_type
        self.scanner_dir: str = GitService.set_scanner_up_to_date(working_dir, scanner_url)
        self.cred_data_dir: str = cred_data_dir
        self.line_checker: set = set()

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

    @abstractmethod
    def init_scanner(self) -> None:
        pass

    @abstractmethod
    def run_scanner(self) -> None:
        pass

    @abstractmethod
    def parse_result(self) -> None:
        pass

    def run_benchmark(self) -> None:
        self.run_scanner()
        result_cnt, lost_cnt, true_cnt, false_cnt = self.parse_result()
        self.analyze_result(result_cnt, lost_cnt, true_cnt, false_cnt)

    def check_line_from_meta(self, file_path: str, line_num: int) -> Tuple[LineStatus, str, str]:
        meta_dir = f"{self.cred_data_dir}/meta"
        repo_name = file_path.split("/")[-3]
        path = "data/" + "/".join(file_path.split("/")[-3:])
        project_id = repo_name
        file_id = ""

        with open(f"{meta_dir}/{repo_name}.csv", "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["FilePath"] == path and self._check_line_num(row["LineStart:LineEnd"], line_num):
                    file_id = row["FileID"]
                    code = str(project_id) + str(file_id) + str(line_num)

                    if code in self.line_checker:
                        return LineStatus.CHECKED, project_id, file_id
                    else:
                        self.line_checker.add(code)

                    if row["GroundTruth"] == "T":
                        return LineStatus.TRUE, project_id, file_id
                    else:
                        return LineStatus.FALSE, project_id, file_id

        return LineStatus.NOT_IN_DB, project_id, file_id

    def analyze_result(self, result_cnt: int, lost_cnt: int, true_cnt: int, false_cnt: int):
        print(f"result_cnt : {result_cnt}, lost_cnt : {lost_cnt}, true_cnt : {true_cnt}, false_cnt : {false_cnt}")

        total_true_cnt, total_false_cnt = self._get_total_true_false_count()

        print(f"{self.scanner_type} -> {Result(true_cnt, false_cnt, total_true_cnt, total_false_cnt)}")

    def _get_total_true_false_count(self) -> Tuple[int, int]:
        total_line_cnt = self._get_total_line_cnt()
        total_true_cnt = self._get_total_true_cnt()
        total_false_cnt = total_line_cnt - total_true_cnt
        return total_true_cnt, total_false_cnt

    def _get_total_line_cnt(self) -> int:
        data_dir = f"{self.cred_data_dir}/data"
        valid_dir_list = ["src", "test", "other"]
        total_line_cnt = 0

        repo_folder_list = os.listdir(data_dir)

        for repo_folder in repo_folder_list:

            dir_list = os.listdir(f"{data_dir}/{repo_folder}")

            for dir in dir_list:
                if dir not in valid_dir_list:
                    continue

                file_list = os.listdir(f"{data_dir}/{repo_folder}/{dir}")

                for file in file_list:
                    with open(f"{data_dir}/{repo_folder}/{dir}/{file}", 'r', encoding='utf8') as f:
                        lines = f.readlines()
                        for line in lines:
                            if line.strip() != "":
                                total_line_cnt += 1

        return total_line_cnt

    def _get_total_true_cnt(self) -> int:
        meta_dir = f"{self.cred_data_dir}/meta"
        total_true_cnt = 0

        meta_file_list = os.listdir(meta_dir)

        for meta_file in meta_file_list:
            with open(f"{meta_dir}/{meta_file}", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row["GroundTruth"] == "T":
                        total_true_cnt += 1

        return total_true_cnt

    def _check_line_num(self, line_arrange: str, line_num: int) -> bool:
        start_num, end_num = [int(x) for x in line_arrange.split(":")]
        if line_num >= start_num and line_num <= end_num:
            return True
        return False
