#!/usr/bin/env python3

"""Generate OpenAI embeddings for company text rows.

Reads the cleaned company text table, batches non-empty rows through the
embeddings API, and writes one JSON object per company to a JSONL file.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path
from typing import Any


DEFAULT_MODEL = "text-embedding-3-small"
DEFAULT_BATCH_SIZE = 100
MAX_RETRIES = 5

METADATA_FIELDS = [
    "ticker",
    "company_name",
    "industry_group",
    "primary_industry",
    "ci_geographic_scope",
    "ci_cyclicality",
    "core_text_field_count",
    "core_text_field_coverage",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate OpenAI embeddings for company text rows."
    )
    parser.add_argument("input_csv", type=Path, help="Path to company_text_v0 CSV.")
    parser.add_argument("output_jsonl", type=Path, help="Path to output JSONL file.")
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Embedding model to use. Default: {DEFAULT_MODEL}.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Number of rows per embeddings request. Default: {DEFAULT_BATCH_SIZE}.",
    )
    parser.add_argument(
        "--dimensions",
        type=int,
        default=None,
        help="Optional output embedding dimensions for text-embedding-3 models.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional max number of non-empty company rows to embed.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite the output file if it already exists.",
    )
    return parser.parse_args()


def load_rows(input_csv: Path, limit: int | None) -> list[dict[str, str]]:
    with input_csv.open("r", newline="", encoding="utf-8-sig") as infile:
        reader = csv.DictReader(infile)
        rows: list[dict[str, str]] = []
        for row in reader:
            company_text = (row.get("company_text") or "").strip()
            if not company_text:
                continue
            rows.append(row)
            if limit is not None and len(rows) >= limit:
                break
    return rows


def batched(items: list[dict[str, str]], batch_size: int) -> list[list[dict[str, str]]]:
    return [items[i : i + batch_size] for i in range(0, len(items), batch_size)]


def request_embeddings(
    client: Any,
    batch: list[dict[str, str]],
    model: str,
    dimensions: int | None,
) -> tuple[list[Any], int]:
    inputs = [row["company_text"] for row in batch]
    kwargs: dict[str, Any] = {
        "model": model,
        "input": inputs,
        "encoding_format": "float",
    }
    if dimensions is not None:
        kwargs["dimensions"] = dimensions

    delay = 1.0
    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.embeddings.create(**kwargs)
            prompt_tokens = getattr(response.usage, "prompt_tokens", 0) or 0
            return response.data, prompt_tokens
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt == MAX_RETRIES:
                break
            time.sleep(delay)
            delay *= 2

    raise RuntimeError(f"Embedding request failed after {MAX_RETRIES} attempts.") from last_error


def write_results(
    client: Any,
    rows: list[dict[str, str]],
    output_jsonl: Path,
    model: str,
    batch_size: int,
    dimensions: int | None,
) -> None:
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    batches = batched(rows, batch_size)
    total_batches = len(batches)
    total_prompt_tokens = 0

    with output_jsonl.open("w", encoding="utf-8") as outfile:
        for batch_index, batch in enumerate(batches, start=1):
            embedding_data, prompt_tokens = request_embeddings(
                client=client,
                batch=batch,
                model=model,
                dimensions=dimensions,
            )
            total_prompt_tokens += prompt_tokens

            for row, embedding_item in zip(batch, embedding_data, strict=True):
                record = {field: row.get(field, "") for field in METADATA_FIELDS}
                record["model"] = model
                record["embedding"] = embedding_item.embedding
                outfile.write(json.dumps(record) + "\n")

            print(
                f"Completed batch {batch_index}/{total_batches} "
                f"({len(batch)} rows, cumulative prompt tokens: {total_prompt_tokens})",
                file=sys.stderr,
            )

    print(
        f"Finished embedding {len(rows)} rows with model {model}. "
        f"Total prompt tokens: {total_prompt_tokens}.",
        file=sys.stderr,
    )


def main() -> None:
    args = parse_args()

    if args.batch_size <= 0:
        raise ValueError("--batch-size must be positive.")
    if args.output_jsonl.exists() and not args.overwrite:
        raise FileExistsError(
            f"{args.output_jsonl} already exists. Pass --overwrite to replace it."
        )

    rows = load_rows(args.input_csv, args.limit)
    if not rows:
        raise ValueError("No non-empty company_text rows found in the input CSV.")

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise ImportError(
            "The `openai` package is not installed. Run `pip install -r requirements.txt` "
            "in your project environment first."
        ) from exc

    client = OpenAI()
    write_results(
        client=client,
        rows=rows,
        output_jsonl=args.output_jsonl,
        model=args.model,
        batch_size=args.batch_size,
        dimensions=args.dimensions,
    )


if __name__ == "__main__":
    main()
