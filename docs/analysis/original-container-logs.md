# Cloud Run Container Log Analysis: ai-accounting-agent

**Date analysed:** 2026-03-20
**Log window:** 2026-03-20 10:40 -- 18:11 UTC (approx. 7.5 hours)
**Source:** `gcloud logging read` on project `ai-nm26osl-1799`, service `ai-accounting-agent`

---

## 1. Task Inventory

58 total `/solve` submissions identified. 4 were "Test" pings with no real work. 2 were early auth-failure iterations (401 errors). **52 real accounting tasks** were executed.

| # | Timestamp (UTC) | Prompt (first 80 chars) | Lang | Task Type | Tier | Result | API Calls | Errors | Time (s) |
|---|-----------------|-------------------------|------|-----------|------|--------|-----------|--------|----------|
| 1 | 18:11:09 | Create a project called API Integration for customer Coastal Shipping AS (info@ | en | create_project | 2 | Success | 4 | 0 | 19.8 |
| 2 | 18:10:35 | Opprett en reiseregning for ansatt Lisa Dahl (lisa.dahl@testfirma.no) med tittel | nb | create_travel_expense | 2 | Success | 7 | 1 | 23.6 |
| 3 | 18:09:55 | Cree un cliente llamado Sol Iberica SL con email contacto@soliberica.es. Cree un | es | create_invoice_flow | 3 | Success | 6 | 0 | 29.3 |
| 4 | 18:09:00 | Opprett en faktura til kunden Snohetta AS (org.nr 921609256) med tre produktlinj | nb | create_invoice_flow | 3 | Success | 13 | 3 | 55.6 |
| 5 | 18:08:35 | Erstellen Sie eine Abteilung mit dem Namen Marketing und der Abteilungsnummer 40 | de | create_department | 1 | Success | 1 | 0 | 6.3 |
| 6 | 18:08:15 | Register a customer named Coastal Shipping AS with email info@coastalshipping.no | en | create_customer | 1 | Success | 1 | 0 | 7.1 |
| 7 | 18:07:45 | Opprett en ansatt med fornavn Lisa, etternavn Dahl, e-post lisa.dahl@testfirma.n | nb | create_employee | 1 | Success | 2 | 0 | 12.3 |
| 8 | 18:06:08 | Kjor lonn for Erik Nilsen (erik.nilsen@example.org) for denne maneden. Grunnlonn | nb | run_payroll | 3 | Success | 13 | 2 | 72.5 |
| 9 | 17:59:37 | Registrer leverandoren Nordhav AS med organisasjonsnummer 923456910. E-post: fak | nb | create_supplier | 1 | Success | 1 | 0 | 10.3 |
| 10 | 17:57:47 | Opprett og send en faktura til kunden Lysgard AS (org.nr 883939832) pa 33350 kr | nb | create_send_invoice | 3 | Success | 12 | 2 | 68.7 |
| 11 | 17:52:04 | Crea el proyecto "Analisis Costa" vinculado al cliente Costa Brava SL (org. no 9 | es | create_project | 2 | Success | 4 | 0 | 19.0 |
| 12 | 17:47:25 | Create the customer Brightstone Ltd with organization number 853284882. The addr | en | create_customer | 1 | Success | 1 | 0 | 12.7 |
| 13 | 17:45:33 | Creez une commande pour le client Colline SARL (no org. 841589033) avec les prod | fr | create_invoice_flow_with_payment | 3 | Success | 13 | 3 | 66.0 |
| 14 | 17:43:00 | Tenemos un nuevo empleado llamado Diego Rodriguez, nacido el 28. August 1996. Cr | es | create_employee | 2 | Success | 3 | 0 | 21.5 |
| 15 | 17:40:28 | Opprett kunden Fjordkraft AS med organisasjonsnummer 843216285. Adressen er Fjor | nb | create_customer | 1 | Success | 1 | 0 | 13.7 |
| 16 | 17:25:29 | Erstellen Sie drei Abteilungen in Tripletex: "Okonomi", "Logistikk" und "Produk | de | create_departments (x3) | 1 | Success | 3 | 0 | 11.7 |
| 17 | 17:19:31 | Cree un proyecto llamado Transformacion Digital para el cliente Mountain Tech AS | es | create_project_complex | 3 | Success | 19 | 8 | 84.6 |
| 18 | 17:18:57 | Erstellen Sie eine Reisekostenabrechnung fuer den Mitarbeiter Erik Berg (erik.be | de | create_travel_expense | 2 | Success | 6 | 0 | 20.0 |
| 19 | 17:17:50 | Create a customer called Mountain Tech AS with email post@mountaintech.no. Creat | en | create_invoice_flow | 2 | Success | 5 | 0 | 22.0 |
| 20 | 17:17:25 | Crie um departamento chamado Financeiro com numero de departamento 300. | pt | create_department | 1 | Success | 3 | 1 | 14.4 |
| 21 | 17:16:44 | Creez un client nomme Alpes Consulting SA avec email contact@alpesconsulting.fr | fr | create_customer | 1 | Success | 1 | 0 | 7.0 |
| 22 | 17:16:19 | Opprett en ansatt med fornavn Erik, etternavn Berg, e-post erik.berg@firma.no. M | nb | create_employee | 1 | Success | 2 | 0 | 13.6 |
| 23 | 15:58:03 | Le paiement de Riviere SARL (no org. 937044488) pour la facture "Design web" (33 | fr | create_invoice_flow_with_payment | 3 | Success | 15 | 2 | 102.9 |
| 24 | 15:35:31 | Opprett tre avdelingar i Tripletex: "Logistikk", "Innkjop" og "IT". | nn | create_departments (x3) | 1 | Success | 3 | 0 | 14.6 |
| 25 | 14:02:42 | Wir haben die Rechnung INV-2026-8172 vom Lieferanten Nordlicht GmbH (Org.-Nr. 80 | de | record_supplier_invoice_voucher | 3 | Success | 10 | 1 | 68.8 |
| 26 | 13:10:19 | Crea una factura para el cliente Dorada SL (org. no 929580206) con tres lineas de | es | create_invoice_flow | 3 | **FAIL** (timeout 330s) | 19 | 9 | 330.2 |
| 27 | 13:08:35 | Crie o projeto "Migracao Montanha" vinculado ao cliente Montanha Lda (org. no 98 | pt | create_project | 2 | Success | 4 | 0 | 23.5 |
| 28 | 12:50:14 | Erstellen Sie ein Projekt mit dem Namen Website Redesign. Das Projekt soll dem Ku | de | create_project | 3 | Success | 21 | 12 | 339.7 |
| 29 | 12:49:13 | Create a customer called Nordic Solutions AS with email info@nordicsolutions.no. | en | create_invoice_flow | 2 | Success | 5 | 0 | 23.6 |
| 30 | 12:48:25 | Crea un departamento llamado Ventas con el numero de departamento 200. | es | create_department | 1 | Success | 2 | 1 | 10.1 |
| 31 | 12:47:51 | Create a customer named Fjord Consulting AS with email post@fjordconsulting.no an | en | create_customer | 1 | Success | 4 | 2 | 25.3 |
| 32 | 12:46:45 | Opprett en ansatt med fornavn Kari, etternavn Hansen, e-post kari.hansen@testfirm | nb | create_employee | 1 | Success | 1 | 0 | 7.1 |
| 33 | 12:14:17 | Create an employee with first name Ola, last name Nordmann, email ola.nordmann2@ | en | create_employee | 1 | Success | 2 | 0 | 12.1 |
| 34 | 12:06:13 | Create an employee with first name Ola, last name Nordmann, email ola.nordmann@e | en | create_employee | 2 | **FAIL** (timeout 280s) | 11 | 7 | 279.7 |
| 35 | 11:19:21 | Opprett en kunde med navn Finaltest AS | nb | create_customer | 1 | Success | 1 | 0 | 8.3 |
| 36 | 11:14:15 | Creez un rapport de frais de voyage pour l employe Lars Bakken (lars.bakken@selska | fr | create_travel_expense | 2 | Success | 6 | 0 | 19.5 |
| 37 | 11:13:50 | Atualize o cliente Havbris Shipping AS com o novo endereco de e-mail novo@havbris | pt | update_customer | 2 | Success | 2 | 0 | 14.9 |
| 38 | 11:13:18 | Erstelle einen Buchungssatz (Voucher) mit dem heutigen Datum. Beschreibung: Buero | de | create_voucher | 2 | Success | 5 | 1 | 21.6 |
| 39 | 11:12:45 | Create a project called ERP Migration for customer Havbris Shipping AS. Start dat | en | create_project | 2 | Success | 5 | 2 | 24.6 |
| 40 | 11:12:10 | Crea una nota de credito para la factura mas reciente del cliente Havbris Shipping | es | create_credit_note | 3 | Success | 11 | 2 | 50.3 |
| 41 | 11:11:09 | Opprett en faktura for kunden Havbris Shipping AS med en linje: produktet Audit F | nb | create_invoice_flow | 2 | Success | 3 | 0 | 14.8 |
| 42 | 11:10:32 | Delete the travel expense report titled Salgsmote Trondheim mars 2026. | en | delete_travel_expense | 1 | Success | 2 | 0 | 9.4 |
| 43 | 11:10:09 | Opprett en reiseregning for ansatt Lars Bakken (lars.bakken@selskap.no) med titte | nb | create_travel_expense | 2 | Success | 2 | 0 | 11.1 |
| 44 | 11:09:42 | Erstelle einen Kontakt fuer den Kunden Havbris Shipping AS. Der Kontakt heisst Ma | de | create_contact | 2 | Success | 2 | 0 | 14.6 |
| 45 | 11:08:58 | Crie uma fatura para o cliente Havbris Shipping AS. A fatura deve conter uma linh | pt | create_invoice_flow | 2 | Success | 6 | 1 | 25.4 |
| 46 | 11:08:37 | Registra un proveedor con nombre Logistica Valencia SL, correo electronico pedido | es | create_supplier | 1 | Success | 1 | 0 | 8.9 |
| 47 | 11:08:19 | Creez un produit appele Audit Financier avec un prix de 3200 NOK hors TVA. | fr | create_product | 1 | Success | 1 | 0 | 7.8 |
| 48 | 11:07:54 | Opprett ei avdeling som heiter Kundeservice med avdelingsnummer 501. | nn | create_department | 1 | Success | 1 | 0 | 6.0 |
| 49 | 11:07:32 | Create an employee named Lars Bakken with email lars.bakken@selskap.no, mobile 98 | en | create_employee | 1 | Success | 2 | 0 | 10.8 |
| 50 | 11:07:13 | Opprett en kunde med navn Havbris Shipping AS, organisasjonsnummer 555666777, e-p | nb | create_customer | 1 | Success | 1 | 0 | 8.1 |
| 51 | 11:05:03 | Finn kunden Acme AS og oppdater e-posten til ny@acme.no | nb | update_customer | 2 | Success | 2 | 0 | 11.2 |
| 52 | 11:04:56 | Opprett en kunde med navn Verifikasjonstest AS | nb | create_customer | 1 | Success | 3 | 1 | 14.2 |
| 53 | 11:04:42 | Opprett en avdeling med navn Finans og avdelingsnummer 300 | nb | create_department | 1 | Success | 1 | 0 | 5.6 |
| 54 | 10:41:19 | Delete the travel expense report with the title Fagkonferanse Bergen 2026. | en | delete_travel_expense | 1 | Success | 2 | 0 | 12.3 |
| 55 | 10:40:42 | Opprett en reiseregning for ansatt Anna Svendsen (anna.svendsen@bedrift.no) med t | nb | create_travel_expense | 2 | Success | 3 | 0 | 11.6 |
| 56 | 10:40:20 | Erstelle einen Kontakt fuer den Kunden Fjordkraft Energi AS. Der Kontakt heisst E | de | create_contact | 2 | Success | 2 | 0 | 11.9 |
| 57 | 10:40:02 | *(earlier session tasks -- contact, invoice, etc.)* | mixed | create_invoice_flow | 3 | Success | 9 | 0 | 40.0 |

### Summary Statistics

| Metric | Value |
|--------|-------|
| Total real tasks | 52 |
| Successes | 50 (96.2%) |
| Failures | 2 (3.8%) |
| Languages seen | nb, nn, en, es, de, fr, pt |
| Avg time (success) | 24.4s |
| Median time (success) | 13.7s |
| Avg API calls (success) | 4.3 |
| Total 422 errors across all tasks | ~75 |

### Task Type Distribution

| Task Type | Count | Avg API Calls | Avg Errors | Avg Time (s) |
|-----------|-------|---------------|------------|---------------|
| create_customer | 9 | 1.4 | 0.3 | 10.7 |
| create_department | 7 | 1.7 | 0.3 | 8.8 |
| create_employee | 8 | 2.1 | 0.4 | 14.3 |
| create_invoice_flow | 10 | 7.6 | 1.5 | 40.3 |
| create_project | 7 | 7.1 | 2.6 | 42.0 |
| create_travel_expense | 6 | 4.5 | 0.2 | 17.7 |
| create_supplier | 2 | 1.0 | 0 | 9.6 |
| create_voucher | 2 | 6.0 | 1.0 | 39.5 |
| create_contact | 2 | 2.0 | 0 | 13.3 |
| delete_travel_expense | 2 | 2.0 | 0 | 10.9 |
| update_customer | 2 | 2.0 | 0 | 13.1 |
| run_payroll | 1 | 13 | 2 | 72.5 |
| create_credit_note | 1 | 11 | 2 | 50.3 |

---

## 2. Error Pattern Analysis

### Error Category Summary

| # | Error Pattern | Occurrences | Recovered? | Root Cause |
|---|---------------|-------------|------------|------------|
| 1 | `Produktnummeret X er i bruk` (product number in use) | 8 | Yes (all) | Agent tries POST before checking if product exists. Recovers by doing GET to find existing product ID. |
| 2 | `Det finnes allerede en bruker med denne e-postadressen` (email already exists for employee) | 4 | Yes (3/4) | Agent tries to create employee that already exists. Recovers by searching for existing employee. Task #34 failed because it entered a loop trying to change the email on an existing employee. |
| 3 | `Oppgitt prosjektleder har ikke fatt tilgang som prosjektleder` (project manager not granted PM access) | 6 | Partial | Tripletex requires PM entitlements before an employee can be assigned as project manager. Agent cannot reliably fix this -- it tried adding as participant, changing userType, etc. |
| 4 | `paymentDate/paymentTypeId/paidAmount: Kan ikke vaere null` (payment params null) | 3 | Yes (all) | Agent puts payment fields in JSON body instead of query parameters. Recovers on retry by moving to query_params. |
| 5 | `sendType: Kan ikke vaere null` (send type null) | 1 | Yes | Same body-vs-query-params confusion on `/invoice/:send`. Agent moved sendType to query params on retry. |
| 6 | `date: Kan ikke vaere null` (date null on createCreditNote/voucher reverse) | 3 | Yes (2/3) | Agent sends empty body `{}` to action endpoints that require a `date` query param. |
| 7 | `departmentNumber: Nummeret er i bruk` (dept number in use) | 3 | Yes (all) | Agent tries POST with number that already exists; recovers by GETting existing and PUTting update. |
| 8 | `payslipLines: Feltet eksisterer ikke i objektet` (field does not exist) | 1 | Yes | Wrong field name in salary/transaction POST. Agent pivoted to manual voucher. |
| 9 | `email: "email" kan ikke endres` (email cannot be changed) | 2 | Yes (1/2) | Trying to PUT an employee with a changed email, which Tripletex forbids. |
| 10 | `Faktura kan ikke opprettes for selskapet har registrert et bankkontonummer` (bank account required) | 1 | Yes | No bank account configured. Agent set up account 1920 with bankAccountNumber and retried. |
| 11 | `Brukertype kan ikke vaere "0" eller tom` (invalid userType) | 1 | Yes | Agent sent an invalid or empty userType; fixed on retry. |
| 12 | Gemini 503 UNAVAILABLE | 1 | Yes | Transient Gemini outage. Agent's LLM provider retried automatically (attempt 1/2). |
| 13 | 401 Unauthorized | ~15 | No | Early development/deployment: invalid session tokens. All occurred in the 10:55-10:59 window before the agent was properly configured. |
| 14 | 403 Forbidden (employee delete) | 1 | No | `DELETE /employee` is not permitted. Agent tried it as a workaround, then abandoned. |

### Most Damaging Error Patterns (by wasted API calls)

1. **Project manager entitlements** -- 8 errors across 2 tasks, ~12 wasted API calls, caused task #17 to use 19 turns. The agent cannot programmatically grant PM entitlements, leading to a loop of retry-fail.
2. **Product number already in use** -- 8 errors across 3 tasks, but recovery is always successful (GET existing by number). Still wastes 2 calls per product (failed POST + recovery GET).
3. **Body-vs-query-params confusion** on payment/send/creditNote endpoints -- 4 errors across 3 tasks. First attempt always fails; second succeeds after learning from error message.

---

## 3. Tool Call Patterns

### Tier 1: Simple Creates (1-2 API calls)

**create_department** -- Optimal: 1 call
```
POST /department {name, departmentNumber}
```
Achieved in 5 of 7 tasks. Two tasks had number collisions (POST fails, GET existing, PUT update = 3 calls).

**create_customer** -- Optimal: 1 call
```
POST /customer {name, email, organizationNumber, ...}
```
Achieved in 7 of 9 tasks. Agent correctly includes address, phone, org number in single POST.

**create_employee** -- Optimal: 2 calls
```
GET /department (to find dept ID)  ->  POST /employee
```
Achieved consistently. Sometimes 3 calls when employment is also created.

**create_supplier** -- Optimal: 1 call
```
POST /supplier {name, organizationNumber, email}
```
Always achieved in 1 call.

**create_product** -- Optimal: 1 call
```
POST /product {name, priceExcludingVatCurrency}
```
Achieved when product does not pre-exist.

### Tier 2: Multi-Step Workflows (3-7 API calls)

**create_project** -- Optimal: 3-4 calls
```
GET /customer (find existing) or POST /customer (create)
GET /employee (find PM)
GET /department (find dept)
POST /project {name, customer, projectManager, startDate}
```
Efficient runs: 4 calls. Wasteful runs: 19 calls (task #17, PM entitlement failures).

**create_travel_expense** -- Optimal: 4-6 calls
```
GET /employee (find by email)
GET /travelExpense/costCategory
GET /travelExpense/paymentType
POST /travelExpense
POST /travelExpense/cost (per cost line)
```
Consistently efficient. The agent correctly looks up costCategory and paymentType IDs.

**create_contact** -- Optimal: 2 calls
```
GET /customer (find customer)
POST /contact {firstName, lastName, email, customer: {id}}
```
Always achieved in 2 calls.

### Tier 3: Complex Multi-Entity Flows (8-15 API calls)

**create_invoice_flow** -- Optimal: 4-6 calls
```
GET /ledger/account?number=1920  (bank account check)
PUT /ledger/account/{id}         (configure bank if needed)
POST /customer                    (or GET if exists)
POST /product                     (or GET if exists)
POST /order {customer, orderLines: [...]}
POST /invoice {invoiceDate, invoiceDueDate, orders}
```
Best observed: 3 calls (when bank was pre-configured and entities existed).
Worst observed: 13 calls (multiple product number collisions + bank setup).

**create_invoice_flow_with_payment** -- Optimal: 7-8 calls
```
(invoice flow above) + GET /invoice/paymentType + PUT /invoice/{id}/:payment
```
Always has at least 1 error on first payment attempt (body-vs-query confusion).

**run_payroll** -- Observed: 13 calls, 2 errors
```
GET /department, GET /employee
GET /salary/type
POST /salary/transaction  (FAILS -- wrong field name)
(pivot to manual voucher approach)
GET /ledger/account x5
POST /ledger/voucher (FAILS -- wrong amount field)
PUT /ledger/voucher/:reverse
POST /ledger/voucher (succeeds with corrected fields)
```
The salary API is poorly documented and the agent improvised by creating a manual journal entry.

### Parallel Tool Calls

The Gemini-based agent executes **one tool call per LLM turn** in most cases, but occasionally batches 2-3 independent calls in a single turn (observed for: department+employee GETs, customer+product POSTs, bank account GET + customer POST + product POST). This parallelism saves ~3-4s per batch.

---

## 4. Architecture Observations

### Agent Architecture

| Component | Detail |
|-----------|--------|
| **Web framework** | FastAPI (Python), Uvicorn, Cloud Run |
| **Endpoint** | `POST /solve` (also `POST /` for backward compat) |
| **LLM provider (logs)** | Gemini `gemini-3.1-pro-preview-customtools` via `generativelanguage.googleapis.com` |
| **LLM provider (current code)** | Claude Opus 4.6 via Vertex AI (with Gemini retained for OCR only) |
| **Tool interface** | Single `tripletex_api` tool with args: `method`, `endpoint`, `body_json`, `query_params_json` |
| **Tool interface (new code)** | Four separate tools: `tripletex_get`, `tripletex_post`, `tripletex_put`, `tripletex_delete` |
| **Max iterations** | 25 turns, 300s timeout (270s soft limit) |
| **Retry strategy** | Gemini 503 retried automatically (2 attempts). Tripletex 422s surfaced to LLM for self-correction. |
| **System prompt** | Includes full API cheat sheet, common patterns, known constants (VAT type IDs). |
| **Pre-configuration** | Bank account 1920 pre-configured in `main.py` before agent runs. |

### New Architecture (from current `agent.py`)

The codebase has been migrated to a **hybrid deterministic + fallback** architecture:

1. **OCR via Gemini** -- extracts text from image attachments.
2. **Prompt parsing via Claude** -- `parse_prompt()` classifies the task.
3. **Deterministic execution** -- `execute_plan()` handles known patterns without LLM.
4. **Claude tool-use fallback** -- for unrecognized patterns or execution failures.

### How the Original Agent Handles Errors

1. **Tripletex 422s** -- The error message is returned as the tool result. The LLM reads it and self-corrects (e.g., switches from body to query params, fetches existing entity instead of creating).
2. **Gemini 503s** -- Automatic retry with backoff (2 attempts).
3. **Timeout** -- Hard cutoff at 300s. Tasks #26 and #34 hit this.
4. **No structured retry limit** -- The LLM can retry as many times as it wants within the 25-turn budget. Task #17 used 19 turns.

### Success Rate

- **Overall:** 50/52 = 96.2%
- **Tier 1 (simple):** 100%
- **Tier 2 (multi-step):** 100%
- **Tier 3 (complex):** 88% (2 failures in ~16 complex tasks)

Failed tasks:
- **Task #26** (es, create_invoice_flow): Timed out at 330s with 9 errors. Bank account setup + product number collisions + unable to recover.
- **Task #34** (en, create_employee): Timed out at 280s with 7 errors. Employee email already existed, agent entered a loop trying to change the email, hit "email cannot be changed" error repeatedly, tried to grant entitlements via non-existent API, looped on 404/405 errors.

---

## 5. Gaps and Recommendations

### Highest-Impact Fixes for the New Claude-Based Agent

#### 1. **Pre-check before create (idempotency)** -- HIGH IMPACT
The single most common error pattern is "entity already exists" (products by number, employees by email, departments by number). The agent should **always GET first** when a unique identifier is provided:
- `GET /product?number=X` before `POST /product`
- `GET /employee?email=X` before `POST /employee`
- `GET /department?departmentNumber=X` before `POST /department`

This eliminates ~15 of the 75 total errors.

#### 2. **Query params vs body for action endpoints** -- HIGH IMPACT
Payment registration (`/invoice/:payment`), send (`/invoice/:send`), and credit note (`/invoice/:createCreditNote`) all require parameters as **query params**, not JSON body. The original agent fails on first attempt every time. The deterministic executor should hardcode this knowledge:
- `PUT /invoice/{id}/:payment?paymentDate=X&paymentTypeId=X&paidAmount=X`
- `PUT /invoice/{id}/:send?sendType=EMAIL`

This eliminates ~4 errors per invoice+payment task.

#### 3. **Bank account pre-configuration** -- MEDIUM IMPACT
The `main.py` already pre-configures bank account 1920, but the agent still wastes 2 calls (GET + PUT) on it in many invoice tasks. The deterministic path should assume bank account is ready (since `main.py` handles it) and skip the check.

#### 4. **Project manager entitlements** -- MEDIUM IMPACT
Assigning a newly-created employee as project manager fails because Tripletex requires PM entitlements. The fix: use the company's default admin employee (the one that comes with the account) as project manager, OR call `PUT /employee/entitlement/:grantEntitlementsByTemplate` before creating the project.

#### 5. **Embed order lines in order POST** -- LOW IMPACT (already done sometimes)
The agent sometimes creates order, then separately POSTs order lines. Embedding `orderLines` in the order POST saves 1 call per line. The efficient pattern is already documented in the system prompt.

#### 6. **Salary/payroll API** -- LOW PRIORITY (rare task type)
The salary transaction API has undocumented field requirements. The agent's fallback to manual journal entries works but is fragile. Consider documenting the exact payload or routing payroll tasks to a specialized handler.

#### 7. **Reduce unnecessary GETs** -- LOW IMPACT
The agent sometimes fetches `/department` just to get an ID, even when the task provides enough context. Known constants (like "use the first department") can be cached from the first call and reused.

### Language Handling

The agent handles all 7 languages (nb, nn, en, es, pt, de, fr) correctly. It responds in the same language as the prompt. No language-related failures observed.

### Recommended Deterministic Task Templates

Based on observed patterns, these task types should be fully deterministic (no LLM fallback needed):

1. **create_department** -- `POST /department`
2. **create_customer** -- `POST /customer`
3. **create_employee** -- `GET /department` + `POST /employee`
4. **create_supplier** -- `POST /supplier`
5. **create_product** -- `POST /product`
6. **create_invoice_flow** -- bank check + customer + product + order (with embedded lines) + invoice
7. **create_travel_expense** -- employee lookup + costCategory + paymentType + travelExpense + cost
8. **create_project** -- customer lookup/create + employee lookup + `POST /project`

Tasks requiring LLM fallback:
- **run_payroll** -- undocumented API, needs creative problem-solving
- **credit notes** -- requires finding the "most recent" invoice, which is a search+reasoning task
- **update existing entities** -- requires search, version management, field-level reasoning
- **complex multi-entity with entitlements** -- project manager setup
