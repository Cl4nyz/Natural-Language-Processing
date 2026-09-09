"""Interpretable regular expressions for Iteration 1 measurements."""

import re
from decimal import Decimal
from typing import Any

from .models import Entity, Sentence


NUMBER = r"\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?"
LENGTH_UNIT = r"cm(?:2|²)?|mm(?:2|²)?|m(?:2|²)?"
UNIT = (
    r"mg\s+per\s+day|beats/min|mcg/dL|ng/mL|mg/L|g/dL|IU/mL|U/L|"
    r"/mm3|mmHg|mm/h|cm2|cm²|mm2|mm²|cm|mm|mg|"
    r"months?|weeks?|days?|h|C"
)

_PATTERNS = [
    (
        "blood_pressure",
        "measurement_blood_pressure_v1",
        re.compile(
            rf"(?P<systolic>{NUMBER})\s*/\s*(?P<diastolic>{NUMBER})\s*(?P<unit>mmHg)(?![A-Za-z0-9])",
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
            rf"(?P<low>{NUMBER})\s*[-–]\s*(?P<high>{NUMBER})\s*(?P<unit>{UNIT})(?![A-Za-z0-9])",
            re.IGNORECASE,
        ),
    ),
    (
        "percentage",
        "measurement_percentage_v1",
        re.compile(rf"(?:(?P<comparator>[<>≤≥])\s*)?(?P<value>{NUMBER})\s*(?P<unit>%)(?![A-Za-z0-9])"),
    ),
    (
        "simple_measurement",
        "measurement_value_unit_v1",
        re.compile(
            rf"(?:(?P<comparator>[<>≤≥])\s*)?(?P<value>{NUMBER})(?P<separator>\s*-?\s*)(?P<unit>{UNIT})(?![A-Za-z0-9])",
            re.IGNORECASE,
        ),
    ),
]

_UNIT_NORMALIZATION = {
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


def parse_number(raw: str) -> int | float:
    number = Decimal(raw.replace(",", ""))
    return int(number) if number == number.to_integral_value() else float(number)


def normalize_unit(unit: str) -> str:
    compact = re.sub(r"\s+", " ", unit.strip())
    return _UNIT_NORMALIZATION.get(compact.casefold(), compact)


def _normalized_label(attributes: dict[str, Any]) -> str:
    kind = attributes["measurement_type"]
    if kind == "blood_pressure":
        return f"{attributes['systolic']}/{attributes['diastolic']} {attributes['unit']}"
    if kind == "dimension":
        return " x ".join(
            f"{value} {unit}" for value, unit in zip(attributes["values"], attributes["units"])
        )
    if kind == "range":
        return f"{attributes['low']}-{attributes['high']} {attributes['unit']}"
    comparator = attributes.get("comparator", "")
    return f"{comparator}{attributes['value']} {attributes['unit']}"


def _attributes(kind: str, match: re.Match[str]) -> dict[str, Any]:
    groups = match.groupdict()
    if kind == "blood_pressure":
        return {
            "measurement_type": kind,
            "systolic": parse_number(groups["systolic"]),
            "diastolic": parse_number(groups["diastolic"]),
            "unit": normalize_unit(groups["unit"]),
        }
    if kind == "dimension":
        values = [parse_number(groups["v1"]), parse_number(groups["v2"])]
        present_units = [groups.get("u1"), groups.get("u2"), groups.get("u3")]
        shared_unit = normalize_unit(next(unit for unit in reversed(present_units) if unit))
        units = [normalize_unit(groups["u1"]) if groups.get("u1") else shared_unit,
                 normalize_unit(groups["u2"]) if groups.get("u2") else shared_unit]
        if groups.get("v3"):
            values.append(parse_number(groups["v3"]))
            units.append(normalize_unit(groups["u3"]) if groups.get("u3") else shared_unit)
        return {"measurement_type": kind, "values": values, "units": units}
    if kind == "range":
        return {
            "measurement_type": kind,
            "low": parse_number(groups["low"]),
            "high": parse_number(groups["high"]),
            "unit": normalize_unit(groups["unit"]),
        }
    result: dict[str, Any] = {
        "measurement_type": kind,
        "value": parse_number(groups["value"]),
        "unit": normalize_unit(groups["unit"]),
    }
    if groups.get("comparator"):
        result["comparator"] = groups["comparator"]
    return result


def extract_measurements(sentences: list[Sentence]) -> list[Entity]:
    entities: list[Entity] = []
    case_counter = 0
    for sentence in sentences:
        occupied: list[tuple[int, int]] = []
        candidates: list[tuple[int, int, str, str, re.Match[str]]] = []
        for kind, rule_id, pattern in _PATTERNS:
            for match in pattern.finditer(sentence.sentence_text):
                groups = match.groupdict()
                if kind == "dimension" and not any(
                    groups.get(name) for name in ("u1", "u2", "u3")
                ):
                    continue
                if kind == "simple_measurement":
                    unit = groups["unit"].casefold()
                    separator = groups.get("separator", "")
                    # Attached C occurs in figure labels (e.g. Figure 2c); clinical
                    # temperatures in this corpus use whitespace (38.7 C).
                    if unit == "c" and not separator:
                        continue
                    # Hyphenated durations (3-day history) carry temporal semantics
                    # that are intentionally deferred; physical measures such as
                    # 7-mm remain valid measurements.
                    if "-" in separator and unit.rstrip("s") in {"day", "week", "month"}:
                        continue
                if any(match.start() < end and start < match.end() for start, end in occupied):
                    continue
                occupied.append((match.start(), match.end()))
                candidates.append((match.start(), match.end(), kind, rule_id, match))
        for local_start, local_end, kind, rule_id, match in sorted(candidates):
            case_counter += 1
            original_span = sentence.sentence_text[local_start:local_end]
            attrs = _attributes(kind, match)
            entities.append(
                Entity(
                    entity_id=f"{sentence.case_id}_M{case_counter:04d}",
                    case_id=sentence.case_id,
                    sentence_id=sentence.sentence_id,
                    type="Measurement",
                    original_span=original_span,
                    normalized_label=_normalized_label(attrs),
                    start_char=sentence.start_char + local_start,
                    end_char=sentence.start_char + local_end,
                    attributes=attrs,
                    rule_id=rule_id,
                )
            )
    return entities
