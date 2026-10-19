"""Local lab-report extractor: photo/PDF bytes → draft suggestions. No network, no cloud.

Suggestions are hints for a human. They never become observations. Confusion-prone fields
(analyte aliases, decimals, units) are flagged so the confirm UI can highlight them.

Image OCR uses Tesseract when the binary is installed. A missing engine yields empty
suggestions with ``engine_missing`` — the draft is still created so a human can type values.
PDF text-layer extraction uses pypdf and does not need Tesseract.
"""

from __future__ import annotations

import hashlib
import io
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from vigil_core.analytes import ANALYTE_REGISTRY

MAX_UPLOAD_BYTES = 2 * 1024 * 1024
ALLOWED_CONTENT_TYPES = frozenset({"image/png", "image/jpeg", "application/pdf"})
IMAGE_TYPES = frozenset({"image/png", "image/jpeg"})

# Printed names → registry codes. Frozen for EXP-OCR-001; not a clinical synonym list.
ANALYTE_ALIASES: Dict[str, str] = {
    "ca 15-3": "ca_15_3",
    "ca15-3": "ca_15_3",
    "ca15.3": "ca_15_3",
    "ca-15-3": "ca_15_3",
    "ca 15.3": "ca_15_3",
    "cancer antigen 15-3": "ca_15_3",
    "cea": "cea",
    "carcinoembryonic antigen": "cea",
}

# Display aliases accepted on the result line (canonical units live in the registry).
UNIT_ALIASES: Dict[str, str] = {
    "u/ml": "U/mL",
    "iu/ml": "U/mL",
    "[iu]/ml": "[iU]/mL",
    "ng/ml": "ng/mL",
    "ug/l": "ug/L",
    "µg/l": "ug/L",
}

_VALUE_RE = re.compile(r"(?<![A-Za-z])(\d{1,4}(?:[.,]\d{1,3})?)(?![A-Za-z])")
_DATE_RE = re.compile(r"(20\d{2}-\d{2}-\d{2})")


@dataclass
class ConfusionFlag:
    field: str
    reason: str


@dataclass
class ParsedSuggestion:
    analyte_code: Optional[str] = None
    analyte_name: Optional[str] = None
    value: Optional[float] = None
    unit: Optional[str] = None
    specimen_collected_at: Optional[str] = None
    flags: List[ConfusionFlag] = field(default_factory=list)

    def as_dict(self) -> Dict[str, object]:
        return {
            "analyte_code": self.analyte_code,
            "analyte_name": self.analyte_name,
            "value": self.value,
            "unit": self.unit,
            "specimen_collected_at": self.specimen_collected_at,
            "flags": [{"field": f.field, "reason": f.reason} for f in self.flags],
        }


@dataclass
class ExtractResult:
    engine: str
    text: str
    suggestion: ParsedSuggestion
    source_sha256: str


@dataclass
class SyntheticReport:
    analyte_code: str
    value: float
    unit: str
    collected_on: str
    png_bytes: bytes
    pdf_bytes: bytes
    plaintext: str


def source_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def tesseract_available() -> bool:
    try:
        import pytesseract

        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def parse_lab_text(text: str) -> ParsedSuggestion:
    """Map printed English lab-report text to a single-analyte suggestion."""
    suggestion = ParsedSuggestion()
    if not text or not text.strip():
        suggestion.flags.append(ConfusionFlag("analyte_code", "no_text"))
        suggestion.flags.append(ConfusionFlag("value", "no_text"))
        suggestion.flags.append(ConfusionFlag("unit", "no_text"))
        return suggestion

    normalised = text.replace("\u00a0", " ")
    folded = re.sub(r"\s+", " ", normalised).strip()
    folded_l = folded.lower()

    date_m = _DATE_RE.search(folded)
    if date_m:
        suggestion.specimen_collected_at = date_m.group(1)

    matched_alias: Optional[str] = None
    alias_at = -1
    for alias, code in sorted(ANALYTE_ALIASES.items(), key=lambda kv: -len(kv[0])):
        at = folded_l.find(alias)
        if at >= 0:
            suggestion.analyte_code = code
            matched_alias = alias
            alias_at = at + len(alias)
            break
    if suggestion.analyte_code:
        definition = ANALYTE_REGISTRY[suggestion.analyte_code]
        suggestion.analyte_name = definition.name
        if matched_alias and matched_alias not in (
            definition.name.lower(),
            suggestion.analyte_code.replace("_", " "),
        ):
            suggestion.flags.append(
                ConfusionFlag("analyte_code", f"matched_alias:{matched_alias}")
            )
    else:
        suggestion.flags.append(ConfusionFlag("analyte_code", "unrecognised_analyte"))

    search_from = max(alias_at, 0)
    value_m = _VALUE_RE.search(folded[search_from:])
    if value_m:
        raw = value_m.group(1)
        if "," in raw:
            suggestion.flags.append(ConfusionFlag("value", "comma_decimal"))
        if re.search(r"[OIl]", raw):
            suggestion.flags.append(ConfusionFlag("value", "ocr_lookalike_digit"))
        suggestion.value = float(raw.replace(",", "."))
        rest = folded[search_from:][value_m.end() :]
        unit_token = _first_unit_token(rest, suggestion.analyte_code)
        if unit_token is None:
            suggestion.flags.append(ConfusionFlag("unit", "unit_not_found"))
        else:
            suggestion.unit = unit_token
            if unit_token.lower() in ("u/ml", "iu/ml"):
                suggestion.flags.append(ConfusionFlag("unit", "u_vs_iu_ml"))
    else:
        suggestion.flags.append(ConfusionFlag("value", "value_not_found"))
        suggestion.flags.append(ConfusionFlag("unit", "unit_not_found"))

    return suggestion


def _first_unit_token(text: str, analyte_code: Optional[str]) -> Optional[str]:
    tokens = re.findall(r"\[?[A-Za-zµ]+\]?(?:/[A-Za-z]+)?", text)
    supported: Sequence[str] = ()
    if analyte_code and analyte_code in ANALYTE_REGISTRY:
        supported = ANALYTE_REGISTRY[analyte_code].supported_units
    supported_folded = {u.lower(): u for u in supported}
    for tok in tokens:
        key = tok.lower()
        if key in UNIT_ALIASES:
            aliased = UNIT_ALIASES[key]
            if not supported or aliased.lower() in supported_folded or aliased in supported:
                return aliased if aliased in supported else supported_folded.get(
                    aliased.lower(), aliased
                )
        if key in supported_folded:
            return supported_folded[key]
    return None


def extract_from_bytes(content: bytes, content_type: str) -> ExtractResult:
    """Run the local extractor. Never calls a network service."""
    digest = source_sha256(content)
    ctype = (content_type or "").split(";")[0].strip().lower()
    if ctype == "application/pdf":
        text = _pdf_text(content)
        engine = "pdf_text"
        if not text.strip():
            engine = "pdf_no_text_layer"
        return ExtractResult(
            engine=engine, text=text, suggestion=parse_lab_text(text), source_sha256=digest
        )
    if ctype in IMAGE_TYPES:
        if not tesseract_available():
            empty = parse_lab_text("")
            empty.flags.append(ConfusionFlag("engine", "engine_missing"))
            return ExtractResult(
                engine="tesseract_missing",
                text="",
                suggestion=empty,
                source_sha256=digest,
            )
        text = _ocr_image(content)
        return ExtractResult(
            engine="tesseract", text=text, suggestion=parse_lab_text(text), source_sha256=digest
        )
    raise ValueError(f"unsupported content type: {content_type}")


def _pdf_text(content: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(content))
    parts: List[str] = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n".join(parts)


def _ocr_image(content: bytes) -> str:
    import pytesseract
    from PIL import Image

    image = Image.open(io.BytesIO(content)).convert("L")
    return pytesseract.image_to_string(image, lang="eng", config="--psm 6") or ""


def _font(size: int):
    from PIL import ImageFont

    candidates = (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
    )
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def report_plaintext(
    *,
    analyte_label: str,
    value: float,
    unit: str,
    collected_on: str,
    patient_line: str = "SYNTHETIC-NOT-A-PERSON",
) -> str:
    return (
        "Vigil Synthetic Laboratory\n"
        f"Patient: {patient_line}\n"
        f"Collected: {collected_on}\n"
        f"{analyte_label}    {value:.1f} {unit}\n"
    )


def render_png(plaintext: str) -> bytes:
    from PIL import Image, ImageDraw

    lines = plaintext.strip("\n").split("\n")
    font = _font(28)
    image = Image.new("RGB", (900, 280), "white")
    draw = ImageDraw.Draw(image)
    y = 24
    for line in lines:
        draw.text((28, y), line, fill=(0, 0, 0), font=font)
        y += 48
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def render_pdf(plaintext: str) -> bytes:
    """Minimal one-page PDF with a Courier text layer (no raster, no Tesseract)."""
    lines = plaintext.strip("\n").split("\n")
    escaped = []
    for line in lines:
        safe = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        escaped.append(safe)
    ops = ["BT", "/F1 12 Tf", "72 720 Td"]
    for i, line in enumerate(escaped):
        if i:
            ops.append("0 -16 Td")
        ops.append(f"({line}) Tj")
    ops.append("ET")
    stream = "\n".join(ops).encode("latin-1", "replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>"
        ),
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out.extend(f"{i} 0 obj\n".encode("ascii"))
        out.extend(obj)
        out.extend(b"\nendobj\n")
    xref_at = len(out)
    out.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    out.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        out.extend(f"{off:010d} 00000 n \n".encode("ascii"))
    out.extend(
        (
            f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_at}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(out)


def render_synthetic_report(
    *,
    analyte_code: str,
    value: float,
    unit: str,
    collected_on: str,
) -> SyntheticReport:
    definition = ANALYTE_REGISTRY[analyte_code]
    if analyte_code == "ca_15_3":
        label = "CA 15-3"
    elif analyte_code == "cea":
        label = "CEA"
    else:
        label = definition.name
    text = report_plaintext(
        analyte_label=label, value=value, unit=unit, collected_on=collected_on
    )
    return SyntheticReport(
        analyte_code=analyte_code,
        value=round(float(value), 1),
        unit=unit,
        collected_on=collected_on,
        png_bytes=render_png(text),
        pdf_bytes=render_pdf(text),
        plaintext=text,
    )


def jpeg_noise(png_bytes: bytes, quality: int = 40) -> bytes:
    from PIL import Image

    image = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def rotate_noise(png_bytes: bytes, degrees: float = 2.0) -> bytes:
    from PIL import Image

    image = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    rotated = image.rotate(degrees, expand=True, fillcolor="white")
    buf = io.BytesIO()
    rotated.save(buf, format="PNG")
    return buf.getvalue()


def speckle_noise(png_bytes: bytes, fraction: float = 0.005, seed: int = 0) -> bytes:
    import numpy as np
    from PIL import Image

    image = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    arr = np.array(image)
    rng = np.random.default_rng(seed)
    mask = rng.random(arr.shape[:2]) < fraction
    salt = rng.random(arr.shape[:2]) < 0.5
    arr[mask & salt] = 255
    arr[mask & ~salt] = 0
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG")
    return buf.getvalue()


def canonical_triple(
    analyte_code: str, value: float, unit: str
) -> Tuple[str, float, str]:
    definition = ANALYTE_REGISTRY[analyte_code]
    unit_folded = unit
    if unit.lower() in UNIT_ALIASES:
        unit_folded = UNIT_ALIASES[unit.lower()]
    supported = {u.lower(): u for u in definition.supported_units}
    canonical_unit = supported.get(unit_folded.lower(), unit_folded)
    return analyte_code, round(float(value), 1), canonical_unit


def suggestion_triple(suggestion: ParsedSuggestion) -> Optional[Tuple[str, float, str]]:
    if suggestion.analyte_code is None or suggestion.value is None or suggestion.unit is None:
        return None
    return canonical_triple(suggestion.analyte_code, suggestion.value, suggestion.unit)


def iso_collected(d: date) -> str:
    return d.isoformat()
