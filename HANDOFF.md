# Handoff

The approved project scope and original 48-task plan are in `PROJECT.md`, `PLAN.md`, `TASKS.json`, and `DECISIONS.md`. The repository is `FreddyFreddyFred/receipt-graveyard`; the workspace update is on clean branch `feature/T0.0-recoverable-controller` based directly on upstream `main`.

`T0.0` is verified: controller `Validate` and `Smoke` passed against all 49 tasks. The ledger was unchanged by smoke. Run `git pull --rebase`, push `feature/T0.0-recoverable-controller`, and open the project-required pull request. `T0.1` is the next required task; do not start it until this branch is synchronized.

To run the controller from the repository root, use:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run-project.ps1 -Action Validate
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run-project.ps1 -Action Smoke
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run-project.ps1 -Action Run -PreflightConfirmed
```

The app is still in planning; the README's application Quick Start commands are future instructions, not currently runnable. Follow D16 in `DECISIONS.md`: use a `feature/<task-id>-<short-slug>` branch and a pull request; never commit directly to `main`.
