#!/usr/bin/env python3
"""Offline consistency checks for the frozen scholarly bibliography.

This verifier does not query the network.  It checks that the bibliography, the
manuscript citation inventory, the independently frozen audit table, and the
artifact literature table agree exactly.  External metadata provenance is
recorded in docs/bibliography-audit.csv and can be re-opened by a human reviewer.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Dict, Iterable, Mapping

DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$", re.IGNORECASE)
CITE_RE = re.compile(r"\\(?:cite|citep|citet|citealp|citealt|citeauthor|citeyear|nocite)\s*(?:\[[^\]]*\]\s*){0,2}\{([^}]*)\}")


def _balanced_entries(text: str) -> Iterable[tuple[str, str, str]]:
    """Yield (entry_type, key, body) while respecting nested braces."""
    i = 0
    n = len(text)
    while i < n:
        at = text.find("@", i)
        if at < 0:
            return
        m = re.match(r"@([A-Za-z]+)\s*\{", text[at:])
        if not m:
            i = at + 1
            continue
        entry_type = m.group(1).lower()
        open_pos = at + m.end() - 1
        depth = 0
        quote = False
        escape = False
        end = None
        for j in range(open_pos, n):
            ch = text[j]
            if escape:
                escape = False
                continue
            if ch == "\\":
                escape = True
                continue
            if ch == '"':
                quote = not quote
                continue
            if quote:
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = j
                    break
        if end is None:
            raise ValueError(f"unterminated BibTeX entry starting at byte {at}")
        payload = text[open_pos + 1 : end]
        comma = payload.find(",")
        if comma < 0:
            raise ValueError(f"BibTeX entry without key/body separator at byte {at}")
        key = payload[:comma].strip()
        body = payload[comma + 1 :]
        if entry_type not in {"comment", "preamble", "string"}:
            yield entry_type, key, body
        i = end + 1


def _split_fields(body: str) -> Iterable[str]:
    start = 0
    brace = 0
    quote = False
    escape = False
    for i, ch in enumerate(body):
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"' and brace == 0:
            quote = not quote
            continue
        if quote:
            continue
        if ch == "{":
            brace += 1
        elif ch == "}":
            brace -= 1
            if brace < 0:
                raise ValueError("unbalanced BibTeX field braces")
        elif ch == "," and brace == 0:
            chunk = body[start:i].strip()
            if chunk:
                yield chunk
            start = i + 1
    chunk = body[start:].strip()
    if chunk:
        yield chunk
    if brace != 0 or quote:
        raise ValueError("unterminated BibTeX field value")


def _unwrap(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and ((value[0] == "{" and value[-1] == "}") or (value[0] == '"' and value[-1] == '"')):
        return value[1:-1].strip()
    return value


def parse_bib(path: Path) -> Dict[str, Dict[str, str]]:
    text = path.read_text(encoding="utf-8")
    entries: Dict[str, Dict[str, str]] = {}
    for entry_type, key, body in _balanced_entries(text):
        if not key or key in entries:
            raise ValueError(f"duplicate or empty BibTeX key: {key!r}")
        fields: Dict[str, str] = {"entry_type": entry_type}
        for chunk in _split_fields(body):
            if "=" not in chunk:
                raise ValueError(f"malformed field in {key}: {chunk!r}")
            name, raw = chunk.split("=", 1)
            name = name.strip().lower()
            if not name or name in fields:
                raise ValueError(f"duplicate or empty field {name!r} in {key}")
            fields[name] = _unwrap(raw)
        entries[key] = fields
    return entries


def _plain(value: str) -> str:
    # Normalize only presentation syntax that differs between BibTeX and CSV.
    value = value.replace("--", "-")
    value = re.sub(r"[{}]", "", value)
    value = re.sub(r"\\['\"`^~=.]\s*([A-Za-z])", r"\1", value)
    value = value.replace(r"\o", "o").replace(r"\v", "")
    value = re.sub(r"\\[A-Za-z]+", "", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value.casefold()


def _venue(fields: Mapping[str, str]) -> str:
    return fields.get("journal") or fields.get("booktitle") or fields.get("organization", "")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def citation_keys(tex_path: Path) -> set[str]:
    text = tex_path.read_text(encoding="utf-8")
    text = re.sub(r"(?m)(?<!\\)%.*$", "", text)
    keys: set[str] = set()
    for match in CITE_RE.finditer(text):
        for key in match.group(1).split(","):
            key = key.strip()
            if key and key != "*":
                keys.add(key)
    return keys


def verify(
    bib_path: Path,
    audit_path: Path,
    literature_path: Path,
    tex_path: Path | None = None,
    canonical_path: Path | None = None,
    minimum: int = 55,
) -> dict[str, int | str]:
    entries = parse_bib(bib_path)
    if len(entries) < minimum:
        raise ValueError(f"bibliography has {len(entries)} entries; minimum is {minimum}")

    dois: dict[str, str] = {}
    for key, fields in entries.items():
        for required in ("author", "title", "year"):
            if not fields.get(required, "").strip():
                raise ValueError(f"{key} is missing required field {required}")
        if not _venue(fields):
            raise ValueError(f"{key} has no journal, booktitle, or issuing organization")
        doi = fields.get("doi", "").strip().lower()
        if doi:
            if not DOI_RE.fullmatch(doi):
                raise ValueError(f"invalid DOI syntax for {key}: {doi}")
            if doi in dois:
                raise ValueError(f"duplicate DOI {doi}: {dois[doi]} and {key}")
            dois[doi] = key

    audit = read_csv(audit_path)
    audit_by_key = {row.get("key", ""): row for row in audit}
    if len(audit_by_key) != len(audit):
        raise ValueError("duplicate key in bibliography audit")
    if set(audit_by_key) != set(entries):
        missing = sorted(set(entries) - set(audit_by_key))
        extra = sorted(set(audit_by_key) - set(entries))
        raise ValueError(f"audit inventory mismatch: missing={missing}, extra={extra}")
    required_audit = {
        "key", "category", "title", "year", "venue", "doi", "identifier_url",
        "verification_source", "verification_status", "checked_on", "notes",
    }
    if audit and set(audit[0]) != required_audit:
        raise ValueError(f"audit columns differ: {sorted(set(audit[0]) ^ required_audit)}")
    for key, fields in entries.items():
        row = audit_by_key[key]
        comparisons = {
            "title": fields["title"],
            "year": fields["year"],
            "venue": _venue(fields),
            "doi": fields.get("doi", ""),
        }
        for column, bib_value in comparisons.items():
            if _plain(row[column]) != _plain(bib_value):
                raise ValueError(f"audit mismatch for {key}.{column}: {row[column]!r} != {bib_value!r}")
        doi = fields.get("doi", "").strip().lower()
        if doi and row["identifier_url"].strip().lower() != "https://doi.org/" + doi:
            raise ValueError(f"audit DOI URL mismatch for {key}")
        if row["verification_status"] not in {"matched_title_year_venue_doi", "matched_title_year_venue"}:
            raise ValueError(f"unrecognized verification status for {key}")
        if not row["verification_source"].strip() or not row["checked_on"].strip():
            raise ValueError(f"incomplete audit provenance for {key}")

    literature = read_csv(literature_path)
    literature_by_key = {row.get("key", ""): row for row in literature}
    if len(literature_by_key) != len(literature):
        raise ValueError("duplicate key in literature table")
    if set(literature_by_key) != set(entries):
        missing = sorted(set(entries) - set(literature_by_key))
        extra = sorted(set(literature_by_key) - set(entries))
        raise ValueError(f"literature inventory mismatch: missing={missing}, extra={extra}")
    for key, fields in entries.items():
        row = literature_by_key[key]
        for column, bib_value in {
            "title": fields["title"], "year": fields["year"],
            "venue": _venue(fields), "doi": fields.get("doi", ""),
        }.items():
            if _plain(row[column]) != _plain(bib_value):
                raise ValueError(f"literature mismatch for {key}.{column}")
        if row.get("included_and_cited", "").strip().lower() != "yes":
            raise ValueError(f"literature entry not marked included/cited: {key}")

    if tex_path is not None:
        cited = citation_keys(tex_path)
        if cited != set(entries):
            missing = sorted(set(entries) - cited)
            unknown = sorted(cited - set(entries))
            raise ValueError(f"citation inventory mismatch: uncited={missing}, unknown={unknown}")
    else:
        cited = set(entries)

    if canonical_path is not None:
        if bib_path.read_bytes() != canonical_path.read_bytes():
            raise ValueError("paper bibliography differs from standalone canonical copy")

    return {
        "status": "matched",
        "entries": len(entries),
        "cited_keys": len(cited),
        "unique_dois": len(dois),
        "no_doi_records": len(entries) - len(dois),
        "audit_rows": len(audit),
        "minimum_required": minimum,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bib", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--literature", type=Path, required=True)
    parser.add_argument("--tex", type=Path)
    parser.add_argument("--canonical", type=Path)
    parser.add_argument("--minimum", type=int, default=55)
    args = parser.parse_args()
    print(json.dumps(verify(args.bib, args.audit, args.literature, args.tex, args.canonical, args.minimum), sort_keys=True))


if __name__ == "__main__":
    main()
