# Competition Ground Truth — All Requests Observed

> Generated: 2026-03-20 from Cloud Logging (project: ai-nm26osl-1799)
> Data window: 2026-03-20 (all requests within the 7-day log retention)
> Sources: `ai-accounting-agent` (original) and `ai-accounting-agent-det` (deterministic)
>
> **Important:** Requests are classified by the API base URL in the subsequent API calls:
> - **Competition** = `tx-proxy-jwanbnu3pq-lz.a.run.app` (the proxy used by the evaluation platform)
> - **Test** = `kkpqfuj-amager.tripletex.dev` (our own Tripletex sandbox for smoke testing)
> - **Unknown** = No API calls made (test pings with 0 API calls)

---

## 1. Task Catalogue

### Task Types Observed in Competition (tx-proxy)

| # | Task Type | Tier | Languages Seen | Count | Avg Time | Avg API | Avg Err | Success |
|---|-----------|------|----------------|-------|----------|---------|---------|---------|
| 1 | create_invoice | 2 | NO, PT, ES | 4 | 127.7s | 14.2 | 4.2 | 75% (3/4) |
| 2 | create_project | 2 | PT, ES, EN | 3 | 26.2s | 4.0 | 0.0 | 100% (3/3) |
| 3 | create_customer | 1 | NO, EN | 3 | 16.4s | 1.3 | 0.0 | 100% (3/3) |
| 4 | create_departments (batch) | 1 | NO, DE | 2 | 13.1s | 3.0 | 0.0 | 100% (2/2) |
| 5 | register_payment | 3 | FR, PT | 2 | 88.9s | 12.5 | 1.0 | 100% (2/2) |
| 6 | create_employee | 1 | ES, PT | 2 | 25.2s | 3.0 | 0.0 | 100% (2/2) |
| 7 | create_supplier | 1 | NO, FR | 2 | 15.8s | 1.5 | 0.0 | 100% (2/2) |
| 8 | run_salary | 3 | NO, PT | 2 | 151.4s | 18.5 | 6.0 | 100% (2/2) |
| 9 | create_project_fixed_price | 3 | ES | 2 | 72.3s | 10.0 | 1.0 | 100% (2/2) |
| 10 | register_supplier_invoice | 3 | DE | 1 | 68.8s | 10.0 | 1.0 | 100% (1/1) |
| 11 | create_order | 2 | FR | 1 | 66.0s | 13.0 | 3.0 | 100% (1/1) |
| 12 | create_custom_dimension | 3 | EN | 1 | 254.1s | 5.0 | 5.0 | 100% (1/1) |

**Task types seen ONLY in our test requests (not in competition):**
create_contact, create_product, create_travel_expense, delete_travel_expense, create_invoice_flow, create_credit_note, create_voucher, update_customer, create_department (single)

> Note: Single `create_department` was never sent by the competition platform. The competition sent `create_departments` (batch of 3) instead. Many Tier 1 types we tested were not part of the actual competition submissions.

### Legend
- **Orig**: original container (`ai-accounting-agent`, OpenAI-based agent)
- **Det**: deterministic container (`ai-accounting-agent-det`, rule-based with LLM fallback)

---

## 2. Full Request Log

### Competition Requests (tx-proxy) — 25 tasks across ~15 submissions

Grouped by submission batch. Tasks arriving within ~5 min of each other are considered one submission.

#### Batch 1 (13:08-13:10) — 2 tasks

| # | Timestamp (UTC) | Prompt (truncated) | Lang | Task Type | Time (s) | API | Err | OK |
|---|-----------------|---------------------|------|-----------|----------|-----|-----|----|
| 1 | 13:08:35 | Crie o projeto "Migracao Montanha" vinculado ao cliente Montanha Lda (org. n. 986713344). O gerente ... | PT | create_project | 23.5s | 4 | 0 | Yes |
| 2 | 13:10:19 | Crea una factura para el cliente Dorada SL (org. n. 929580206) con tres lineas de producto: Mantenim... | ES | create_invoice | 330.2s | 19 | 9 | **No** |

#### Batch 2 (14:02) — 1 task

| # | Timestamp (UTC) | Prompt (truncated) | Lang | Task Type | Time (s) | API | Err | OK |
|---|-----------------|---------------------|------|-----------|----------|-----|-----|----|
| 3 | 14:02:42 | Wir haben die Rechnung INV-2026-8172 vom Lieferanten Nordlicht GmbH (Org.-Nr. 803273723) uber 19100... | DE | register_supplier_invoice | 68.8s | 10 | 1 | Yes |

#### Batch 3 (15:35) — 1 task

| # | Timestamp (UTC) | Prompt (truncated) | Lang | Task Type | Time (s) | API | Err | OK |
|---|-----------------|---------------------|------|-----------|----------|-----|-----|----|
| 4 | 15:35:31 | Opprett tre avdelingar i Tripletex: "Logistikk", "Innkjop" og "IT". | NO | create_departments | 14.6s | 3 | 0 | Yes |

#### Batch 4 (15:58) — 1 task

| # | Timestamp (UTC) | Prompt (truncated) | Lang | Task Type | Time (s) | API | Err | OK |
|---|-----------------|---------------------|------|-----------|----------|-----|-----|----|
| 5 | 15:58:03 | Le paiement de Riviere SARL (n. org. 937044488) pour la facture "Design web" (33050 NOK HT) a ete r... | FR | register_payment | 102.9s | 15 | 2 | Yes |

#### Batch 5 (17:25) — 1 task

| # | Timestamp (UTC) | Prompt (truncated) | Lang | Task Type | Time (s) | API | Err | OK |
|---|-----------------|---------------------|------|-----------|----------|-----|-----|----|
| 6 | 17:25:29 | Erstellen Sie drei Abteilungen in Tripletex: "Okonomi", "Logistikk" und "Produksjon". | DE | create_departments | 11.7s | 3 | 0 | Yes |

#### Batch 6 (17:40-17:52) — 5 tasks

| # | Timestamp (UTC) | Prompt (truncated) | Lang | Task Type | Time (s) | API | Err | OK |
|---|-----------------|---------------------|------|-----------|----------|-----|-----|----|
| 7 | 17:40:28 | Opprett kunden Fjordkraft AS med organisasjonsnummer 843216285. Adressen er Fjordveien 129, 2317 Ham... | NO | create_customer | 13.7s | 1 | 0 | Yes |
| 8 | 17:43:00 | Tenemos un nuevo empleado llamado Diego Rodriguez, nacido el 28. August 1996. Creelo como empleado c... | ES | create_employee | 21.5s | 3 | 0 | Yes |
| 9 | 17:45:33 | Creez une commande pour le client Colline SARL (n. org. 841589033) avec les produits Stockage cloud... | FR | create_order | 66.0s | 13 | 3 | Yes |
| 10 | 17:47:25 | Create the customer Brightstone Ltd with organization number 853284882. The address is Parkveien 61,... | EN | create_customer | 12.7s | 1 | 0 | Yes |
| 11 | 17:52:04 | Crea el proyecto "Analisis Costa" vinculado al cliente Costa Brava SL (org. n. 921937946). El direct... | ES | create_project | 19.0s | 4 | 0 | Yes |

#### Batch 7 (17:57-17:59) — 2 tasks

| # | Timestamp (UTC) | Prompt (truncated) | Lang | Task Type | Time (s) | API | Err | OK |
|---|-----------------|---------------------|------|-----------|----------|-----|-----|----|
| 12 | 17:57:47 | Opprett og send en faktura til kunden Lysgard AS (org.nr 883939832) pa 33350 kr eksklusiv MVA... | NO | create_invoice | 68.7s | 12 | 2 | Yes |
| 13 | 17:59:37 | Registrer leverandoren Nordhav AS med organisasjonsnummer 923456910. E-post: faktura@nordhav.no. | NO | create_supplier | 10.3s | 1 | 0 | Yes |

#### Batch 8 (18:06-18:09) — 2 tasks

| # | Timestamp (UTC) | Prompt (truncated) | Lang | Task Type | Time (s) | API | Err | OK |
|---|-----------------|---------------------|------|-----------|----------|-----|-----|----|
| 14 | 18:06:08 | Kjor lonn for Erik Nilsen (erik.nilsen@example.org) for denne maneden. Grunnlonn er 53350 kr. Legg t... | NO | run_salary | 72.5s | 13 | 2 | Yes |
| 15 | 18:09:00 | Opprett en faktura til kunden Snohetta AS (org.nr 921609256) med tre produktlinjer: Konsulenttimer (... | NO | create_invoice | 55.6s | 13 | 3 | Yes |

#### Batch 9 (18:52) — 1 task

| # | Timestamp (UTC) | Prompt (truncated) | Lang | Task Type | Time (s) | API | Err | OK |
|---|-----------------|---------------------|------|-----------|----------|-----|-----|----|
| 16 | 18:52:17 | Create a custom accounting dimension "Produktlinje" with the values "Standard" and "Basis". Then pos... | EN | create_custom_dimension | 254.1s | 5 | 5 | Yes |

#### Batch 10 (19:01) — 1 task

| # | Timestamp (UTC) | Prompt (truncated) | Lang | Task Type | Time (s) | API | Err | OK |
|---|-----------------|---------------------|------|-----------|----------|-----|-----|----|
| 17 | 19:01:22 | Crie uma fatura para o cliente Oceano Lda (org. n. 825975497) com tres linhas de produto: Design web... | PT | create_invoice | 56.3s | 13 | 3 | Yes |

#### Batch 11 (19:13-19:17) — 3 tasks

| # | Timestamp (UTC) | Prompt (truncated) | Lang | Task Type | Time (s) | API | Err | OK |
|---|-----------------|---------------------|------|-----------|----------|-----|-----|----|
| 18 | 19:13:25 | Enregistrez le fournisseur Lumiere SARL avec le numero d'organisation 879852439. E-mail : faktura@lu... | FR | create_supplier | 21.3s | 2 | 0 | Yes |
| 19 | 19:14:23 | Opprett kunden Skogheim AS med organisasjonsnummer 893718729. Adressa er Storgata 111, 7010 Trondhei... | NO | create_customer | 22.9s | 2 | 0 | Yes |
| 20 | 19:17:15 | Establezca un precio fijo de 152400 NOK en el proyecto "Mejora de infraestructura" para Estrella SL... | ES | create_project_fixed_price | 84.5s | 10 | 1 | Yes |

#### Batch 12 (19:22-19:24) — 2 tasks

| # | Timestamp (UTC) | Prompt (truncated) | Lang | Task Type | Time (s) | API | Err | OK |
|---|-----------------|---------------------|------|-----------|----------|-----|-----|----|
| 21 | 19:22:54 | Temos um novo funcionario chamado Rita Almeida, nascido em 29. December 1995. Crie-o como funcionari... | PT | create_employee | 29.0s | 3 | 0 | Yes |
| 22 | 19:24:00 | Processe o salario de Sofia Sousa (sofia.sousa@example.org) para este mes. O salario base e de 30200... | PT | run_salary | 230.4s | 24 | 10 | Yes |

#### Batch 13 (19:40) — 1 task

| # | Timestamp (UTC) | Prompt (truncated) | Lang | Task Type | Time (s) | API | Err | OK |
|---|-----------------|---------------------|------|-----------|----------|-----|-----|----|
| 23 | 19:40:35 | Create the project "Upgrade Windmill" linked to the customer Windmill Ltd (org no. 978017681). The p... | EN | create_project | 36.1s | 4 | 0 | Yes |

#### Batch 14 (19:47) — 1 task

| # | Timestamp (UTC) | Prompt (truncated) | Lang | Task Type | Time (s) | API | Err | OK |
|---|-----------------|---------------------|------|-----------|----------|-----|-----|----|
| 24 | 19:47:50 | Establezca un precio fijo de 152400 NOK en el proyecto "Mejora de infraestructura" para Estrella SL... | ES | create_project_fixed_price | 60.1s | 10 | 1 | Yes |

#### Batch 15 (19:55) — 1 task

| # | Timestamp (UTC) | Prompt (truncated) | Lang | Task Type | Time (s) | API | Err | OK |
|---|-----------------|---------------------|------|-----------|----------|-----|-----|----|
| 25 | 19:55:09 | O pagamento de Cascata Lda (org. n. 844279892) referente a fatura "Horas de consultoria" (41350 NOK... | PT | register_payment | 74.9s | 10 | 0 | Yes |

---

### Our Test Requests (kkpqfuj-amager) — 64 tasks

These are our own smoke tests and manual testing against our Tripletex sandbox.

| # | Timestamp (UTC) | Prompt (truncated) | Lang | Task Type | Time (s) | API | Err | OK |
|---|-----------------|---------------------|------|-----------|----------|-----|-----|----|
| 1 | 09:26:47 | *(54 chars, prompt not logged)* | ? | ? | ? | ? | ? | ? |
| 2 | 09:36:06 | *(55 chars, prompt not logged)* | ? | ? | ? | ? | ? | ? |
| 3 | 10:12:25 | Opprett en kunde med navn Testfirma AS og e-post post@testfirma.no | NO | create_customer | 10.2s | 1 | 0 | Yes |
| 4 | 10:22:59 | Opprett en kunde med navn Bergen Elektro AS, organisasjonsnummer 987654321... | NO | create_customer | 7.8s | 1 | 0 | Yes |
| 5 | 10:23:17 | Create an employee named Per Olsen with email per.olsen@firma.no... | EN | create_employee | 16.7s | 3 | 0 | Yes |
| 6 | 10:23:45 | Opprett ei avdeling med namn Marknadsfoering og avdelingsnummer 300. | NO | create_department | 6.6s | 1 | 0 | Yes |
| 7 | 10:24:10 | Creez un produit appele Service de conseil avec un prix de 950 NOK hors TVA. | FR | create_product | 7.9s | 1 | 0 | Yes |
| 8 | 10:24:27 | Registra un proveedor con nombre Suministros Madrid SL... | ES | create_supplier | 7.6s | 1 | 0 | Yes |
| 9 | 10:24:45 | Crie uma fatura para o cliente Nordvik Bygg AS... | PT | create_invoice | 49.5s | 11 | 3 | Yes |
| 10 | 10:25:51 | Erstelle einen Kontakt fuer den Kunden Bergen Elektro AS... | DE | create_contact | 11.8s | 2 | 0 | Yes |
| 11 | 10:26:12 | Opprett en reiseregning for ansatt Per Olsen... | NO | create_travel_expense | 11.7s | 3 | 0 | Yes |
| 12 | 10:26:34 | Delete the travel expense report titled Kundemote Stavanger. | EN | delete_travel_expense | 10.8s | 2 | 0 | Yes |
| 13 | 10:37:40 | Opprett en kunde med navn Fjordkraft Energi AS... | NO | create_customer | 8.6s | 1 | 0 | Yes |
| 14 | 10:38:00 | Create an employee named Anna Svendsen... | EN | create_employee | 11.0s | 2 | 0 | Yes |
| 15 | 10:38:22 | Opprett ei avdeling som heiter Logistikk med avdelingsnummer 401. | NO | create_department | 6.5s | 1 | 0 | Yes |
| 16 | 10:38:47 | Creez un produit appele Formation en ligne avec un prix de 2500 NOK hors TVA. | FR | create_product | 7.4s | 1 | 0 | Yes |
| 17 | 10:39:05 | Registra un proveedor con nombre Tecnologia Barcelona SL... | ES | create_supplier | 7.0s | 1 | 0 | Yes |
| 18 | 10:39:21 | Crie uma fatura para o cliente Fjordkraft Energi AS... | PT | create_invoice | 40.0s | 9 | 0 | Yes |
| 19 | 10:40:20 | Erstelle einen Kontakt fuer den Kunden Fjordkraft Energi AS... | DE | create_contact | 11.9s | 2 | 0 | Yes |
| 20 | 10:40:42 | Opprett en reiseregning for ansatt Anna Svendsen... | NO | create_travel_expense | 11.6s | 3 | 0 | Yes |
| 21 | 10:41:19 | Delete the travel expense report with the title Fagkonferanse Bergen 2026. | EN | delete_travel_expense | 12.3s | 2 | 0 | Yes |
| 22 | 10:55:19 | *(58 chars, prompt not logged)* | ? | ? | ? | ? | ? | ? |
| 23 | 10:59:11 | *(58 chars, prompt not logged)* | ? | ? | ? | ? | ? | ? |
| 24 | 11:04:42 | Opprett en avdeling med navn Finans og avdelingsnummer 300 | NO | create_department | 14.2s | 3 | 1 | Yes |
| 25 | 11:04:56 | Opprett en kunde med navn Verifikasjonstest AS | NO | create_customer | 5.6s | 1 | 0 | Yes |
| 26 | 11:05:03 | Finn kunden Acme AS og oppdater e-posten til ny@acme.no | NO | update_customer | 11.2s | 2 | 0 | Yes |
| 27 | 11:07:13 | Opprett en kunde med navn Havbris Shipping AS... | NO | create_customer | 8.1s | 1 | 0 | Yes |
| 28 | 11:07:32 | Create an employee named Lars Bakken... | EN | create_employee | 10.8s | 2 | 0 | Yes |
| 29 | 11:07:54 | Opprett ei avdeling som heiter Kundeservice med avdelingsnummer 501. | NO | create_department | 6.0s | 1 | 0 | Yes |
| 30 | 11:08:19 | Creez un produit appele Audit Financier avec un prix de 3200 NOK hors TVA. | FR | create_product | 7.8s | 1 | 0 | Yes |
| 31 | 11:08:37 | Registra un proveedor con nombre Logistica Valencia SL... | ES | create_supplier | 8.9s | 1 | 0 | Yes |
| 32 | 11:08:58 | Crie uma fatura para o cliente Havbris Shipping AS... | PT | create_invoice | 25.4s | 6 | 1 | Yes |
| 33 | 11:09:42 | Erstelle einen Kontakt fuer den Kunden Havbris Shipping AS... | DE | create_contact | 14.6s | 2 | 0 | Yes |
| 34 | 11:10:09 | Opprett en reiseregning for ansatt Lars Bakken... | NO | create_travel_expense | 11.1s | 2 | 0 | Yes |
| 35 | 11:10:32 | Delete the travel expense report titled Salgsmote Trondheim mars 2026. | EN | delete_travel_expense | 9.4s | 2 | 0 | Yes |
| 36 | 11:11:09 | Opprett en faktura for kunden Havbris Shipping AS med en linje... | NO | create_invoice | 50.3s | 11 | 2 | Yes |
| 37 | 11:12:10 | Crea una nota de credito para la factura mas reciente del cliente Havbris Shipping AS. | ES | create_credit_note | 24.6s | 5 | 2 | Yes |
| 38 | 11:12:45 | Create a project called ERP Migration for customer Havbris Shipping AS... | EN | create_project | 14.8s | 3 | 0 | Yes |
| 39 | 11:13:18 | Erstelle einen Buchungssatz (Voucher) mit dem heutigen Datum... | DE | create_voucher | 21.6s | 5 | 1 | Yes |
| 40 | 11:13:50 | Atualize o cliente Havbris Shipping AS com o novo endereco de e-mail... | PT | update_customer | 14.9s | 2 | 0 | Yes |
| 41 | 11:14:15 | Creez un rapport de frais de voyage pour l employe Lars Bakken... | FR | create_travel_expense | 19.5s | 6 | 0 | Yes |
| 42 | 11:19:21 | Opprett en kunde med navn Finaltest AS | NO | create_customer | 8.3s | 1 | 0 | Yes |
| 43 | 12:06:13 | Create an employee with first name Ola, last name Nordmann, email ola.nordmann@example.com... | EN | create_employee | 279.7s | 11 | 7 | **No** |
| 44 | 12:14:17 | Create an employee with first name Ola, last name Nordmann, email ola.nordmann2@example.com... | EN | create_employee | 12.1s | 2 | 0 | Yes |
| 45 | 12:46:45 | Opprett en ansatt med fornavn Kari, etternavn Hansen... | NO | create_employee | 25.3s | 4 | 2 | Yes |
| 46 | 12:47:51 | Create a customer named Fjord Consulting AS... | EN | create_customer | 7.1s | 1 | 0 | Yes |
| 47 | 12:48:25 | Crea un departamento llamado Ventas con el numero de departamento 200. | ES | create_department | 10.1s | 2 | 1 | Yes |
| 48 | 12:49:13 | Create a customer called Nordic Solutions AS... Then create a produ... | EN | create_invoice_flow | 23.6s | 5 | 0 | Yes |
| 49 | 12:50:14 | Erstellen Sie ein Projekt mit dem Namen Website Redesign... | DE | create_project | 339.7s | 21 | 12 | Yes |
| 50 | 17:16:19 | Opprett en ansatt med fornavn Erik, etternavn Berg... | NO | create_employee | 13.6s | 2 | 0 | Yes |
| 51 | 17:16:44 | Creez un client nomme Alpes Consulting SA... | FR | create_customer | 7.0s | 1 | 0 | Yes |
| 52 | 17:17:25 | Crie um departamento chamado Financeiro com numero de departamento 300. | PT | create_department | 14.4s | 3 | 1 | Yes |
| 53 | 17:17:50 | Create a customer called Mountain Tech AS... Create a product... | EN | create_invoice_flow | 22.0s | 5 | 0 | Yes |
| 54 | 17:18:57 | Erstellen Sie eine Reisekostenabrechnung fuer den Mitarbeiter Erik Berg... | DE | create_travel_expense | 20.0s | 6 | 0 | Yes |
| 55 | 17:19:31 | Cree un proyecto llamado Transformacion Digital para el cliente Mountain Tech AS... | ES | create_project | 84.6s | 19 | 8 | Yes |
| 56 | 18:07:45 | Opprett en ansatt med fornavn Lisa, etternavn Dahl... | NO | create_employee | 12.3s | 2 | 0 | Yes |
| 57 | 18:08:15 | Register a customer named Coastal Shipping AS... | EN | create_customer | 7.1s | 1 | 0 | Yes |
| 58 | 18:08:35 | Erstellen Sie eine Abteilung mit dem Namen Marketing und der Abteilungsnummer 400. | DE | create_department | 6.3s | 1 | 0 | Yes |
| 59 | 18:09:55 | Cree un cliente llamado Sol Iberica SL... Cree un producto... | ES | create_invoice_flow | 29.3s | 6 | 0 | Yes |
| 60 | 18:10:35 | Opprett en reiseregning for ansatt Lisa Dahl... | NO | create_travel_expense | 23.6s | 7 | 1 | Yes |
| 61 | 18:11:09 | Create a project called API Integration for customer Coastal Shipping AS... | EN | create_project | 19.8s | 4 | 0 | Yes |
| 62 | 18:50:21 | Create customer Testco AS. Create product Widget at 500 NOK excl VAT... | EN | create_invoice_flow | 46.8s | 11 | 0 | Yes |
| 63 | 19:38:48 | Run salary for employee Test Salary (test.salary.div@test.no)... | EN | run_salary | 23.1s | 6 | 0 | Yes |
| 64 | 19:39:22 | Create a customer called Havblick AS with org number 987654321... | EN | create_invoice_flow | 26.6s | 5 | 0 | Yes |

### Unknown (no API calls — test pings)

| # | Timestamp (UTC) | Prompt | Time (s) | API Calls |
|---|-----------------|--------|----------|-----------|
| 1 | 10:51:26 | Test... | 3.1s | 0 |
| 2 | 10:51:29 | Test... | 3.0s | 0 |
| 3 | 11:33:01 | Test... | 5.1s | 0 |
| 4 | 11:33:07 | Test... | 3.1s | 0 |
| 5 | 11:51:48 | Test... | 11.0s | 0 |
| 6 | 11:52:09 | Test... | 2.8s | 0 |

### Deterministic Container (`ai-accounting-agent-det`) -- Smoke Test Runs

The det container received repeating batches of smoke test tasks. Prompts are reconstructed from smoke_test.py and planner logs. Each batch tests 11 entity types.

| Run | Timestamp (UTC) | Prompt (from smoke_test.py / planner) | Language | Task Type | Time (s) | API Calls | Path | Status |
|-----|-----------------|---------------------------------------|----------|-----------|----------|-----------|------|--------|
| **Run 1** | 11:14:04 | Opprett en avdeling med navn 'TestSalg_...' og avdelingsnummer '...' | NO | create_department | 14.1s | 0 | det+fallback | completed |
| | 11:14:20 | Opprett en ansatt med fornavn 'Kari', etternavn '...', e-post ... og brukertype STANDARD | NO | create_employee | 15.7s | 0 | det+fallback | completed |
| | 11:14:36 | Opprett en kunde med navn '...' og e-post ... | NO | create_customer | 14.2s | 0 | det+fallback | completed |
| | 11:14:51 | Opprett et produkt med navn '...' pris 1500 NOK ekskl. mva og MVA-sats 25% | NO | create_product | 290.9s | 0 | det+fallback | completed |
| | 11:19:42 | Create an employee... | EN | create_employee_en | 15.8s | 0 | det+fallback | completed |
| | 11:19:59 | Erstellen Sie einen Kunden... | DE | create_customer_de | 21.4s | 0 | det+fallback | completed |
| **Run 2** | 14:30:44 | Opprett avdeling | NO | create_department | 12.8s | 0 | det+fallback | completed |
| | 14:30:57 | Opprett ansatt | NO | create_employee | 35.8s | 0 | det+fallback | completed |
| | 14:31:34 | Opprett kunde | NO | create_customer | 15.8s | 0 | det+fallback | completed |
| | 14:31:50 | Opprett produkt | NO | create_product | 283.0s | 0 | det+fallback | completed |
| | 14:36:34 | Opprett reiseregning | NO | create_travel_expense | 23.9s | 0 | det+fallback | completed |
| | 14:36:59 | Opprett prosjekt | NO | create_project | 23.8s | 0 | det+fallback | completed |
| | 14:37:39 | Create invoice flow (200 chars) | NO | create_invoice_flow | *see result* | 0 | det+fallback | completed |
| | 14:38:33 | Opprett reiseregning (travel expense) | NO | create_travel_expense | 59.0s | 0 | det+fallback | completed |
| | 14:39:33 | Opprett prosjekt (project) | NO | create_project | 86.1s | 0 | det+fallback | completed |
| | 14:41:00 | Update customer | NO | update_customer | 28.3s | 0 | fallback | completed |
| | 14:41:29 | Delete department | NO | delete_department | 22.7s | 0 | fallback | completed |
| **Run 3** | 18:10:19 | Opprett avdeling | NO | create_department | 2.6s | 1 | deterministic | completed |
| | 18:10:22 | Opprett ansatt | NO | create_employee | 2.9s | 1 | deterministic | completed |
| | 18:10:25 | Opprett kunde | NO | create_customer | 2.6s | 1 | deterministic | completed |
| | 18:10:28 | Opprett produkt | NO | create_product | 84.8s | 0 | det+fallback | completed |
| | 18:11:54 | Create employee EN | EN | create_employee_en | 2.7s | 1 | deterministic | completed |
| | 18:11:57 | Create customer DE | DE | create_customer_de | 1.7s | 1 | deterministic | completed |
| | 18:12:59 | Create invoice flow | NO | create_invoice_flow | 30.3s | 0 | det+fallback | completed |
| | 18:13:30 | Create travel expense | NO | create_travel_expense | 31.2s | 0 | det+fallback | completed |
| | 18:14:02 | Create project | NO | create_project | 13.4s | 0 | det+fallback | completed |
| | 18:14:16 | Update customer | NO | update_customer | 2.7s | 2 | deterministic | completed |
| | 18:14:19 | Delete department | NO | delete_department | 2.7s | 2 | deterministic | completed |
| **Run 4** | 18:36:50 | Opprett avdeling | NO | create_department | 2.6s | 1 | deterministic | completed |
| | 18:36:54 | Opprett ansatt | NO | create_employee | 3.0s | 1 | deterministic | completed |
| | 18:36:57 | Opprett kunde | NO | create_customer | 2.3s | 1 | deterministic | completed |
| | 18:37:00 | Opprett produkt | NO | create_product | 88.9s | 0 | det+fallback | completed |
| | 18:38:30 | Create employee EN | EN | create_employee_en | 3.0s | 1 | deterministic | completed |
| | 18:38:33 | Create customer DE | DE | create_customer_de | 1.9s | 1 | deterministic | completed |
| **Run 5** | 19:02:40 | Opprett avdeling | NO | create_department | 3.3s | 1 | deterministic | completed |
| | 19:02:44 | Opprett ansatt | NO | create_employee | 2.8s | 1 | deterministic | completed |
| | 19:02:48 | Opprett kunde | NO | create_customer | 2.4s | 1 | deterministic | completed |
| | 19:02:51 | Opprett produkt | NO | create_product | 3.5s | 2 | deterministic | completed |
| | 19:02:55 | Create employee EN | EN | create_employee_en | 4.5s | 1 | deterministic | completed |
| | 19:03:00 | Create customer DE | DE | create_customer_de | 3.6s | 1 | deterministic | completed |
| | 19:03:23 | Create invoice flow | NO | create_invoice_flow | 26.0s | 0 | det+fallback | completed |
| | 19:03:49 | Create travel expense | NO | create_travel_expense | 23.1s | 0 | det+fallback | completed |
| | 19:04:13 | Create project | NO | create_project | 12.1s | 0 | det+fallback | completed |
| | 19:04:26 | Update customer | NO | update_customer | 2.6s | 2 | deterministic | completed |
| | 19:04:29 | Delete department | NO | delete_department | 3.0s | 2 | deterministic | completed |
| **Standalone** | 19:21:55 | *(17 chars -- likely "Test..." or ping)* | ? | test_ping | 15.0s | 0 | fallback | completed |
| | 19:22:28 | Opprett avdeling med namn Test og nr 999 | NO | create_department | 2.6s | 1 | deterministic | completed |
| | 19:33:12 | Opprett avdeling med namn FinalTest og nr 888 | NO | create_department | 2.7s | 1 | deterministic | completed |
| | 19:33:15 | Opprett kunde CurlTest AS | NO | create_customer | 2.2s | 1 | deterministic | completed |
| | 19:37:59 | Create custom dimension "Region" with values... then post voucher | EN | create_custom_dimension | 231.1s | 0 | fallback | completed |

---

## 3. Task Type Distribution

### Competition Requests Only (25 tasks via tx-proxy)

| Task Type | Count | % of Total | Avg Time (s) | Avg API Calls | Avg Errors | Success Rate |
|-----------|-------|------------|--------------|---------------|------------|--------------|
| create_invoice | 4 | 16% | 127.7 | 14.2 | 4.2 | 75% (3/4) |
| create_project | 3 | 12% | 26.2 | 4.0 | 0.0 | 100% (3/3) |
| create_customer | 3 | 12% | 16.4 | 1.3 | 0.0 | 100% (3/3) |
| create_departments (batch) | 2 | 8% | 13.1 | 3.0 | 0.0 | 100% (2/2) |
| register_payment | 2 | 8% | 88.9 | 12.5 | 1.0 | 100% (2/2) |
| create_employee | 2 | 8% | 25.2 | 3.0 | 0.0 | 100% (2/2) |
| create_supplier | 2 | 8% | 15.8 | 1.5 | 0.0 | 100% (2/2) |
| run_salary | 2 | 8% | 151.4 | 18.5 | 6.0 | 100% (2/2) |
| create_project_fixed_price | 2 | 8% | 72.3 | 10.0 | 1.0 | 100% (2/2) |
| register_supplier_invoice | 1 | 4% | 68.8 | 10.0 | 1.0 | 100% (1/1) |
| create_order | 1 | 4% | 66.0 | 13.0 | 3.0 | 100% (1/1) |
| create_custom_dimension | 1 | 4% | 254.1 | 5.0 | 5.0 | 100% (1/1) |
| **TOTAL** | **25** | **100%** | **70.5** | **7.9** | **1.7** | **96% (24/25)** |

### Competition Language Distribution

| Language | Count | % |
|----------|-------|---|
| Norwegian (NO) | 7 | 28% |
| Portuguese (PT) | 5 | 20% |
| Spanish (ES) | 5 | 20% |
| French (FR) | 3 | 12% |
| English (EN) | 3 | 12% |
| German (DE) | 2 | 8% |

### Competition Tier Distribution

| Tier | Count | % | Avg Time | Avg Errors | Success |
|------|-------|---|----------|------------|---------|
| Tier 1 (single-entity CRUD) | 9 | 36% | 16.2s | 0.0 | 100% (9/9) |
| Tier 2 (multi-step flows) | 5 | 20% | 61.8s | 1.2 | 80% (4/5) |
| Tier 3 (complex/salary/vouchers) | 11 | 44% | 112.0s | 2.7 | 100% (11/11) |

### Test Request Distribution (64 tasks via kkpqfuj-amager)

| Task Type | Count | Avg Time (s) | Success Rate |
|-----------|-------|--------------|--------------|
| create_customer | 10 | 8.2 | 100% |
| create_employee | 8 | 50.7 | 88% (7/8) |
| create_department | 5 | 8.7 | 100% |
| create_invoice | 4 | 41.3 | 100% |
| create_invoice_flow | 5 | 29.7 | 100% |
| create_travel_expense | 5 | 17.2 | 100% |
| create_supplier | 3 | 7.8 | 100% |
| create_product | 3 | 7.7 | 100% |
| delete_travel_expense | 3 | 10.8 | 100% |
| create_contact | 3 | 12.8 | 100% |
| create_project | 3 | 146.4 | 100% |
| update_customer | 2 | 13.1 | 100% |
| create_credit_note | 1 | 24.6 | 100% |
| create_voucher | 1 | 21.6 | 100% |
| run_salary | 1 | 23.1 | 100% |
| unknown/unlogged | 6 | ? | ? |

---

## 4. Competition-Critical Observations

### 4.1 Key Correction: Competition Had 25 Tasks, Not 79

The original analysis mixed competition and test requests. After separating by API base URL:
- **Competition (tx-proxy):** 25 tasks across ~15 submission batches
- **Our tests (kkpqfuj):** 64 tasks from manual testing and smoke tests
- **Unknown pings:** 6 test pings with 0 API calls

With 26 submissions used, some submissions were single-task tests while Batch 6 sent 5 tasks at once.

### 4.2 Failed Tasks (Competition Only)

| # | Timestamp | Task Type | Time | Errors | Likely Cause |
|---|-----------|-----------|------|--------|--------------|
| 2 | 13:10:19 | create_invoice (ES) | 330.2s | 9 | Spanish-language invoice with 3 product lines for Dorada SL. Exceeded timeout with 19 API calls. Complex multi-product invoice creation in non-English language. |

Only **1 competition task failed** (96% success rate). The employee creation failure (#43 in old numbering) was actually a test request.

### 4.3 High-Error Competition Tasks (errors >= 2)

| # | Timestamp | Task Type | Time | API | Errors | Notes |
|---|-----------|-----------|------|-----|--------|-------|
| 16 | 18:52:17 | create_custom_dimension | 254.1s | 5 | 5 | Custom dimension + voucher posting. Every API call errored but task eventually marked as success. |
| 22 | 19:24:00 | run_salary (PT) | 230.4s | 24 | 10 | Portuguese salary run. Extremely high API call count with many retries. |
| 2 | 13:10:19 | create_invoice (ES) | 330.2s | 19 | 9 | Failed -- Spanish 3-product invoice. |
| 9 | 17:45:33 | create_order (FR) | 66.0s | 13 | 3 | French order creation. High error count despite success. |
| 15 | 18:09:00 | create_invoice (NO) | 55.6s | 13 | 3 | Norwegian multi-product invoice. Recovered from errors. |
| 17 | 19:01:22 | create_invoice (PT) | 56.3s | 13 | 3 | Portuguese multi-product invoice. |

### 4.4 Competition Task Types that Score Poorly

1. **create_invoice (multi-product)**: 4 competition tasks, avg 127.7s, 4.2 errors, 75% success. The ES variant failed entirely (330.2s timeout). This is the highest-impact task type to fix.
2. **run_salary**: 2 tasks, avg 151.4s, 6.0 errors. Portuguese salary run took 230.4s with 10 errors. Extremely slow.
3. **create_custom_dimension**: 1 task, 254.1s, 5 errors. 100% API error rate. The agent brute-forces through.
4. **create_order**: 1 task, 66.0s, 3 errors. French order creation struggles with multi-product setup.

### 4.5 What the Competition Actually Tests (vs What We Tested)

The competition platform favors **Tier 2-3 tasks much more heavily** than our test suite assumed:
- **44% of competition tasks are Tier 3** (salary, payment, supplier invoice, fixed price, custom dimension)
- **20% are Tier 2** (invoice, order, project)
- **36% are Tier 1** (customer, employee, supplier, departments)

Task types we tested heavily but never appeared in competition:
- `create_contact`, `create_product`, `create_travel_expense`, `delete_travel_expense` (none in competition)
- `create_invoice_flow` (end-to-end customer+product+invoice+payment, never in competition)
- `create_voucher`, `create_credit_note`, `update_customer` (never in competition)
- `create_department` (single, never in competition -- only batch `create_departments`)

Task types in competition that we under-tested:
- `register_payment` (2 competition tasks, 0 in our Tier 1-2 tests)
- `register_supplier_invoice` (1 competition task, 0 in tests)
- `create_project_fixed_price` (2 competition tasks, 0 in tests)
- `create_order` (1 competition task, 0 in tests)

### 4.6 Scoring Model (revised from competition data)

Competition submissions are NOT uniform 10-13 task batches. The actual pattern is:
- Many single-task submissions (testing one task type at a time)
- Occasional multi-task batches (Batch 6 had 5 tasks)
- Heavy emphasis on Tier 3 complex tasks (44% of all tasks)

Each submission typically sends 1-5 tasks, not 10-13 as previously estimated.

### 4.7 Det Container Performance vs Original

**Deterministic path works well for Tier 1:**
- create_department: 2.5s det vs 9.7s original (3.9x faster)
- create_customer: 2.4s det vs 9.8s original (4.1x faster)
- create_employee: 2.9s det vs 45.5s original (15.7x faster)
- 1 API call, 0 errors, 100% success on deterministic path

**Deterministic path struggles with:**
- create_product: Some runs fell back to LLM (88.9s), but Run 5 succeeded deterministically (3.5s, 2 API calls). Likely a bug fix between runs.
- create_invoice_flow: Always falls back (det+fallback), ~26s. Missing deterministic handler for multi-entity flows.
- create_travel_expense: Always falls back (det+fallback), ~23-31s. Missing employee lookup or travel expense handler.
- create_project: Always falls back (det+fallback), ~12-86s. Missing project manager/employee dependency resolution.

**Key det container validation errors observed:**
- Employee creation: `"Ma angis for Tripletex-brukere."` (email required for Tripletex users) -- the deterministic planner does not always set email.
- Travel expense: `"Kan ikke vaere null."` for employee field -- travel expense requires an employee ID that the det planner fails to provide.

### 4.8 Optimization Priority (revised by actual competition impact)

| Priority | Task Type | Why | Current Gap |
|----------|-----------|-----|-------------|
| 1 | create_invoice (multi-product) | 16% of competition tasks, 75% success, 127.7s avg | Need deterministic handler for multi-product invoices |
| 2 | run_salary | 8% of tasks, Tier 3, 151.4s avg, 6 avg errors | Need deterministic salary flow |
| 3 | create_project_fixed_price | 8% of tasks, 72.3s avg | Need fixed-price project handler |
| 4 | register_payment | 8% of tasks, 88.9s avg | Need payment registration handler |
| 5 | create_custom_dimension | 4% but 254s, 5 errors | Need custom dimension API handler |
| 6 | register_supplier_invoice | 4%, 68.8s, 1 error | Need supplier invoice handler |
| 7 | create_order | 4%, 66.0s, 3 errors | Need order creation handler |

### 4.9 Fresh Sandbox Gotchas

1. **Non-English prompts cause more retries**: The agent makes significantly more errors on ES/PT/FR prompts for complex tasks vs English equivalents.
2. **Multi-product invoices are fragile**: Invoices with 3+ product lines require creating customer + multiple products + order + invoice. Each step can fail and the agent retries from scratch.
3. **Salary runs are extremely slow**: Even successful salary runs take 72-230s with many retries.
4. **Custom dimensions are almost entirely unsupported**: The agent falls back to pure LLM and hits 100% error rate on API calls.
5. **Fixed-price project setup**: Spanish-language fixed-price tasks take 60-85s with 1 error. The `projectFixedPrice` API is uncommon and the agent needs multiple attempts.
6. **Payment registration is complex**: Requires finding customer, finding invoice, posting payment with correct type. Multi-step process with high API count.
