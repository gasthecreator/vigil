#!/usr/bin/env python3
"""Independent audit of saved evidence excerpts (network required; run via `make audit-evidence`).

For every file in docs/evidence/excerpts/*.md:
  * every number inside a blockquote ('>' lines) or a fenced code block must appear in retrieved source text:
      - PubMed abstract (by PMID), and Europe PMC open-access full text when the paper is OA;
      - for non-PubMed sources, the page behind the **URL:** line (HTML stripped).
  * a claimed licence of "Open Access" must be true according to Europe PMC.
  * a cited PMC URL must match Europe PMC's PMCID for the PMID.
Exit 1 on any violation. Quoting a number you could not retrieve is a violation; mark it UNVERIFIED outside a quote instead.
"""

from __future__ import annotations

import json
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
NUM = re.compile(r"(?<![\w.])\d+(?:[.,]\d+)*(?![\w])")


def _get(url: str, retries: int = 3) -> str:
    for attempt in range(retries):
        try:
            time.sleep(1.0)
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=40) as resp:
                return resp.read().decode("utf8", "ignore")
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2.0 * (attempt + 1))
    return ""


def _strip(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def europepmc(pmid: str) -> dict:
    d = json.loads(
        _get(
            f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=EXT_ID:{pmid}%20AND%20SRC:MED&format=json&resultType=core"
        )
    )
    return d["resultList"]["result"][0]


def abstract(pmid: str) -> str:
    root = ET.fromstring(
        _get(
            f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={pmid}&retmode=xml"
        )
    )
    return " ".join("".join(x.itertext()) for x in root.iter("AbstractText"))


def quoted_text(md: str) -> str:
    out, fence = [], False
    for line in md.splitlines():
        if line.strip().startswith("```"):
            fence = not fence
            continue
        if fence or line.lstrip().startswith(">"):
            out.append(line.lstrip("> "))
    return "\n".join(out)


def audit(path: Path) -> list[str]:
    md = path.read_text(encoding="utf-8")
    v: list[str] = []
    pmid = re.search(r"PMID:\*{0,2}\s*\[?(\d{6,9})", md) or re.search(
        r"PMID[^0-9]{0,6}(\d{6,9})", md
    )
    url = re.search(r"\*\*URL:\*\*\s*(\S+)", md)
    sources: list[str] = []
    if pmid:
        pm = pmid.group(1)
        meta = europepmc(pm)
        sources.append(abstract(pm))
        if meta.get("isOpenAccess") == "Y" and meta.get("pmcid"):
            sources.append(
                _strip(
                    _get(
                        f"https://www.ebi.ac.uk/europepmc/webservices/rest/{meta['pmcid']}/fullTextXML"
                    )
                )
            )
        else:
            if re.search(r"open access|cc-by", md, re.I):
                v.append(
                    f"claims open access/licence but Europe PMC says isOpenAccess={meta.get('isOpenAccess')}"
                )
        cited = re.search(r"PMC\d+", url.group(1) if url else "")
        if cited and meta.get("pmcid") and cited.group(0) != meta["pmcid"]:
            v.append(
                f"cited {cited.group(0)} but Europe PMC PMCID for PMID {pm} is {meta['pmcid']}"
            )
    if url and "ncbi.nlm.nih.gov" not in url.group(1):
        try:
            sources.append(_strip(_get(url.group(1))))
        except Exception as e:  # noqa: BLE001
            v.append(f"cannot retrieve {url.group(1)}: {e}")
    haystack = " ".join(sources).replace("\u00b7", ".").replace(",", "")
    for n in sorted(set(NUM.findall(quoted_text(md)))):
        if n.replace(",", "") not in haystack:
            v.append(f"number {n} appears in a quote/code block but not in retrievable source text")
    return v


def main() -> int:
    bad = 0
    for p in sorted((ROOT / "docs" / "evidence" / "excerpts").glob("*.md")):
        res = audit(p)
        print(("FAIL " if res else "ok   ") + p.name)
        for r in res:
            print("     -", r)
        bad += bool(res)
    print(f"{bad} excerpt file(s) failed")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
