# Current state

- **Updated:** 2026-10-18
- **Project:** The Receipt Graveyard, scoped in `PROJECT.md`.
- **Local branch:** `codex/main-task-run`, tracking the synchronized `main` history after workspace PR #1 merged.
- **Last verified task:** `T2.2`.
- **Current task:** `T2.2` currency detection and normalization is verified and pushed; the controller selected `T2.4` as the next high-priority ready task. `T1.4` remains blocked pending a usable Tesseract executable.
- **Verification:** Python 3.14.4 `.venv`; full `pytest tests/ -v` passed 75 tests with the real Tesseract integration skipped because the executable is unavailable. Sixteen T2.2 cases passed. Ruff, `pip check`, controller `Validate`, and `git diff --check` passed. T1.2 visual before/after review passed.
- **GitHub:** `main` is synchronized through verified task T2.2 at `0b447ea`; workspace controller PR [#1](https://github.com/FreddyFreddyFred/receipt-graveyard/pull/1) merged as `cbd7f08`.
- **Workflow:** D18 records the user's approval to commit and push each verified task directly to `main` during this run.
- **Blockers:** Tesseract wrapper and mocked adapter checks pass, but this Windows environment has no Tesseract executable on PATH. The official Windows installer SHA-256 matches the official GitHub release, yet a non-admin per-user silent install produced no executable; Chocolatey reports this shell is non-elevated. The required clean-receipt OCR integration test is skipped, so T1.4 acceptance is incomplete. Revisit when a Tesseract executable is installed or its path is available.
- **Next action:** Review T2.4's scope and Git state, then begin it through the validated controller. Keep partial T1.4 changes isolated and revisit its blocker when a usable runtime is available.
