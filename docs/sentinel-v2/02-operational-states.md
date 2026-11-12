# Operational states — existing semantics and V2 prototype

Source anchors: `src/lib/api.ts`, `features/auth/session.ts`, `app/App.tsx`, feature hooks and UI; server auth/service tests. This records actual behavior, not a list of promised improvements. All old states remain in their original screens during Phase 1.

| State | Existing behavior | V2 prototype / migration acceptance |
|---|---|---|
| Initial load | React Query pending and feature Skeleton; session check before protected shell | Session-check/loading text uses role=status; no authenticated reads before /me |
| Success | Typed API data, origin badges and server values | Dossier reuses typed hooks/formatMoney; API outputs never replaced by fixtures |
| Empty | Feature-specific empty text/CTA | No matches, no case, no assessment and no timeline are distinct states |
| Partial data | Missing refs display —; risk/case panels query independently | Unavailable refs and unscored risk displayed; risk/case failure does not become mock data |
| Network/timeout/5xx | ApiError JSON/correlation IDs; query retries only when allowed by app client; explicit error panels | Isolated preview cache disables automatic retries; explicit Try again only on reads |
| Session expiration | /me 401 returns null; main query/mutation error handlers invalidate session; protected shell redirects | Any preview API 401 clears its private cache and invalidates /me. Sign-in gate replaces private content |
| Forbidden | Backend role/tenant checks; ErrorState; controls hidden as UI hints only | 403 stays error; no auth bypass; no mutations in prototype |
| Input validation | Login schema; query limits; forms; upload/service validation; server final authority | Demo selector constrained to two examples; existing search endpoint still limits q; server errors visible |
| Stale data | Query keys/cache; previous rows retained during transaction/case pagination; no universal stale indicator found | Separate short-lived preview cache, no polling or data retained outside preview. Do not claim existing general stale warnings |
| File failure | Multipart API error; evidence type/size/content checks; user retries | Existing uploader remains unchanged. Full migration must preserve checks and failures before replacing it |
| Retry | Explicit read refetch; query retry excludes client errors; mutations do not auto-retry | Retry only explicit reads. No duplicate mutation retry introduced |
| Unsaved edits | Local form state; no universal leave-page guard found | Record current behavior; an unsaved-edit guard would be a deliberate improvement, not claimed baseline parity |
| Duplicate submission | Pending controls + server idempotency/state/independent-approval constraints | Prototype read-only; future screens must retain both pending and server safeguards |
| Refresh | Router resolves nested routes; persisted session; query state on existing transaction/case pages | Demo `example`, authorized `q/id` survive refresh; reel restores saved p after lazy mount |
| Back/forward | Existing router/query behavior; component-only policy/network controls may reset | Demo URL selection/history tested; no blanket promise of persistence for all controls |
| Deep link | UUID routes and aliases; server/static Pages fallback differs by build | Authorized dossier id is supported; old case link remains unchanged. Final aliases require Gate 1 approval |
| Offline/reconnect | No offline data store found; normal errors/query behavior | No fabricated offline success or live polling health; readable failure remains |
| Loading auth failure | Existing shell may redirect after /me error when no data | Preview distinguishes /me failure from unauthenticated null; records the difference without altering original auth |

Accessibility: loading/status and error semantics, keyboard-operable native controls, focusable skip target, readable non-motion story. Axe results are bounded automated checks; screen-reader and physical-device testing remain unperformed.

Security boundaries to preserve: same-origin cookies/CSRF, per-merchant queries, private evidence downloads, ADMIN/ANALYST/VIEWER enforcement, independent financial decisions and disabled operational policy activation. Provider integrations are separately BLOCKED for genuine external verification.
