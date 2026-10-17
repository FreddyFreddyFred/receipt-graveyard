# 🪦 The Receipt Graveyard

> An intelligent expense-receipt processing and policy-compliance system built for a hackathon.

[![CI](https://github.com/FreddyFreddyFred/receipt-graveyard/actions/workflows/ci.yml/badge.svg)](https://github.com/FreddyFreddyFred/receipt-graveyard/actions/workflows/ci.yml)

---

## What It Does

The Receipt Graveyard ingests messy, real-world receipt images (faded, rotated, multi-currency, handwritten) and:

1. **Extracts** structured data — vendor, date, amount, currency, line items, tax, tip
2. **Classifies** expenses against a configurable policy document (YAML)
3. **Detects** duplicates and suspicious submission patterns
4. **Produces** per-receipt compliance verdicts (Approved / Flagged / Denied) with human-readable explanations
5. **Generates** per-employee monthly summary reports

It replaces manual finance-team receipt review and removes friction for employees seeking reimbursement.

---

## Project Status

**🚧 Planning phase.** Architecture and task breakdown are complete. Implementation starts at [T0.1](PLAN.md#phase-0--project-setup--foundation).

---

## Documentation

| Document | Purpose |
|----------|---------|
| [PROJECT.md](PROJECT.md) | Product goals, MVP features, constraints, assumptions, definition of success |
| [PLAN.md](PLAN.md) | Full phased implementation plan with task dependencies, acceptance criteria, and verification steps |
| [DECISIONS.md](DECISIONS.md) | Architecture Decision Records (ADR) — all design choices and their rationale |
| [TASKS.json](TASKS.json) | Machine-readable task list — single source of truth for task status |

---

## Tech Stack (Planned)

| Layer | Technology |
|-------|-----------|
| Language | Python 3.10+ |
| Image preprocessing | OpenCV |
| OCR | Tesseract / EasyOCR / PaddleOCR (benchmarked in T1.5) |
| Data models | Pydantic v2 |
| Policy format | YAML |
| Database | SQLite |
| REST API | FastAPI |
| Logging | structlog |
| Testing | pytest + pytest-cov |
| Linting | ruff + mypy |

---

## Quick Start (Once Implemented)

```bash
# 1. Clone and set up virtual environment
git clone https://github.com/FreddyFreddyFred/receipt-graveyard.git
cd receipt-graveyard
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .

# 2. Process a folder of receipt images
python -m receipt_graveyard process \
  --receipts data/sample_receipts/ \
  --policy data/sample_policy.yaml \
  --output reports/

# 3. Start the REST API
uvicorn receipt_graveyard.api.app:app --reload
# Docs available at http://localhost:8000/docs
```

> **Note:** The above commands will work once T0.1–T7.2 are complete.

---

## Project Structure (Planned)

```
receipt-graveyard/
├── src/
│   └── receipt_graveyard/
│       ├── api/             # FastAPI routes & middleware
│       ├── ocr/             # OCR abstraction + engine adapters
│       ├── preprocessing/   # Image deskew, denoise, binarise
│       ├── extraction/      # Parse OCR text → structured Receipt
│       ├── policy/          # Policy YAML loader & rule evaluator
│       ├── detection/       # Duplicate & anomaly detection
│       ├── models/          # Pydantic data models
│       ├── reports/         # Report generation (JSON + Markdown)
│       ├── db/              # SQLite schema & repository
│       ├── pipeline/        # Orchestrator & verdict assembler
│       └── utils/           # Logging, config
├── tests/                   # Unit, integration, e2e, edge-case tests
├── data/
│   ├── sample_receipts/     # Test receipt images (≥20)
│   ├── sample_policy.yaml   # Sample expense policy
│   └── exchange_rates.json  # Static currency exchange rates
├── docs/                    # Additional documentation
├── .github/workflows/       # CI pipeline
├── PROJECT.md
├── PLAN.md
├── DECISIONS.md
└── TASKS.json
```

---

## License

TBD — to be decided before first public release.
