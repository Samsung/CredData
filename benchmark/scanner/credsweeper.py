import json
import subprocess

from benchmark.common.constants import URL, LineStatus, ScannerType
from benchmark.scanner.scanner import Scanner
from meta_cred import MetaCred


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

        cred_set = set()
        for cred in data:
            meta_cred = MetaCred(cred)
            # path will be same for all line_data_list
            path_upper = meta_cred.path.upper()
            if any(i in path_upper for i in ["/COPYING", "/LICENSE"]):
                continue
            uniq_cred_key = (meta_cred.line_start, meta_cred.line_end,
                        meta_cred.value_start, meta_cred.value_end,
                        meta_cred.path, meta_cred.rule)
            if uniq_cred_key in cred_set:
                # after value sanitize there may be duplicated coordinates - skip them
                continue
            cred_set.add(uniq_cred_key)

            self.reported[meta_cred.rule] = 1 + self.reported.get(meta_cred.rule, 0)

            check_line_result, project_id, file_id = \
                self.check_line_from_meta(file_path=meta_cred.path,
                                          line_start=meta_cred.line_start,
                                          line_end=meta_cred.line_end,
                                          value_start=meta_cred.strip_value_start,
                                          value_end=meta_cred.strip_value_end,
                                          rule=meta_cred.rule)
