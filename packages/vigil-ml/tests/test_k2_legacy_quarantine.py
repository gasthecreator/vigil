import pytest
from vigil_ml import SequentialDetectorBenchmark, SequentialEProcessK2


@pytest.mark.parametrize(
    "legacy_type",
    [SequentialEProcessK2, SequentialDetectorBenchmark],
)
def test_legacy_k2_execution_is_quarantined(legacy_type):
    with pytest.raises(RuntimeError, match="retired"):
        legacy_type()
