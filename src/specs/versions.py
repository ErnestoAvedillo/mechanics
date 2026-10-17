"""
Which documents of a user's library are searched, and why each of the others is not.

Editions and languages are resolved per library, not globally: a document is only "obsolete" for
the users who also have a newer edition of the same standard. Nothing is deleted or re-indexed;
the result only decides which document ids the chat and the MCP tools may search.

Rules, applied per standard (issuer + number) over the user's documents with confirmed metadata:
  1. The most recent edition is used; older editions are superseded.
  2. Within that edition, the document written in the language that prevails (the original) is used.
     Translations are hidden while the original is available; if only translations exist, one is
     used and flagged, because the original may prevail.
  3. If the same variant exists several times (same edition and language, different file), the
     most recently uploaded one is used and the others are flagged as possible duplicates.
Documents whose metadata is not confirmed, or that have no edition date, are always searched:
they cannot be compared reliably, and hiding them would silently remove content.
"""
from collections import defaultdict, namedtuple

from .models import Document

CURRENT = "current"
UNREVIEWED = "unreviewed"
TRANSLATION_ONLY = "translation_only"
SUPERSEDED = "superseded"
TRANSLATION = "translation"
DUPLICATE = "duplicate"

SEARCHED = {CURRENT, UNREVIEWED, TRANSLATION_ONLY}

# `by` is the id of the document that is used instead (None when the document itself is used)
LibraryState = namedtuple("LibraryState", "state by")


def library_state(user_id):
    """Maps the id of every document the user has access to onto its LibraryState."""
    documents = Document.objects.filter(accesses__user_id=user_id).distinct()
    states = {}
    groups = defaultdict(list)
    for document in documents:
        if document.metadata_status != Document.METADATA_CONFIRMED or not (document.spec_issuer and document.spec_number):
            states[document.id] = LibraryState(UNREVIEWED, None)
        else:
            groups[(document.spec_issuer.casefold(), document.spec_number.casefold())].append(document)
    for group in groups.values():
        states.update(_resolve_standard(group))
    return states


def searched_document_ids(user_id):
    """Ids of the documents the user's searches may use."""
    return sorted(pk for pk, state in library_state(user_id).items() if state.state in SEARCHED)


def _resolve_standard(group):
    """Applies the rules to the documents of one standard."""
    states = {d.id: LibraryState(CURRENT, None) for d in group if not d.edition_date}
    dated = [d for d in group if d.edition_date]
    if not dated:
        return states

    newest = max(d.edition_date for d in dated)
    latest_edition = [d for d in dated if d.edition_date == newest]
    originals = [d for d in latest_edition if not d.is_translation]
    pool = originals or latest_edition

    # One language only: that of the earliest upload, so the choice never flips between runs
    language = min(pool, key=lambda d: (d.upload_date, d.id)).language
    variants = [d for d in pool if d.language == language]
    chosen = max(variants, key=lambda d: (d.upload_date, d.id))
    states[chosen.id] = LibraryState(CURRENT if originals else TRANSLATION_ONLY, None)

    for document in dated:
        if document.id == chosen.id:
            continue
        if document.edition_date < newest:
            state = SUPERSEDED
        elif document in variants:
            state = DUPLICATE
        else:
            state = TRANSLATION
        states[document.id] = LibraryState(state, chosen.id)
    return states
