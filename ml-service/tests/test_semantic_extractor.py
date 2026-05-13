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
                "task_archetypes",
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

    def test_event_planning_archetype_avoids_generic_fallback(self):
        result = autonomous_decomposition(
            {
                "title": "Организовать сюрприз на день рождения для друга",
                "description": "",
                "context": "личная задача",
            }
        )

        self.assertIn("event_planning", result["task_archetypes"])
        self.assertIn("social_coordination", result["task_archetypes"])
        self.assertIn("определить формат события", result["base_subgoals_from_title"])
        self.assertIn("согласовать участников и детали", result["merged_subgoals"])
        self.assertIn("подготовить подарок или сценарий", result["merged_subgoals"])
        self.assertEqual(result["domain"], "event_planning")
        self.assertNotIn("выполнить основной этап", result["merged_subgoals"])

    def test_event_archetype_domain_is_not_travel_after_finalization(self):
        result = fallback_semantics(
            {
                "title": "Организовать сюрприз на день рождения для друга",
                "description": "",
                "context": "личная задача",
            }
        )

        self.assertEqual(result["domain"], "event_planning")
        self.assertNotEqual(result["domain"], "travel")
        self.assertIn("event_planning", result["task_archetypes"])
        self.assertIn("рассчитать бюджет", result["subgoals"])

    def test_career_planning_archetype_builds_decision_frame(self):
        result = autonomous_decomposition(
            {
                "title": "Разобраться с карьерным направлением на ближайший год",
                "description": "",
                "context": "личная стратегия",
            }
        )

        self.assertIn("career_planning", result["task_archetypes"])
        self.assertIn("decision_making", result["task_archetypes"])
        self.assertIn("уточнить карьерную цель на год", result["base_subgoals_from_title"])
        self.assertIn("собрать возможные направления", result["merged_subgoals"])
        self.assertIn("определить критерии выбора", result["merged_subgoals"])
        self.assertNotIn("разбить задачу на этапы", result["merged_subgoals"])

    def test_creative_project_archetype_for_youtube_concept(self):
        result = autonomous_decomposition(
            {
                "title": "Придумать концепцию собственного YouTube-канала",
                "description": "",
                "context": "личный творческий проект",
            }
        )

        self.assertIn("creative_project", result["task_archetypes"])
        self.assertIn("определить аудиторию и тему", result["base_subgoals_from_title"])
        self.assertIn("сформулировать концепцию YouTube-канала", result["merged_subgoals"])
        self.assertNotIn("проверить итог", result["merged_subgoals"])

    def test_logistics_and_personal_organization_archetype_for_move_and_deadlines(self):
        result = autonomous_decomposition(
            {
                "title": "Подготовить переезд и не завалить учебные дедлайны",
                "description": "",
                "context": "учеба и бытовая организация",
            }
        )

        self.assertIn("logistics", result["task_archetypes"])
        self.assertIn("personal_organization", result["task_archetypes"])
        self.assertIn("определить дату и объем переезда", result["base_subgoals_from_title"])
        self.assertIn("организовать транспорт и помощь", result["merged_subgoals"])
        self.assertIn("сохранить учебные дедлайны", result["merged_subgoals"])
        self.assertNotIn("выполнить основной этап", result["merged_subgoals"])


if __name__ == "__main__":
    unittest.main()
