import os

import git


class GitService:
    @classmethod
    def clone(cls, scanner_dir: str, scanner_url: str) -> None:
        git.Git(scanner_dir).clone(scanner_url)

    @classmethod
    def pull(cls, scanner_dir: str) -> None:
        git.Git(scanner_dir).pull()

    @classmethod
    def set_scanner_up_to_date(cls, working_dir: str, scanner_url: str) -> str:
        scanner_dir = working_dir + "/temp/" + scanner_url.split("/")[-1].split(".")[0]

        if "https://" in scanner_url:
            if os.path.isdir(scanner_dir):
                cls.pull(scanner_dir)
            else:
                cls.clone(working_dir + "/temp", scanner_url)
        else:
            os.makedirs(scanner_dir, exist_ok=True)

        return scanner_dir
