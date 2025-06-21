import random

from obfuscate_creds import gen_random_value

import unittest


class ObfuscatorTest(unittest.TestCase):

    def test_gen_random_value(self):
        for seed, value, expected in (
                (
                        0,
                        "0x00, 0x00, 0x00, 0x00",
                        "0x66, 0x04, 0x87, 0x64"
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
        ):
            random.seed(seed)
            actual = gen_random_value(value)
            self.assertEqual( expected,  actual, (seed, value, expected, actual))
