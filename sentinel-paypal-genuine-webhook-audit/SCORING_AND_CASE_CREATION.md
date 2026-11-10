# Scoring & Case Creation Audit

**Job Queue:** `apps/api/app/services/risk/jobs.py`  
**Scoring Pipeline:** `apps/api/app/services/risk/scoring.py`  
**Case Management:** `apps/api/app/services/cases.py`  
**ML Model:** Operational XGBoost Classifier (`operational-v1`, feature version `op-features-v1`)  

---

## 1. At-Least-Once Durable Scoring Jobs

When a capture webhook succeeds, it invokes `enqueue(db, txn.id)`:

```python
def enqueue(db: Session, transaction_id: uuid.UUID) -> None:
    db.execute(
        insert(RiskScoringJob)
        .values(transaction_id=transaction_id)
        .on_conflict_do_nothing(index_elements=["transaction_id"])
    )
```

### Durability & Concurrency Properties:
- `on_conflict_do_nothing` guarantees that duplicate webhook events or rapid repeated deliveries cannot create multiple competing scoring jobs for the same transaction.
- The worker claims jobs using `SELECT ... FOR UPDATE SKIP LOCKED LIMIT 1`.
- Claims assign a unique `lease_token` (UUID) and 2-minute expiration window.
- Retries are bounded to `MAX_ATTEMPTS = 5` with exponential backoff (`min(300, 5 * 2^attempts) seconds`).
- If 5 attempts fail, the job is dead-lettered (`status = 'DEAD', last_error = 'LeaseExhausted'`).

---

## 2. Feature Extraction & No-Leakage Guarantee

In [`apps/api/app/services/risk/scoring.py`](file:///c:/Users/ranja/Sentinel/SENTINEL-/apps/api/app/services/risk/scoring.py#L47-L76):
- `load_history` loads earlier transactions matching the merchant and data origin:
  `Transaction.occurred_at < txn.occurred_at`
  `Transaction.id != txn.id`
- This ensures absolute temporal separation: events that occurred after the transaction's capture time (such as subsequent refunds or disputes) are excluded from the feature snapshot.
- Features computed include:
  1. `cust_txn_count_1h`, `cust_txn_count_24h`, `cust_amount_24h_log`
  2. `hours_since_cust_prev`
  3. `cust_prior_txn_count_90d`
  4. `cust_prior_refund_count_90d`
  5. `cust_prior_dispute_count_90d`
  6. `amount_vs_merchant_median`
  7. `merchant_txn_count_1h`
  8. `amount_log`

---

## 3. XGBoost Inference & Risk Assessment

- The feature dictionary is evaluated by `model.predict([features])`.
- Returns calibrated probability, base value, and TreeSHAP feature contributions.
- Generates `RiskAssessment` record:
  - `risk_score`: Calibrated probability float (e.g. `0.2904`).
  - `risk_band`: `LOW`, `MEDIUM`, or `HIGH`.
  - `policy_decision`: `ALLOW` (for LOW), `REVIEW` (for MEDIUM), `ESCALATE` (for HIGH).
  - `policy_mode`: `"SHADOW"` (advisory only; never executes automatic financial holds or cancellations).
  - `feature_snapshot`: JSON dictionary of exact computed features.
  - `explanation`: Full TreeSHAP log-odds breakdown and human-readable feature labels.
  - `thresholds`: `{"medium": 0.0558, "high": 0.1036}`.

---

## 4. Conditional Case Creation

In `score_transaction`:
```python
if open_case_on_high and assessment.risk_band is RiskBand.HIGH:
    from app.services.cases import open_from_assessment
    open_from_assessment(db, txn, assessment)
```

### Case Creation Rules:
1. **High Risk Threshold Trigger:**
   If the calibrated risk score meets or exceeds `model.high_threshold` (`0.1036`), `open_from_assessment` creates an open `Case` in the review queue.
2. **Medium and Low Risk Handling:**
   Transactions with scores below `0.1036` record the `RiskAssessment` but do not generate an investigation case, keeping the analyst review queue focused strictly on high-priority cases.
3. **Audit Trail:**
   Inserts `audit_events` row with action `"case.opened"` and metadata linking `case_id`, `transaction_id`, and `assessment_id`.
4. **Zero Financial Mutation:**
   Case creation purely establishes an analyst task. It does NOT initiate a refund, void, chargeback, or hold on PayPal Sandbox.

---

## 5. Verification Status

All 14 unit and integration tests in `apps/api/tests/test_risk_cases.py` and `apps/api/tests/test_scoring_jobs.py` passed with 100% success.
