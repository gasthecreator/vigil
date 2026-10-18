"""M4 resource-aware test ladder (docs/ml/M4-CONTRACT.md).

Stateless: nothing is read from or written to the clinical database and no patient is named. The route is a
clinician decision aid. It is clinician/admin only, and it is refused in silent mode because its response is a
model output (``vigil_api.silent_mode``). The engine is pure; the only clock read is here, to default ``as_of``.
"""

from __future__ import annotations

from datetime import date
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from vigil_api import silent_mode
from vigil_api.auth import require_roles
from vigil_api.models.v2 import User, UserRole
from vigil_api.schemas.v2 import TestLadderFacility, TestLadderRequest, TestLadderResponse
from vigil_ml import m4_ladder

router = APIRouter()

_EVIDENCE = m4_ladder.load_evidence()
_TEMPLATES = m4_ladder.load_facility_templates()


def _inline_facility(f: TestLadderFacility) -> m4_ladder.FacilityCapability:
    return m4_ladder.facility_from_dict(
        {
            "facility_id": f.facility_id,
            "name": f.name,
            "tier": f.tier,
            "illustrative": False,
            "modalities": [m.model_dump(mode="json") for m in f.modalities],
        }
    )


@router.get("/facilities", response_model=List[Dict[str, object]])
def list_registry_facilities(
    current_user: User = Depends(require_roles(UserRole.CLINICIAN, UserRole.ADMIN)),
):
    """Registry facilities. Only illustrative tier templates ship; none is a real facility."""
    return [
        {
            "facility_id": f.facility_id,
            "name": f.name,
            "tier": f.tier,
            "illustrative": f.illustrative,
            "modalities": sorted(m.modality for m in f.modalities),
        }
        for f in _TEMPLATES.values()
    ]


@router.post("/recommend", response_model=TestLadderResponse)
def recommend_test_ladder(
    payload: TestLadderRequest,
    current_user: User = Depends(require_roles(UserRole.CLINICIAN, UserRole.ADMIN)),
):
    """Which tests are worth doing at this facility, in what order, and what remains unknown after each.

    Decision support only: a negative result never excludes involvement (the remaining probability is
    returned as an interval), tests without an accuracy source are never ranked, and no numeric weight
    trades cost against information.
    """
    silent_mode.block_in_silent_mode("The test-escalation ladder")

    if (payload.facility_id is None) == (payload.facility is None):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide exactly one of facility_id or facility.",
        )
    if payload.facility_id is not None:
        facility = _TEMPLATES.get(payload.facility_id)
        if facility is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Unknown registry facility_id."
            )
    else:
        assert payload.facility is not None
        facility = _inline_facility(payload.facility)

    today = date.today()
    as_of = payload.as_of or today
    if as_of > today:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="as_of cannot be in the future.",
        )

    p = payload.prior
    lo = p.value if p.lo is None else p.lo
    hi = p.value if p.hi is None else p.hi
    try:
        prior = m4_ladder.Prior(value=p.value, lo=lo, hi=hi, provenance=p.provenance)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    result = m4_ladder.recommend(
        payload.organ,
        prior,
        facility,
        as_of,
        evidence=_EVIDENCE,
        other_facilities=list(_TEMPLATES.values()),
        max_price_band=payload.max_price_band,
    )
    return result.to_dict()
