#!/usr/bin/env python3

"""Compute nearest peers from a JSONL embeddings file."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from sklearn.metrics.pairwise import cosine_similarity


METADATA_FIELDS = [
    "ticker",
    "company_name",
    "industry_group",
    "primary_industry",
    "ci_geographic_scope",
    "ci_cyclicality",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compute nearest peers from a JSONL embeddings file."
    )
    parser.add_argument("input_jsonl", type=Path, help="Path to embeddings JSONL.")
    parser.add_argument("output_csv", type=Path, help="Path to nearest-peers CSV.")
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of nearest peers to keep for each company. Default: 5.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite the output file if it already exists.",
    )
    return parser.parse_args()


def load_embeddings(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as infile:
        for line_number, line in enumerate(infile, start=1):
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            if "embedding" not in record:
                raise ValueError(f"Missing `embedding` field on line {line_number}.")
            rows.append(record)
    if not rows:
        raise ValueError("Input JSONL contains no embedding rows.")
    return rows


def build_output_rows(records: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
    embeddings = [record["embedding"] for record in records]
    similarity_matrix = cosine_similarity(embeddings)
    output_rows: list[dict[str, Any]] = []

    for i, record in enumerate(records):
        ranked = sorted(
            (
                (j, score)
                for j, score in enumerate(similarity_matrix[i])
                if i != j
            ),
            key=lambda item: item[1],
            reverse=True,
        )[:top_k]

        for rank, (peer_index, score) in enumerate(ranked, start=1):
            peer = records[peer_index]
            row = {
                "ticker": record.get("ticker", ""),
                "company_name": record.get("company_name", ""),
                "industry_group": record.get("industry_group", ""),
                "primary_industry": record.get("primary_industry", ""),
                "peer_rank": rank,
                "peer_ticker": peer.get("ticker", ""),
                "peer_company_name": peer.get("company_name", ""),
                "peer_industry_group": peer.get("industry_group", ""),
                "peer_primary_industry": peer.get("primary_industry", ""),
                "cosine_similarity": f"{score:.6f}",
            }
            output_rows.append(row)

    return output_rows


def write_output(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "ticker",
        "company_name",
        "industry_group",
        "primary_industry",
        "peer_rank",
        "peer_ticker",
        "peer_company_name",
        "peer_industry_group",
        "peer_primary_industry",
        "cosine_similarity",
    ]

    with path.open("w", newline="", encoding="utf-8") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()

    if args.top_k <= 0:
        raise ValueError("--top-k must be positive.")
    if args.output_csv.exists() and not args.overwrite:
        raise FileExistsError(
            f"{args.output_csv} already exists. Pass --overwrite to replace it."
        )

    records = load_embeddings(args.input_jsonl)
    output_rows = build_output_rows(records, args.top_k)
    write_output(args.output_csv, output_rows)


if __name__ == "__main__":
    main()
