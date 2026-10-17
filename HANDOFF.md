# Handoff

The approved scope is in `PROJECT.md`; the 49-task canonical graph is in `TASKS.json` and mirrored by `PLAN.md`. Repository: `FreddyFreddyFred/receipt-graveyard`.

`T0.0`, `T0.1`, `T0.2`, `T0.4`, and `T1.1` are verified. The controller passed `Validate` and safe `Smoke` in both Windows PowerShell 5.1 and PowerShell 7. PR [#1](https://github.com/FreddyFreddyFred/receipt-graveyard/pull/1) is merged to `main`; T0.1's fresh Python 3.14.4 `.venv` passed editable and requirements installs, package import, Ruff, and `pip check`. T0.2's 11 sub-package imports and D13 directory comparison passed. T0.4 added the initial pytest fixture and smoke test. T1.1's model JSON round-trips, required-field validation, optional defaults, and Ruff checks passed (11 pytest tests total). The current working branch `codex/main-task-run` is based on the merged main history. D18 records the user's explicit approval to push each individually verified task directly to `main` for this run.

T1.2 is verified locally with 19 passing pytest tests, Ruff, `pip check`, graph validation, safe controller smoke, and visual before/after inspection. The controller selected required task T1.4 (OCR abstraction and first engine adapter) next; it depends on verified T0.2 and T1.2. T1.2 is being synchronized to `main` before T1.4 begins. Before each future task, run graph validation, inspect the task scope and Git status, and choose the highest-priority ready required task. Implement one task at a time, run its acceptance checks, update `TASKS.json`, `PLAN.md`, `STATE.md`, and this handoff, review the diff, commit only intended files, then `git pull --rebase origin main` and `git push origin HEAD:main`.

The controller's `Run` action selects and starts the next ready task in the ledger; it does not autonomously implement application code. The application itself is still in planning and is not runnable yet. To inspect or start the next task from the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run-project.ps1 -Action Validate
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run-project.ps1 -Action Next
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run-project.ps1 -Action Run -PreflightConfirmed
```
