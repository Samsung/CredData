import json
import os
import subprocess
from typing import Tuple

from benchmark.common.constants import URL, LineStatus, ScannerType
from benchmark.scanner.scanner import Scanner


class Wraith(Scanner):
    def __init__(self, working_dir: str, cred_data_dir: str) -> None:
        super().__init__(ScannerType.WRAITH, URL.WRAITH, working_dir, cred_data_dir)
        self.output_dir = f"{self.scanner_dir}/output.json"
        self.working_dir = working_dir

    @property
    def output_dir(self) -> str:
        return self._output_dir

    @output_dir.setter
    def output_dir(self, output_dir: str) -> None:
        self._output_dir = output_dir

    @property
    def working_dir(self) -> str:
        return self._working_dir

    @working_dir.setter
    def working_dir(self, working_dir: str) -> None:
        self._working_dir = working_dir

    def init_scanner(self) -> None:
        self.scanner_path = f"{self.working_dir}/benchmark/scanner/bin/wraith/wraith"
        self.signature_path = f"{self.working_dir}/benchmark/scanner/bin/wraith/default.yaml"

    def run_scanner(self) -> None:
        self.init_scanner()
        self.output_lines = subprocess.check_output([
            self.scanner_path, "--silent", "--signature-file", self.signature_path, "scanLocalPath", "--local-paths",
            f"{self.cred_data_dir}/data/", "--scan-tests", "--json", "--num-threads",
            str(os.cpu_count() * 2)
        ],
                                                    cwd=self.scanner_dir,
                                                    universal_newlines=True)
        with open(self.output_dir, "w") as f:
            f.write(self.output_lines)

    def parse_result(self) -> Tuple[int, int, int, int]:
        with open(self.output_dir, "r") as f:
            data = json.loads(''.join(f.readlines()[:-1]))

        for line_data in data:
            if line_data["FilePath"].split("/")[-1] == "LICENSE":
                continue

            _, _, _ = self.check_line_from_meta(line_data["FilePath"], int(line_data["LineNumber"]))
