#!/usr/bin/env python3

"""Create interactive cluster visualizations from clustered company output."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


COLOR_OPTIONS = {
    "cluster": "cluster_label",
    "industry_group": "industry_group",
    "primary_industry": "primary_industry",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plot clustered company embeddings as an interactive HTML scatter plot."
    )
    parser.add_argument("input_csv", type=Path, help="Path to clustered company CSV.")
    parser.add_argument("output_html", type=Path, help="Path to output HTML plot.")
    parser.add_argument(
        "--color-by",
        choices=sorted(COLOR_OPTIONS.keys()),
        default="cluster",
        help="Field to color points by. Default: cluster.",
    )
    parser.add_argument(
        "--title",
        default=None,
        help="Optional chart title.",
    )
    parser.add_argument(
        "--point-size",
        type=int,
        default=7,
        help="Marker size. Default: 7.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite the output file if it already exists.",
    )
    return parser.parse_args()


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as infile:
        reader = csv.DictReader(infile)
        rows = list(reader)
    if not rows:
        raise ValueError("Input CSV contains no rows.")
    return rows


def build_hover_text(row: dict[str, str]) -> str:
    return (
        f"Ticker: {row.get('ticker', '')}<br>"
        f"Name: {row.get('company_name', '')}<br>"
        f"Cluster: {row.get('cluster_label', '')}<br>"
        f"Industry group: {row.get('industry_group', '')}<br>"
        f"Primary industry: {row.get('primary_industry', '')}<br>"
        f"Geography: {row.get('ci_geographic_scope', '')}<br>"
        f"Cyclicality: {row.get('ci_cyclicality', '')}"
    )


def main() -> None:
    args = parse_args()

    if args.output_html.exists() and not args.overwrite:
        raise FileExistsError(
            f"{args.output_html} already exists. Pass --overwrite to replace it."
        )

    try:
        import pandas as pd
        import plotly.express as px
    except ImportError as exc:
        raise ImportError(
            "This script requires `pandas` and `plotly`. "
            "Run `pip install -r requirements.txt` first."
        ) from exc

    rows = load_rows(args.input_csv)
    df = pd.DataFrame(rows)

    for column in ["pca_x", "pca_y"]:
        if column not in df.columns:
            raise ValueError(f"Input CSV is missing required column `{column}`.")
        df[column] = df[column].astype(float)

    color_field = COLOR_OPTIONS[args.color_by]
    if color_field not in df.columns:
        raise ValueError(f"Input CSV is missing required column `{color_field}`.")

    df["hover_text"] = df.apply(build_hover_text, axis=1)
    title = args.title or f"Company Embedding Plot Colored By {color_field}"

    fig = px.scatter(
        df,
        x="pca_x",
        y="pca_y",
        color=color_field,
        hover_name="ticker",
        hover_data={
            "pca_x": False,
            "pca_y": False,
            color_field: True,
            "company_name": True,
            "industry_group": True,
            "primary_industry": True,
            "cluster_label": True,
        },
        title=title,
    )

    fig.update_traces(marker={"size": args.point_size, "opacity": 0.8})
    fig.update_layout(
        xaxis_title="PCA 1",
        yaxis_title="PCA 2",
        legend_title=color_field,
    )

    args.output_html.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(args.output_html), include_plotlyjs="cdn")


if __name__ == "__main__":
    main()
