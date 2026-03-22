"""Keyword-based multilingual task classifier.

Classifies accounting task prompts into known task types using regex patterns.
Patterns are ordered most-specific-first so that e.g. "register_supplier_invoice"
matches before "create_supplier" and "fixed_price_project" before "create_project".
"""
import re

# (task_type, [regex_patterns]) — ordered most specific first
TASK_PATTERNS: list[tuple[str, list[str]]] = [
    # --- New specific patterns (must match before generic patterns) ---
    ("year_end_close", [
        r"jahresabschluss", r"year.?end.*clos", r"cierre.*anual", r"encerramento.*anual",
        r"årsavslutning", r"clôture.*annuel", r"abschreibung.*anlagen",
        r"årsoppgjør", r"årsoppgjer",
        r"fechamento\s*anual", r"cl[oô]ture\s*annuelle",
        r"abschreibung.*steuerr[üu]ckstellung",
        r"steuerr[üu]ckstellung.*abschreibung",
        r"depreciation.*tax\s*provision", r"tax\s*provision.*depreciation",
        r"avskrivning.*skatteavsetning", r"skatteavsetning.*avskrivning",
    ]),
    ("year_end_corrections", [
        r"erreurs.*grand.*livre", r"errors.*ledger", r"errores.*libro.*mayor",
        r"erros.*razão", r"fehler.*hauptbuch", r"feil.*hovedbok",
        r"correction.*voucher", r"korrigering",
    ]),
    ("monthly_closing", [
        r"cierre.*mensual", r"monthly.*clos", r"månedsslutt", r"monatsabschluss",
        r"clôture.*mensuel", r"encerramento.*mensal", r"periodificación",
        r"periodisering", r"deprecia.*mensual",
        r"månedsavslutning", r"månavslutninga", r"månedsavslutninga",
        r"lønnsavsetning.*periodiser", r"lønnsavsetjing",
        r"periodiser.*avskrivning", r"avskrivning.*periodiser",
    ]),
    ("cost_analysis_projects", [
        r"kostnadsanalyse", r"cost.*analy[sz]", r"análisis.*costo", r"análise.*custo",
        r"kostenanalyse", r"analyse.*coût", r"totalkostnad.*økte",
        r"totalkostnad.*auk", r"kostnadskonto.*auk",
        r"gesamtkosten.*gestiegen", r"costos.*aumentaron", r"largest.*increase",
        r"costs.*increas", r"total.*costs", r"expense.*accounts.*increase",
    ]),
    ("project_lifecycle", [
        r"ciclo.*vida.*pro[jy]", r"lifecycle.*project", r"prosjektlivssyklus",
        r"lebenszyklus.*projekt", r"cycle.*vie.*projet",
        r"orçamento.*registe.*horas", r"budget.*register.*hours",
        r"full.*project.*lifecycle", r"complete.*project.*lifecycle",
        r"ciclo.*completo.*pro[jy]", r"vollständig.*projekt",
        r"prosjektsyklus", r"heile.*prosjekt",
        r"budsjett.*registrer.*timar", r"budget.*hours.*supplier.*invoice",
    ]),
    ("overdue_invoice_reminder", [
        r"überfällig.*rechnung", r"overdue.*invoice", r"factura.*vencid[ao]",
        r"fatura.*vencid[ao]", r"purregebyr", r"mahnung", r"reminder.*fee",
        r"cargo.*recordatorio", r"taxa.*lembrete", r"frais.*rappel",
    ]),
    ("forex_payment", [
        r"valuta", r"exchange\s*rate", r"tipo\s*de\s*cambio", r"taxa\s*de\s*câmbio",
        r"wechselkurs", r"taux\s*de\s*change", r"agio", r"disagio",
        r"kurs.*eur", r"eur.*kurs", r"rate.*eur", r"eur.*rate",
    ]),
    # --- Original composite / specific patterns ---
    # bank_reconciliation MUST come before register_supplier_invoice
    # because bank reconciliation prompts mention "factures" (invoices)
    ("bank_reconciliation", [
        r"bank.*avstemming", r"bank.*reconcil", r"reconcil.*bank",
        r"concilia.*banc", r"rapproch.*bancaire",
        r"relev[ée]\s*bancaire", r"kontoauszug", r"bankutskrift",
        r"bank\s*statement", r"extracto\s*banc", r"extrato\s*banc",
    ]),
    ("register_supplier_invoice", [
        r"leverandør.*faktura", r"faktura.*leverandør",
        r"leverandor.*faktura", r"faktura.*leverandor",
        r"supplier.*invoice", r"invoice.*supplier",
        r"proveedor.*factura", r"factura.*proveedor",
        r"fornecedor.*fatura", r"fatura.*fornecedor",
        r"lieferant.*rechnung", r"rechnung.*lieferant",
        r"fournisseur.*facture", r"facture.*fournisseur",
    ]),
    ("fixed_price_project", [
        r"fast\s*pris", r"fixed\s*price", r"precio\s*fijo", r"preço\s*fixo",
        r"festpreis", r"prix\s*fixe",
    ]),
    ("reverse_payment", [
        r"reverser.*betaling", r"reverse.*payment", r"revertir.*pago",
        r"reverter.*pagamento", r"stornierung", r"annuler.*paiement",
        r"stornieren.*zahlung", r"zahlung.*stornieren",
        r"zurückgebucht", r"tilbakeført.*betaling", r"betaling.*tilbakeført",
        r"cancelar.*pago", r"anular.*pagamento",
    ]),
    ("credit_note", [
        r"kreditnota", r"credit\s*note", r"nota\s*de\s*crédito", r"gutschrift",
        r"note\s*de\s*crédit",
        r"avoir.*annul", r"[ée]mettez.*avoir", r"émettre.*avoir",
    ]),
    ("employee_onboarding", [
        r"arbeidskontrakt", r"employment.*contract", r"contrat.*travail",
        r"contrato.*trabalho", r"contrato.*trabajo",
        r"carta\s*de\s*oferta", r"lettre\s*d.offre", r"tilbudsbrev",
        r"offer\s*letter", r"carta\s*de\s*ofrecimiento",
        r"integracao", r"integra[cç][aã]o", r"integration.*employ",
        r"incorporaci[oó]n", r"int[eé]gration.*employ",
        r"new\s*employee.*start", r"ny\s*ansatt.*start", r"neuer\s*mitarbeiter.*start",
        r"nouvel\s*employ.*début", r"nuevo\s*empleado.*empez", r"novo\s*funcion.*início",
    ]),
    ("travel_expense", [
        r"reise", r"travel.*expense", r"gastos.*viaje", r"despesas.*viagem",
        r"reisekosten", r"frais.*voyage", r"reiserekning", r"reiseregning",
        r"despesa.*recibo", r"recibo.*despesa", r"expense.*receipt",
        r"receipt.*expense", r"kvittering", r"beleg.*ausgabe",
    ]),
    ("register_hours", [
        r"timer", r"\d+\s*hours", r"register.*hours", r"erfassen.*stunden",
        r"\d+\s*horas", r"registe.*horas", r"\d+\s*stunden",
        r"\d+\s*heures", r"timeføring", r"timesheet",
    ]),
    ("custom_dimension", [
        r"dimensjon", r"dimension", r"dimensión", r"dimensão",
    ]),
    ("run_salary", [
        r"kj[øo]r.*l[øo]nn", r"l[øo]nnskj[øo]ring", r"l[øo]nnsutbetaling",
        r"run.*salary", r"ejecute.*nómina", r"execute.*folha",
        r"gehalt.*auszahlen", r"gehaltsabrechnung", r"exécuter.*paie",
        r"processar.*folha", r"process.*payroll", r"salary.*run",
        r"process.*sal[aá]rio",
    ]),
    ("register_payment", [
        r"betal", r"payment", r"pago", r"pagamento", r"zahlung", r"paiement",
    ]),
    ("create_invoice", [
        r"faktura(?!@)", r"invoice", r"factura(?!@)", r"fatura(?!@)", r"rechnung", r"facture(?!@)",
    ]),
    ("create_order", [
        r"bestilling", r"order", r"pedido", r"encomenda", r"bestellung", r"commande",
        r"auftrag",
    ]),
    ("create_project", [
        r"prosjekt", r"project", r"proyecto", r"projeto", r"projekt", r"projet",
    ]),
    ("create_departments", [
        r"avdeling", r"department", r"departamento", r"abteilung", r"département",
    ]),
    ("create_employee", [
        r"ansatt", r"employee", r"empleado", r"funcionário", r"mitarbeiter", r"employé",
    ]),
    ("create_customer", [
        r"kunde", r"customer", r"cliente", r"client",
    ]),
    ("create_supplier", [
        r"leverandør", r"supplier", r"proveedor", r"fornecedor",
        r"lieferant", r"fournisseur",
    ]),
    ("create_product", [
        r"produkt", r"product", r"producto", r"produto", r"produit",
    ]),
]


def classify_task(prompt: str) -> str | None:
    """Classify a task prompt into a known task type.

    Returns the task_type string or None if no pattern matches.
    """
    prompt_lower = prompt.lower()
    for task_type, patterns in TASK_PATTERNS:
        for pattern in patterns:
            if re.search(pattern, prompt_lower):
                return task_type
    return None
