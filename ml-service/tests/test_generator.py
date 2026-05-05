import unittest

from app.planning.generator import generate_plan


class GeneratorTest(unittest.TestCase):
    def test_generate_plan_uses_json_template_from_database(self):
        task = {
            "title": "Проверить настройки приложения",
            "estimated_minutes": 90,
        }
        prediction = {
            "method_code": "pomodoro",
            "planning_params": {"review_minutes": 20},
        }
        templates = {
            "pomodoro": {
                "steps": [
                    {
                        "title": "Собрать материалы",
                        "description": "Собрать материалы для задачи \"{task_title}\".",
                    },
                    {
                        "title": "Проверить результат",
                        "description": "Проверить итог задачи \"{task_title}\".",
                    },
                ]
            }
        }

        plan = generate_plan(task, prediction, templates)

        self.assertEqual(len(plan), 2)
        self.assertEqual(plan[0]["title"], "Собрать материалы")
        self.assertEqual(plan[0]["description"], "Собрать материалы для задачи \"Проверить настройки приложения\".")
        self.assertEqual(plan[0]["estimated_minutes"], 45)
        self.assertEqual(plan[1]["estimated_minutes"], 20)
        self.assertEqual(plan[1]["status"], "pending")

    def test_generate_plan_requires_template_steps(self):
        with self.assertRaisesRegex(RuntimeError, "не содержит шагов"):
            generate_plan(
                {"title": "Задача", "estimated_minutes": 60},
                {"method_code": "pomodoro", "planning_params": {}},
                {"pomodoro": {"steps": []}},
            )

    def test_generate_plan_adapts_presentation_steps(self):
        task = {
            "title": "Подготовить презентацию по базам данных",
            "description": "Нужны слайды и выступление",
            "estimated_minutes": 120,
        }
        prediction = {
            "method_code": "time_blocking",
            "planning_params": {},
        }
        templates = {
            "time_blocking": {
                "steps": [
                    {"title": "Шаблонный шаг 1", "description": "Шаблонное описание 1"},
                    {"title": "Шаблонный шаг 2", "description": "Шаблонное описание 2"},
                ]
            }
        }

        plan = generate_plan(task, prediction, templates)

        self.assertEqual(plan[0]["title"], "Собрать материалы для выступления")
        self.assertIn("Подготовить презентацию по базам данных", plan[0]["description"])
        self.assertEqual(plan[1]["title"], "Собрать структуру слайдов")

    def test_generate_plan_keeps_base_template_for_unknown_task_type(self):
        task = {
            "title": "Навести порядок в настройках",
            "description": "Проверить параметры приложения",
            "estimated_minutes": 60,
        }
        prediction = {
            "method_code": "pomodoro",
            "planning_params": {},
        }
        templates = {
            "pomodoro": {
                "steps": [
                    {"title": "Базовый шаг", "description": "Базовое описание для \"{task_title}\"."},
                ]
            }
        }

        plan = generate_plan(task, prediction, templates)

        self.assertEqual(plan[0]["title"], "Базовый шаг")
        self.assertEqual(plan[0]["description"], "Базовое описание для \"Навести порядок в настройках\".")


if __name__ == "__main__":
    unittest.main()
