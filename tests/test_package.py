import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from sftp_mounter.package import calculate_sha256, download_file, get_project_version

class TestPackage(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_get_project_version(self):
        version = get_project_version()
        self.assertEqual(version, "1.3.0")

    def test_calculate_sha256(self):
        test_file = os.path.join(self.test_dir, 'sample.txt')
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("SFTP Mounter Test Content")
        
        sha = calculate_sha256(test_file)
        self.assertEqual(len(sha), 64)
        self.assertTrue(sha.isalnum())

    @patch('urllib.request.urlopen')
    def test_download_file_success(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.side_effect = [b"chunk1", b"chunk2", b""]
        mock_urlopen.return_value.__enter__.return_value = mock_response

        target = os.path.join(self.test_dir, 'downloaded.bin')
        res = download_file("http://example.com/file.bin", target)
        self.assertTrue(res)
        self.assertTrue(os.path.exists(target))

    @patch('urllib.request.urlopen', side_effect=Exception("Network error"))
    def test_download_file_failure(self, mock_urlopen):
        target = os.path.join(self.test_dir, 'failed.bin')
        res = download_file("http://invalid.url/file.bin", target)
        self.assertFalse(res)

if __name__ == '__main__':
    unittest.main()
