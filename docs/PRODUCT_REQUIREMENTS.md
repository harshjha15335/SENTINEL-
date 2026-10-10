# Product Requirements

## Problem
Merchants using PayPal see suspicious payments and disputes in separate places and assemble
evidence by hand. Fraud dashboards flag; they rarely explain, link, gather evidence or record
what the merchant decided and why.

## Product
SENTINEL is a decision-support and workflow system for PayPal merchants: it ingests genuine
PayPal payment events, assesses risk with explainable models, investigates with grounded AI tools,
prepares evidence, recommends an action, and records the merchant's approved decision. It never
acts autonomously on money.

## Users and roles
- **ADMIN**: configures policy, manages users, sees the audit log, approves financial actions.
- **ANALYST**: works cases, runs investigations, requests actions, creates sandbox orders.
- **VIEWER**: read-only.

## Hackathon constraints (verified on the official rules page, 2026-10-10)
Deadline 2026-11-12 12:00 PT. PayPal integration must be central; AI must be functional; working
hosted demo or reproducible setup; public repo with a visible OSI licence; YouTube video under 3
minutes. Five equally weighted criteria: technology, design, impact, idea, presentation.

## MVP scope (must ship)
1. Real sandbox checkout: create → buyer approval (PayPal v6 buttons) → capture → persisted with PayPal IDs. **(built; awaiting credentials for a live run)**
2. Verified webhooks updating transactions idempotently. **(built)**
3. Transaction workspace and Command Center with provenance on every figure. **(built)**
4. Risk assessment with genuine model, SHAP explanation and limitations. (Phase 3)
5. Investigation agent producing schema-validated, cited findings from read-only tools. (Phase 4)
6. Approval workflow; refund executed only by backend after approval, idempotent. (Phase 4/5)
7. Fraud network view with per-edge provenance; dispute workspace using real API where permitted, labelled simulation otherwise; policy lab in shadow mode. (Phase 5)

## Non-goals
Live PayPal mode; autonomous refunds; Neo4j/Kafka/Kubernetes; GNNs; claims of production fraud accuracy.

## Data provenance labels (shown in UI)
LIVE SANDBOX · MERCHANT PROVIDED · SYNTHETIC DEMO · SIMULATED · (model output is labelled as model-generated assessment when Phase 3 lands).
