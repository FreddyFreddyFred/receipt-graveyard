# PROJECT.md — The Receipt Graveyard

## 1. Product Goal

Build an intelligent expense-receipt processing system that:

1. **Ingests** messy, real-world receipt images (faded, rotated, cropped, handwritten, multi-currency).
2. **Extracts** structured data (vendor, date, amount, currency, line items, tax, tip).
3. **Applies** a company expense policy with layered rules (category caps, city-specific daily limits, non-reimbursable items, approval thresholds, client-name / attendee-count requirements, trip-vs-office context).
4. **Detects** duplicates, suspicious submissions, and accumulated limit breaches across a month.
5. **Produces** per-receipt compliance verdicts (approve / flag / deny) with human-readable explanations, and per-employee monthly summaries.

The system replaces manual squinting-at-receipts work for finance teams and removes friction for employees seeking reimbursement.

---

## 2. Required Features (MVP)

| ID | Feature | Notes |
|----|---------|-------|
| F1 | **Receipt image ingestion** | Accept JPEG/PNG/PDF; handle rotation, crop, fading |
| F2 | **OCR & data extraction** | Extract vendor, date, total, currency, line items, tax, tip |
| F3 | **Expense policy engine** | Parse a structured policy document; evaluate layered rules |
| F4 | **Category classification** | Map extracted items to policy categories (meals, transport, supplies, etc.) |
| F5 | **Currency normalisation** | Convert foreign currencies to a base currency for limit checks |
| F6 | **Duplicate detection** | Identify same receipt submitted twice (same or different channels) |
| F7 | **Anomaly / fraud flagging** | Detect suspicious patterns (round numbers, frequency, just-under-limit) |
| F8 | **Cumulative limit tracking** | Track per-employee daily / monthly / trip totals against policy caps |
| F9 | **Compliance verdict** | Per-receipt decision: Approved · Flagged for Review · Denied, with reasons |
| F10 | **Monthly summary report** | Per-employee report of all receipts, verdicts, and totals |
| F11 | **REST API** | Endpoints for upload, status, verdict retrieval, and report generation |
| F12 | **Error handling & logging** | Graceful degradation on bad images; structured logging throughout |

## 3. Optional Improvements (Post-MVP)

| ID | Feature |
|----|---------|
| O1 | Web dashboard UI for finance reviewers |
| O2 | Email / Slack integration for receipt submission |
| O3 | Configurable policy editor UI |
| O4 | Multi-tenant support |
| O5 | Receipt data correction workflow (human-in-the-loop) |
| O6 | Exportable audit trail (CSV / PDF) |
| O7 | ML-based category classifier trained on company history |

---

## 4. Constraints

| # | Constraint |
|---|-----------|
| C1 | **No paid third-party services** unless explicitly approved (e.g., no paid cloud OCR APIs). Use open-source OCR (Tesseract / EasyOCR / PaddleOCR). |
| C2 | **No production deployment** — the system must be runnable locally or in a dev/test environment. |
| C3 | **No destructive operations** on user data; all originals are preserved. |
| C4 | Must handle the "messy" dataset described: faded thermal prints, rotations, partial data, math errors, duplicates. |
| C5 | Policy rules must be data-driven (loaded from a config/file), not hard-coded. |

## 5. Assumptions

| # | Assumption |
|---|-----------|
| A1 | The expense policy will be provided as a structured document (JSON/YAML) or will be manually transcribed into one. |
| A2 | Receipt images will be provided as files on disk (a folder of images); no live camera capture needed. |
| A3 | A reasonable set of sample/test receipts and a sample policy document will be created for development and testing. |
| A4 | Python 3.10+ is the primary language (rich OCR/ML ecosystem). |
| A5 | Base currency is USD unless the policy specifies otherwise. |
| A6 | Employee identity is conveyed via metadata (filename convention or a manifest file), not extracted from the receipt itself. |
| A7 | "Month of receipts" means batch processing; real-time streaming is not required for MVP. |
| A8 | Exchange rates can use a static/bundled table for MVP; live rates are an optional improvement. |

## 6. Out of Scope

- Payroll integration or actual fund disbursement.
- Tax filing or regulatory compliance beyond company policy.
- Mobile app or native desktop client.
- User authentication / authorisation (dev/test mode only).
- Training custom ML models (use pre-trained / rule-based approaches).
- Multi-language receipt support beyond English (unless trivially handled by OCR engine).

## 7. Definition of Success

1. Given a folder of ≥ 20 sample receipt images (including duplicates, bad scans, multi-currency) and a sample expense policy, the system produces a correct compliance verdict for **≥ 90 %** of receipts.
2. Duplicates are detected with **zero false negatives** on exact-match duplicates and reasonable accuracy on near-duplicates.
3. Cumulative daily/monthly limits are correctly enforced across an employee's submission timeline.
4. Every verdict includes a human-readable explanation referencing the specific policy rule(s).
5. The full pipeline (ingest → extract → classify → evaluate → report) runs end-to-end via a single CLI command or API call.
6. All required features have automated tests that pass.
