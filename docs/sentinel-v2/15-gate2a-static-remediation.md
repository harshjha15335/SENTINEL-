# Gate 2A — static export and capability corrections

DESIGN APPROVAL: APPROVED

DEPLOYMENT APPROVAL: PENDING

Scope: static release blockers only. The approved homepage, backend contracts, authentication, workers, hosting and private review Site remain unchanged. No deployment is authorized.

## Root cause, established from historical evidence

The original export helper used eight concurrent detail workers, but each API request used an independent READ COMMITTED database session. Transaction pagination completed on 2026-11-09 at 20:48:04.957039 UTC (46 requests, beginning 20:47:56.294043). Transaction `1e054580-49f1-48be-a7a4-a4d4cf23647d` was created at 20:52:15.263822 UTC and case `73823607-ce2b-4090-9fd4-d1e3119f28d6` at 20:52:15.667697. The case list was read at 20:57:23.260398. Thus the payment did not exist when transaction pagination finished; it did exist when cases were read. Transaction ordering already had a UUID tie-break; neither list supplied filters. The defect is cross-request snapshot timing, not an orphan in the source database.

Historical evidence is preserved under `/workspace/sentinel-phase2/evidence/static-export.log`, `/workspace/sentinel-release-audit/`, and the original download archives. The existing checkout and history were not reset. Pre-change recovery: `backup/sentinel-v2-before-gate2a` at `9794b1c5615d2cb445d4ba9c797167d45d22fbf9`; verified bundle `/workspace/sentinel-gate2a/before-gate2a.bundle`.

## Export/build contract

The exporter requires explicit `SENTINEL_STATIC_FIXTURE_APPROVED=true`, a loopback disposable database ending `_test`, `SENTINEL_PAYPAL_MODE=fixture`, `SENTINEL_AI_PROVIDER=none`, and the seeded viewer password supplied privately. It authenticates before creating a PostgreSQL exported REPEATABLE READ, READ ONLY snapshot. All later API reads import that snapshot on independent read-only connections. Bounded detail concurrency retains input order. Pagination totals and duplicate identifiers are checked. The script refuses to overwrite output; it stages, validates, then renames a complete export. No dummy payment is inserted and no case is removed.

`apps/api/scripts/validate_static_demo.py` is a dependency-free canonical gate shared by export and Vite. It checks transaction/case/detail/extras/risk/dashboard closure, associations, counts, origins, fixture persona and sensitive-field exclusions. Case assessments may correctly reference an earlier assessment; they must retain the case's recorded assessment ID and payment association. Case audit entries for unavailable workflows are historical metadata, not downloadable evidence or navigable resources; their case and payment associations are checked. JSON object keys are sorted; record IDs/order/content are preserved. Export time and source revision are explicit metadata, not deterministic across runs. No database URL or credential is serialized.

Static builds require Python 3 plus `SENTINEL_STATIC_SNAPSHOT_DIR=/absolute/path/to/validated/export`. Vite rejects missing/invalid snapshots before generating assets, copies the validated eleven JSON files, and validates the output. Normal builds require no snapshot and keep their existing API behavior. The manually triggered Pages workflow now uses its own `sentinel_static_test` fixture database and the same gate; it has not been run or deployed.

```sh
# apps/web; snapshot must have been exported from the approved fixture DB
npm run typecheck
npm run lint
npm test
npm run build
SENTINEL_STATIC_SNAPSHOT_DIR=/path/to/export VITE_STATIC_DEMO=true VITE_ROUTER=hash SENTINEL_WEB_BASE=./ npm run build -- --outDir /path/to/new-portable-output
SENTINEL_STATIC_SNAPSHOT_DIR=/path/to/export VITE_STATIC_DEMO=true SENTINEL_WEB_BASE=/SENTINEL-/ npm run build -- --outDir /path/to/new-pages-output
python3 ../api/scripts/validate_static_demo.py /path/to/export
```

## Capability contract

`src/lib/capabilities.ts` explicitly declares build capabilities; route boundaries and navigation consume those declarations. Static supported features: dashboard, transactions, recorded risk, case facts/history, risk model, public homepage and public authored demo. Service-only screens are Policy Lab, Monitoring, Relationship explorer, Refund review, Dispute preparation, Sandbox checkout, Integration/account, Demo guide and Operations. Static navigation hides these entries; direct/legacy links show an accessible full-application explanation with supported return links. Case workbench investigation runs, evidence/packets and decisions/approvals use the same boundary and never mount their service panels. No alternate backend workflow is fabricated. The existing viewer restrictions and static API write refusal remain. Unknown pages and missing record IDs keep intentional recovery/error states.

Operational builds pass through every boundary, retain all original navigation/role rules, and retain mounted workbench panels/drafts. Auth, CSRF and server role checks are untouched.

## Verification and delivery

Execution evidence and final manifests are retained separately in `/workspace/sentinel-gate2a/`. Final test counts, source revision, artifact hashes, remaining host-specific checks and verdict will be recorded in its `REPORT.md`. No private review download, source bundle, database, secret configuration or audit report belongs inside the static candidate. Recovery/source bundles remain separate from the publishable files.

Host review still must verify the chosen base path, deep-link fallback, HTTPS/security headers, cache rules, content type/compression, accessibility and route behavior at the actual host. This local candidate is not a deployed service. Authenticated hosting/workers/TLS and live PayPal remain separate, unauthorized workstreams.
