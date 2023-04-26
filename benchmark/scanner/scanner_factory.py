from benchmark.common import ScannerType
from benchmark.scanner import Scanner

class ScannerFactory:
    @classmethod
    def create_scanner(cls, scanner_type: str, working_dir: str, cred_data_dir: str) -> Scanner:
        if scanner_type == ScannerType.CREDSWEEPER:
            from benchmark.scanner import CredSweeper
            return CredSweeper(working_dir, cred_data_dir)
        elif scanner_type == ScannerType.DETECT_SECRETS:
            from benchmark.scanner import DetectSecrets
            return DetectSecrets(working_dir, cred_data_dir)
        elif scanner_type == ScannerType.GITLEAKS:
            from benchmark.scanner import Gitleaks
            return Gitleaks(working_dir, cred_data_dir)
        elif scanner_type == ScannerType.SHHGIT:
            from benchmark.scanner import Shhgit
            return Shhgit(working_dir, cred_data_dir)
        elif scanner_type == ScannerType.CREDENTIAL_DIGGER:
            from benchmark.scanner import CredentialDigger
            return CredentialDigger(working_dir, cred_data_dir)
        elif scanner_type == ScannerType.WRAITH:
            from benchmark.scanner import Wraith
            return Wraith(working_dir, cred_data_dir)
        elif scanner_type == ScannerType.TRUFFLEHOG3:
            from benchmark.scanner import TruffleHog3
            return TruffleHog3(working_dir, cred_data_dir)
        elif scanner_type == ScannerType.TRUFFLEHOG:
            from benchmark.scanner import TruffleHog
            return TruffleHog(working_dir, cred_data_dir)
