import base64
import random
import string
import subprocess
from argparse import ArgumentParser
import logging
import pathlib

import yaml

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(filename)s:%(lineno)s | %(message)s",
    level="INFO")
logger = logging.getLogger(__file__)

current_path = pathlib.Path(__file__).parent.absolute()
project_path = current_path.parent.absolute()

temp_dir = current_path / 'tmp'


def load_ids():
    snapshot_file = "snapshot.yaml"
    with open(project_path / snapshot_file, encoding="utf-8") as f:
        snapshot_data = yaml.load(f, Loader=yaml.FullLoader)
        return [data['id'] for data in snapshot_data]


existing_ids = load_ids()


def save_to_yaml(repos_dict, yaml_file):
    pathlib.Path(yaml_file).parent.mkdir(parents=True, exist_ok=True)
    with open(yaml_file, "w", encoding="utf-8") as f:
        yaml.dump(repos_dict, f)


def generate_unique_id():
    while True:
        unique_id = ''.join(random.choice(string.printable) for _ in range(6))
        encoded_id = base64.b64encode(unique_id.encode()).decode('utf-8')
        if encoded_id not in existing_ids:
            existing_ids.append(encoded_id)
            return encoded_id


def download(repo_url):
    logger.info(f"Download {repo_url}")
    repo_url = repo_url.strip()
    ownername, reponame = repo_url.split("/")[-2:]
    reponame = reponame.split(".")[0]
    pathlib.Path(f"{temp_dir}/{ownername}").mkdir(parents=True, exist_ok=True)
    try:
        subprocess.check_call(['git', 'clone', repo_url, f"{temp_dir}/{ownername}/{reponame}"])
        commit_sha = (subprocess.check_output(['git', '-C', f'{temp_dir}/{ownername}/{reponame}', 'rev-parse', 'HEAD'])
                      .decode('ascii').strip())
        try:
            tag = subprocess.check_output(['git', '-C', f'{temp_dir}/{ownername}/{reponame}', 'describe', '--long',
                                           '--dirty', '--tags']).decode('ascii').strip()
        except subprocess.CalledProcessError:
            tag = 'None'
        id = generate_unique_id()
        logger.info(f"Downloaded {repo_url} {commit_sha}")
        return {'id': id, 'url': repo_url, 'sha': commit_sha, 'tag': tag}
    except subprocess.CalledProcessError as e:
        logger.error(f"Couldn't download repo {temp_dir}/{ownername}/{reponame}. {e}")


def download_repos(input_repo_file):
    with open(input_repo_file, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    downloaded_repos = []
    for line in lines:
        repo = download(line)
        if repo:
            downloaded_repos.append(repo)
    return downloaded_repos


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--input_repo_file", dest="input_repo_file", required=True,
                        help="File with list of GitHub repos to be analyzed")
    args = parser.parse_args()
    logger.info("Start download")
    repos = download_repos(args.input_repo_file)
    save_to_yaml(repos, current_path / 'result' / 'repos.yaml')
