#!/usr/bin/env python3

"""Build a cleaned company text table for embedding generation.

Input:
    A CSV file with at least a `ticker` column and any subset of the supported
    text/classification fields.

Output:
    A CSV file with one row per company and a standardized `company_text`
    column suitable for embedding generation.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Iterable


CORE_TEXT_FIELDS = [
    "ci_business_overview",
    "ci_business_model",
    "ci_products_services",
    "ci_target_customer",
]

BASELINE_FIELDS = [
    "ticker",
    "company_name",
    "industry_group",
    "primary_industry",
]

OPTIONAL_METADATA_FIELDS = [
    "ci_geographic_scope",
    "ci_cyclicality",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a cleaned company text table from a raw company CSV."
    )
    parser.add_argument("input_csv", type=Path, help="Path to the raw input CSV.")
    parser.add_argument("output_csv", type=Path, help="Path to the cleaned output CSV.")
    return parser.parse_args()


def normalize_text(value: str) -> str:
    collapsed = " ".join(value.replace("\n", " ").replace("\r", " ").split())
    return collapsed.strip()


def present_fields(row: dict[str, str], fields: Iterable[str]) -> list[str]:
    return [field for field in fields if normalize_text(row.get(field, ""))]


def build_company_text(row: dict[str, str]) -> str:
    sections: list[str] = []
    section_labels = {
        "ci_business_overview": "Business overview",
        "ci_business_model": "Business model",
        "ci_products_services": "Products and services",
        "ci_target_customer": "Target customer",
    }

    for field in CORE_TEXT_FIELDS:
        value = normalize_text(row.get(field, ""))
        if value:
            sections.append(f"{section_labels[field]}: {value}")

    return "\n".join(sections)


def build_output_row(row: dict[str, str]) -> dict[str, str]:
    output: dict[str, str] = {}

    for field in BASELINE_FIELDS + OPTIONAL_METADATA_FIELDS:
        output[field] = normalize_text(row.get(field, ""))

    if not output["company_name"]:
        output["company_name"] = output["ticker"]

    available_fields = present_fields(row, CORE_TEXT_FIELDS)
    missing_fields = [field for field in CORE_TEXT_FIELDS if field not in available_fields]

    output["company_text"] = build_company_text(row)
    output["core_text_field_count"] = str(len(available_fields))
    output["core_text_field_coverage"] = f"{len(available_fields)}/{len(CORE_TEXT_FIELDS)}"
    output["available_core_text_fields"] = ";".join(available_fields)
    output["missing_core_text_fields"] = ";".join(missing_fields)

    return output


def validate_columns(fieldnames: list[str] | None) -> None:
    if not fieldnames:
        raise ValueError("Input CSV has no header row.")
    if "ticker" not in fieldnames:
        raise ValueError("Input CSV must include a `ticker` column.")


def main() -> None:
    args = parse_args()

    with args.input_csv.open("r", newline="", encoding="utf-8-sig") as infile:
        reader = csv.DictReader(infile)
        validate_columns(reader.fieldnames)
        rows = [build_output_row(row) for row in reader]

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    output_fields = BASELINE_FIELDS + OPTIONAL_METADATA_FIELDS + [
        "company_text",
        "core_text_field_count",
        "core_text_field_coverage",
        "available_core_text_fields",
        "missing_core_text_fields",
    ]

    with args.output_csv.open("w", newline="", encoding="utf-8") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=output_fields)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
