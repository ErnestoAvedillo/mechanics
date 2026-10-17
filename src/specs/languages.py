"""
Languages a standard can be written in, for the selectors of the review form.

The user picks a full name (shown in the interface language); the ISO 639-1 code is what is stored.
Names are Spanish msgids translated through the usual .po files, so the list is shown in Spanish or English.
"""
from django.utils.translation import gettext_lazy as _

# code -> full name. Add a language here and translate its name in both .po files.
LANGUAGE_NAMES = {
    "de": _("Alemán"), "en": _("Inglés"), "es": _("Español"), "fr": _("Francés"), "it": _("Italiano"),
    "pt": _("Portugués"), "zh": _("Chino"), "ja": _("Japonés"), "ko": _("Coreano"),
    "nl": _("Neerlandés"), "sv": _("Sueco"), "da": _("Danés"), "no": _("Noruego"), "fi": _("Finés"),
    "cs": _("Checo"), "sk": _("Eslovaco"), "pl": _("Polaco"), "hu": _("Húngaro"), "ro": _("Rumano"),
    "bg": _("Búlgaro"), "hr": _("Croata"), "sl": _("Esloveno"), "sr": _("Serbio"), "el": _("Griego"),
    "tr": _("Turco"), "ru": _("Ruso"), "uk": _("Ucraniano"), "ar": _("Árabe"), "he": _("Hebreo"),
    "hi": _("Hindi"), "th": _("Tailandés"), "vi": _("Vietnamita"), "id": _("Indonesio"),
    "ca": _("Catalán"), "eu": _("Euskera"), "gl": _("Gallego"),
}

# Shown first because they cover most automotive standards
COMMON = ["de", "en", "es", "fr", "it", "pt", "zh", "ja", "ko"]


def language_choices(extra=()):
    """
    (code, full name) pairs: the common languages first, then the rest alphabetically by name.
    `extra` adds codes outside the list (for example one the LLM detected) so an existing value
    is never lost; they are shown by their code.
    """
    others = sorted((c for c in LANGUAGE_NAMES if c not in COMMON), key=lambda c: str(LANGUAGE_NAMES[c]).lower())
    choices = [(code, str(LANGUAGE_NAMES[code])) for code in COMMON + others]
    known = set(LANGUAGE_NAMES)
    choices += [(code, code) for code in sorted(set(extra) - known) if code]
    return choices


def language_name(code):
    """Full name of a language code, or the code itself when it is not in the list."""
    return str(LANGUAGE_NAMES.get(code, code))
