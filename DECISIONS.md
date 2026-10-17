# DECISIONS.md — Architecture & Design Decisions

> Living document. Each decision is numbered. Unresolved choices are marked with ❓.
> Update status when a decision is made.

---

## D1 — Primary Language & Runtime

**Status:** ✅ Decided  
**Decision:** Python 3.10+ with virtual-env based dependency management.  
**Rationale:** Best ecosystem for OCR (Tesseract/EasyOCR/PaddleOCR), image processing (Pillow/OpenCV), and data manipulation (pandas). FastAPI for the REST layer.

---

## D2 — OCR Engine Selection

**Status:** ❓ Needs evaluation during T1.4  
**Options:**
| Option | Pros | Cons |
|--------|------|------|
| Tesseract (pytesseract) | Mature, widely used, easy install | Weaker on rotated/noisy images without preprocessing |
| EasyOCR | Good multi-language, handles rotations | Heavier dependency (PyTorch) |
| PaddleOCR | State-of-art accuracy, fast | PaddlePaddle dependency, less common on Windows |

**Plan:** Implement behind an abstraction interface; benchmark all three on sample receipts in task T1.4, then choose.

---

## D3 — Policy Document Format

**Status:** ✅ Decided  
**Decision:** YAML file with a well-defined schema.  
**Rationale:** YAML is human-readable, supports comments (useful for documenting policy intent), and maps cleanly to Python dicts. JSON schema validation will be applied on load.

---

## D4 — Data Storage (MVP)

**Status:** ✅ Decided  
**Decision:** SQLite for structured data (receipts, verdicts, employee totals); filesystem for receipt images.  
**Rationale:** Zero-config, portable, sufficient for single-user / batch-mode MVP. No external database server to manage.

---

## D5 — Currency Conversion Strategy

**Status:** ✅ Decided (MVP) / ❓ Post-MVP  
**Decision (MVP):** Bundled static exchange-rate table (JSON file, rates as of a fixed date).  
**Decision (Post-MVP):** Optionally fetch live rates from a free API (e.g., exchangerate.host).  
**Rationale:** Avoids paid-service dependency. Static rates are deterministic and testable.

---

## D6 — Duplicate Detection Strategy

**Status:** ✅ Decided  
**Decision:** Two-layer approach:
1. **Exact duplicate:** perceptual hash (pHash) of the receipt image.
2. **Semantic duplicate:** match on (employee, vendor, date, amount) tuple within a tolerance window.

**Rationale:** Covers both "same photo uploaded twice" and "same receipt entered manually and also photographed."

---

## D7 — Image Preprocessing Pipeline

**Status:** ✅ Decided  
**Decision:** OpenCV-based pipeline: deskew → denoise → contrast enhancement → binarisation → crop/border removal, applied before OCR.  
**Rationale:** Directly addresses the "faded, rotated, cropped" receipt challenge.

---

## D8 — API Framework

**Status:** ✅ Decided  
**Decision:** FastAPI  
**Rationale:** Async-capable, auto-generates OpenAPI docs, Pydantic model validation, lightweight.

---

## D9 — Anomaly / Fraud Detection Approach

**Status:** ✅ Decided (MVP)  
**Decision:** Rule-based heuristics for MVP:
- Receipts with round-number totals (e.g., \$50.00, \$100.00)
- Totals just under policy limits (within 5%)
- High submission frequency from a single employee
- Weekend/holiday submissions for non-travel expenses
- Line-item math that doesn't reconcile with the stated total

**Post-MVP:** Statistical outlier detection (z-score / IQR on per-employee distributions).

---

## D10 — Employee Identity Mapping

**Status:** ✅ Decided  
**Decision:** A manifest CSV/JSON file maps each receipt filename (or a filename prefix/folder) to an employee ID and optional metadata (department, trip ID, city).  
**Rationale:** Receipt images don't reliably contain employee identity. A sidecar manifest is simple and flexible.

---

## D11 — Report Output Format

**Status:** ✅ Decided  
**Decision:** JSON as the canonical machine-readable format + Markdown for human review. HTML deferred to optional post-MVP (O6).  
**Rationale:** JSON is trivially testable (schema validation) and consumable by other tools. Markdown renders natively in GitHub, Slack, and most review tools without extra tooling. Keeping HTML optional avoids scope creep for the hackathon deadline.

---

## D12 — Test Data Strategy

**Status:** ✅ Decided  
**Decision:** Create a synthetic test dataset:
- 20–30 receipt images (mix of clean, faded, rotated, handwritten, multi-currency)
- A sample expense policy YAML covering all rule types
- A manifest mapping receipts to 3–4 fictitious employees
- Known duplicates and policy violations seeded intentionally

**Rationale:** Enables deterministic, repeatable testing with known expected outcomes.

---

## D13 — Project Structure Convention

**Status:** ✅ Decided  
**Decision:**
```
MyApp/
├── src/
│   └── receipt_graveyard/      # Main package
│       ├── api/                # FastAPI routes
│       ├── ocr/                # OCR abstraction + engines
│       ├── preprocessing/      # Image preprocessing
│       ├── extraction/         # Data extraction from OCR output
│       ├── policy/             # Policy engine
│       ├── detection/          # Duplicate & anomaly detection
│       ├── models/             # Pydantic / DB models
│       ├── reports/            # Report generation
│       └── utils/              # Shared utilities
├── tests/                      # Mirrors src structure
├── data/
│   ├── sample_receipts/        # Test receipt images
│   ├── sample_policy.yaml      # Sample expense policy
│   └── exchange_rates.json     # Static exchange rates
├── docs/                       # Additional documentation
├── PROJECT.md
├── PLAN.md
├── TASKS.json
├── DECISIONS.md
├── requirements.txt
└── pyproject.toml
```

---

## D14 — Logging Framework

**Status:** ✅ Decided  
**Decision:** Python `logging` module with `structlog` for structured JSON log output.  
**Rationale:** Standard library base ensures compatibility; structlog adds machine-parseable output useful for debugging the extraction pipeline.

---

## D15 — Line-Item Math Reconciliation

**Status:** ✅ Decided  
**Decision:** When line items are extractable, sum them and compare to the stated total. Flag discrepancies exceeding a configurable tolerance (default: \$0.50 or 2%, whichever is greater).  
**Rationale:** Thermal receipts often have OCR errors in digits; a small tolerance avoids false positives while still catching genuine mismatches.

---

## D16 — Branching Strategy

**Status:** ✅ Decided  
**Decision:** GitHub Flow — feature branches off `main`, merged via pull requests (self-reviewed for solo work).

**Rules:**
1. `main` is always in a working / passing-CI state. Never commit directly to `main`.
2. Create a branch per task: `feature/T0.1-project-setup`, `feature/T1.2-preprocessing`, etc.
3. Open a PR when the task acceptance criteria are met and all tests pass.
4. Squash-merge into `main` to keep the history clean.
5. Delete the feature branch after merge.

**Branch naming convention:** `feature/<task-id>-<short-slug>` (e.g. `feature/T3.2-policy-evaluator`)  
**Hotfix naming:** `fix/<short-slug>` (e.g. `fix/gitignore-missing`)

**Rationale:** GitHub Flow is simple, low-overhead, and works well for solo or small-team hackathon projects. It keeps `main` deployable at all times and provides natural checkpoints (PRs) to verify acceptance criteria before merging.

---

## D17 — Recoverable Task Controller

**Status:** ✅ Decided
**Decision:** Keep the existing `TASKS.json` schema and task graph as canonical. The Windows PowerShell controller validates that schema, requires verified prerequisites before starting dependent tasks, and stores logs only in the ignored `logs/` directory.
**Rationale:** Preserve the approved 48-task project plan while adding task-by-task recovery across sessions.

## D18 — User-Approved Main-Branch Task Run

**Status:** ✅ Approved for this task run
**Decision:** Per the user's explicit instruction on 2026-10-18, merge the verified workspace setup into `main`, then commit and push each individually verified required task directly to `main`. Before each push, synchronize with `git pull --rebase`. This approval supersedes D16 only for the current task run; otherwise D16 remains the default.
**Rationale:** The user requested a continuously updated `main` branch with each completed task pushed as soon as it passes acceptance checks.

## D19 — Initial Installable Package Boundary

**Status:** ✅ Clarified
**Decision:** T0.1 creates the root `src/receipt_graveyard/__init__.py` because its editable-install acceptance criteria require importing `receipt_graveyard`. T0.2 creates the remaining sub-package directories and initializers.
**Rationale:** This keeps the dependency graph executable: a package must exist before T0.1 can verify installation and import, while T0.2 remains responsible for the complete D13 structure.

## D20 — Core Model Contracts

**Status:** ✅ Decided
**Decision:** Represent money and quantities with `Decimal`. Receipt extraction fields, line-item quantity/amount details, and employee context metadata remain optional when source data is incomplete; a receipt's line-item collection defaults to empty. Line-item descriptions, employee IDs, policy rule IDs/types, and verdict receipt IDs/statuses are required. `PolicyRule` carries a rule `type` and generic `parameters`; T3.1 validates the type-specific schema. Verdict status values are `Approved`, `Flagged for Review`, and `Denied`, with empty-by-default reasons and rule IDs.
**Rationale:** These contracts preserve incomplete OCR results, avoid binary floating-point arithmetic for money, and leave policy-rule validation to the task dedicated to the policy schema.

## D21 — Version 1 Expense Policy Schema

**Status:** ✅ Decided
**Decision:** A policy document has `version: 1` and a non-empty `rules` list; `base_currency` is optional and defaults to USD. When supplied, it must be an uppercase ISO-style code. Rule IDs are unique. Supported rule types are `category_cap`, `non_reimbursable`, `city_daily_limit`, `context_limit`, `approval_threshold`, and `client_attendee_requirement`; each type has a closed, type-specific parameter schema. Unknown fields and rule types are rejected. YAML floating-point values in rule parameters are converted to `Decimal` after JSON Schema validation.
**Rationale:** One versioned and strict format gives policy evaluation, sample data, and documentation a stable contract while preserving exact monetary values.

## D22 — Per-Receipt Policy Evaluation Boundary

**Status:** ✅ Decided
**Decision:** T3.2 evaluates category caps against the sum of matching line items on the current receipt and detects non-reimbursable description matches. Over-cap amounts and incomplete amount data are flagged for review; non-reimbursable items are denied. A currency mismatch is flagged instead of comparing unlike amounts. The result carries structured violations with rule IDs and can be converted to the shared `Verdict` model. Aggregate daily/monthly/trip totals, context rules, and currency conversion remain with their later tasks.
**Rationale:** Keep the evaluator accurate with the information available from one receipt, preserve audit references, and avoid false approvals when amounts or currencies cannot be safely compared.

## D23 — Perceptual Duplicate Hash

**Status:** ✅ Decided
**Decision:** T4.1 computes a 64-bit perceptual hash from a grayscale image resized to 32×32 and transformed with the 2-D DCT. It compares hashes using Hamming distance, with a default duplicate threshold of 10 differing bits; callers can choose a validated threshold from 0 through 64.
**Rationale:** OpenCV is already a required project dependency, and this compact pHash supports resized and JPEG-recompressed image comparisons without adding a third-party package.

## D24 — Cumulative Limit Tracker State

**Status:** ✅ Decided
**Decision:** T4.3 uses a stateful, in-memory tracker that receives receipts in submission order and accumulates `category_cap` rules with daily or monthly periods by employee and rule. It flags the receipt that crosses the cap without changing prior results. Incomplete amounts or incomparable currencies taint the affected period and keep later checks flagged; trip-period rules are surfaced for review until trip context is available.
**Rationale:** The running totals require batch state, and conservative flags prevent a missing amount or unsupported time window from causing a later receipt to appear compliant.

## D25 — Structured Logging Configuration

**Status:** ✅ Decided
**Decision:** T0.3 configures structlog to write JSON records with timestamp, level, event, and bound context. `RECEIPT_GRAVEYARD_LOG_LEVEL` controls the minimum level; INFO is the default, with DEBUG, INFO, WARNING, ERROR, and CRITICAL accepted.
**Rationale:** A predictable JSON event format supports local debugging and later pipeline integration without an external logging service.

## D26 — Synthetic Receipt Fixtures

**Status:** ✅ Decided
**Decision:** T1.3 uses generated, fictional receipts with deterministic ground-truth metadata. The dataset includes 20 unique PNGs plus exact and resized/recompressed duplicate copies, at least three employee IDs, four currency codes, and low-contrast, tilted, and script-font approximations of handwriting. The generator refuses to overwrite any existing output whose bytes differ from its deterministic result.
**Rationale:** Synthetic fixtures provide known expected values without publishing real employee or purchase data, and deterministic generation makes tests repeatable while protecting local edits.

## D27 — Static Currency Snapshot

**Status:** ✅ Decided
**Decision:** T2.2 uses a bundled USD-normalized rate table dated 2026-10-16. The currency module derives each USD-per-unit rate from the ECB's published EUR-base reference rates, detects the configured symbols and ISO codes, and rounds converted values to the destination currency's minor units. Missing or unsupported source currency defaults to the requested base with an explicit warning; conflicting markers raise an ambiguity error. The snapshot is for deterministic MVP checks, not historical transaction pricing or settlement.
**Rationale:** A dated, sourced table follows the approved static-rate strategy, gives repeatable tests, and makes its limits visible to callers.
