#!/usr/bin/env python3

"""Evaluate LLM peer-judge output against a filled human review template."""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path


VERDICTS = ("Good", "Mixed", "Bad")
SENSIBLE_VALUES = ("yes", "mostly", "no")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate LLM peer-judge output against human review."
    )
    parser.add_argument(
        "judge_csv",
        type=Path,
        help="Path to outputs/peer_judge_results_v0.csv.",
    )
    parser.add_argument(
        "human_review_csv",
        type=Path,
        help="Path to a filled human review CSV based on docs/peer_review_template.csv.",
    )
    parser.add_argument(
        "output_md",
        type=Path,
        help="Path to write outputs/peer_judge_eval_v0.md.",
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


def safe_ratio(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "n/a"
    return f"{numerator / denominator:.1%}"


def build_confusion_matrix() -> dict[str, Counter[str]]:
    return {human: Counter() for human in VERDICTS}


def main() -> None:
    args = parse_args()
    if args.output_md.exists() and not args.overwrite:
        raise FileExistsError(
            f"{args.output_md} already exists. Pass --overwrite to replace it."
        )

    judge_rows = read_csv(args.judge_csv)
    human_rows = read_csv(args.human_review_csv)

    judge_by_ticker = {
        normalize_text(row.get("ticker")): row
        for row in judge_rows
        if normalize_text(row.get("ticker"))
    }
    human_by_ticker = {
        normalize_text(row.get("ticker")): row
        for row in human_rows
        if normalize_text(row.get("ticker")) and normalize_text(row.get("verdict"))
    }

    overlapping_tickers = sorted(set(judge_by_ticker) & set(human_by_ticker))
    missing_from_judge = sorted(set(human_by_ticker) - set(judge_by_ticker))
    missing_from_humans = sorted(set(judge_by_ticker) - set(human_by_ticker))

    confusion = build_confusion_matrix()
    verdict_matches = 0
    sensible_matches = 0
    review_or_reject = 0
    failure_mode_counter: Counter[str] = Counter()
    focus_counter: Counter[str] = Counter()
    mismatch_rows: list[dict[str, str]] = []

    for ticker in overlapping_tickers:
        human = human_by_ticker[ticker]
        judge = judge_by_ticker[ticker]

        human_verdict = normalize_text(human.get("verdict"))
        judge_verdict = normalize_text(judge.get("judge_verdict"))
        human_sensible = normalize_text(human.get("economically_sensible"))
        judge_sensible = normalize_text(judge.get("economically_sensible"))
        focus_category = normalize_text(human.get("focus_category"))
        action = normalize_text(judge.get("recommended_action"))
        failure_modes = [
            mode for mode in normalize_text(judge.get("failure_modes")).split(";") if mode
        ]

        if human_verdict in VERDICTS and judge_verdict in VERDICTS:
            confusion[human_verdict][judge_verdict] += 1
        if human_verdict == judge_verdict:
            verdict_matches += 1
        if human_sensible in SENSIBLE_VALUES and judge_sensible in SENSIBLE_VALUES:
            if human_sensible == judge_sensible:
                sensible_matches += 1
        if action in {"review", "reject"}:
            review_or_reject += 1

        focus_counter[focus_category] += 1
        failure_mode_counter.update(failure_modes)

        if human_verdict != judge_verdict:
            mismatch_rows.append(
                {
                    "ticker": ticker,
                    "focus_category": focus_category,
                    "human_verdict": human_verdict,
                    "judge_verdict": judge_verdict,
                    "judge_score": normalize_text(judge.get("judge_score")),
                    "recommended_action": action,
                    "failure_modes": ";".join(failure_modes),
                    "judge_notes": normalize_text(judge.get("judge_notes")),
                    "human_notes": normalize_text(human.get("notes")),
                }
            )

    lines: list[str] = []
    lines.append("# Peer Judge Evaluation v0")
    lines.append("")
    lines.append("## Inputs")
    lines.append("")
    lines.append(f"- Judge file: `{args.judge_csv}`")
    lines.append(f"- Human review file: `{args.human_review_csv}`")
    lines.append("")
    lines.append("## Coverage")
    lines.append("")
    lines.append(f"- Judge rows: `{len(judge_rows)}`")
    lines.append(f"- Human-reviewed rows with verdicts: `{len(human_by_ticker)}`")
    lines.append(f"- Overlapping comparable rows: `{len(overlapping_tickers)}`")
    lines.append(f"- Human rows missing from judge output: `{len(missing_from_judge)}`")
    lines.append(f"- Judge rows missing from human review: `{len(missing_from_humans)}`")
    lines.append("")
    lines.append("## Headline Metrics")
    lines.append("")
    lines.append(f"- Exact verdict agreement: `{verdict_matches}/{len(overlapping_tickers)}` ({safe_ratio(verdict_matches, len(overlapping_tickers))})")
    lines.append(f"- Economically sensible agreement: `{sensible_matches}/{len(overlapping_tickers)}` ({safe_ratio(sensible_matches, len(overlapping_tickers))})")
    lines.append(f"- Judge action = review or reject: `{review_or_reject}/{len(overlapping_tickers)}` ({safe_ratio(review_or_reject, len(overlapping_tickers))})")
    lines.append("")
    lines.append("## Verdict Confusion Matrix")
    lines.append("")
    lines.append(r"| Human \ Judge | Good | Mixed | Bad |")
    lines.append("| --- | ---: | ---: | ---: |")
    for human_verdict in VERDICTS:
        row = confusion[human_verdict]
        lines.append(
            f"| {human_verdict} | {row['Good']} | {row['Mixed']} | {row['Bad']} |"
        )
    lines.append("")
    lines.append("## Human Focus Categories")
    lines.append("")
    if focus_counter:
        for key, value in sorted(focus_counter.items()):
            lines.append(f"- `{key}`: `{value}`")
    else:
        lines.append("- No focus categories found in the human review file.")
    lines.append("")
    lines.append("## Common Judge Failure Modes")
    lines.append("")
    if failure_mode_counter:
        for key, value in failure_mode_counter.most_common():
            lines.append(f"- `{key}`: `{value}`")
    else:
        lines.append("- No failure modes recorded.")
    lines.append("")
    lines.append("## Mismatched Cases")
    lines.append("")
    if mismatch_rows:
        for row in mismatch_rows:
            lines.append(
                f"- `{row['ticker']}`: human=`{row['human_verdict']}`, judge=`{row['judge_verdict']}`, "
                f"focus=`{row['focus_category']}`, score=`{row['judge_score']}`, "
                f"action=`{row['recommended_action']}`, failure_modes=`{row['failure_modes']}`"
            )
            lines.append(f"  Judge notes: {row['judge_notes']}")
            lines.append(f"  Human notes: {row['human_notes']}")
    else:
        lines.append("- No verdict mismatches found.")
    lines.append("")
    lines.append("## Missing Coverage")
    lines.append("")
    if missing_from_judge:
        lines.append(
            "- Human-reviewed tickers missing from judge output: "
            + ", ".join(f"`{ticker}`" for ticker in missing_from_judge[:25])
        )
    else:
        lines.append("- No human-reviewed tickers were missing from judge output.")
    if missing_from_humans:
        lines.append(
            "- Judge-output tickers missing from human review: "
            + ", ".join(f"`{ticker}`" for ticker in missing_from_humans[:25])
        )
    else:
        lines.append("- No judge-output tickers were missing from human review.")
    lines.append("")
    lines.append("## Recommendation Template")
    lines.append("")
    lines.append("Use the metrics above to decide one of three outcomes:")
    lines.append("")
    lines.append("- `keep`: the judge agrees well with humans and provides useful flags")
    lines.append("- `revise`: the judge has some value but prompt/schema changes are needed")
    lines.append("- `drop`: the judge adds noise or fails to match human review")
    lines.append("")

    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
