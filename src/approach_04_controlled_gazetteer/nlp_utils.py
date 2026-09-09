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
    r"/mm3|mmHg|mm/h|cm2|cm²|mm2|mm²|cm|mm|mg|C"
)

MEASUREMENT_PATTERNS = [
    (
        "scientific_notation",
        "measurement_scientific_notation_degraded_v1",
        re.compile(
            rf"(?P<coefficient>{NUMBER})\s*[x×]\s*10(?:\^)?"
            rf"(?P<exponent>\d+)\s*/\s*(?P<denominator>[A-Za-z]+)",
            re.IGNORECASE,
        ),
    ),
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

NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
}

ORDINAL_WORDS = {
    "first": 1,
    "second": 2,
    "third": 3,
    "fourth": 4,
    "fifth": 5,
    "sixth": 6,
    "seventh": 7,
    "eighth": 8,
    "ninth": 9,
    "tenth": 10,
}

NUMBER_WORD_PATTERN = "|".join(NUMBER_WORDS)
ORDINAL_WORD_PATTERN = "|".join(ORDINAL_WORDS)
TIME_UNIT = r"h|hours?|days?|weeks?|months?|years?"

TEMPORAL_PATTERNS = [
    (
        "relative_day",
        "temporal_postoperative_day_v1",
        re.compile(r"\b(?P<marker>postoperative\s+day|POD)\s+(?P<value>\d+)\b", re.IGNORECASE),
    ),
    (
        "duration",
        "temporal_hyphenated_duration_v1",
        re.compile(
            rf"\b(?P<value>\d+)-(?P<unit>{TIME_UNIT})\b(?!\s*-?\s*old\b)",
            re.IGNORECASE,
        ),
    ),
    (
        "relative_day",
        "temporal_numeric_ordinal_day_v1",
        re.compile(r"\b(?P<value>\d+)(?:st|nd|rd|th)\s+day\b", re.IGNORECASE),
    ),
    (
        "relative_day",
        "temporal_word_ordinal_day_v1",
        re.compile(rf"\b(?P<word>{ORDINAL_WORD_PATTERN})\s+day\b", re.IGNORECASE),
    ),
    (
        "relative_day",
        "temporal_day_number_v1",
        re.compile(r"\bday\s+(?P<value>\d+)\b", re.IGNORECASE),
    ),
    (
        "duration",
        "temporal_numeric_duration_v1",
        re.compile(rf"\b(?P<value>{NUMBER})\s*(?P<unit>{TIME_UNIT})\b", re.IGNORECASE),
    ),
    (
        "duration",
        "temporal_word_duration_v1",
        re.compile(rf"\b(?P<word>{NUMBER_WORD_PATTERN})\s+(?P<unit>{TIME_UNIT})\b", re.IGNORECASE),
    ),
]

REFERENCE_SIGNAL = r"(?:normal|reference)\s+range(?:\s*\(\s*NR\s*\))?|NR"
REFERENCE_UNIT = rf"{UNIT}|%"
REFERENCE_PATTERNS = [
    (
        "reference_range_signal_v1",
        re.compile(
            rf"(?P<signal>{REFERENCE_SIGNAL})\s*"
            rf"(?P<reference>(?P<low>{NUMBER})\s*[-–]\s*(?P<high>{NUMBER})\s*"
            rf"(?P<unit>{REFERENCE_UNIT})(?![A-Za-z0-9]))",
            re.IGNORECASE,
        ),
    ),
    (
        "reference_threshold_signal_v1",
        re.compile(
            rf"(?P<signal>{REFERENCE_SIGNAL})\s*"
            rf"(?P<reference>(?P<comparator>[<>≤≥])\s*(?P<value>{NUMBER})\s*"
            rf"(?P<unit>{REFERENCE_UNIT})(?![A-Za-z0-9]))",
            re.IGNORECASE,
        ),
    ),
]


# cria uma copia limpa sem alterar o texto original
def clean_text(text):
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    return text.strip()


# normaliza o texto para comparacao
def normalize_form(text):
    return re.sub(r"\s+", " ", text.strip()).casefold()


# retorna a palavra anterior a uma posicao
def previous_word(text, position):
    match = re.search(r"([A-Za-z]+)$", text[:position])
    return match.group(1).casefold() if match else ""


# divide o texto em sentencas e preserva os offsets
def split_sentences(case_id, original_text):
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


# divide uma sentenca em tokens e preserva os offsets
def tokenize(sentence):
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


# converte o numero textual para int ou float
def parse_number(raw_value):
    number = Decimal(raw_value.replace(",", ""))
    return int(number) if number == number.to_integral_value() else float(number)


# normaliza variantes de unidades
def normalize_unit(unit):
    unit = re.sub(r"\s+", " ", unit.strip())
    return UNIT_NORMALIZATION.get(unit.casefold(), unit)


# organiza os atributos conforme o tipo de medicao
def measurement_attributes(kind, match):
    values = match.groupdict()

    if kind == "scientific_notation":
        coefficient = parse_number(values["coefficient"])
        exponent = int(values["exponent"])
        return {
            "measurement_type": kind,
            "coefficient": coefficient,
            "base": 10,
            "exponent": exponent,
            "value": coefficient * (10 ** exponent),
            "unit": f"1/{values['denominator']}",
            "normalization_rule": "normalize_degraded_scientific_notation_v1",
        }

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


# monta o rotulo normalizado de uma medicao
def normalized_measurement_label(attributes):
    kind = attributes["measurement_type"]
    if kind == "scientific_notation":
        denominator = attributes["unit"].split("/", 1)[1]
        return (
            f"{attributes['coefficient']} × 10^{attributes['exponent']}/{denominator}"
        )
    if kind == "blood_pressure":
        return f"{attributes['systolic']}/{attributes['diastolic']} {attributes['unit']}"
    if kind == "dimension":
        pieces = zip(attributes["values"], attributes["units"])
        return " x ".join(f"{value} {unit}" for value, unit in pieces)
    if kind == "range":
        return f"{attributes['low']}-{attributes['high']} {attributes['unit']}"
    comparator = attributes.get("comparator", "")
    return f"{comparator}{attributes['value']} {attributes['unit']}"


# extrai medicoes e evita spans sobrepostos
def extract_measurements(sentences):
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


# normaliza unidades temporais
def normalize_time_unit(unit):
    unit = unit.casefold()
    if unit in {"h", "hour", "hours"}:
        return "hour"
    return unit.rstrip("s")


# organiza os atributos de um candidato temporal
def temporal_attributes(kind, match):
    groups = match.groupdict()
    if groups.get("value"):
        value = parse_number(groups["value"])
    elif kind == "relative_day":
        value = ORDINAL_WORDS[groups["word"].casefold()]
    else:
        value = NUMBER_WORDS[groups["word"].casefold()]

    attributes = {"temporal_type": kind, "value": value, "unit": "day"}
    if groups.get("unit"):
        attributes["unit"] = normalize_time_unit(groups["unit"])
    if groups.get("marker"):
        attributes["marker"] = normalize_form(groups["marker"])
    return attributes


# extrai candidatos temporais sem criar nos
def extract_temporal_candidates(sentences):
    candidates = []
    candidate_number = 0

    for sentence in sentences:
        occupied = []
        matches = []
        for kind, rule_id, pattern in TEMPORAL_PATTERNS:
            for match in pattern.finditer(sentence["sentence_text"]):
                overlaps = any(
                    match.start() < end and start < match.end() for start, end in occupied
                )
                if overlaps:
                    continue
                occupied.append((match.start(), match.end()))
                matches.append((match.start(), match.end(), kind, rule_id, match))

        for start, end, kind, rule_id, match in sorted(matches):
            candidate_number += 1
            attributes = temporal_attributes(kind, match)
            original_span = sentence["sentence_text"][start:end]
            candidates.append(
                {
                    "candidate_id": f"{sentence['case_id']}_T{candidate_number:04d}",
                    "case_id": sentence["case_id"],
                    "sentence_id": sentence["sentence_id"],
                    "type": "TemporalCandidate",
                    "original_span": original_span,
                    "normalized_label": f"{attributes['value']} {attributes['unit']}",
                    "start_char": sentence["start_char"] + start,
                    "end_char": sentence["start_char"] + end,
                    "attributes": attributes,
                    "rule_id": rule_id,
                }
            )
    return candidates


# extrai intervalos de referencia com sinais explicitos
def extract_reference_range_candidates(sentences):
    candidates = []
    candidate_number = 0

    for sentence in sentences:
        matches = []
        for rule_id, pattern in REFERENCE_PATTERNS:
            for match in pattern.finditer(sentence["sentence_text"]):
                matches.append((match.start("reference"), rule_id, match))

        for start, rule_id, match in sorted(matches):
            groups = match.groupdict()
            unit = normalize_unit(groups["unit"])
            attributes = {
                "signal": normalize_form(groups["signal"]),
                "unit": unit,
                "evidence": match.group(0),
            }
            if groups.get("low"):
                attributes["reference_type"] = "range"
                attributes["low"] = parse_number(groups["low"])
                attributes["high"] = parse_number(groups["high"])
                normalized_label = f"{attributes['low']}-{attributes['high']} {unit}"
            else:
                attributes["reference_type"] = "threshold"
                attributes["comparator"] = groups["comparator"]
                attributes["value"] = parse_number(groups["value"])
                normalized_label = f"{groups['comparator']}{attributes['value']} {unit}"

            candidate_number += 1
            end = match.end("reference")
            candidates.append(
                {
                    "candidate_id": f"{sentence['case_id']}_R{candidate_number:04d}",
                    "case_id": sentence["case_id"],
                    "sentence_id": sentence["sentence_id"],
                    "type": "ReferenceRangeCandidate",
                    "original_span": sentence["sentence_text"][start:end],
                    "normalized_label": normalized_label,
                    "start_char": sentence["start_char"] + start,
                    "end_char": sentence["start_char"] + end,
                    "attributes": attributes,
                    "rule_id": rule_id,
                }
            )
    return candidates
