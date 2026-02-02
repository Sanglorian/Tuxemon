# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from tuxemon.locale.translator import TranslatorPo


class TestTranslatorPo(unittest.TestCase):

    @patch("tuxemon.locale.translator.translation")
    def test_translation_success(self, mock_translation):
        mock_trans = MagicMock()
        mock_trans.gettext.return_value = "Bonjour"
        mock_translation.return_value = mock_trans

        po = TranslatorPo(
            locale_name="fr",
            domain="base",
            localedir=Path("."),
            fallback_locale="en",
        )
        result = po.translate("Hello")
        self.assertEqual(result, "Bonjour")

    @patch(
        "tuxemon.locale.translator.translation",
        side_effect=FileNotFoundError,
    )
    def test_fallback_to_null_translations(self, mock_translation):
        po = TranslatorPo(
            locale_name="xx",
            domain="base",
            localedir=Path("."),
            fallback_locale="en",
        )
        result = po.translate("Hello")
        self.assertEqual(result, "Hello")  # Should be untranslated

    def test_format_translation(self):
        po = TranslatorPo(
            locale_name="en",
            domain="base",
            localedir=Path("."),
            fallback_locale="en",
        )
        po.translate = MagicMock(return_value="Hello, {name}")
        result = po.format("Hello, {name}", {"name": "Alice"})
        self.assertEqual(result, "Hello, Alice")

    def test_maybe_translate_none(self):
        po = TranslatorPo("en", "base", Path("."), "en")
        result = po.maybe_translate(None)
        self.assertEqual(result, "")

    @patch("tuxemon.locale.translator.translation")
    def test_plural_translation_success(self, mock_translation):
        mock_trans = MagicMock()
        mock_trans.ngettext.side_effect = lambda singular, plural, n: (
            f"{n} apple" if n == 1 else f"{n} apples"
        )

        mock_fallback = MagicMock()
        mock_fallback.ngettext.side_effect = lambda s, p, n: f"{n} fallback"

        mock_translation.side_effect = [mock_trans, mock_fallback]

        po = TranslatorPo(
            locale_name="en",
            domain="base",
            localedir=Path("."),
            fallback_locale="en",
        )

        singular = "apple"
        plural = "apples"

        result_one = po.translate_plural(singular, plural, 1)
        result_many = po.translate_plural(singular, plural, 3)

        self.assertEqual(result_one, "1 apple")
        self.assertEqual(result_many, "3 apples")

    @patch("tuxemon.locale.translator.translation")
    def test_has_translation(self, mock_translation):
        mock_trans = MagicMock()
        mock_trans.gettext.side_effect = lambda msg: (
            "Bonjour" if msg == "Hello" else msg
        )
        mock_fallback = MagicMock()
        mock_fallback.gettext.side_effect = lambda msg: msg

        mock_translation.side_effect = [mock_trans, mock_fallback]

        po = TranslatorPo("fr", "base", Path("."), "en")
        self.assertTrue(po.has_translation("Hello"))
        self.assertFalse(po.has_translation("Goodbye"))

    @patch("tuxemon.locale.translator.translation")
    def test_has_plural_translation(self, mock_translation):
        mock_trans = MagicMock()
        mock_trans.ngettext.side_effect = lambda s, p, n: s if n == 1 else p
        mock_fallback = MagicMock()
        mock_fallback.ngettext.side_effect = lambda s, p, n: s if n == 1 else p

        mock_translation.side_effect = [mock_trans, mock_fallback]

        po = TranslatorPo("en", "base", Path("."), "en")
        self.assertFalse(po.has_plural_translation("apple", "apples", 0))

    @patch(
        "tuxemon.locale.translator.translation",
        side_effect=FileNotFoundError,
    )
    def test_missing_all_translations(self, mock_translation):
        po = TranslatorPo("xx", "base", Path("."), "yy")
        result = po.translate("Hello")
        self.assertEqual(result, "Hello")

    def test_get_current_language(self):
        po = TranslatorPo("it", "base", Path("."), "en")
        self.assertEqual(po.get_current_language(), "it")

    def test_maybe_translate_string(self):
        po = TranslatorPo("en", "base", Path("."), "en")
        po.translate = MagicMock(return_value="Hi")
        self.assertEqual(po.maybe_translate("Hello"), "Hi")

    def test_maybe_translate_none(self):
        po = TranslatorPo("en", "base", Path("."), "en")
        self.assertEqual(po.maybe_translate(None), "")
