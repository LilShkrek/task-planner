import unittest
from unittest.mock import patch

import torch

from app.models import perceptron


class FakeModel:
    def __call__(self, token_features, task_features):
        return {
            "method_scores": torch.tensor([[0.1, 3.0, -1.0]], dtype=torch.float32),
            "planning_params": torch.tensor([[0.5, 0.25, 0.75, 0.4]], dtype=torch.float32),
        }


class PerceptronTest(unittest.TestCase):
    def test_choose_method_uses_highest_method_score(self):
        methods = [
            {"code": "eisenhower", "name": "Матрица Эйзенхауэра", "best_for": "важные задачи"},
            {"code": "pomodoro", "name": "Pomodoro", "best_for": "фокус-сессии"},
            {"code": "smart", "name": "SMART", "best_for": "уточнение цели"},
        ]
        task = {"priority": 3, "estimated_minutes": 120}
        sequence_state = {
            "tensor": torch.zeros((1, 80, 6), dtype=torch.float32),
            "token_count": 10,
        }

        with patch.object(perceptron, "_model_for", return_value=FakeModel()):
            prediction = perceptron.choose_method(task, sequence_state, methods)

        self.assertEqual(prediction["method_code"], "pomodoro")
        self.assertEqual(prediction["method_name"], "Pomodoro")
        self.assertEqual(prediction["scores"]["pomodoro"], 3.0)
        self.assertGreater(prediction["confidence"], 0.8)
        self.assertEqual(prediction["planning_params"]["focus_minutes"], 40)


if __name__ == "__main__":
    unittest.main()
