"""Funciones sencillas de texto y mediciones para la primera entrega."""

import re
from decimal import Decimal


ABBREVIATIONS = {"dr", "fig", "figs", "mr", "mrs", "ms", "prof", "st", "vs"}

TOKEN_PATTERN = re.compile(
    r"CA\s+19-9"
    r"|\d{1,3}(?:,\d{3})+(?:\.\d+)?(?:[A-Za-zµμ]+(?:/[A-Za-z0-9µμ]+)?)?"
    r"|\d+(?:\.\d+)?(?:[A-Za-zµμ]+(?:/[A-Za-z0-9µμ]+)?)"
    r"|\d+(?:\.\d+)?%"
    r"|[A-Za-z]+(?:-[A-Za-z0-9]+)+"
    r"|[A-Za-zµμ]+(?:/[A-Za-z0-9µμ]+)+"
    r"|\d+(?:[.,]\d+)*(?:-\d+(?:[.,]\d+)*)?"
    r"|[A-Za-zµμ]+(?:'[A-Za-z]+)?"
    r"|[^\w\s]",
    re.IGNORECASE,
)

NUMBER = r"\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?"
LENGTH_UNIT = r"cm(?:2|²)?|mm(?:2|²)?|m(?:2|²)?"
UNIT = (
    r"mg\s+per\s+day|beats/min|mcg/dL|ng/mL|mg/L|g/dL|IU/mL|U/L|"
    r"/mm3|mmHg|mm/h|cm2|cm²|mm2|mm²|cm|mm|mg|months?|weeks?|days?|h|C"
)

MEASUREMENT_PATTERNS = [
    (
        "blood_pressure",
        "measurement_blood_pressure_v1",
        re.compile(
            rf"(?P<systolic>{NUMBER})\s*/\s*(?P<diastolic>{NUMBER})\s*"
            rf"(?P<unit>mmHg)(?![A-Za-z0-9])",
            re.IGNORECASE,
        ),
    ),
    (
        "dimension",
        "measurement_dimension_v1",
        re.compile(
            rf"(?P<v1>{NUMBER})\s*(?P<u1>{LENGTH_UNIT})?\s*[x×]\s*"
            rf"(?P<v2>{NUMBER})\s*(?P<u2>{LENGTH_UNIT})?"
            rf"(?:\s*[x×]\s*(?P<v3>{NUMBER})\s*(?P<u3>{LENGTH_UNIT})?)?"
            rf"(?![A-Za-z0-9])",
            re.IGNORECASE,
        ),
    ),
    (
        "range",
        "measurement_range_v1",
        re.compile(
            rf"(?P<low>{NUMBER})\s*[-–]\s*(?P<high>{NUMBER})\s*"
            rf"(?P<unit>{UNIT})(?![A-Za-z0-9])",
            re.IGNORECASE,
        ),
    ),
    (
        "percentage",
        "measurement_percentage_v1",
        re.compile(
            rf"(?:(?P<comparator>[<>≤≥])\s*)?(?P<value>{NUMBER})\s*"
            rf"(?P<unit>%)(?![A-Za-z0-9])"
        ),
    ),
    (
        "simple_measurement",
        "measurement_value_unit_v1",
        re.compile(
            rf"(?:(?P<comparator>[<>≤≥])\s*)?(?P<value>{NUMBER})"
            rf"(?P<separator>\s*-?\s*)(?P<unit>{UNIT})(?![A-Za-z0-9])",
            re.IGNORECASE,
        ),
    ),
]

UNIT_NORMALIZATION = {
    "iu/ml": "IU/mL",
    "u/l": "U/L",
    "ng/ml": "ng/mL",
    "mcg/dl": "mcg/dL",
    "mg/l": "mg/L",
    "g/dl": "g/dL",
    "mmhg": "mmHg",
    "cm²": "cm2",
    "mm²": "mm2",
    "mg per day": "mg/day",
}


def clean_text(text):
    """Crea una copia limpia sin modificar el texto original."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    return text.strip()


def normalize_form(text):
    return re.sub(r"\s+", " ", text.strip()).casefold()


def previous_word(text, position):
    match = re.search(r"([A-Za-z]+)$", text[:position])
    return match.group(1).casefold() if match else ""


def split_sentences(case_id, original_text):
    """Divide el texto y conserva offsets sobre original_text."""
    boundaries = []
    position = 0

    while position < len(original_text):
        char = original_text[position]
        if char not in ".!?":
            position += 1
            continue

        is_decimal = (
            char == "."
            and position > 0
            and position + 1 < len(original_text)
            and original_text[position - 1].isdigit()
            and original_text[position + 1].isdigit()
        )
        if is_decimal or (char == "." and previous_word(original_text, position) in ABBREVIATIONS):
            position += 1
            continue

        end = position + 1
        while end < len(original_text) and original_text[end] in "\"')]}":
            end += 1
        if end == len(original_text) or original_text[end].isspace():
            boundaries.append(end)
        position = end

    if not boundaries or boundaries[-1] < len(original_text):
        boundaries.append(len(original_text))

    sentences = []
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
                {
                    "case_id": case_id,
                    "sentence_id": len(sentences) + 1,
                    "sentence_text": original_text[start:end],
                    "start_char": start,
                    "end_char": end,
                }
            )
        raw_start = raw_end
    return sentences


def tokenize(sentence):
    """Tokeniza una oración y conserva offsets sobre original_text."""
    tokens = []
    for match in TOKEN_PATTERN.finditer(sentence["sentence_text"]):
        token = match.group(0)
        tokens.append(
            {
                "case_id": sentence["case_id"],
                "sentence_id": sentence["sentence_id"],
                "token_id": len(tokens) + 1,
                "token": token,
                "start_char": sentence["start_char"] + match.start(),
                "end_char": sentence["start_char"] + match.end(),
                "original_form": token,
                "normalized_form": normalize_form(token),
            }
        )
    return tokens


def parse_number(raw_value):
    number = Decimal(raw_value.replace(",", ""))
    return int(number) if number == number.to_integral_value() else float(number)


def normalize_unit(unit):
    unit = re.sub(r"\s+", " ", unit.strip())
    return UNIT_NORMALIZATION.get(unit.casefold(), unit)


def measurement_attributes(kind, match):
    values = match.groupdict()

    if kind == "blood_pressure":
        return {
            "measurement_type": kind,
            "systolic": parse_number(values["systolic"]),
            "diastolic": parse_number(values["diastolic"]),
            "unit": normalize_unit(values["unit"]),
        }

    if kind == "dimension":
        found_units = [values.get("u1"), values.get("u2"), values.get("u3")]
        shared_unit = normalize_unit(next(unit for unit in reversed(found_units) if unit))
        result_values = [parse_number(values["v1"]), parse_number(values["v2"])]
        result_units = [
            normalize_unit(values["u1"]) if values.get("u1") else shared_unit,
            normalize_unit(values["u2"]) if values.get("u2") else shared_unit,
        ]
        if values.get("v3"):
            result_values.append(parse_number(values["v3"]))
            result_units.append(
                normalize_unit(values["u3"]) if values.get("u3") else shared_unit
            )
        return {"measurement_type": kind, "values": result_values, "units": result_units}

    if kind == "range":
        return {
            "measurement_type": kind,
            "low": parse_number(values["low"]),
            "high": parse_number(values["high"]),
            "unit": normalize_unit(values["unit"]),
        }

    attributes = {
        "measurement_type": kind,
        "value": parse_number(values["value"]),
        "unit": normalize_unit(values["unit"]),
    }
    if values.get("comparator"):
        attributes["comparator"] = values["comparator"]
    return attributes


def normalized_measurement_label(attributes):
    kind = attributes["measurement_type"]
    if kind == "blood_pressure":
        return f"{attributes['systolic']}/{attributes['diastolic']} {attributes['unit']}"
    if kind == "dimension":
        pieces = zip(attributes["values"], attributes["units"])
        return " x ".join(f"{value} {unit}" for value, unit in pieces)
    if kind == "range":
        return f"{attributes['low']}-{attributes['high']} {attributes['unit']}"
    comparator = attributes.get("comparator", "")
    return f"{comparator}{attributes['value']} {attributes['unit']}"


def extract_measurements(sentences):
    """Extrae mediciones mediante reglas ordenadas y evita spans solapados."""
    entities = []
    measurement_number = 0

    for sentence in sentences:
        occupied = []
        candidates = []

        for kind, rule_id, pattern in MEASUREMENT_PATTERNS:
            for match in pattern.finditer(sentence["sentence_text"]):
                groups = match.groupdict()

                if kind == "dimension" and not any(groups.get(key) for key in ("u1", "u2", "u3")):
                    continue

                if kind == "simple_measurement":
                    unit = groups["unit"].casefold()
                    separator = groups.get("separator", "")
                    if unit == "c" and not separator:
                        continue
                    if "-" in separator and unit.rstrip("s") in {"day", "week", "month"}:
                        continue

                overlaps = any(
                    match.start() < end and start < match.end() for start, end in occupied
                )
                if overlaps:
                    continue

                occupied.append((match.start(), match.end()))
                candidates.append((match.start(), match.end(), kind, rule_id, match))

        for start, end, kind, rule_id, match in sorted(candidates):
            measurement_number += 1
            attributes = measurement_attributes(kind, match)
            original_span = sentence["sentence_text"][start:end]
            entities.append(
                {
                    "entity_id": f"{sentence['case_id']}_M{measurement_number:04d}",
                    "case_id": sentence["case_id"],
                    "sentence_id": sentence["sentence_id"],
                    "type": "Measurement",
                    "original_span": original_span,
                    "normalized_label": normalized_measurement_label(attributes),
                    "start_char": sentence["start_char"] + start,
                    "end_char": sentence["start_char"] + end,
                    "attributes": attributes,
                    "rule_id": rule_id,
                }
            )
    return entities
