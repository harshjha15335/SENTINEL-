# Recovery and rollback boundaries

Original integration, UI and implementation refs remain unchanged. The remediation branch is local only; PR #2 still points to audited 8250671. No production rollback is currently needed because nothing was deployed.

To inspect the pre-remediation baseline without discarding work, create a new detached worktree:

```bash
git -C /workspace/SENTINEL-integration worktree add --detach /workspace/SENTINEL-remediation-baseline 8250671f202bfee5813518c52056492903d061df
```

Do not reset, clean, force-push or overwrite an existing worktree. Keep the remediation branch and local recovery refs. Its final full SHA and private recovery-bundle verification are in the external delivery report.

Future hosted rollback requires a separately approved prior immutable artifact, database/schema compatibility check and backup/restore plan. Do not reverse migrations or financial records automatically. The worker standby uses the same advisory lock protocol as the prior worker, so it can coexist with a prior active worker during handoff; hosted lifecycle/rollback still needs approval-dependent acceptance. Stop on stale readiness, lock loss, job duplication/loss, auth errors, TLS failure or unexpected provider calls. Preserve evidence and reconcile before retrying.
