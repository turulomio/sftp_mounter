import os
import sys
import unittest
from PySide6.QtWidgets import QApplication

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sftp_mounter.i18n import I18N, SUPPORTED_LANGUAGES
from sftp_mounter.gui import MainWindow

app = QApplication.instance() or QApplication(sys.argv)


class TestOpenUserDirMenu(unittest.TestCase):
    def test_i18n_menu_open_user_dir(self):
        """Test that menu_open_user_dir translation exists in all languages."""
        for lang_code in SUPPORTED_LANGUAGES.keys():
            i18n = I18N(default_lang=lang_code)
            text = i18n.t('menu_open_user_dir')
            self.assertTrue(text, f"Missing menu_open_user_dir for language {lang_code}")

    def test_main_window_menu_action(self):
        """Test that MainWindow has act_open_user_dir action configured."""
        window = MainWindow(app)
        self.assertTrue(hasattr(window, 'act_open_user_dir'))
        self.assertEqual(window.act_open_user_dir.text(), window.i18n.t('menu_open_user_dir'))
        self.assertTrue(hasattr(window, 'on_open_user_dir'))


if __name__ == '__main__':
    unittest.main()
