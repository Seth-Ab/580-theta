# LLM Judge Peer Review Spec v0

## Purpose

This experiment tests whether an LLM can act as a structured review layer on top of the existing Stage 1 nearest-peer pipeline.

The judge is not meant to replace embeddings, manual market-definition work, or final analyst judgment. Its role is narrower:

- score whether a nearest-peer set looks economically sensible
- explain likely failure modes
- flag cases that deserve manual review

The main research question is:

Can an LLM judge improve or accelerate nearest-peer evaluation without degrading judgment quality?

## Position In The Current Pipeline

The current Stage 1 pipeline is:

1. build company text
2. generate embeddings
3. find nearest peers
4. review peer quality

This experiment inserts the LLM only at Step 4.

The intended flow is:

1. `outputs/company_text_v0.csv`
2. `outputs/company_peers_top5.csv`
3. `scripts/judge_nearest_peers_openai.py`
4. `outputs/peer_judge_results_v0.csv`
5. `scripts/evaluate_peer_judge.py`
6. `outputs/peer_judge_eval_v0.md`

## Inputs

Primary required inputs:

- `outputs/company_peers_top5.csv`
- `outputs/company_text_v0.csv`

Optional evaluation input:

- a filled human-review CSV based on `docs/peer_review_template.csv`

## Unit Of Judgment

One judgment row corresponds to one focal company and its top peer set.

For v0, the judge should evaluate the top `k` peers already produced by the similarity pipeline. It should not change the peer ranking and should not generate new peers.

## Judge Questions

For each focal company, the judge should answer:

1. Are these peers economically sensible?
2. Does the peer set look strong, mixed, or weak?
3. What is the main reason if the set is weak?
4. Should a human accept the set, review it, or reject it?

## Output Schema

`outputs/peer_judge_results_v0.csv` should contain one row per focal company with these columns:

- `ticker`
- `company_name`
- `industry_group`
- `primary_industry`
- `peer_set_size`
- `peer_tickers`
- `judge_verdict`
- `judge_score`
- `economically_sensible`
- `same_industry_group_share`
- `same_primary_industry_share`
- `failure_modes`
- `recommended_action`
- `judge_notes`
- `model`
- `as_of_date`

### Field meanings

- `judge_verdict`: `Good`, `Mixed`, or `Bad`
- `judge_score`: `0-100` quality score
- `economically_sensible`: `yes`, `mostly`, or `no`
- `failure_modes`: semicolon-delimited tags
- `recommended_action`: `accept`, `review`, or `reject`

## Allowed Failure Modes

The v0 judge should restrict failure-mode tags to:

- `generic_text`
- `weak_company_text`
- `diversified_company`
- `adjacent_market`
- `label_disagreement_but_plausible`
- `wrong_peer`
- `mixed_peer_set`
- `insufficient_context`

## Prompt Design Rules

The prompt should force the model to judge only from the provided evidence:

- focal company metadata
- focal company text
- peer metadata
- peer company text

The prompt should explicitly instruct the model:

- not to invent outside facts
- not to reward shared wording alone
- not to assume same industry label means correct peer
- to prefer economic overlap, business model similarity, end-market similarity, and value-chain similarity
- to return strict JSON only

## Success Criteria

The judge is useful only if it improves the workflow in at least one concrete way:

- agrees well with human review
- catches obviously bad peer sets reliably
- produces useful failure-mode explanations
- reduces the amount of manual review needed

If it only produces plausible-sounding prose without useful signal, it should be dropped.

## Evaluation Design

Use a small labeled review set first.

Recommended starting size:

- `25-50` focal companies

Recommended coverage:

- obvious peer cases
- diversified firms
- weak-text firms
- surprising cases

Compare:

1. human review only
2. LLM judge output
3. agreement and disagreement patterns

## Core Metrics

`scripts/evaluate_peer_judge.py` should report:

- total reviewed cases
- exact verdict agreement
- verdict confusion counts
- agreement on `economically_sensible`
- agreement on same-industry and same-primary-industry shares when present
- cases where the judge says `review` or `reject`
- common judge failure modes

## Interpretation Rules

Good signs:

- high agreement on clearly good and clearly bad cases
- useful failure tags for mixed cases
- strong performance on weak-text or diversified cases

Bad signs:

- the judge mostly mirrors broad industry labels
- the judge cannot distinguish adjacent from true peers
- the judge is overconfident on weak evidence
- the judge gives generic notes that do not explain why a set is strong or weak

## What This Experiment Does Not Do

This branch does not:

- replace embeddings
- rerank peers automatically
- define markets
- score cluster coherence
- assign companies to markets
- estimate exposure weights

Those can be considered only if peer judging is helpful first.

## Exact Run Order

1. Confirm `outputs/company_text_v0.csv` exists.
2. Confirm `outputs/company_peers_top5.csv` exists.
3. Fill a small human-review file using `docs/peer_review_template.csv`.
4. Run `scripts/judge_nearest_peers_openai.py`.
5. Review `outputs/peer_judge_results_v0.csv`.
6. Run `scripts/evaluate_peer_judge.py`.
7. Write the final summary into `outputs/peer_judge_eval_v0.md`.

## Known Limitations

- The repo currently lacks stable human-readable company names in some upstream artifacts.
- The judge can only reason over the supplied text, which may itself be weak or incomplete.
- A strong narrative from the model does not prove correctness.
- Results are only meaningful if compared against human review.
