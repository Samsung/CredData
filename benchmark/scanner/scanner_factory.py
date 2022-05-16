from benchmark.common import ScannerType
from benchmark.scanner import (CredentialDigger, CredSweeper, DetectSecrets, Gitleaks, Scanner, Shhgit, TruffleHog,
                               TruffleHog3, Wraith)


class ScannerFactory:
    @classmethod
    def create_scanner(cls, scanner_type: str, working_dir: str, cred_data_dir: str) -> Scanner:
        if scanner_type == ScannerType.CREDSWEEPER:
            return CredSweeper(working_dir, cred_data_dir)
        elif scanner_type == ScannerType.DETECT_SECRETS:
            return DetectSecrets(working_dir, cred_data_dir)
        elif scanner_type == ScannerType.GITLEAKS:
            return Gitleaks(working_dir, cred_data_dir)
        elif scanner_type == ScannerType.SHHGIT:
            return Shhgit(working_dir, cred_data_dir)
        elif scanner_type == ScannerType.CREDENTIAL_DIGGER:
            return CredentialDigger(working_dir, cred_data_dir)
        elif scanner_type == ScannerType.WRAITH:
            return Wraith(working_dir, cred_data_dir)
        elif scanner_type == ScannerType.TRUFFLEHOG3:
            return TruffleHog3(working_dir, cred_data_dir)
        elif scanner_type == ScannerType.TRUFFLEHOG:
            return TruffleHog(working_dir, cred_data_dir)
