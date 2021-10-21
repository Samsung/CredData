import os
import subprocess

from benchmark.scanner.scanner_factory import ScannerFactory


class Benchmark:
    def __init__(self) -> None:
        ScannerFactory()
        self.working_dir: str = os.getcwd()
        os.makedirs("temp", exist_ok=True)
        self.cred_data_path: str = self.set_cred_data()

    @property
    def working_dir(self) -> str:
        return self._working_dir

    @working_dir.setter
    def working_dir(self, working_dir: str) -> None:
        self._working_dir = working_dir

    @property
    def cred_data_path(self) -> str:
        return self._cred_data_path

    @cred_data_path.setter
    def cred_data_path(self, cred_data_path: str) -> None:
        self._cred_data_path = cred_data_path

    def set_cred_data(self) -> str:
        cred_data_path = os.getcwd()
        if not os.path.exists(f"{cred_data_path}/data"):
            subprocess.call(["./venv/bin/python", "download_data.py", "--data_dir", "data"], cwd=cred_data_path)
        return cred_data_path

    def run(self, scanner_type: str) -> None:
        ScannerFactory.create_scanner(scanner_type, self.working_dir, self.cred_data_path).run_benchmark()
