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


def _step(code, name, title, description, group, role, stage):
    return {
        "position": 1,
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
