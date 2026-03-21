"""Tests for keyword-based task classifier."""
import pytest
from execution_plans._classifier import classify_task


class TestClassifier:
    """Test classification across task types and languages."""

    @pytest.mark.parametrize("prompt,expected", [
        # create_customer
        ("Create the customer Brightstone Ltd with organization number 853284882", "create_customer"),
        ("Opprett kunden Fjordkraft AS med organisasjonsnummer 843216285", "create_customer"),
        ("Crie o cliente Montanha Lda com número de organização 986713344", "create_customer"),

        # create_employee
        ("Create an employee named Per Olsen with email per.olsen@firma.no", "create_employee"),
        ("Tenemos un nuevo empleado llamado Diego Rodriguez", "create_employee"),
        ("Temos um novo funcionário chamado Rita Almeida", "create_employee"),

        # create_supplier
        ("Registrer leverandøren Nordhav AS med organisasjonsnummer 923456910", "create_supplier"),
        ("Enregistrez le fournisseur Lumiere SARL avec le numéro d'organisation 879852439", "create_supplier"),

        # create_departments (batch)
        ("Opprett tre avdelingar i Tripletex: Logistikk, Innkjop og IT", "create_departments"),
        ("Erstellen Sie drei Abteilungen in Tripletex", "create_departments"),

        # create_invoice
        ("Opprett og send en faktura til kunden Lysgard AS", "create_invoice"),
        ("Crea una factura para el cliente Dorada SL", "create_invoice"),
        ("Crie uma fatura para o cliente Oceano Lda", "create_invoice"),

        # register_supplier_invoice — must match BEFORE create_supplier
        ("Wir haben die Rechnung vom Lieferanten Nordlicht GmbH", "register_supplier_invoice"),
        ("Enregistrez la facture du fournisseur Lumiere SARL", "register_supplier_invoice"),

        # register_payment
        ("Le paiement de Riviere SARL pour la facture Design web", "register_payment"),
        ("O pagamento de Cascata Lda referente a fatura", "register_payment"),

        # run_salary
        ("Kjør lønn for Erik Nilsen for denne måneden", "run_salary"),
        ("Processe o salário de Sofia Sousa para este mês", "run_salary"),

        # fixed_price_project — must match BEFORE create_project
        ("Establezca un precio fijo de 152400 NOK en el proyecto", "fixed_price_project"),
        ("Set a fixed price of 100000 NOK on the project", "fixed_price_project"),

        # create_project
        ("Crie o projeto Migracao Montanha vinculado ao cliente", "create_project"),
        ("Create the project Upgrade Windmill linked to the customer", "create_project"),

        # create_order
        ("Créez une commande pour le client Colline SARL", "create_order"),

        # custom_dimension
        ("Create a custom accounting dimension Produktlinje", "custom_dimension"),

        # travel_expense
        ("Registrer ei reiserekning for Svein Berg", "travel_expense"),
        ("Erfassen Sie eine Reisekostenabrechnung", "travel_expense"),

        # credit_note
        ("Issue a full credit note that reverses the entire invoice", "credit_note"),

        # reverse_payment
        ("Reverse the payment for invoice 12345", "reverse_payment"),

        # register_hours
        ("Register 8 hours for the project", "register_hours"),

        # bank_reconciliation
        ("Rapprochez le relevé bancaire CSV ci-joint", "bank_reconciliation"),

        # unknown
        ("Do something completely unrelated", None),
    ])
    def test_classify(self, prompt, expected):
        assert classify_task(prompt) == expected

    def test_specific_before_general(self):
        """register_supplier_invoice must match before create_supplier."""
        prompt = "Register the supplier invoice from Nordlicht GmbH"
        assert classify_task(prompt) == "register_supplier_invoice"

    def test_fixed_price_before_project(self):
        """fixed_price_project must match before create_project."""
        prompt = "Set a fixed price on the project Infrastructure Upgrade"
        assert classify_task(prompt) == "fixed_price_project"
