#!/usr/bin/env python3
"""Generate Awesome-CV LaTeX fragments from a public ORCID record."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


API_BASE = "https://pub.orcid.org/v3.0"
TOKEN_URL = "https://orcid.org/oauth/token"
ORCID_RE = re.compile(r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$")

SECTIONS = {
    "employments": ("employment-summary", "Esperienza professionale"),
    "educations": ("education-summary", "Formazione"),
    "qualifications": ("qualification-summary", "Qualifiche"),
    "invited-positions": ("invited-position-summary", "Posizioni su invito"),
    "distinctions": ("distinction-summary", "Premi e riconoscimenti"),
    "memberships": ("membership-summary", "Associazioni scientifiche"),
    "services": ("service-summary", "Servizio scientifico"),
}

DEFAULT_EDITORIAL_KEYWORDS = (
    "editor", "editorial", "journal", "review editor", "redatt", "rivista"
)


def request_json(url: str, *, token: str | None = None,
                 data: dict[str, str] | None = None) -> dict[str, Any]:
    body = urllib.parse.urlencode(data).encode() if data else None
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=body, headers=headers,
                                 method="POST" if body else "GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        raise RuntimeError(f"ORCID API: HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Impossibile contattare ORCID: {exc.reason}") from exc


def get_token(client_id: str, client_secret: str) -> str:
    payload = request_json(TOKEN_URL, data={
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials",
        "scope": "/read-public",
    })
    token = payload.get("access_token")
    if not token:
        raise RuntimeError("ORCID non ha restituito un access token")
    return str(token)


def fetch_record(orcid: str, token: str) -> dict[str, Any]:
    if not ORCID_RE.fullmatch(orcid):
        raise ValueError("ORCID iD non valido; formato atteso 0000-0000-0000-0000")
    return request_json(f"{API_BASE}/{orcid}/record", token=token)


def value(node: Any) -> str:
    """Read ORCID's common {value: ...} wrapper without failing on nulls."""
    if node is None:
        return ""
    if isinstance(node, dict):
        return value(node.get("value"))
    return str(node)


def latex(text: Any) -> str:
    s = value(text)
    replacements = {
        "\\": r"\textbackslash{}", "&": r"\&", "%": r"\%",
        "$": r"\$", "#": r"\#", "_": r"\_", "{": r"\{",
        "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in s).strip()


def date_part(date: Any) -> str:
    if not isinstance(date, dict):
        return ""
    parts = [value(date.get(key)) for key in ("year", "month", "day")]
    parts = [p for p in parts if p]
    return "-".join(parts)


def date_range(item: dict[str, Any]) -> str:
    start = date_part(item.get("start-date"))
    end = date_part(item.get("end-date"))
    if start and end:
        return f"{start} -- {end}"
    if start:
        return f"{start} -- oggi"
    return end


def location(org: dict[str, Any]) -> str:
    address = org.get("address") or {}
    return ", ".join(filter(None, (value(address.get("city")),
                                    value(address.get("region")),
                                    value(address.get("country")))))


def affiliation_entries(container: Any, summary_key: str) -> list[dict[str, Any]]:
    if not isinstance(container, dict):
        return []
    result: list[dict[str, Any]] = []
    for group in container.get("affiliation-group") or []:
        # Equivalent assertions can occur in one group; prefer the first summary.
        summaries = group.get("summaries") or []
        if summaries and isinstance(summaries[0], dict):
            item = summaries[0].get(summary_key)
            if isinstance(item, dict):
                result.append(item)
    return result


def sort_key(item: dict[str, Any]) -> tuple[str, str]:
    end = date_part(item.get("end-date")) or "9999"
    start = date_part(item.get("start-date"))
    return end, start


def render_entry(item: dict[str, Any]) -> str:
    org = item.get("organization") or {}
    role = value(item.get("role-title")) or value(item.get("department-name")) or "Attività"
    department = value(item.get("department-name"))
    detail = department if department and department != role else ""
    url = value(item.get("url"))
    notes = [latex(x) for x in (detail, url) if x]
    description = r"\begin{cvitems}\item " + r" \enspace{} ".join(notes) + r"\end{cvitems}" if notes else ""
    return (
        "\\cventry\n"
        f"  {{{latex(date_range(item))}}}\n"
        f"  {{{latex(role)}}}\n"
        f"  {{{latex(org.get('name'))}}}\n"
        f"  {{{latex(location(org))}}}\n"
        "  {}\n"
        f"  {{{description}}}\n"
    )


def write_section(path: Path, title: str, items: list[dict[str, Any]]) -> None:
    lines = [f"% Generato automaticamente: non modificare.\n\\cvsection{{{latex(title)}}}\n"]
    if items:
        lines.append("\\begin{cventries}\n")
        lines.extend(render_entry(x) for x in sorted(items, key=sort_key, reverse=True))
        lines.append("\\end{cventries}\n")
    else:
        lines.append("% Nessuna voce pubblica presente su ORCID.\n")
    path.write_text("\n".join(lines), encoding="utf-8")


def is_editorial(item: dict[str, Any], keywords: tuple[str, ...]) -> bool:
    org = item.get("organization") or {}
    haystack = " ".join((value(item.get("role-title")),
                          value(item.get("department-name")),
                          value(org.get("name")))).casefold()
    return any(keyword.casefold() in haystack for keyword in keywords)


def person_name(record: dict[str, Any]) -> tuple[str, str]:
    name = (((record.get("person") or {}).get("name")) or {})
    return value(name.get("given-names")), value(name.get("family-name"))


def generate(record: dict[str, Any], out: Path,
             editorial_keywords: tuple[str, ...]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    activities = record.get("activities-summary") or {}
    manifest: list[str] = []

    for section, (summary_key, title) in SECTIONS.items():
        items = affiliation_entries(activities.get(section), summary_key)
        if section == "services":
            editorial = [x for x in items if is_editorial(x, editorial_keywords)]
            items = [x for x in items if not is_editorial(x, editorial_keywords)]
            write_section(out / "editorial-services.tex", "Servizio editoriale", editorial)
            manifest.append("editorial-services.tex")
        filename = f"{section}.tex"
        write_section(out / filename, title, items)
        manifest.append(filename)

    given, family = person_name(record)
    metadata = {
        "given_name": given,
        "family_name": family,
        "generated_files": manifest,
    }
    (out / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--orcid", help="ORCID iD da scaricare")
    source.add_argument("--record-json", type=Path, help="record ORCID già scaricato")
    parser.add_argument("--out", type=Path, default=Path("generated"))
    parser.add_argument("--save-json", type=Path,
                        help="salva una copia del record scaricato")
    parser.add_argument("--editorial-keyword", action="append", default=[],
                        help="keyword aggiuntiva per classificare il servizio editoriale")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.record_json:
            record = json.loads(args.record_json.read_text(encoding="utf-8"))
        else:
            client_id = os.environ.get("ORCID_CLIENT_ID")
            client_secret = os.environ.get("ORCID_CLIENT_SECRET")
            if not client_id or not client_secret:
                raise RuntimeError("Impostare ORCID_CLIENT_ID e ORCID_CLIENT_SECRET")
            record = fetch_record(args.orcid, get_token(client_id, client_secret))
            if args.save_json:
                args.save_json.write_text(
                    json.dumps(record, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
        keywords = DEFAULT_EDITORIAL_KEYWORDS + tuple(args.editorial_keyword)
        generate(record, args.out, keywords)
        print(f"Sezioni LaTeX generate in {args.out}")
        return 0
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"Errore: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
