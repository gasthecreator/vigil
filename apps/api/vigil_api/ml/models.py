"""
PyTorch Neural Network Architectures for Sentinel Longitudinal Surveillance.
Implements an Attention-Gated Bidirectional LSTM for multimodal sequential lab inference.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class TemporalAttention(nn.Module):
    """
    Self-attention layer over temporal LSTM hidden representations.
    Allows the model to focus on the exact visit/time inflection point
    where subtle anomalies began diverging.
    """

    def __init__(self, hidden_dim: int):
        super().__init__()
        self.projection = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.Tanh(),
            nn.Linear(hidden_dim // 2, 1, bias=False),
        )

    def forward(
        self, lstm_outputs: torch.Tensor, mask: torch.Tensor | None = None
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
            lstm_outputs: (batch_size, seq_len, hidden_dim)
            mask: (batch_size, seq_len) boolean mask, True for valid steps, False for padding
        Returns:
            context_vector: (batch_size, hidden_dim)
            attention_weights: (batch_size, seq_len)
        """
        scores = self.projection(lstm_outputs).squeeze(-1)  # (batch_size, seq_len)

        if mask is not None:
            scores = scores.masked_fill(~mask, -1e9)

        attention_weights = F.softmax(scores, dim=-1)  # (batch_size, seq_len)
        context = torch.bmm(attention_weights.unsqueeze(1), lstm_outputs).squeeze(
            1
        )  # (batch_size, hidden_dim)

        return context, attention_weights


class LongitudinalLSTM(nn.Module):
    """
    Bidirectional LSTM with Temporal Attention for longitudinal risk scoring.
    Inputs: Sequence of 5 standardized lab biomarkers concatenated with
            4 baseline organ susceptibility priors (total dim = 9).
    Outputs: Calculated Metastatic Recurrence Risk probability in [0.0, 1.0].
    """

    def __init__(
        self,
        input_size: int = 9,
        hidden_size: int = 32,
        num_layers: int = 2,
        dropout: float = 0.2,
    ):
        super().__init__()
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.bidirectional = True
        self.num_directions = 2

        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            bidirectional=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )

        lstm_out_dim = hidden_size * self.num_directions  # 64
        self.attention = TemporalAttention(hidden_dim=lstm_out_dim)

        # Classification head combining attention context and final LSTM hidden step
        self.classifier = nn.Sequential(
            nn.Linear(lstm_out_dim * 2, 32),
            nn.LeakyReLU(negative_slope=0.1),
            nn.Dropout(p=0.2),
            nn.Linear(32, 16),
            nn.LeakyReLU(negative_slope=0.1),
            nn.Linear(16, 1),
            nn.Sigmoid(),
        )

    def forward(
        self,
        x: torch.Tensor,
        mask: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
            x: Tensor of shape (batch_size, seq_len, input_size)
            mask: Optional Tensor of shape (batch_size, seq_len)
        Returns:
            risk: (batch_size, 1) probability in [0.0, 1.0]
            attn_weights: (batch_size, seq_len)
        """
        lstm_out, _ = self.lstm(x)  # (batch_size, seq_len, 64)

        # Compute temporal attention context
        context, attn_weights = self.attention(lstm_out, mask=mask)

        # Extract the last valid sequence timestep
        if mask is not None:
            lengths = mask.sum(dim=1).long().clamp(min=1) - 1
            batch_indices = torch.arange(x.size(0), device=x.device)
            last_step = lstm_out[batch_indices, lengths]
        else:
            last_step = lstm_out[:, -1, :]

        # Concatenate context with last step
        fused = torch.cat([context, last_step], dim=-1)  # (batch_size, 128)
        risk = self.classifier(fused)  # (batch_size, 1)

        return risk, attn_weights
