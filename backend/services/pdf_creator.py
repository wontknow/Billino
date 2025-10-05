from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from models import Customer, InvoiceItemRead, InvoiceRead, Profile


def create_invoice_pdf_a4() -> bytes:
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # --- Beispiel-Daten ---
    customer = Customer(
        id=1, name="Max Mustermann", address="Musterstraße 1", city="12345 Musterstadt"
    )
    profile = Profile(
        id=1,
        name="Salon Sunshine",
        address="Hauptstraße 12",
        city="12345 Berlin",
        bank_data="DE12 3456 7890 1234 5678 90",

        tax_number="12/345/67890",
    )
    invoice = InvoiceRead(
        id=1,
        number="2024|001",
        date="2024-01-01",
        customer_id=customer.id,
        profile_id=profile.id,
        include_tax=False,
        total_amount=24.00,
        invoice_items=[
            InvoiceItemRead(
                id=1,
                invoice_id=1,
                quantity=1,
                description="Haarschnitt Damen",
                price=24.00,
            )
        ],
    )

    # --- Header ---
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(width / 2, height - 40, f"Rechnung Nr.: {invoice.number}")

    # --- Linien unter Header ---
    c.line(30, height - 50, width - 30, height - 50)

    # --- Zwei Spalten (Absender links / Infos rechts) ---
    c.setFont("Helvetica", 11)
    left_x = 30
    right_x = width - 200
    y_start = height - 90

    # Linke Spalte: Profil
    c.drawString(left_x, y_start, profile.name)
    c.drawString(left_x, y_start - 15, profile.address)
    c.drawString(left_x, y_start - 30, profile.city)
    c.drawString(left_x, y_start - 45, f"IBAN: {profile.bank_data}")

    # Rechte Spalte: Rechnungsinfo
    c.drawString(right_x, y_start, f"Datum: {invoice.date}")
    c.drawString(right_x, y_start - 15, f"Steuernummer: {profile.tax_number}")

    

    # --- Empfänger mittig ---
    c.setFont("Helvetica-Bold", 12)
    c.drawString(30, y_start - 80, "Rechnung an:")
    c.setFont("Helvetica", 11)
    c.drawString(30, y_start - 95, customer.name)
    c.drawString(30, y_start - 110, customer.address)
    c.drawString(30, y_start - 125, customer.city)

    # --- Tabelle Kopf ---
    table_y = y_start - 160
    c.setFont("Helvetica-Bold", 11)
    c.drawString(30, table_y, "Menge")
    c.drawString(100, table_y, "Bezeichnung")
    c.drawString(width - 120, table_y, "Betrag (€)")
    c.line(30, table_y - 5, width - 30, table_y - 5)

    # --- Tabelle Inhalte ---
    c.setFont("Helvetica", 11)
    current_y = table_y - 25
    for item in invoice.invoice_items:
        c.drawString(30, current_y, str(item.quantity))
        c.drawString(100, current_y, item.description)
        c.drawRightString(width - 30, current_y, f"{item.price:.2f}")
        current_y -= 20

    # --- Summenbereich ---
    c.line(30, current_y - 10, width - 30, current_y - 10)
    current_y -= 30

    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(width - 120, current_y, "Gesamtbetrag netto:")
    c.drawRightString(width - 30, current_y, f"{sum(item.quantity * item.price for item in invoice.invoice_items):.2f} €")
    current_y -= 20

    c.setFont("Helvetica", 11)
    c.drawRightString(width - 120, current_y, "zzgl. MwSt (19%):")
    if invoice.include_tax:
        c.drawRightString(width - 30, current_y, f"{sum(item.quantity * item.price for item in invoice.invoice_items) * 0.19:.2f} €")
    current_y -= 20

    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(width - 120, current_y, "Gesamtbetrag inkl. MwSt:")
    c.drawRightString(width - 30, current_y, f"{invoice.total_amount:.2f} €")

    # --- Footer ---
    # c.setFont("Helvetica", 9)
    # c.drawCentredString(width / 2, 40, "Vielen Dank für Ihren Besuch!")
    # c.drawCentredString(
    #     width / 2, 25, "Bitte überweisen Sie den Betrag innerhalb von 14 Tagen."
    # )

    # Footer: gesetzlicher Hinweis (§19 UStG)
    if not invoice.include_tax:
        c.setFont("Helvetica-Oblique", 9)
        c.drawCentredString(width / 2, 25, "Gemäß § 19 UStG wird keine Umsatzsteuer berechnet.")


    # --- Fertigstellen ---
    c.showPage()
    c.save()

    pdf = buffer.getvalue()
    buffer.close()

    with open("output_invoice.pdf", "wb") as f:
        f.write(pdf)

    return pdf


if __name__ == "__main__":
    pdf_bytes = create_invoice_pdf_a4()
    print(f"✅ PDF erstellt: {len(pdf_bytes)} Bytes")
