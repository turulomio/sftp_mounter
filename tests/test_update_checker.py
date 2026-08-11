import os
import sys
import unittest
import time
from PySide6.QtWidgets import QApplication

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sftp_mounter.i18n import I18N, SUPPORTED_LANGUAGES
from sftp_mounter.gui import MainWindow, parse_version, UpdateCheckWorker

app = QApplication.instance() or QApplication(sys.argv)


class TestUpdateChecker(unittest.TestCase):
    def test_version_parsing(self):
        """Test parse_version tuple comparisons."""
        self.assertEqual(parse_version("1.2.0"), (1, 2, 0))
        self.assertEqual(parse_version("v1.3.5"), (1, 3, 5))
        self.assertTrue(parse_version("1.3.0") > parse_version("1.2.0"))
        self.assertFalse(parse_version("1.2.0") > parse_version("1.2.0"))
        self.assertFalse(parse_version("1.1.9") > parse_version("1.2.0"))

    def test_i18n_update_keys(self):
        """Test that all update check translation keys exist in all languages."""
        keys = [
            'menu_check_updates', 'update_available', 'update_no_updates',
            'update_check_error', 'update_checking', 'btn_download_update'
        ]
        for lang_code in SUPPORTED_LANGUAGES.keys():
            i18n = I18N(default_lang=lang_code)
            for k in keys:
                res = i18n.t(k, latest='1.3.0', current='1.2.0')
                self.assertTrue(res, f"Missing key {k} for language {lang_code}")

    def test_update_card_ui_flow(self):
        """Test update card manual and automatic completion handlers."""
        window = MainWindow(app)
        self.assertTrue(hasattr(window, 'update_card'))
        self.assertTrue(hasattr(window, 'act_check_updates'))
        self.assertTrue(window.update_card.isHidden())

        # Simulate update check finish when a new version IS found
        window.on_update_check_finished(
            has_update=True,
            latest_v="1.3.0",
            html_url="https://github.com/turulomio/sftp_mounter/releases/tag/v1.3.0",
            error_msg="",
            is_manual=False
        )
        self.assertFalse(window.update_card.isHidden())
        self.assertIn("1.3.0", window.lbl_update_status.text())

        # Simulate manual update check when NO new version is found
        window.on_update_check_finished(
            has_update=False,
            latest_v="1.2.0",
            html_url="",
            error_msg="",
            is_manual=True
        )
        self.assertFalse(window.update_card.isHidden())

        # Simulate automatic update check when NO new version is found (should stay hidden)
        window.update_card.setVisible(False)
        window.on_update_check_finished(
            has_update=False,
            latest_v="1.2.0",
            html_url="",
            error_msg="",
            is_manual=False
        )
        self.assertTrue(window.update_card.isHidden())


if __name__ == '__main__':
    unittest.main()
