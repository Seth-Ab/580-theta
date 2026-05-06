#!/usr/bin/env python3

"""Cluster company embeddings and attach cluster labels to company metadata."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from sklearn.cluster import AgglomerativeClustering
from sklearn.decomposition import PCA
from sklearn.metrics.pairwise import cosine_similarity


OUTPUT_FIELDS = [
    "ticker",
    "company_name",
    "industry_group",
    "primary_industry",
    "ci_geographic_scope",
    "ci_cyclicality",
    "model",
    "cluster_label",
    "pca_x",
    "pca_y",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Cluster company embeddings with AgglomerativeClustering."
    )
    parser.add_argument("input_jsonl", type=Path, help="Path to embeddings JSONL.")
    parser.add_argument("output_csv", type=Path, help="Path to clustered output CSV.")
    parser.add_argument(
        "--n-clusters",
        type=int,
        default=30,
        help="Number of clusters to fit. Default: 30.",
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
        raise ValueError("Input JSONL contains no embeddings.")
    return rows


def cluster_records(records: list[dict[str, Any]], n_clusters: int) -> tuple[list[int], list[list[float]]]:
    embeddings = [record["embedding"] for record in records]

    similarity = cosine_similarity(embeddings)
    distance = 1.0 - similarity

    clustering = AgglomerativeClustering(
        n_clusters=n_clusters,
        metric="precomputed",
        linkage="average",
    )
    labels = clustering.fit_predict(distance)

    pca = PCA(n_components=2)
    coords = pca.fit_transform(embeddings)

    return labels.tolist(), coords.tolist()


def write_output(
    path: Path,
    records: list[dict[str, Any]],
    labels: list[int],
    coords: list[list[float]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()

        for record, label, (pca_x, pca_y) in zip(records, labels, coords, strict=True):
            row = {
                "ticker": record.get("ticker", ""),
                "company_name": record.get("company_name", ""),
                "industry_group": record.get("industry_group", ""),
                "primary_industry": record.get("primary_industry", ""),
                "ci_geographic_scope": record.get("ci_geographic_scope", ""),
                "ci_cyclicality": record.get("ci_cyclicality", ""),
                "model": record.get("model", ""),
                "cluster_label": label,
                "pca_x": f"{pca_x:.6f}",
                "pca_y": f"{pca_y:.6f}",
            }
            writer.writerow(row)


def main() -> None:
    args = parse_args()

    if args.n_clusters <= 1:
        raise ValueError("--n-clusters must be greater than 1.")
    if args.output_csv.exists() and not args.overwrite:
        raise FileExistsError(
            f"{args.output_csv} already exists. Pass --overwrite to replace it."
        )

    records = load_embeddings(args.input_jsonl)
    labels, coords = cluster_records(records, args.n_clusters)
    write_output(args.output_csv, records, labels, coords)


if __name__ == "__main__":
    main()
