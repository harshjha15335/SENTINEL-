# SENTINEL reliability and next-phase completion report

Verified 6 November 2026. This is a local implementation and verification report, not a claim of continuous hosting, genuine PayPal delivery, real AI execution or production financial readiness.

## 1. Executive summary

The recovered application was extended in place on `feature/reliability-next-phase`, starting from `1866d384fb31451e09cd89a285d0d07429137afe`. The implementation commit is **`3ff7f88aabc6a97b519c767482ab3d5108d0cde1`**. Documentation follows in a separate delivery commit, whose exact SHA is recorded in the final response and `/workspace/sentinel-next-phase/delivery.json`.

New functionality includes a guarded full/partial refund ledger and sandbox executor, dispute preparation, validation-only Policy Lab, risk monitoring, bounded payer-reference network views, additional read-only investigation tools, and an append-only fresh judge scenario. Existing investigation/evidence/packet/approval code and the frozen model were retained.

The actual remote bridge remains blocked by proxy CONNECT denial. OAuth reaches the sandbox but returns `401 invalid_client`. Those problems were diagnosed, not hidden. Full local readiness stays503 because the required bridge is not healthy. No genuine payment, capture, refund, dispute submission, paid provisioning, push or merge was performed.

## 2. Critical error diagnosis

| Original issue | Verified cause / evidence | Change and current status |
|---|---|---|
| Supabase bridge ProxyError | Exact project host CONNECT fails with403 before upstream; authenticated Management API can read receiver metadata. Active environment metadata lists a wildcard, but exact-host requests are still denied. | Added credential-free host/purpose/stage/TLS/status diagnostics. Saved an exact-project hostname rule alongside existing certificate-host draft additions. Runtime activation remains external; bridge is truthfully DEGRADED. |
| Stale inbox / readiness503 | Last snapshot is older than its90-second freshness window; required bridge heartbeat does not satisfy health contract. | Retained freshness checks and503. Added separate last-successful-poll metadata; idle polling does not fabricate accepted work or fresh metrics. No hardcoded readiness bypass. |
| OAuth authentication | Fresh nonfinancial sandbox token request returns401 `invalid_client`. Official OAuth documentation was fetched; construction uses Basic authentication and client_credentials. | Credential pair/delivery binding remains invalid or unusable; the failing response cannot identify which credential is wrong. Token cache now respects short TTLs, rotation invalidates tokens, malformed responses fail safely, and untrusted error descriptions are not exposed. |
| Fixture status claimed OAuth success | Existing fixture gateway check returned success even though no provider authentication occurred. | `/paypal/status` now reports `not_attempted` in fixture mode and does not call a credential checker. Only sandbox authentication can report success. Regression test passed. |
| Certificate retrieval scope | Old URL check allowed approved hosts with unexpected userinfo/ports/paths. | Reject userinfo, non443 ports, query/fragment, noncertificate paths and encoded/traversal paths. Retrieval is bounded to64KiB and cache size128; TLS verification remains enabled. |
| Demo overdue / Unknown item | Old judge scenario had fixed historical dates and no mapped catalog product. | Explicit `judge-demo --fresh` appends a daily SIMULATED version with valid product links and current SLA. Earlier transactions, cases, evidence and audit timestamps are retained. |
| Build/test disruption | Repeated VFS Docker layers exhausted the32GiB workspace; the affected tests reported PostgreSQL DiskFull. | Pruned unused build caches/untagged unused images only, retained data/source/backups, consolidated runtime image assembly into one layer, rebuilt successfully and reran from a clean disposable test DB. |

The active receiver was read through the Management API as ACTIVE version4; it was not redeployed. Remote inbox SQL diagnostics returned400 and REST polling remains denied, so no fresh remote inbox count is claimed. A cached4 processed/2 DEAD SIMULATED count is historical evidence, not current provider verification.

## 3. Feature completion matrix

| Capability | Category | Verified scope / limit |
|---|---|---|
| Durable receipt, deduplication, leases, retry/terminal states and scoring | Implemented and tested | Existing architecture retained; local PostgreSQL RPC/FastAPI/model/case tests pass. |
| Event → case → investigation → evidence → packet → independent approval | Implemented and tested | One controlled local fixture test traverses the complete chain. No provider call occurs. |
| Full/partial refund requests, budget reservations and independent approval | Implemented and tested | Server amounts/currency, row locks, immutable snapshots and default-off gate; concurrent/timeout/reconciliation cases use mocked providers. |
| Sandbox refund execution/reconciliation adapter | Implemented, integration unverified | Explicit admin snapshot confirmation, stable request key, preflight capture checks and no automatic ambiguous resubmission. No actual refund was executed. Production environment refuses execution. |
| Dispute workspace, checklist, grounded draft and PDF export | Implemented and tested | Merchant-scoped local records, exact evidence references, private downloads; draft remains deterministic. |
| Read-only PayPal dispute sync | Implemented, integration unverified | First20 provider records only; exact single owned capture; ambiguous/unmatched mappings are skipped. Permissions and genuine results unverified. |
| Dispute external submission | Not implemented | Hard-disabled by endpoint; no enabling flag. Future approval of an exact outgoing payload would require separate work and authorization. |
| Real AI provider adapter and case tools | Implemented, integration unverified | Existing OpenAI/Anthropic PydanticAI adapter retained. New prior-only graph, stored dispute and shadow-policy tools are scoped/citation-bound. Scripted provider and deterministic tests pass; real AI test skipped. |
| Policy Lab | Implemented and tested | Actual validation predictions reconstructed from generator and frozen model, with digest/split checks. Confusion/ROC/PR/calibration/threshold/capacity/cost visualizations; draft history and independent shadow approval. No serving activation. |
| Risk monitoring | Implemented and tested | Merchant/origin/time-scoped volume, bands, cases, scores, model versions and fixed-bin score PSI. Inadequate/truncated samples remain unavailable; delayed-label calibration is not invented. |
| Relationship explorer | Implemented and tested | Bounded payments/payer/case graph, filterable and keyboard-accessible evidence inventory. No invented device, IP or card identity; no global cross-merchant graph. |
| Judge experience | Implemented and tested | New daily fixture, guide, catalog mapping, pending workflows and viewer-only access. Historical overdue cases remain intact. |
| Remote bridge recovery | Blocked by external dependency | Requires approved effective egress/proxy access to the project hostname and certificate hosts. |
| Genuine provider authentication / event delivery | Blocked by external dependency | Correct runtime credential/binding needed; genuine payment tests remain separately unauthorized. |
| Continuous public Python hosting | Blocked by external dependency | Prepared container/blueprint; no host account/current official quote/cost approval or public application URL verified. |
| Real AI execution | Blocked by external dependency | Supported provider/model/key and bounded inference authorization required; no costs incurred. |
| Live-money PayPal mode, hosted backups/PITR, full provider pagination, feature-level drift, shared rate limiter, durable AI task queue | Not implemented | Sandbox-only architecture remains; some items are intentionally disabled or require future infrastructure/engineering. |

Refund available balance is a **managed ledger estimate**, not an independently attested account-wide remaining balance. Unknown observed external refunds are blocked; unobserved external changes still require provider enforcement/reconciliation. An execution flag named `submission_started` means a durable submission may have begun, not proof PayPal received it. Financial history uses restrictive deletion foreign keys. Existing Phase4 intent executions still have `provider_called=false` and are not automatically promoted into executable refunds.

Policy comparison is baseline-versus-proposed validation behavior. Approval never changes the frozen serving model or threshold. Synthetic held-out metrics remain unchanged:1,811 payments,78 adverse,170 HIGH flags,48 true positives,122 false positives,30 false negatives,1,611 true negatives,28.2% precision and61.5% recall. No merchant accuracy or recovered-money claim follows from those values.

## 4. Files changed and architecture inventory

Primary implementation paths:

- `apps/api/app/models/{refunds,disputes,policy}.py`: new workflow persistence.
- `apps/api/app/services/{refunds,disputes,policy,monitoring,outbound}.py`: guarded workflows, validation inference, scoped analytics and safe diagnostics.
- `apps/api/app/api/v1/{refunds,disputes,policy,monitoring}.py`: authenticated routers and typed contracts.
- `apps/api/app/schemas/{refunds,disputes,policy,monitoring}.py`: validated request/response models.
- `apps/api/app/services/paypal/{sandbox,gateway,fixture}.py`: token safety, diagnostics and read-only refund lookup.
- `apps/api/app/services/{webhooks,inbox_bridge,worker_health}.py` and `workers/supabase_inbox.py`: certificate bounds, stable HTTP event trace and truthful poll metadata.
- `apps/api/app/services/investigation/{agent,toolbox,schemas,deterministic}.py`: real local graph/dispute/policy tool data with original grounding controls.
- `apps/api/app/services/demo/judge.py`, `api/v1/demo.py`, `cli.py`: additive fresh fixture and actual scenario metadata.
- `apps/api/alembic/versions/20261106_d105a4143283_refund_dispute_shadow_policy_workflows.py`: four new tables and immutable workflow/decision triggers; no rewrite of historical payment records.
- `apps/web/src/features/{refunds,disputes,policy,monitoring,network}/`: functional API-connected screens.
- `apps/web/src/features/{operations,cases,investigation}/`, `app/App.tsx`, `components/layout/AppShell.tsx`: navigation, case links, provider/poll status and citation labels.
- `apps/api/tests/`, `apps/web/src/features/*/*.test.tsx`, `apps/web/e2e/next-phase.spec.ts`: service/security/ML-integrity/workflow/responsive regression coverage.
- `Dockerfile`, `.env.example`, `deploy/render-continuous.yaml`, `packages/contracts/openapi.{json,ts}`: reviewed deployment, flags and generated API types.

The implementation commit contains72 changed files; exact paths are available through `git show --name-only 3ff7f88` and the delivery manifest. Setup/runbook/demo/architecture/report documents follow in the documentation commit.

[Architecture and persistence boundaries](NEXT_PHASE_ARCHITECTURE.md) document the exact component path. Liveness, readiness, provider configuration, worker health and inbox observation time remain separate facts. Existing event/provider IDs and linked transaction/case/job/run/packet IDs allow durable tracing. A stable event-ID hash is also propagated as X-Correlation-ID across bridge/API retries without rewriting signed bytes or headers.

## 5. Test results and revision

Fresh baseline was run from an immutable archive of1866d38 against a dedicated `sentinel_baseline_test` database: backend134 passed/1 real-AI skip, ML7, frontend29, strict types/lint/build passed. No concurrent feature edit contaminated that baseline.

Final implementation3ff7f88 results:

| Command / check | Actual result |
|---|---|
| API `pytest`, dedicated `sentinel_nextphase_test` | **190 passed, 1 real-AI skip** |
| API `ruff check app tests alembic` | Passed |
| API `ruff format --check app tests alembic` | Passed |
| API strict `mypy app` | Passed,102 application source files |
| Existing ML `pytest ml/tests` from immutable baseline; served artifact digests compared | **7 passed**, artifacts unchanged afterward |
| Web `npm run typecheck`, `npm run lint`, `npm run build` | Passed |
| Web `npm test` | **39 passed**,13 files |
| Browser `playwright test`, desktop/mobile with axe, actual API | **14 passed** in stable final run |
| Supabase tests with dedicated local SQL URL | **12 passed** |
| Deno receiver tests | **11 passed** |
| New migration upgrade/parent downgrade/upgrade + `alembic check` | Passed on disposable DB; no model drift |
| Docker build and nonroot smoke | Passed; UID10001; readiness health check; API/UI/session/pipeline and read-only new routes available |
| Image/source SHA comparison | Application Python/JSON source matches checkout |
| Full supervisor restart | Sessions and private evidence/packet SHA-256 retained; API/pipeline recover, bridge remains truthfully blocked |
| Actual runtime financial gate and draft export | Execution false; fixture OAuth not_attempted; authorized dispute-draft PDF200 |
| Local backup restore | Business rows, all stored blobs and refund/policy snapshots compared in a separate database; see backup-restore.json |
| Known private-literal source/build audit | No matches;367 files scanned before implementation commit |

Initial integration failures were investigated: old tool availability/prompt-version assertions were updated for actual new read-only tools; one new test used a nonexistent audit attribute and was corrected. Browser accessibility found unfocusable scrollable regions and those were fixed. A disk-full run was invalidated, caches cleaned and the complete suite rerun. One browser run overlapped an intentional API restart and was discarded; the final stable run was separate. These failed/interrupted logs are retained rather than disguised as passes.

The single skipped test is real-AI integration. Actual sandbox OAuth failed401 and is not included as a passing mock assertion. Actual hosted inbox delivery is not reverified while REST is proxy-blocked.

## 6. Deployment and integration status

- **Local:** the recovered API/frontend and application DB run on the new migration `d105a4143283`. Pipeline is healthy. Sessions and existing/new private packets remain accessible.
- **Current readiness:**503, because required Supabase communication is denied before upstream. Database/schema and pipeline checks remain separately OK.
- **Hosted receiver:** Management API reports ACTIVE version4 at `https://cfslzvvdjxstpupkqbpw.supabase.co/functions/v1/paypal-webhook`. No receiver redeployment or remote production modification occurred. Direct external reachability and fresh inbox contents are not asserted from blocked requests.
- **Hosted full application:** no verified public Python URL. The review-only Render proposal follows the new branch and reviewed migration but has not been applied. Current pricing/account resources were not verified; no billable resource was created.
- **Sandbox verified:** only a nonfinancial OAuth failure is established. No genuine payment/event/refund/dispute success.
- **Production verified:** none. Live-money mode remains absent; production environment refuses refund execution.
- **AI:** provider adapter and controlled tests work; no real provider execution or inference charge occurred.

The image and exact container-source manifest are in `container-smoke.json` and `container-source-hashes.json`. Direct dependencies are pinned, but full transitive/base-image byte-for-byte reproducibility and dependency vulnerability scanning are not claimed.

## 7. Security verification

Tests cover role/CSRF/session enforcement, tenant isolation, fixture/genuine separation, required-worker failures, duplicate and lost-response handling, crash/lease recovery, durable jobs, certificate URL rejection, bounded retrieval, token expiry/rotation, safe error text, prompt injection/citation validation, evidence upload/download boundaries and snapshot/decision immutability.

New refund cases include full/partial budgets, concurrent requests/execution, independent decisions, default and production gates, provider capture mismatch, external partial-refund uncertainty, ambiguous timeouts and read-only reconciliation. A model flag or approval alone cannot call the executor. The AI has no financial or external submission tool.

Global inbox totals remain restricted to the explicitly configured installation operator merchant. Ordinary viewers/analysts are denied operations. Policy, dispute, monitoring and network queries enforce merchant scope; simulation uses shipped synthetic validation data, not another tenant's records.

Unresolved risks/limits: per-process login limiter, no antivirus/OCR guarantee, in-process investigation jobs with stale-run recovery rather than a durable AI queue, incomplete provider pagination/permission verification, managed ledger uncertainty for unobserved external refunds, and unverified hosted proxy/TLS/backup configuration. No formal penetration test or vulnerability-scan pass is claimed.

## 8. Remaining actions

1. Independently export/verify the final bundle and private backup through an approved off-environment destination. Local copies are not verified durable external storage.
2. Review/save and publish the saved exact-project/certificate-host network configuration. If project-host CONNECT still fails despite its exact rule, have the environment administrator inspect proxy scope/enforcement. Preserve TLS and signature validation.
3. Correct the paired sandbox runtime credentials or supported delivery binding in secure settings; repeat only nonfinancial OAuth first. Do not request values in chat or treat configured names as authenticated success.
4. Provide a supported AI provider/model/key and explicit bounded inference authorization before real-AI testing.
5. Supply hosting access, obtain a current official regional quote and explicit cost approval, then authorize source publication/delivery and deployment. Verify public HTTPS, proxy trust, secure cookies, worker supervision, private persistence and managed backup restoration.
6. Keep genuine payment/refund/dispute submission tests separately unauthorized until explicitly requested. Extend full dispute pagination, account-wide refund reconciliation and any future external submission approval payload before financial release.

[Exact environment names](NEXT_PHASE_SETUP.md) and [deployment/rollback/backup procedures](NEXT_PHASE_RUNBOOK.md) are provided separately. No secret values are included.

## 9. Demo walkthrough

The private viewer account uses the existing securely stored judge password. From the prepared application, sign in and open `/demo`.

1. Inspect Command Center; keep SYNTHETIC_DEMO and SIMULATED totals separate from genuine provider activity.
2. Follow the prepared fresh payment and inspect the mapped catalog item, frozen-model risk score and TreeSHAP limitations.
3. Open the case, current deadline, actual record citations, explicitly deterministic investigation, unverified fixture attachment, private packet and pending independent approval.
4. Use `/policy` for validation-only what-if controls, cost assumptions, curves/confusion/capacity and shadow proposal history. Nothing activates.
5. Open `/monitoring` and `/network`; use origin/window/risk filters and inspect the explanation behind each bounded relationship.
6. Open `/refunds` and `/disputes`; the prepared rows are a PENDING_APPROVAL refund with submission_started=false, a labelled local dispute/draft and a DRAFT shadow proposal. Viewer write/approve/execute controls are absent and server authorization remains enforced.
7. Administrators can inspect `/operations`, including the real degraded bridge and stale snapshot. Viewer operations access correctly returns403.

`python -m app.cli judge-demo --fresh` safely appends the current daily scenario and is idempotent on repeat. It does not overwrite earlier dates, force a HIGH result or create a PayPal operation. [Demo setup and boundaries](NEXT_PHASE_DEMO.md) provide reproduction details. New module screenshot evidence is captured from actual desktop/mobile API-connected views, not decorative mocks.

## 10. Git, recovery and evidence

Base ref: `backup/next-phase-base-20261106` at1866d38. Implementation:3ff7f88 on `feature/reliability-next-phase`. Final documentation SHA, new completion backup, bundle path/SHA-256 and original-checkout state are recorded in `/workspace/sentinel-next-phase/delivery.json` after preservation completes. Existing Session8/recovery branches and bundles remain intact. No reset, force-push, merge or remote publication occurred.

The original checkout remains at public main `aed5d5647d14b2f7fd29575b21487ead337c64b3`; only dedicated local backup refs are added. The recovered checkout's origin is the other local clone, not GitHub, so local remote refs are not publication evidence.

Evidence directory: `/workspace/sentinel-next-phase/`. Key files: baseline/BASELINE_REPORT.json, backend-final.log, web-tests.log, browser-release.log, migration-final.log, container-smoke.json, runtime-verification.json, financial-gate-and-draft-export.json, connectivity-initial.json, oauth-current.json, receiver-management-status.json, backup-restore.json and secret-audit.json. Private env files, database dumps and browser authentication traces are not public report attachments.

The deployment milestone is not complete while external connectivity/hosting/provider prerequisites remain unresolved. This delivery preserves a tested local implementation and an exact record of those limits.
