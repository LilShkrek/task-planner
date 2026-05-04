import re

import torch


MAX_TOKENS = 80
TOKEN_FEATURE_SIZE = 6


def encode_text_sequence(text):
    tokens = re.findall(r"[A-Za-zА-Яа-яЁё0-9]+", text.lower())
    rows = [_token_features(token) for token in tokens[:MAX_TOKENS]]

    while len(rows) < MAX_TOKENS:
        rows.append([0.0] * TOKEN_FEATURE_SIZE)

    return {
        "tensor": torch.tensor([rows], dtype=torch.float32),
        "token_count": len(tokens),
        "avg_token_length": sum(len(token) for token in tokens) / max(len(tokens), 1),
    }


def _token_features(token):
    vowels = sum(1 for char in token if char in "aeiouаеёиоуыэюя")
    digits = sum(1 for char in token if char.isdigit())
    cyrillic = sum(1 for char in token if "а" <= char <= "я" or char == "ё")

    return [
        min(len(token), 20) / 20,
        vowels / max(len(token), 1),
        digits / max(len(token), 1),
        1.0 if token in {"сегодня", "завтра", "дедлайн", "deadline", "срочно"} else 0.0,
        1.0 if token in {"сделать", "подготовить", "изучить", "написать", "проверить"} else 0.0,
        cyrillic / max(len(token), 1),
    ]
