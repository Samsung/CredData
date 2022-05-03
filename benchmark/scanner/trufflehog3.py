import json
import os
import subprocess
from typing import Tuple

from benchmark.common.constants import URL, LineStatus, ScannerType
from benchmark.scanner.scanner import Scanner


class TruffleHog3(Scanner):
    def __init__(self, working_dir: str, cred_data_dir: str) -> None:
        super().__init__(ScannerType.TRUFFLEHOG3, URL.TRUFFLEHOG3, working_dir, cred_data_dir)
        self.output_dir = f"{self.scanner_dir}/output.json"
        if os.path.exists(self.output_dir):
            os.remove(self.output_dir)

    @property
    def output_dir(self) -> str:
        return self._output_dir

    @output_dir.setter
    def output_dir(self, output_dir: str) -> None:
        self._output_dir = output_dir

    def init_scanner(self) -> None:
        # trufflehog3 > 2.0.7 versions are have multiprocessing issue.
        subprocess.call(["virtualenv", "venv"], cwd=self.scanner_dir)
        subprocess.call(["./venv/bin/python", "-m", "pip", "install", "trufflehog3==2.0.7"], cwd=self.scanner_dir)

    def run_scanner(self) -> None:
        self.init_scanner()
        subprocess.call([
            "./venv/bin/trufflehog3", f"{self.cred_data_dir}/data/", "-o", self.output_dir, "-f", "json",
            "--line-numbers"
        ],
                        cwd=self.scanner_dir)

    def parse_result(self) -> Tuple[int, int, int, int]:
        with open(self.output_dir, "r") as f:
            data_list = json.load(f)

        for data in data_list:
            for line in data["stringsFound"]:
                line_data = {"path": data["path"], "line_number": int(line.split(" ")[0])}
                if line_data["path"].split("/")[-1] == "LICENSE":
                    continue
                _, _, _ = self.check_line_from_meta(line_data["path"], line_data["line_number"])
