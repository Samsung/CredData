import binascii
import csv
import dataclasses
import hashlib
import json
import os
import pathlib
from pathlib import Path

from download_data import TMP_DIR, get_file_scope
from meta_row import MetaRow, _meta_from_file


def migrate_repo(repo_id, new_repo_id):
    print(repo_id, new_repo_id)
    all_repo_items = pathlib.Path(f"tmp/{repo_id}").glob("**/*")
    all_repo_files = [str(p) for p in all_repo_items if p.is_file() and not p.is_symlink()]
    repo_files = {}
    for full_path in all_repo_files:
        short_path = os.path.relpath(full_path, f"{TMP_DIR}/{repo_id}/").replace('\\', '/')
        file_id = hashlib.sha256(short_path.encode()).hexdigest()[:8]
        repo_files[(new_repo_id,file_id)] = short_path
    new_meta = []
    meta_file = Path(f"meta/{new_repo_id}.csv")
    for row in _meta_from_file(meta_file):
        meta_row = MetaRow(row)
        short_path = repo_files[(meta_row.RepoName,meta_row.FileID)].lower()
        file_path_name, file_extension = os.path.splitext(short_path)
        file_scope = get_file_scope(file_path_name)
        file_extension = file_extension.lower()
        meta_row.FilePath=f"data/{new_repo_id}{file_scope}{meta_row.FileID}{file_extension}"
        # workaround to keep empty cells instead '-1'
        if 0 > meta_row.ValueStart:
            meta_row.ValueStart = None
        if 0 > meta_row.ValueEnd:
            meta_row.ValueEnd = None
        new_meta.append(meta_row)

    with open(meta_file, 'w', newline='\n') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=dataclasses.asdict(new_meta[0]).keys(), lineterminator='\n')
        writer.writeheader()
        for row in new_meta:
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
