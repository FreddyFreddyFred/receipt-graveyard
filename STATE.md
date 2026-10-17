# Current state

- **Updated:** 2026-10-18
- **Project:** The Receipt Graveyard, scoped in `PROJECT.md` on GitHub.
- **Branch:** `feature/T0.0-recoverable-controller`, based directly on the existing `origin/main` history.
- **Last verified task:** `T0.0`.
- **Verification:** `scripts/run-project.ps1 -Action Validate` and `-Action Smoke` passed against all 49 tasks. Smoke checks covered invalid graph cases and priority selection; `TASKS.json` remained unchanged during smoke.
- **Blockers:** GitHub synchronization is pending for `feature/T0.0-recoverable-controller`.
- **Next action:** run `git pull --rebase`, push the feature branch, open its pull request, then continue with ready task `T0.1`.
