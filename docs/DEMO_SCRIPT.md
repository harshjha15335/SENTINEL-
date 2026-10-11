# Demo Script (draft, < 3 minutes)

Draft only; final timings after Phase 5. Every scene must use real behaviour; simulated scenes keep their on-screen label.

1. (0:00–0:20) Problem: suspicious payment → manual evidence hunt. Show Command Center with origin badges.
2. (0:20–0:50) Live sandbox checkout with PayPal buttons and a sandbox buyer; capture appears in Transactions with PayPal order and capture IDs. *(requires credentials)*
3. (0:50–1:10) Webhook arrives; transaction timeline shows "Status updated from verified webhook".
4. (1:10–1:40) Review queue: open a HIGH case on synthetic data.
   - Show the score, the "Model-generated" and "Shadow policy" labels, the SHAP drivers (e.g. prior refunds) and the limitations.
   - Then show the Risk Model page: model vs rules on held-out data, with the "synthetic data only" banner.
   - Setup: `python -m app.cli demo-load`. *(built)*
5. (1:40–2:20) Investigation Workbench: run the investigation (AI agent with credentials; otherwise the labelled deterministic summary), show cited findings and the tool trace, upload an invoice PDF, generate the evidence packet, request "Prepare refund". *(built; AI run needs credentials)*
6. (2:20–2:45) Admin approves the refund intent; execution record shows "no PayPal request was made" *(built)*. Backend refund execution with provider response *(Phase 5)*.
7. (2:45–2:58) Graph and policy lab glimpse; close on provenance principle.
