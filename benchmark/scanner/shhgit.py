import csv
import os
import subprocess
from typing import Tuple

from benchmark.common.constants import URL, LineStatus, ScannerType
from benchmark.scanner.scanner import Scanner


class Shhgit(Scanner):
    def __init__(self, working_dir: str, cred_data_dir: str) -> None:
        super().__init__(ScannerType.SHHGIT, URL.SHHGIT, working_dir, cred_data_dir)
        self.output_dir = f"{self.scanner_dir}/output.csv"

    @property
    def output_dir(self) -> str:
        return self._output_dir

    @output_dir.setter
    def output_dir(self, output_dir: str) -> None:
        self._output_dir = output_dir

    def init_scanner(self) -> None:
        self.shhgit_path = f"{os.path.dirname(os.path.realpath(__file__))}/bin/shhgit/shhgit"
        if os.path.exists(self.output_dir):
            os.remove(self.output_dir)

    def run_scanner(self) -> None:
        self.init_scanner()
        subprocess.call(
            [self.shhgit_path, "-silent", "--local", f"{self.cred_data_dir}/data", "--csv-path", self.output_dir],
            cwd=self.scanner_dir)

    def parse_result(self) -> Tuple[int, int, int, int]:
        with open(self.output_dir, "r") as f:
            reader = csv.DictReader(f)

            for row in reader:
                file_path = row["Matching file"][1:]
                if file_path.split("/")[-1] == "LICENSE":
                    continue
                for match in row["Matches"].split(", "):
                    line_num = self._get_line_num(file_path, match)
                    _, _, _ = self.check_line_from_meta(file_path, line_num)

    def _get_line_num(self, file_path: str, match: str) -> int:
        with open(f"{self.cred_data_dir}/data/{file_path}", "r") as f:
            for line_num, line in enumerate(f.readlines()):
                if match in line:
                    return line_num + 1
        return -1
