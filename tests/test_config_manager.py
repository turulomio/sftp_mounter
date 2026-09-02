"""
Unit tests for the ConfigManager and credential persistence module of SFTP Mounter.

Verifies password encoding and decoding, profile loading/saving/deleting, and
general application configuration management under isolated temporary environments.
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from sftp_mounter.config_manager import ConfigManager, _encode_pass, _decode_pass


class TestConfigManager(unittest.TestCase):
    """
    Test suite for ConfigManager profile and settings persistence.
    """

    def setUp(self):
        """Sets up a mock APPDATA environment directory for testing configuration persistence."""
        self.test_dir = tempfile.mkdtemp()
        self.patcher = patch.dict(os.environ, {'APPDATA': self.test_dir})
        self.patcher.start()
        self.cm = ConfigManager()

    def tearDown(self):
        """Restores the environment variables and cleans up the temporary directory."""
        self.patcher.stop()
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_encode_decode_pass(self):
        """Tests reversible password obfuscation and fallback for unencoded plaintext."""
        self.assertEqual(_encode_pass(""), "")
        self.assertEqual(_decode_pass(""), "")

        secret = "MySecretPassword123!"
        encoded = _encode_pass(secret)
        self.assertNotEqual(encoded, secret)
        decoded = _decode_pass(encoded)
        self.assertEqual(decoded, secret)

        # Fallback decode for legacy plaintext strings
        self.assertEqual(_decode_pass("plain_text"), "plain_text")

    def test_save_and_get_profile(self):
        """Tests creating, persisting, and querying SFTP connection profiles."""
        profile_data = {
            "host": "sftp.example.com",
            "port": 22,
            "user": "testuser",
            "auth_type": "password",
            "password": "secretpassword",
            "drive_letter": "Z:"
        }
        self.cm.save_profile("TestServer", profile_data)

        profiles = self.cm.load_profiles()
        self.assertIn("TestServer", profiles)
        self.assertEqual(profiles["TestServer"]["password"], "secretpassword")

        p = self.cm.get_profile("TestServer")
        self.assertIsNotNone(p)
        self.assertEqual(p["host"], "sftp.example.com")

    def test_delete_profile(self):
        """Tests profile deletion and clean removal from configuration files."""
        profile_data = {"host": "sftp.example.com"}
        self.cm.save_profile("ToDelete", profile_data)
        self.assertIsNotNone(self.cm.get_profile("ToDelete"))

        res = self.cm.delete_profile("ToDelete")
        self.assertTrue(res)
        self.assertIsNone(self.cm.get_profile("ToDelete"))

    def test_settings(self):
        """Tests reading and updating global application settings."""
        self.cm.save_settings({"start_with_windows": True})
        settings = self.cm.load_settings()
        self.assertTrue(settings.get("start_with_windows"))
        self.assertEqual(settings.get("non_existent_key", "default_val"), "default_val")


if __name__ == '__main__':
    unittest.main()
