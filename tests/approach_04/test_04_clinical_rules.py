import unittest

from src.approach_04_controlled_gazetteer.clinical_rules import (
    GAZETTEERS,
    extract_clinical_entities,
    extract_clinical_relations,
)
from src.approach_04_controlled_gazetteer.nlp_utils import split_sentences


class ClinicalRuleTests(unittest.TestCase):
    def process(self, text):
        sentences = split_sentences("TEST_01", text)
        entities = extract_clinical_entities(sentences)
        edges = extract_clinical_relations("TEST_01", sentences, entities)
        return entities, edges

    def test_alias_normalization(self):
        entities, _ = self.process("CT, CTA and EGD were reviewed.")
        labels = {entity["original_span"]: entity["normalized_label"] for entity in entities}
        self.assertEqual(labels["CT"], "computed tomography")
        self.assertEqual(labels["CTA"], "computed tomography angiography")
        self.assertEqual(labels["EGD"], "esophagogastroduodenoscopy")

    def test_multiword_matching(self):
        entities, _ = self.process("The patient had unintentional weight loss.")
        symptoms = [entity for entity in entities if entity["type"] == "Symptom"]
        self.assertEqual(len(symptoms), 1)
        self.assertEqual(symptoms[0]["original_span"], "unintentional weight loss")

    def test_presented_with_relation(self):
        _, edges = self.process("The patient presented with abdominal pain and nausea.")
        self.assertEqual([edge["relation"] for edge in edges], ["HAS_SYMPTOM", "HAS_SYMPTOM"])

        _, edges = self.process(
            "The patient presented to the emergency department with abdominal pain."
        )
        self.assertEqual(sum(edge["relation"] == "HAS_SYMPTOM" for edge in edges), 1)

    def test_underwent_relation(self):
        _, edges = self.process("The patient underwent CT and EGD.")
        underwent = [edge for edge in edges if edge["relation"] == "UNDERWENT"]
        self.assertEqual(len(underwent), 2)

    def test_exam_reveals_finding_patterns(self):
        for verb in ["showed", "revealed", "demonstrated", "demonstrating", "indicated"]:
            with self.subTest(verb=verb):
                _, edges = self.process(f"CT {verb} a cystic lesion.")
                reveals = [edge for edge in edges if edge["relation"] == "REVEALS"]
                self.assertEqual(len(reveals), 1)

    def test_history_relation(self):
        _, edges = self.process(
            "The patient had a history of hypertension and aortic valve replacement."
        )
        history = [edge for edge in edges if edge["relation"] == "HAS_HISTORY"]
        self.assertEqual(len(history), 2)

    def test_sign_relation(self):
        _, edges = self.process(
            "Physical examination revealed localized tenderness and rales."
        )
        signs = [edge for edge in edges if edge["relation"] == "HAS_SIGN"]
        self.assertEqual(len(signs), 2)

    def test_suspected_and_confirmed_diagnosis(self):
        text = (
            "Findings were suggesting the diagnosis of a mucinous pancreatic cystic neoplasm. "
            "The patient had a diagnosis of pulmonary embolism."
        )
        entities, edges = self.process(text)
        diagnoses = {
            entity["normalized_label"]: entity["attributes"]["certainty"]
            for entity in entities if entity["type"] == "Diagnosis"
        }
        self.assertEqual(diagnoses["mucinous pancreatic cystic neoplasm"], "suspected")
        self.assertEqual(diagnoses["pulmonary embolism"], "confirmed")
        self.assertEqual(sum(edge["relation"] == "HAS_DIAGNOSIS" for edge in edges), 2)

    def test_simple_negation(self):
        entities, _ = self.process("She had no fever. The obturator sign was negative.")
        assertions = {entity["original_span"]: entity["attributes"]["assertion"] for entity in entities}
        self.assertEqual(assertions["fever"], "negated")
        self.assertEqual(assertions["obturator sign"], "negated")

    def test_negation_over_list(self):
        entities, _ = self.process("She denied dysphagia, nausea, vomiting, and abdominal pain.")
        symptoms = [entity for entity in entities if entity["type"] == "Symptom"]
        self.assertEqual(len(symptoms), 4)
        self.assertTrue(all(entity["attributes"]["assertion"] == "negated" for entity in symptoms))

    def test_parenthetical_alias_is_not_duplicated(self):
        entities, _ = self.process("The patient underwent pulmonary CTA for pulmonary embolism (PE).")
        diagnoses = [entity for entity in entities if entity["type"] == "Diagnosis"]
        self.assertEqual(len(diagnoses), 1)

    def test_free_of_requires_copular_context(self):
        entities, _ = self.process("The pancreas was mobilised free of the cyst.")
        cyst = next(entity for entity in entities if entity["original_span"] == "cyst")
        self.assertEqual(cyst["attributes"]["assertion"], "present")

    def test_expanded_terms_were_removed(self):
        removed_terms = {
            "computed tomography angiography",
            "iron deficiency anemia",
            "left lower pulmonary artery branch",
            "right lower quadrant",
            "right pulmonary artery branch",
            "left pulmonary branch",
            "left ventricle",
        }
        current_terms = {
            term for gazetteer in GAZETTEERS.values() for term in gazetteer
        }
        self.assertTrue(removed_terms.isdisjoint(current_terms))

    def test_admitted_with_and_experienced_relations(self):
        _, edges = self.process("The patient was admitted with chest tightness and fever.")
        self.assertEqual(sum(edge["relation"] == "HAS_SYMPTOM" for edge in edges), 2)

        _, edges = self.process("He experienced dyspnea, fever, and chills.")
        self.assertEqual(sum(edge["relation"] == "HAS_SYMPTOM" for edge in edges), 3)

    def test_procedure_was_performed_relation(self):
        _, edges = self.process("A laparoscopic appendectomy was performed successfully.")
        underwent = [edge for edge in edges if edge["relation"] == "UNDERWENT"]
        self.assertEqual(len(underwent), 1)
        self.assertEqual(underwent[0]["rule_id"], "patient_underwent_procedure_performed_v1")

    def test_sign_polarity_relations(self):
        entities, edges = self.process(
            "McBurney's point was positive and the obturator sign was negative."
        )
        signs = {
            entity["normalized_label"]: entity["attributes"]["assertion"]
            for entity in entities if entity["type"] == "Sign"
        }
        self.assertEqual(signs["McBurney's point"], "present")
        self.assertEqual(signs["obturator sign"], "negated")
        sign_edges = [edge for edge in edges if edge["relation"] == "HAS_SIGN"]
        self.assertEqual(len(sign_edges), 2)
        self.assertEqual(
            {edge["attributes"]["assertion"] for edge in sign_edges},
            {"present", "negated"},
        )


if __name__ == "__main__":
    unittest.main()
