# Reproducible private judge demonstration

Use an isolated DEMO merchant and securely retain `SENTINEL_JUDGE_PASSWORD`. After migrations, run from `apps/api`:

```bash
.venv/bin/python -m app.cli judge-demo --fresh
```

The command appends a daily SIMULATED scenario with catalog-linked products, twenty prior fixture payments and a new naturally HIGH-risk payment. It reuses the existing model; it refuses to force a HIGH score. The case receives a current relative deadline. Earlier synthetic payments, audit timestamps, investigations, evidence and overdue case records remain untouched. Same-day reruns are idempotent. The viewer password is not rotated.

Sign in privately as the configured judge viewer, then:

1. Open Command Center and inspect origin-separated totals. No simulated total is merchant revenue.
2. Open Demo guide, then the prepared payment. Read the frozen-model score and TreeSHAP explanation, with noncausal/synthetic limitations.
3. Open the case. Inspect cited records, deterministic or explicitly model-generated investigation, unverified illustrative attachment, downloadable private packet and pending independent approval.
4. Open Policy Lab. Change a threshold/capacity/cost assumption and compare baseline/proposed validation outcomes. This does not activate a policy or prove financial recovery.
5. Open Risk Monitoring. Select an origin/time window; inspect score/case distributions and reference-window limitations. Empty or insufficient samples must remain explicit.
6. Open Network Explorer. Inspect edges with actual payer-reference provenance and related records; relationships are not proof of fraud.
7. Open Refunds and Disputes. Viewer access is read-only. Demo refund requests are approval intent, never a simulated claim that money moved. Dispute response drafts/export remain preparation, not submission.
8. Read integration limitations. Administrators may inspect Operations; judge access is expected to return403.

A trusted operator can explicitly prepare a demo dispute/draft and a pending partial refund request on the newly created SIMULATED case through the existing domain services. Do not enable execution or synchronize real provider resources merely to populate a screenshot. Admin/analyst workflow demonstrations must use separately controlled private accounts and keep decisions independent.

The screenshot/test artifacts distinguish local UI behavior from genuine sandbox and hosted behavior. Do not describe a real AI or PayPal execution unless a separately authorized provider test actually completed.
