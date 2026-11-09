# SENTINEL — Final integration recovery and release verification

Verified 6 November 2026. This is a local release verification report. SENTINEL is **not production-ready**: the genuine Supabase bridge is blocked, sandbox OAuth fails, no real AI inference is verified, and no continuous public Python deployment exists.

## A. Executive summary

The existing recovered project was inspected and extended in place on feature/reliability-next-phase. Starting commit: 396e998283e3616f410d0ef8f9c472c799ad70f9. Release implementation commit: 1bc15e7155362e0561a953ca676690eef0ea8cdc. Final documentation commit and bundle checksum are recorded in the adjacent delivery.json outside the checkout, avoiding a self-referential commit hash in this tracked report.

Four focused fixes were completed:

- PayPal environment inputs now remove outer copy/paste whitespace and reject empty or embedded-whitespace credentials at startup and gateway construction/rotation. Credentials are normalized before HTTP Basic encoding; no values or tokens are logged. A real nonfinancial OAuth retry still returns 401 invalid_client, so this is a handling fix, not successful authentication.
- Failed LLM investigations now retain denied mutation/unknown-tool attempts in their stored audit trail after timeout, budget exhaustion, invalid output or provider rejection. Arguments remain omitted and provider error bodies remain private.
- Repeated bootstrap now preserves existing passwords. Explicit seed --rotate-passwords is required to replace them and revokes existing sessions. Existing merchant/role collisions are refused. No actual administrator password was rotated in this session.
- Destructive API tests now validate a loopback database name ending in _test before migration downgrade or truncation. The deployment proposal removes permanent seed-password variables, requires explicit trusted proxy configuration and declares one instance. Controlled replacement is required because rollout overlap can contend for the singleton worker lock.

The model, thresholds, existing features, recovery history and application database were preserved. No genuine payment, order creation, capture, refund, dispute submission, paid AI request, paid provisioning, source push or merge occurred. Browser checkout tests used the explicitly SIMULATED fixture gateway.

## B. Root-cause analysis

| Component | Current state / exact error | Evidence-supported cause | Required correction |
| --- | --- | --- | --- |
| Supabase receiver | Management API 200; ACTIVE version 4 | Receiver is deployed. Original index.ts and receiver.ts embedded in its ESZIP source maps match local source after line-ending/outer-whitespace normalization. | No redeploy needed based on source compatibility. Verify actual delivery only after the bridge and provider are usable. |
| Supabase bridge | ProxyError; CONNECT 403 before upstream | Request to cfslzvvdjxstpupkqbpw.supabase.co is rejected during proxy CONNECT. Current enforced metadata lists *.supabase.co; the saved draft additionally lists the exact project host. This is not a Supabase API-key 403. | Review/save/publish the existing exact-host network draft, then retry. If denied afterward, platform administrator must inspect proxy enforcement and destination scope for HTTPS443 and /rest/v1/rpc/. |
| PayPal OAuth | Provider HTTP401 AUTHENTICATION, issue invalid_client | Standard sandbox client_credentials + HTTP Basic request reaches PayPal. Outer whitespace existed and was corrected in code, but the retry remains rejected. The submitted credential pair/delivery binding is not accepted; which credential or binding is wrong is not proven. | Securely supply the paired credentials from the same sandbox REST app through supported raw process-environment delivery, or correct the platform's supported encoded-Basic credential binding. Restart/rotate, then repeat token-only authentication. Never extract proxy-held credentials. |
| Backend API | /api/v1/health200; /api/v1/ready503 | Database/schema and pipeline are healthy; required genuine-origin bridge is not ready. | Keep truthful503 until bridge polling is healthy. Do not disable dependency checks. |
| PostgreSQL | Current schema d105a4143283 | Local application database responds; isolated migration and restore checks pass. | Hosted database TLS, retention, capacity and backups remain to be verified. |
| Workers | Pipeline healthy; bridge degraded | Bridge process existence does not imply successful polling. No fresh remote inbox snapshot is available. | Require fresh successful-poll timestamps and durable acceptance before acknowledging events. |
| AI | No supported provider/key/model configured | SENTINEL_INVESTIGATION_MODEL is present but does not configure the current adapter. Actual names are SENTINEL_AI_PROVIDER, SENTINEL_AI_MODEL and SENTINEL_AI_API_KEY. | Choose a supported provider/model, bind its key securely and approve bounded API usage before a real run. |
| Hosting | No verified public Python URL | No authorized hosting account or reviewed current cost quote was available. | Review the concrete proposal and provider quote, authorize cost/source publication separately, then test public endpoints. |

Local DNS lookup also failed, but proxy-routed requests use proxy-side resolution; that observation does not establish that the public project hostname is nonexistent or explain the proxy's exact internal policy decision. TLS and inherited proxy settings remain enabled. The exact project hostname and approved PayPal certificate hosts are already in a saved configuration draft; saving is not activation.

The deployed receiver is returned as ESZIP2.3, so raw TypeScript bytes are not embedded as plain modules. Parsing the bundle's original-source maps establishes source compatibility for both modules. Different transpiler formatting makes a raw generated-token comparison unsuitable for receiver.ts. Compatibility does not establish current secret values, provider authentication or genuine delivery.

## C. Integration verification

| Service / lifecycle | Verification level | Practical limit |
| --- | --- | --- |
| Application PostgreSQL | Local connectivity, schema, migration roundtrip and restore verified | No managed backup/PITR or hosted database verified. |
| Supabase receiver management | Authenticated management reads; active version and deployed source compatibility verified | Management access is separate from project REST/inbox access. |
| Supabase project inbox | Blocked at proxy CONNECT | No fresh contents, remote lease recovery or genuine-origin drain claimed. Historical cached aggregates are not current evidence. |
| Bridge/FastAPI lifecycle | Full controlled local PostgreSQL/RPC/HTTP fixture suite passed | Fixture signatures are deliberately separate from genuine PayPal cryptographic provenance. |
| PayPal sandbox OAuth | Real token-only request attempted; 401 invalid_client | Not sandbox-authenticated. Financial calls: zero. |
| AI investigation | Scripted provider and supported SDK construction tested offline; deterministic fallback works | No real provider request; one credential-gated integration test skipped. |
| Public application | Not deployed/verified | Local URLs and Docker manifests are not continuous hosting. |

Controlled fixtures cover receipt, durable inbox, lease claim/renewal, unchanged body/header forwarding, durable API acceptance, deduplication, reconciliation, risk assessment, SHAP, HIGH-risk case, deterministic investigation, evidence, PDF packet and independent approval. Duplicate delivery, response loss after API commit, worker-crash/reclaim, stale acknowledgements, lease expiry, API unavailability, invalid fixture signatures and out-of-order events are covered. Financial provenance stays SIMULATED; production forwarding claims genuine-origin receipts only.

The lifecycle can be followed using provider event ID, its bounded correlation hash, payment event, transaction, scoring job, case, investigation, evidence packet and approval identifiers. Genuine-event timestamps/identifiers cannot be invented while remote delivery remains unverified.

## D. Deployment status

Recommended initial architecture: one same-origin Docker web service for React/FastAPI plus supervised pipeline and bridge, with separate persistent PostgreSQL and database-backed private evidence. Keep the existing Supabase receiver/inbox. Supabase Edge Functions do not host the Python/XGBoost workers.

The concrete review-only manifest is deploy/render-continuous.yaml: Docker web service, proposed Starter plan, one instance, Singapore, managed PostgreSQL proposed basic-256mb, readiness health check, automatic deployment disabled, pinned migration d105a4143283, production security settings and private server-side secret inputs. Those plan names, capacity and current prices require provider validation; no monthly cost is asserted or approved. No billable resource was created.

See docs/FINAL_DEPLOYMENT.md for Render/Railway/Vercel comparisons. Railway is an alternative for the same continuous container/database; Vercel can host a frontend but cannot replace these continuous Python workers. A split frontend requires tested same-origin proxy/cookie/CSRF routing; CORS alone is insufficient. No platform migration was performed.

A single desired replica does not prevent an overlapping rollout. The pipeline holds a singleton advisory lock, and readiness uses shared worker heartbeats. Require a controlled stop-old/start-new maintenance window until worker ownership/handoff is redesigned and tested for overlap. Horizontal scaling and seamless zero-downtime rollout are not claimed.

Container e669c783a4a7e76ea944566820242e78f3deb980ac575a6bf20e6b870e6126ce built successfully. All 105 application Python/JSON source files matched the image. Its isolated smoke test verified non-root UID10001, UI/session/module routes, schema, pipeline and disabled fixture ingress. That isolated fixture image intentionally omitted Supabase and did not enable required-worker readiness; its200 is not evidence that the real bridge is ready. The actual recovered runtime still has required-worker readiness enabled and returns503.

## E. Feature validation

| Module | Current verified behavior | Remaining limit |
| --- | --- | --- |
| Command Center / transactions | Origin-separated totals, transaction detail, authenticated routes, responsive views | Displayed demo money is synthetic, not provider proceeds. |
| Frozen model / SHAP | Serving parity, chronological leakage protections, reproducibility tests and unchanged artifacts | Benchmark precision 28.2% means 122 of 170 HIGH flags were false positives in that synthetic test window; no merchant accuracy claim. |
| Review / investigation | Automatic HIGH cases, grounded structured output, case-scoped read-only tools, citations, fallback and failed-run denied-tool audit | Real AI unavailable; no fraud-intent conclusion from risk alone. |
| Evidence / packets / approvals | Private authenticated downloads, hashes, persistence, independent decisions and immutable snapshots | Human-supplied proof remains unverified; no provider submission. |
| Refunds | Full/partial amounts, reservations, independent approval, idempotency, merchant checks and ambiguous-outcome reconciliation | Execution defaults off and production refuses it. Ledger balance cannot establish unseen external refunds. No genuine refund tested. |
| Disputes | Owned-case association, evidence references, grounded draft, missing proof/deadlines and private PDF preparation | Read-only provider sync permissions/results unverified; first20 records; external submission hard-disabled. |
| Policy Lab | Frozen-model validation-only simulation, confusion/precision/recall, capacity/cost assumptions, ROC/PR/calibration and shadow drafts | No held-out test tuning and no serving-policy activation. Recovery/cost assumptions are illustrative. |
| Monitoring | Merchant/origin/window-scoped distributions, queues, freshness and bounded PSI | Insufficient/truncated samples remain unavailable; no invented outcome calibration without reliable labels. |
| Network | Bounded actual payer/payment/case links, provenance/filtering and case navigation | No invented device/card/IP links or cross-merchant graph. Large production-scale load testing remains unverified. |
| Operations / judge | Actual degraded worker state, protected operator metrics, isolated synthetic guide and viewer write denial | Judge-accessible public deployment absent. |

The append-only prepared scenario was retained rather than rewriting historical audit dates. Read-only judge routes were inspected at desktop 1440x900 and Pixel 7 sizes. Investigation, evidence and approvals are panels inside the case workbench, not separate nonexistent routes. Administrator Operations and simulated checkout were exercised by their authorized existing browser tests.

## F. Automated tests

| Suite / command | Current result | Evidence under /workspace/sentinel-final-release |
| --- | --- | --- |
| API: dedicated-loopback-_test URL plus .venv/bin/pytest | 213 passed, 0 failed, 1 skipped | backend-final.log |
| Frontend: npm test | 39 passed across13 files | web-tests.log |
| Browser: npx playwright test --workers=1 | 16 passed, 0 failed/skipped; desktop/mobile, axe and overflow checks | browser-tests.log |
| ML: PYTHONPATH=apps/api:ml apps/api/.venv/bin/pytest ml/tests | 7 passed | ml-tests.log |
| Supabase: dedicated SENTINEL_SUPABASE_TEST_DATABASE_URL plus pytest supabase/tests | 12 passed, no skip | supabase-tests.log |
| Receiver: Deno test supabase/functions/paypal-webhook | 11 passed, 0 failed | receiver-tests.log |
| Deployment proposal: pytest deploy/tests | 2 passed | deployment-tests.log |
| Supplemental AI/evidence outage regressions | 26 passed; included in final 213 | operational-supplement.log |
| Backend Ruff, formatting, mypy | Passed;102 source files typed | ruff-final.log, format-final.log, mypy-final.log |
| Web types, ESLint, production build | Passed | web-types-final.log, web-lint-final.log, web-build.log |
| Disposable Alembic upgrade, parent downgrade, upgrade, check | Passed; no new upgrade operations | migrations.log |
| Contracts generation / Git diff check | Passed; generated contracts unchanged | contracts.log |
| Current container/source smoke | Passed | container-smoke.json, container-source-hashes.json |
| Backup restore and isolated PostgreSQL restart | Passed; all 30 blob hashes and recorded counts match | backup-restore.json |
| Application supervisor restart | Sessions and private evidence/packet hashes preserved; pipeline recovered; readiness stayed503 | runtime-verification.json |
| Known runtime literal secret scan | Passed across374 source/new/build files before documentation commit | security-check.json |

The single skipped test is real-provider AI investigation: supported provider credentials/model and authorized spend were unavailable. Genuine payment/capture/refund/dispute tests were not executed because separate authorization was explicitly required. Remote Supabase end-to-end verification is blocked by CONNECT403; public hosting/TLS/judge tests are blocked by absent deployment. These are unverified acceptance items, not passing tests.

The existing ML reproducibility test fits only to a temporary test path; no serving artifact was retrained, replaced or tuned. Git confirms both ml/ and app/risk_models unchanged from the starting revision.

Intermediate failures were retained and corrected: the first disposable DB name did not end in _test (181passed/1skip/9fixture errors); a new test initially used wrong session-field names (207passed/1skip/1failure); the first Deno command used a nonexistent executable path; and initial isolated restore readiness could observe PostgreSQL's temporary initialization server. The restore harness now waits for TCP readiness, and the fresh restore/restart passed. Final runs above supersede these diagnostics; none involved resetting/restoring the application database.

Required outage scenarios are represented by tests or explicit scope: proxy/upstream403 distinction, unreachable Supabase, invalid OAuth, duplicates, crash/reclaim/lease expiry, API loss, isolated database restart, unavailable/rate-limited/invalid AI, evidence read outage and recovery, disabled refund execution, judge-write denial and cross-merchant denial. Real hosted failover, sustained production graph load, offsite backup and overlap deployment behavior remain unverified.

## G. Security

Authentication, sessions, CSRF, merchant isolation, judge read-only authorization, private downloads, evidence hashes, PayPal signature verification and TLS remain enforced. No route permits live PayPal mode. Refund execution defaults disabled and production refuses execution even if the flag is set. Dispute submission is hard403 without an enabling switch. Approval does not move money; Policy Lab cannot activate serving thresholds. Service-role and provider keys remain server-side; none enters browser/VITE variables or reports.

Actual runtime names: SENTINEL_DATABASE_URL; SENTINEL_PAYPAL_MODE, SENTINEL_PAYPAL_CLIENT_ID, SENTINEL_PAYPAL_CLIENT_SECRET, SENTINEL_PAYPAL_WEBHOOK_ID; SENTINEL_SUPABASE_URL, SENTINEL_SUPABASE_SERVICE_ROLE_KEY, optional SENTINEL_BRIDGE_API_URL; SENTINEL_AI_PROVIDER, SENTINEL_AI_MODEL, SENTINEL_AI_API_KEY; SENTINEL_COOKIE_SECURE, SENTINEL_CORS_ORIGINS, SENTINEL_STORAGE_BACKEND, SENTINEL_HOSTED_DEPLOYMENT, SENTINEL_REQUIRE_WORKERS_READY, SENTINEL_FORWARDED_ALLOW_IPS; SENTINEL_AUTO_MIGRATE, SENTINEL_MIGRATION_TARGET; SENTINEL_JUDGE_PASSWORD; SENTINEL_REFUND_EXECUTION_ENABLED. SUPABASE_ACCESS_TOKEN is administrative, not normal bridge authentication. SENTINEL_INVESTIGATION_* names do not configure the current provider.

Private dumps/configuration/logs remain outside Git. No administrator credentials are published. Literal scanning is bounded evidence, not a guarantee against every unknown or encoded secret. No network workaround, tunnel, TLS disabling, financial permission relaxation or readiness bypass was used.

## H. Screenshots

Fresh screenshot archive: /workspace/sentinel-final-release/SENTINEL_Final_Screenshots.zip. It contains 56 PNGs from the passing browser run, including desktop/mobile Command Center, transactions/payment, model, review queue, investigation/evidence/approval workbench, refunds, disputes, policy, monitoring, network, settings and judge guide. Some modules have both interaction and full-route captures. The generated PDF includes selected screenshots; full-page originals remain in the ZIP. Passwords and private tokens are absent.

Demo: sign in using the privately configured judge account, open Demo guide and the prepared investigation, inspect payment/risk/SHAP and cited deterministic findings, download private evidence/packet, review the independent approval, then inspect pending refund/dispute preparation, Policy Lab assumptions, monitoring and bounded payer links. The judge cannot write. Administrator Operations truthfully shows the degraded bridge. The synthetic guide is ready locally; it is not a public genuine-provider demonstration.

## I. Remaining blockers and exact actions

1. Review/save/publish the existing environment draft containing cfslzvvdjxstpupkqbpw.supabase.co and approved verifier certificate hosts api.sandbox.paypal.com, api.paypal.com and api-m.paypal.com. Active networking is separate from the saved draft. If denial persists, administrator must investigate proxy enforcement for that exact project and HTTPS443/RPC access. Do not broaden to unrestricted Internet.
2. Correct paired sandbox client credentials or their supported runtime delivery binding securely. Proxy readiness is not raw Basic-encoding compatibility. Retry token-only OAuth until successful; then inspect read-only webhook registration for the configured Webhook ID. No financial operation is needed for authentication diagnosis.
3. Configure a supported AI provider, explicit model and private SENTINEL_AI_API_KEY. Approve bounded paid usage before running the real evidence-grounded integration test. No key or token should be pasted into chat.
4. Obtain a hosting account and official current quote for the proposed continuous container/database, backup/storage, transfer and logs. Validate plan resources, database TLS and controlled replacement. Obtain explicit cost approval before provisioning and explicit push/publication authorization if repository publication is required. No approval amount is requested without a verified quote.
5. After deployment, verify public HTTPS, auth/CSRF/judge restrictions, private evidence, exact migration, current required-worker readiness, restore/retention, supervision/restart, alerts and real inbox freshness. No public application URL exists yet.
6. Genuine sandbox delivery remains a separate optional test requiring explicit transaction authorization. Keep the user's skipped-payment preference until that is granted. Distinguish fixture-tested, sandbox-authenticated, genuine-delivery-verified and production-verified states.
7. Export the final Git bundle and checksum independently. Local clone/restore verification does not establish off-environment durability or reliable restoration into a fresh task.

All independent authorized source, local verification, screenshots and recovery work was completed. External access/approval requirements above are not hidden by fixture success or green liveness.

## J. Git preservation

Checkout: /workspace/SENTINEL-recovered. Branch: feature/reliability-next-phase. Baseline396e998 and implementation1bc15e7155362e0561a953ca676690eef0ea8cdc are retained in the original lineage. Backup branch backup/final-release-base-20261106 preserves the baseline. A completion backup ref and verified full-history bundle are generated after the documentation commit. Final SHA, checksum, clone verification and clean-worktree status are recorded in /workspace/sentinel-final-release/delivery.json.

Pre-change full-history backup: /workspace/sentinel-final-release/before.bundle. Final bundle: /workspace/sentinel-final-release/SENTINEL_Final_Release.bundle, with adjacent .sha256 checksum. A clone from the final bundle must match the final checkout HEAD before delivery. Private pre-change application dump was restored only into an isolated container and all 30 stored blob hashes matched; a post-verification dump is retained privately. No data downgrade, reset, merge, force-push or push occurred. Previous Session8/recovery bundles and branches remain intact. Original /workspace/SENTINEL- stays at aed5d5647d14b2f7fd29575b21487ead337c64b3.
