import random
import unittest

from obfuscate_creds import gen_random_value


class ObfuscatorTest(unittest.TestCase):

    def test_gen_random_value(self):
        for seed, value, expected in [
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
