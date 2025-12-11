import binascii
import random
import unittest

from constants import PRIVATE_KEY_CATEGORY, LABEL_TRUE
from meta_row import MetaRow
from obfuscate_creds import gen_random_value, obfuscate_jwt, obfuscate_glsa, process_pem_key


class ObfuscatorTest(unittest.TestCase):

    def test_gen_random_value(self):
        for seed, value, expected in [
            (
                    654_987,
                    "b1:c2:c4:d9:9a:8e:78:98:aa:a8:b9:8b:bc:d9:8e:ef",
                    "b3:f9:b1:f1:6c:0f:99:62:ba:e5:b4:7b:ab:f9:7a:ed",
            ),
            (
                    1978_6574,
                    "b1c2c4d9 9a8e7898 aaa8b98b bcd98eef",
                    "b9a7a6f9 2a6d2015 bad9c44b edf78eed",
            ),
            (
                    # Postman cred PMAK-
                    59,
                    "0123456789abcdef01234567-0123456789abcdef0123456789abcdef00",
                    "3170240907ddecbf95281150-5410319914cafeff9159260174eebcef64",
            ),
            (
                    # UUID
                    36,
                    "79FA3A01-1BCE-C896-F2C8-69F4C10294E1",
                    "50AC1A82-3CFF-D584-E1E6-76C6B62187F3",
            ),
            (
                    # UUID mixed case style
                    36,
                    "79FA3A01-1BCE-cafe-F2C8-69F4C10294E1",
                    "50AZ4C08-2HIX-unlr-I8C9-67M5Y63621Q7",
            ),
            (
                    # mailgun
                    50,
                    "5a5f470fa9c943c05859b4b028372761-32ba5fe3-094446db",
                    "7c5f375ae5b812c15533a5e961195603-54df1bd4-972493ee",
            ),
            (
                    1,
                    "90, 134, 91, 94, 1, 38, 21, 116, 63, 214, 23, 184, 123,",
                    "39, 141, 87, 86, 3, 27, 16, 240, 84, 191, 60, 108, 163,",
            ),
            # not dec or hex bytes definition
            (
                    1,
                    " 00 00 00 00 	 00 00 00   00\t",
                    " 29 14 17 77 	 63 17 06   69\t",
            ),
            # seed=256 and data under 256
            (
                    256,
                    "	 192 	, 	255	 ",
                    "	 226 	, 	230	 "
            ),
            # seed=256 and data over 255
            (
                    256,
                    "	 192 	, 	256	 ",
                    "	 746 	, 	560	 "
            ),
            (
                    0o777,
                    "0777,0444",
                    "0171,0237"
            ),
            (
                    0,
                    "0x00, 0x00, 0x00, 0x00",
                    "0x66, 0x04, 0x87, 0x64"
            ),
            (
                    8,
                    "04,01,06, 07, 0",
                    "03,05,06, 02, 0"
            ),
            (
                    8,
                    "074,\t012,044, 067, 066, 0777",
                    "035,	062,030, 012, 033, 0607"
            ),
            (
                    10,
                    "074,0,066, 256, 333, 897",
                    "906,7,903, 774, 208, 751"
            ),
            (
                    10,
                    "192,168,255,1,\t65536,32768,16384,0,1",
                    "906,790,377,4,	20875,13506,29566,4,4"
            ),
            (
                    10,
                    "1111,0,1,2,3",
                    "9067,9,0,3,7"
            ),
            (
                    1,
                    "0x00, 0x00, 0x00, 0x00",
                    "0x29, 0x14, 0x17, 0x77"
            ),
            (
                    4,
                    "0,00,000,0x0BeDa0,0x24234,0x2342ULL",
                    "0,03,041,0x6DbAa0,0x68403,0x8854ULL"
            ),
            (
                    2,
                    "sdgfds",
                    "bcclfx"
            ),
        ]:
            random.seed(seed)
            actual = gen_random_value(value)
            self.assertEqual(expected, actual, (seed, value, expected, actual))

    def test_dec(self):
        original_data = random.randbytes(1000)
        dec_string = ''
        for i in original_data:
            if dec_string:
                dec_string += ' ' * random.randint(0, 4)
                dec_string += ','
            dec_string += ' ' * random.randint(0, 4)
            dec_string += str(i)
        print(dec_string)
        obfuscated_string = gen_random_value(dec_string)
        for i in obfuscated_string.split(','):
            d = int(i.strip())
            self.assertLessEqual(0, d)
            self.assertGreaterEqual(255, d)

    def test_obfuscate_jwt(self):
        value = "eyJhbGciOjEwfQ%3D%3D"
        obfuscated = obfuscate_jwt(value)
        self.assertNotEqual(value, obfuscated)
        self.assertEqual(len(value), len(obfuscated))
        value = "eyJhbGciOiI+LHgifQ=="
        obfuscated = obfuscate_jwt(value)
        self.assertNotEqual(value, obfuscated)
        self.assertEqual(len(value), len(obfuscated))
        with self.assertRaises(binascii.Error):
            # '+' is web escaped to %2B - cannot be obfuscated with the same value length
            obfuscate_jwt("eyJhbGciOiI%2BLHgifQ%3D%3D")

    def test_obfuscate_glsa(self):
        random.seed(20251110)
        # the value from CredSweeper samples
        value = "glsa_ThisI5NtTheTok3nYou8reLo0k1ngF0r_0a2a3df7"
        obfuscated = obfuscate_glsa(value)
        self.assertNotEqual(value, obfuscated)
        self.assertEqual(len(value), len(obfuscated))
        # tested value
        self.assertEqual("glsa_DaldL9OnCudSrj7jWui7wxVj9b4ltV2p_c97ad013", obfuscated)

    def test_obfuscate_pem(self):
        random.seed(20251211)
        original_lines = [
            "BOM",
            "/* some comment */ -----BEGIN RSA PRIVATE KEY----- any dummy info",
            "MIIEpQIBAAKCAQEA5mPfjyiQnuiLJPn63vr4sznghBRxzX/FirstLineFixed+J4",
            "MIIEpQIBAAKCAQEA5mPfjyiQnuiLJPn63vr4sznghBRxzX/SeconLineUpdat+J4",
            "MIIEpQIBAAKCAQEA5mPfjyiQnuiLJPn63vr4sznghBRxzX/ThirdLineUpdat+J4",
            "unhanged====",
            "-----END RSA PRIVATE KEY-----",
            "EOF",
        ]
        obfuscated_lines = [
            "BOM",
            "/* some comment */ -----BEGIN RSA PRIVATE KEY----- any dummy info",
            "MIIEpQIBAAKCAQEA5mPfjyiQnuiLJPn63vr4sznghBRxzX/FirstLineFixed+J4",
            'hVBzwYLllXwvsCqC1vIWiVSUrVpchQV32XB7LPfyjpSLlG/SRIMrpCDoiMWFl+A5',
            'ktePWZqcrQEoRLDs1dSJXpLKJSQmroj63oC4xTJPSITaEd/IoPwOBdRoaTEtW+x3',
            "unhanged====",
            "-----END RSA PRIVATE KEY-----",
            "EOF"]
        row = MetaRow({"Id": 1,
                       "FileID": "01234567",
                       "Domain": "str",
                       "RepoName": "98765432",
                       "FilePath": "str",
                       "LineStart": 2,
                       "LineEnd": len(original_lines) + 1,
                       "GroundTruth": LABEL_TRUE,
                       "ValueStart": 19,
                       "ValueEnd": 29,
                       "CryptographyKey": "",
                       "PredefinedPattern": "",
                       "Category": PRIVATE_KEY_CATEGORY})
        process_pem_key(row, original_lines, 0)
        self.assertListEqual(obfuscated_lines, original_lines)
