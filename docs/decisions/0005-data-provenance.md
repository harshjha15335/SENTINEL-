# 0005 · Data provenance is a column, not a convention

Status: accepted (2026-10-10)

Every transaction and payment event has `data_origin ∈ {LIVE_SANDBOX, MERCHANT_PROVIDED,
SYNTHETIC_DEMO, SIMULATED}`. It is set from the gateway that produced the record
(`gateway.data_origin`) or from webhook verification status, never from client input. Aggregates
are grouped by origin and currency; the UI renders an origin badge wherever a record appears.
Simulator webhook events are stored but never mutate `LIVE_SANDBOX` transactions.
