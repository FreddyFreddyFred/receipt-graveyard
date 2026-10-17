# Current state

- **Updated:** 2026-10-18
- **Project:** The Receipt Graveyard, scoped in `PROJECT.md`.
- **Local branch:** `codex/main-task-run`, tracking the synchronized `main` history after workspace PR #1 merged.
- **Last verified task:** `T6.2`, pushed to `main` at `f037e8a`.
- **Current task:** No task is in progress. The validated controller selected `T8.1` (high priority) as the next required ready task. `T1.4` remains blocked pending a usable Tesseract executable; its partial work remains isolated in the working tree.
- **Verification:** Python 3.14.4 `.venv`; full working-tree `pytest tests/ -v` passed 98 tests with one real Tesseract integration skipped. The suite includes the separate uncommitted T1.4 OCR tests. Repository checks cover employee/receipt/verdict CRUD, Decimal and model round-trips, FK behavior, audit history, transaction rollback when audit fails, and in-memory persistence. Ruff, `pip check`, controller `Validate`, and `git diff --check` passed. T1.2 visual before/after review passed.
- **GitHub:** `main` is synchronized through verified task T6.2 at `f037e8a`. Workspace controller PR [#1](https://github.com/FreddyFreddyFred/receipt-graveyard/pull/1) merged as `cbd7f08`.
- **Workflow:** D18 records the user's approval to commit and push each verified task directly to `main` during this run.
- **Blockers:** Tesseract wrapper and mocked adapter checks pass, but this Windows environment has no Tesseract executable on PATH. The official Windows installer SHA-256 matches the official GitHub release, yet a non-admin per-user silent install produced no executable; Chocolatey reports this shell is non-elevated. The required clean-receipt OCR integration test is skipped, so T1.4 acceptance is incomplete. Revisit when a Tesseract executable is installed or its path is available.
- **Next action:** Inspect T8.1's acceptance criteria, API package, and Git state; then begin it through the validated controller. Keep partial T1.4 changes isolated.
