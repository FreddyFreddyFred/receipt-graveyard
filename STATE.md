# Current state

- **Updated:** 2026-10-18
- **Project:** The Receipt Graveyard, scoped in `PROJECT.md`.
- **Local branch:** `codex/main-task-run`, tracking the synchronized `main` history after workspace PR #1 merged.
- **Last verified task:** `T6.1`, pushed to `main` at `763b2dd`.
- **Current task:** No task is in progress. The validated controller selected `T6.2` (high priority) as the next required ready task. `T1.4` remains blocked pending a usable Tesseract executable; its partial work remains isolated in the working tree.
- **Verification:** Python 3.14.4 `.venv`; full `pytest tests/ -v` passed 92 tests with the real Tesseract integration skipped because the executable is unavailable. Schema/migration tests pass twice-run idempotence, foreign-key enforcement, verdict cascade, and audit retention; a fresh temporary file database also ran the migration twice with all four tables present. Ruff, `pip check`, controller `Validate`, and `git diff --check` passed. T1.2 visual before/after review passed.
- **GitHub:** `main` is synchronized through verified task T6.1 at `763b2dd`. Workspace controller PR [#1](https://github.com/FreddyFreddyFred/receipt-graveyard/pull/1) merged as `cbd7f08`.
- **Workflow:** D18 records the user's approval to commit and push each verified task directly to `main` during this run.
- **Blockers:** Tesseract wrapper and mocked adapter checks pass, but this Windows environment has no Tesseract executable on PATH. The official Windows installer SHA-256 matches the official GitHub release, yet a non-admin per-user silent install produced no executable; Chocolatey reports this shell is non-elevated. The required clean-receipt OCR integration test is skipped, so T1.4 acceptance is incomplete. Revisit when a Tesseract executable is installed or its path is available.
- **Next action:** Inspect T6.2's acceptance criteria, schema, and repository state; then begin it through the validated controller. Keep partial T1.4 changes isolated.
