import json
import random
import unittest
from pathlib import Path

from unittest.mock import patch

from download_data import (
    download_and_check,
    get_file_scope,
    validate_github_repo_url,
)


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

    def test_validate_github_repo_url(self):
        valid_urls = [
            "https://github.com/Samsung/CredData",
            "https://github.com/Samsung/CredData.git",
        ]
        invalid_urls = [
            "http://github.com/owner/repo",
            "https://evil.example/owner/repo",
            "https://github.com/owner/repo/extra",
            "https://github.com/owner/repo;touch",
            "https://github.com/owner/repo?next=evil",
        ]

        for url in valid_urls:
            with self.subTest(url=url):
                validate_github_repo_url(url)

        for url in invalid_urls:
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    validate_github_repo_url(url)

    @patch("download_data.subprocess.run")
    def test_malicious_url_is_rejected_before_git(self, mock_run):
        malicious_url = (
            "https://github.com/owner/repo;"
            " touch /tmp/creddata-pwned"
        )
        repo_id = "a" * 40 + "0" * 24

        with self.assertRaises(ValueError):
            download_and_check((repo_id, malicious_url))

        mock_run.assert_not_called()

    @patch("download_data.os.path.exists", return_value=False)
    @patch("download_data.shutil.rmtree")
    @patch("download_data.os.mkdir")
    @patch("download_data.subprocess.run")
    def test_git_commands_use_argument_lists(
        self,
        mock_run,
        mock_mkdir,
        mock_rmtree,
        mock_exists,
    ):
        repo_id = "a" * 40 + "0" * 24

        download_and_check(
            (repo_id, "https://github.com/owner/repo")
        )

        self.assertTrue(mock_run.call_args_list)
        for call in mock_run.call_args_list:
            self.assertIsInstance(call.args[0], list)
            self.assertNotIn("shell", call.kwargs)

