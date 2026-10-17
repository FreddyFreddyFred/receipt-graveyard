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
