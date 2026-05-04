from datetime import datetime, timezone

import torch

from app.models.network import build_model


MODELS = {}


def choose_method(task, sequence_state, methods):
    task_features = _task_features(task, sequence_state)
    method_codes = [method["code"] for method in methods]
    model = _model_for(len(method_codes))

    with torch.no_grad():
        output = model(sequence_state["tensor"], task_features["tensor"])
        method_scores = output["method_scores"][0]
        planning_vector = output["planning_params"][0]
        probabilities = torch.softmax(method_scores, dim=0)

    method_index = int(torch.argmax(probabilities).item())
    method = methods[method_index]
    scores = {
        method_codes[index]: round(float(method_scores[index].item()), 4)
        for index in range(len(method_codes))
    }

    return {
        "method_code": method["code"],
        "method_name": method["name"],
        "confidence": round(float(probabilities[method_index].item()), 3),
        "reason": _reason(method, task_features["values"]),
        "scores": scores,
        "planning_params": _planning_params(planning_vector),
        "features": task_features["values"],
    }


def _model_for(method_count):
    if method_count not in MODELS:
        MODELS[method_count] = build_model(method_count)
    return MODELS[method_count]


def _task_features(task, sequence_state):
    priority = int(task.get("priority") or 3)
    estimated = int(task.get("estimated_minutes") or 60)
    deadline_hours = _hours_to_deadline(task.get("deadline"))

    values = {
        "priority": priority / 5,
        "estimated_hours": min(estimated / 480, 1),
        "has_deadline": 1.0 if deadline_hours is not None else 0.0,
        "deadline_pressure": _deadline_pressure(deadline_hours),
        "text_complexity": min(sequence_state["token_count"] / 80, 1),
        "uncertainty": 1.0 if sequence_state["token_count"] < 6 else 0.0,
    }

    tensor = torch.tensor([list(values.values())], dtype=torch.float32)
    return {"tensor": tensor, "values": values}


def _planning_params(vector):
    return {
        "focus_minutes": int(20 + float(vector[0].item()) * 40),
        "break_minutes": int(5 + float(vector[1].item()) * 15),
        "block_count": max(1, int(1 + float(vector[2].item()) * 4)),
        "review_minutes": int(10 + float(vector[3].item()) * 30),
    }


def _hours_to_deadline(value):
    if not value:
        return None
    try:
        deadline = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    now = datetime.now(timezone.utc)
    return max((deadline.astimezone(timezone.utc) - now).total_seconds() / 3600, 0)


def _deadline_pressure(hours):
    if hours is None:
        return 0.0
    if hours <= 24:
        return 1.0
    if hours <= 72:
        return 0.7
    if hours <= 168:
        return 0.4
    return 0.1


def _reason(method, features):
    return f"модель выбрала метод из БД: {method['best_for']}"
