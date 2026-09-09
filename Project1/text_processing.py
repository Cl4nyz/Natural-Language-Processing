"""Offset-preserving sentence segmentation and tokenization.

All offsets emitted here are half-open intervals [start_char, end_char) over the
original case_text. The cleaned text is intentionally not used for offsets.
"""

import re

from .models import Sentence, Token


_ABBREVIATIONS = {"dr", "fig", "figs", "mr", "mrs", "ms", "prof", "st", "vs"}

_TOKEN_RE = re.compile(
    r"""
    CA\s+19-9                                               # clinical multiword token
    | \d{1,3}(?:,\d{3})+(?:\.\d+)?(?:[A-Za-zµμ]+(?:/[A-Za-z0-9µμ]+)?)?
    | \d+(?:\.\d+)?(?:[A-Za-zµμ]+(?:/[A-Za-z0-9µμ]+)?)   # 6cm, 12.8%, ng handled below
    | \d+(?:\.\d+)?%                                      # percentage
    | [A-Za-z]+(?:-[A-Za-z0-9]+)+                          # EUS-FNA, C-reactive, 19-year
    | [A-Za-zµμ]+(?:/[A-Za-z0-9µμ]+)+                      # ng/ml, U/L
    | \d+(?:[.,]\d+)*(?:-\d+(?:[.,]\d+)*)?                # numbers/ranges
    | [A-Za-zµμ]+(?:'[A-Za-z]+)?                           # words
    | [^\w\s]                                              # punctuation/symbol fallback
    """,
    re.IGNORECASE | re.VERBOSE,
)


def minimal_clean(text: str) -> str:
    """Create a conservative processed copy; never use it to replace case_text."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    return text.strip()


def _previous_word(text: str, period_index: int) -> str:
    match = re.search(r"([A-Za-z]+)$", text[:period_index])
    return match.group(1).casefold() if match else ""


def segment_sentences(case_id: str, original_text: str) -> list[Sentence]:
    """Segment by terminal punctuation while protecting decimals/abbreviations."""
    boundaries: list[int] = []
    length = len(original_text)
    index = 0
    while index < length:
        char = original_text[index]
        if char not in ".!?":
            index += 1
            continue
        if char == "." and index > 0 and index + 1 < length:
            if original_text[index - 1].isdigit() and original_text[index + 1].isdigit():
                index += 1
                continue
        if char == "." and _previous_word(original_text, index) in _ABBREVIATIONS:
            index += 1
            continue

        candidate_end = index + 1
        while candidate_end < length and original_text[candidate_end] in "\"')]}":
            candidate_end += 1
        if candidate_end == length or original_text[candidate_end].isspace():
            boundaries.append(candidate_end)
        index = candidate_end

    if not boundaries or boundaries[-1] < length:
        boundaries.append(length)

    sentences: list[Sentence] = []
    raw_start = 0
    for raw_end in boundaries:
        start = raw_start
        while start < raw_end and original_text[start].isspace():
            start += 1
        end = raw_end
        while end > start and original_text[end - 1].isspace():
            end -= 1
        if start < end:
            sentences.append(
                Sentence(case_id, len(sentences) + 1, original_text[start:end], start, end)
            )
        raw_start = raw_end
    return sentences


def tokenize_sentence(sentence: Sentence) -> list[Token]:
    tokens: list[Token] = []
    for match in _TOKEN_RE.finditer(sentence.sentence_text):
        tokens.append(
            Token(
                case_id=sentence.case_id,
                sentence_id=sentence.sentence_id,
                token_id=len(tokens) + 1,
                token=match.group(0),
                start_char=sentence.start_char + match.start(),
                end_char=sentence.start_char + match.end(),
            )
        )
    return tokens


def normalize_form(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip()).casefold()
