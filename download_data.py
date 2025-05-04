import base64
import hashlib
import logging
import os
import pathlib
import random
import re
import shutil
import string
import subprocess
import sys
from argparse import Namespace, ArgumentParser
from multiprocessing import Pool
from typing import List

import yaml

from meta_row import read_meta, MetaRow

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(filename)s:%(lineno)s | %(message)s",
    level="INFO")
logger = logging.getLogger(__file__)


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
    logger.debug(license_files)
    return license_files


def download_and_check(repo_data: dict):
    """download one git repo or fetch from remote if exists"""
    logger.info(f"Download {repo_data}")
    repo_url = repo_data["url"]
    commit_sha = repo_data["sha"]
    ownername, reponame = repo_url.split("/")[-2:]

    temp_dir = repo_data["temp_dir"]
    try:
        if os.path.exists(f"{temp_dir}/{ownername}/{reponame}"):
            subprocess.check_call(f"cd {temp_dir}/{ownername}/{reponame} && git checkout {commit_sha}", shell=True)
            logger.info(f"Downloaded and checkout already {repo_url} {commit_sha}")
            return
    except subprocess.CalledProcessError:
        logger.debug(f"Downloading {repo_url} {commit_sha} in {temp_dir}/{ownername}/{reponame}")

    try:
        checkout_command = (
            f"rm -rf {temp_dir}/{ownername}/{reponame}"
            f" && mkdir -p {temp_dir}/{ownername}/{reponame}"
            f" && cd {temp_dir}/{ownername}/{reponame}"
            f" && git init && git config advice.detachedHead false && git remote add origin {repo_url}"
            f" && git fetch --depth 1 origin {commit_sha} && git checkout {commit_sha} && git log --oneline -1")
        subprocess.check_call(checkout_command, shell=True)
        logger.info(f"Downloaded {repo_url} {commit_sha}")
    except subprocess.CalledProcessError:
        logger.error(f"Couldn't checkout repo {temp_dir}/{ownername}/{reponame}. {repo_data}")
        assert False, f"Couldn't checkout repo {temp_dir}/{ownername}/{reponame}. {repo_data}"
        # Remove repo
        if not is_empty(f"{temp_dir}/{ownername}/{reponame}"):
            shutil.rmtree(f"{temp_dir}/{ownername}/{reponame}")


def download(temp_dir, jobs):
    """Download github repos and checkout proper commits"""
    snapshot_file = "snapshot.yaml"
    with open(snapshot_file) as f:
        snapshot_data = yaml.load(f, Loader=yaml.FullLoader)
    os.makedirs(temp_dir, exist_ok=True)
    len_snapshot_data = len(snapshot_data)

    unique_urls = set()
    for repo_data in snapshot_data:
        assert repo_data["url"] not in unique_urls, f"Duplicate url is not supported {repo_data}"
        unique_urls.add(repo_data["url"])
        repo_data["temp_dir"] = temp_dir

    if 1 < jobs:
        with Pool(processes=jobs) as p:
            for i, x in enumerate(p.map(download_and_check, snapshot_data)):
                logger.info(f"Downloaded: {i + 1}/{len_snapshot_data}")
    else:
        for i, repo_data in enumerate(snapshot_data):
            download_and_check(repo_data)
            logger.info(f"Downloaded: {i + 1}/{len_snapshot_data}")


def is_empty(directory):
    exists = os.path.exists(directory)
    if exists:
        return len(os.listdir(directory)) == 0
    return True


def move_files(temp_dir, dataset_dir):
    """Select files with credential candidates. Files without candidates is omitted"""
    snapshot_file = "snapshot.yaml"
    with open(snapshot_file) as f:
        snapshot_data = yaml.load(f, Loader=yaml.FullLoader)
    os.makedirs(temp_dir, exist_ok=True)

    os.makedirs(dataset_dir, exist_ok=True)
    missing_repos = []

    for i, repo_data in enumerate(snapshot_data):
        new_repo_id = hashlib.sha256(repo_data["id"].encode()).hexdigest()[:8]
        logger.debug(f'Hash of repo {repo_data["id"]} = {new_repo_id}')
        repo_url = repo_data["url"]
        ownername, reponame = repo_url.split("/")[-2:]
        meta_file_path = f"meta/{new_repo_id}.csv"

        if not os.path.exists(meta_file_path):
            with open(meta_file_path, "w") as f:
                f.write("Id,FileID,Domain,RepoName,FilePath,LineStart,LineEnd,GroundTruth,WithWords,ValueStart")
                f.write(",ValueEnd,InURL,InRuntimeParameter,CharacterSet,CryptographyKey,PredefinedPattern")
                f.write(",VariableNameType,Entropy,Length,Base64Encode,HexEncode,URLEncode,Category\n")
            assert False, f"New meta file {meta_file_path}! Restart again for new repo."

        logger.info(f"Processing: {i + 1}/{len(snapshot_data)} {repo_data['id']}")

        # Select file names from meta that we will use in dataset
        interesting_files = dict()
        meta_rows = read_meta(meta_file_path)
        for row in meta_rows:
            key = row.FileID
            file_path = row.FilePath
            assert not file_path.endswith(".xml"), f"xml parsing breaks raw text numeration {file_path}"
            if key in interesting_files:
                # check correctness
                assert interesting_files[key] == file_path, (key, file_path)
            else:
                interesting_files[key] = file_path

        # Select all files in the repo
        # pathlib.Path.glob used instead of glob.glob, as glob.glob could not search for a hidden files
        repo_files = pathlib.Path(f"{temp_dir}/{ownername}/{reponame}").glob("**/*")
        repo_files = [str(p) for p in repo_files if p.is_file() and not p.is_symlink()]
        files_found = set()
        ids_found = set()

        # For each file find its mapping to the metadata or skip
        for full_path in repo_files:
            short_path = os.path.relpath(full_path, f"{temp_dir}/{ownername}/{reponame}/").replace('\\', '/')
            file_id = hashlib.sha256(short_path.encode()).hexdigest()[:8]
            _, file_extension = os.path.splitext(full_path)
            file_type = get_file_type(short_path, file_extension)
            # copy all files if empty meta file except .git/* and .xml files
            if file_id in interesting_files.keys() \
                    or not meta_rows and "/.git/" not in full_path and not full_path.endswith(".xml"):
                files_found.add(full_path)
                ids_found.add(file_id)
                logger.debug(f"COPY {full_path} ; {short_path} -> {file_id} : {new_repo_id} : {file_type}")
            else:
                logger.debug(f"SKIP {full_path} ; {short_path} -> {file_id} : {new_repo_id} : {file_type}")

        # Check if there are files that present in meta but we could not find, or we somehow found files not from meta
        if meta_rows and 0 != len(ids_found.symmetric_difference(set(interesting_files.keys()))):
            logger.error(f"Couldn't find all files mentioned in metadata for {new_repo_id} repo. "
                         f"Removing {meta_file_path}, so missing files would not count in the dataset statistics. "
                         f"You can use git to restore {meta_file_path} file back")
            missing_repos.append(meta_file_path)
            if os.path.exists(meta_file_path):
                os.rename(meta_file_path, f"{meta_file_path}.bak")
            continue

        # Copy files to new dataset location
        for j, full_path in enumerate(sorted(list(files_found))):
            short_path = os.path.relpath(full_path, f"{temp_dir}/{ownername}/{reponame}/").replace('\\', '/')
            _, file_extension = os.path.splitext(full_path)
            file_type = get_file_type(short_path, file_extension)
            file_id = hashlib.sha256(short_path.encode()).hexdigest()[:8]
            logger.debug(f"{full_path} -> {file_id}")

            code_file_basedir = f'{dataset_dir}/{new_repo_id}/{file_type}'
            code_file_location = f'{code_file_basedir}/{file_id}{file_extension}'

            for row in meta_rows:
                if row.FilePath == code_file_location:
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

        license_files = collect_licenses(temp_dir, ownername, reponame)

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


CHARS4RAND = (string.ascii_lowercase + string.ascii_uppercase).encode("ascii")
DIGITS = string.digits.encode("ascii")
# 0 on first position may break json e.g. "id":123, -> "qa":038, which is incorrect json
DIGITS4RAND = DIGITS[1:]


def obfuscate_jwt(value: str) -> str:
    len_value = len(value)
    pad_num = 0x3 & len(value)
    if pad_num:
        value += '=' * (4 - pad_num)
    if '-' in value or '_' in value:
        decoded = base64.b64decode(value, altchars=b"-_", validate=True)
    else:
        decoded = base64.b64decode(value, validate=True)
    new_json = bytearray(len(decoded))
    backslash = False
    n = 0
    while len(decoded) > n:
        if backslash:
            new_json[n] = 0x3F  # ord('?')
            backslash = False
            n += 1
            continue
        if decoded[n] in b'nft"':
            reserved_word_found = False
            for wrd in [
                # reserved words in JSON
                b"null", b"false", b"true",
                # trigger words from CredSweeper filter ValueJsonWebTokenCheck
                b'"alg":', b'"apu":', b'"apv":', b'"aud":', b'"b64":', b'"crit":', b'"crv":', b'"cty":', b'"d":',
                b'"dp":', b'"dq":', b'"e":', b'"enc":', b'"epk":', b'"exp":', b'"ext":', b'"iat":', b'"id":', b'"iss":',
                b'"iv":', b'"jku":', b'"jti":', b'"jwk":', b'"k":', b'"key_ops":', b'"keys":', b'"kid":', b'"kty":',
                b'"n":', b'"nbf":', b'"nonce":', b'"oth":', b'"p":', b'"p2c":', b'"p2s":', b'"password":', b'"ppt":',
                b'"q":', b'"qi":', b'"role":', b'"secret":', b'"sub":', b'"svt":', b'"tag":', b'"token":', b'"typ":',
                b'"url":', b'"use":', b'"x":', b'"x5c":', b'"x5t":', b'"x5t#S256":', b'"x5u":', b'"y":', b'"zip":'
            ]:
                # safe words to keep JSON structure (false, true, null)
                # and important JWT ("alg", "type", ...)
                if decoded[n:n + len(wrd)] == wrd:
                    end_pos = n + len(wrd)
                    while n < end_pos:
                        new_json[n] = decoded[n]
                        n += 1
                    reserved_word_found = True
                    break
            if reserved_word_found:
                continue
        # any other data will be obfuscated
        if decoded[n] in DIGITS:
            new_json[n] = random.choice(DIGITS4RAND)
        elif decoded[n] in CHARS4RAND:
            new_json[n] = random.choice(CHARS4RAND)
        elif '\\' == decoded[n]:
            new_json[n] = 0x3F  # ord('?')
            backslash = True
        else:
            new_json[n] = decoded[n]
        n += 1

    encoded = base64.b64encode(new_json, altchars=b"-_").decode("ascii")
    while len(encoded) > len_value:
        encoded = encoded[:-1]
    assert len(encoded) == len_value

    return encoded


def get_obfuscated_value(value, meta_row: MetaRow):
    if "Info" == meta_row.PredefinedPattern:
        # not a credential - does not require obfuscation
        obfuscated_value = value
    elif any(value.startswith(x) for x in ["AKIA", "ABIA", "ACCA", "AGPA", "AIDA", "AIPA", "AKIA", "ANPA", "ANVA",
                                           "AROA", "APKA", "ASCA", "ASIA", "AIza"]) \
            or value.startswith("xox") and 15 <= len(value) and value[3] in "aboprst" and '-' == value[4]:
        obfuscated_value = value[:4] + generate_value(value[4:])
    elif any(value.startswith(x) for x in ["ya29."]):
        obfuscated_value = value[:5] + generate_value(value[5:])
    elif any(value.startswith(x) for x in ["whsec_", "Basic ", "OAuth "]):
        obfuscated_value = value[:6] + generate_value(value[6:])
    elif any(value.startswith(x) for x in ["hexkey:", "base64:", "phpass:", "Bearer ", "Apikey "]):
        obfuscated_value = value[:7] + generate_value(value[7:])
    elif any(value.startswith(x) for x in
             ["hexpass:", "hexsalt:", "pk_live_", "rk_live_", "sk_live_", "pk_test_", "rk_test_", "sk_test_"]):
        obfuscated_value = value[:8] + generate_value(value[8:])
    elif any(value.startswith(x) for x in ["SWMTKN-1-"]):
        obfuscated_value = value[:9] + generate_value(value[9:])
    elif any(value.startswith(x) for x in ["hexsecret:"]):
        obfuscated_value = value[:10] + generate_value(value[10:])
    elif value.startswith("eyJ"):
        # Check if it's a proper "JSON Web Token" with header and payload
        if "." in value:
            split_jwt = value.split(".")
            obf_jwt = []
            for part in split_jwt:
                if part.startswith("eyJ"):
                    obfuscated = obfuscate_jwt(part)
                else:
                    obfuscated = generate_value(part)
                obf_jwt.append(obfuscated)
            obfuscated_value = '.'.join(obf_jwt)
        else:
            obfuscated_value = obfuscate_jwt(value)
    elif value.startswith("hooks.slack.com/services/"):
        obfuscated_value = "hooks.slack.com/services/" + generate_value(value[25:])
    elif (value.startswith("wx") and 18 == len(value)
          or (any(value.startswith(x) for x in
                  ["AC", "AD", "AL", "CA", "CF", "CL", "CN", "CR", "FW", "IP", "KS", "MM", "NO", "PK", "PN", "QU", "RE",
                   "SC", "SD", "SK", "SM", "TR", "UT", "XE", "XR"]) and 34 == len(value))):
        obfuscated_value = value[:2] + generate_value(value[2:])
    elif value.startswith("00D") and (12 <= len(value) <= 18 or '!' in value):
        obfuscated_value = value[:3] + generate_value(value[3:])
    elif ".apps.googleusercontent.com" in value:
        pos = value.index(".apps.googleusercontent.com")
        obfuscated_value = generate_value(value[:pos]) + ".apps.googleusercontent.com" + generate_value(
            value[pos + 27:])
    elif ".s3.amazonaws.com" in value:
        pos = value.index(".s3.amazonaws.com")
        obfuscated_value = generate_value(value[:pos]) + ".s3.amazonaws.com" + generate_value(value[pos + 17:])
    elif ".firebaseio.com" in value:
        pos = value.index(".firebaseio.com")
        obfuscated_value = generate_value(value[:pos]) + ".firebaseio.com" + generate_value(value[pos + 15:])
    elif ".firebaseapp.com" in value:
        pos = value.index(".firebaseapp.com")
        obfuscated_value = generate_value(value[:pos]) + ".firebaseapp.com" + generate_value(value[pos + 16:])
    else:
        obfuscated_value = generate_value(value)

    return obfuscated_value


def check_asc_or_desc(line_data_value: str) -> bool:
    """ValuePatternCheck as example"""
    count_asc = 1
    count_desc = 1
    for i in range(len(line_data_value) - 1):
        if line_data_value[i] in string.ascii_letters + string.digits \
                and ord(line_data_value[i + 1]) - ord(line_data_value[i]) == 1:
            count_asc += 1
            if 4 == count_asc:
                return True
        else:
            count_asc = 1
        if line_data_value[i] in string.ascii_letters + string.digits \
                and ord(line_data_value[i]) - ord(line_data_value[i + 1]) == 1:
            count_desc += 1
            if 4 == count_desc:
                return True
        else:
            count_desc = 1
            continue
    return False


def generate_value(value):
    """Wrapper to skip obfuscation with false positive or negatives"""
    pattern_keyword = re.compile(r"(api|pass|pw[d\b])", flags=re.IGNORECASE)
    pattern_similar = re.compile(r"(\w)\1{3,}")
    new_value = None
    while new_value is None \
            or pattern_keyword.findall(new_value) \
            or pattern_similar.findall(new_value) \
            or check_asc_or_desc(new_value):
        new_value = gen_random_value(value)
    return new_value


def gen_random_value(value):
    obfuscated_value = ""

    digits_set = string.digits
    upper_set = string.ascii_uppercase
    lower_set = string.ascii_lowercase

    byte_hex = "0x" in value and "," in value
    base_32 = True
    hex_upper = True
    hex_lower = True
    for n, i in enumerate(value):
        if byte_hex and i not in "x0123456789ABCDEFabcdef, \t-{}[]()":
            # there may be an array in string e.g. CEKPET="[0xCA, 0xFE, ...]" - quoted value
            byte_hex = False
        if base_32 and i not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567":
            base_32 = False
        if '-' == i and len(value) in (18, 36) and n in (8, 13, 18, 23):
            # UUID separator or something like this
            continue
        if ':' == i and 2 == n % 3:
            # wifi key like 7f:44:52:fe: ...
            continue
        if hex_upper and i not in "0123456789ABCDEF":
            hex_upper = False
        if hex_lower and i not in "0123456789abcdef":
            hex_lower = False

    if hex_lower:
        lower_set = lower_set[:6]
    elif base_32 and not hex_upper:
        digits_set = digits_set[2:8]
    elif hex_upper:
        upper_set = upper_set[:6]

    web_escape_case = 0
    backslash_case = False
    hex_data = 0
    for v in value:
        if '%' == v:
            web_escape_case = 2
            backslash_case = False
            obfuscated_value += v
            continue
        if '\\' == v:
            web_escape_case = 0
            backslash_case = True
            obfuscated_value += v
            continue
        if 0 < web_escape_case:
            obfuscated_value += v
            web_escape_case -= 1
            continue
        if backslash_case:
            if 'x' == v:
                # obfuscation with hex \xeb should be \0xad but not \xxl
                hex_data = 2
            if 'u' == v:
                # unicode obfuscation
                hex_data = 4
            obfuscated_value += v
            backslash_case = False
            continue
        if byte_hex and ('0' == v or 'x' == v):
            # keep byte hex definition prefix '0x' in 0xFF, 0xAA, ...
            obfuscated_value += v
            continue

        if v in string.digits:
            obfuscated_value += random.choice(digits_set)
        elif v in string.ascii_lowercase[:6] and (0 < hex_data or byte_hex):
            obfuscated_value += random.choice(lower_set[:6])
        elif v in string.ascii_lowercase:
            obfuscated_value += random.choice(lower_set)
        elif v in string.ascii_uppercase[:6] and (0 < hex_data or byte_hex):
            obfuscated_value += random.choice(upper_set[:6])
        elif v in string.ascii_uppercase:
            obfuscated_value += random.choice(upper_set)
        else:
            obfuscated_value += v

        if 0 < hex_data:
            hex_data -= 1

    return obfuscated_value


def replace_rows(data: List[MetaRow]):
    # Change data in already copied files
    logger.info("Single line obfuscation")
    for row in data:
        # PEM keys and other multiple-line credentials is processed in other function
        if "" != row.CryptographyKey or row.LineEnd != row.LineStart:
            continue

        if 'T' != row.GroundTruth:
            # false cases do not require an onbuscation
            continue

        if not (0 <= row.ValueStart and 0 <= row.ValueEnd):
            continue

        if row.Category in ["IPv4", "IPv6", "AWS Multi", "Google Multi"]:
            # skip obfuscation for the categories which are multi pattern or info
            continue

        file_location = row.FilePath

        try:
            with open(file_location, "rb") as f:
                lines = f.read().decode().replace("\r\n", '\n').replace('\r', '\n').split('\n')
        except Exception as exc:
            logger.error(row)
            logger.critical(exc)
            return

        old_line = lines[row.LineStart - 1]
        value = old_line[row.ValueStart:row.ValueEnd]
        # credsweeper does not scan lines over 8000 symbols, so 1<<13 is enough
        random.seed((row.LineStart << 13 + row.ValueStart) ^ int(row.FileID, 16))
        obfuscated_value = get_obfuscated_value(value, row)
        new_line = old_line[:row.ValueStart] + obfuscated_value + old_line[row.ValueEnd:]

        lines[row.LineStart - 1] = new_line

        with open(file_location, "w", encoding="utf8") as f:
            f.write('\n'.join(lines))


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
            if j > 0 and char in ["n", "r"] and segment[j - 1] == "\\":
                new_line += char
            # Special case for preserving f"" and b"" lines
            elif j < len(segment) - 1 and char in ["b", "f"] and segment[j + 1] in ["'", '"']:
                new_line += char
            else:
                new_line += random.choice(string.ascii_letters)
        elif char in string.digits:
            new_line += random.choice(string.digits)
        else:
            new_line += char

    return new_line


def create_new_key(lines: List[str]):
    # Create new lines with similar formatting as old one
    new_lines = []
    pem_regex = re.compile(r"[0-9A-Za-z=/+_-]{16,}")

    is_first_segment = True
    for i, old_l in enumerate(lines):
        start, segment, end = split_in_bounds(i, len(lines), old_l)
        if segment is None:
            new_lines.append(old_l)
            continue

        # DEK-Info: AES-128-CBC, ...
        # Proc-Type: 4,ENCRYPTED
        # Version: GnuPG v1.4.9 (GNU/Linux)
        if "DEK-" in segment or "Proc-" in segment or "Version" in segment or not pem_regex.search(segment):
            new_line = segment
        elif is_first_segment:
            is_first_segment = False
            assert len(segment) >= 64, (segment, lines)
            new_line = segment[:64] + obfuscate_segment(segment[64:])
        else:
            new_line = obfuscate_segment(segment)

        new_l = start + new_line + end

        new_lines.append(new_l)

    return new_lines


def create_new_multiline(lines: List[str], starting_position: int):
    # Create new lines with similar formatting as old one
    new_lines = []

    first_line = lines[0]

    new_lines.append(first_line[:starting_position] + obfuscate_segment(first_line[starting_position:]))

    # Do not replace ssh-rsa substring if present
    if "ssh-rsa" in first_line:
        s = first_line.find("ssh-rsa")
        new_lines[0] = new_lines[0][:s] + "ssh-rsa" + new_lines[0][s + 7:]

    for i, old_l in enumerate(lines[1:]):
        new_line = obfuscate_segment(old_l)
        new_lines.append(new_line)

    return new_lines


def process_pem_key(row: MetaRow):
    # Change data in already copied files (only keys)
    try:
        # Skip credentials that are not PEM or multiline
        if row.CryptographyKey == "" and row.LineStart == row.LineEnd:
            return

        if row.Category in ["AWS Multi", "Google Multi"]:
            # skip double obfuscation for the categories
            return

        with open(row.FilePath, "r", encoding="utf8") as f:
            text = f.read()
        lines = text.split("\n")

        random.seed(row.LineStart ^ int(row.FileID, 16))

        if '' != row.CryptographyKey:
            new_lines = create_new_key(lines[row.LineStart - 1:row.LineEnd])
        else:
            new_lines = create_new_multiline(lines[row.LineStart - 1:row.LineEnd], row.ValueStart)

        lines[row.LineStart - 1:row.LineEnd] = new_lines

        with open(row.FilePath, "w", encoding="utf8") as f:
            f.write('\n'.join(lines))

    except Exception as exc:
        raise RuntimeError(f"FAILURE: {row}")


def process_pem_keys(data: List[MetaRow]):
    logger.info("Private key obfuscation")
    for row in data:
        if 'T' == row.GroundTruth and "Private Key" == row.Category:
            process_pem_key(row)


def obfuscate_creds(meta_dir: str, dataset_dir: str):
    all_credentials = []
    for meta_row in read_meta(meta_dir):
        meta_row.FilePath = meta_row.FilePath.replace("data", dataset_dir, 1)
        all_credentials.append(meta_row)
    all_credentials.sort(key=lambda x: (x.FilePath, x.LineStart, x.LineEnd, x.ValueStart, x.ValueEnd))
    replace_rows(all_credentials)
    process_pem_keys(all_credentials)


def main(args: Namespace):
    temp_directory = "tmp"

    if os.path.exists(args.data_dir):
        if not args.clean_data:
            raise FileExistsError(f"{args.data_dir} directory already exists. "
                                  f"Please remove it or select other directory.")
        shutil.rmtree(args.data_dir)

    if not args.skip_download:
        logger.info("Start download")
        download(temp_directory, 1 if not args.jobs else int(args.jobs))
        logger.info("Download finished. Now processing the files...")
    else:
        logger.info("Download skipped. Now processing the files...")
    removed_meta = move_files(temp_directory, args.data_dir)
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
