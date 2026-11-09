# SENTINEL — Post-restoration release status

Verified 07 November 2026, 15:45 IST. **Supabase recovery is verified; the application now returns readiness200.** This supersedes previous INACTIVE/CONNECT403 blocker reports for Supabase. Public Python deployment, PayPal authentication and real AI remain incomplete.

| Gate | Current proof / state |
| --- | --- |
| Supabase project | VERIFIED: ACTIVE_HEALTHY, ap-northeast-1, PostgreSQL17.11 |
| Supabase RPC | VERIFIED: service-role metrics/claim/renew/finish work over real HTTPS |
| Normal bridge | VERIFIED: HEALTHY, fresh successful idle polls; processed0 is honest because no genuine events were received |
| FastAPI readiness | VERIFIED:200 with database/schema/pipeline/bridge required checks, including after supervisor restart |
| Remote fixture lifecycle | VERIFIED within scope: real hosted SIMULATED inbox to isolated LOCAL API/worker and existing case services |
| Genuine PayPal OAuth/registration | FAILED/UNVERIFIED: fresh401invalid_client; registration blocked until authentication |
| OpenAI/model | UNVERIFIED: key not active, requested gpt-6.1-terra not confirmed; no paid call |
| Render/public judge | NOT DEPLOYED: current quote/docs/account/authorization unavailable |
| Financial safety | VERIFIED locally: no unauthorized PayPal order/payment/capture/refund/dispute or paid AI request |

The remote fixture generated one HIGH case (score0.282081), completed deterministic investigation, evidence packet and independent internal approval. Duplicate, crash/reclaim, API outage, stale acknowledgement, out-of-order and invalid-fixture-signature scenarios passed. All six prior inbox rows retained identical canonical row hashes. Three new test receipts remain labelled SIMULATED and terminal; none was deleted. No genuine PayPal signature/delivery or public Python host was implied. Full identifiers and scope appear in SUPABASE_RECOVERY.md and remote-fixture/result.json.

Changes: scripts/verify-webhook-pipeline.py now requires a dedicated loopback _test database instead of a hardcoded shared integration DB, refuses unsafe inbox state, proves historical-row preservation and completes existing case services. Four offline safety regressions added in supabase/tests/test_fixture_safety.py. Existing app features, model weights/thresholds, migrations, security controls and deployment settings were not rewritten. New documentation records recovered state and remaining owner actions.

Fresh tests: backend213passed/1real-AI skip; frontend39; browser16; ML7; Supabase SQL/deploy/harness16; receiver11; deployment2. Static checks/build/contracts, migration safety,105-file image parity, fresh smoke, consistent-snapshot restore/database restart and session/evidence restart passed. See TEST_RESULTS.md for commands, scope and corrected harness diagnostics. Normal remote poll recovery required no policy activation or receiver redeployment. Active environment still reports revision3; pending documentation/certificate/AI requirements are separate.

Baseline1ab862aa184b7c664d716cf3f1d79a7738335cfa on feature/reliability-next-phase is preserved. Final commit, recovery checksum, clean-worktree and fresh-clone proof are recorded in DELIVERY.json after documentation commit. No push, merge, reset, paid provisioning, public deployment, administrator rotation or financial action occurred. Off-environment backup remains unverified.

Remaining owner actions are only secure PayPal correction, documentation/key/model/pricing access, explicitly bounded AI approval, concrete Render cost/publication/deployment authorization and independent recovery export. Do not restore Supabase again. Read OWNER_ACTIONS.md for precise steps.

## Reproduce the authorized fixture check

Set SENTINEL_FIXTURE_DATABASE_URL to a dedicated loopback PostgreSQL database ending _test, set private SENTINEL_SUPABASE_URL/SERVICE_ROLE_KEY and SUPABASE_ACCESS_TOKEN securely, then run the existing scripts/verify-webhook-pipeline.py with --allow-hosted-fixtures using the API virtualenv. Use an exclusive fixture window; it refuses existing active receipts. Never use a user database or production receiver for fixtures. Detailed trace and remaining access steps are in /workspace/sentinel-post-restoration.
