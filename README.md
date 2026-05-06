# 580 - Group Theta

## Current Starting Point
The first implementation target is a cleaned company text table for embedding generation.

## Starter Assets
- `scripts/build_company_text_table.py`: builds a standardized company-level text table from a raw CSV
- `scripts/embed_company_text_openai.py`: sends cleaned company text to the OpenAI embeddings API and writes JSONL results
- `scripts/find_nearest_peers.py`: computes cosine similarity and writes top peer matches to a CSV
- `scripts/cluster_company_embeddings.py`: clusters embeddings and writes cluster labels with PCA coordinates
- `scripts/plot_company_clusters.py`: creates an interactive HTML scatter plot from clustered output
- `docs/stage1_company_text_spec.md`: defines the v0 input fields, output fields, and construction rules
- `docs/peer_review_template.csv`: fillable template for manual nearest-peer review
- `docs/peer_review_guide.md`: instructions for reviewing peer quality before clustering

## Usage
```bash
python3 scripts/build_company_text_table.py path/to/raw_companies.csv outputs/company_text_v0.csv
```

```bash
export OPENAI_API_KEY="your_api_key_here"
python3 scripts/embed_company_text_openai.py outputs/company_text_v0.csv outputs/company_embeddings_small.jsonl --limit 100
```

```bash
python3 scripts/find_nearest_peers.py outputs/company_embeddings_small.jsonl outputs/company_peers_top5.csv
```

```bash
python3 scripts/cluster_company_embeddings.py outputs/company_embeddings_small.jsonl outputs/company_clusters_k30.csv
```

```bash
python3 scripts/plot_company_clusters.py outputs/company_clusters_k30.csv outputs/company_clusters_k30_by_cluster.html
python3 scripts/plot_company_clusters.py outputs/company_clusters_k30.csv outputs/company_clusters_k30_by_industry.html --color-by industry_group
```

## Expected Input Columns
Minimum required:

- `ticker`

Strongly recommended:

- `company_name`
- `industry_group`
- `primary_industry`
- `ci_business_overview`
- `ci_business_model`
- `ci_products_services`
- `ci_target_customer`
