import unittest
from sftp_mounter.i18n import I18N, SUPPORTED_LANGUAGES, TRANSLATIONS

class TestI18N(unittest.TestCase):
    def setUp(self):
        self.i18n = I18N('en')

    def test_supported_languages(self):
        self.assertIn('en', SUPPORTED_LANGUAGES)
        self.assertIn('es', SUPPORTED_LANGUAGES)

    def test_change_language(self):
        self.i18n.set_language('es')
        self.assertEqual(self.i18n.get_language(), 'es')
        
        # Setting invalid language shouldn't change current language
        self.i18n.set_language('invalid_lang')
        self.assertEqual(self.i18n.get_language(), 'es')

    def test_translation_lookup(self):
        self.i18n.set_language('en')
        self.assertEqual(self.i18n.t('title'), 'SFTP Mounter')
        
        self.i18n.set_language('es')
        self.assertEqual(self.i18n.t('menu_options'), 'Opciones')

    def test_translation_fallback(self):
        self.i18n.set_language('en')
        # Non-existent key should return key itself
        self.assertEqual(self.i18n.t('non_existent_key_123'), 'non_existent_key_123')

    def test_translation_formatting(self):
        self.i18n.set_language('en')
        # Assuming a key with formatting exists or testing generic string formatting fallback
        res = self.i18n.t('title', dummy='test')
        self.assertEqual(res, 'SFTP Mounter')

if __name__ == '__main__':
    unittest.main()
