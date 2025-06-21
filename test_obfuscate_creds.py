import random

from obfuscate_creds import gen_random_value


def test_gen_random_value():
    for seed, value, expected in (
            (0, "sdgfds", "mynbiq"),
            (42, "0,00,0x0BeDa0,0x24234,0x2342ULL", "0,01,0x0AfCb3,0x21819,0x6001ULL"),
    ):
        random.seed(seed)
        actual = gen_random_value(value)
        print(actual)
        assert actual == expected
