import binascii
import csv
import dataclasses
import hashlib
import json
import os
import pathlib
from pathlib import Path
from typing import Union, Generator

from download_data import TMP_DIR, get_file_scope


def _meta_from_file(meta_path: Path) -> Generator[dict, None, None]:
    if ".csv" != meta_path.suffix:
        # *.csv.orig artifacts after git merge
        print(f"WARNING: skip {meta_path} file")
        return
    with open(meta_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not isinstance(row, dict):
                raise RuntimeError(f"ERROR: wrong row '{row}' in {meta_path}")
            yield row


def _meta_from_dir(meta_path: Path) -> Generator[dict, None, None]:
    for root, dirs, files in os.walk(meta_path):
        root_path = Path(root)
        for file in files:
            yield from _meta_from_file(root_path / file)
        # meta dir is flat
        break


def _get_source_gen(meta_path: Union[Path]) -> Generator[dict, None, None]:
    if not isinstance(meta_path, Path):
        raise RuntimeError(f"ERROR: unsupported source {meta_path} type {type(meta_path)}")

    if not meta_path.exists():
        raise RuntimeError(f"ERROR: {meta_path} does not exist")

    if meta_path.is_dir():
        source_gen = _meta_from_dir
    elif meta_path.is_file():
        source_gen = _meta_from_file
    else:
        raise RuntimeError(f"ERROR: unsupported {meta_path} file type")
    yield from source_gen(meta_path)


def get_file_type_old(file_path: str, file_extension: str):
    file_path = file_path.lower()
    example_indicators = ["test", "examp"]
    other_indicators = ["doc/", "documen", ".md", "readme"]
    if any(ind in file_path for ind in example_indicators):
        return "test"
    if any(ind in file_path for ind in other_indicators) or file_extension == "":
        return "other"
    return "src"


@dataclasses.dataclass
class NewMetaRow:
    Repo: str
    Scope: str
    File: str
    Extension: str
    LineStart: int
    LineEnd: int
    Label: str
    ValueStart: int
    ValueEnd: int
    Info: str
    Category: str


def migrate_repo(repo_id, new_repo_id):
    print(repo_id, new_repo_id)
    all_repo_items = pathlib.Path(f"tmp/{repo_id}").glob("**/*")
    all_repo_files = [str(p) for p in all_repo_items if p.is_file() and not p.is_symlink()]
    repo_files = {}
    for full_path in all_repo_files:
        short_path = os.path.relpath(full_path, f"{TMP_DIR}/{repo_id}/").replace('\\', '/')
        file_id = hashlib.sha256(short_path.encode()).hexdigest()[:8]
        repo_files[file_id] = short_path
    new_meta = []
    meta_file = Path(f"meta/{new_repo_id}.csv")
    for old_meta_row in _get_source_gen(meta_file):
        new_meta_row = NewMetaRow(
            Repo=old_meta_row["RepoName"],
            Scope="TBD:Scope",
            File=old_meta_row["FileID"],
            Extension="TBD:Extension",
            LineStart=old_meta_row["LineStart"],
            LineEnd=old_meta_row["LineEnd"],
            Label=old_meta_row["GroundTruth"],
            ValueStart=old_meta_row["ValueStart"],
            ValueEnd=old_meta_row["ValueEnd"],
            Info=old_meta_row["PredefinedPattern"],
            Category=old_meta_row["Category"]
        )

        short_path = repo_files[new_meta_row.File].lower()
        file_path_name, file_extension = os.path.splitext(short_path)
        new_meta_row.Scope = get_file_scope(file_path_name)
        new_meta_row.Extension = file_extension.lower()
        new_meta.append(new_meta_row)

    with open(meta_file, 'w', newline='\n') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=dataclasses.asdict(new_meta[0]).keys())
        writer.writeheader()
        for row in sorted(new_meta,key=lambda x: x.File):
            writer.writerow(dataclasses.asdict(row))



def main():
    with open("snapshot.json", encoding="utf_8") as f:
        snapshot = json.load(f)

    for repo_id, repo_url in snapshot.items():
        repo_id_bytes = binascii.unhexlify(repo_id)
        new_repo_id = f"{binascii.crc32(repo_id_bytes):08x}"
        migrate_repo(repo_id, new_repo_id)


if __name__ == """__main__""":
    main()
