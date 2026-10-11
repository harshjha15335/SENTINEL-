# Deployment

SENTINEL ships as **one container**. FastAPI serves the API under `/api` and the built React app on every other path, all from the same origin. Session cookies and CSRF therefore work without any cross-site setup. The image is the root `Dockerfile`.

The full app needs its API and PostgreSQL, so options 1 to 3 run the container. GitHub Pages can host only static files, so option 4 is a read-only snapshot. All four start from this GitHub repository.

## 1. GitHub Codespaces (no other account)
1. Open https://codespaces.new/harshjha15335/SENTINEL- and create the codespace.
2. `.devcontainer/` starts PostgreSQL 16 next to a Python 3.12 + Node 24 container. `setup.sh` then:
   - installs dependencies and builds the web app
   - runs the migrations
   - creates the demo users with random passwords
   - loads the synthetic scenario
3. `start.sh` serves the app on port **8000**, which opens automatically.
4. Sign in as `analyst@northwind.example`. The passwords are in `.devcontainer/demo-credentials.txt`, which is git-ignored.
5. The forwarded port is private to you by default. To show someone else, set port 8000 to *Public* in the Ports panel, and switch it back afterwards.

**Checked in this container:** the setup and start scripts ran on a clean copy of the repo, and the Playwright suite passed against the result. Not yet checked: the Codespaces image itself and its Node feature.

## 2. Render (public URL)
`render.yaml` is a Blueprint that defines:
- a free Docker web service built from this repo
- a free PostgreSQL database

To deploy:
1. Use the *Deploy to Render* button in the README, or go to https://render.com/deploy?repo=https://github.com/harshjha15335/SENTINEL-.
2. When asked for the PayPal variables, leave them empty to stay in demo mode.
3. Find the demo sign-in passwords under the `sentinel` service, then *Environment*. Render generates them.

What to expect:
- The first boot migrates the database, seeds the users and loads the synthetic scenario. Later boots skip the scenario (`demo-load --if-empty`).
- The service redeploys on each push to `main`.
- The health check is `/api/v1/ready`.
- Free-plan limits apply, so check Render's current terms: the service sleeps when idle and takes about a minute to wake, and free databases expire after a fixed period.

## 3. Container image (GHCR)
The `Image` workflow (`.github/workflows/image.yml`):
1. builds the image
2. boots it against PostgreSQL in demo mode
3. smoke-tests readiness, the web shell, client-side routes, CSP, sign-in and the 170-case review queue
4. pushes `ghcr.io/harshjha15335/sentinel:main` and `:sha-<commit>` from `main`

GitHub may create the package as private. Making it public is a package setting the repository owner controls.

```bash
docker run -p 8000:8000 \
  -e SENTINEL_DATABASE_URL=postgresql://USER:PASS@HOST:5432/DB \
  -e SENTINEL_PAYPAL_MODE=fixture -e SENTINEL_DEMO_AUTOLOAD=true \
  -e SENTINEL_SEED_ADMIN_PASSWORD=... -e SENTINEL_SEED_ANALYST_PASSWORD=... \
  ghcr.io/harshjha15335/sentinel:main
```

## 4. Static demo on GitHub Pages (read only)
https://harshjha15335.github.io/SENTINEL-/

The `Pages` workflow (`.github/workflows/pages.yml`) runs on every push to `main`:
1. Loads the synthetic demo into a throwaway PostgreSQL database in the runner, with one-off passwords.
2. `apps/api/scripts/export_static_demo.py` signs in as the seeded viewer and saves the real API responses (dashboard, transactions, risk assessments, cases, model card) as JSON.
3. Builds the web app with `VITE_STATIC_DEMO=true` and the `/SENTINEL-/` base path. In this build `api()` reads the snapshot (`src/lib/staticApi.ts`) and refuses every write.
4. Copies `index.html` to `404.html` so deep links work, then runs `e2e/static-demo.spec.ts` against a local Pages-like server before deploying.

What a visitor sees:
- Every screen carries a "Static demo, read only" banner saying the data is SYNTHETIC_DEMO, nothing is saved and no PayPal call is made.
- They browse as the read-only viewer, so no claim, resolve, re-score or checkout controls appear. There is no sign-in and no session.
- The audit log stays admin-only, as on the server.

Try it locally:
```bash
cd apps/web
VITE_STATIC_DEMO=true SENTINEL_WEB_BASE=/SENTINEL-/ npx vite build --outDir /tmp/site/SENTINEL-
# add the exported JSON as /tmp/site/SENTINEL-/demo-data and copy index.html to 404.html, then:
node scripts/pages-preview.mjs /tmp/site SENTINEL-
SENTINEL_STATIC_DEMO=true SENTINEL_WEB_URL=http://127.0.0.1:4173/SENTINEL-/ npx playwright test e2e/static-demo.spec.ts
```

Pages must be set to deploy from GitHub Actions (Settings → Pages → Source).

## Configuration
| Variable | Purpose |
|---|---|
| `SENTINEL_DATABASE_URL` | PostgreSQL URL. `postgres://` and `postgresql://` are converted to psycopg 3 automatically. |
| `SENTINEL_PAYPAL_MODE` | `fixture` (SIMULATED, no PayPal calls) or `sandbox`. There is no live mode. |
| `SENTINEL_PAYPAL_CLIENT_ID`, `SENTINEL_PAYPAL_CLIENT_SECRET` | Sandbox REST app credentials. Set both or neither. |
| `SENTINEL_PAYPAL_WEBHOOK_ID` | Webhook id for signature verification. Register `https://<host>/api/v1/webhooks/paypal` in the PayPal developer dashboard. |
| `SENTINEL_SEED_{ADMIN,ANALYST,VIEWER}_PASSWORD` | Demo users created at start-up. They are skipped if the admin password is empty. |
| `SENTINEL_DEMO_AUTOLOAD` | `true` loads the SYNTHETIC_DEMO scenario once. |
| `SENTINEL_COOKIE_SECURE` | `true` behind HTTPS. |
| `SENTINEL_WEB_DIST` | Path of the built web app. The image sets it to `/app/web`. |
| `PORT` | Listen port, default 8000. |

## Switching a deployment to the PayPal sandbox
Set `SENTINEL_PAYPAL_MODE=sandbox` together with the client id and secret, then redeploy. The Settings page shows whether the token check passes. New payments are then recorded as **Live sandbox**. Earlier simulated and synthetic records keep their labels and are never merged into sandbox totals.

## Security notes
- The browser bundle contains no secrets.
- HTML responses carry a Content-Security-Policy. PayPal's sandbox SDK is the only allowed third party. The Playwright suite fails if the app triggers a CSP violation.
- The login rate limit is per process and uses the client address from the proxy's `X-Forwarded-For` header (`--proxy-headers`). Run a single instance, or move the limiter to a shared store first.
