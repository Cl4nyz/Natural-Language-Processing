import unittest

from project1.nlp_utils import extract_measurements, split_sentences, tokenize


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


if __name__ == "__main__":
    unittest.main()
