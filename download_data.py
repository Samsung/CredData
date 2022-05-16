import csv
import hashlib
import os
import pathlib
import random
import re
import shutil
import string
import subprocess
from argparse import ArgumentParser
from typing import Dict, List

import yaml


def int2ascii(x, digs=string.ascii_lowercase):
    # Based on example from https://stackoverflow.com/a/2267446
    base = len(digs)

    if x < 0:
        sign = -1
    elif x == 0:
        return digs[0]
    else:
        sign = 1

    x *= sign
    digits = []

    while x:
        digits.append(digs[int(x % base)])
        x = int(x / base)

    if sign < 0:
        digits.append('-')

    digits.reverse()

    return ''.join(digits)


def get_file_type(file_path: str, file_extension: str):
    file_path = file_path.lower()

    example_indicators = ["test", "examp"]
    other_indicators = ["doc/", "documen", ".md", "readme"]

    if any(ind in file_path for ind in example_indicators):
        return "test"
    if any(ind in file_path for ind in other_indicators) or file_extension == "":
        return "other"

    return "src"


def collect_licenses(temp_dir, ownername, reponame):
    license_files = list(pathlib.Path(f"{temp_dir}/{ownername}/{reponame}").glob("*LICEN*"))
    license_files += list(pathlib.Path(f"{temp_dir}/{ownername}/{reponame}").glob("*Licen*"))
    license_files += list(pathlib.Path(f"{temp_dir}/{ownername}/{reponame}").glob("*licen*"))
    license_files += list(pathlib.Path(f"{temp_dir}/{ownername}/{reponame}").glob("*COPYING*"))
    license_files += list(pathlib.Path(f"{temp_dir}/{ownername}/{reponame}/docs/mixes/").glob("LICENSE"))
    license_files = [str(lf) for lf in license_files]
    license_files = [lf for lf in license_files if "licensemanager" not in lf]
    return license_files


def download(temp_dir):
    """Download github repos and checkout proper commits"""
    snapshot_file = "snapshot.yaml"
    with open(snapshot_file) as f:
        snapshot_data = yaml.load(f, Loader=yaml.FullLoader)
    os.makedirs(temp_dir, exist_ok=True)

    for i, repo_data in enumerate(snapshot_data):
        repo_url = repo_data["url"]
        commit_sha = repo_data["sha"]
        ownername, reponame = repo_url.split("/")[-2:]

        os.makedirs(f"{temp_dir}/{ownername}", exist_ok=True)

        download_command = f"cd {temp_dir}/{ownername} && git clone {repo_url}"
        checkout_command = f"cd {temp_dir}/{ownername}/{reponame} && git checkout -f {commit_sha}"

        subprocess.call(download_command, shell=True)
        try:
            subprocess.check_call(checkout_command, shell=True)
        except subprocess.CalledProcessError:
            print("Couldn't checkout repo. Skip")
            # Remove repo
            if not is_empty(f"{temp_dir}/{ownername}/{reponame}"):
                shutil.rmtree(f"{temp_dir}/{ownername}/{reponame}")

        print(f"Downloaded: {i + 1}/{len(snapshot_data)}")


def is_empty(directory):
    exists = os.path.exists(directory)
    if exists:
        return len(os.listdir(directory)) == 0
    return True


def move_files(temp_dir, dataset_dir):
    """Select files with credential candidates. Files without candidates is omited"""
    snapshot_file = "snapshot.yaml"
    with open(snapshot_file) as f:
        snapshot_data = yaml.load(f, Loader=yaml.FullLoader)
    os.makedirs(temp_dir, exist_ok=True)

    os.makedirs(dataset_dir, exist_ok=True)
    missing_repos = []

    for i, repo_data in enumerate(snapshot_data):
        new_repo_id = hashlib.sha256(repo_data["id"].encode()).hexdigest()[:8]
        repo_url = repo_data["url"]
        ownername, reponame = repo_url.split("/")[-2:]
        meta_file_path = f"meta/{new_repo_id}.csv"

        if not os.path.exists(meta_file_path):
            print(f"Couldn't find all files mentioned in metadata for {new_repo_id} repo. "
                  f"Removing {meta_file_path}, so missing files would not count in the dataset statistics")
            print(f"You can use git to restore {meta_file_path} file back")
            missing_repos.append(meta_file_path)
            continue

        print(f"Processing: {i + 1}/{len(snapshot_data)} {reponame}")

        # Select file names from meta that we will use in dataset
        interesting_files = set()
        with open(meta_file_path) as csvfile:
            meta_reader = csv.DictReader(csvfile)
            for row in meta_reader:
                interesting_files.add(row["FileID"])

        # Select all files in the repo
        # pathlib.Path.glob used instead of glob.glob, as glob.glob could not search for a hidden files
        repo_files = pathlib.Path(f"{temp_dir}/{ownername}/{reponame}").glob("**/*")
        repo_files = [str(p) for p in repo_files]
        files_found = set()
        ids_found = set()

        # For each file find its mapping to the metadata or skip
        for full_path in repo_files:
            short_path = full_path.replace(f"{temp_dir}/{ownername}/{reponame}/", "")
            file_id = hashlib.sha256(short_path.encode()).hexdigest()[:8]
            if file_id in interesting_files:
                files_found.add(full_path)
                ids_found.add(file_id)

        # Check if there are files that present in meta but we could not find, or we somehow found files not from meta
        if len(ids_found.symmetric_difference(interesting_files)) != 0:
            print(f"Couldn't find all files mentioned in metadata for {new_repo_id} repo. "
                  f"Removing {meta_file_path}, so missing files would not count in the dataset statistics")
            print(f"You can use git to restore {meta_file_path} file back")
            missing_repos.append(meta_file_path)
            if os.path.exists(meta_file_path):
                os.remove(meta_file_path)

        # Copy files to new dataset location
        for j, full_path in enumerate(sorted(list(files_found))):
            short_path = full_path.replace(f"{temp_dir}/{ownername}/{reponame}/", "")
            _, file_extension = os.path.splitext(full_path)
            file_type = get_file_type(short_path, file_extension)
            file_id = int2ascii(j)
            code_file_basebir = f'{dataset_dir}/{new_repo_id}/{file_type}'
            code_file_location = f'{dataset_dir}/{new_repo_id}/{file_type}/{file_id}{file_extension}'
            os.makedirs(code_file_basebir, exist_ok=True)
            shutil.copy(full_path, code_file_location)

        license_files = collect_licenses(temp_dir, ownername, reponame)

        for license_location in license_files:
            name = license_location.split("/")[-1]
            if os.path.isdir(license_location):
                shutil.copytree(license_location, f"{dataset_dir}/{new_repo_id}/{name}")
            else:
                shutil.copy(license_location, f"{dataset_dir}/{new_repo_id}/{name}")

    return missing_repos


def get_obfuscated_value(value, predefined_pattern):
    obfuscated_value = ""

    if predefined_pattern == "AWS Client ID" or value.startswith("AKIA"):  # AKIA, AIPA, ASIA, AGPA, ...
        obfuscated_value = value[:4] + generate_value(value[4:])
    elif predefined_pattern == "Google API Key":  # AIza
        obfuscated_value = "AIza" + generate_value(value[4:])
    elif predefined_pattern == "Google OAuth Access Token":  # ya29.
        obfuscated_value = "ya29." + generate_value(value[5:])
    elif predefined_pattern == "JSON Web Token":  # eyJ
        # Check if it's a proper "JSON Web Token" with header and payload
        if ".eyJ" in value:
            header = "eyJ" + generate_value(value.split(".")[0][3:])
            payload = "eyJ" + generate_value(value.split(".")[1][3:])
            obfuscated_value = header + "." + payload
            if len(value.split(".")) >= 3:  # Signature is optional
                signature = generate_value(value.split(".")[2])
                obfuscated_value += "." + signature
        # Otherwise it's a JWT-like token that also have eyJ indicator and encoded in similar way,
        #  but contains only header/payload part
        else:
            obfuscated_value = "eyJ" + generate_value(value[3:])
    elif value.startswith("eyJ"):
        if ".eyJ" in value:
            pos = value.index(".eyJ")
            obfuscated_value = "eyJ" + generate_value(value[3:pos]) + ".eyJ" + generate_value(value[pos + 4:])
        else:
            obfuscated_value = "eyJ" + generate_value(value[3:])

    elif value.startswith("xoxp"):
        obfuscated_value = value[:4] + generate_value(value[4:])
    elif value.startswith("xoxt"):
        obfuscated_value = value[:4] + generate_value(value[4:])
    elif "apps.googleusercontent.com" in value:
        pos = value.index("apps.googleusercontent.com")
        obfuscated_value = generate_value(value[:pos]) + "apps.googleusercontent.com" + generate_value(value[pos + 26:])
    else:
        obfuscated_value = generate_value(value)

    return obfuscated_value


def generate_value(value):
    obfuscated_value = ""

    for v in value:
        if v in string.ascii_lowercase:
            obfuscated_value += random.choice(string.ascii_lowercase)
        elif v in string.ascii_uppercase:
            obfuscated_value += random.choice(string.ascii_uppercase)
        elif v in string.digits:
            obfuscated_value += random.choice(string.digits)
        else:
            obfuscated_value += v

    return obfuscated_value


def replace_rows(data: List[Dict[str, str]]):
    # Change data in already copied files
    for row in data:

        line_start = int(row["LineStart:LineEnd"].split(":")[0])
        line_end = int(row["LineStart:LineEnd"].split(":")[1])

        # PEM keys and other multiple-line credentials is processed in other function
        if row["CryptographyKey"] != "" or line_end - line_start > 0:
            continue

        if row["GroundTruth"] not in ["T", "N/A"]:
            continue

        if row["ValueStart"] == "":
            continue

        value_start = int(row["ValueStart"])
        value_end = int(row["ValueEnd"])

        file_location = row["FilePath"]

        with open(file_location, "r") as f:
            lines = f.read()
        lines = lines.split("\n")

        old_line = lines[line_start - 1]

        non_spaces = set(string.ascii_letters + string.punctuation + string.digits)
        indentation = 0
        for c in old_line:
            if c in non_spaces:
                break
            indentation += 1

        predefined_pattern = row["PredefinedPattern"]
        value = old_line[indentation + value_start:indentation + value_end]
        obfuscated_value = get_obfuscated_value(value, predefined_pattern)
        new_line = old_line[:indentation + value_start] + obfuscated_value + old_line[indentation + value_end:]

        lines[line_start - 1] = new_line
        # Remove empty last line. Redundant last line may appear due to `lines.split("\n")`
        if lines[-1] == "":
            lines = lines[:-1]

        with open(file_location, "w") as f:
            for l in lines:
                f.write(l + "\n")


def split_in_bounds(i: int, lines_len: int, old_line: str):
    # Check that if BEGIN or END keywords in the row: split this row to preserve --BEGIN and --END unedited
    # Example: in line `key = "-----BEGIN PRIVATE KEY-----HBNUIhsgdeyut..."
    #  `key = "-----BEGIN PRIVATE KEY-----` should be unchanged

    start_regex = re.compile(r"-+\s*BEGIN[\s\w]*-+")
    end_regex = re.compile(r"-+\s*END[\s\w]*-+")

    if i == 0 and lines_len == 1:
        _, segment = start_regex.split(old_line, 1)
        segment, _ = end_regex.split(segment, 1)
        if len(segment) == 0:
            return None, None, None
        start, end = old_line.split(segment)
    elif i == 0 and "BEGIN" in old_line:
        _, segment = start_regex.split(old_line, 1)
        if len(segment) == 0:
            return None, None, None
        start = old_line.split(segment)[0]
        end = ""
    elif i == lines_len - 1 and "END" in old_line:
        segment, _ = end_regex.split(old_line, 1)
        if len(segment) == 0:
            return None, None, None
        end = old_line.split(segment)[-1]
        start = ""
    else:
        start = ""
        end = ""
        segment = old_line

    return start, segment, end


def obfuscate_segment(segment: str):
    # Create new line similar to `segment` but created from random characters
    new_line = ""

    for j, char in enumerate(segment):
        if char in string.ascii_letters:
            # Special case for preserving \n character
            if j > 0 and char == "n" and segment[j - 1] == "\\":
                new_line += "n"
            # Special case for preserving f"" and b"" lines
            elif j < len(segment) - 1 and char in ["b", "f"] and segment[j + 1] in ["'", '"']:
                new_line += char
            else:
                new_line += random.sample(string.ascii_letters, 1)[0]
        elif char in string.digits:
            new_line += random.sample(string.digits, 1)[0]
        else:
            new_line += char

    return new_line


def create_new_key(lines: List[str]):
    # Create new lines with similar formatting as old one
    new_lines = []

    for i, old_l in enumerate(lines):
        start, segment, end = split_in_bounds(i, len(lines), old_l)
        if segment is None:
            new_lines.append(old_l)
            continue

        # DEK-Info: AES-128-CBC, ...
        # Proc-Type: 4,ENCRYPTED
        # Version: GnuPG v1.4.9 (GNU/Linux)
        if "DEK-" in segment or "Proc-" in segment or "Version" in segment:
            new_line = segment
        else:
            new_line = obfuscate_segment(segment)

        new_l = start + new_line + end

        new_lines.append(new_l)

    return new_lines


def create_new_multiline(lines: List[str], starting_position: int):
    # Create new lines with similar formatting as old one
    new_lines = []

    # Process first line independently, so we won't damage variable name
    first_line = lines[0]
    starting_position = int(starting_position)

    # Add number of space-like characters from the line padding to the starting_position
    c = 0
    while c < len(first_line):
        if first_line[c] in (string.ascii_letters + string.punctuation + string.digits):
            break
        else:
            c += 1
    starting_position += c

    new_lines.append(first_line[:starting_position] + obfuscate_segment(first_line[starting_position:]))

    # Do not replace ssh-rsa substring if present
    if "ssh-rsa" in first_line:
        s = first_line.find("ssh-rsa")
        new_lines[0] = new_lines[0][:s] + "ssh-rsa" + new_lines[0][s + 7:]

    for i, old_l in enumerate(lines[1:]):
        new_line = obfuscate_segment(old_l)
        new_lines.append(new_line)

    return new_lines


def process_pem_keys(data: List[Dict[str, str]]):
    # Change data in already copied files (only keys)
    for row in data:

        line_start = int(row["LineStart:LineEnd"].split(":")[0])
        line_end = int(row["LineStart:LineEnd"].split(":")[1])

        # Skip credentials that are not PEM or multiline
        if row["CryptographyKey"] == "" and line_end - line_start < 1:
            continue

        if row["GroundTruth"] not in ["T", "N/A"]:
            continue

        file_location = row["FilePath"]

        with open(file_location, "r") as f:
            lines = f.read()
        lines = lines.split("\n")

        if row["CryptographyKey"] != "":
            new_lines = create_new_key(lines[line_start - 1:line_end])
        else:
            value_start = int(row["ValueStart"])
            new_lines = create_new_multiline(lines[line_start - 1:line_end], value_start)

        lines[line_start - 1:line_end] = new_lines
        # Remove empty last line. Redundant last line may appear due to `lines.split("\n")`
        if lines[-1] == "":
            lines = lines[:-1]

        with open(file_location, "w") as f:
            for l in lines:
                f.write(l + "\n")


def obfuscate_creds(dataset_dir):
    metadata_files = list(pathlib.Path(f"meta").glob("*.csv"))
    metadata_files = [str(meta_file) for meta_file in metadata_files]
    metadata_files = sorted(metadata_files)

    all_credentials = []

    for meta_file in metadata_files:
        with open(meta_file) as csvfile:
            meta_reader = csv.DictReader(csvfile)
            for row in meta_reader:
                row["FilePath"] = row["FilePath"].replace("data", dataset_dir, 1)
                all_credentials.append(row)

    replace_rows(all_credentials)
    process_pem_keys(all_credentials)


if __name__ == "__main__":
    random.seed(993317)  # Set fixed random seed for the same dataset results

    parser = ArgumentParser(prog="python download_data.py")

    parser.add_argument("--data_dir", dest="data_dir", required=True, help="Dataset location after download")
    args = parser.parse_args()

    temp_directory = "tmp"

    if os.path.exists(args.data_dir):
        raise FileExistsError(f"{args.data_dir} directory already exists. Please remove it or select other directory.")

    print("Start download")
    download(temp_directory)
    print("Download finished. Now processing the files...")
    removed_meta = move_files(temp_directory, args.data_dir)
    print("Finalizing dataset. Please wait a moment...")
    obfuscate_creds(args.data_dir)
    print("Done!")
    print(f"All files saved to {args.data_dir}")

    if len(removed_meta) > 0:
        print("Some repos had a problem with download.")
        print("Removing meta so missing files would not count in the dataset statistics:")
        for missing in removed_meta:
            print(missing)
        print(f"You can use git to restore mentioned meta files back")
