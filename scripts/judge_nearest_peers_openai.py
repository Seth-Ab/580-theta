#!/usr/bin/env python3

"""Judge nearest-peer quality using an OpenAI chat model.

This script reads the nearest-peer CSV plus company text, asks a model to judge
whether each focal company's peer set is economically sensible, and writes one
structured result row per focal company.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any


DEFAULT_MODEL = os.environ.get("OPENAI_JUDGE_MODEL", "gpt-4.1-mini")
DEFAULT_TOP_K = 5
DEFAULT_MAX_CASES = None
MAX_RETRIES = 5
OUTPUT_FIELDS = [
    "ticker",
    "company_name",
    "industry_group",
    "primary_industry",
    "peer_set_size",
    "peer_tickers",
    "judge_verdict",
    "judge_score",
    "economically_sensible",
    "same_industry_group_share",
    "same_primary_industry_share",
    "failure_modes",
    "recommended_action",
    "judge_notes",
    "model",
    "as_of_date",
]
ALLOWED_VERDICTS = {"Good", "Mixed", "Bad"}
ALLOWED_ECONOMIC_SENSIBLE = {"yes", "mostly", "no"}
ALLOWED_ACTIONS = {"accept", "review", "reject"}
ALLOWED_FAILURE_MODES = {
    "generic_text",
    "weak_company_text",
    "diversified_company",
    "adjacent_market",
    "label_disagreement_but_plausible",
    "wrong_peer",
    "mixed_peer_set",
    "insufficient_context",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Judge nearest-peer quality using an OpenAI chat model."
    )
    parser.add_argument(
        "peers_csv",
        type=Path,
        help="Path to outputs/company_peers_top5.csv or similar nearest-peer CSV.",
    )
    parser.add_argument(
        "company_text_csv",
        type=Path,
        help="Path to outputs/company_text_v0.csv.",
    )
    parser.add_argument(
        "output_csv",
        type=Path,
        help="Path to write outputs/peer_judge_results_v0.csv.",
    )
    parser.add_argument(
        "--review-template",
        type=Path,
        default=None,
        help=(
            "Optional filled review template. If provided, only judge tickers present "
            "in the template."
        ),
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Chat model to use. Default: {DEFAULT_MODEL}.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=DEFAULT_TOP_K,
        help=f"Number of peers to judge per focal company. Default: {DEFAULT_TOP_K}.",
    )
    parser.add_argument(
        "--max-cases",
        type=int,
        default=DEFAULT_MAX_CASES,
        help="Optional maximum number of focal companies to judge.",
    )
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=0.0,
        help="Optional pause between API calls.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite the output file if it already exists.",
    )
    return parser.parse_args()


def normalize_text(value: str | None) -> str:
    return " ".join((value or "").replace("\n", " ").replace("\r", " ").split()).strip()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as infile:
        return list(csv.DictReader(infile))


def load_company_text(path: Path) -> dict[str, dict[str, str]]:
    rows = read_csv(path)
    company_by_ticker: dict[str, dict[str, str]] = {}
    for row in rows:
        ticker = normalize_text(row.get("ticker"))
        if ticker:
            company_by_ticker[ticker] = row
    if not company_by_ticker:
        raise ValueError("No company-text rows found.")
    return company_by_ticker


def load_allowed_tickers(review_template: Path | None) -> set[str] | None:
    if review_template is None:
        return None
    rows = read_csv(review_template)
    allowed = {
        normalize_text(row.get("ticker"))
        for row in rows
        if normalize_text(row.get("ticker"))
    }
    return allowed or None


def load_peer_groups(
    peers_csv: Path,
    allowed_tickers: set[str] | None,
    top_k: int,
    max_cases: int | None,
) -> list[dict[str, Any]]:
    rows = read_csv(peers_csv)
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    focal_meta: dict[str, dict[str, str]] = {}

    for row in rows:
        ticker = normalize_text(row.get("ticker"))
        if not ticker:
            continue
        if allowed_tickers is not None and ticker not in allowed_tickers:
            continue
        grouped[ticker].append(row)
        focal_meta[ticker] = row

    groups: list[dict[str, Any]] = []
    for ticker in sorted(grouped):
        peer_rows = sorted(
            grouped[ticker],
            key=lambda row: int(normalize_text(row.get("peer_rank")) or "999999"),
        )[:top_k]
        groups.append(
            {
                "ticker": ticker,
                "meta": focal_meta[ticker],
                "peer_rows": peer_rows,
            }
        )

    if max_cases is not None:
        groups = groups[:max_cases]

    if not groups:
        raise ValueError("No peer groups available after filtering.")
    return groups


def share_matching(peer_rows: list[dict[str, str]], focal_field: str, peer_field: str) -> str:
    if not peer_rows:
        return ""
    focal_value = normalize_text(peer_rows[0].get(focal_field))
    matches = 0
    for row in peer_rows:
        if normalize_text(row.get(peer_field)) == focal_value and focal_value:
            matches += 1
    return f"{matches}/{len(peer_rows)}"


def build_prompt_payload(
    group: dict[str, Any],
    company_by_ticker: dict[str, dict[str, str]],
) -> dict[str, Any]:
    ticker = group["ticker"]
    focal_row = company_by_ticker.get(ticker, {})
    focal_meta = group["meta"]
    peers_payload: list[dict[str, Any]] = []

    for row in group["peer_rows"]:
        peer_ticker = normalize_text(row.get("peer_ticker"))
        peer_company = company_by_ticker.get(peer_ticker, {})
        peers_payload.append(
            {
                "peer_rank": normalize_text(row.get("peer_rank")),
                "peer_ticker": peer_ticker,
                "peer_company_name": normalize_text(row.get("peer_company_name")),
                "peer_industry_group": normalize_text(row.get("peer_industry_group")),
                "peer_primary_industry": normalize_text(row.get("peer_primary_industry")),
                "cosine_similarity": normalize_text(row.get("cosine_similarity")),
                "peer_company_text": normalize_text(peer_company.get("company_text")),
            }
        )

    return {
        "focal_company": {
            "ticker": ticker,
            "company_name": normalize_text(focal_meta.get("company_name")),
            "industry_group": normalize_text(focal_meta.get("industry_group")),
            "primary_industry": normalize_text(focal_meta.get("primary_industry")),
            "company_text": normalize_text(focal_row.get("company_text")),
        },
        "peer_set": peers_payload,
        "rubric": {
            "good": "Most peers look economically plausible based on business model, products, customers, or value-chain role.",
            "mixed": "Some peers are plausible but the set is diluted by generic, adjacent, or weak peers.",
            "bad": "Most peers look economically weak, generic, or wrong.",
        },
    }


def build_messages(payload: dict[str, Any]) -> list[dict[str, str]]:
    system_prompt = """
You are evaluating nearest-peer quality for a market-definition research workflow.

Judge only from the supplied evidence. Do not use outside knowledge. Do not assume
that the same industry label means a peer is correct. Shared wording alone is not
enough. Prefer economic overlap, similar business model, similar products, similar
customers, similar end markets, or similar value-chain role.

Return valid JSON only with this schema:
{
  "judge_verdict": "Good" | "Mixed" | "Bad",
  "judge_score": integer from 0 to 100,
  "economically_sensible": "yes" | "mostly" | "no",
  "failure_modes": ["tag", ...],
  "recommended_action": "accept" | "review" | "reject",
  "judge_notes": "1-3 sentences grounded in the provided text"
}

Allowed failure_modes:
- generic_text
- weak_company_text
- diversified_company
- adjacent_market
- label_disagreement_but_plausible
- wrong_peer
- mixed_peer_set
- insufficient_context

If the peer set is strong, failure_modes may be an empty list.
""".strip()

    user_prompt = (
        "Evaluate the following focal company and its nearest peers.\n\n"
        + json.dumps(payload, ensure_ascii=True, indent=2)
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def request_judgment(client: Any, model: str, payload: dict[str, Any]) -> dict[str, Any]:
    messages = build_messages(payload)
    delay = 1.0
    last_error: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            if not content:
                raise ValueError("Model returned empty content.")
            return json.loads(content)
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt == MAX_RETRIES:
                break
            time.sleep(delay)
            delay *= 2

    raise RuntimeError(f"Judgment request failed after {MAX_RETRIES} attempts.") from last_error


def coerce_failure_modes(value: Any) -> list[str]:
    if isinstance(value, list):
        modes = [normalize_text(str(item)) for item in value]
    elif isinstance(value, str):
        modes = [normalize_text(item) for item in value.split(";")]
    else:
        modes = []
    cleaned = [mode for mode in modes if mode in ALLOWED_FAILURE_MODES]
    deduped: list[str] = []
    for mode in cleaned:
        if mode not in deduped:
            deduped.append(mode)
    return deduped


def validate_judgment(judgment: dict[str, Any]) -> dict[str, str]:
    verdict = normalize_text(str(judgment.get("judge_verdict")))
    if verdict not in ALLOWED_VERDICTS:
        raise ValueError(f"Invalid judge_verdict: {verdict}")

    score_raw = judgment.get("judge_score")
    try:
        score = int(score_raw)
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"Invalid judge_score: {score_raw}") from exc
    score = max(0, min(100, score))

    sensible = normalize_text(str(judgment.get("economically_sensible")))
    if sensible not in ALLOWED_ECONOMIC_SENSIBLE:
        raise ValueError(f"Invalid economically_sensible: {sensible}")

    action = normalize_text(str(judgment.get("recommended_action")))
    if action not in ALLOWED_ACTIONS:
        raise ValueError(f"Invalid recommended_action: {action}")

    failure_modes = coerce_failure_modes(judgment.get("failure_modes"))
    notes = normalize_text(str(judgment.get("judge_notes")))

    return {
        "judge_verdict": verdict,
        "judge_score": str(score),
        "economically_sensible": sensible,
        "failure_modes": ";".join(failure_modes),
        "recommended_action": action,
        "judge_notes": notes,
    }


def build_output_row(
    group: dict[str, Any],
    company_by_ticker: dict[str, dict[str, str]],
    model: str,
    judgment: dict[str, str],
) -> dict[str, str]:
    ticker = group["ticker"]
    focal_meta = group["meta"]
    peer_rows = group["peer_rows"]
    peer_tickers = [normalize_text(row.get("peer_ticker")) for row in peer_rows]

    return {
        "ticker": ticker,
        "company_name": normalize_text(focal_meta.get("company_name")),
        "industry_group": normalize_text(focal_meta.get("industry_group")),
        "primary_industry": normalize_text(focal_meta.get("primary_industry")),
        "peer_set_size": str(len(peer_rows)),
        "peer_tickers": ";".join(peer_tickers),
        "judge_verdict": judgment["judge_verdict"],
        "judge_score": judgment["judge_score"],
        "economically_sensible": judgment["economically_sensible"],
        "same_industry_group_share": share_matching(
            peer_rows, "industry_group", "peer_industry_group"
        ),
        "same_primary_industry_share": share_matching(
            peer_rows, "primary_industry", "peer_primary_industry"
        ),
        "failure_modes": judgment["failure_modes"],
        "recommended_action": judgment["recommended_action"],
        "judge_notes": judgment["judge_notes"],
        "model": model,
        "as_of_date": str(date.today()),
    }


def write_output(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()

    if args.top_k <= 0:
        raise ValueError("--top-k must be positive.")
    if args.max_cases is not None and args.max_cases <= 0:
        raise ValueError("--max-cases must be positive if provided.")
    if args.output_csv.exists() and not args.overwrite:
        raise FileExistsError(
            f"{args.output_csv} already exists. Pass --overwrite to replace it."
        )

    company_by_ticker = load_company_text(args.company_text_csv)
    allowed_tickers = load_allowed_tickers(args.review_template)
    groups = load_peer_groups(
        peers_csv=args.peers_csv,
        allowed_tickers=allowed_tickers,
        top_k=args.top_k,
        max_cases=args.max_cases,
    )

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise ImportError(
            "The `openai` package is not installed. Run `pip install -r requirements.txt` "
            "in your project environment first."
        ) from exc

    client = OpenAI()
    output_rows: list[dict[str, str]] = []

    for index, group in enumerate(groups, start=1):
        payload = build_prompt_payload(group, company_by_ticker)
        judgment = request_judgment(client=client, model=args.model, payload=payload)
        validated = validate_judgment(judgment)
        output_rows.append(
            build_output_row(
                group=group,
                company_by_ticker=company_by_ticker,
                model=args.model,
                judgment=validated,
            )
        )
        print(
            f"Judged {index}/{len(groups)}: {group['ticker']} -> {validated['judge_verdict']}",
            file=sys.stderr,
        )
        if args.sleep_seconds > 0:
            time.sleep(args.sleep_seconds)

    write_output(args.output_csv, output_rows)
    print(f"Wrote {len(output_rows)} judge rows to {args.output_csv}", file=sys.stderr)


if __name__ == "__main__":
    main()
