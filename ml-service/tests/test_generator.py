import unittest

from app.planning.generator import generate_plan


class GeneratorTest(unittest.TestCase):
    def test_generate_plan_uses_json_template_from_database(self):
        task = {
            "title": "Подготовить доклад",
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
        self.assertEqual(plan[0]["description"], "Собрать материалы для задачи \"Подготовить доклад\".")
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


if __name__ == "__main__":
    unittest.main()
