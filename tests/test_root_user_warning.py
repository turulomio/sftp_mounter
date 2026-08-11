import os
import sys
import unittest
from PySide6.QtWidgets import QApplication

# Ensure sftp_mounter package is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sftp_mounter.i18n import I18N, SUPPORTED_LANGUAGES
from sftp_mounter.config_manager import ConfigManager
from sftp_mounter.gui import ProfileManagerDialog

# Initialize QApplication for headless GUI tests
app = QApplication.instance() or QApplication(sys.argv)


class TestRootUserWarning(unittest.TestCase):
    def test_i18n_translations(self):
        """Test that root_user_warning key exists for all supported languages."""
        for lang_code in SUPPORTED_LANGUAGES.keys():
            i18n = I18N(default_lang=lang_code)
            warning_text = i18n.t('root_user_warning')
            self.assertTrue(warning_text, f"Translation missing for language {lang_code}")
            self.assertIn("root", warning_text.lower(), f"Warning text for {lang_code} should mention 'root'")

    def test_profile_manager_root_warning(self):
        """Test that ProfileManagerDialog toggles root warning card visibility based on username."""
        i18n = I18N(default_lang='es')
        config_manager = ConfigManager()
        dialog = ProfileManagerDialog(config_manager=config_manager, i18n=i18n)

        # Initially warning card should be hidden if txt_user is empty
        dialog.txt_user.setText("")
        self.assertTrue(dialog.root_warning_card.isHidden())

        # Setting username to 'root' should show the warning card
        dialog.txt_user.setText("root")
        self.assertFalse(dialog.root_warning_card.isHidden())

        # Testing uppercase 'ROOT'
        dialog.txt_user.setText("ROOT")
        self.assertFalse(dialog.root_warning_card.isHidden())

        # Testing with whitespace ' root '
        dialog.txt_user.setText(" root ")
        self.assertFalse(dialog.root_warning_card.isHidden())

        # Changing username to non-root should hide the warning card
        dialog.txt_user.setText("admin")
        self.assertTrue(dialog.root_warning_card.isHidden())


if __name__ == '__main__':
    unittest.main()
