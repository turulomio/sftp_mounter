"""
Unit tests for the binary preparation and packaging module of SFTP Mounter.

Verifies project version resolution, SHA-256 hash calculation on binary files,
and remote dependency download workflows with mock network handlers.
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from sftp_mounter.package import calculate_sha256, download_file, get_project_version


class TestPackage(unittest.TestCase):
    """
    Test suite for packaging scripts and dependency preparation tools.
    """

    def setUp(self):
        """Creates a temporary workspace directory for test artifacts."""
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Cleans up the temporary workspace directory after each test."""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_get_project_version(self):
        """Tests that get_project_version extracts the version correctly from pyproject.toml."""
        version = get_project_version()
        self.assertEqual(version, "1.4.0")

    def test_calculate_sha256(self):
        """Tests that calculate_sha256 generates a valid 64-character hexadecimal checksum."""
        test_file = os.path.join(self.test_dir, 'sample.txt')
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("SFTP Mounter Test Content")

        sha = calculate_sha256(test_file)
        self.assertEqual(len(sha), 64)
        self.assertTrue(sha.isalnum())

    @patch('urllib.request.urlopen')
    def test_download_file_success(self, mock_urlopen):
        """Tests successful HTTP file download with chunked streaming."""
        mock_response = MagicMock()
        mock_response.read.side_effect = [b"chunk1", b"chunk2", b""]
        mock_urlopen.return_value.__enter__.return_value = mock_response

        target = os.path.join(self.test_dir, 'downloaded.bin')
        res = download_file("http://example.com/file.bin", target)
        self.assertTrue(res)
        self.assertTrue(os.path.exists(target))

    @patch('urllib.request.urlopen', side_effect=Exception("Network error"))
    def test_download_file_failure(self, mock_urlopen):
        """Tests download error handling when network requests fail."""
        target = os.path.join(self.test_dir, 'failed.bin')
        res = download_file("http://invalid.url/file.bin", target)
        self.assertFalse(res)


if __name__ == '__main__':
    unittest.main()
