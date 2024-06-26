from enum import Enum


class ScannerType(Enum):
    CREDSWEEPER = "credsweeper"
    DETECT_SECRETS = "detect_secrets"
    GITLEAKS = "gitleaks"
    SHHGIT = "shhgit"
    CREDENTIAL_DIGGER = "credential_digger"
    WRAITH = "wraith"
    TRUFFLEHOG3 = "trufflehog3"
    TRUFFLEHOG = "trufflehog"

    def __repr__(self):
        return self.value

    def __str__(self):
        return self.value


class LineStatus(Enum):
    TRUE = True
    FALSE = False
    NOT_IN_DB = "not_in_db"
    CHECKED = "checked"


class URL:
    CREDSWEEPER = "dummy://github.com/Samsung/CredSweeper.git"
    DETECT_SECRETS = "detect_secrets"
    GITLEAKS = "gitleaks"
    SHHGIT = "shhgit"
    CREDENTIAL_DIGGER = "credential_digger"
    WRAITH = "wraith"
    TRUFFLEHOG3 = "trufflehog3"
    TRUFFLEHOG = "trufflehog"
