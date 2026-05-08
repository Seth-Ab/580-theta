#!/usr/bin/env python3

"""Build the v0 canonical entity table for Team Theta.

Input:
    A CSV file with at least a `ticker` column.

Output:
    A canonical entity CSV with one row per input ticker and an optional
    Markdown specification describing the schema and construction rules.
"""

from __future__ import annotations

import argparse
import csv
import re
from collections import Counter
from pathlib import Path


AS_OF_DATE = "2026-05-08"
SOURCE_NAME = "GSE580_theta_data.csv"

OUTPUT_FIELDS = [
    "entity_id",
    "ticker",
    "company_name",
    "canonical_name",
    "parent_entity_id",
    "is_public",
    "country",
    "region",
    "source",
    "as_of_date",
    "confidence_score",
    "notes",
]

LEGAL_SUFFIX_PATTERN = re.compile(
    r"""
    (?:,\s*)?
    (?:
        inc\.?|
        corp\.?|
        corporation|
        ltd\.?|
        plc|
        llc|
        co\.?|
        company
    )
    \s*$
    """,
    re.IGNORECASE | re.VERBOSE,
)

COUNTRY_REGION = {
    "United States": "North America",
    "US": "North America",
    "Canada": "North America",
    "Mexico": "North America",
    "United Kingdom": "Europe",
    "Germany": "Europe",
    "France": "Europe",
    "Italy": "Europe",
    "Spain": "Europe",
    "Netherlands": "Europe",
    "Switzerland": "Europe",
    "Ireland": "Europe",
    "Norway": "Europe",
    "Sweden": "Europe",
    "Denmark": "Europe",
    "Japan": "Asia-Pacific",
    "China": "Asia-Pacific",
    "Taiwan": "Asia-Pacific",
    "South Korea": "Asia-Pacific",
    "India": "Asia-Pacific",
    "Australia": "Asia-Pacific",
    "Brazil": "Latin America",
}

COUNTRY_ALIASES = {
    "u.s.": "United States",
    "us": "United States",
    "usa": "United States",
    "united states": "United States",
    "united states of america": "United States",
    "canada": "Canada",
    "mexico": "Mexico",
    "united kingdom": "United Kingdom",
    "uk": "United Kingdom",
    "germany": "Germany",
    "france": "France",
    "italy": "Italy",
    "spain": "Spain",
    "netherlands": "Netherlands",
    "switzerland": "Switzerland",
    "ireland": "Ireland",
    "norway": "Norway",
    "sweden": "Sweden",
    "denmark": "Denmark",
    "japan": "Japan",
    "china": "China",
    "taiwan": "Taiwan",
    "south korea": "South Korea",
    "korea": "South Korea",
    "india": "India",
    "australia": "Australia",
    "brazil": "Brazil",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build outputs/entities_v0.csv from a company universe CSV."
    )
    parser.add_argument("input_csv", type=Path, help="Path to GSE580_theta_data.csv.")
    parser.add_argument("output_csv", type=Path, help="Path to entities_v0.csv.")
    parser.add_argument(
        "--spec",
        type=Path,
        default=None,
        help="Optional path for docs/entity_table_spec.md.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing output/spec files.",
    )
    return parser.parse_args()


def normalize_text(value: str | None) -> str:
    return " ".join((value or "").replace("\n", " ").replace("\r", " ").split()).strip()


def clean_ticker(value: str | None) -> str:
    return normalize_text(value).upper()


def clean_canonical_name(company_name: str) -> str:
    name = normalize_text(company_name)
    previous = None
    while previous != name:
        previous = name
        name = LEGAL_SUFFIX_PATTERN.sub("", name).strip(" ,")
    return name


def infer_country(row: dict[str, str]) -> str:
    country_fields = [
        "country",
        "domicile_country",
        "headquarters_country",
        "hq_country",
        "incorporation_country",
    ]
    for field in country_fields:
        value = normalize_text(row.get(field))
        if value:
            return COUNTRY_ALIASES.get(value.lower(), value)

    text = " ".join(
        normalize_text(row.get(field))
        for field in ["ci_geographic_scope", "ci_foreign_exposure_desc"]
    )
    lowered = text.lower()
    if not lowered:
        return "Unknown"

    explicit_patterns = [
        (r"\bheadquartered in the (?:u\.s\.|us|usa|united states)\b", "United States"),
        (r"\bheadquartered in canada\b", "Canada"),
        (r"\bheadquartered in mexico\b", "Mexico"),
        (r"\bbased in the (?:u\.s\.|us|usa|united states)\b", "United States"),
        (r"\bbased in canada\b", "Canada"),
        (r"\bbased in mexico\b", "Mexico"),
        (r"\bu\.s\.-focused\b", "United States"),
        (r"\bus-focused\b", "United States"),
        (r"\bprimarily (?:u\.s\.|us|united states)\b", "United States"),
        (r"\bdomestic u\.s\.\b", "United States"),
        (r"\bdomestic us\b", "United States"),
    ]
    for pattern, country in explicit_patterns:
        if re.search(pattern, lowered):
            return country

    scope = normalize_text(row.get("ci_geographic_scope")).lower()
    if scope in {"domestic", "u.s.", "us", "usa", "united states", "north america"}:
        return "United States"

    return "Unknown"


def region_for_country(country: str) -> str:
    if country == "Unknown":
        return "Unknown"
    return COUNTRY_REGION.get(country, "Other/Unknown")


def build_note(parts: list[str]) -> str:
    return "; ".join(part for part in parts if part)


def build_entities(rows: list[dict[str, str]], fieldnames: list[str]) -> tuple[list[dict[str, str]], list[str]]:
    if "ticker" not in fieldnames:
        raise ValueError("Input CSV must include a `ticker` column.")

    has_company_name = "company_name" in fieldnames
    sorted_rows = sorted(rows, key=lambda row: clean_ticker(row.get("ticker")))
    ticker_counts = Counter(clean_ticker(row.get("ticker")) for row in sorted_rows)
    duplicate_tickers = sorted(ticker for ticker, count in ticker_counts.items() if ticker and count > 1)

    output_rows: list[dict[str, str]] = []
    for index, row in enumerate(sorted_rows, start=1):
        ticker = clean_ticker(row.get("ticker"))
        notes: list[str] = ["parent relationships not resolved in v0"]

        company_name = normalize_text(row.get("company_name")) if has_company_name else ""
        if not company_name:
            company_name = ticker
            notes.append("company_name missing; used ticker fallback")

        if ticker_counts[ticker] > 1:
            notes.append("duplicate ticker")

        country = infer_country(row)
        if country == "Unknown":
            notes.append("country unknown")

        confidence = "0.95"
        if not has_company_name or normalize_text(row.get("company_name")) == "":
            confidence = "0.80"
        if ticker_counts[ticker] > 1:
            confidence = "0.60"

        output_rows.append(
            {
                "entity_id": f"ENT{index:06d}",
                "ticker": ticker,
                "company_name": company_name,
                "canonical_name": clean_canonical_name(company_name),
                "parent_entity_id": "",
                "is_public": "TRUE",
                "country": country,
                "region": region_for_country(country),
                "source": SOURCE_NAME,
                "as_of_date": AS_OF_DATE,
                "confidence_score": confidence,
                "notes": build_note(notes),
            }
        )

    return output_rows, duplicate_tickers


def write_csv(path: Path, rows: list[dict[str, str]], overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"{path} already exists. Pass --overwrite to replace it.")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def write_spec(path: Path, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"{path} already exists. Pass --overwrite to replace it.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """# Entity Table Spec v0

## Purpose

`outputs/entities_v0.csv` is the canonical company backbone for the Team Theta market-definition workflow. It gives each input ticker one stable internal `entity_id` so later outputs can join to a shared company identity layer instead of relying only on raw ticker strings.

## Column Definitions

- `entity_id`: Stable internal identifier for the entity.
- `ticker`: Cleaned public-company ticker, uppercased and stripped of surrounding spaces.
- `company_name`: Company name from the source when available; otherwise the ticker fallback.
- `canonical_name`: Readable cleaned name used for matching and review.
- `parent_entity_id`: Reserved for future parent/subsidiary mapping. Blank in v0.
- `is_public`: `TRUE` for all v0 rows because the source universe is public listed companies.
- `country`: Country from a usable source field or conservative inference; otherwise `Unknown`.
- `region`: Broad region derived from country.
- `source`: Source file used to build the row.
- `as_of_date`: Snapshot date for this v0 output.
- `confidence_score`: Simple quality score for the identity row.
- `notes`: Concise flags for missing names, duplicates, unknown countries, and unresolved parents.

## Cleaning Rules

Tickers are stripped of surrounding whitespace and uppercased. Company names are stripped and repeated spaces are collapsed. `canonical_name` removes common legal suffixes only when they appear at the end of the name, including `Inc`, `Inc.`, `Corp`, `Corporation`, `Ltd`, `PLC`, `LLC`, `Co`, and `Company`.

The v0 cleaner intentionally does not over-clean names. It keeps names readable and avoids removing business descriptors that may matter for analyst review.

## entity_id Rule

Rows are sorted by cleaned ticker. IDs are assigned sequentially in that sorted order using the format `ENT000001`, `ENT000002`, and so on. This makes IDs stable as long as the input ticker universe and sort rule stay fixed.

## confidence_score Rule

- `0.95`: ticker exists and `company_name` exists in the source row.
- `0.80`: ticker exists but `company_name` is missing, so ticker is used as the fallback company name.
- `0.60`: duplicate or ambiguous ticker issues appear.

## Known Limitations of v0

- The current source file may not contain a `company_name` column, so v0 may use ticker fallbacks.
- Parent/subsidiary relationships are not resolved.
- Country inference is conservative and leaves non-obvious cases as `Unknown`.
- Private and foreign competitors named in text fields are not added as separate entities yet.
- Corporate actions, historical ticker changes, and aliases are deferred to the alias/entity-resolution layer.

## Joining Later Tasks

Later task outputs should join to this table through `entity_id`. If an intermediate file only has `ticker`, first join `ticker` to `entities_v0.csv`, then carry `entity_id` into downstream files such as `entity_aliases_v0.csv`, `entity_labels_v0.csv`, embedding inputs, peer-review outputs, and market-level aggregation tables.
""",
        encoding="utf-8",
    )


def main() -> None:
    args = parse_args()

    with args.input_csv.open("r", newline="", encoding="utf-8-sig") as infile:
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames or []
        rows = list(reader)

    entities, duplicate_tickers = build_entities(rows, fieldnames)
    write_csv(args.output_csv, entities, args.overwrite)
    if args.spec:
        write_spec(args.spec, args.overwrite)

    print(f"Rows created: {len(entities)}")
    print(f"Duplicate tickers found: {len(duplicate_tickers)}")
    if duplicate_tickers:
        print("Duplicate ticker values: " + ", ".join(duplicate_tickers))
    print("Output columns: " + ", ".join(OUTPUT_FIELDS))


if __name__ == "__main__":
    main()
