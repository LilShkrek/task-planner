import unittest

from app.models.multi_method import select_methods


class MultiMethodSelectionTest(unittest.TestCase):
    def test_selects_diverse_methods_for_presentation_task(self):
        result = select_methods(
            _ranked_methods(),
            {"title": "Подготовить презентацию", "estimated_minutes": 120, "priority": 4},
        )

        selected = result["selected_methods"]
        self.assertEqual(len(selected), 5)
        self.assertEqual(len({method["group"] for method in selected}), 5)
        self.assertEqual(len({method["plan_stage"] for method in selected}), 5)
        self.assertIn("формулировка цели", {method["group"] for method in selected})
        self.assertIn("контроль / завершение", {method["group"] for method in selected})
        self.assertGreater(result["combination_confidence"], 0)
        self.assertIn("лучше одного метода", result["explanation"])

    def test_selects_three_methods_for_short_urgent_task(self):
        result = select_methods(
            _ranked_methods(),
            {"title": "Срочно ответить на письмо", "estimated_minutes": 20, "priority": 5},
        )

        selected = result["selected_methods"]
        self.assertEqual(len(selected), 3)
        self.assertEqual(len({method["code"] for method in selected}), 3)
        self.assertEqual(
            {method["plan_stage"] for method in selected},
            {"prioritization", "execution_time", "review_control"},
        )

    def test_selection_does_not_duplicate_roles_before_covering_groups(self):
        ranked = _ranked_methods() + [
            {
                "code": "abcde",
                "name": "ABCDE",
                "group": "приоритизация",
                "role": "выбирает важное и срочное",
                "score": 9.9,
                "confidence": 0.2,
            }
        ]

        result = select_methods(ranked, {"estimated_minutes": 140, "priority": 3})
        roles = [method["role"] for method in result["selected_methods"]]
        stages = [method["plan_stage"] for method in result["selected_methods"]]

        self.assertEqual(len(roles), len(set(roles)))
        self.assertEqual(len(stages), len(set(stages)))

    def test_large_travel_task_prefers_time_method_over_start_method(self):
        ranked = _ranked_methods() + [
            {
                "code": "five_minute_rule",
                "name": "Five-Minute Rule",
                "group": "старт / борьба с прокрастинацией",
                "role": "снижает порог старта",
                "score": 8.6,
                "confidence": 0.3,
            }
        ]

        result = select_methods(
            ranked,
            {
                "title": "Спланировать отпуск",
                "description": "Выбрать даты, бюджет, жилье, маршрут и документы",
                "estimated_minutes": 180,
                "priority": 3,
                "_semantic_structure": {
                    "domain": "travel",
                    "subgoals": ["выбрать даты поездки", "определить бюджет", "подобрать жилье", "составить маршрут"],
                },
            },
        )

        execution = [method for method in result["selected_methods"] if method["plan_stage"] == "execution_time"][0]
        self.assertEqual(execution["code"], "time_blocking")
        self.assertGreater(execution["compatibility_score"], 0.8)
        self.assertNotIn("five_minute_rule", [method["code"] for method in result["selected_methods"]])


def _ranked_methods():
    return [
        {
            "code": "eisenhower",
            "name": "Eisenhower Matrix",
            "group": "приоритизация",
            "role": "выбирает важное и срочное",
            "score": 8.0,
            "confidence": 0.25,
        },
        {
            "code": "time_blocking",
            "name": "Time Blocking",
            "group": "распределение времени",
            "role": "распределяет работу по календарю",
            "score": 7.8,
            "confidence": 0.21,
        },
        {
            "code": "wbs",
            "name": "WBS",
            "group": "декомпозиция",
            "role": "разбивает работу на части",
            "score": 7.5,
            "confidence": 0.18,
        },
        {
            "code": "smart",
            "name": "SMART",
            "group": "формулировка цели",
            "role": "уточняет измеримую цель",
            "score": 7.1,
            "confidence": 0.14,
        },
        {
            "code": "checklist",
            "name": "Checklist Method",
            "group": "контроль / завершение",
            "role": "проверяет обязательные пункты",
            "score": 6.9,
            "confidence": 0.12,
        },
        {
            "code": "single_tasking",
            "name": "Single-Tasking",
            "group": "выполнение",
            "role": "удерживает фокус на одном действии",
            "score": 6.5,
            "confidence": 0.1,
        },
    ]


if __name__ == "__main__":
    unittest.main()
