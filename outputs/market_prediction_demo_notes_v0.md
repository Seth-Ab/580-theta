# Market Prediction Demo Notes v0

## Setup

- Input file: `outputs/market_revenue_growth_v0.csv`
- Features used: `prior_growth_mean` and `latest_prior_growth`.
- `prior_growth_mean` is the average of `growth_q11_to_q10` through `growth_q2_to_q1`.
- `latest_prior_growth` is `growth_q2_to_q1`.
- Target: `growth_q1_to_q0`.
- Model used: leave_one_out_ols.
- Baseline: predict `growth_q1_to_q0` using `prior_growth_mean`.

## Summary Metrics

- Mean absolute error: 0.064307
- Baseline mean absolute error: 0.066821
- Directional accuracy: 0.714
- Baseline directional accuracy: 0.857

## Interpretation

This is a tiny proof-of-concept demo with only seven market observations.
It is not a production forecasting model, and accuracy is not the main claim.
The useful result is that the Theta market framework now produces market-level growth features that can feed a transparent predicted-versus-actual workflow.
The baseline comparison provides a simple check on whether the fitted demo adds anything beyond each market's own prior average growth.
These results should be described as pipeline validation rather than evidence of robust predictive performance.
