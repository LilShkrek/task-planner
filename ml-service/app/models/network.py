import os

import torch
from torch import nn


DEFAULT_MODEL_PATH = "/app/artifacts/time_management_model.pt"


class TimeManagementNetwork(nn.Module):
    def __init__(self, method_count, token_feature_size=6, task_feature_size=6, hidden_size=16, dense_size=24):
        super().__init__()
        self.recurrent = nn.GRU(
            input_size=token_feature_size,
            hidden_size=hidden_size,
            batch_first=True,
        )
        self.dense = nn.Sequential(
            nn.Linear(hidden_size + task_feature_size, dense_size),
            nn.ReLU(),
            nn.Linear(dense_size, dense_size),
            nn.ReLU(),
        )
        self.method_head = nn.Linear(dense_size, method_count)
        self.planning_head = nn.Sequential(
            nn.Linear(dense_size, 4),
            nn.Sigmoid(),
        )

    def forward(self, token_features, task_features):
        _, hidden = self.recurrent(token_features)
        recurrent_state = hidden[-1]
        combined = torch.cat([recurrent_state, task_features], dim=1)
        dense_state = self.dense(combined)
        return {
            "method_scores": self.method_head(dense_state),
            "planning_params": self.planning_head(dense_state),
        }


def model_path():
    return os.getenv("MODEL_PATH", DEFAULT_MODEL_PATH)


def build_model(method_count, weights_path=None, method_codes=None):
    torch.manual_seed(42)
    model = TimeManagementNetwork(method_count=method_count)
    path = model_path() if weights_path is None else weights_path
    _load_weights_if_available(model, method_count, path, method_codes)
    model.eval()
    return model


def _load_weights_if_available(model, method_count, weights_path, method_codes):
    if not weights_path or not os.path.exists(weights_path):
        return

    checkpoint = torch.load(weights_path, map_location="cpu")
    checkpoint_method_count = checkpoint.get("method_count") if isinstance(checkpoint, dict) else None
    checkpoint_method_codes = checkpoint.get("method_codes") if isinstance(checkpoint, dict) else None
    state_dict = checkpoint.get("state_dict") if isinstance(checkpoint, dict) else checkpoint

    if checkpoint_method_count is not None and checkpoint_method_count != method_count:
        print(
            f"Файл весов {weights_path} пропущен: ожидалось методов {method_count}, "
            f"в файле {checkpoint_method_count}.",
            flush=True,
        )
        return

    if method_codes and checkpoint_method_codes and checkpoint_method_codes != method_codes:
        print(f"Файл весов {weights_path} пропущен: порядок методов в БД отличается от обученного.", flush=True)
        return

    try:
        model.load_state_dict(state_dict)
        print(f"Загружены веса модели из {weights_path}", flush=True)
    except RuntimeError as exc:
        print(f"Не удалось загрузить веса модели из {weights_path}: {exc}", flush=True)
