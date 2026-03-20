# Competition Task Fixtures

JSON fixtures for every unique competition task type + language combination observed
in production logs on 2026-03-20 (tx-proxy windows only, excluding our own test runs
against kkpqfuj-amager).

## Source

Extracted from Cloud Run logs for `ai-accounting-agent` service, filtering for
`Task received. Prompt:` entries that correlated with tx-proxy API calls during
known competition windows.

## Prompt completeness

Prompts are truncated at ~100 characters in the original container logs. Files marked
"complete" had prompts shorter than this limit and appear to contain the full text.

## Fixture index

| # | File | Task Type | Tier | Lang | Complete? |
|---|------|-----------|------|------|-----------|
| 01 | `01_create_customer_en.json` | create_customer | 1 | EN | No |
| 02 | `02_create_customer_no.json` | create_customer | 1 | NO | No |
| 03 | `03_create_employee_es.json` | create_employee | 1 | ES | No |
| 04 | `04_create_employee_pt.json` | create_employee | 1 | PT | No |
| 05 | `05_create_department_de.json` | create_department | 1 | DE | Yes |
| 06 | `06_create_department_no.json` | create_department | 1 | NO | Yes |
| 07 | `07_create_supplier_fr.json` | create_supplier | 1 | FR | No |
| 08 | `08_create_supplier_no.json` | create_supplier | 1 | NO | Yes |
| 09 | `09_create_invoice_es.json` | create_invoice | 2 | ES | No |
| 10 | `10_create_invoice_no.json` | create_invoice | 2 | NO | No |
| 11 | `11_create_invoice_pt.json` | create_invoice | 2 | PT | No |
| 12 | `12_create_invoice_and_payment_no.json` | create_invoice_and_payment | 2 | NO | No |
| 13 | `13_create_order_fr.json` | create_order | 2 | FR | No |
| 14 | `14_create_project_en.json` | create_project | 2 | EN | No |
| 15 | `15_create_project_es.json` | create_project | 2 | ES | No |
| 16 | `16_create_project_pt.json` | create_project | 2 | PT | No |
| 17 | `17_create_custom_dimension_en.json` | create_custom_dimension | 2 | EN | No |
| 18 | `18_register_supplier_invoice_de.json` | register_supplier_invoice | 2 | DE | No |
| 19 | `19_register_payment_fr.json` | register_payment | 2 | FR | No |
| 20 | `20_register_payment_pt.json` | register_payment | 2 | PT | No |
| 21 | `21_run_salary_no.json` | run_salary | 2 | NO | No |
| 22 | `22_run_salary_pt.json` | run_salary | 2 | PT | No |
| 23 | `23_set_project_fixed_price_es.json` | set_project_fixed_price | 2 | ES | No |

## Task type summary

**Tier 1** (single entity create): 8 fixtures
- create_customer (EN, NO)
- create_employee (ES, PT)
- create_department (DE, NO)
- create_supplier (FR, NO)

**Tier 2** (complex operations): 15 fixtures
- create_invoice (ES, NO, PT)
- create_invoice_and_payment (NO)
- create_order (FR)
- create_project (EN, ES, PT)
- create_custom_dimension (EN)
- register_supplier_invoice (DE)
- register_payment (FR, PT)
- run_salary (NO, PT)
- set_project_fixed_price (ES)

## Languages observed

| Code | Count |
|------|-------|
| NO | 7 |
| ES | 5 |
| PT | 5 |
| EN | 3 |
| FR | 3 |
| DE | 2 |

Note: Tier 3 tasks have not been released yet (opens Saturday).
