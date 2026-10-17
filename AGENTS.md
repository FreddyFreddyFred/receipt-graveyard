# Project rules

- Read `PROJECT.md`, `PLAN.md`, `TASKS.json`, and `DECISIONS.md` before project work. Treat `TASKS.json` as the canonical task ledger and keep `PLAN.md` synchronized with it.
- Validate the task graph with `scripts/run-project.ps1 -Action Validate` before each run. Dependencies must exist, be acyclic, and be completed with passing verification before a dependent task starts.
- Work on one required task at a time. Select the highest-priority ready required task; keep optional work separate. Record the exact reason for any blocked task and continue with another independent ready task when one exists.
- Before starting a task, inspect its scope, relevant files, and current Git state. Change only files in that task's scope. Run only checks supported by the project documentation and package scripts.
- Review changed files and the diff before recording completion. A task is complete only when its acceptance criteria pass and its verification evidence is recorded.
- After each verified task, update `TASKS.json`, `PLAN.md`, `STATE.md`, and `HANDOFF.md`. Stage only that task's intended files; never include unrelated user changes.
- Commit verified work locally, then run `git pull --rebase` and `git push`. If synchronization cannot proceed, preserve local work and record the exact failure in `STATE.md` and `HANDOFF.md`.
- Do not discard user changes, reset the repository, or perform destructive cleanup. Do not deploy, publish, spend money, expose secrets, or run destructive database migrations without explicit approval.
- Keep credentials and other secrets out of tracked files and all execution logs. The `logs/` directory is local and ignored by Git.
- Do not invent product requirements. If the approved application scope is unavailable, record the blocker and stop application implementation.
- Follow D16 in `DECISIONS.md` unless a later decision records an explicit user-approved workflow change. D18 records approval for this task run to commit and push each verified task directly to `main`; pull with rebase before pushing. Outside that approved run, use D16 feature branches and pull requests.
