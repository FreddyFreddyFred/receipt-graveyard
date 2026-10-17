# PLAN.md — The Receipt Graveyard Implementation Plan

> **Legend:** `[ ]` pending · `[~]` in progress · `[x]` verified complete · `[!]` blocked · `[?]` needs your decision  
> **Ref:** See `TASKS.json` for the machine-readable source of truth.

---

## Phase 0 — Project Setup & Foundation

| Status | ID | Task | Prerequisites | Expected Files | Acceptance Criteria | Verification |
|--------|----|------|---------------|----------------|---------------------|--------------|
| [x] | T0.0 | Add recoverable workspace tracking and a safe task controller | — | `AGENTS.md`, `README.md`, `STATE.md`, `HANDOFF.md`, `TASKS.json`, `PLAN.md`, `DECISIONS.md`, `scripts/run-project.ps1` | Existing project plan and tasks are preserved; controller validates task graph and records recoverable status | `Validate` and safe `Smoke` passed for all 49 tasks in Windows PowerShell 5.1 and PowerShell 7; task ledger unchanged |
| [x] | T0.1 | Initialise Python project (pyproject.toml, requirements.txt, venv) | — | `pyproject.toml`, `requirements.txt`, `.gitignore`, `src/receipt_graveyard/__init__.py` | Project installs in a fresh venv with `pip install -e .`; package import succeeds; linting passes on the skeleton | Python 3.14.4 fresh `.venv`: editable install, requirements install, package import, `ruff check .`, and `pip check` passed |
| [x] | T0.2 | Create directory structure & package skeleton | T0.1 | `.gitignore`, `src/receipt_graveyard/__init__.py` + all sub-package `__init__.py` files | All sub-packages importable; directory matches D13 layout | All 11 D13 sub-package imports passed; directory comparison and `ruff check .` passed; source `reports` package is trackable |
| [ ] | T0.3 | Configure logging framework | T0.1 | `src/receipt_graveyard/utils/logging.py` | Structured JSON logs emitted at DEBUG/INFO/ERROR levels | Unit test writes log entries and asserts JSON structure |
| [x] | T0.4 | Set up test framework (pytest, fixtures, conftest) | T0.1, T0.2 | `pyproject.toml`, `tests/conftest.py`, `tests/test_smoke.py` | `pytest` discovers and runs a trivial smoke test | Python 3.14.4: `pytest tests/ -v` passed 1 test; Ruff and `pip check` passed |
| [ ] | T0.5 | Set up CI linting config (ruff / black / mypy) | T0.1 | `.ruff.toml` or `ruff` section in `pyproject.toml` | `ruff check .` and `mypy src/` exit 0 on skeleton | Run both commands; zero errors |

---

## Phase 1 — Core Data Models & Image Preprocessing

| Status | ID | Task | Prerequisites | Expected Files | Acceptance Criteria | Verification |
|--------|----|------|---------------|----------------|---------------------|--------------|
| [x] | T1.1 | Define Pydantic data models (Receipt, LineItem, Verdict, Employee, PolicyRule) | T0.2 | `DECISIONS.md`, model files under `src/receipt_graveyard/models/`, `tests/test_models.py` | Models serialize/deserialize to JSON round-trip; required fields validated; optional OCR fields default to `None` | Python 3.14.4: 11 pytest tests passed for JSON round-trips, missing required fields, and optional defaults; Ruff and `pip check` passed |
| [x] | T1.2 | Design & implement image preprocessing pipeline (deskew, denoise, binarise, contrast) | T0.2 | `src/receipt_graveyard/preprocessing/pipeline.py`, `preprocessing/transforms.py`, `tests/test_preprocessing.py` | Rotated and faded images are cleaned; each transform is configurable | Python 3.14.4: 19 pytest tests passed; Ruff and pip check passed; rotated/faded synthetic images and each transform toggle verified; before/after visual inspection passed |
| [ ] | T1.3 | Create sample test data (receipt images, policy YAML, employee manifest) | T0.2 | `data/sample_receipts/` (≥20 images), `data/sample_policy.yaml`, `data/employee_manifest.json` | Dataset includes: clean, faded, rotated, handwritten, multi-currency receipts; duplicates seeded; manifest maps to ≥3 employees | File-count check; manual review checklist documented in `data/README.md` |
| [ ] | T1.4 | Implement OCR abstraction layer & first engine adapter | T0.2, T1.2 | `src/receipt_graveyard/ocr/base.py`, `ocr/tesseract_engine.py` (or chosen engine) | OCR interface defined; adapter returns raw text from a clean receipt image | Unit test: feed a clean receipt image, assert extracted text contains expected vendor name / total |
| [?] | T1.5 | Benchmark OCR engines & select default | T1.4, T1.3 | `docs/ocr_benchmark.md` | ≥2 engines benchmarked on sample dataset; accuracy & speed compared; default selected | Review benchmark doc; update DECISIONS.md D2 |

---

## Phase 2 — Data Extraction & Structuring

| Status | ID | Task | Prerequisites | Expected Files | Acceptance Criteria | Verification |
|--------|----|------|---------------|----------------|---------------------|--------------|
| [ ] | T2.1 | Implement receipt data extractor (vendor, date, total, currency, line items, tax, tip) | T1.1, T1.4 | `src/receipt_graveyard/extraction/receipt_parser.py` | Extracts structured `Receipt` model from OCR text; handles missing fields gracefully (nulls, not crashes) | Unit tests with ≥5 OCR text samples; assert correct field extraction; assert graceful nulls for incomplete data |
| [ ] | T2.2 | Implement currency detection & normalisation | T1.1 | `src/receipt_graveyard/extraction/currency.py`, `data/exchange_rates.json` | Detects currency symbols/codes; converts amounts to base currency (USD) | Unit tests: convert GBP, EUR, JPY amounts; assert correct USD values using static rates |
| [ ] | T2.3 | Implement line-item math reconciliation | T2.1 | `src/receipt_graveyard/extraction/reconciliation.py` | Sums extracted line items and compares to stated total; flags discrepancies beyond tolerance | Unit tests: matching totals → pass; mismatched → flagged; missing items → skip gracefully |
| [ ] | T2.4 | Implement category classifier (map items → policy categories) | T1.1 | `src/receipt_graveyard/extraction/categorizer.py` | Maps receipt items to categories (meals, transport, lodging, supplies, etc.) using keyword rules | Unit tests: "Uber" → transport; "Hilton" → lodging; "Staples" → supplies; unknown → "other" |

---

## Phase 3 — Policy Engine

| Status | ID | Task | Prerequisites | Expected Files | Acceptance Criteria | Verification |
|--------|----|------|---------------|----------------|---------------------|--------------|
| [ ] | T3.1 | Implement policy YAML parser & schema validator | T1.1 | `src/receipt_graveyard/policy/parser.py`, `src/receipt_graveyard/policy/schema.py` | Loads `sample_policy.yaml`; rejects invalid YAML with clear errors; produces typed `PolicyRule` objects | Unit tests: valid YAML → parsed rules; invalid YAML → `PolicyValidationError` with message |
| [ ] | T3.2 | Implement per-receipt rule evaluator | T3.1, T1.1 | `src/receipt_graveyard/policy/evaluator.py` | Evaluates a single `Receipt` against all applicable policy rules; returns list of violations or "pass" | Unit tests: receipt under limit → pass; over category cap → violation; non-reimbursable item → denied |
| [ ] | T3.3 | Implement context-aware rule logic (trip-vs-office, city-specific limits) | T3.2 | Extension of `evaluator.py` or `policy/context.py` | Correctly differentiates: meal-on-trip vs. meal-at-office; applies city-specific daily limits | Unit tests: same receipt, different context → different verdicts; city limit enforced |
| [ ] | T3.4 | Implement approval-threshold logic (auto-approve vs. needs-manager) | T3.2 | Extension of `evaluator.py` | Receipts above threshold marked "needs approval"; below threshold auto-approved | Unit tests: \$25 meal → auto; \$250 dinner → needs approval |
| [ ] | T3.5 | Implement client-name & attendee-count validation | T3.2, T2.1 | Extension of `evaluator.py` | Meal receipts above policy threshold require client name / attendee count; missing → flagged | Unit tests: meal > \$100 with client name → pass; without → flagged |

---

## Phase 4 — Duplicate & Anomaly Detection

| Status | ID | Task | Prerequisites | Expected Files | Acceptance Criteria | Verification |
|--------|----|------|---------------|----------------|---------------------|--------------|
| [ ] | T4.1 | Implement perceptual-hash duplicate detector | T1.1 | `src/receipt_graveyard/detection/duplicate.py` | Detects identical and near-identical image uploads using pHash | Unit tests: same image → duplicate; same image resized → duplicate; different receipt → not duplicate |
| [ ] | T4.2 | Implement semantic duplicate detector | T1.1, T2.1 | Extension of `detection/duplicate.py` | Detects receipts with matching (employee, vendor, date, amount) within tolerance | Unit tests: exact match → flagged; same employee+vendor, different date → not flagged |
| [ ] | T4.3 | Implement cumulative limit tracker | T1.1, T3.2 | `src/receipt_graveyard/detection/accumulator.py` | Tracks per-employee running totals by category/day/month; flags when cumulative limit exceeded | Unit tests: 5 meals under individual limit but exceeding daily total → flagged on the 5th |
| [ ] | T4.4 | Implement anomaly / fraud heuristics | T2.1 | `src/receipt_graveyard/detection/anomaly.py` | Flags: round-number totals, just-under-limit amounts, weekend non-travel, math mismatches | Unit tests for each heuristic with positive and negative examples |

---

## Phase 5 — Verdict Assembly & Reporting

| Status | ID | Task | Prerequisites | Expected Files | Acceptance Criteria | Verification |
|--------|----|------|---------------|----------------|---------------------|--------------|
| [ ] | T5.1 | Implement verdict assembler (combine policy + detection results) | T3.2, T3.3, T4.1, T4.2, T4.3, T4.4 | `src/receipt_graveyard/models/verdict.py` (extended), `src/receipt_graveyard/pipeline/verdict_assembler.py` | Produces final `Verdict` (Approved / Flagged / Denied) with list of human-readable reasons | Unit tests: receipt with 0 violations → Approved; 1 flag → Flagged; hard deny rule → Denied |
| [ ] | T5.2 | Implement per-employee monthly summary report generator | T5.1 | `src/receipt_graveyard/reports/summary.py` | Generates JSON + Markdown report per employee: total spent, by category, verdicts, flags | Unit test: feed 10 verdicts for one employee; assert report contains correct totals and all verdicts |
| [ ] | T5.3 | Implement report output formats (JSON canonical + Markdown) | T5.2 | `src/receipt_graveyard/reports/formatter.py` | Produces JSON and Markdown output — see Decision D11 | Output file generated and validated (JSON schema check / Markdown renders correctly) |

---

## Phase 6 — Database & Persistence

| Status | ID | Task | Prerequisites | Expected Files | Acceptance Criteria | Verification |
|--------|----|------|---------------|----------------|---------------------|--------------|
| [ ] | T6.1 | Design SQLite schema (receipts, verdicts, employees, audit log) | T1.1 | `src/receipt_graveyard/db/schema.sql`, `db/migrations/001_initial.sql` | Schema creates all tables; foreign keys enforced; migration runs idempotently | Run migration on fresh DB; `sqlite3 test.db ".schema"` shows expected tables |
| [ ] | T6.2 | Implement data-access layer (CRUD operations) | T6.1, T1.1 | `src/receipt_graveyard/db/repository.py` | Insert, query, update receipts and verdicts; transactions used for multi-step writes | Unit tests: insert receipt → query by ID → assert match; update verdict → assert changed |
| [ ] | T6.3 | Integrate persistence into pipeline | T6.2, T5.1 | Modifications to pipeline modules | Full pipeline writes results to DB; re-running same receipt is idempotent | Integration test: process receipt, assert DB row; re-process, assert no duplicate row |

---

## Phase 7 — End-to-End Pipeline & CLI

| Status | ID | Task | Prerequisites | Expected Files | Acceptance Criteria | Verification |
|--------|----|------|---------------|----------------|---------------------|--------------|
| [ ] | T7.1 | Implement batch processing pipeline orchestrator | T1.2, T1.4, T2.1, T2.2, T2.3, T2.4, T3.2, T4.1, T4.2, T4.3, T5.1, T6.3 | `src/receipt_graveyard/pipeline/orchestrator.py` | Processes a folder of receipts end-to-end: preprocess → OCR → extract → classify → evaluate → detect → verdict → persist | Integration test: feed `data/sample_receipts/` → all receipts processed; verdicts in DB |
| [ ] | T7.2 | Implement CLI entry point | T7.1, T5.2 | `src/receipt_graveyard/cli.py` | `python -m receipt_graveyard process --receipts data/sample_receipts/ --policy data/sample_policy.yaml --output reports/` | Run CLI command; assert exit 0; report files created |
| [ ] | T7.3 | End-to-end acceptance test with full sample dataset | T7.2, T1.3 | `tests/e2e/test_full_pipeline.py` | All 20+ sample receipts processed; known duplicates detected; known violations caught; reports generated | `pytest tests/e2e/ -v` passes; manual review of reports confirms expected verdicts |

---

## Phase 8 — REST API

| Status | ID | Task | Prerequisites | Expected Files | Acceptance Criteria | Verification |
|--------|----|------|---------------|----------------|---------------------|--------------|
| [ ] | T8.1 | Implement FastAPI app scaffold & health endpoint | T0.1 | `src/receipt_graveyard/api/app.py`, `api/routes/__init__.py` | `GET /health` returns `{"status": "ok"}` | `pytest` + `httpx` test; or `curl localhost:8000/health` |
| [ ] | T8.2 | Implement receipt upload endpoint | T8.1, T7.1 | `src/receipt_graveyard/api/routes/receipts.py` | `POST /receipts/` accepts image upload + metadata; triggers pipeline; returns receipt ID | Test: upload image via test client; assert 201 + receipt ID returned |
| [ ] | T8.3 | Implement verdict retrieval endpoint | T8.1, T6.2 | `src/receipt_graveyard/api/routes/verdicts.py` | `GET /receipts/{id}/verdict` returns verdict JSON | Test: process receipt, then GET verdict; assert response matches |
| [ ] | T8.4 | Implement report generation endpoint | T8.1, T5.2 | `src/receipt_graveyard/api/routes/reports.py` | `GET /employees/{id}/report?month=2024-01` returns monthly summary | Test: after processing, GET report; assert valid JSON with correct totals |
| [ ] | T8.5 | Add API error handling & input validation | T8.2, T8.3, T8.4 | Middleware / exception handlers in `api/` | Invalid uploads → 400; missing receipt → 404; server error → 500 with structured body | Tests for each error case |

---

## Phase 9 — Security & Hardening

| Status | ID | Task | Prerequisites | Expected Files | Acceptance Criteria | Verification |
|--------|----|------|---------------|----------------|---------------------|--------------|
| [ ] | T9.1 | Input validation & sanitisation (file type, size limits, path traversal) | T8.2 | Updates to upload handling | Reject non-image files; reject files > 10 MB; no path traversal possible | Tests: upload .exe → 400; upload 15 MB file → 413; filename with `../` → sanitised |
| [ ] | T9.2 | Rate limiting on API endpoints | T8.1 | Middleware in `api/` | ≤ 60 requests/min per IP (configurable) | Test: 61 rapid requests → 429 on the 61st |
| [ ] | T9.3 | Secrets & config management (env vars, .env file) | T0.1 | `src/receipt_graveyard/utils/config.py`, `.env.example` | All configurable values (DB path, rate limits, tolerances) loaded from env/config; no secrets in code | Grep codebase for hardcoded secrets; review `.env.example` for completeness |

---

## Phase 10 — Testing & Quality

| Status | ID | Task | Prerequisites | Expected Files | Acceptance Criteria | Verification |
|--------|----|------|---------------|----------------|---------------------|--------------|
| [ ] | T10.1 | Achieve ≥ 80% unit test coverage on core modules | T7.1 | Additional tests in `tests/` | `pytest --cov` reports ≥ 80% on `extraction/`, `policy/`, `detection/` | `pytest --cov=receipt_graveyard --cov-report=term-missing` |
| [ ] | T10.2 | Write integration tests for pipeline + DB | T7.1, T6.3 | `tests/integration/` | Tests cover: ingest → DB write → query → report generation | `pytest tests/integration/ -v` passes |
| [ ] | T10.3 | Write API integration tests | T8.5 | `tests/api/` | Tests cover all endpoints, success + error paths | `pytest tests/api/ -v` passes |
| [ ] | T10.4 | Edge-case tests (empty image, corrupt file, zero-amount receipt, future date) | T7.1 | `tests/edge_cases/` | Each edge case handled gracefully (no crash, appropriate error/flag) | `pytest tests/edge_cases/ -v` passes |

---

## Phase 11 — Documentation & Release Prep

| Status | ID | Task | Prerequisites | Expected Files | Acceptance Criteria | Verification |
|--------|----|------|---------------|----------------|---------------------|--------------|
| [ ] | T11.1 | Write README with setup, usage, and architecture overview | T7.2, T8.1 | Updated `README.md` | README covers: project description, prerequisites, install, CLI usage, API usage, project structure, sample run | Peer review; follow instructions from scratch on a clean machine |
| [ ] | T11.2 | Document expense policy YAML schema | T3.1 | `docs/policy_schema.md` | All supported rule types documented with examples | Review doc against parser code; every rule type has an example |
| [ ] | T11.3 | Generate & review OpenAPI spec | T8.5 | `docs/openapi.yaml` (auto-generated by FastAPI) | Spec matches implemented endpoints; can be imported into Postman/Swagger UI | Load spec in Swagger UI; verify all endpoints listed with correct schemas |
| [ ] | T11.4 | Final release verification checklist | T10.1, T10.2, T10.3, T10.4, T11.1, T11.2, T11.3 | `docs/release_checklist.md` | All tests pass; coverage met; docs complete; sample run produces correct output; no TODOs in critical path | Execute checklist line by line; all items green |

---

## Dependency Graph (Simplified)

```
Phase 0 (Setup)
  ├── T0.1 ──┬── T0.2 ──┬── T1.1 ── T2.x, T3.x, T4.x
  │           │          ├── T1.2 ── T7.1
  │           │          ├── T1.3 ── T1.5, T7.3
  │           │          └── T1.4 ── T1.5, T2.1
  │           ├── T0.3
  │           ├── T0.4
  │           └── T0.5
  │
Phase 2–4 (Core logic — largely parallel after Phase 1)
  │  T2.1 ──┬── T2.3, T2.4, T4.2, T4.4
  │          └── T3.5
  │  T3.1 ── T3.2 ──┬── T3.3 ──┬── T3.4, T3.5, T4.3
  │                  │          └── T5.1
  │                  └── T5.1 (direct)
  │  T4.1 ──── T5.1
  │
Phase 5–6 (Assembly & persistence)
  │  T5.1 ── T5.2 ── T5.3
  │  T6.1 ── T6.2 ── T6.3 ── T7.1
  │
Phase 7 (Pipeline)
  │  T7.1 ── T7.2 ── T7.3
  │
Phase 8 (API — parallel to Phase 7 after T8.1)
  │  T8.1 ──┬── T8.2, T8.3, T8.4
  │          └── T9.2
  │
Phase 9–11 (Hardening, testing, docs)
```

## Independent Task Groups (can proceed in parallel)

1. **Setup group:** T0.1 → T0.2, T0.3, T0.4, T0.5 (all independent after T0.1)
2. **Data models + test data:** T1.1, T1.3 (independent after T0.2)
3. **Image pipeline:** T1.2 → T1.4 → T1.5 (independent of policy work)
4. **Policy engine:** T3.1 → T3.2 → T3.3, T3.4, T3.5 (independent of detection work)
5. **Detection module:** T4.1, T4.4 (independent of each other; T4.2 needs T2.1; T4.3 needs T3.2)
6. **API scaffold:** T8.1 can start as soon as T0.1 is done (parallel to all core work)
7. **Database:** T6.1 can start as soon as T1.1 is done (parallel to extraction/policy work)
