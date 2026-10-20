"""Quarantined legacy trainer retained only for an actionable migration error.

The original prototype trained on synthetic oracle targets and serialized the
result with pickle. It is not an approved model-training or artifact path.
"""


def train_baseline_model(*args: object, **kwargs: object) -> None:
    """Reject attempts to train the retired prototype."""
    raise RuntimeError(
        "The legacy organ-susceptibility trainer is quarantined: its synthetic "
        "oracle targets and pickle artifact are not valid model evidence."
    )


if __name__ == "__main__":
    train_baseline_model()
