"""Keyword-based multilingual task classifier with language detection.

Detects prompt language first, then routes to language-specific regex patterns
before falling back to universal patterns. Patterns are ordered most-specific-first
so that e.g. "register_supplier_invoice" matches before "create_supplier".
"""
import re

# ---------------------------------------------------------------------------
# Language detection — simple, fast, no external dependencies
# ---------------------------------------------------------------------------

# Character markers and high-frequency words per language
_LANG_MARKERS = {
    "no": {
        "chars": set("øåæ"),
        "words": [
            r"\bog\b", r"\bfor\b", r"\bmed\b", r"\bhar\b", r"\bden\b",
            r"\bsom\b", r"\bopprett\b", r"\bfaktura\b", r"\bkunde\b",
            r"\bavdeling\b", r"\bansatt\b", r"\bleverandør\b",
        ],
    },
    "nn": {  # Nynorsk — distinct from Bokmål
        "chars": set(),
        "words": [
            r"\bmotteke\b", r"\btilsett\b", r"\btimar\b", r"\bsjaa\b",
            r"\bhovudboka?\b", r"\boppdaga\b", r"\bheile\b", r"\bein\b",
            r"\bgjer\b", r"\brekn\b", r"\bauk\b", r"\bforfalln?e\b",
            r"\bfrå\b", r"\bmånavslutninga\b", r"\btilbod\b",
        ],
    },
    "de": {
        "chars": set("äöüß"),
        "words": [
            r"\bund\b", r"\bder\b", r"\bdie\b", r"\bdas\b", r"\bein\b",
            r"\berstellen\b", r"\brechnung\b", r"\bkunde\b", r"\blieferant\b",
            r"\bmitarbeiter\b", r"\babteilung\b",
        ],
    },
    "fr": {
        "chars": set("éèêëàâùûüïôœç"),
        "words": [
            r"\bune?\b", r"\ble\b", r"\bla\b", r"\bles\b", r"\bdes\b",
            r"\bcréez\b", r"\bfacture\b", r"\bclient\b", r"\bfournisseur\b",
            r"\bemployé\b", r"\bdépartement\b", r"\benvoyez\b",
        ],
    },
    "es": {
        "chars": set("ñ¿¡"),
        "words": [
            r"\by\b", r"\bdel\b", r"\bcon\b", r"\bpara\b", r"\buna?\b",
            r"\bcree?\b", r"\bfactura\b", r"\bcliente\b", r"\bproveedor\b",
            r"\bempleado\b", r"\bdepartamento\b", r"\benv[ií]e\b",
        ],
    },
    "pt": {
        "chars": set("ãõ"),
        "words": [
            r"\be\b", r"\bcom\b", r"\bpara\b", r"\buma?\b", r"\bdos?\b",
            r"\bcrie\b", r"\bfatura\b", r"\bcliente\b", r"\bfornecedor\b",
            r"\bfuncionário\b", r"\bdepartamento\b", r"\benvie\b",
            r"\bregistre\b", r"\bprojeto\b", r"\bproduto\b", r"\bpagamento\b",
            r"\btrabalho\b", r"\bempresa\b", r"\bnovo\b", r"\bnova\b",
        ],
    },
    "en": {
        "chars": set(),
        "words": [
            r"\bthe\b", r"\band\b", r"\bfor\b", r"\bwith\b", r"\bcreate\b",
            r"\binvoice\b", r"\bcustomer\b", r"\bsupplier\b", r"\bemployee\b",
            r"\bdepartment\b", r"\bsend\b",
        ],
    },
}


def detect_language(prompt: str) -> str:
    """Detect the language of a prompt. Returns ISO 639-1 code or 'nn' for Nynorsk.

    Uses character markers first (most reliable), then word frequency scoring.
    """
    prompt_lower = prompt.lower()

    # Nynorsk check first — specific words that distinguish it from Bokmål
    nn_markers = _LANG_MARKERS["nn"]["words"]
    nn_hits = sum(1 for w in nn_markers if re.search(w, prompt_lower))
    if nn_hits >= 2:
        return "nn"

    # Character-based detection (most reliable for de/fr/es/pt/no)
    char_scores: dict[str, int] = {}
    for lang, info in _LANG_MARKERS.items():
        if lang == "nn":
            continue
        chars = info["chars"]
        if chars:
            hits = sum(1 for c in prompt_lower if c in chars)
            if hits > 0:
                char_scores[lang] = hits

    # If we have a clear character winner, use it
    if char_scores:
        best = max(char_scores, key=char_scores.get)
        # Norwegian chars (øåæ) are definitive
        if best == "no":
            return "no"
        # PT vs FR disambiguation: shared chars (é, ê, ç) cause PT→FR misdetection.
        # Cross-check with word frequency whenever FR wins on characters.
        if best == "fr":
            pt_words = _LANG_MARKERS["pt"]["words"]
            fr_words = _LANG_MARKERS["fr"]["words"]
            pt_hits = sum(1 for w in pt_words if re.search(w, prompt_lower))
            fr_hits = sum(1 for w in fr_words if re.search(w, prompt_lower))
            if pt_hits > fr_hits:
                return "pt"
        # For others, require at least 1 char hit to distinguish
        if char_scores[best] >= 1:
            return best

    # Word frequency fallback
    word_scores: dict[str, int] = {}
    for lang, info in _LANG_MARKERS.items():
        if lang == "nn":
            continue
        hits = sum(1 for w in info["words"] if re.search(w, prompt_lower))
        word_scores[lang] = hits

    if word_scores:
        best = max(word_scores, key=word_scores.get)
        if word_scores[best] >= 2:
            return best

    return "en"  # default fallback


# ---------------------------------------------------------------------------
# Language-specific task patterns
# ---------------------------------------------------------------------------
# These are checked FIRST for the detected language, giving precise matches
# before falling back to universal patterns.

LANG_PATTERNS: dict[str, list[tuple[str, list[str]]]] = {
    "no": [
        ("year_end_close", [r"årsoppgjør", r"årsavslutning", r"avskrivning.*skatteavsetning"]),
        ("year_end_corrections", [r"feil.*hovedbok", r"korrigering"]),
        ("monthly_closing", [r"månedsavslutning", r"periodisering", r"lønnsavsetning"]),
        ("cost_analysis_projects", [r"kostnadsanalyse", r"totalkostnad.*økte"]),
        ("project_lifecycle", [r"prosjektsyklus", r"prosjektlivssyklus"]),
        ("overdue_invoice_reminder", [r"purregebyr", r"forfalt.*faktura"]),
        ("bank_reconciliation", [r"bank.*avstemming", r"bankutskrift"]),
        ("register_supplier_invoice", [r"leverandør.*faktura(?!@)", r"faktura(?!@).*leverandør"]),
        ("reverse_payment", [r"reverser.*betaling", r"tilbakeført.*betaling"]),
        ("credit_note", [r"kreditnota"]),
        ("employee_onboarding", [r"arbeidskontrakt", r"tilbudsbrev", r"ny\s*ansatt"]),
        ("travel_expense", [r"reise(?:kostnad|rekning|regning)", r"kvittering"]),
        ("register_hours", [r"\btimer\b", r"timeføring"]),
        ("run_salary", [r"kj[øo]r.*l[øo]nn", r"l[øo]nnskj[øo]ring", r"l[øo]nnsutbetaling"]),
        ("custom_dimension", [r"dimensjon"]),
        ("forex_payment", [r"valuta", r"kurs.*eur"]),
        ("register_payment", [r"betal"]),
        ("create_invoice", [r"faktura(?!@)"]),
        ("create_departments", [r"avdeling"]),
        ("create_employee", [r"ansatt"]),
        ("create_project", [r"prosjekt"]),
        ("create_customer", [r"opprett.*kunde", r"\bny\s+kunde\b", r"\bkunder?\b.*(?:registrer|legg)"]),
        ("create_supplier", [r"leverandør"]),
        ("create_product", [r"produkt"]),
        ("create_order", [r"bestilling"]),
    ],
    "nn": [
        ("year_end_close", [r"årsoppgjer", r"avskrivning.*skatteavsetjing"]),
        ("year_end_corrections", [r"feil.*hovudbok", r"oppdaga.*feil"]),
        ("monthly_closing", [r"månavslutninga", r"lønnsavsetjing", r"periodiser"]),
        ("cost_analysis_projects", [r"totalkostnad.*auk", r"kostnadskonto.*auk"]),
        ("project_lifecycle", [r"heile.*prosjekt", r"prosjektsyklus"]),
        ("overdue_invoice_reminder", [r"purregebyr", r"forfallen.*faktura"]),
        ("bank_reconciliation", [r"bank.*avstemming"]),
        ("register_supplier_invoice", [r"leverandor.*faktura(?!@)", r"faktura(?!@).*leverandor"]),
        ("employee_onboarding", [r"tilbodsbrev"]),
        ("travel_expense", [r"reiserekning"]),
        ("register_hours", [r"\btimar\b"]),
        ("run_salary", [r"kj[øo]r.*l[øo]nn"]),
        ("custom_dimension", [r"dimensjon"]),
        ("create_employee", [r"tilsett"]),
    ],
    "de": [
        ("year_end_close", [r"jahresabschluss", r"abschreibung", r"steuerr[üu]ckstellung"]),
        ("year_end_corrections", [r"fehler.*hauptbuch"]),
        ("monthly_closing", [r"monatsabschluss"]),
        ("cost_analysis_projects", [r"kostenanalyse", r"gesamtkosten.*gestiegen"]),
        ("project_lifecycle", [r"projektzyklus", r"projekt.*lebenszyklus", r"vollst[äa]ndig.*projekt"]),
        ("overdue_invoice_reminder", [r"[üu]berf[äa]llig.*rechnung", r"mahngeb[üu]hr", r"mahnung"]),
        ("bank_reconciliation", [r"kontoauszug"]),
        ("register_supplier_invoice", [r"lieferant.*rechnung", r"rechnung.*lieferant"]),
        ("fixed_price_project", [r"festpreis"]),
        ("reverse_payment", [r"stornierung", r"stornieren.*zahlung", r"zur[üu]ckgebucht"]),
        ("credit_note", [r"gutschrift"]),
        ("employee_onboarding", [r"arbeitsvertrag", r"neuer\s*mitarbeiter"]),
        ("travel_expense", [r"reisekosten", r"beleg.*ausgabe"]),
        ("register_hours", [r"erfassen.*stunden", r"\d+\s*stunden"]),
        ("run_salary", [r"gehalt.*auszahlen", r"gehaltsabrechnung"]),
        ("custom_dimension", [r"dimension"]),
        ("forex_payment", [r"wechselkurs"]),
        ("register_payment", [r"zahlung"]),
        ("create_invoice", [r"rechnung"]),
        ("create_departments", [r"abteilung"]),
        ("create_employee", [r"mitarbeiter"]),
        ("create_supplier", [r"lieferant"]),
        ("create_product", [r"produkt"]),
        ("create_project", [r"projekt"]),
        ("create_order", [r"bestellung", r"auftrag"]),
    ],
    "fr": [
        ("year_end_close", [r"cl[oô]ture.*annuel"]),
        ("year_end_corrections", [r"erreurs.*grand.*livre"]),
        ("monthly_closing", [r"clôture.*mensuel"]),
        ("cost_analysis_projects", [r"analyse.*coût"]),
        ("project_lifecycle", [r"cycle.*vie.*projet"]),
        ("overdue_invoice_reminder", [r"frais.*rappel"]),
        ("bank_reconciliation", [r"rapproch.*bancaire", r"relev[ée]\s*bancaire"]),
        ("register_supplier_invoice", [r"fournisseur.*facture(?!@)", r"facture(?!@).*fournisseur"]),
        ("fixed_price_project", [r"prix\s*fixe"]),
        ("reverse_payment", [r"annul.*paiement", r"retourné"]),
        ("credit_note", [r"note\s*de\s*crédit", r"avoir.*annul", r"[ée]mettez.*avoir"]),
        ("employee_onboarding", [r"contrat.*travail", r"lettre\s*d.offre", r"int[eé]gration.*employ"]),
        ("travel_expense", [r"frais.*voyage", r"note\s*de\s*frais", r"d[eé]pense.*re[cç]u"]),
        ("register_hours", [r"\d+\s*heures"]),
        ("run_salary", [r"ex[eé]cut\w*.*paie", r"\bpaie\b"]),
        ("custom_dimension", [r"dimension"]),
        ("forex_payment", [r"taux\s*de\s*change"]),
        ("register_payment", [r"paiement"]),
        ("create_invoice", [r"facture(?!@)"]),
        ("create_departments", [r"département"]),
        ("create_employee", [r"employé"]),
        ("create_project", [r"projet"]),
        ("create_customer", [r"créez.*client", r"nouveau.*client"]),
        ("create_supplier", [r"fournisseur"]),
        ("create_product", [r"produit"]),
        ("create_order", [r"commande"]),
    ],
    "es": [
        ("year_end_close", [r"cierre.*anual"]),
        ("year_end_corrections", [r"errores.*libro.*mayor"]),
        ("monthly_closing", [r"cierre.*mensual", r"periodificación"]),
        ("cost_analysis_projects", [r"análisis.*costo", r"costos.*aumentaron"]),
        ("project_lifecycle", [r"ciclo.*vida.*pro[jy]", r"ciclo.*completo"]),
        ("overdue_invoice_reminder", [r"factura.*vencid[ao]", r"cargo.*recordatorio"]),
        ("bank_reconciliation", [r"concilia.*banc", r"extracto\s*banc"]),
        ("register_supplier_invoice", [r"proveedor.*factura(?!@)", r"factura(?!@).*proveedor"]),
        ("fixed_price_project", [r"precio\s*fijo"]),
        ("reverse_payment", [r"revertir.*pago", r"cancel.*pago", r"devuelt[oa]"]),
        ("credit_note", [r"nota\s*de\s*crédito"]),
        ("employee_onboarding", [r"contrato.*trabajo", r"carta\s*de\s*oferta", r"incorporaci[oó]n"]),
        ("travel_expense", [r"gastos.*viaje"]),
        ("register_hours", [r"\d+\s*horas", r"regist[re].*horas"]),
        ("run_salary", [r"ejecute.*nómina"]),
        ("custom_dimension", [r"dimensi[oó]n"]),
        ("forex_payment", [r"tipo\s*de\s*cambio"]),
        ("register_payment", [r"pago"]),
        ("create_invoice", [r"factura(?!@)"]),
        ("create_departments", [r"departamento"]),
        ("create_employee", [r"empleado"]),
        ("create_project", [r"proyecto"]),
        ("create_customer", [r"cree.*cliente", r"nuevo.*cliente", r"registr.*cliente"]),
        ("create_supplier", [r"proveedor"]),
        ("create_product", [r"producto"]),
        ("create_order", [r"pedido"]),
    ],
    "pt": [
        ("year_end_close", [r"encerramento.*anual", r"fechamento\s*anual"]),
        ("year_end_corrections", [r"erros.*razão"]),
        ("monthly_closing", [r"encerramento.*mensal"]),
        ("cost_analysis_projects", [r"análise.*custo"]),
        ("project_lifecycle", [r"ciclo.*vida.*pro[jy]"]),
        ("overdue_invoice_reminder", [r"fatura.*vencid[ao]", r"taxa.*lembrete"]),
        ("bank_reconciliation", [r"extrato\s*banc"]),
        ("register_supplier_invoice", [r"fornecedor.*fatura(?!@)", r"fatura(?!@).*fornecedor"]),
        ("fixed_price_project", [r"preço\s*fixo"]),
        ("reverse_payment", [r"reverter.*pagamento", r"cancel.*pagamento", r"devolvid[oa]"]),
        ("credit_note", [r"nota\s*de\s*crédito"]),
        ("employee_onboarding", [r"contrato.*trabalho", r"carta\s*de\s*ofrecimiento"]),
        ("travel_expense", [r"despesas.*viagem", r"despesa.*recibo"]),
        ("register_hours", [r"\d+\s*horas", r"regist[re].*horas"]),
        ("run_salary", [r"execute.*folha", r"processar.*folha", r"process.*sal[aá]rio"]),
        ("custom_dimension", [r"dimensão"]),
        ("forex_payment", [r"taxa\s*de\s*câmbio"]),
        ("register_payment", [r"pagamento"]),
        ("create_invoice", [r"fatura(?!@)"]),
        ("create_departments", [r"departamento"]),
        ("create_employee", [r"funcionário"]),
        ("create_project", [r"projeto"]),
        ("create_customer", [r"crie.*cliente", r"novo.*cliente", r"registr.*cliente"]),
        ("create_supplier", [r"fornecedor"]),
        ("create_product", [r"produto"]),
        ("create_order", [r"encomenda"]),
    ],
    "en": [
        ("year_end_close", [r"year.?end.*clos", r"depreciation.*tax\s*provision"]),
        ("year_end_corrections", [r"errors.*ledger", r"correction.*voucher"]),
        ("monthly_closing", [r"month.*clos"]),
        ("cost_analysis_projects", [r"cost.*analy[sz]", r"expense.*accounts.*increase"]),
        ("project_lifecycle", [r"lifecycle.*project", r"project.*lifecycle", r"full.*project.*lifecycle"]),
        ("overdue_invoice_reminder", [r"overdue.*invoice", r"reminder.*fee"]),
        ("bank_reconciliation", [r"bank.*reconcil", r"reconcil.*bank", r"bank\s*statement"]),
        ("register_supplier_invoice", [r"supplier.*invoice", r"invoice.*supplier"]),
        ("fixed_price_project", [r"fixed\s*price"]),
        ("reverse_payment", [r"reverse.*payment"]),
        ("credit_note", [r"credit\s*note"]),
        ("employee_onboarding", [r"employment.*contract", r"offer\s*letter", r"new\s*employee.*start"]),
        ("travel_expense", [r"travel.*expense", r"expense.*receipt", r"receipt.*expense"]),
        ("register_hours", [r"\d+\s*hours", r"register.*hours", r"timesheet"]),
        ("run_salary", [r"run.*salary", r"process.*payroll", r"salary.*run"]),
        ("custom_dimension", [r"dimension"]),
        ("forex_payment", [r"exchange\s*rate", r"agio"]),
        ("register_payment", [r"payment"]),
        ("create_invoice", [r"invoice"]),
        ("create_departments", [r"department"]),
        ("create_employee", [r"employee"]),
        ("create_project", [r"project"]),
        ("create_customer", [r"create.*customer", r"new.*customer", r"register.*customer"]),
        ("create_supplier", [r"supplier"]),
        ("create_product", [r"product"]),
        ("create_order", [r"order"]),
    ],
}

# ---------------------------------------------------------------------------
# Universal fallback patterns (all languages, ordered most-specific-first)
# ---------------------------------------------------------------------------

UNIVERSAL_PATTERNS: list[tuple[str, list[str]]] = [
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
        r"erros.*razão", r"fehler.*hauptbuch", r"feil.*hovedbok", r"feil.*hovudbok",
        r"correction.*voucher", r"korrigering",
    ]),
    ("monthly_closing", [
        r"cierre.*mensual", r"month.*clos", r"månedsslutt", r"monatsabschluss",
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
        r"ciclo.*vida.*pro[jy]", r"lifecycle.*project", r"project.*lifecycle", r"prosjektlivssyklus",
        r"lebenszyklus.*projekt", r"cycle.*vie.*projet",
        r"orçamento.*registe.*horas", r"budget.*register.*hours",
        r"full.*project.*lifecycle", r"complete.*project.*lifecycle",
        r"ciclo.*completo.*pro[jy]", r"vollst[äa]ndig.*projekt",
        r"prosjektsyklus", r"heile.*prosjekt",
        r"budsjett.*registrer.*timar", r"budget.*hours.*supplier.*invoice",
    ]),
    ("overdue_invoice_reminder", [
        r"[üu]berf[äa]llig.*rechnung", r"overdue.*invoice", r"factura.*vencid[ao]",
        r"fatura.*vencid[ao]", r"purregebyr", r"mahnung", r"reminder.*fee",
        r"cargo.*recordatorio", r"taxa.*lembrete", r"frais.*rappel",
        r"mahngeb[üu]hr", r"forfalt.*faktura", r"forfallen.*faktura",
    ]),
    ("bank_reconciliation", [
        r"bank.*avstemming", r"bank.*reconcil", r"reconcil.*bank",
        r"concilia.*banc", r"rapproch.*bancaire",
        r"relev[ée]\s*bancaire", r"kontoauszug", r"bankutskrift",
        r"bank\s*statement", r"extracto\s*banc", r"extrato\s*banc",
    ]),
    ("register_supplier_invoice", [
        r"leverandør.*faktura(?!@)", r"faktura(?!@).*leverandør",
        r"leverandor.*faktura(?!@)", r"faktura(?!@).*leverandor",
        r"supplier.*invoice", r"invoice.*supplier",
        r"proveedor.*factura(?!@)", r"factura(?!@).*proveedor",
        r"fornecedor.*fatura(?!@)", r"fatura(?!@).*fornecedor",
        r"lieferant.*rechnung", r"rechnung.*lieferant",
        r"fournisseur.*facture(?!@)", r"facture(?!@).*fournisseur",
    ]),
    ("fixed_price_project", [
        r"fast\s*pris", r"fixed\s*price", r"precio\s*fijo", r"preço\s*fixo",
        r"festpreis", r"prix\s*fixe",
    ]),
    ("reverse_payment", [
        r"reverser.*betaling", r"reverse.*payment", r"revertir.*pago",
        r"reverter.*pagamento", r"stornierung", r"annul.*paiement",
        r"stornieren.*zahlung", r"zahlung.*stornieren",
        r"zur[üu]ckgebucht", r"tilbakeført.*betaling", r"betaling.*tilbakeført",
        r"cancel.*pago", r"cancel.*pagamento", r"anular.*pagamento",
        r"retourné", r"devuelt[oa]", r"devolvid[oa]",
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
        r"new\s*employee.*start", r"ny\s*ansatt", r"neuer\s*mitarbeiter.*start",
        r"nouvel\s*employ.*début", r"nuevo\s*empleado.*empez", r"novo\s*funcion.*início",
    ]),
    ("travel_expense", [
        r"reise", r"travel.*expense", r"gastos.*viaje", r"despesas.*viagem",
        r"reisekosten", r"frais.*voyage", r"reiserekning", r"reiseregning",
        r"despesa.*recibo", r"recibo.*despesa", r"expense.*receipt",
        r"receipt.*expense", r"kvittering", r"beleg.*ausgabe",
        r"d[eé]pense.*re[cç]u", r"re[cç]u.*d[eé]pense",
        r"note\s*de\s*frais",
    ]),
    ("register_hours", [
        r"\btimer\b", r"\btimar\b", r"\d+\s*hours", r"register.*hours", r"erfassen.*stunden",
        r"\d+\s*horas", r"regist[re].*horas", r"\d+\s*stunden",
        r"\d+\s*heures", r"timeføring", r"timesheet",
    ]),
    ("run_salary", [
        r"kj[øo]r.*l[øo]nn", r"l[øo]nnskj[øo]ring", r"l[øo]nnsutbetaling",
        r"run.*salary", r"ejecute.*nómina", r"execute.*folha",
        r"gehalt.*auszahlen", r"gehaltsabrechnung", r"ex[eé]cut\w*.*paie",
        r"\bpaie\b",
        r"processar.*folha", r"process.*payroll", r"salary.*run",
        r"process.*sal[aá]rio",
    ]),
    ("custom_dimension", [
        r"dimensjon", r"dimension", r"dimensión", r"dimensão",
    ]),
    ("forex_payment", [
        r"valuta", r"exchange\s*rate", r"tipo\s*de\s*cambio", r"taxa\s*de\s*câmbio",
        r"wechselkurs", r"taux\s*de\s*change", r"agio", r"disagio",
        r"kurs.*eur", r"eur.*kurs", r"rate.*eur", r"eur.*rate",
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
        r"ansatt", r"tilsett", r"employee", r"empleado", r"funcionário", r"mitarbeiter", r"employé",
    ]),
    ("create_customer", [
        r"opprett.*kunde", r"create.*customer", r"cree?.*cliente",
        r"crie.*cliente", r"erstellen.*kunde", r"créez.*client",
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


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def classify_task(prompt: str, language: str | None = None) -> str | None:
    """Classify a task prompt into a known task type.

    If language is provided, checks language-specific patterns first
    for more precise matching, then falls back to universal patterns.

    Args:
        prompt: The task prompt text.
        language: Detected language name (e.g. 'Norwegian', 'French').
                  If None, skips language-specific patterns.

    Returns the task_type string or None if no pattern matches.
    """
    prompt_lower = prompt.lower()

    # Phase 1: Language-specific patterns (if language provided)
    if language:
        # Map language names to LANG_PATTERNS keys
        lang_key_map = {
            "norwegian": "no", "norsk": "no", "bokmål": "no", "bokmal": "no",
            "nynorsk": "nn",
            "german": "de", "deutsch": "de",
            "french": "fr", "français": "fr", "francais": "fr",
            "spanish": "es", "español": "es", "espanol": "es",
            "portuguese": "pt", "português": "pt", "portugues": "pt",
            "english": "en",
        }
        lang_key = lang_key_map.get(language.lower().strip(), None)
        if lang_key:
            lang_patterns = LANG_PATTERNS.get(lang_key, [])
            for task_type, patterns in lang_patterns:
                for pattern in patterns:
                    if re.search(pattern, prompt_lower):
                        return task_type

    # Phase 2: Universal fallback (all languages)
    for task_type, patterns in UNIVERSAL_PATTERNS:
        for pattern in patterns:
            if re.search(pattern, prompt_lower):
                return task_type

    return None
