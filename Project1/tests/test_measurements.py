import unittest

from Project1.measurements import extract_measurements
from Project1.text_processing import segment_sentences


class MeasurementExtractorTests(unittest.TestCase):
    def extract_one(self, text: str):
        results = extract_measurements(segment_sentences("TEST_01", text))
        self.assertEqual(len(results), 1, (text, results))
        return results[0]

    def test_required_positive_examples(self):
        examples = {
            "6cm": (6, "cm", "simple_measurement"),
            "6 cm": (6, "cm", "simple_measurement"),
            "9.5cm": (9.5, "cm", "simple_measurement"),
            "12,476.5ng/ml": (12476.5, "ng/mL", "simple_measurement"),
            "20.1 mmHg": (20.1, "mmHg", "simple_measurement"),
            "0.68 cm2": (0.68, "cm2", "simple_measurement"),
            "7-mm": (7, "mm", "simple_measurement"),
            "30%": (30, "%", "percentage"),
        }
        for text, (value, unit, kind) in examples.items():
            with self.subTest(text=text):
                entity = self.extract_one(text)
                self.assertEqual(entity.original_span, text)
                self.assertEqual(entity.attributes["value"], value)
                self.assertEqual(entity.attributes["unit"], unit)
                self.assertEqual(entity.attributes["measurement_type"], kind)

    def test_blood_pressure(self):
        entity = self.extract_one("138/94 mmHg")
        self.assertEqual(entity.attributes["systolic"], 138)
        self.assertEqual(entity.attributes["diastolic"], 94)
        self.assertEqual(entity.rule_id, "measurement_blood_pressure_v1")
        self.assertEqual(entity.normalized_label, "138/94 mmHg")

    def test_range(self):
        entity = self.extract_one("10-140 U/L")
        self.assertEqual(entity.attributes["low"], 10)
        self.assertEqual(entity.attributes["high"], 140)
        self.assertEqual(entity.rule_id, "measurement_range_v1")
        self.assertEqual(entity.normalized_label, "10-140 U/L")

    def test_dimension(self):
        entity = self.extract_one("6cm x 9cm")
        self.assertEqual(entity.attributes["values"], [6, 9])
        self.assertEqual(entity.attributes["units"], ["cm", "cm"])
        self.assertEqual(entity.rule_id, "measurement_dimension_v1")

        shared_unit = self.extract_one("3 x 3 cm")
        self.assertEqual(shared_unit.attributes["values"], [3, 3])
        self.assertEqual(shared_unit.attributes["units"], ["cm", "cm"])

    def test_contextual_numbers_are_not_measurements(self):
        for text in ["Figure 1", "Figure 2c", "day 4", "patient 2", "2014", "3-day history"]:
            with self.subTest(text=text):
                self.assertEqual(extract_measurements(segment_sentences("TEST_01", text)), [])

    def test_original_offsets(self):
        text = "Result was 6cm. Then 30% remained."
        for entity in extract_measurements(segment_sentences("TEST_01", text)):
            self.assertEqual(text[entity.start_char:entity.end_char], entity.original_span)
            self.assertEqual(entity.original_span, entity.original_span.strip())


if __name__ == "__main__":
    unittest.main()
