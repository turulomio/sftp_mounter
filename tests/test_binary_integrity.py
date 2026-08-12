import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    import PySide6
    pyside_dir = os.path.dirname(PySide6.__file__)
    if pyside_dir not in os.environ.get('PATH', ''):
        os.environ['PATH'] = pyside_dir + os.path.pathsep + os.environ.get('PATH', '')
    if hasattr(os, 'add_dll_directory'):
        try:
            os.add_dll_directory(pyside_dir)
        except Exception:
            pass
except Exception:
    pass

from PySide6.QtWidgets import QApplication

from sftp_mounter.mounter import Mounter
from sftp_mounter.i18n import I18N, SUPPORTED_LANGUAGES
from sftp_mounter.gui import MainWindow, BinaryIntegrityWorker

app = QApplication.instance() or QApplication(sys.argv)


class TestBinaryIntegrity(unittest.TestCase):
    def test_calculate_file_sha256(self):
        """Test hash calculation on known content."""
        mounter = Mounter()
        # Non-existent file should return empty string
        self.assertEqual(mounter.calculate_file_sha256("/non/existent/file.txt"), "")

        # Test on temporary file
        temp_file = os.path.join(mounter.app_dir, "test_hash_sample.tmp")
        try:
            with open(temp_file, "wb") as f:
                f.write(b"hello world")
            # SHA-256 for "hello world"
            expected = "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
            calculated = mounter.calculate_file_sha256(temp_file)
            self.assertEqual(calculated, expected)
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def test_get_binary_integrity_info(self):
        """Test get_binary_integrity_info structure and local hash calculation."""
        mounter = Mounter()
        info = mounter.get_binary_integrity_info()
        self.assertIn('rclone', info)
        self.assertIn('winfsp_msi', info)

        for comp in ['rclone', 'winfsp_msi']:
            self.assertIn('path', info[comp])
            self.assertIn('hash', info[comp])

    def test_i18n_integrity_keys(self):
        """Test that all binary integrity translation keys exist across supported languages."""
        keys = [
            'menu_verify_integrity', 'integrity_dialog_title', 'integrity_checking',
            'integrity_match', 'integrity_mismatch', 'integrity_remote_unavailable'
        ]
        for lang_code in SUPPORTED_LANGUAGES.keys():
            i18n = I18N(default_lang=lang_code)
            for k in keys:
                res = i18n.t(k)
                self.assertTrue(res, f"Missing key {k} for language {lang_code}")

    def test_main_window_menu_action(self):
        """Test that MainWindow has act_verify_integrity action configured in help menu."""
        window = MainWindow(app)
        self.assertTrue(hasattr(window, 'act_verify_integrity'))
        self.assertEqual(window.act_verify_integrity.text(), window.i18n.t('menu_verify_integrity'))
        self.assertTrue(hasattr(window, 'on_verify_integrity_clicked'))


if __name__ == '__main__':
    unittest.main()
