# ML Methodology (plan; nothing trained yet)

**Status: not started.** No model has been trained and no metric exists. The UI shows "Not scored".

## Two tracks
- **Track A – research benchmark (IEEE-CIS).** Its own feature set, chronological split on `TransactionDT`, rule baseline → logistic regression → XGBoost (LightGBM only if justified). Purpose: demonstrate method, not to score PayPal payments. Data downloaded via Kaggle API after accepting competition rules; never committed.
- **Track B – operational engine.** Features only from PayPal sandbox order/capture/event data, merchant records, or explicitly synthetic attributes (seeded generator, documented labels). If no credible model emerges, ship a rules + anomaly fallback with `score_origin = RULES`.

## Pipeline
ingest → schema validation → profiling → missing values → leakage audit → past-only rolling features → chronological train/validation/test → baselines → candidates → tuning on train/validation → calibration on validation → cost-sensitive threshold on validation → single untouched test evaluation → artifact + registry metadata (dataset hash, code version, metrics) → reproducible inference.

## Metrics to report
Precision, recall, F1, PR-AUC, ROC-AUC, confusion matrix, precision/recall at review capacity, FPR, Brier score, inference latency, expected decision cost under stated assumptions, class prevalence.

## Required tests
No target leakage; no future data in rolling windows; reproducible splits; consistent preprocessing; schema handling; missing-data inference; prediction range; artifact load; calibration/threshold use the validation split.

## Features we will not invent
Device or card fingerprints, IP reputation, identity data, PayPal-internal risk attributes. Unavailable data is marked unavailable.
