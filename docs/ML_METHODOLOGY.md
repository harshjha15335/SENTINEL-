# ML Methodology

**Status (2026-10-10):** Track B (operational model) is trained, evaluated once on held-out data, and serving in the API. Track A (IEEE-CIS benchmark) has not started; it needs Kaggle access.

Every number below comes from `apps/api/app/risk_models/operational-v1/metadata.json`, which `ml/sentinel_ml/train_operational.py` writes. None was typed in by hand. Reproduce it with:

```
PYTHONPATH=apps/api:ml apps/api/.venv/bin/python -m sentinel_ml.train_operational
```

CI re-trains the model and checks it against the committed artifact (`ml/tests/test_pipeline.py::test_committed_artifact_is_reproducible`):
- **Exact match required:** the dataset hash, the chosen model and the booster digest.
- **Small tolerance allowed:** the Platt parameters and the thresholds derived from them. Platt fitting uses an iterative optimiser whose last digits depend on the CPU and BLAS build. One CI machine produced a high threshold of 0.1052 instead of 0.1036.
- **What production serves:** always the committed artifact, never a fresh re-fit.

## Track B: operational engine (synthetic-trained)

### Data: SYNTHETIC_DEMO only
- **Generator:** `app/services/demo/scenario.py`, version `demo-scenario-v1`, seed 2026.
- **Size:** 3,000 payers and 9,051 payments over 150 days, starting 2026-05-01.
- **Labels:** `adverse` means a dispute or chargeback followed the payment. 409 payments are positive, a prevalence of 4.5%.
- **Archetypes:** regular, high value, burst fraud, quiet fraud, refund abuse, and busy legitimate. The busy legitimate group is there to tempt false positives. Each archetype has a noisy adverse probability, so a perfect score would indicate a bug.
- **Integrity:** the dataset hash is recorded in the metadata.
- **Nothing here describes real people or PayPal outcomes.**

### Features: past-only, one implementation
`app/services/risk/features.py` is used by training (`ml/sentinel_ml/dataset.py`) and by live scoring (`app/services/risk/scoring.py`), so the two can't drift apart.

**The 12 features:**

| Group | Features |
|---|---|
| Amount | amount (log); amount ÷ the merchant's recent median |
| Merchant history | flag when merchant history is under 10 payments; merchant payments in the last hour |
| Payer history | new payer; payer's earlier payments over 90 days, 1h and 24h; payer's amount over 24h; hours since the payer's previous payment |
| Payer outcomes | payer's prior refunds and disputes over 90 days, counted only when the refund or dispute itself happened before the scored payment |

**How past-only is enforced:**
- `compute_features` filters out any row at or after the target, so callers can't leak the future by accident.
- History is restricted to the same merchant and the same data origin. Synthetic history can never shift the features of a sandbox payment.

**Not modelled, because SENTINEL does not observe them:** device, card or IP fingerprints, identity data, and PayPal-internal risk attributes.

### Split, selection, calibration and threshold
1. **Chronological 60/20/20 split** by `occurred_at`, with no shuffling:
   - train: 5,430 rows
   - validation: 1,810 rows
   - test: 1,811 rows
2. **Candidates:**
   - a transparent rules baseline (count of four red flags)
   - logistic regression (standardised, class-balanced)
   - XGBoost over a 12-point grid (depth, trees, learning rate)
   - Selection is by validation PR-AUC.
3. **Calibration:** Platt (sigmoid), fitted on validation with the base model frozen.
4. **High threshold:** the lowest expected cost on validation, while flagging at most 8% of payments (the review capacity).
   - Medium band: the 80th percentile of validation scores, capped at the high threshold.
   - Costs are illustrative assumptions, not measurements:

     | Assumption | Value |
     |---|---|
     | Analyst review | $4 |
     | Chargeback fee on a missed adverse payment | $20 plus the payment amount |
     | Share of loss a review prevents | 70% |
5. **One evaluation** on the test split.

### Validation comparison (PR-AUC / ROC-AUC)

| Candidate | PR-AUC | ROC-AUC |
|---|---|---|
| Rules baseline | 0.085 | 0.708 |
| Logistic regression | 0.305 | 0.851 |
| **XGBoost (depth 2, 150 trees, lr 0.1), chosen** | **0.378** | 0.847 |

### Held-out test results
Test split: 1,811 payments, 78 of them adverse (4.3%).

| Metric | XGBoost at threshold 0.1036 | Rules baseline (≥ 2 flags) |
|---|---|---|
| PR-AUC | 0.348 | 0.136 |
| ROC-AUC | 0.841 | 0.758 |
| Precision | 28.2% | 22.4% |
| Recall | 61.5% | 38.5% |
| F1 | 0.387 | 0.283 |
| False-positive rate | 7.0% | 6.0% |
| Share flagged | 9.4% | 7.4% |
| Brier | 0.033 | 0.050 |
| Confusion matrix (tn / fp / fn / tp) | 1611 / 122 / 30 / 48 | 1629 / 104 / 48 / 30 |
| Precision / recall at 8% capacity (top-k) | 31.3% / 57.7% | 20.8% / 38.5% |
| Expected cost (no review: $32,453) | $14,253 | $16,974 |

**Inference latency:** about 0.002 ms per row in batch, measured in the training run. That excludes database lookups.

**Reading the results honestly:**
- The 8% review cap held on validation. On the later test window the same threshold flagged 9.4%. Thresholds drift when traffic shifts, which is a reason to keep the policy in shadow mode and monitor the flag rate.
- Precision is modest (28%), and quiet-fraud payers are hard by construction.

### Serving
- **Artifact:** XGBoost's native JSON booster plus the Platt parameters a and b. Nothing is pickled.
- **Integrity checks at load:**
  - the booster file's SHA-256 must match its metadata
  - the feature names and feature version must match the serving code
- **Golden predictions:** `golden.json` holds five test rows. The serving code reproduces them exactly (`tests/test_risk_cases.py`).
- **Explanations:** exact TreeSHAP values from XGBoost's `pred_contribs`, in log-odds before calibration.
  - CI checks them against `shap.TreeExplainer` (`ml/tests`).
  - Calibration is monotonic, so direction and ranking carry over.
  - The UI says explanations describe the model, not the payer's intent.
- **When scoring runs:**
  - automatically after a capture (best effort; a scoring failure never affects the payment)
  - on demand by an analyst or admin
  - by `python -m app.cli demo-load`, which scores only the held-out test window, so demo scores are out-of-sample
- **Serving parity:**
  - Loading the scenario through the database path yields 170 HIGH assessments.
  - That equals the offline test tp + fp (48 + 122).
  - This is checked by `test_demo_load_matches_offline_evaluation`.
- **Policy:**
  - Bands map to ALLOW, REVIEW or ESCALATE in **shadow mode**. SENTINEL records what the policy would do and never blocks, captures or reverses a payment.
  - HIGH opens a review case.
- **Assessments on sandbox or simulated payments** carry an extra limitation: the model was trained on synthetic data, so the score demonstrates the pipeline and is not a validated risk estimate.

### Tests
**`ml/tests/test_pipeline.py`:**
- the scenario is deterministic
- features ignore future rows
- refunds count only when they happened earlier
- the split is chronological and disjoint
- dataset rows equal the serving feature function
- XGBoost contributions equal SHAP
- the committed artifact is reproducible

**`apps/api/tests/test_risk_cases.py`:**
- golden parity and SHAP additivity
- a tampered artifact is refused
- same-origin, past-only history in the database path
- shadow labelling
- role checks
- demo-load parity

## Track A: research benchmark (IEEE-CIS). Not started.
- **Data access:** needs Kaggle access and acceptance of the competition rules. The data will never be committed.
- **Planned method:**
  - its own feature set and a chronological split on `TransactionDT`
  - the same baseline-then-candidates method as Track B
- **Purpose:** to show the method on public data, not to score PayPal payments.
