import os
import sqlite3
import subprocess
from typing import Tuple

from credentialdigger import SqliteClient

from benchmark.common.constants import URL, LineStatus, ScannerType
from benchmark.scanner.scanner import Scanner


class CredentialDigger(Scanner):
    def __init__(self, working_dir: str, cred_data_dir: str) -> None:
        super().__init__(ScannerType.CREDENTIAL_DIGGER, URL.CREDENTIAL_DIGGER, working_dir, cred_data_dir)
        self.output_dir: str = f"{self.scanner_dir}/output.db"
        self.working_dir: str = working_dir

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

    @property
    def client(self) -> SqliteClient:
        return self._client

    @client.setter
    def client(self, client: SqliteClient) -> None:
        self._client = client

    def init_scanner(self) -> None:
        self.client = SqliteClient(path=f"{self.scanner_dir}/output.db")
        self.client.add_rules_from_file(f"{self.working_dir}/benchmark/scanner/bin/credential_digger/rules.yml")
        os.environ[
            "path_model"] = "https://github.com/SAP/credential-digger/releases/download/PM-v1.0.1/path_model-1.0.1.tar.gz"
        os.environ[
            "snippet_model"] = "https://github.com/SAP/credential-digger/releases/download/SM-v1.0.0/snippet_model-1.0.0.tar.gz"
        subprocess.call([f"{self.working_dir}/venv/bin/python", "-m", "credentialdigger", "download", "path_model"],
                        cwd=self.scanner_dir)
        subprocess.call([f"{self.working_dir}/venv/bin/python", "-m", "credentialdigger", "download", "snippet_model"],
                        cwd=self.scanner_dir)

    def run_scanner(self) -> None:
        self.init_scanner()
        self.client.scan_path(scan_path=f"{self.cred_data_dir}/data", models=["PathModel", "SnippetModel"], force=True)

    def parse_result(self) -> Tuple[str, str, str, str]:
        conn = sqlite3.connect(self.output_dir)
        cursor = conn.cursor()
        cursor.execute("SELECT id, file_name, line_number FROM discoveries WHERE state = 'new'")

        for data in cursor.fetchall():
            line_data = {"file_name": data[1], "line_number": data[2]}
            if line_data["file_name"].split("/")[-1] == "LICENSE" or "COPYING" in line_data["file_name"].split("/")[-1]:
                continue
            _, _, _ = self.check_line_from_meta(line_data["file_name"], line_data["line_number"])
