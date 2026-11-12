# Gate 2B — static host preparation

DESIGN APPROVAL: APPROVED

DEPLOYMENT APPROVAL: PENDING

Use [the isolated Cloudflare Pages preparation](../../hosting/cloudflare-pages/README.md). The input remains the verified Gate 2A portable application at `5261ebf24c9e2c58949fc883e8c377acea101d37`. Host configuration is additive and separate; approved application/animation/backend/model source is unchanged. No hosting resources, sharing changes, pushes, merges or deployments are authorized.

The release script preserves the Gate 2A package and exports a future publish root containing its exact 58 portable files plus reviewed `_headers` and an intentional physical-path 404 page. Reports/manifests/recovery remain outside that root. Current official Cloudflare documentation, input validation, local enforced-CSP browser tests, compression/cache probes, lab performance measurements and remaining actual-host requirements are retained in `/workspace/sentinel-gate2b/`. Final executed results and immutable artifact hashes are recorded in its delivery report. No actual-host checks are represented as passed.
