import unittest

from project1.nlp_utils import (
    extract_measurements,
    extract_reference_range_candidates,
    extract_temporal_candidates,
    split_sentences,
    tokenize,
)


class Project1Tests(unittest.TestCase):
    def extract_one(self, text):
        results = extract_measurements(split_sentences("TEST_01", text))
        self.assertEqual(len(results), 1)
        return results[0]

    def test_simple_measurements(self):
        examples = {
            "6cm": (6, "cm"),
            "6 cm": (6, "cm"),
            "9.5cm": (9.5, "cm"),
            "12,476.5ng/ml": (12476.5, "ng/mL"),
            "20.1 mmHg": (20.1, "mmHg"),
            "0.68 cm2": (0.68, "cm2"),
            "7-mm": (7, "mm"),
            "30%": (30, "%"),
        }
        for text, expected in examples.items():
            with self.subTest(text=text):
                result = self.extract_one(text)
                self.assertEqual(result["attributes"]["value"], expected[0])
                self.assertEqual(result["attributes"]["unit"], expected[1])

    def test_blood_pressure(self):
        result = self.extract_one("138/94 mmHg")
        self.assertEqual(result["attributes"]["systolic"], 138)
        self.assertEqual(result["attributes"]["diastolic"], 94)
        self.assertEqual(result["rule_id"], "measurement_blood_pressure_v1")

    def test_range(self):
        result = self.extract_one("10-140 U/L")
        self.assertEqual(result["attributes"]["low"], 10)
        self.assertEqual(result["attributes"]["high"], 140)
        self.assertEqual(result["rule_id"], "measurement_range_v1")

    def test_dimensions(self):
        for text, values in [("6cm x 9cm", [6, 9]), ("3 x 3 cm", [3, 3])]:
            with self.subTest(text=text):
                result = self.extract_one(text)
                self.assertEqual(result["attributes"]["values"], values)
                self.assertEqual(result["rule_id"], "measurement_dimension_v1")

    def test_numbers_without_measurement_unit(self):
        examples = ["Figure 1", "Figure 2c", "day 4", "patient 2", "2014", "3-day history"]
        for text in examples:
            with self.subTest(text=text):
                self.assertEqual(extract_measurements(split_sentences("TEST_01", text)), [])

    def test_offsets(self):
        text = "Result was 6cm. Then 30% remained."
        for result in extract_measurements(split_sentences("TEST_01", text)):
            start = result["start_char"]
            end = result["end_char"]
            self.assertEqual(text[start:end], result["original_span"])

    def test_sentence_segmentation(self):
        text = "Value was 9.5cm. St. Jude valve remained stable."
        sentences = split_sentences("TEST_01", text)
        self.assertEqual(len(sentences), 2)
        for sentence in sentences:
            self.assertEqual(
                text[sentence["start_char"]:sentence["end_char"]],
                sentence["sentence_text"],
            )

    def test_clinical_tokens(self):
        text = "EUS-FNA CA 19-9 12,476.5ng/ml 6cm x 9cm mmHg C-reactive"
        sentence = {
            "case_id": "TEST_01",
            "sentence_id": 1,
            "sentence_text": text,
            "start_char": 0,
            "end_char": len(text),
        }
        tokens = tokenize(sentence)
        forms = [token["token"] for token in tokens]
        expected = [
            "EUS-FNA", "CA 19-9", "12,476.5ng/ml", "6cm",
            "x", "9cm", "mmHg", "C-reactive",
        ]
        for token in expected:
            self.assertIn(token, forms)

    def test_temporal_candidates(self):
        text = "3-day history. Follow-up after 14 days and three months. Postoperative day 4. POD 7."
        sentences = split_sentences("TEST_01", text)
        candidates = extract_temporal_candidates(sentences)
        spans = [candidate["original_span"] for candidate in candidates]
        self.assertEqual(
            spans,
            ["3-day", "14 days", "three months", "Postoperative day 4", "POD 7"],
        )
        self.assertTrue(all(candidate["type"] == "TemporalCandidate" for candidate in candidates))

    def test_temporal_candidates_are_not_measurements(self):
        text = "Symptoms lasted 14 days and returned three months later."
        sentences = split_sentences("TEST_01", text)
        self.assertEqual(extract_measurements(sentences), [])
        self.assertEqual(len(extract_temporal_candidates(sentences)), 2)

    def test_patient_age_is_not_temporal_candidate(self):
        text = "A 44-year-old woman and an A-53-year old man were described."
        candidates = extract_temporal_candidates(split_sentences("TEST_01", text))
        self.assertEqual(candidates, [])

    def test_degraded_scientific_notation(self):
        result = self.extract_one("WBC, 12.65 x 109/L")
        self.assertEqual(result["original_span"], "12.65 x 109/L")
        self.assertEqual(result["normalized_label"], "12.65 × 10^9/L")
        self.assertEqual(result["attributes"]["value"], 12650000000)
        self.assertEqual(
            result["attributes"]["normalization_rule"],
            "normalize_degraded_scientific_notation_v1",
        )

    def test_reference_range_candidates(self):
        text = "Values: normal range (NR) 3800-10,000/mm3, NR <5 mg/L and reference range 3-20 mm/h."
        candidates = extract_reference_range_candidates(split_sentences("TEST_01", text))
        self.assertEqual(
            [candidate["original_span"] for candidate in candidates],
            ["3800-10,000/mm3", "<5 mg/L", "3-20 mm/h"],
        )
        self.assertTrue(
            all(candidate["type"] == "ReferenceRangeCandidate" for candidate in candidates)
        )

    def test_unitless_values_remain_outside_measurements(self):
        text = "A 4/6 murmur, 3-4 degree insufficiency and INR 2.0-3.0 were reported."
        self.assertEqual(extract_measurements(split_sentences("TEST_01", text)), [])

    def test_candidate_offsets(self):
        text = "After three months, normal range 10-140 U/L was reported."
        sentences = split_sentences("TEST_01", text)
        candidates = extract_temporal_candidates(sentences)
        candidates += extract_reference_range_candidates(sentences)
        for candidate in candidates:
            start = candidate["start_char"]
            end = candidate["end_char"]
            self.assertEqual(text[start:end], candidate["original_span"])


if __name__ == "__main__":
    unittest.main()
