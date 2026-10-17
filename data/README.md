# Synthetic Sample Receipt Dataset

This directory contains deterministic, locally generated receipt images and their ground-truth sidecar. Every vendor, employee, date, and amount is fictional; no real transaction or personal information is included.

## Contents

- `sample_receipts/` contains 22 PNG images: 20 unique receipts and two intentional duplicates.
- `sample_policy.yaml` is a version 1 expense policy covering category caps, non-reimbursable items, city and context rules, approval thresholds, and client details.
- `exchange_rates.json` is a fixed USD rate snapshot dated 2026-10-16. It supports deterministic tests and is not transaction-date pricing or a settlement quote.
- `employee_manifest.json` maps all images to three fictional employees and records expected vendor, date, currency, total, line items, variant tags, and duplicate relationships.
- `scripts/generate_sample_data.py` regenerates the image set and manifest deterministically. It refuses to overwrite a file whose content differs from the generated output.

## Dataset Coverage

The 20 unique receipt images include clean scans, faded low-contrast scans, tilted scans, cursive-style synthetic handwriting, and receipts in USD, EUR, GBP, and JPY. `receipt-021-exact-duplicate.png` is byte-identical to `receipt-001.png`; `receipt-022-near-duplicate.png` is a resized and JPEG-recompressed copy of `receipt-006.png`. The manifest identifies both seeded pairs.

The handwriting variant uses OpenCV's script font with small deterministic position changes. It is a visual test approximation, not a sample of authentic handwriting. Receipt images are generated from fixed input records so extraction tests have known expected values.

## Expected Outcomes

- The exact and near duplicate pairs should be detected by the image perceptual-hash detector.
- The wine line on `receipt-018.png` should match the sample policy's non-reimbursable item rule.
- `receipt-012.png` exceeds the sample USD daily meal cap when evaluated by the per-receipt rule engine.
- Non-USD receipts require currency normalization before their values can be compared with USD policy limits.
- Currency conversion rounds to the destination currency's configured minor-unit precision using half-up rounding. The rate file records the ECB reference-rate source and snapshot date.
- `employee_manifest.json` is the ground truth for extraction and employee association checks.

## Manual Review Checklist

- [x] Confirm there are at least 20 readable PNG receipts in `sample_receipts/`.
- [x] Review clean, faded, rotated, and script-font handwriting variants.
- [x] Confirm USD, EUR, GBP, and JPY are represented in the visible receipt text and manifest.
- [x] Confirm both manifest duplicate references point to the intended source image.
- [x] Confirm all receipt employee IDs exist in the manifest's three-employee list.
- [x] Confirm the sample policy loads as version 1 and contains all six supported rule types.
- [x] Confirm the wine receipt is marked as non-reimbursable in the expected policy outcomes.
- [x] Confirm the static exchange-rate file loads with a fixed as-of date and source metadata.

## Regeneration

From the repository root, run:

```powershell
python .\scripts\generate_sample_data.py
```

The generator does not delete existing files. It leaves identical generated files untouched and stops if a target already exists with different content, so local modifications are preserved for review.
