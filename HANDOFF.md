# Handoff

The approved scope is in `PROJECT.md`; the 49-task canonical graph is in `TASKS.json` and mirrored by `PLAN.md`. Repository: `FreddyFreddyFred/receipt-graveyard`.

`T0.0`, `T0.1`, `T0.2`, and `T0.4` are verified. The controller passed `Validate` and safe `Smoke` in both Windows PowerShell 5.1 and PowerShell 7. PR [#1](https://github.com/FreddyFreddyFred/receipt-graveyard/pull/1) is merged to `main`; T0.1's fresh Python 3.14.4 `.venv` passed editable and requirements installs, package import, Ruff, and `pip check`. T0.2's 11 sub-package imports, D13 directory comparison, and Ruff check passed. T0.4's `pytest tests/ -v` passed one smoke test. The current working branch `codex/main-task-run` is based on the merged main history. D18 records the user's explicit approval to push each individually verified task directly to `main` for this run.

T0.2's verified package skeleton is synchronized to `main` at `84ba504`. T0.4 is locally verified and should be committed and synchronized before starting the next task. The controller selects T1.1 (critical priority) next; it depends on the verified package structure. Before each future task, run graph validation, inspect the task scope and Git status, and choose the highest-priority ready required task. Implement one task at a time, run its acceptance checks, update `TASKS.json`, `PLAN.md`, `STATE.md`, and this handoff, review the diff, commit only intended files, then `git pull --rebase origin main` and `git push origin HEAD:main`.

The controller's `Run` action selects and starts the next ready task in the ledger; it does not autonomously implement application code. The application itself is still in planning and is not runnable yet. To inspect or start the next task from the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run-project.ps1 -Action Validate
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run-project.ps1 -Action Next
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run-project.ps1 -Action Run -PreflightConfirmed
```
