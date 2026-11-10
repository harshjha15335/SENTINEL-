# SENTINEL — Cloudflare Pages preparation

DESIGN APPROVAL: APPROVED

DEPLOYMENT APPROVAL: PENDING

This is an isolated static-host configuration for the immutable Gate 2A portable/hash application at `5261ebf24c9e2c58949fc883e8c377acea101d37`. No application/backend/model source changes are needed. No Cloudflare project, account setting, DNS record, sharing permission or deployment has been created or changed. Existing private review hosting is untouched.

## Reproduce without hosting actions

Commit configuration first. From repository root:

```sh
python hosting/cloudflare-pages/prepare.py /path/to/SENTINEL-Gate2A-static-candidates.zip /path/to/NEW-release-directory
```

The exact future publish root is `NEW-release-directory/publish`. Its contents are also archived in `NEW-release-directory/cloudflare-publish.zip`, with `_headers` and a plain accessible `404.html` at the ZIP root. Do not upload the containing release directory, reports, manifests, credentials or recovery bundles. `HOST-MANIFEST.json` and `SHA256SUMS` stay outside `publish`.

Preparation verifies the exact Gate 2A input archive hash, every original checksum and manifest, application revision, snapshot closure/privacy/counts, Cloudflare header/file limits and a clean source revision. The 58 portable application/data files are copied unchanged; only `_headers` and `404.html` are added. The existing Gate 2A package and source recovery are preserved.

## Proposed Pages settings — only after explicit authorization

Preferred method: Pages Direct Upload of the prebuilt `publish` directory or its `cloudflare-publish.zip`. A new Direct Upload project is a future action requiring approval; no project name or hostname is claimed to exist. Choose the approved name/account at deployment time. Framework preset/build command/repository integration are unnecessary for Direct Upload; no Cloudflare build, environment variables, secrets, Functions, Workers, database, bindings or API service are required. Do not run Wrangler from a repository that could contain Functions. The prepared upload root contains none.

Cloudflare documents that a Direct Upload project cannot later switch to Git integration; a new project is needed for that. Choose deliberately before approving resource creation. Keep automatic Git deployments disabled/unconfigured; existing repository workflows are not executed here.

Cloudflare provides Pages deployment hostnames and certificate handling; custom domains require separate approved setup and valid certificate issuance/CAA records. No custom domain or DNS changes are proposed now. Actual HTTPS certificate trust, HTTP→HTTPS redirects, protocol negotiation and hostname behavior must be verified on the approved host. `_headers` does not configure TLS or create an HTTPS redirect.

## Header policy and rationale

- Scripts: same-origin only; no inline scripts, inline event handlers, eval, third-party script hosts or Workers. `object-src`, framing, forms, media and base URLs are disabled. Connections and fonts stay same-origin; images may additionally use `data:` for bundled icon rendering.
- Styles: same-origin plus inline styles. The approved React/GSAP animation sets inline transforms and progress values; AG Grid also uses dynamic styling. This permission is intentional for the existing application, not an attempt to suppress script failures. No `unsafe-eval` or inline script permission is added. A nonce would require document transformation and coordinated source changes; neither is introduced for this static artifact.
- Framing: CSP `frame-ancestors 'none'` plus `X-Frame-Options: DENY`. The public demo is intended to open directly, not be embedded in an iframe.
- `nosniff`, `Referrer-Policy: no-referrer`, restricted device permissions, and HSTS `max-age=86400`. HSTS is host-only: no `includeSubDomains` and no preload commitment. A longer HSTS period requires a separate, verified hostname policy. Local self-signed testing does not establish real-host TLS/HSTS behavior.
- Hashed `/assets/*`: browser cache one year and immutable. `/`, HTML and fixed-name `/demo-data/*` JSON: browser revalidation on every reuse, retaining ETags and avoiding stale immutable snapshot URLs. JSON is explicitly `application/json; charset=utf-8`. Fonts/JS/CSS/SVG rely on Pages' automatic MIME handling and must be checked at the actual host.
- No overlapping Cache-Control assignments: Cloudflare joins duplicate header values. Preserve its optimized edge caching defaults; do not create zone Cache Rules or hard-code `Content-Encoding`, `Content-Length` or `no-transform`. Pages documents Gzip/Brotli delivery whenever possible. Verify actual negotiated responses, ETags/304 and cache behavior after publication.
- Hash routing uses `/#/`, `/#/demo-payment`, `/#/app`, `/#/app/transactions`, `/#/app/transactions/UUID`, `/#/app/cases/UUID`, `/#/app/model`. Browser refresh/back/forward retain fragments. Service-only hash links explain full-app requirements; invalid IDs show deliberate errors. Plain physical unknown paths return the static 404 with recovery links. A top-level `404.html` prevents Pages' implicit SPA fallback from serving relative assets at arbitrary nested physical paths.

## Documentation reviewed

Official documentation was fetched from Cloudflare's own `cloudflare/cloudflare-docs` production branch because this executor blocks direct access to `developers.cloudflare.com`. The evidence directory preserves retrieved documents, hashes, source revision and retrieval method. Consult current provider documentation again before any eventual deployment:

- https://developers.cloudflare.com/pages/configuration/headers/
- https://developers.cloudflare.com/pages/configuration/serving-pages/
- https://developers.cloudflare.com/pages/get-started/direct-upload/
- https://developers.cloudflare.com/pages/platform/limits/
- https://developers.cloudflare.com/pages/functions/pricing/
- https://developers.cloudflare.com/pages/configuration/rollbacks/
- https://developers.cloudflare.com/pages/configuration/custom-domains/
- https://developers.cloudflare.com/speed/optimization/content/compression/

Current documentation states static asset requests are free and unlimited when no Functions execute; the Free plan allows 20,000 site files, 25 MiB per asset and 500 builds/month. Dashboard drag-and-drop permits 1,000 files; Wrangler permits 20,000. This small prebuilt static upload requires no paid compute plan under those documented limits. No purchase is authorized; account eligibility/quotas must still be confirmed by the owner. Custom domain registration and optional products are separate costs, not included or required here.

## Local validation model

`local-preview.mjs` serves only loopback HTTPS with an explicitly local certificate, models this `_headers` subset, returns correct MIME/cache headers, offers Brotli/Gzip negotiation and ETag/304, and provides a local HTTP redirect. It is a test harness, not Cloudflare software and not proof of edge behavior. Test certificates/keys belong outside the publish root and are not included in archives.

```sh
node hosting/cloudflare-pages/local-preview.mjs /path/to/publish /private/local.crt /private/local.key
# apps/web, with the loopback preview already running:
SENTINEL_STATIC_DEMO=true SENTINEL_STATIC_HASH=true npx playwright test --config playwright.host.config.ts
```

The host test configuration accepts only the disposable local certificate. Do not use that TLS exception for actual-host verification. Browser tests check the unchanged wallet, bidirectional scrolling, mobile fallback, reduced motion, keyboard skip, CSP enforcement and recorded read-only views. Standard static tests retain deep links, refresh, back/forward, unavailable features and invalid record checks. Local performance results are laboratory measurements, not field Core Web Vitals or a host performance certification.

## Actual-host smoke plan — remains pending

After an explicitly authorized deployment, use a trusted HTTPS client without certificate bypass. Verify HTTP redirects to the correct HTTPS hostname; root and hash-linked views open; all module/font/CSS/data requests use the approved origin and MIME types; `_headers` is not publicly served; unknown physical paths return a genuine recovery 404. Check the CSP and all security headers, with no duplicate/conflicting cache values. Confirm framing and inline-script rejection.

Request representative HTML, hashed JS/CSS/fonts and every JSON file with `Accept-Encoding: br` and `gzip`; check negotiated encoding, decoded hashes against the manifest, ETag/304 behavior, HTML/JSON revalidation and immutable asset policy. Do not infer compression merely from an `Accept-Encoding` request. Repeat the functional browser suite with normal TLS validation, inspect browser CSP/network errors, then test keyboard, reduced motion, forward/reverse scrolling, mobile and network loading at the public hostname. Confirm zero merchant API, provider, external resource or write requests in normal use. Save headers/results, actual deployment ID and manifest hash before handing out a judge URL. Reload long-lived tabs after a release or rollback.

## Rollback

Keep every approved `cloudflare-publish.zip`, its SHA256, host manifest and source bundle immutable outside public files. Record the Cloudflare production deployment ID mapped to each approved artifact. Cloudflare documents dashboard **Deployments → All deployments → target successful production deployment → Rollback to this deployment**; preview deployments are not valid rollback targets. After an authorized rollback, re-run host smoke checks, verify the restored manifest's decoded content hashes and JSON revalidation, and reload long-lived tabs.

The first-ever deployment has no previous production deployment to roll back to. Do not invent one: if the first launch fails, stop distribution and use an explicitly approved withdrawal/maintenance procedure. Re-uploading an immutable artifact is a new deployment and also requires authorization. This task has no authority to perform either action.

## Remaining boundary

Readiness here means an artifact and configuration ready for deployment approval. Actual Cloudflare acceptance, HTTPS trust/redirects, security headers at the edge, cache/compression behavior, hostname performance, domain/account settings and rollback remain unverified until a future authorized host test. The authenticated backend and real PayPal tracks are unchanged and separate. Stop before publication.
