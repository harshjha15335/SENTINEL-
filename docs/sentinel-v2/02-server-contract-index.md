# Server contract index (source-derived, baseline 410109c)

All paths are below `/api/v1`. Source/default dependencies are recorded, not inferred from marketing. Generated OpenAPI remains canonical for field validation.

| Method | Path | Handler | Dependency / authorization reference | Response annotation |
|---|---|---|---|---|
| GET | `/audit` | `apps/api/app/api/v1/audit.py:15` `list_audit` | Depends(admin_only), Depends(get_db) | `Page[AuditOut]` |
| POST | `/auth/login` | `apps/api/app/api/v1/auth.py:26` `login` | Depends(get_db) | `SessionOut` |
| POST | `/auth/logout` | `apps/api/app/api/v1/auth.py:88` `logout` | Depends(current_principal), Depends(get_db) | `Response` |
| GET | `/me` | `apps/api/app/api/v1/auth.py:111` `me` | Depends(any_member) | `MeOut` |
| GET | `/cases` | `apps/api/app/api/v1/cases.py:63` `list_` | Depends(any_member), Depends(get_db) | `Page[CaseOut]` |
| POST | `/cases` | `apps/api/app/api/v1/cases.py:89` `open_` | Depends(operator), Depends(get_db) | `CaseDetailOut` |
| GET | `/cases/{case_id}` | `apps/api/app/api/v1/cases.py:99` `detail` | Depends(any_member), Depends(get_db) | `CaseDetailOut` |
| POST | `/cases/{case_id}/claim` | `apps/api/app/api/v1/cases.py:108` `claim` | Depends(operator), Depends(get_db) | `CaseDetailOut` |
| POST | `/cases/{case_id}/notes` | `apps/api/app/api/v1/cases.py:117` `note` | Depends(operator), Depends(get_db) | `CaseNoteOut` |
| POST | `/cases/{case_id}/resolve` | `apps/api/app/api/v1/cases.py:127` `resolve` | Depends(operator), Depends(get_db) | `CaseDetailOut` |
| GET | `/products` | `apps/api/app/api/v1/catalog.py:14` `list_products` | Depends(any_member), Depends(get_db) | `list[ProductOut]` |
| GET | `/dashboard/summary` | `apps/api/app/api/v1/dashboard.py:17` `summary` | Depends(any_member), Depends(get_db) | `DashboardSummaryOut` |
| GET | `/demo/scenario` | `apps/api/app/api/v1/demo.py:32` `scenario` | Depends(any_member), Depends(get_db) | `JudgeScenarioOut` |
| GET | `/disputes` | `apps/api/app/api/v1/disputes.py:34` `list_disputes` | Depends(any_member), Depends(get_db) | `list[DisputeOut]` |
| POST | `/disputes/demo` | `apps/api/app/api/v1/disputes.py:51` `create_demo` | Depends(operator), Depends(get_db) | `DisputeOut` |
| POST | `/disputes/sync` | `apps/api/app/api/v1/disputes.py:60` `synchronize` | Depends(admin_only), Depends(paypal_gateway), Depends(get_db) | `DisputeSyncOut` |
| GET | `/disputes/{identity}` | `apps/api/app/api/v1/disputes.py:69` `detail` | Depends(any_member), Depends(get_db) | `DisputeDetailOut` |
| POST | `/disputes/{identity}/drafts` | `apps/api/app/api/v1/disputes.py:97` `create_draft` | Depends(operator), Depends(get_db) | `DisputeDraftOut` |
| POST | `/disputes/{identity}/assign` | `apps/api/app/api/v1/disputes.py:106` `assign` | Depends(operator), Depends(get_db) | `DisputeOut` |
| GET | `/disputes/{identity}/drafts/{draft_id}/download` | `apps/api/app/api/v1/disputes.py:116` `download_draft` | Depends(any_member), Depends(get_db) | `Response` |
| POST | `/disputes/{identity}/submit` | `apps/api/app/api/v1/disputes.py:159` `disabled_submission` | Depends(admin_only), Depends(get_db) | `None` |
| GET | `/health` | `apps/api/app/api/v1/health.py:12` `health` | Inspect handler / signature verification | `dict[str, str]` |
| GET | `/ready` | `apps/api/app/api/v1/health.py:17` `ready` | Depends(get_db) | `JSONResponse` |
| GET | `/cases/{case_id}/ai/status` | `apps/api/app/api/v1/investigations.py:126` `ai_status` | Depends(any_member) | `AIStatusOut` |
| GET | `/monitoring/risk` | `apps/api/app/api/v1/monitoring.py:28` `risk_monitoring` | Depends(any_member), Depends(get_db) | `MonitoringOut` |
| GET | `/network` | `apps/api/app/api/v1/monitoring.py:44` `relationship_network` | Depends(any_member), Depends(get_db) | `NetworkOut` |
| GET | `/operations/webhooks` | `apps/api/app/api/v1/operations.py:50` `webhook_operations` | Depends(admin_only), Depends(get_db) | `OperationsOut` |
| GET | `/paypal/status` | `apps/api/app/api/v1/paypal.py:24` `status` | Depends(any_member) | `PayPalStatusOut` |
| POST | `/paypal/orders` | `apps/api/app/api/v1/paypal.py:56` `create_order` | Depends(operator), Depends(paypal_gateway), Depends(get_db) | `OrderCreatedOut` |
| POST | `/paypal/orders/{order_id}/capture` | `apps/api/app/api/v1/paypal.py:83` `capture_order` | Depends(operator), Depends(paypal_gateway), Depends(get_db) | `TransactionOut` |
| GET | `/policy-lab/simulate` | `apps/api/app/api/v1/policy.py:26` `simulate` | Depends(any_member) | `PolicySimulationOut` |
| GET | `/policy-lab/drafts` | `apps/api/app/api/v1/policy.py:33` `drafts` | Depends(any_member), Depends(get_db) | `list[PolicyDraft]` |
| POST | `/policy-lab/drafts` | `apps/api/app/api/v1/policy.py:47` `create` | Depends(operator), Depends(get_db) | `PolicyDraft` |
| POST | `/policy-lab/drafts/{ident}/submit` | `apps/api/app/api/v1/policy.py:58` `submit` | Depends(operator), Depends(get_db) | `PolicyDraft` |
| POST | `/policy-lab/drafts/{ident}/decide` | `apps/api/app/api/v1/policy.py:65` `decide` | Depends(admin_only), Depends(get_db) | `PolicyDraft` |
| GET | `/refunds` | `apps/api/app/api/v1/refunds.py:31` `list_refunds` | Depends(any_member), Depends(get_db) | `list[RefundOut]` |
| GET | `/transactions/{transaction_id}/refunds` | `apps/api/app/api/v1/refunds.py:45` `history` | Depends(any_member), Depends(get_db) | `RefundHistoryOut` |
| POST | `/cases/{case_id}/refunds` | `apps/api/app/api/v1/refunds.py:75` `request_refund` | Depends(operator), Depends(get_db) | `RefundOut` |
| GET | `/refunds/{refund_id}` | `apps/api/app/api/v1/refunds.py:85` `get_refund` | Depends(any_member), Depends(get_db) | `RefundOut` |
| POST | `/refunds/{refund_id}/decision` | `apps/api/app/api/v1/refunds.py:96` `decide_refund` | Depends(admin_only), Depends(get_db) | `RefundOut` |
| POST | `/refunds/{refund_id}/execute` | `apps/api/app/api/v1/refunds.py:110` `execute_refund` | Depends(admin_only), Depends(paypal_gateway), Depends(get_db) | `RefundOut` |
| POST | `/refunds/{refund_id}/reconcile` | `apps/api/app/api/v1/refunds.py:124` `reconcile_refund` | Depends(admin_only), Depends(paypal_gateway), Depends(get_db) | `RefundOut` |
| GET | `/risk/model` | `apps/api/app/api/v1/risk.py:19` `model_card` | Depends(any_member) | `ModelCardOut` |
| GET | `/transactions/{transaction_id}/risk` | `apps/api/app/api/v1/risk.py:72` `latest` | Depends(any_member), Depends(get_db) | `RiskAssessmentOut` |
| POST | `/transactions/{transaction_id}/risk` | `apps/api/app/api/v1/risk.py:85` `rescore` | Depends(operator), Depends(get_db) | `RiskAssessmentOut` |
| GET | `/transactions` | `apps/api/app/api/v1/transactions.py:17` `list_` | Depends(any_member), Depends(get_db) | `Page[TransactionOut]` |
| GET | `/transactions/{transaction_id}` | `apps/api/app/api/v1/transactions.py:41` `detail` | Depends(any_member), Depends(get_db) | `TransactionDetailOut` |
| POST | `/webhooks/paypal` | `apps/api/app/api/v1/webhooks.py:38` `paypal_webhook` | Depends(get_db), Depends(get_verifier) | `JSONResponse` |
| POST | `/webhooks/fixtures/paypal` | `apps/api/app/api/v1/webhooks.py:96` `fixture_webhook` | Depends(get_db) | `JSONResponse` |
