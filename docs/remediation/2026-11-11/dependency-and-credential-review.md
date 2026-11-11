# Low-severity audit follow-up

## N01 — dependency reproducibility (proposal only)

Direct pins and npm lock remain unchanged. No dependency upgrades are part of remediation. Python transitive dependencies remain not fully locked.

Proposed separate change: generate reviewed runtime and dev/ML constraints/locks from pyproject for the supported Python/platform, include hashes where supported, use frozen CI/container installation, check drift and SBOM, and run the full suite against a fresh frozen install. Separate runtime from ML tooling. Do not treat a pip freeze from an existing environment as a reviewed universal lock. Existing transitive resolution is recorded in external evidence without credential-bearing index URLs.

## N02 — credential-shaped offline literal

The mock provider constructor formerly contained a provider-key-shaped literal. Surrounding code uses a local MockTransport; no local evidence establishes its external validity or provenance. No authentication attempt was made and the old literal is never printed in reports.

The mock now uses `offline-test-not-a-provider-credential`. This removes credential-shaped material from this source location while preserving the mocked transport. Existing Git history remains unchanged. Owner provenance/rotation review remains necessary if the old value could have been genuine; replacement is not proof that it was fake or that historical exposure is resolved.
