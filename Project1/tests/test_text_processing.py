import unittest

from Project1.models import Sentence
from Project1.text_processing import segment_sentences, tokenize_sentence


class TextProcessingTests(unittest.TestCase):
    def test_sentence_offsets_and_decimal_protection(self):
        text = "Value was 9.5cm. St. Jude valve remained stable."
        sentences = segment_sentences("TEST_01", text)
        self.assertEqual(len(sentences), 2)
        for sentence in sentences:
            self.assertEqual(text[sentence.start_char:sentence.end_char], sentence.sentence_text)

    def test_required_clinical_tokens(self):
        text = "EUS-FNA CA 19-9 12,476.5ng/ml 6cm x 9cm mmHg C-reactive"
        sentence = Sentence("TEST_01", 1, text, 0, len(text))
        tokens = tokenize_sentence(sentence)
        forms = [token.token for token in tokens]
        for expected in [
            "EUS-FNA", "CA 19-9", "12,476.5ng/ml", "6cm", "x", "9cm", "mmHg", "C-reactive"
        ]:
            self.assertIn(expected, forms)
        for token in tokens:
            self.assertEqual(text[token.start_char:token.end_char], token.token)


if __name__ == "__main__":
    unittest.main()
