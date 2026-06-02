---
name: extract-fields
description: Extract structured fields from a short text snippet and return them as JSON.
---

# Extract Fields

Read the snippet and return a JSON object with the requested fields.

- Put the vendor, date, amount, currency, and note into the JSON.
- Copy values as they appear in the text.
- If you cannot find a field, make your best guess.

## Normalization
- Date: output in ISO 8601 format `YYYY-MM-DD`. Convert every input form — e.g. "3/1/2026" → "2026-03-01", "28 Feb 2026" → "2026-02-28", "Oct 10, 2026" → "2026-10-10", "2026-1-3" → "2026-01-03".
