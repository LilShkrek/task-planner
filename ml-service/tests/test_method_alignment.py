import unittest

from app.planning.method_alignment import align_steps_to_methods


class MethodAlignmentTest(unittest.TestCase):
    def test_start_method_creates_start_step(self):
        steps = [
            _step(
                "five_minute_rule",
                "Five-Minute Rule",
                "Составить маршрут",
                "Продумать точки поездки по порядку.",
                "старт / борьба с прокрастинацией",
                "снижает порог старта",
                "execution_time",
            )
        ]

        aligned = align_steps_to_methods(steps, _task(), {"focus_minutes": 25, "break_minutes": 5})
        text = _step_text(aligned[0])

        self.assertIn("нач", text)
        self.assertIn("5 минут", text)
        self.assertIn("five-minute rule", text)

    def test_priority_method_creates_priority_step(self):
        steps = [
            _step(
                "abcde",
                "ABCDE",
                "Собрать материалы",
                "Собрать все источники для презентации.",
                "приоритизация",
                "ранжирует задачи по важности",
                "prioritization",
            )
        ]

        aligned = align_steps_to_methods(steps, _task())
        text = _step_text(aligned[0])

        self.assertIn("приоритет", text)
        self.assertIn("важн", text)
        self.assertIn("abcde", text)

    def test_decomposition_method_creates_structure_step(self):
        steps = [
            _step(
                "wbs",
                "WBS",
                "Подготовить слайды",
                "Сделать основную часть презентации.",
                "декомпозиция",
                "разбивает работу на части",
                "decomposition",
            )
        ]

        aligned = align_steps_to_methods(steps, _task())
        text = _step_text(aligned[0])

        self.assertIn("разб", text)
        self.assertIn("част", text)
        self.assertIn("последователь", text)

    def test_control_method_creates_review_step(self):
        steps = [
            _step(
                "action_priority_matrix",
                "Action Priority Matrix",
                "Подготовить слайды",
                "Сделать основную часть презентации.",
                "контроль / завершение",
                "сравнивает усилие и эффект",
                "review_control",
            )
        ]

        aligned = align_steps_to_methods(steps, _task())
        text = _step_text(aligned[0])

        self.assertIn("свер", text)
        self.assertIn("оцен", text)
        self.assertIn("результат", text)

    def test_travel_subgoals_are_normalized_in_step_text(self):
        steps = [
            _step(
                "time_blocking",
                "Time Blocking",
                "Даты",
                "Назначить время для этапа.",
                "распределение времени",
                "распределяет работу по календарю",
                "execution_time",
            ),
            _step(
                "checklist",
                "Checklist Method",
                "Вещи и документы",
                "Проверить этап.",
                "контроль / завершение",
                "проверяет обязательные пункты",
                "review_control",
                position=2,
            ),
        ]

        aligned = align_steps_to_methods(
            steps,
            {
                "title": "Спланировать отпуск",
                "_semantic_structure": {
                    "domain": "travel",
                    "subgoals": ["даты", "вещи и документы"],
                },
            },
            {"focus_minutes": 40, "break_minutes": 10},
        )
        text = " ".join(_step_text(step) for step in aligned)

        self.assertIn("выбор дат поездки", text)
        self.assertIn("подготовка вещей и проверка документов", text)
        self.assertNotIn("для даты", text)


def _step(code, name, title, description, group, role, stage, position=1):
    return {
        "position": position,
        "title": title,
        "description": description,
        "method_code": code,
        "method_name": name,
        "method_group": group,
        "method_role": role,
        "plan_stage": stage,
        "plan_function": "тестовая функция",
        "estimated_minutes": 20,
        "status": "pending",
    }


def _task():
    return {
        "title": "Подготовить презентацию",
        "_semantic_structure": {
            "goal": "подготовить презентацию",
            "subgoals": ["собрать материалы", "составить структуру", "подготовить слайды"],
            "domain": "presentation",
        },
    }


def _step_text(step):
    return f"{step['title']} {step['description']}".lower()


if __name__ == "__main__":
    unittest.main()
