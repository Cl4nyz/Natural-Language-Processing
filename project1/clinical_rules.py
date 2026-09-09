"""Gazetteers y reglas clínicas explícitas de la Iteración 2."""

import json
import re
from pathlib import Path


def load_gazetteers(path=None):
    """Carga los términos clínicos desde el archivo JSON."""
    path = path or Path(__file__).with_name("gazetteers.json")
    with path.open(encoding="utf-8") as file:
        return json.load(file)


GAZETTEERS = load_gazetteers()

NEGATION_CUES = re.compile(
    r"\b(no evidence of|did not show|did not identify|negative for|"
    r"(?:was|were|is|are)\s+free of|denied|no|negative)\b",
    re.IGNORECASE,
)
NEGATION_STOP = re.compile(r"\b(but|however|although)\b|;", re.IGNORECASE)
POST_NEGATION = re.compile(r"^\s+(?:was|were|is|are)?\s*negative\b", re.IGNORECASE)


def flexible_term_pattern(term):
    pieces = [re.escape(piece) for piece in term.split()]
    return r"(?<![A-Za-z0-9])" + r"\s+".join(pieces) + r"(?![A-Za-z0-9])"


def find_assertion(sentence_text, start, end):
    assertion = "present"
    for cue in NEGATION_CUES.finditer(sentence_text[:start]):
        scope_end = len(sentence_text)
        stop = NEGATION_STOP.search(sentence_text, cue.end())
        if stop:
            scope_end = stop.start()
        if cue.end() <= start <= scope_end:
            assertion = "negated"
    if POST_NEGATION.search(sentence_text[end:end + 30]):
        assertion = "negated"
    return assertion


def diagnosis_certainty(sentence_text, start):
    context = sentence_text[max(0, start - 80):start]
    if re.search(r"\b(suggesting|suspecting|suspected)\b", context, re.IGNORECASE):
        return "suspected"
    return "confirmed"


def extract_clinical_entities(sentences):
    entities = []
    entity_number = 0

    for sentence in sentences:
        matches = []
        for entity_type, terms in GAZETTEERS.items():
            for term, normalized_label in terms.items():
                pattern = re.compile(flexible_term_pattern(term), re.IGNORECASE)
                for match in pattern.finditer(sentence["sentence_text"]):
                    matches.append(
                        (match.start(), match.end(), entity_type, normalized_label, term)
                    )

        # Longest match wins when gazetteer entries overlap.
        selected = []
        occupied = []
        for start, end, entity_type, normalized_label, term in sorted(
            matches, key=lambda item: (item[0], -(item[1] - item[0]))
        ):
            if any(start < old_end and old_start < end for old_start, old_end in occupied):
                continue
            occupied.append((start, end))
            selected.append((start, end, entity_type, normalized_label, term))

        # Do not create a second mention for a parenthetical alias immediately
        # following its full form: esophagogastroduodenoscopy (EGD).
        without_parenthetical_aliases = []
        for item in sorted(selected):
            start, end, entity_type, normalized_label, _term = item
            repeated_alias = False
            for previous in without_parenthetical_aliases:
                previous_start, previous_end, previous_type, previous_label, _ = previous
                between = sentence["sentence_text"][previous_end:start]
                after = sentence["sentence_text"][end:end + 1]
                if (
                    previous_type == entity_type
                    and previous_label == normalized_label
                    and re.fullmatch(r"\s*\(\s*", between)
                    and after == ")"
                ):
                    repeated_alias = True
                    break
            if not repeated_alias:
                without_parenthetical_aliases.append(item)
        selected = without_parenthetical_aliases

        for start, end, entity_type, normalized_label, term in sorted(selected):
            entity_number += 1
            assertion_types = {"Symptom", "Sign", "Finding", "Diagnosis"}
            assertion = "present"
            if entity_type in assertion_types:
                assertion = find_assertion(sentence["sentence_text"], start, end)
            attributes = {"assertion": assertion, "gazetteer_term": term}
            if entity_type == "Diagnosis":
                attributes["certainty"] = diagnosis_certainty(
                    sentence["sentence_text"], start
                )
            entities.append(
                {
                    "entity_id": f"{sentence['case_id']}_C{entity_number:04d}",
                    "case_id": sentence["case_id"],
                    "sentence_id": sentence["sentence_id"],
                    "type": entity_type,
                    "original_span": sentence["sentence_text"][start:end],
                    "normalized_label": normalized_label,
                    "start_char": sentence["start_char"] + start,
                    "end_char": sentence["start_char"] + end,
                    "attributes": attributes,
                    "rule_id": f"gazetteer_{entity_type.casefold()}_v1",
                }
            )
    return entities


def add_edge(edges, case_id, source_id, target_id, relation, sentence, rule_id, attributes):
    key = (source_id, target_id, relation)
    if any((edge["source_id"], edge["target_id"], edge["relation"]) == key for edge in edges):
        return
    edges.append(
        {
            "case_id": case_id,
            "edge_id": f"{case_id}_E{len(edges) + 1:04d}",
            "source_id": source_id,
            "target_id": target_id,
            "relation": relation,
            "attributes": attributes,
            "evidence": sentence["sentence_text"],
            "sentence_id": sentence["sentence_id"],
            "rule_id": rule_id,
        }
    )


def entities_after(entities, position, allowed_types):
    return [
        entity for entity in entities
        if entity["type"] in allowed_types and entity["start_char"] >= position
    ]


def extract_clinical_relations(case_id, sentences, entities):
    edges = []
    patient_id = f"{case_id}_PATIENT"

    for sentence in sentences:
        sentence_entities = [
            entity for entity in entities if entity["sentence_id"] == sentence["sentence_id"]
        ]
        local_start = sentence["start_char"]
        text = sentence["sentence_text"]

        presented_pattern = r"\bpresented(?:\s+to\s+[^,.;]{1,80})?\s+with\b"
        for trigger in re.finditer(presented_pattern, text, re.IGNORECASE):
            for entity in entities_after(
                sentence_entities, local_start + trigger.end(), {"Symptom"}
            ):
                add_edge(
                    edges, case_id, patient_id, entity["entity_id"], "HAS_SYMPTOM",
                    sentence, "patient_has_symptom_presented_with_v1",
                    {"assertion": entity["attributes"]["assertion"]},
                )

        admitted_pattern = r"\bwas\s+admitted(?:\s+to\s+[^,.;]{1,80})?\s+with\b"
        for trigger in re.finditer(admitted_pattern, text, re.IGNORECASE):
            for entity in entities_after(
                sentence_entities, local_start + trigger.end(), {"Symptom"}
            ):
                add_edge(
                    edges, case_id, patient_id, entity["entity_id"], "HAS_SYMPTOM",
                    sentence, "patient_has_symptom_admitted_with_v1",
                    {"assertion": entity["attributes"]["assertion"]},
                )

        for trigger in re.finditer(r"\bexperienced\b", text, re.IGNORECASE):
            for entity in entities_after(
                sentence_entities, local_start + trigger.end(), {"Symptom"}
            ):
                add_edge(
                    edges, case_id, patient_id, entity["entity_id"], "HAS_SYMPTOM",
                    sentence, "patient_has_symptom_experienced_v1",
                    {"assertion": entity["attributes"]["assertion"]},
                )

        sign_trigger = re.search(r"\bphysical examination\s+revealed\b", text, re.IGNORECASE)
        if sign_trigger:
            for entity in entities_after(
                sentence_entities, local_start + sign_trigger.end(), {"Sign"}
            ):
                add_edge(
                    edges, case_id, patient_id, entity["entity_id"], "HAS_SIGN",
                    sentence, "patient_has_sign_physical_exam_v1",
                    {"assertion": entity["attributes"]["assertion"]},
                )

        for sign in sentence_entities:
            if sign["type"] != "Sign":
                continue
            local_end = sign["end_char"] - local_start
            if re.match(r"\s+was\s+(?:positive|negative)\b", text[local_end:], re.IGNORECASE):
                add_edge(
                    edges, case_id, patient_id, sign["entity_id"], "HAS_SIGN",
                    sentence, "patient_has_sign_polarity_v1",
                    {"assertion": sign["attributes"]["assertion"]},
                )

        history_patterns = [
            re.compile(r"\bmedical history\s+included\b", re.IGNORECASE),
            re.compile(r"\bhistory\s+of\b", re.IGNORECASE),
        ]
        for pattern in history_patterns:
            for trigger in pattern.finditer(text):
                before = text[max(0, trigger.start() - 10):trigger.start()]
                if re.search(r"family\s*$", before, re.IGNORECASE):
                    continue
                for entity in entities_after(
                    sentence_entities,
                    local_start + trigger.end(),
                    {"Diagnosis", "Procedure"},
                ):
                    add_edge(
                        edges, case_id, patient_id, entity["entity_id"], "HAS_HISTORY",
                        sentence, "patient_has_history_explicit_v1",
                        {"assertion": entity["attributes"]["assertion"]},
                    )

        for trigger in re.finditer(r"\bunderwent\b", text, re.IGNORECASE):
            for entity in entities_after(
                sentence_entities, local_start + trigger.end(), {"Exam", "Procedure"}
            ):
                add_edge(
                    edges, case_id, patient_id, entity["entity_id"], "UNDERWENT",
                    sentence, "patient_underwent_explicit_v1",
                    {"assertion": entity["attributes"]["assertion"]},
                )

        for procedure in sentence_entities:
            if procedure["type"] != "Procedure":
                continue
            local_end = procedure["end_char"] - local_start
            if re.match(r"\s+was\s+performed\b", text[local_end:], re.IGNORECASE):
                add_edge(
                    edges, case_id, patient_id, procedure["entity_id"], "UNDERWENT",
                    sentence, "patient_underwent_procedure_performed_v1",
                    {"assertion": procedure["attributes"]["assertion"]},
                )

        verb_pattern = r"\b(showed|revealed|demonstrated|demonstrating|indicated)\b"
        for verb in re.finditer(verb_pattern, text, re.IGNORECASE):
            exams_before = [
                entity for entity in sentence_entities
                if entity["type"] == "Exam" and entity["end_char"] <= local_start + verb.start()
            ]
            if not exams_before:
                continue
            exam = max(exams_before, key=lambda entity: entity["end_char"])
            for finding in entities_after(
                sentence_entities, local_start + verb.end(), {"Finding"}
            ):
                add_edge(
                    edges, case_id, exam["entity_id"], finding["entity_id"], "REVEALS",
                    sentence, "exam_reveals_finding_explicit_v1",
                    {"assertion": finding["attributes"]["assertion"]},
                )

        diagnosis_triggers = re.compile(
            r"\b(suggesting\s+the\s+diagnosis\s+of|diagnosis\s+of|diagnosed\s+with|consistent\s+with)\b",
            re.IGNORECASE,
        )
        for trigger in diagnosis_triggers.finditer(text):
            for diagnosis in entities_after(
                sentence_entities, local_start + trigger.end(), {"Diagnosis"}
            ):
                add_edge(
                    edges, case_id, patient_id, diagnosis["entity_id"], "HAS_DIAGNOSIS",
                    sentence, "patient_has_diagnosis_explicit_v1",
                    {
                        "assertion": diagnosis["attributes"]["assertion"],
                        "certainty": diagnosis["attributes"]["certainty"],
                    },
                )

        for diagnosis in sentence_entities:
            if diagnosis["type"] != "Diagnosis":
                continue
            local_end = diagnosis["end_char"] - local_start
            if re.match(r"\s+was\s+diagnosed\b", text[local_end:], re.IGNORECASE):
                add_edge(
                    edges, case_id, patient_id, diagnosis["entity_id"], "HAS_DIAGNOSIS",
                    sentence, "patient_has_diagnosis_passive_v1",
                    {
                        "assertion": diagnosis["attributes"]["assertion"],
                        "certainty": diagnosis["attributes"]["certainty"],
                    },
                )
    return edges
