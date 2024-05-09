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


class LineStatus(Enum):
    TRUE = True
    FALSE = False
    NOT_IN_DB = "not_in_db"
    CHECKED = "checked"


class URL(Enum):
    CREDSWEEPER = "https://github.com/Samsung/CredSweeper.git"
    DETECT_SECRETS = "detect_secrets"
    GITLEAKS = "gitleaks"
    SHHGIT = "shhgit"
    CREDENTIAL_DIGGER = "credential_digger"
    WRAITH = "wraith"
    TRUFFLEHOG3 = "trufflehog3"
    TRUFFLEHOG = "trufflehog"
