import unittest

from download_data import get_file_scope


class DownloadTest(unittest.TestCase):

    def test_get_file_scope(self):

        self.assertEqual("/local/lib/python/usr/",
                         get_file_scope("/usr/local/lib/python"))
        self.assertEqual("/conf/",
                         get_file_scope("config/config.yml"))
        self.assertEqual("/spec/",
                         get_file_scope("pet/modules/stdlib/spec/functions/t.rb"))
        self.assertEqual("/test/src/conf/resource/docker/",
                         get_file_scope("src/test/resources/dockerConfig/myDockerCfg"))
        self.assertEqual("/test/src/example/",
                         get_file_scope("testapi/src/java/TestApiExample.java"))
        self.assertEqual("/test/src/fixture/lib/",
                         get_file_scope("packages/src/lib/__tests__/fixtures/request.json"))
        self.assertEqual("/_/",
                         get_file_scope("X3"))
