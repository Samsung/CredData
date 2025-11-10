import base64
import logging
import random
import re
import string
import sys
from argparse import Namespace, ArgumentParser
from typing import List

from meta_row import read_meta, MetaRow

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(filename)s:%(lineno)s | %(message)s",
    level="INFO")
logger = logging.getLogger(__file__)

CHARS4RAND = (string.ascii_lowercase + string.ascii_uppercase).encode("ascii")
DIGITS = string.digits.encode("ascii")
# 0 on first position may break json e.g. "id":123, -> "qa":038, which is incorrect json
DIGITS4RAND = DIGITS[1:]

NKEY_SEED_PATTERN = re.compile(r"S[ACNOPUX][A-Z2-7]{40,200}")
GOOGLEAPI_PATTERN = re.compile(r"1//0[0-9A-Za-z_-]{80,400}")

OCT_PATTERN = re.compile(r"(\s*0[01234567]{0,3}(\s*,|\s*\Z))+$")
DEC_PATTERN = re.compile(r"(\s*(2([0-4][0-9]|5[0-5])|1[0-9][0-9]|[0-9][0-9]|[0-9])(\s*,|\s*\Z))+$")

def obfuscate_jwt(value: str) -> str:
    len_value = len(value)
    if value.endswith("%3D%3D%3D"):
        padding_web_escape = 3
        value = value[:-9] + "==="
    elif value.endswith("%3D%3D"):
        padding_web_escape = 2
        value = value[:-6] + "=="
    elif value.endswith("%3D"):
        padding_web_escape = 1
        value = value[:-3]
    else:
        padding_web_escape = 0
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
                b'"alg":', b'"apu":', b'"apv":', b'"aud":', b'"b64":', b'"crit":', b'"crv":', b'"cty":',
                b'"d":', b'"dp":', b'"dq":', b'"e":', b'"enc":', b'"epk":', b'"exp":', b'"ext":', b'"iat":',
                b'"id":', b'"iss":', b'"iv":', b'"jku":', b'"jti":', b'"jwk":', b'"k":', b'"key_ops":',
                b'"keys":', b'"kid":', b'"kty":', b'"n":', b'"nbf":', b'"nonce":', b'"oth":', b'"p":',
                b'"p2c":', b'"p2s":', b'"password":', b'"ppt":', b'"q":', b'"qi":', b'"role":', b'"secret":',
                b'"sub":', b'"svt":', b'"tag":', b'"token":', b'"typ":', b'"url":', b'"use":', b'"x":',
                b'"x5c":', b'"x5t":', b'"x5t#S256":', b'"x5u":', b'"y":', b'"zip":', b'"o":', b'"m":'
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
    if padding_web_escape:
        encoded = encoded[:-padding_web_escape] + '%3D' * padding_web_escape
    while len(encoded) > len_value:
        assert '=' == encoded[-1], encoded
        encoded = encoded[:-1]
    assert len(encoded) == len_value

    return encoded


def obfuscate_basic_auth(value):
    # rfc7617 uses standard base64 encoding from rfc4648#section-4
    len_value = len(value)
    pad_num = 0x3 & len(value)
    if pad_num:
        value += '=' * (4 - pad_num)
    decoded = base64.b64decode(value,validate=True)
    basic = decoded.decode("utf_8")
    new_basic = generate_value(basic)
    encoded = base64.b64encode(new_basic.encode("utf_8")).decode("ascii")
    while len(encoded) > len_value:
        # only padding sign may be truncated
        assert '=' == encoded[-1], encoded
        encoded = encoded[:-1]
    assert len(encoded) == len_value
    return encoded


def get_obfuscated_value(value, meta_row: MetaRow):
    if "Info" == meta_row.PredefinedPattern:
        # not a credential - does not require obfuscation
        obfuscated_value = value
    elif "Basic Authorization" in meta_row.Category:
        obfuscated_value = obfuscate_basic_auth(value)
    elif any(value.startswith(x) for x in ["AKIA", "ABIA", "ACCA", "AGPA", "AIDA", "AIPA", "AKIA", "ANPA",
                                           "ANVA", "AROA", "APKA", "ASCA", "ASIA", "AIza"]) \
            or value.startswith('1//0') and GOOGLEAPI_PATTERN.match(value) \
            or value.startswith('key-') and 36 == len(value) \
            or value.startswith("xox") and 15 <= len(value) and value[3] in "abeoprst" and '-' == value[4]:
        obfuscated_value = value[:4] + generate_value(value[4:])
    elif any(value.startswith(x) for x in ["ya29.", "pass:", "salt:", "akab-", "PMAK-", "PMAT-", "xapp-"]):
        obfuscated_value = value[:5] + generate_value(value[5:])
    elif any(value.startswith(x) for x in ["whsec_", "Basic ", "OAuth "]):
        obfuscated_value = value[:6] + generate_value(value[6:])
    elif any(value.startswith(x) for x in ["hexkey:", "base64:", "phpass:", "Bearer ", "Apikey "]):
        obfuscated_value = value[:7] + generate_value(value[7:])
    elif any(value.startswith(x) for x in
             ["hexpass:", "hexsalt:", "pk_live_", "rk_live_", "sk_live_", "pk_test_", "rk_test_", "sk_test_"]):
        obfuscated_value = value[:8] + generate_value(value[8:])
    elif any(value.startswith(x) for x in ["SWMTKN-1-", "dckr_pat_", "dckr_oat_"]):
        obfuscated_value = value[:9] + generate_value(value[9:])
    elif any(value.startswith(x) for x in ["hexsecret:"]):
        obfuscated_value = value[:10] + generate_value(value[10:])
    elif any(value.startswith(x) for x in ["ED25519-1-Raw:ED25519:"]):
        obfuscated_value = value[:22] + generate_value(value[22:])
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
    elif 18 == len(value) and value.startswith("wx") \
            or 34 == len(value) and any(value.startswith(x) for x in
                                        ["AC", "AD", "AL", "CA", "CF", "CL", "CN", "CR", "FW", "IP",
                                         "KS", "MM", "NO", "PK", "PN", "QU", "RE", "SC", "SD", "SK",
                                         "SM", "TR", "UT", "XE", "XR"]) \
            or value.startswith('S') and NKEY_SEED_PATTERN.match(value):
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
    if value == obfuscated_value:
        logger.warning(f"The same value: {value}, {str(meta_row)}")
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
    pattern_keyword = re.compile(r"(api|key|pass|pw[d\b])", flags=re.IGNORECASE)
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

    oct_set = list("01234567")
    dec_set = list(string.digits)
    upper_set = string.ascii_uppercase
    lower_set = string.ascii_lowercase
    hex_upper_lower_set = set(string.digits + string.ascii_uppercase[:6] + string.ascii_lowercase[:6])
    hex_char_in_values_set = hex_upper_lower_set | set(" xULul,mrst\t-{}[]()/*")
    hex_upper_lower_x_set = hex_upper_lower_set | set('x')

    byte_oct = bool(OCT_PATTERN.match(value))
    byte_dec = bool(DEC_PATTERN.match(value)) and not byte_oct
    byte_hex = "0x" in value and "," in value
    base_32 = True
    hex_upper = True
    hex_lower = True
    for n, v in enumerate(value):
        if byte_hex and v not in hex_char_in_values_set:
            # 0x12, /* master */ 0xfe - the case
            # there may be an array in string e.g. CEKPET="[0xCA, 0xFE, ...]" - quoted value
            byte_hex = False
        if base_32 and v not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567":
            base_32 = False
        if '-' == v and len(value) in (18, 36, 50, 59) and n in (8, 13, 18, 23, 24, 32, 40):
            # UUID separator or something like this
            continue
        if ':' == v and 2 == n % 3:
            # wifi key like 7f:44:52:fe: ...
            continue
        if hex_upper and v not in "0123456789ABCDEF":
            hex_upper = False
        if hex_lower and v not in "0123456789abcdef":
            hex_lower = False

    if hex_lower:
        lower_set = lower_set[:6]
    elif base_32 and not hex_upper:
        dec_set = dec_set[2:8]
    elif hex_upper:
        upper_set = upper_set[:6]

    web_escape_case = 0
    backslash_case = False
    hex_data = 0
    for n, v in enumerate(value):
        _v = obfuscated_value[n - 1] if 1 <= n else None
        __v = obfuscated_value[n - 2] if 2 <= n else None
        v_ = value[n + 1] if (n + 1) < len(value) else None
        v__ = value[n + 2] if (n + 2) < len(value) else None
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
        if byte_oct and '0' == v and _v not in oct_set:
            # keep byte oct definition prefix '000'. e.g. 066 -> 077, 077 -> 033
            obfuscated_value += v
            continue
        if byte_hex and (v in "xLUlu" or '0' == v and _v not in hex_upper_lower_x_set):
            # keep byte hex definition prefix '000' or '0x'. e.g. 0x00 -> 0x42, 007 -> 033
            obfuscated_value += v
            continue

        if byte_oct and v in oct_set:
            obfuscated_value += random.choice(oct_set)
        elif byte_dec and v in dec_set:
            if __v in dec_set and _v in dec_set:
                # 255
                #   ^
                if '2' == __v and '5' == _v:
                    obfuscated_value += random.choice("012345")
                else:
                    obfuscated_value += random.choice(dec_set)
            elif __v not in dec_set and _v in dec_set and v_ in dec_set:
                # 255
                #  ^
                if '2' == _v:
                    obfuscated_value += random.choice("012345")
                else:
                    obfuscated_value += random.choice(dec_set)
            elif __v not in dec_set and _v in dec_set and v_ not in dec_set:
                # 99
                #  ^
                obfuscated_value += random.choice(dec_set)
            elif _v not in dec_set:
                # 9,127,
                #   ^
                if v_ in dec_set and v__ in dec_set:
                    obfuscated_value += random.choice("12")
                elif v_ not in dec_set:
                    # single digit may be 0
                    obfuscated_value += random.choice(dec_set)
                else:
                    # first digit should be not 0
                    obfuscated_value += random.choice("123456789")
            else:
                # ??
                raise ValueError(value)
        elif v in string.digits:
            obfuscated_value += random.choice(dec_set)
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


def replace_rows(data: List[MetaRow], lines: List[str]):
    # Change data in already copied files
    for row in data:
        # PEM keys and other multiple-line credentials is processed in other function
        if "" != row.CryptographyKey or row.LineEnd != row.LineStart:
            continue

        if 'T' != row.GroundTruth:
            # false cases do not require an obfuscation
            continue

        if not (0 <= row.ValueStart and 0 <= row.ValueEnd):
            continue

        if row.Category in ["AWS Multi", "Google Multi"]:
            # skip obfuscation for the categories which are multi pattern
            continue

        old_line = lines[row.LineStart - 1]
        value = old_line[row.ValueStart:row.ValueEnd]
        # CredSweeper may scan huge lines since v1.6
        random.seed((row.ValueStart | (row.LineStart << 16)) ^ int(row.FileID, 16))
        obfuscated_value = get_obfuscated_value(value, row)
        new_line = old_line[:row.ValueStart] + obfuscated_value + old_line[row.ValueEnd:]

        lines[row.LineStart - 1] = new_line


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


def process_pem_key(row: MetaRow, lines:List[str]):
    # Change data in already copied files (only keys)
    try:
        # Skip credentials that are not PEM or multiline
        if row.CryptographyKey == "" and row.LineStart == row.LineEnd:
            return

        if row.Category in ["AWS Multi", "Google Multi"]:
            # skip double obfuscation for the categories
            return

        random.seed(row.LineStart ^ int(row.FileID, 16))

        if '' != row.CryptographyKey:
            new_lines = create_new_key(lines[row.LineStart - 1:row.LineEnd])
        else:
            new_lines = create_new_multiline(lines[row.LineStart - 1:row.LineEnd], row.ValueStart)

        lines[row.LineStart - 1:row.LineEnd] = new_lines

    except Exception as exc:
        logger.error(f"FAILURE: {row}")
        logger.critical(exc)
        raise

def process_pem_keys(data: List[MetaRow], lines:List[str]):
    for row in data:
        if 'T' == row.GroundTruth and "Private Key" == row.Category:
            process_pem_key(row, lines)


def obfuscate_creds(meta_dir: str, dataset_dir: str):
    dataset_files = {}
    for meta_row in read_meta(meta_dir):
        meta_row.FilePath = meta_row.FilePath.replace("data", dataset_dir, 1)
        if meta_row.FilePath in dataset_files:
            dataset_files[meta_row.FilePath].append(meta_row)
        else:
            dataset_files[meta_row.FilePath] = [meta_row]
    logger.info(f"Obfuscate {len(dataset_files)} files")
    for dataset_file, meta_rows in dataset_files.items():
        try:
            with open(dataset_file, "rb") as f:
                lines = f.read().decode().replace("\r\n", '\n').replace('\r', '\n').split('\n')
        except Exception as exc:
            logger.error(dataset_file)
            logger.critical(exc)
            raise
        meta_rows.sort(key=lambda x: (x.LineStart, x.LineEnd, x.ValueStart, x.ValueEnd))
        replace_rows(meta_rows, lines)
        process_pem_keys(meta_rows, lines)

        with open(dataset_file, "w", encoding="utf8") as f:
            f.write('\n'.join(lines))


def main(args: Namespace):
    obfuscate_creds(args.meta_dir, args.data_dir)
    logger.info(f"Obfuscation was done")
    return 0


if __name__ == "__main__":
    parser = ArgumentParser(prog="python obfuscate_creds.py")

    parser.add_argument("--meta_dir", dest="meta_dir", default="meta", help="Dataset markup")
    parser.add_argument("--data_dir", dest="data_dir", default="data", help="Dataset location after download")
    parser.add_argument("--jobs", dest="jobs", help="Jobs for multiprocessing")
    _args = parser.parse_args()

    sys.exit(main(_args))
