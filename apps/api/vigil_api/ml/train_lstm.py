"""Quarantined legacy trainer retained only for an actionable migration error.

The original prototype trained a bidirectional LSTM on circular ``is_anomaly``
targets and serialized a scaler with pickle. It is not an approved training or
artifact path.
"""


def train_lstm_model(*args: object, **kwargs: object) -> None:
    """Reject attempts to train the retired prototype."""
    raise RuntimeError(
        "The legacy anomaly trainer is quarantined: its circular synthetic "
        "targets and pickle scaler are not valid model evidence."
    )


if __name__ == "__main__":
    train_lstm_model()
