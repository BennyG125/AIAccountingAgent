"""Task definitions for integration tests.

7 categories × 7 languages = 49 parametrized test cases.
Each task has prompts per language, verification steps, and a tier.
"""

import time

_run_id = str(int(time.time()))[-6:]


def unique(name: str) -> str:
    """Append a run-scoped suffix so each test run creates distinct entities."""
    return f"{name}_{_run_id}"


TASKS = {
    # ------------------------------------------------------------------
    # Tier 1 — single-step entity creation
    # ------------------------------------------------------------------
    "create_department": {
        "tier": 1,
        "prompts": {
            "nb": f"Opprett en avdeling med navn '{unique('Salg')}' og avdelingsnummer '200'",
            "en": f"Create a department named '{unique('Salg')}' with department number '200'",
            "es": f"Crea un departamento llamado '{unique('Salg')}' con número de departamento '200'",
            "pt": f"Crie um departamento chamado '{unique('Salg')}' com número de departamento '200'",
            "nn": f"Opprett ei avdeling med namn '{unique('Salg')}' og avdelingsnummer '200'",
            "de": f"Erstellen Sie eine Abteilung namens '{unique('Salg')}' mit Abteilungsnummer '200'",
            "fr": f"Créez un département nommé '{unique('Salg')}' avec le numéro de département '200'",
        },
        "verify": [
            {
                "entity_type": "department",
                "search_params": {"name": unique("Salg")},
                "expected_fields": {
                    "name": unique("Salg"),
                    "departmentNumber": "200",
                },
            }
        ],
    },

    "create_employee": {
        "tier": 1,
        "prompts": {
            "nb": (
                f"Opprett en ansatt med fornavn 'Kari', etternavn '{unique('Nordmann')}', "
                f"e-post kari_{_run_id}@example.com og brukertype STANDARD"
            ),
            "en": (
                f"Create an employee with first name 'Kari', last name '{unique('Nordmann')}', "
                f"email kari_{_run_id}@example.com and user type STANDARD"
            ),
            "es": (
                f"Crea un empleado con nombre 'Kari', apellido '{unique('Nordmann')}', "
                f"correo kari_{_run_id}@example.com y tipo de usuario STANDARD"
            ),
            "pt": (
                f"Crie um funcionário com nome 'Kari', sobrenome '{unique('Nordmann')}', "
                f"e-mail kari_{_run_id}@example.com e tipo de usuário STANDARD"
            ),
            "nn": (
                f"Opprett ein tilsett med fornamn 'Kari', etternamn '{unique('Nordmann')}', "
                f"e-post kari_{_run_id}@example.com og brukartype STANDARD"
            ),
            "de": (
                f"Erstellen Sie einen Mitarbeiter mit Vorname 'Kari', Nachname '{unique('Nordmann')}', "
                f"E-Mail kari_{_run_id}@example.com und Benutzertyp STANDARD"
            ),
            "fr": (
                f"Créez un employé avec le prénom 'Kari', le nom '{unique('Nordmann')}', "
                f"l'e-mail kari_{_run_id}@example.com et le type d'utilisateur STANDARD"
            ),
        },
        "verify": [
            {
                "entity_type": "employee",
                "search_params": {"lastName": unique("Nordmann")},
                "expected_fields": {
                    "firstName": "Kari",
                    "lastName": unique("Nordmann"),
                    "email": f"kari_{_run_id}@example.com",
                },
            }
        ],
    },

    "create_customer": {
        "tier": 1,
        "prompts": {
            "nb": (
                f"Opprett en kunde med navn '{unique('Bergen Consulting AS')}' "
                f"og e-post post_{_run_id}@bergenconsulting.no"
            ),
            "en": (
                f"Create a customer named '{unique('Bergen Consulting AS')}' "
                f"with email post_{_run_id}@bergenconsulting.no"
            ),
            "es": (
                f"Crea un cliente llamado '{unique('Bergen Consulting AS')}' "
                f"con correo post_{_run_id}@bergenconsulting.no"
            ),
            "pt": (
                f"Crie um cliente chamado '{unique('Bergen Consulting AS')}' "
                f"com e-mail post_{_run_id}@bergenconsulting.no"
            ),
            "nn": (
                f"Opprett ein kunde med namn '{unique('Bergen Consulting AS')}' "
                f"og e-post post_{_run_id}@bergenconsulting.no"
            ),
            "de": (
                f"Erstellen Sie einen Kunden namens '{unique('Bergen Consulting AS')}' "
                f"mit E-Mail post_{_run_id}@bergenconsulting.no"
            ),
            "fr": (
                f"Créez un client nommé '{unique('Bergen Consulting AS')}' "
                f"avec l'e-mail post_{_run_id}@bergenconsulting.no"
            ),
        },
        "verify": [
            {
                "entity_type": "customer",
                "search_params": {"name": unique("Bergen Consulting AS")},
                "expected_fields": {
                    "name": unique("Bergen Consulting AS"),
                    "email": f"post_{_run_id}@bergenconsulting.no",
                },
            }
        ],
    },

    "create_product": {
        "tier": 1,
        "prompts": {
            "nb": (
                f"Opprett et produkt med navn '{unique('Konsulenttjeneste')}', "
                f"pris 1500 NOK ekskl. mva og MVA-sats 25%"
            ),
            "en": (
                f"Create a product named '{unique('Konsulenttjeneste')}' "
                f"at 1500 NOK ex VAT with 25% VAT rate"
            ),
            "es": (
                f"Crea un producto llamado '{unique('Konsulenttjeneste')}' "
                f"a 1500 NOK sin IVA con tasa de IVA del 25%"
            ),
            "pt": (
                f"Crie um produto chamado '{unique('Konsulenttjeneste')}' "
                f"a 1500 NOK sem IVA com taxa de IVA de 25%"
            ),
            "nn": (
                f"Opprett eit produkt med namn '{unique('Konsulenttjeneste')}', "
                f"pris 1500 NOK ekskl. mva og MVA-sats 25%"
            ),
            "de": (
                f"Erstellen Sie ein Produkt namens '{unique('Konsulenttjeneste')}' "
                f"zu 1500 NOK exkl. MwSt. mit 25% MwSt.-Satz"
            ),
            "fr": (
                f"Créez un produit nommé '{unique('Konsulenttjeneste')}' "
                f"à 1500 NOK HT avec un taux de TVA de 25%"
            ),
        },
        "verify": [
            {
                "entity_type": "product",
                "search_params": {"name": unique("Konsulenttjeneste")},
                "expected_fields": {
                    "name": unique("Konsulenttjeneste"),
                    "priceExcludingVatCurrency": 1500,
                },
            }
        ],
    },

    # ------------------------------------------------------------------
    # Tier 2 — multi-step flows
    # ------------------------------------------------------------------
    "create_invoice_flow": {
        "tier": 2,
        "prompts": {
            "nb": (
                f"Opprett en kunde '{unique('Fjord Tech AS')}', "
                f"opprett et produkt '{unique('Rådgivning')}' til 2000 kr ekskl. mva, "
                f"opprett en ordre for kunden med produktet, "
                f"fakturer ordren, og registrer betaling for fakturaen."
            ),
            "en": (
                f"Create a customer '{unique('Fjord Tech AS')}', "
                f"create a product '{unique('Rådgivning')}' at 2000 NOK ex VAT, "
                f"create an order for the customer with that product, "
                f"invoice the order, and register payment for the invoice."
            ),
            "es": (
                f"Crea un cliente '{unique('Fjord Tech AS')}', "
                f"crea un producto '{unique('Rådgivning')}' a 2000 NOK sin IVA, "
                f"crea un pedido para el cliente con ese producto, "
                f"factura el pedido y registra el pago de la factura."
            ),
            "pt": (
                f"Crie um cliente '{unique('Fjord Tech AS')}', "
                f"crie um produto '{unique('Rådgivning')}' a 2000 NOK sem IVA, "
                f"crie um pedido para o cliente com esse produto, "
                f"fature o pedido e registe o pagamento da fatura."
            ),
            "nn": (
                f"Opprett ein kunde '{unique('Fjord Tech AS')}', "
                f"opprett eit produkt '{unique('Rådgivning')}' til 2000 kr ekskl. mva, "
                f"opprett ein ordre for kunden med produktet, "
                f"fakturer ordren, og registrer betaling for fakturaen."
            ),
            "de": (
                f"Erstellen Sie einen Kunden '{unique('Fjord Tech AS')}', "
                f"erstellen Sie ein Produkt '{unique('Rådgivning')}' zu 2000 NOK exkl. MwSt., "
                f"erstellen Sie einen Auftrag für den Kunden mit diesem Produkt, "
                f"stellen Sie die Rechnung für den Auftrag aus und registrieren Sie die Zahlung."
            ),
            "fr": (
                f"Créez un client '{unique('Fjord Tech AS')}', "
                f"créez un produit '{unique('Rådgivning')}' à 2000 NOK HT, "
                f"créez une commande pour le client avec ce produit, "
                f"facturez la commande et enregistrez le paiement de la facture."
            ),
        },
        "verify": [
            {
                "entity_type": "customer",
                "search_params": {"name": unique("Fjord Tech AS")},
                "expected_fields": {"name": unique("Fjord Tech AS")},
            },
            {
                "entity_type": "product",
                "search_params": {"name": unique("Rådgivning")},
                "expected_fields": {
                    "name": unique("Rådgivning"),
                    "priceExcludingVatCurrency": 2000,
                },
            },
        ],
    },

    "create_travel_expense": {
        "tier": 2,
        "prompts": {
            "nb": (
                f"Opprett en reiseregning med beskrivelse '{unique('Kundemøte Oslo')}' "
                f"for en ansatt, med en kostnad på 500 NOK."
            ),
            "en": (
                f"Create a travel expense with description '{unique('Kundemøte Oslo')}' "
                f"for an employee, with a cost of 500 NOK."
            ),
            "es": (
                f"Crea un gasto de viaje con descripción '{unique('Kundemøte Oslo')}' "
                f"para un empleado, con un coste de 500 NOK."
            ),
            "pt": (
                f"Crie uma despesa de viagem com descrição '{unique('Kundemøte Oslo')}' "
                f"para um funcionário, com um custo de 500 NOK."
            ),
            "nn": (
                f"Opprett ein reiserekning med beskriving '{unique('Kundemøte Oslo')}' "
                f"for ein tilsett, med ein kostnad på 500 NOK."
            ),
            "de": (
                f"Erstellen Sie eine Reisekostenabrechnung mit Beschreibung '{unique('Kundemøte Oslo')}' "
                f"für einen Mitarbeiter, mit Kosten von 500 NOK."
            ),
            "fr": (
                f"Créez une note de frais de voyage avec la description '{unique('Kundemøte Oslo')}' "
                f"pour un employé, avec un coût de 500 NOK."
            ),
        },
        "verify": [
            {
                "entity_type": "travel_expense",
                "search_params": {},
                "expected_fields": {"title": unique("Kundemøte Oslo")},
            }
        ],
    },

    "create_project": {
        "tier": 2,
        "prompts": {
            "nb": (
                f"Opprett et prosjekt med navn '{unique('Nettside Redesign')}' "
                f"og sett en prosjektleder."
            ),
            "en": (
                f"Create a project named '{unique('Nettside Redesign')}' "
                f"and assign a project manager."
            ),
            "es": (
                f"Crea un proyecto llamado '{unique('Nettside Redesign')}' "
                f"y asigna un jefe de proyecto."
            ),
            "pt": (
                f"Crie um projeto chamado '{unique('Nettside Redesign')}' "
                f"e atribua um gerente de projeto."
            ),
            "nn": (
                f"Opprett eit prosjekt med namn '{unique('Nettside Redesign')}' "
                f"og set ein prosjektleiar."
            ),
            "de": (
                f"Erstellen Sie ein Projekt namens '{unique('Nettside Redesign')}' "
                f"und weisen Sie einen Projektleiter zu."
            ),
            "fr": (
                f"Créez un projet nommé '{unique('Nettside Redesign')}' "
                f"et attribuez un chef de projet."
            ),
        },
        "verify": [
            {
                "entity_type": "project",
                "search_params": {"name": unique("Nettside Redesign")},
                "expected_fields": {"name": unique("Nettside Redesign")},
            }
        ],
    },
}
