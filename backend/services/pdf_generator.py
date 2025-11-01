import io
from typing import BinaryIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .pdf_data_structures import PDFInvoiceData, PDFSummaryInvoiceData


class PDFGenerator:
    """
    Service for generating PDF documents from prepared data.

    This service takes structured data objects and creates properly formatted
    PDF documents using ReportLab with professional, minimalist design.
    """

    def __init__(self):
        self.styles = getSampleStyleSheet()
        # Define elegant color palette
        self.colors = {
            "primary": colors.Color(0.2, 0.2, 0.2),  # Dark charcoal
            "secondary": colors.Color(0.4, 0.4, 0.4),  # Medium gray
            "accent": colors.Color(0.85, 0.85, 0.85),  # Light gray
            "background": colors.Color(0.97, 0.97, 0.97),  # Very light gray
            "success": colors.Color(0.2, 0.4, 0.2),  # Dark green
            "text": colors.Color(0.15, 0.15, 0.15),  # Near black
        }
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Setup custom paragraph styles for professional PDF generation."""
        # Main document title style
        self.styles.add(
            ParagraphStyle(
                name="DocumentTitle",
                parent=self.styles["Heading1"],
                fontSize=24,
                fontName="Helvetica-Bold",
                textColor=self.colors["primary"],
                spaceAfter=8 * mm,
                spaceBefore=0,
                alignment=TA_LEFT,
                leftIndent=0,
            )
        )

        # Section header style
        self.styles.add(
            ParagraphStyle(
                name="SectionHeader",
                parent=self.styles["Heading2"],
                fontSize=12,
                fontName="Helvetica-Bold",
                textColor=self.colors["primary"],
                spaceAfter=4 * mm,
                spaceBefore=6 * mm,
                alignment=TA_LEFT,
            )
        )

        # Address style - elegant and clean
        self.styles.add(
            ParagraphStyle(
                name="Address",
                parent=self.styles["Normal"],
                fontSize=10,
                fontName="Helvetica",
                leading=14,
                textColor=self.colors["text"],
                leftIndent=0,
                spaceAfter=0,
            )
        )

        # Professional info style
        self.styles.add(
            ParagraphStyle(
                name="InfoText",
                parent=self.styles["Normal"],
                fontSize=10,
                fontName="Helvetica",
                textColor=self.colors["secondary"],
                leading=14,
                spaceAfter=2 * mm,
            )
        )

        # Right aligned style for amounts
        self.styles.add(
            ParagraphStyle(
                name="RightAlign",
                parent=self.styles["Normal"],
                alignment=TA_RIGHT,
                fontSize=10,
                fontName="Helvetica",
            )
        )

        # Total amount style - emphasized
        self.styles.add(
            ParagraphStyle(
                name="TotalAmount",
                parent=self.styles["Normal"],
                fontSize=12,
                fontName="Helvetica-Bold",
                textColor=self.colors["primary"],
                alignment=TA_RIGHT,
            )
        )

    def generate_invoice_pdf(self, data: PDFInvoiceData) -> bytes:
        """
        Generate PDF for a single invoice with professional design.

        Args:
            data: PDFInvoiceData object with all necessary information

        Returns:
            PDF content as bytes
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=25 * mm,
            leftMargin=25 * mm,
            topMargin=20 * mm,
            bottomMargin=25 * mm,
        )

        # Build PDF content
        story = []

        # Document header with elegant styling
        story.append(
            Paragraph(f"Rechnung {data.invoice_number}", self.styles["DocumentTitle"])
        )

        # Subtle separator line
        story.append(
            HRFlowable(
                width="100%",
                thickness=0.5,
                lineCap="round",
                color=self.colors["accent"],
                spaceAfter=8 * mm,
            )
        )

        # Sender and customer information with professional layout
        address_data = [
            [
                Paragraph(
                    f"<b>Rechnungssteller</b><br/><br/>{data.sender_name}<br/>{data.sender_address}",
                    self.styles["Address"],
                ),
                Paragraph(
                    f"<b>Rechnungsempfänger</b><br/><br/>{data.customer_name}{('<br/>' + data.customer_address) if data.customer_address else ''}",
                    self.styles["Address"],
                ),
            ]
        ]

        address_table = Table(
            address_data, colWidths=[9 * cm, 9 * cm], rowHeights=[35 * mm]
        )
        address_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8 * mm),
                ]
            )
        )
        story.append(address_table)

        # Invoice metadata section
        story.append(Paragraph("<b>Rechnungsdetails</b>", self.styles["SectionHeader"]))

        meta_data = [["Rechnungsdatum:", data.date.strftime("%d.%m.%Y")]]

        if data.sender_tax_number:
            meta_data.append(["Steuernummer:", data.sender_tax_number])

        meta_table = Table(meta_data, colWidths=[4 * cm, 8 * cm])
        meta_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("TEXTCOLOR", (0, 0), (0, -1), self.colors["secondary"]),
                    ("TEXTCOLOR", (1, 0), (1, -1), self.colors["text"]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 2 * mm),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
                ]
            )
        )
        story.append(meta_table)
        story.append(Spacer(1, 8 * mm))

        # Items table with modern styling
        if data.items:
            story.append(Paragraph("<b>Leistungen</b>", self.styles["SectionHeader"]))

            items_data = [["Beschreibung", "Menge", "Einzelpreis", "Gesamtpreis"]]

            for item in data.items:
                total = item["quantity"] * item["price"]
                items_data.append(
                    [
                        item["description"],
                        str(item["quantity"]),
                        f"{item['price']:.2f} €",
                        f"{total:.2f} €",
                    ]
                )

            items_table = Table(
                items_data, colWidths=[7.5 * cm, 2 * cm, 3 * cm, 3.5 * cm]
            )
            items_table.setStyle(
                TableStyle(
                    [
                        # Header styling
                        ("BACKGROUND", (0, 0), (-1, 0), self.colors["primary"]),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 10),
                        ("TOPPADDING", (0, 0), (-1, 0), 4 * mm),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 4 * mm),
                        # Data rows styling
                        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                        ("FONTSIZE", (0, 1), (-1, -1), 9),
                        ("TEXTCOLOR", (0, 1), (-1, -1), self.colors["text"]),
                        # Alignment
                        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                        ("ALIGN", (0, 0), (0, -1), "LEFT"),
                        # Padding
                        ("LEFTPADDING", (0, 0), (-1, -1), 3 * mm),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
                        ("TOPPADDING", (0, 1), (-1, -1), 3 * mm),
                        ("BOTTOMPADDING", (0, 1), (-1, -1), 3 * mm),
                        # Borders - subtle and modern
                        ("LINEBELOW", (0, 0), (-1, 0), 1, self.colors["primary"]),
                        ("LINEBELOW", (0, 1), (-1, -2), 0.25, self.colors["accent"]),
                    ]
                )
            )
            story.append(items_table)
            story.append(Spacer(1, 8 * mm))

        # Professional totals section
        story.append(Paragraph("<b>Rechnungsbetrag</b>", self.styles["SectionHeader"]))

        if data.total_tax > 0:
            # Show net, tax, and gross with elegant styling
            totals_data = [
                ["Nettobetrag:", f"{data.total_net:.2f} €"],
                [
                    f"Umsatzsteuer ({data.tax_rate*100:.0f}%):",
                    f"{data.total_tax:.2f} €",
                ],
                ["", ""],  # Spacer row
                ["Gesamtbetrag:", f"{data.total_gross:.2f} €"],
            ]
        else:
            # §19 UStG case - no tax
            totals_data = [
                ["Gesamtbetrag:", f"{data.total_gross:.2f} €"],
                ["", ""],  # Spacer row
                ["Steuerbefreiung:", "Gemäß §19 UStG wird keine Umsatzsteuer erhoben."],
            ]

        totals_table = Table(totals_data, colWidths=[10 * cm, 6 * cm])
        totals_table.setStyle(
            TableStyle(
                [
                    # Regular rows
                    ("FONTNAME", (0, 0), (-1, -2), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -2), 10),
                    ("TEXTCOLOR", (0, 0), (0, -2), self.colors["secondary"]),
                    ("TEXTCOLOR", (1, 0), (1, -2), self.colors["text"]),
                    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                    # Total row emphasis
                    ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, -1), (-1, -1), 12),
                    ("TEXTCOLOR", (0, -1), (-1, -1), self.colors["primary"]),
                    ("LINEABOVE", (0, -1), (-1, -1), 1.5, self.colors["primary"]),
                    ("TOPPADDING", (0, -1), (-1, -1), 4 * mm),
                    # General padding
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -2), 2 * mm),
                    ("BOTTOMPADDING", (0, 0), (-1, -2), 2 * mm),
                ]
            )
        )
        story.append(totals_table)

        # Bank data with elegant styling
        if data.sender_bank_data:
            story.append(Spacer(1, 10 * mm))
            story.append(
                Paragraph("<b>Zahlungsinformationen</b>", self.styles["SectionHeader"])
            )
            story.append(Paragraph(data.sender_bank_data, self.styles["InfoText"]))

        # Build PDF
        doc.build(story)

        # Get PDF content
        pdf_content = buffer.getvalue()
        buffer.close()

        return pdf_content

    def generate_summary_invoice_pdf(self, data: PDFSummaryInvoiceData) -> bytes:
        """
        Generate PDF for a summary invoice with professional design.

        Args:
            data: PDFSummaryInvoiceData object with all necessary information

        Returns:
            PDF content as bytes
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=25 * mm,
            leftMargin=25 * mm,
            topMargin=20 * mm,
            bottomMargin=25 * mm,
        )

        # Build PDF content
        story = []

        # Document header with elegant styling
        story.append(
            Paragraph(f"Sammelrechnung {data.range_text}", self.styles["DocumentTitle"])
        )

        # Subtle separator line
        story.append(
            HRFlowable(
                width="100%",
                thickness=0.5,
                lineCap="round",
                color=self.colors["accent"],
                spaceAfter=8 * mm,
            )
        )

        # Sender and customer information with professional layout
        address_data = [
            [
                Paragraph(
                    f"<b>Rechnungssteller</b><br/><br/>{data.sender_name}<br/>{data.sender_address}",
                    self.styles["Address"],
                ),
                Paragraph(
                    f"<b>Rechnungsempfänger</b><br/><br/>{data.customer_name}{('<br/>' + data.customer_address) if data.customer_address else ''}",
                    self.styles["Address"],
                ),
            ]
        ]

        address_table = Table(
            address_data, colWidths=[9 * cm, 9 * cm], rowHeights=[35 * mm]
        )
        address_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8 * mm),
                ]
            )
        )
        story.append(address_table)

        # Invoice metadata section
        story.append(Paragraph("<b>Rechnungsdetails</b>", self.styles["SectionHeader"]))

        meta_data = [["Rechnungsdatum:", data.date.strftime("%d.%m.%Y")]]

        if data.sender_tax_number:
            meta_data.append(["Steuernummer:", data.sender_tax_number])

        meta_table = Table(meta_data, colWidths=[4 * cm, 8 * cm])
        meta_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("TEXTCOLOR", (0, 0), (0, -1), self.colors["secondary"]),
                    ("TEXTCOLOR", (1, 0), (1, -1), self.colors["text"]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 2 * mm),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
                ]
            )
        )
        story.append(meta_table)
        story.append(Spacer(1, 8 * mm))

        # Included invoices with professional styling
        if data.invoice_details:
            story.append(
                Paragraph("<b>Enthaltene Rechnungen</b>", self.styles["SectionHeader"])
            )

            # Create elegant list of invoices with customer names
            invoice_list_data = []
            for i, detail in enumerate(data.invoice_details, 1):
                invoice_list_data.append([
                    f"{i}.", 
                    f"Rechnung {detail['number']} - {detail['customer_name']}"
                ])

            invoice_table = Table(invoice_list_data, colWidths=[1 * cm, 15 * cm])
            invoice_table.setStyle(
                TableStyle(
                    [
                        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                        ("FONTSIZE", (0, 0), (-1, -1), 10),
                        ("TEXTCOLOR", (0, 0), (0, -1), self.colors["secondary"]),
                        ("TEXTCOLOR", (1, 0), (1, -1), self.colors["text"]),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                        ("TOPPADDING", (0, 0), (-1, -1), 1 * mm),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 1 * mm),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ]
                )
            )
            story.append(invoice_table)
            story.append(Spacer(1, 8 * mm))

        # Professional totals section
        story.append(Paragraph("<b>Rechnungsbetrag</b>", self.styles["SectionHeader"]))

        if data.total_tax > 0:
            # Show net, tax, and gross with elegant styling
            totals_data = [
                ["Nettobetrag:", f"{data.total_net:.2f} €"],
                ["Umsatzsteuer:", f"{data.total_tax:.2f} €"],
                ["", ""],  # Spacer row
                ["Gesamtbetrag:", f"{data.total_gross:.2f} €"],
            ]
        else:
            # §19 UStG case - no tax
            totals_data = [
                ["Gesamtbetrag:", f"{data.total_gross:.2f} €"],
                ["", ""],  # Spacer row
                ["Steuerbefreiung:", "Gemäß §19 UStG wird keine Umsatzsteuer erhoben."],
            ]

        totals_table = Table(totals_data, colWidths=[10 * cm, 6 * cm])
        totals_table.setStyle(
            TableStyle(
                [
                    # Regular rows
                    ("FONTNAME", (0, 0), (-1, -2), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -2), 10),
                    ("TEXTCOLOR", (0, 0), (0, -2), self.colors["secondary"]),
                    ("TEXTCOLOR", (1, 0), (1, -2), self.colors["text"]),
                    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                    # Total row emphasis
                    ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, -1), (-1, -1), 12),
                    ("TEXTCOLOR", (0, -1), (-1, -1), self.colors["primary"]),
                    ("LINEABOVE", (0, -1), (-1, -1), 1.5, self.colors["primary"]),
                    ("TOPPADDING", (0, -1), (-1, -1), 4 * mm),
                    # General padding
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -2), 2 * mm),
                    ("BOTTOMPADDING", (0, 0), (-1, -2), 2 * mm),
                ]
            )
        )
        story.append(totals_table)

        # Bank data with elegant styling
        if data.sender_bank_data:
            story.append(Spacer(1, 10 * mm))
            story.append(
                Paragraph("<b>Zahlungsinformationen</b>", self.styles["SectionHeader"])
            )
            story.append(Paragraph(data.sender_bank_data, self.styles["InfoText"]))

        # Build PDF
        doc.build(story)

        # Get PDF content
        pdf_content = buffer.getvalue()
        buffer.close()

        return pdf_content
