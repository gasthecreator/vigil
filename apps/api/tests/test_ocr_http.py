"""HTTP attack tests for the OCR confirm gate. Do not need Tesseract."""

from __future__ import annotations

import base64

from sqlalchemy import select
from sqlalchemy.orm import Session
from vigil_api.models.v2 import Observation, OcrDraft
from vigil_api.ocr import render_synthetic_report

TINY_PNG = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def _pdf_body() -> dict:
    report = render_synthetic_report(
        analyte_code="ca_15_3", value=22.0, unit="U/mL", collected_on="2026-02-01"
    )
    return {
        "filename": "report.pdf",
        "content_type": "application/pdf",
        "content_base64": base64.b64encode(report.pdf_bytes).decode("ascii"),
    }


def _png_body() -> dict:
    return {
        "filename": "report.png",
        "content_type": "image/png",
        "content_base64": TINY_PNG,
    }


def _confirm_body(**overrides) -> dict:
    body = {
        "confirmed": True,
        "analyte_code": "ca_15_3",
        "value": 22.0,
        "unit": "U/mL",
        "specimen_collected_at": "2026-02-01T00:00:00Z",
    }
    body.update(overrides)
    return body


def _obs_count(api_env, patient_id: str) -> int:
    with Session(api_env.engine) as session:
        return len(
            session.execute(select(Observation).where(Observation.patient_id == patient_id))
            .scalars()
            .all()
        )


def test_unconfirmed_draft_is_not_an_observation(api_env):
    pid = api_env.create_patient("MRN-OCR-1")
    before = _obs_count(api_env, pid)
    created = api_env.client.post(
        f"/api/v1/patients/{pid}/ocr-drafts",
        json=_pdf_body(),
        headers=api_env.headers("patient", subject=pid, patient_id=pid),
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["status"] == "pending"
    assert body["observation_id"] is None
    assert "draft" in body["notice"].lower()
    listed = api_env.client.get(
        f"/api/v1/patients/{pid}/observations",
        headers=api_env.headers("clinician"),
    )
    assert listed.status_code == 200
    assert listed.json() == []
    assert _obs_count(api_env, pid) == before


def test_confirm_without_human_fields_does_not_write(api_env):
    pid = api_env.create_patient("MRN-OCR-2")
    created = api_env.client.post(
        f"/api/v1/patients/{pid}/ocr-drafts",
        json=_pdf_body(),
        headers=api_env.headers("clinician"),
    )
    assert created.status_code == 201, created.text
    draft_id = created.json()["id"]
    missing = api_env.client.post(
        f"/api/v1/patients/{pid}/ocr-drafts/{draft_id}/confirm",
        json={"confirmed": True},
        headers=api_env.headers("clinician"),
    )
    assert missing.status_code == 422
    false_flag = api_env.client.post(
        f"/api/v1/patients/{pid}/ocr-drafts/{draft_id}/confirm",
        json=_confirm_body(confirmed=False),
        headers=api_env.headers("clinician"),
    )
    assert false_flag.status_code == 422
    assert _obs_count(api_env, pid) == 0
    with Session(api_env.engine) as session:
        row = session.get(OcrDraft, draft_id)
        assert row is not None
        assert row.status == "pending"
        assert row.observation_id is None


def test_patient_cannot_confirm_a_draft(api_env):
    pid = api_env.create_patient("MRN-OCR-3")
    created = api_env.client.post(
        f"/api/v1/patients/{pid}/ocr-drafts",
        json=_pdf_body(),
        headers=api_env.headers("patient", subject=pid, patient_id=pid),
    )
    assert created.status_code == 201, created.text
    draft_id = created.json()["id"]
    forbidden = api_env.client.post(
        f"/api/v1/patients/{pid}/ocr-drafts/{draft_id}/confirm",
        json=_confirm_body(),
        headers=api_env.headers("patient", subject=pid, patient_id=pid),
    )
    assert forbidden.status_code == 403
    ql = api_env.client.post(
        f"/api/v1/patients/{pid}/ocr-drafts/{draft_id}/confirm",
        json=_confirm_body(),
        headers=api_env.headers("quality_lead"),
    )
    assert ql.status_code == 403
    assert _obs_count(api_env, pid) == 0


def test_human_confirm_writes_posted_values_not_ocr_suggestion(api_env):
    pid = api_env.create_patient("MRN-OCR-4")
    created = api_env.client.post(
        f"/api/v1/patients/{pid}/ocr-drafts",
        json=_pdf_body(),
        headers=api_env.headers("clinician"),
    )
    assert created.status_code == 201, created.text
    draft = created.json()
    # Suggestion on this PDF is 22.0; the human posts a different reviewed value.
    confirmed = api_env.client.post(
        f"/api/v1/patients/{pid}/ocr-drafts/{draft['id']}/confirm",
        json=_confirm_body(value=41.0),
        headers=api_env.headers("clinician"),
    )
    assert confirmed.status_code == 201, confirmed.text
    body = confirmed.json()
    assert body["draft_status"] == "confirmed"
    assert body["raw_value"] == 41.0
    listed = api_env.client.get(
        f"/api/v1/patients/{pid}/observations",
        headers=api_env.headers("clinician"),
    )
    assert listed.status_code == 200
    rows = listed.json()
    assert len(rows) == 1
    raw = rows[0].get("raw_value", rows[0].get("value"))
    assert float(raw) == 41.0
    again = api_env.client.post(
        f"/api/v1/patients/{pid}/ocr-drafts/{draft['id']}/confirm",
        json=_confirm_body(value=41.0),
        headers=api_env.headers("clinician"),
    )
    assert again.status_code == 409


def test_other_patient_cannot_read_ocr_draft(api_env):
    a = api_env.create_patient("MRN-OCR-A")
    b = api_env.create_patient("MRN-OCR-B")
    created = api_env.client.post(
        f"/api/v1/patients/{a}/ocr-drafts",
        json=_png_body(),
        headers=api_env.headers("clinician"),
    )
    assert created.status_code == 201, created.text
    draft_id = created.json()["id"]
    leak = api_env.client.get(
        f"/api/v1/patients/{a}/ocr-drafts/{draft_id}",
        headers=api_env.headers("patient", subject=b, patient_id=b),
    )
    assert leak.status_code == 403
    cross = api_env.client.get(
        f"/api/v1/patients/{b}/ocr-drafts/{draft_id}",
        headers=api_env.headers("patient", subject=b, patient_id=b),
    )
    assert cross.status_code == 404


def test_reject_does_not_create_an_observation(api_env):
    pid = api_env.create_patient("MRN-OCR-5")
    created = api_env.client.post(
        f"/api/v1/patients/{pid}/ocr-drafts",
        json=_png_body(),
        headers=api_env.headers("patient", subject=pid, patient_id=pid),
    )
    assert created.status_code == 201, created.text
    draft_id = created.json()["id"]
    rejected = api_env.client.post(
        f"/api/v1/patients/{pid}/ocr-drafts/{draft_id}/reject",
        json={},
        headers=api_env.headers("patient", subject=pid, patient_id=pid),
    )
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["status"] == "rejected"
    assert _obs_count(api_env, pid) == 0
