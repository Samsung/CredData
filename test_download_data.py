import json
import random
import unittest
from pathlib import Path

from download_data import get_file_scope


class DownloadTest(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None

    def test_get_file_scope(self):
        self.assertEqual("/local/lib/python/usr/",
                         get_file_scope("/usr/local/lib/python"))
        self.assertEqual("/conf/",
                         get_file_scope("config/config.yml"))
        self.assertEqual("/spec/modul/",
                         get_file_scope("pet/modules/stdlib/spec/functions/t.rb"))
        self.assertEqual("/test/src/conf/resource/docker/",
                         get_file_scope("src/test/resources/dockerConfig/myDockerCfg"))
        self.assertEqual("/test/src/example/",
                         get_file_scope("testapi/src/java/TestApiExample.java"))
        self.assertEqual("/test/src/fixture/lib/",
                         get_file_scope("packages/src/lib/__tests__/fixtures/request.json"))
        self.assertEqual("/_/",
                         get_file_scope("X3"))
        with open(Path(__file__).parent / "word_in_path.json") as f:
            words = json.load(f)
        big_path = '/'.join(words)
        file_scope_1 = get_file_scope(big_path)
        self.assertTrue(all(x in file_scope_1 for x in words))
        # /_/ should not present in a path with a known word
        self.assertNotIn('/_/', get_file_scope(f"/X3/{random.choice(words)}"))
