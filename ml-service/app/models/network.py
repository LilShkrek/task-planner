import torch
from torch import nn


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


def build_model(method_count):
    torch.manual_seed(42)
    model = TimeManagementNetwork(method_count=method_count)
    model.eval()
    return model
