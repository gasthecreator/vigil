"""Public K1 imports must resolve to the contract and benchmark implementation."""

import vigil_ml
from vigil_ml import k1


def test_package_level_k1_is_the_canonical_contract_implementation():
    assert vigil_ml.HybridKineticModelK1 is k1.HybridKineticModelK1
