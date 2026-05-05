import json
import os

import torch
from torch import nn

from app.catalog.repository import load_catalog
from app.models.network import build_model, model_path
from app.models.perceptron import _task_features
from app.models.recurrent import encode_text_sequence


DATASET_PATH = "/app/data/training_tasks.json"


def main():
    dataset_path = os.getenv("TRAINING_DATASET_PATH", DATASET_PATH)
    output_path = os.getenv("MODEL_PATH", model_path())
    epochs = int(os.getenv("TRAINING_EPOCHS", "80"))
    learning_rate = float(os.getenv("TRAINING_LR", "0.01"))

    catalog = load_catalog()
    methods = catalog["methods"]
    method_codes = [method["code"] for method in methods]
    examples = _load_examples(dataset_path, method_codes)

    model = build_model(len(method_codes), weights_path="", method_codes=method_codes)
    model.train()

    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    method_loss = nn.CrossEntropyLoss()
    planning_loss = nn.MSELoss()

    for epoch in range(epochs):
        total_loss = 0.0
        for example in examples:
            optimizer.zero_grad()
            output = model(example["token_features"], example["task_features"])
            loss = method_loss(output["method_scores"], example["method_target"])
            loss = loss + 0.1 * planning_loss(output["planning_params"], example["planning_target"])
            loss.backward()
            optimizer.step()
            total_loss += float(loss.item())

        if (epoch + 1) % 20 == 0 or epoch == 0:
            avg_loss = total_loss / len(examples)
            print(f"epoch={epoch + 1} loss={avg_loss:.4f}", flush=True)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    torch.save(
        {
            "method_count": len(method_codes),
            "method_codes": method_codes,
            "state_dict": model.state_dict(),
        },
        output_path,
    )
    print(f"Веса модели сохранены в {output_path}", flush=True)


def _load_examples(dataset_path, method_codes):
    with open(dataset_path, "r", encoding="utf-8") as file:
        raw_examples = json.load(file)

    examples = []
    for raw in raw_examples:
        target_method = raw["target_method"]
        if target_method not in method_codes:
            raise RuntimeError(f"метод {target_method} из датасета отсутствует в БД")

        task = raw["task"]
        text = " ".join(str(task.get(field, "")) for field in ("title", "description", "context"))
        sequence_state = encode_text_sequence(text)
        task_features = _task_features(task, sequence_state)

        examples.append(
            {
                "token_features": sequence_state["tensor"],
                "task_features": task_features["tensor"],
                "method_target": torch.tensor([method_codes.index(target_method)], dtype=torch.long),
                "planning_target": torch.tensor([_planning_target(raw.get("planning_params", {}))], dtype=torch.float32),
            }
        )

    if not examples:
        raise RuntimeError("учебный датасет пуст")

    return examples


def _planning_target(params):
    return [
        _scale(params.get("focus_minutes", 25), 20, 60),
        _scale(params.get("break_minutes", 5), 5, 20),
        _scale(params.get("block_count", 2), 1, 5),
        _scale(params.get("review_minutes", 15), 10, 40),
    ]


def _scale(value, minimum, maximum):
    value = max(minimum, min(maximum, float(value)))
    return (value - minimum) / (maximum - minimum)


if __name__ == "__main__":
    main()
