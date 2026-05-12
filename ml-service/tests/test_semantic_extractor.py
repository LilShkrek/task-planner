import unittest

from app.semantic.extractor import autonomous_decomposition, extract_semantics, fallback_semantics


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
        self.assertEqual(result["domain"], "travel")
        self.assertIn("выбрать даты поездки", result["base_subgoals_from_title"])
        self.assertIn("рассчитать бюджет", result["description_hints"])
        self.assertEqual(result["subgoals"], result["merged_subgoals"])
        self.assertGreater(result["decomposition_confidence"], 0)

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
        self.assertIn("выбрать даты поездки", result["subgoals"])
        self.assertIn("рассчитать бюджет", result["subgoals"])
        self.assertIn("отпуск", result["constraints"])
        self.assertEqual(result["domain"], "travel")

    def test_fallback_semantics_keeps_simple_json_shape(self):
        result = fallback_semantics(
            {
                "title": "Ответить на письмо",
                "description": "Уточнить дату сдачи и приложить файл",
                "context": "почта",
                "estimated_minutes": 30,
            }
        )

        self.assertEqual(
            set(result.keys()),
            {
                "goal",
                "subgoals",
                "constraints",
                "domain",
                "base_subgoals_from_title",
                "description_hints",
                "merged_subgoals",
                "decomposition_confidence",
            },
        )
        self.assertIn("уточнить цель письма", result["subgoals"])
        self.assertIn("уточнить дату сдачи", result["description_hints"])
        self.assertIn("оценка времени: 30 минут", result["constraints"])
        self.assertEqual(result["domain"], "email")

    def test_domain_is_normalized_from_noisy_phrase(self):
        result = fallback_semantics(
            {
                "title": "Спланировать отпуск",
                "description": "Выбрать даты, рассчитать бюджет и забронировать жилье",
                "context": "личная задача",
            }
        )

        self.assertEqual(result["domain"], "travel")

    def test_title_only_builds_autonomous_travel_decomposition(self):
        result = fallback_semantics(
            {
                "title": "Спланировать отпуск в Казани",
                "description": "",
                "context": "личная поездка",
                "estimated_minutes": 180,
            }
        )

        self.assertIn("выбрать даты поездки", result["base_subgoals_from_title"])
        self.assertIn("рассчитать бюджет", result["subgoals"])
        self.assertIn("подобрать жилье", result["subgoals"])
        self.assertIn("составить маршрут", result["subgoals"])
        self.assertNotIn("оценка времени: 180 минут", result["subgoals"])
        self.assertEqual(result["description_hints"], [])

    def test_description_hints_do_not_replace_title_first_frame(self):
        title = "Подготовить презентацию по базам данных"
        title_only = fallback_semantics({"title": title, "description": "", "context": "учебная задача"})
        short_description = fallback_semantics(
            {
                "title": title,
                "description": "Нужны слайды",
                "context": "учебная задача",
            }
        )
        detailed_description = fallback_semantics(
            {
                "title": title,
                "description": "Собрать материалы, составить структуру, сделать слайды, прорепетировать выступление",
                "context": "учебная задача",
            }
        )

        self.assertEqual(title_only["base_subgoals_from_title"], short_description["base_subgoals_from_title"])
        self.assertEqual(title_only["base_subgoals_from_title"], detailed_description["base_subgoals_from_title"])
        self.assertIn("собрать материалы", detailed_description["description_hints"])
        self.assertIn("подготовить слайды", detailed_description["description_hints"])
        self.assertLess(len(detailed_description["description_hints"]), 5)

    def test_autonomous_decomposition_keeps_description_as_hints(self):
        result = autonomous_decomposition(
            {
                "title": "Спланировать эксперименты для проверки гипотез",
                "description": "Сначала сформулировать гипотезы; потом определить критерии оценки; затем провести эксперименты",
                "context": "исследовательская работа",
            }
        )

        self.assertIn("сформулировать гипотезы", result["base_subgoals_from_title"])
        self.assertIn("определить критерии оценки", result["description_hints"])
        self.assertEqual(result["merged_subgoals"][0], "сформулировать гипотезы")
        self.assertGreaterEqual(result["decomposition_confidence"], 0.75)


if __name__ == "__main__":
    unittest.main()
