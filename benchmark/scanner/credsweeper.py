import json
import subprocess

from benchmark.common.constants import URL, LineStatus, ScannerType
from benchmark.scanner.scanner import Scanner


class CredSweeper(Scanner):
    RESULT_DICT = {LineStatus.TRUE: 'O',
                   LineStatus.FALSE: 'X',
                   LineStatus.NOT_IN_DB: 'N',
                   LineStatus.CHECKED: 'C'}

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
            "./venv/bin/python", "-m", "credsweeper", "--banner", "--path", f"{self.cred_data_dir}/data", "--jobs", "4",
            "--save-json", self.output_dir, "--sort"
        ],
            cwd=self.scanner_dir)

    def parse_result(self) -> None:
        with open(self.output_dir, "r") as f:
            data = json.load(f)

        for result in data:
            # path will be same for all line_data_list
            path_upper = result["line_data_list"][0]["path"].upper()
            if any(i in path_upper for i in ["/COPYING", "/LICENSE"]):
                continue
            # primary cred will be first, but line number is greater than secondary (multi pattern)
            sorted_by_line_num = sorted(result["line_data_list"], key=lambda x: (x["line_num"], x["value_start"]))
            line_data_first = sorted_by_line_num[0]
            line_start = line_data_first["line_num"]
            offset_first = len(line_data_first["line"]) - len(line_data_first["line"].lstrip())
            value_start = line_data_first["value_start"] - offset_first

            line_data_last = sorted_by_line_num[-1]
            line_end = line_data_last["line_num"]
            offset_last = len(line_data_last["line"]) - len(line_data_last["line"].lstrip())
            value_end = line_data_last["value_end"] - offset_last

            check_line_result, line_data_first["project_id"], line_data_first["per_repo_file_id"] = \
                self.check_line_from_meta(file_path=line_data_first["path"],
                                          line_start=line_start,
                                          line_end=line_end,
                                          value_start=value_start,
                                          value_end=value_end,
                                          rule=result["rule"])

            line_data_first["TP"] = self.RESULT_DICT.get(check_line_result, '?')
