import base64
import json
import os
import subprocess
from typing import Tuple

from benchmark.common.constants import URL, LineStatus, ScannerType
from benchmark.scanner.scanner import Scanner


class TruffleHog(Scanner):
    def __init__(self, working_dir, cred_data_dir):
        super().__init__(ScannerType.TRUFFLEHOG, URL.TRUFFLEHOG, working_dir, cred_data_dir)
        self.output_dir: str = f"{self.scanner_dir}/output.json"

    @property
    def output_dir(self) -> str:
        return self._output_dir

    @output_dir.setter
    def output_dir(self, output_dir: str) -> None:
        self._output_dir = output_dir

    def init_scanner(self) -> None:
        self.trufflehog_path = f"{os.path.dirname(os.path.realpath(__file__))}/bin/trufflehog/trufflehog"

    def run_scanner(self) -> None:
        self.init_scanner()
        with open(self.output_dir, "w") as f:
            f.write(
                subprocess.Popen(
                    [self.trufflehog_path, "filesystem", f"--directory={self.cred_data_dir}/data", "--json"],
                    cwd=self.scanner_dir,
                    stdout=subprocess.PIPE).communicate()[0].decode("utf-8"))

    def parse_result(self) -> Tuple[int, int, int, int]:
        data = []
        with open(self.output_dir, "r") as f:
            lines = f.readlines()
            for line in lines:
                data.append(json.loads(line))

        for line_data in data:
            file_path = line_data["SourceMetadata"]["Data"]["Filesystem"]["file"]
            if file_path.split("/")[-1] == "LICENSE":
                continue
            line = base64.b64decode(line_data["Raw"]).decode("utf-8", "backslashreplace")
            line_num = self._get_line_num(file_path, line)
            _, _, _ = self.check_line_from_meta(file_path, line_num)

    def _get_line_num(self, file_path: str, match: str) -> int:
        with open(file_path, "r") as f:
            for line_num, line in enumerate(f.readlines()):
                if match in line:
                    return line_num + 1
        return -1
