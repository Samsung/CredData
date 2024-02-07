import base64
import hashlib
import os
import random
import shutil
import string
import subprocess
import logging
import pathlib
import yaml

from argparse import ArgumentParser
from download_data import get_file_type

logging.basicConfig(
    format='%(asctime)s | %(levelname)s | %(filename)s:%(lineno)s | %(message)s',
    level='INFO')
logger = logging.getLogger(__file__)

current_path = pathlib.Path(__file__).parent.absolute()
project_path = current_path.parent.absolute()
result_path = current_path / 'result'
temp_path = result_path / 'tmp'
data_path = result_path / 'data'
scan_result_path = result_path / 'scan_result'


def load_ids():
    with open(project_path / 'snapshot.yaml', encoding='utf-8') as f:
        snapshot_data = yaml.load(f, Loader=yaml.FullLoader)
        return [data['id'] for data in snapshot_data]


existing_ids = load_ids()


def save_to_yaml(repos_dict, yaml_file):
    pathlib.Path(yaml_file).parent.mkdir(parents=True, exist_ok=True)
    with open(yaml_file, 'w', encoding='utf-8') as f:
        yaml.dump(repos_dict, f)


def load_from_yaml(yaml_file):
    with open(yaml_file, encoding='utf-8') as f:
        return yaml.load(f, Loader=yaml.FullLoader)


def get_owner_repo_name_from_url(url):
    owner_name, repo_name = url.split('/')[-2:]
    repo_name = repo_name.split('.')[0]
    return owner_name, repo_name


def generate_unique_id():
    while True:
        unique_id = ''.join(random.choice(string.printable) for _ in range(6))
        encoded_id = base64.b64encode(unique_id.encode()).decode('utf-8')
        if encoded_id not in existing_ids:
            existing_ids.append(encoded_id)
            return encoded_id


def download_repo(repo_url, base_path):
    logger.info(f'Download {repo_url}')
    repo_url = repo_url.strip()
    owner_name, repo_name = get_owner_repo_name_from_url(repo_url)
    pathlib.Path(f'{base_path}/{owner_name}').mkdir(parents=True, exist_ok=True)
    repo_path = f'{base_path}/{owner_name}/{repo_name}'
    try:
        subprocess.check_call(['git', 'clone', repo_url, repo_path])
        commit_sha = (subprocess.check_output(['git', '-C', repo_path, 'rev-parse', 'HEAD']).decode('ascii').strip())
        try:
            tag = (subprocess.check_output(['git', '-C', repo_path, 'describe', '--long', '--dirty', '--tags'])
                   .decode('ascii').strip())
        except subprocess.CalledProcessError:
            tag = 'None'
        logger.info(f'Downloaded {repo_url} {commit_sha}')
        return {'id': generate_unique_id(), 'url': repo_url, 'sha': commit_sha, 'tag': tag}
    except subprocess.CalledProcessError as e:
        logger.error(f"Couldn't download repo {repo_path}. {e}")


def download_repos(input_repo_file, dst_path):
    with open(input_repo_file, 'r', encoding='utf-8') as file:
        urls = file.readlines()
    downloaded_repos = []
    for url in urls:
        repo = download_repo(url, dst_path)
        if repo:
            downloaded_repos.append(repo)
    return downloaded_repos


def hashing_file_names(src_path, dst_path, repos_info):
    os.makedirs(dst_path, exist_ok=True)
    for i, repo_data in enumerate(repos_info):
        new_repo_id = hashlib.sha256(repo_data['id'].encode()).hexdigest()[:8]
        logger.info(f'Hash of repo {repo_data["id"]} = {new_repo_id}')
        owner_name, repo_name = get_owner_repo_name_from_url(repo_data['url'])
        repo_path = f'{src_path}/{owner_name}/{repo_name}'
        # Select all files in the repo
        repo_files = [os.path.join(root, file) for root, dirs, files in os.walk(repo_path) for file in files]
        # Copy files to new dataset location
        for j, full_path in enumerate(sorted(list(repo_files))):
            short_path = os.path.relpath(full_path, repo_path).replace('\\', '/')
            _, file_extension = os.path.splitext(full_path)
            file_type = get_file_type(short_path, file_extension)
            file_id = hashlib.sha256(short_path.encode()).hexdigest()[:8]

            file_dst_dir = f'{dst_path}/{new_repo_id}/{file_type}'
            os.makedirs(file_dst_dir, exist_ok=True)
            file_dst_full_path = f'{file_dst_dir}/{file_id}{file_extension}'
            shutil.copy(full_path, file_dst_full_path)
            logger.info('COPIED FILE: %s -> %s', full_path, file_dst_full_path)


def run_credsweeper(data_dir, result_dir):
    pathlib.Path(result_dir).mkdir(parents=True, exist_ok=True)
    for repo in os.listdir(data_dir):
        logger.info(f'Running CredSweeper on {repo}')
        repo_path = data_dir / repo
        try:
            subprocess.check_call(['credsweeper', '--path', repo_path, '--save-json', f'{repo}.json'])
        except subprocess.CalledProcessError as e:
            logger.error(f"Couldn't run credsweeper for repo {repo}. {e}")


def run_detect_secrets(data_dir, result_dir):
    pathlib.Path(result_dir).mkdir(parents=True, exist_ok=True)
    for repo in os.listdir(data_dir):
        logger.info(f'Running DetectSecrets on {repo}')
        try:
            out = (subprocess.check_output(['detect-secrets', '-C', f'{data_dir}/{repo}/', 'scan', '--all-files'])
                   .decode())
            with open(f'{result_dir}/{repo}.baseline', 'w') as f:
                f.write(out)
        except subprocess.CalledProcessError as e:
            logger.error(f"Couldn't run detect-secrets for repo {data_dir}/{repo}. {e}")


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--input_repo_file", dest="input_repo_file", required=True,
                        help="File with list of GitHub repos to be analyzed")
    args = parser.parse_args()
    logger.info('Start download')
    repos = download_repos(args.input_repo_file, temp_path)

    save_to_yaml(repos, result_path / 'repos.yaml')
    # repos = load_from_yaml(result_path / 'repos.yaml')

    hashing_file_names(temp_path, data_path, repos)

    run_detect_secrets(data_path, scan_result_path / 'detect_secrets')
    run_credsweeper(data_path, scan_result_path / 'credsweeper')
