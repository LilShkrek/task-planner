import unittest

from app.semantic.extractor import extract_semantics, fallback_semantics


class SemanticJSONGenerator:
    def generate(self, prompt, max_chars=220):
        return """
        {
          "goal": "организовать поездку в Казань",
          "subgoals": ["выбрать даты", "рассчитать бюджет", "забронировать жилье", "составить маршрут"],
          "constraints": ["взять документы", "не выйти за бюджет"],
          "domain": "отпуск и поездка"
        }
        """


class BrokenSemanticGenerator:
    def generate(self, prompt, max_chars=220):
        return "не json"


class SemanticExtractorTest(unittest.TestCase):
    def test_extract_semantics_parses_generated_json(self):
        result = extract_semantics(
            {
                "title": "Организовать поездку в Казань",
                "description": "Выбрать даты, рассчитать бюджет, забронировать жилье и составить маршрут",
                "context": "отпуск",
            },
            text_generator=SemanticJSONGenerator(),
        )

        self.assertEqual(result["goal"], "организовать поездку в Казань")
        self.assertIn("рассчитать бюджет", result["subgoals"])
        self.assertIn("взять документы", result["constraints"])
        self.assertEqual(result["domain"], "отпуск и поездка")

    def test_extract_semantics_falls_back_to_raw_task_text(self):
        result = extract_semantics(
            {
                "title": "Организовать поездку в Казань",
                "description": "Выбрать даты, рассчитать бюджет, забронировать жилье и составить маршрут",
                "context": "отпуск",
            },
            text_generator=BrokenSemanticGenerator(),
        )

        self.assertEqual(result["goal"], "Организовать поездку в Казань")
        self.assertIn("Выбрать даты", result["subgoals"])
        self.assertIn("рассчитать бюджет", result["subgoals"])
        self.assertIn("отпуск", result["constraints"])

    def test_fallback_semantics_keeps_simple_json_shape(self):
        result = fallback_semantics(
            {
                "title": "Ответить на письмо",
                "description": "Уточнить дату сдачи и приложить файл",
                "context": "почта",
                "estimated_minutes": 30,
            }
        )

        self.assertEqual(set(result.keys()), {"goal", "subgoals", "constraints", "domain"})
        self.assertIn("Уточнить дату сдачи", result["subgoals"])
        self.assertIn("оценка времени: 30 минут", result["constraints"])


if __name__ == "__main__":
    unittest.main()
