import json
import linecache
import os
import subprocess
from typing import Tuple

from benchmark.common.constants import URL, LineStatus, ScannerType
from benchmark.scanner.scanner import Scanner


class DetectSecrets(Scanner):
    def __init__(self, working_dir, cred_data_dir):
        super().__init__(ScannerType.DETECT_SECRETS, URL.DETECT_SECRETS, working_dir, cred_data_dir)
        self.output_dir: str = f"{self.scanner_dir}/output.json"

    @property
    def output_dir(self) -> str:
        return self._output_dir

    @output_dir.setter
    def output_dir(self, output_dir: str) -> None:
        self._output_dir = output_dir

    def init_scanner(self) -> None:
        subprocess.call(["virtualenv", "venv"], cwd=self.scanner_dir)
        subprocess.call(["./venv/bin/python", "-m", "pip", "install", "detect-secrets"], cwd=self.scanner_dir)

    def run_scanner(self) -> None:
        self.init_scanner()
        proc = subprocess.Popen(
            [f"{self.scanner_dir}/venv/bin/detect-secrets", "scan", "--all-files", f"{self.cred_data_dir}/data"],
            cwd=self.scanner_dir + "/../../",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        out = proc.communicate()
        with open(self.output_dir, "w") as f:
            f.write(out[0].decode("utf8"))

    def parse_result(self) -> Tuple[int, int, int, int]:
        with open(self.output_dir, "r") as f:
            data = json.load(f)

        for path in data["results"]:
            for line_data in data["results"][path]:
                if line_data["filename"].split("/")[-1] == "LICENSE":
                    continue
                check_line_result, line_data["project_id"], line_data["per_repo_file_id"] = self.check_line_from_meta(
                    line_data["filename"], line_data["line_number"])
                if check_line_result == LineStatus.TRUE:
                    line_data["TP"] = "O"
                elif check_line_result == LineStatus.FALSE:
                    line_data["TP"] = "X"
                elif check_line_result == LineStatus.NOT_IN_DB:
                    line_data["TP"] = "N"
                elif check_line_result == LineStatus.CHECKED:
                    line_data["TP"] = "C"
                else:
                    line_data["TP"] = ""

                line_data["line"] = linecache.getline(f"{os.getcwd()}/temp/{line_data['filename']}",
                                                      line_data["line_number"])
                line_data["filename"] = line_data["filename"].split("/")[-1]
