import json
import os
import subprocess
from typing import Tuple

from benchmark.common.constants import URL, LineStatus, ScannerType
from benchmark.scanner.scanner import Scanner


class Gitleaks(Scanner):
    def __init__(self, working_dir, cred_data_dir):
        super().__init__(ScannerType.GITLEAKS, URL.GITLEAKS, working_dir, cred_data_dir)
        self.output_dir: str = f"{self.scanner_dir}/output.json"

    @property
    def output_dir(self) -> str:
        return self._output_dir

    @output_dir.setter
    def output_dir(self, output_dir: str) -> None:
        self._output_dir = output_dir

    def init_scanner(self) -> None:
        self.gitleaks_path = f"{os.path.dirname(os.path.realpath(__file__))}/bin/gitleaks/gitleaks"

    def run_scanner(self) -> None:
        self.init_scanner()
        subprocess.call([self.gitleaks_path, "--no-git", "-p"
                         f"{self.cred_data_dir}/data", "-o", self.output_dir],
                        cwd=self.scanner_dir)

    def parse_result(self) -> Tuple[int, int, int, int]:
        with open(self.output_dir, "r") as f:
            data = json.load(f)

        for line_data in data:
            if line_data["file"].split("/")[-1] == "LICENSE":
                continue
            _, _, _ = self.check_line_from_meta(line_data["file"], line_data["lineNumber"])
