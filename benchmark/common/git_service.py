from typing import Dict

import git
import os


class GitService:
    @classmethod
    def __init__(cls, config: Dict) -> None:
        cls.github_id = config["github_id"]
        cls.github_token = config["github_token"]

    @property
    def github_id(cls) -> str:
        return cls.__github_id

    @github_id.setter
    def github_id(cls, github_id: str) -> None:
        cls.__github_id = github_id

    @property
    def github_token(cls) -> str:
        return cls.__github_token

    @github_token.setter
    def github_token(cls, github_token: str) -> None:
        cls.__github_token = github_token

    @classmethod
    def _get_clone_url(cls, url: str) -> None:
        return url.replace("https://", f"https://{cls.github_id}:{cls.github_token}@")

    @classmethod
    def clone(cls, scanner_dir: str, scanner_url: str) -> None:
        clone_url = cls._get_clone_url(scanner_url)
        git.Git(scanner_dir).clone(clone_url)

    @classmethod
    def pull(cls, scanner_dir: str) -> None:
        git.Git(scanner_dir).pull()

    @classmethod
    def set_scanner_up_to_date(cls, working_dir: str, scanner_url: str) -> None:
        scanner_dir = working_dir + "/temp/" + scanner_url.split("/")[-1].split(".")[0]

        if "https://" in scanner_url:
            if os.path.isdir(scanner_dir):
                cls.pull(scanner_dir)
            else:
                cls.clone(working_dir + "/temp", scanner_url)
        else:
            os.makedirs(scanner_dir, exist_ok=True)

        return scanner_dir
