import binascii
import functools
import hashlib
import json
import logging
import os
import pathlib
import shutil
import subprocess
import sys
from argparse import Namespace, ArgumentParser
from multiprocessing import Pool
from typing import Tuple, Any, Dict

from meta_row import read_meta
from obfuscate_creds import obfuscate_creds

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(filename)s:%(lineno)s | %(message)s",
    level="INFO")
logger = logging.getLogger(__file__)

TMP_DIR = "tmp"


@functools.cache
def get_words_in_path():
    # json format is used to prevent strings concatenation in python without comma in multiline
    with open("word_in_path.json") as f:
        # the file should be the same list in CredSweeper ml_config
        result = json.load(f)
    return result


def get_file_scope(path_without_extension: str):
    result = '/'
    local_file_path_lower = f"./{path_without_extension.lower()}"
    for word in get_words_in_path():
        if word in local_file_path_lower:
            result += word[1:] if word.startswith('/') else word
            if not result.endswith('/'):
                result += '/'
    if '/' == result:
        # underscore is new "other"
        result = "/_/"
    return result


def collect_licenses(repo_id):
    license_files = list(pathlib.Path(f"{TMP_DIR}/{repo_id}").glob("*LICEN*"))
    license_files += list(pathlib.Path(f"{TMP_DIR}/{repo_id}").glob("*Licen*"))
    license_files += list(pathlib.Path(f"{TMP_DIR}/{repo_id}").glob("*licen*"))
    license_files += list(pathlib.Path(f"{TMP_DIR}/{repo_id}").glob("*COPYING*"))
    license_files += list(pathlib.Path(f"{TMP_DIR}/{repo_id}/docs/mixes/").glob("LICENSE"))
    license_files = [str(lf) for lf in license_files]
    license_files = [lf for lf in license_files if "licensemanager" not in lf]
    logger.debug(license_files)
    return license_files


def download_and_check(repo_data: Tuple[Any, Any]):
    """download one git repo or fetch from remote if exists"""
    logger.info(f"Download {repo_data}")
    repo_id = repo_data[0]
    commit_sha = repo_id[:40]
    repo_url = repo_data[1]

    try:
        if os.path.exists(f"{TMP_DIR}/{repo_id}"):
            subprocess.check_call(f"cd {TMP_DIR}/{repo_id} && git checkout {commit_sha}", shell=True)
            logger.info(f"Downloaded and checkout already {repo_url} {commit_sha}")
            return
    except subprocess.CalledProcessError:
        logger.debug(f"Downloading {repo_url} {commit_sha} in {TMP_DIR}/{commit_sha}")

    try:
        checkout_command = (
            f"rm -rf {TMP_DIR}/{repo_id}"
            f" && mkdir -p {TMP_DIR}/{repo_id}"
            f" && cd {TMP_DIR}/{repo_id}"
            f" && git init && git config advice.detachedHead false && git remote add origin {repo_url}"
            f" && git fetch --depth 1 origin {commit_sha} && git checkout {commit_sha} && git log --oneline -1")
        subprocess.check_call(checkout_command, shell=True)
        logger.info(f"Downloaded {repo_url} {commit_sha}")
    except subprocess.CalledProcessError:
        logger.exception(f"Couldn't checkout repo {repo_data}", stack_info=True)
        raise


def download(snapshot_data: dict, jobs: int):
    """Download github repos and checkout proper commits"""
    len_snapshot_data = len(snapshot_data)

    if 1 < jobs:
        with Pool(processes=jobs) as p:
            for i, x in enumerate(p.map(download_and_check, list(snapshot_data.items()))):
                logger.info(f"Downloaded: {i + 1}/{len_snapshot_data}")
    else:
        for i, repo_data in enumerate(snapshot_data.items()):
            download_and_check(repo_data)
            logger.info(f"Downloaded: {i + 1}/{len_snapshot_data}")


def get_new_repo_id(repo_id: str) -> str:
    repo_id_bytes = binascii.unhexlify(repo_id)
    new_repo_id = f"{binascii.crc32(repo_id_bytes):08x}"
    return new_repo_id


def move_files(snapshot_data: dict, dataset_dir: str):
    """Select files with credential candidates. Files without candidates is omitted"""
    os.makedirs(dataset_dir, exist_ok=True)
    missing_repos = []
    for i, (repo_id, repo_url) in enumerate(snapshot_data.items()):
        new_repo_id = get_new_repo_id(repo_id)
        meta_file_path = f"meta/{new_repo_id}.csv"

        logger.info(f"Processing: {i + 1}/{len(snapshot_data)} {repo_id} : {repo_url}")

        # Select file names from meta that we will use in dataset file_id : file_path
        interesting_files: Dict[str, str] = {}
        meta_rows = read_meta(meta_file_path)
        for row in meta_rows:
            key = row.FileID
            file_path = row.FilePath
            assert not file_path.endswith(".xml"), f"xml parsing breaks raw text numeration {file_path}"
            if key in interesting_files:
                # check correctness
                assert interesting_files[key] == file_path, f"Wrong markup: {row}"
            else:
                interesting_files[key] = file_path

        # Select all files in the repo
        # pathlib.Path.glob used instead of glob.glob, as glob.glob could not search for a hidden files
        all_repo_items = pathlib.Path(f"{TMP_DIR}/{repo_id}").glob("**/*")
        all_repo_files = [str(p) for p in all_repo_items if p.is_file() and not p.is_symlink()]
        # full_path : file_id, file_scope, file_extension
        files_found: Dict[str, Tuple[str, str, str]] = {}

        # For each file find its mapping to the metadata or skip
        for full_path in all_repo_files:
            short_path = os.path.relpath(full_path, f"{TMP_DIR}/{repo_id}/").replace('\\', '/')
            file_id = hashlib.sha256(short_path.encode()).hexdigest()[:8]
            if "/.git/" in short_path or short_path.endswith(".xml"):
                # skip the path because changeable .git system files, .xml different value position and line
                if file_id in interesting_files.keys():
                    logger.warning(f"SKIP: {full_path}")
                continue
            file_path_name, file_extension = os.path.splitext(short_path)
            # use lowercase of extension to match ml_config data
            file_extension = file_extension.lower()
            new_file_scope = get_file_scope(file_path_name)
            # copy all files if empty meta file except .git/* and .xml files
            if file_id in interesting_files.keys() or not meta_rows:
                files_found[full_path] = (file_id, new_file_scope, file_extension)
                logger.debug(f"COPY {full_path} -> {new_repo_id}{new_file_scope}{file_id}")
            else:
                logger.debug(f"SKIP {full_path} ; {new_repo_id}{new_file_scope}{file_id}")
        # Check if there are files that present in meta but we could not find, or we somehow found files not from meta
        if meta_rows and \
                0 != len(set(x[0] for x in files_found.values()).symmetric_difference(set(interesting_files.keys()))):
            logger.error(f"Couldn't find all files mentioned in metadata for {new_repo_id} repo. "
                         f"Removing {meta_file_path}, so missing files would not count in the dataset statistics. "
                         f"You can use git to restore {meta_file_path} file back")
            missing_repos.append(meta_file_path)
            if os.path.exists(meta_file_path):
                os.rename(meta_file_path, f"{meta_file_path}.bak")
            continue

        # Copy files to new dataset location
        for full_path, (file_id, file_scope, file_extension) in files_found.items():
            logger.debug(f"{full_path} -> {file_id}")

            code_file_basedir = f'{dataset_dir}/{new_repo_id}{file_scope}'
            code_file_location = f'{code_file_basedir}{file_id}{file_extension}'

            for row in meta_rows:
                if row.FileID == file_id and row.FilePath == code_file_location:
                    logger.debug(row)
                    break
            else:
                if meta_rows:
                    # raise the error only for well-known repos
                    raise RuntimeError(f"Cannot find {code_file_location}")

            if not meta_rows and (os.path.isdir(full_path) or "/.git/" in full_path):
                # workaround for new repos
                continue

            os.makedirs(code_file_basedir, exist_ok=True)
            shutil.copy(full_path, code_file_location)
            logger.debug("COPIED FILE: %s -> %s", full_path, code_file_location)

        license_files = collect_licenses(repo_id)

        # create dir for license files
        code_file_basedir = f'{dataset_dir}/{new_repo_id}'
        os.makedirs(code_file_basedir, exist_ok=True)
        for license_location in license_files:
            name = os.path.basename(license_location)
            if os.path.isdir(license_location):
                shutil.copytree(license_location, f"{dataset_dir}/{new_repo_id}/{name}", dirs_exist_ok=True)
                logger.debug("COPIED DIR: %s -> %s", license_location, f"{dataset_dir}/{new_repo_id}/{name}")
            else:
                shutil.copy(license_location, f"{dataset_dir}/{new_repo_id}/{name}")
                logger.debug("COPIED FILE: %s -> %s", license_location, f"{dataset_dir}/{new_repo_id}/{name}")

    return missing_repos


def check_snapshot_meta(snapshot: dict) -> int:
    result = 0
    sha1_dub_check = {}
    id_dub_check = {}
    for repo_id, repo_url in snapshot.items():
        new_repo_id = get_new_repo_id(repo_id)
        meta_file_path = f"meta/{new_repo_id}.csv"
        if not os.path.exists(meta_file_path):
            with open(meta_file_path, "w") as f:
                f.write("Id,FileID,Domain,RepoName,FilePath,LineStart,LineEnd,GroundTruth,ValueStart,ValueEnd"
                        ",CryptographyKey,PredefinedPattern,Category\n")
            logger.warning(f"New meta file {meta_file_path} created!")
            result += 1
        # duplicate commit check
        if dub_sha1 := sha1_dub_check.get(repo_id[:40]):
            logger.warning(f"{repo_id}:{repo_url} may be from the same commit with {dub_sha1}")
        sha1_dub_check[repo_id[:40]] = (repo_id, repo_url)
        # repo_id collision check
        if dub_id := id_dub_check.get(new_repo_id):
            logger.error(f"{repo_id} has collision {new_repo_id} with {dub_id}")
            result += 1
        id_dub_check[new_repo_id] = (repo_id, repo_url)
    return result


def main(args: Namespace):
    if os.path.exists(args.data_dir):
        if not args.clean_data:
            raise FileExistsError(f"{args.data_dir} directory already exists. "
                                  f"Please remove it or select other directory.")
        shutil.rmtree(args.data_dir)

    with open("snapshot.json", encoding="utf_8") as f:
        snapshot = json.load(f)

    if new_meta_count := check_snapshot_meta(snapshot):
        logger.critical(f"Check logs, fix and restart if necessary: {new_meta_count}")
        return 1

    jobs = 1 if not args.jobs else max(1, int(args.jobs))
    if not args.skip_download:
        logger.info("Start download")
        os.makedirs(TMP_DIR, exist_ok=True)
        download(snapshot, jobs)
        logger.info("Download finished. Now processing the files...")
    else:
        logger.info("Download skipped. Now processing the files...")

    removed_meta = move_files(snapshot, args.data_dir)
    # check whether there were issues with downloading
    assert 0 == len(removed_meta), removed_meta
    logger.info("Finalizing dataset. Please wait a moment...")
    obfuscate_creds("meta", args.data_dir)
    logger.info(f"Done! All files saved to {args.data_dir}")
    return 0


if __name__ == "__main__":
    parser = ArgumentParser(prog="python download_data.py")

    parser.add_argument("--data_dir", dest="data_dir", default="data", help="Dataset location after download")
    parser.add_argument("--jobs", dest="jobs", help="Jobs for multiprocessing")
    parser.add_argument("--skip_download", help="Skip download", action="store_const", const=True)
    parser.add_argument("--clean_data", help="Recreate data dir", action="store_const", const=True)
    _args = parser.parse_args()

    sys.exit(main(_args))
