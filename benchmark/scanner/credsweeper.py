import json
import subprocess
from typing import Tuple

from benchmark.common.constants import URL, LineStatus, ScannerType
from benchmark.scanner.scanner import Scanner


class CredSweeper(Scanner):
    def __init__(self, working_dir: str, cred_data_dir: str) -> None:
        super().__init__(ScannerType.CREDSWEEPER, URL.CREDSWEEPER, working_dir, cred_data_dir)
        self.output_dir: str = f"{self.scanner_dir}/output.json"

    @property
    def output_dir(self) -> str:
        return self._output_dir

    @output_dir.setter
    def output_dir(self, output_dir: str) -> None:
        self._output_dir = output_dir

    def init_scanner(self) -> None:
        subprocess.call(["virtualenv", "venv"], cwd=self.scanner_dir)
        subprocess.call(["./venv/bin/python", "-m", "pip", "install", "-qr", "requirements.txt"], cwd=self.scanner_dir)

    def run_scanner(self) -> None:
        self.init_scanner()
        subprocess.call([
            "./venv/bin/python", "-m", "credsweeper", "--path", f"{self.cred_data_dir}/data", "--ml_validation",
            "--save-json", self.output_dir
        ],
                        cwd=self.scanner_dir)

    def parse_result(self) -> Tuple[int, int, int, int]:
        with open(self.output_dir, "r") as f:
            data = json.load(f)

        for result in data:
            for line_data in result["line_data_list"]:
                if line_data["path"].split("/")[-1] == "LICENSE":
                    continue
                check_line_result, line_data["project_id"], line_data["per_repo_file_id"] = self.check_line_from_meta(
                    line_data["path"], line_data["line_num"])
                if check_line_result == LineStatus.TRUE:
                    line_data["TP"] = "O"
                elif check_line_result == LineStatus.FALSE:
                    line_data["TP"] = "X"
                elif check_line_result == LineStatus.NOT_IN_DB:
                    line_data["TP"] = "N"
                elif check_line_result == LineStatus.CHECKED:
                    line_data["TP"] = "C"
                line_data["line"] = line_data["line"].strip()
                line_data["rule"] = result["rule"]
                line_data["severity"] = result["severity"]
                line_data["api_validation"] = result["api_validation"]
                line_data["ml_validation"] = result["ml_validation"]
