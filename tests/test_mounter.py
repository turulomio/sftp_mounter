"""
Unit tests for the Mounter engine and driver integration module of SFTP Mounter.

Verifies binary extraction, drive availability checks, password obscuring,
file checksums, and version detection fallbacks.
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from sftp_mounter.mounter import Mounter


class TestMounter(unittest.TestCase):
    """
    Test suite for Mounter lifecycle, path handling, and helper routines.
    """

    def setUp(self):
        """Sets up a temporary application directory environment for Mounter tests."""
        self.test_dir = tempfile.mkdtemp()
        self.patcher = patch.dict(os.environ, {'APPDATA': self.test_dir})
        self.patcher.start()

    def tearDown(self):
        """Stops environment patching and removes temporary directories."""
        self.patcher.stop()
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)

    @patch('sftp_mounter.mounter.Mounter.extract_binaries')
    def test_mounter_init(self, mock_extract):
        """Tests Mounter initialization, binary directory setup, and binary extraction call."""
        mounter = Mounter()
        self.assertTrue(os.path.exists(mounter.bin_dir))
        self.assertEqual(len(mounter.active_mounts), 0)
        mock_extract.assert_called_once()

    @patch('sftp_mounter.mounter.Mounter.extract_binaries')
    def test_get_bundled_path_dev(self, mock_extract):
        """Tests get_bundled_path behavior for non-existent assets in development mode."""
        mounter = Mounter()
        path = mounter.get_bundled_path("non_existent_file.xyz")
        self.assertIsNone(path)

    @patch('sftp_mounter.mounter.Mounter.extract_binaries')
    def test_is_drive_letter_in_use(self, mock_extract):
        """Tests that is_drive_letter_in_use returns a boolean flag for given drive letter."""
        mounter = Mounter()
        res = mounter.is_drive_letter_in_use("Z:")
        self.assertIsInstance(res, bool)

    @patch('sftp_mounter.mounter.Mounter.extract_binaries')
    @patch('os.path.exists', return_value=False)
    def test_is_actually_mounted(self, mock_exists, mock_extract):
        """Tests is_actually_mounted validation when mount target does not physically exist."""
        mounter = Mounter()
        self.assertFalse(mounter.is_actually_mounted("X:"))

    @patch('sftp_mounter.mounter.Mounter.extract_binaries')
    def test_obscure_password_fallback(self, mock_extract):
        """Tests obscure_password fallback behavior when rclone executable is unavailable."""
        mounter = Mounter()
        mounter.rclone_exe = "/non/existent/rclone.exe"
        raw_pass = "my_secret_pass"
        res = mounter.obscure_password(raw_pass)
        self.assertEqual(res, raw_pass)

    def test_calculate_file_sha256(self):
        """Tests static SHA-256 calculation on a known file."""
        test_file = os.path.join(self.test_dir, 'sha_test.txt')
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("Hello World")
        sha = Mounter.calculate_file_sha256(test_file)
        self.assertEqual(len(sha), 64)

    @patch('sftp_mounter.mounter.Mounter.extract_binaries')
    def test_versions(self, mock_extract):
        """Tests rclone version detection fallback when binary is missing."""
        mounter = Mounter()
        mounter.rclone_exe = "/non/existent/rclone.exe"
        r_ver = mounter.get_rclone_version()
        self.assertIn("Not detected", r_ver)


if __name__ == '__main__':
    unittest.main()
