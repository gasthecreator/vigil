"""Deprecated import path for the canonical K1 API.

The former nine-state neural ODE model was a distinct implementation and is
retired. Keep this module only so existing imports resolve to the single
contract implementation; do not add model logic here.
"""

from vigil_ml.k1 import HybridKineticModelK1

__all__ = ["HybridKineticModelK1"]
