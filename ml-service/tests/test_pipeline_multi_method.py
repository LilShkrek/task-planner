import unittest
from unittest.mock import patch

import torch

from app import pipeline
from app.models import perceptron


class FakeModel:
    def __call__(self, token_features, task_features):
        return {
            "method_scores": torch.tensor([[8.0, 7.7, 7.4, 7.2, 6.9, 6.6]], dtype=torch.float32),
            "planning_params": torch.tensor([[0.5, 0.25, 0.75, 0.4]], dtype=torch.float32),
        }


class AlwaysBadGenerator:
    def generate(self, prompt, max_chars=220):
        if "Поле: schedule_hint" in prompt:
            return "Расписание задачи."
        if "Поле: step_description" in prompt:
            return "Описание шага задачи."
        return "Задача"


class PipelineMultiMethodTest(unittest.TestCase):
    def setUp(self):
        perceptron.MODELS.clear()

    def tearDown(self):
        perceptron.MODELS.clear()

    def test_presentation_task_returns_selected_methods_and_staged_plan(self):
        result = self._analyze(
            {
                "title": "Подготовить презентацию по базам данных",
                "description": "Нужны слайды, структура и репетиция выступления",
                "context": "учебная задача",
                "priority": 4,
                "estimated_minutes": 120,
            },
            {
                "goal": "подготовить презентацию по базам данных",
                "subgoals": ["собрать материал", "составить структуру", "подготовить слайды", "прорепетировать выступление"],
                "constraints": ["учебная задача"],
                "domain": "presentation",
            },
        )

        self.assertEqual(len(result["selected_methods"]), 5)
        self.assertEqual(len(result["plan_draft"]), 5)
        self.assertEqual(
            list(result.keys())[:4],
            ["selection_mode", "user_facing_primary_strategy", "selected_methods", "combination_confidence"],
        )
        self.assertEqual(result["selection_mode"], "multi_method")
        self.assertEqual(result["user_facing_primary_strategy"], "Комбинированный план из 5 методов")
        self.assertNotIn("method_code", result)
        self.assertNotIn("method_name", result)
        self.assertNotIn("confidence", result)
        self.assertNotIn("reason", result)
        self.assertEqual(result["legacy_compatibility"]["method_code"], "smart")
        self.assertIn("reason_legacy", result["legacy_compatibility"])
        self.assertGreater(result["combination_confidence"], 0)
        self.assertIn("ranked_methods", result)
        self.assertIn("лучше одного метода", result["explanation"])
        self.assert_plan_matches_selected_methods(result)
        self.assertIn("слайд", result["plan_draft"][0]["description"].lower())

    def test_experiment_task_keeps_subject_steps(self):
        result = self._analyze(
            {
                "title": "Спланировать эксперименты для проверки гипотез",
                "description": "Нужно сформулировать гипотезы, критерии оценки и провести эксперименты",
                "context": "исследовательская работа",
                "priority": 4,
                "estimated_minutes": 150,
            },
            {
                "goal": "проверить гипотезы через эксперименты",
                "subgoals": ["сформулировать гипотезы", "определить критерии оценки", "провести эксперименты"],
                "constraints": ["зафиксировать результаты"],
                "domain": "research",
            },
        )

        text = " ".join(f"{step['title']} {step['description']}" for step in result["plan_draft"]).lower()
        self.assertIn("гипотез", text)
        self.assertIn("эксперимент", text)
        self.assertIn("selected_methods", result)
        self.assert_plan_matches_selected_methods(result)

    def test_travel_task_covers_travel_subgoals_with_selected_methods(self):
        result = self._analyze(
            {
                "title": "Спланировать отпуск в Казани",
                "description": "Выбрать даты поездки, определить бюджет, подобрать жилье, продумать маршрут и собрать вещи",
                "context": "личная поездка",
                "priority": 3,
                "estimated_minutes": 180,
            },
            {
                "goal": "спланировать отпуск в Казани",
                "subgoals": [
                    "выбрать даты поездки",
                    "определить бюджет",
                    "подобрать место проживания",
                    "продумать маршрут",
                    "собрать список вещей и документов",
                ],
                "constraints": ["личная поездка"],
                "domain": "travel",
            },
        )

        text = " ".join(f"{step['title']} {step['description']}" for step in result["plan_draft"]).lower()
        self.assertIn("дат", text)
        self.assertIn("бюджет", text)
        self.assertIn("жиль", text)
        self.assertIn("маршрут", text)
        self.assertIn("документ", text)
        summary = result["summary"].lower()
        self.assertIn("выбор дат", summary)
        self.assertIn("расчет бюджета", summary)
        self.assertIn("выбор жилья", summary)
        self.assertIn("составление маршрута", summary)
        self.assertIn("подготовку вещей и документов", summary)
        self.assertNotIn("маршрут и вещи и документы", summary)
        self.assertIn("этап", result["schedule_hint"].lower())
        self.assertIn("финальную проверку", result["schedule_hint"].lower())
        self.assert_plan_matches_selected_methods(result)

    def test_short_urgent_task_selects_compact_combination(self):
        result = self._analyze(
            {
                "title": "Срочно ответить на письмо",
                "description": "Коротко ответить преподавателю и приложить файл",
                "context": "почта",
                "priority": 5,
                "estimated_minutes": 20,
            },
            {
                "goal": "ответить на письмо",
                "subgoals": ["уточнить цель письма", "написать ответ", "проверить вложение"],
                "constraints": ["срочно"],
                "domain": "email",
            },
        )

        self.assertEqual(len(result["selected_methods"]), 3)
        self.assertEqual(len(result["plan_draft"]), 3)
        self.assertIn("Комбинация выбрана", result["explanation"])
        self.assertEqual(result["selection_mode"], "multi_method")
        self.assertEqual(result["user_facing_primary_strategy"], "Комбинированный план из 3 методов")
        self.assert_plan_matches_selected_methods(result)
        self.assertEqual(
            {method["plan_stage"] for method in result["selected_methods"]},
            {"prioritization", "execution_time", "review_control"},
        )

    def assert_plan_matches_selected_methods(self, result):
        selected = result["selected_methods"]
        steps = result["plan_draft"]
        self.assertGreaterEqual(len(selected), 3)
        self.assertLessEqual(len(selected), 5)
        self.assertEqual(len({method["plan_stage"] for method in selected}), len(selected))
        self.assertEqual(len(selected), len(steps))
        for method, step in zip(selected, steps):
            self.assertEqual(step["method_code"], method["code"])
            self.assertEqual(step["method_name"], method["name"])
            self.assertEqual(step["method_role"], method["role"])
            self.assertEqual(step["plan_stage"], method["plan_stage"])
            self.assertEqual(step["plan_function"], method["plan_function"])
            self.assertIn(method["name"], result["explanation"])
            self.assertIn(method["plan_function"], result["explanation"])

    def _analyze(self, task, semantic_structure):
        with patch.object(pipeline, "load_catalog", return_value=_catalog()):
            with patch.object(perceptron, "_model_for", return_value=FakeModel()):
                with patch.object(pipeline, "extract_semantics", return_value=semantic_structure):
                    with patch("app.generation.response_generator.get_text_generator", return_value=AlwaysBadGenerator()):
                        return pipeline.analyze_task(task)


def _catalog():
    methods = [
        _method("smart", "SMART", "формулировка цели", "уточняет измеримую цель"),
        _method("eisenhower", "Eisenhower Matrix", "приоритизация", "выбирает важное и срочное"),
        _method("wbs", "WBS", "декомпозиция", "разбивает работу на части"),
        _method("time_blocking", "Time Blocking", "распределение времени", "распределяет работу по календарю"),
        _method("single_tasking", "Single-Tasking", "выполнение", "удерживает фокус на одном действии"),
        _method("checklist", "Checklist Method", "контроль / завершение", "проверяет обязательные пункты"),
    ]
    return {
        "methods": methods,
        "templates": {
            method["code"]: {
                "steps": [
                    {"title": "Уточнить результат", "description": "Определить результат для {task_title}."},
                    {"title": "Выбрать главное", "description": "Отделить главное от второстепенного."},
                    {"title": "Разбить работу", "description": "Разложить задачу на части."},
                    {"title": "Выполнить этап", "description": "Сделать основной этап работы."},
                    {"title": "Проверить результат", "description": "Проверить итог и завершить задачу."},
                ],
                "schedule_hint": "Работать по этапам.",
            }
            for method in methods
        },
    }


def _method(code, name, group, role):
    return {
        "code": code,
        "name": name,
        "description": f"Описание метода {name}",
        "best_for": "учебные задачи",
        "group": group,
        "role": role,
    }


if __name__ == "__main__":
    unittest.main()
