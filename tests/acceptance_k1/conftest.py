import os
import pytest

def pytest_collection_modifyitems(config, items):
    if os.environ.get("VIGIL_ACCEPTANCE") != "1":
        skip = pytest.mark.skip(reason="set VIGIL_ACCEPTANCE=1 to run K1 acceptance tests")
        for item in items:
            item.add_marker(skip)
