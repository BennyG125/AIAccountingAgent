"""Keyword-based multilingual task classifier.

Classifies accounting task prompts into known task types using regex patterns.
Patterns are ordered most-specific-first so that e.g. "register_supplier_invoice"
matches before "create_supplier" and "fixed_price_project" before "create_project".
"""
import re

# (task_type, [regex_patterns]) — ordered most specific first
TASK_PATTERNS: list[tuple[str, list[str]]] = [
    # Composite / specific patterns first
    ("year_end_close", [
        r"jahresabschluss", r"year.?end\s*clos", r"årsavslutning", r"årsoppgjør",
        r"cierre\s*anual", r"fechamento\s*anual", r"cl[oô]ture\s*annuelle",
        r"abschreibung.*steuerr[üu]ckstellung",
        r"steuerr[üu]ckstellung.*abschreibung",
        r"depreciation.*tax\s*provision", r"tax\s*provision.*depreciation",
        r"avskrivning.*skatteavsetning", r"skatteavsetning.*avskrivning",
    ]),
    ("register_supplier_invoice", [
        r"leverandør.*faktura", r"faktura.*leverandør",
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
    ]),
    ("credit_note", [
        r"kreditnota", r"credit\s*note", r"nota\s*de\s*crédito", r"gutschrift",
        r"note\s*de\s*crédit",
    ]),
    ("bank_reconciliation", [
        r"bank.*avstemming", r"bank.*reconcil", r"concilia.*banc",
        r"rapproch.*bancaire",
    ]),
    ("employee_onboarding", [
        r"arbeidskontrakt", r"employment.*contract", r"contrat.*travail",
        r"contrato.*trabajo",
    ]),
    ("travel_expense", [
        r"reise", r"travel.*expense", r"gastos.*viaje", r"despesas.*viagem",
        r"reisekosten", r"frais.*voyage", r"reiserekning", r"reiseregning",
    ]),
    ("register_hours", [
        r"timer", r"hours", r"horas", r"stunden", r"heures", r"timeføring",
    ]),
    ("custom_dimension", [
        r"dimensjon", r"dimension", r"dimensión", r"dimensão",
    ]),
    ("run_salary", [
        r"l[øo]nn", r"salary", r"salario", r"salário", r"gehalt", r"salaire",
    ]),
    ("register_payment", [
        r"betal", r"payment", r"pago", r"pagamento", r"zahlung", r"paiement",
    ]),
    ("create_invoice", [
        r"faktura", r"invoice", r"factura", r"fatura", r"rechnung", r"facture",
    ]),
    ("create_order", [
        r"bestilling", r"order", r"pedido", r"encomenda", r"bestellung", r"commande",
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
