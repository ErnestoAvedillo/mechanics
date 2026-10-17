"""
Metadata of an engineering standard: extraction with the LLM, validation and normalisation.

The extraction never blocks indexing: if it fails, the document is marked as failed and the
uploader fills the fields in by hand. The values are only a proposal until the uploader
confirms them, because they decide which edition replaces which.
"""
import json
import logging
import re
from datetime import date

from llama_index.core import Settings

from .models import Document

logger = logging.getLogger(__name__)

# Canonical short name -> other names the same issuer appears under. Extend freely.
CANONICAL_ISSUERS = {
    # German and European OEMs
    "VW": ["Volkswagen", "Volkswagen AG", "Volkswagen Group", "VW AG"],
    "BMW": ["BMW Group", "BMW AG"],
    "MB": ["Mercedes", "Mercedes-Benz", "Mercedes Benz", "Mercedes-Benz AG", "Daimler", "Daimler AG"],
    "Audi": ["Audi AG"],
    "Porsche": ["Dr. Ing. h.c. F. Porsche AG", "Porsche AG"],
    "Opel": ["Opel Automobile", "Vauxhall"],
    "Stellantis": ["Stellantis N.V."],
    "Renault": ["Renault Group", "Renault SA", "Groupe Renault"],
    "Volvo": ["Volvo Cars", "Volvo Car Corporation"],
    "JLR": ["Jaguar Land Rover", "Jaguar Land Rover Limited"],
    # American
    "Ford": ["Ford Motor Company", "Ford Motor Co"],
    "GM": ["General Motors", "General Motors Company"],
    "Tesla": ["Tesla Inc", "Tesla Motors"],
    # Japanese, Korean, Indian
    "Toyota": ["Toyota Motor Corporation", "Toyota Motor Corp"],
    "Honda": ["Honda Motor Co", "Honda Motor Company"],
    "Nissan": ["Nissan Motor Co", "Nissan Motor Company"],
    "Mazda": ["Mazda Motor Corporation"],
    "Subaru": ["Subaru Corporation"],
    "Suzuki": ["Suzuki Motor Corporation"],
    "Hyundai": ["Hyundai Motor", "Hyundai Motor Company", "Hyundai Motor Group"],
    "Kia": ["Kia Corporation", "Kia Motors"],
    "Tata": ["Tata Motors"],
    "Mahindra": ["Mahindra & Mahindra"],
    # Chinese
    "BYD": ["BYD Auto", "BYD Company", "BYD Company Limited", "BYD Auto Co", "比亚迪"],
    "Geely": ["Geely Auto", "Geely Automobile", "Zhejiang Geely", "Geely Holding", "吉利"],
    "Chery": ["Chery Automobile", "Chery Auto", "奇瑞"],
    "GWM": ["Great Wall", "Great Wall Motor", "Great Wall Motors", "长城"],
    "SAIC": ["SAIC Motor", "SAIC Motor Corporation", "上汽"],
    "MG": ["MG Motor", "Morris Garages"],
    "NIO": ["NIO Inc"],
    "XPeng": ["Xpeng", "XPENG", "Xiaopeng", "Xpeng Motors"],
    "Li Auto": ["Li Xiang", "Lixiang", "理想"],
    "Dongfeng": ["Dongfeng Motor", "Dongfeng Motor Corporation", "东风"],
    "FAW": ["FAW Group", "China FAW", "一汽"],
    "GAC": ["GAC Group", "Guangzhou Automobile Group", "广汽"],
    "Changan": ["Chongqing Changan", "Changan Automobile", "长安"],
    "BAIC": ["BAIC Group", "Beijing Automotive", "北汽"],
    "Leapmotor": ["Leap Motor", "零跑"],
    "Zeekr": ["ZEEKR", "极氪"],
    "Lynk & Co": ["Lynk&Co", "Lynk and Co"],
    "Haval": ["HAVAL"],
    "Xiaomi": ["Xiaomi Auto", "Xiaomi EV"],
}
ISSUER_ALIASES = {}
for _canonical, _others in CANONICAL_ISSUERS.items():
    for _name in [_canonical, *_others]:
        ISSUER_ALIASES[_name.upper()] = _canonical

# Language a issuer's standards are originally written in. Used only when a document says it is
# a translation without naming the language that prevails.
ISSUER_HOME_LANGUAGE = {
    **{issuer: "de" for issuer in ("VW", "BMW", "MB", "Audi", "Porsche", "Opel", "DIN", "VDA")},
    **{issuer: "zh" for issuer in (
        "BYD", "Geely", "Chery", "GWM", "SAIC", "MG", "NIO", "XPeng", "Li Auto", "Dongfeng", "FAW", "GAC",
        "Changan", "BAIC", "Leapmotor", "Zeekr", "Lynk & Co", "Haval", "Xiaomi", "GB", "QC")},
    **{issuer: "ja" for issuer in ("Toyota", "Honda", "Nissan", "Mazda", "Subaru", "Suzuki")},
    **{issuer: "ko" for issuer in ("Hyundai", "Kia")},
    "Renault": "fr", "Volvo": "sv", "UNE": "es",
}

EXTRACTION_PROMPT = """You read the first pages of an engineering standard or specification \
(the text may come from OCR). Extract the following as JSON. Use null when a value is not \
clearly stated; never guess.
{{
 "issuer": short common name of the OEM / company / standards body (for example "VW", "BMW", "BYD", "ISO", "GB"),
 "number": the standard's identifier without the edition, for example "TL 245", "GS 90010-1" or "GB/T 10125",
 "title": the title as printed,
 "edition_date": publication or edition date as YYYY-MM-DD, YYYY-MM or YYYY,
 "supersedes": list of identifiers with edition that this document replaces, for example ["GS 90011:2014-02"], or [],
 "language": ISO 639-1 code of the language this document is written in,
 "is_translation": true if the document says it is a translation or that another language version prevails, false if it presents itself as the original, null if unclear,
 "original_language": ISO 639-1 code of the language declared as binding or original (for example from a sentence like "Es gilt die deutsche Fassung" or "The German version prevails"), otherwise null,
 "copyright_notice": the exact copyright line if one is printed, otherwise null
}}
Return ONLY the JSON object.

--- TEXT ---
{text}"""


def normalize_issuer(raw):
    """Canonical short name: known aliases first, then short names in upper case (ISO, DIN, GB), else as given."""
    name = re.sub(r"\s+", " ", (raw or "").strip())
    if not name:
        return ""
    alias = ISSUER_ALIASES.get(name.upper())
    if alias:
        return alias
    return name.upper() if len(name) <= 5 else name


def normalize_number(raw):
    """
    Canonical identifier without the edition: 'gs90010-1:2023-05' -> 'GS 90010-1'.
    The edition is removed when it follows a colon (ISO, DIN, BMW) or is a trailing four-digit
    year after a dash (Chinese 'GB/T 10125-2021'), so part numbers such as '-1' are kept.
    """
    number = (raw or "").replace(" ", " ")
    number = re.sub(r"[‐-―−]", "-", number).strip()            # dashes of every kind
    number = re.sub(r":\s*\d{4}([-./]\d{1,2}){0,2}\s*$", "", number)           # ':2023-05'
    number = re.sub(r"(?<=\d)\s*-\s*(19|20)\d{2}\s*$", "", number)             # '-2021'
    number = re.sub(r"\s+", " ", number).strip().upper()
    number = re.sub(r"\s*/\s*", "/", number)                                   # 'GB / T' -> 'GB/T'
    return re.sub(r"^([A-Z]+(?:/[A-Z]+)?)(\d)", r"\1 \2", number)              # 'GS90010' -> 'GS 90010'


def parse_edition_date(raw):
    """Date of an edition given as YYYY, YYYY-MM or YYYY-MM-DD; month and day default to 1."""
    match = re.fullmatch(r"\s*(\d{4})(?:[-./](\d{1,2})(?:[-./](\d{1,2}))?)?\s*", str(raw or ""))
    if not match:
        return None
    year, month, day = int(match.group(1)), int(match.group(2) or 1), int(match.group(3) or 1)
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _text(value, limit):
    """A short clean string; the model sometimes returns the word 'null' or non-string values."""
    if value is None or isinstance(value, (list, dict)):
        return ""
    text = str(value).strip()
    return "" if text.lower() in ("null", "none", "n/a", "unknown") else text[:limit]


def parse_extraction(raw_answer):
    """
    Validates and normalises the model's JSON answer.
    Returns a dict or None when the answer holds no usable JSON object.
    """
    match = re.search(r"\{.*\}", raw_answer or "", re.S)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None

    supersedes = data.get("supersedes")
    supersedes = [_text(s, 100) for s in supersedes] if isinstance(supersedes, list) else []
    language = _valid_language(data.get("language"))
    issuer = normalize_issuer(_text(data.get("issuer"), 100))
    return {
        "issuer": issuer,
        "number": normalize_number(_text(data.get("number"), 100)),
        "title": _text(data.get("title"), 300),
        "edition_date": parse_edition_date(_text(data.get("edition_date"), 20)),
        "supersedes": [s for s in supersedes if s],
        "language": language,
        "original_language": _original_language(
            language, issuer, data.get("is_translation"), _valid_language(data.get("original_language"))),
        "copyright_notice": _text(data.get("copyright_notice"), 300),
    }


def _valid_language(value):
    code = _text(value, 5).lower()
    return code if re.fullmatch(r"[a-z]{2,3}", code) else ""


def _original_language(language, issuer, is_translation, stated):
    """
    The language that prevails for the standard. Order: what the document states, the issuer's home
    language if the document says it is a translation, and otherwise the document's own language.
    """
    if stated:
        return stated
    if is_translation is True or str(is_translation).lower() == "true":
        return ISSUER_HOME_LANGUAGE.get(issuer, "")
    return language


def extract_metadata(text):
    """Asks the LLM for the metadata of a standard. Returns the validated dict, or None on any failure."""
    try:
        # Temperature 0: the same text should give the same metadata on every run
        answer = str(Settings.llm.complete(EXTRACTION_PROMPT.format(text=text[:6000]), temperature=0))
    except Exception:
        logger.exception("Metadata extraction failed")
        return None
    return parse_extraction(answer)


def apply_metadata(document, metadata):
    """
    Stores an extraction on the document as a proposal pending the uploader's review.
    Nothing usable (no issuer and no number) counts as a failed extraction.
    """
    if not metadata or not (metadata["issuer"] and metadata["number"]):
        document.metadata_status = Document.METADATA_FAILED
        document.save(update_fields=["metadata_status"])
        return False
    document.spec_issuer = metadata["issuer"]
    document.spec_number = metadata["number"]
    document.title = metadata["title"]
    document.edition_date = metadata["edition_date"]
    document.language = metadata["language"]
    document.original_language = metadata["original_language"]
    document.supersedes = metadata["supersedes"]
    document.copyright_notice = metadata["copyright_notice"]
    document.metadata_status = Document.METADATA_PENDING
    document.save(update_fields=[
        "spec_issuer", "spec_number", "title", "edition_date", "language", "original_language",
        "supersedes", "copyright_notice", "metadata_status",
    ])
    return True
