import io
from typing import BinaryIO, List

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, A6
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    FrameBreak,
    HRFlowable,
    PageBreak,
    PageTemplate,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .pdf_data_structures import PDFInvoiceData


class PDFA6Generator:
    """
    Service for generating A6-formatted invoices on A4 pages.

    This service takes a list of individual invoices and arranges them
    in a 2x2 grid on A4 pages, with each invoice scaled to A6 format.
    Includes crop marks for easy cutting.
    """

    def __init__(self):
        self.styles = getSampleStyleSheet()
        # A6 dimensions for scaling
        self.a6_width = A6[0]  # 105 mm
        self.a6_height = A6[1]  # 148 mm

        # A4 layout: 2x2 grid with calculated margins for centering
        self.a4_width = A4[0]
        self.a4_height = A4[1]

        # Calculate margins to center the 2x2 grid on A4
        total_content_width = 2 * self.a6_width
        total_content_height = 2 * self.a6_height

        margin_x = (self.a4_width - total_content_width) / 2
        margin_y = (self.a4_height - total_content_height) / 2

        self.page_margin_x = margin_x
        self.page_margin_y = margin_y
        self.crop_mark_length = 5 * mm
        self.crop_mark_offset = 2 * mm

        # Calculate positions for 2x2 grid
        self.invoice_width = self.a6_width
        self.invoice_height = self.a6_height

        # Grid positions (x, y from bottom-left) - corrected for proper centering
        self.positions = [
            # Bottom row
            (self.page_margin_x, self.page_margin_y),  # Bottom-left
            (
                self.page_margin_x + self.invoice_width,
                self.page_margin_y,
            ),  # Bottom-right
            # Top row
            (self.page_margin_x, self.page_margin_y + self.invoice_height),  # Top-left
            (
                self.page_margin_x + self.invoice_width,
                self.page_margin_y + self.invoice_height,
            ),  # Top-right
        ]

        # Define elegant color palette (smaller scale)
        self.colors = {
            "primary": colors.Color(0.2, 0.2, 0.2),  # Dark charcoal
            "secondary": colors.Color(0.4, 0.4, 0.4),  # Medium gray
            "accent": colors.Color(0.85, 0.85, 0.85),  # Light gray
            "background": colors.Color(0.97, 0.97, 0.97),  # Very light gray
            "success": colors.Color(0.2, 0.4, 0.2),  # Dark green
            "text": colors.Color(0.15, 0.15, 0.15),  # Near black
            "crop_mark": colors.Color(0.0, 0.0, 0.0),  # Black for crop marks
        }
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Setup custom paragraph styles optimized for A6 format."""
        # A6 Document title style - smaller
        self.styles.add(
            ParagraphStyle(
                name="A6DocumentTitle",
                parent=self.styles["Heading1"],
                fontSize=14,
                fontName="Helvetica-Bold",
                textColor=self.colors["primary"],
                spaceAfter=4 * mm,
                spaceBefore=0,
                alignment=TA_LEFT,
                leftIndent=0,
            )
        )

        # A6 Section header style - smaller
        self.styles.add(
            ParagraphStyle(
                name="A6SectionHeader",
                parent=self.styles["Heading2"],
                fontSize=8,
                fontName="Helvetica-Bold",
                textColor=self.colors["primary"],
                spaceAfter=2 * mm,
                spaceBefore=3 * mm,
                alignment=TA_LEFT,
            )
        )

        # A6 Address style - compact
        self.styles.add(
            ParagraphStyle(
                name="A6Address",
                parent=self.styles["Normal"],
                fontSize=7,
                fontName="Helvetica",
                leading=9,
                textColor=self.colors["text"],
                leftIndent=0,
                spaceAfter=0,
            )
        )

        # A6 Info text style - compact
        self.styles.add(
            ParagraphStyle(
                name="A6InfoText",
                parent=self.styles["Normal"],
                fontSize=7,
                fontName="Helvetica",
                textColor=self.colors["secondary"],
                leading=9,
                spaceAfter=1 * mm,
            )
        )

        # A6 Right aligned style for amounts
        self.styles.add(
            ParagraphStyle(
                name="A6RightAlign",
                parent=self.styles["Normal"],
                alignment=TA_RIGHT,
                fontSize=7,
                fontName="Helvetica",
            )
        )

        # A6 Total amount style - emphasized but smaller
        self.styles.add(
            ParagraphStyle(
                name="A6TotalAmount",
                parent=self.styles["Normal"],
                fontSize=8,
                fontName="Helvetica-Bold",
                textColor=self.colors["primary"],
                alignment=TA_RIGHT,
            )
        )

    def _create_single_invoice_story(self, data: PDFInvoiceData) -> List:
        """Create story elements for a single A6 invoice."""
        story = []

        # Document header - compact
        story.append(
            Paragraph(f"Rechnung {data.invoice_number}", self.styles["A6DocumentTitle"])
        )

        # Subtle separator line - thinner
        story.append(
            HRFlowable(
                width="100%",
                thickness=0.25,
                lineCap="round",
                color=self.colors["accent"],
                spaceAfter=3 * mm,
            )
        )

        # Compact sender and customer information
        address_data = [
            [
                Paragraph(
                    f"<b>Rechnungssteller</b><br/><br/>{data.sender_name}<br/>{data.sender_address}",
                    self.styles["A6Address"],
                ),
                Paragraph(
                    f"<b>Rechnungsempfänger</b><br/><br/>{data.customer_name}{('<br/>' + data.customer_address) if data.customer_address else ''}",
                    self.styles["A6Address"],
                ),
            ]
        ]

        address_table = Table(
            address_data, colWidths=[4 * cm, 4 * cm], rowHeights=[18 * mm]
        )
        address_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm),
                ]
            )
        )
        story.append(address_table)

        # Compact invoice metadata
        story.append(Paragraph("<b>Details</b>", self.styles["A6SectionHeader"]))

        meta_data = [["Datum:", data.date.strftime("%d.%m.%Y")]]
        if data.sender_tax_number:
            meta_data.append(["Steuer-Nr.:", data.sender_tax_number])

        meta_table = Table(meta_data, colWidths=[2 * cm, 4 * cm])
        meta_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 7),
                    ("TEXTCOLOR", (0, 0), (0, -1), self.colors["secondary"]),
                    ("TEXTCOLOR", (1, 0), (1, -1), self.colors["text"]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 1 * mm),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 1 * mm),
                ]
            )
        )
        story.append(meta_table)
        story.append(Spacer(1, 3 * mm))

        # Compact items table
        if data.items:
            story.append(Paragraph("<b>Leistungen</b>", self.styles["A6SectionHeader"]))

            items_data = [["Beschreibung", "Menge", "Preis"]]

            for item in data.items:
                total = item["quantity"] * item["price"]
                items_data.append(
                    [
                        (
                            item["description"][:25] + "..."
                            if len(item["description"]) > 25
                            else item["description"]
                        ),
                        str(item["quantity"]),
                        f"{total:.2f} €",
                    ]
                )

            items_table = Table(items_data, colWidths=[5 * cm, 1 * cm, 2 * cm])
            items_table.setStyle(
                TableStyle(
                    [
                        # Header styling
                        ("BACKGROUND", (0, 0), (-1, 0), self.colors["primary"]),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 6),
                        ("TOPPADDING", (0, 0), (-1, 0), 2 * mm),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 2 * mm),
                        # Data rows styling
                        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                        ("FONTSIZE", (0, 1), (-1, -1), 6),
                        ("TEXTCOLOR", (0, 1), (-1, -1), self.colors["text"]),
                        # Alignment
                        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                        ("ALIGN", (0, 0), (0, -1), "LEFT"),
                        # Padding
                        ("LEFTPADDING", (0, 0), (-1, -1), 1 * mm),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 1 * mm),
                        ("TOPPADDING", (0, 1), (-1, -1), 1 * mm),
                        ("BOTTOMPADDING", (0, 1), (-1, -1), 1 * mm),
                        # Borders
                        ("LINEBELOW", (0, 0), (-1, 0), 0.5, self.colors["primary"]),
                        ("LINEBELOW", (0, 1), (-1, -2), 0.1, self.colors["accent"]),
                    ]
                )
            )
            story.append(items_table)
            story.append(Spacer(1, 3 * mm))

        # Compact totals section
        story.append(Paragraph("<b>Summe</b>", self.styles["A6SectionHeader"]))

        if data.total_tax > 0:
            totals_data = [
                ["Netto:", f"{data.total_net:.2f} €"],
                [f"MwSt ({data.tax_rate*100:.0f}%):", f"{data.total_tax:.2f} €"],
                ["Gesamt:", f"{data.total_gross:.2f} €"],
            ]
        else:
            totals_data = [
                ["Gesamt:", f"{data.total_gross:.2f} €"],
                ["§19 UStG", "Keine MwSt."],
            ]

        totals_table = Table(totals_data, colWidths=[4 * cm, 3 * cm])
        totals_table.setStyle(
            TableStyle(
                [
                    # Regular rows
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 7),
                    ("TEXTCOLOR", (0, 0), (0, -1), self.colors["secondary"]),
                    ("TEXTCOLOR", (1, 0), (1, -1), self.colors["text"]),
                    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                    # Total row emphasis (last row or second-to-last if tax)
                    (
                        "FONTNAME",
                        (0, -2 if data.total_tax > 0 else -1),
                        (-1, -2 if data.total_tax > 0 else -1),
                        "Helvetica-Bold",
                    ),
                    (
                        "FONTSIZE",
                        (0, -2 if data.total_tax > 0 else -1),
                        (-1, -2 if data.total_tax > 0 else -1),
                        8,
                    ),
                    (
                        "TEXTCOLOR",
                        (0, -2 if data.total_tax > 0 else -1),
                        (-1, -2 if data.total_tax > 0 else -1),
                        self.colors["primary"],
                    ),
                    (
                        "LINEABOVE",
                        (0, -2 if data.total_tax > 0 else -1),
                        (-1, -2 if data.total_tax > 0 else -1),
                        0.5,
                        self.colors["primary"],
                    ),
                    # General padding
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 1 * mm),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 1 * mm),
                ]
            )
        )
        story.append(totals_table)

        # Compact bank data
        if data.sender_bank_data:
            story.append(Spacer(1, 3 * mm))
            story.append(Paragraph("<b>Zahlung</b>", self.styles["A6SectionHeader"]))
            # Truncate bank data for A6 format
            bank_data = (
                data.sender_bank_data[:100] + "..."
                if len(data.sender_bank_data) > 100
                else data.sender_bank_data
            )
            story.append(Paragraph(bank_data, self.styles["A6InfoText"]))

        return story

    def _draw_crop_marks(self, canvas, doc):
        """Draw crop marks for cutting guidelines."""
        canvas.saveState()
        canvas.setStrokeColor(self.colors["crop_mark"])
        canvas.setLineWidth(0.5)

        # Vertical cut line (between left and right columns)
        x_center = self.page_margin_x + self.invoice_width
        y_positions = [
            self.page_margin_y,  # Bottom
            self.page_margin_y + self.invoice_height,  # Middle
            self.page_margin_y + 2 * self.invoice_height,  # Top
        ]

        for y_pos in y_positions:
            canvas.line(
                x_center - self.crop_mark_length / 2,
                y_pos,
                x_center + self.crop_mark_length / 2,
                y_pos,
            )

        # Horizontal cut line (between top and bottom rows)
        y_center = self.page_margin_y + self.invoice_height
        x_positions = [
            self.page_margin_x,  # Left
            self.page_margin_x + self.invoice_width,  # Middle
            self.page_margin_x + 2 * self.invoice_width,  # Right
        ]

        for x_pos in x_positions:
            canvas.line(
                x_pos,
                y_center - self.crop_mark_length / 2,
                x_pos,
                y_center + self.crop_mark_length / 2,
            )

        canvas.restoreState()

    def generate_a6_invoices_pdf(
        self, invoice_data_list: List[PDFInvoiceData]
    ) -> bytes:
        """
        Generate PDF with multiple A6 invoices arranged on A4 pages.

        Args:
            invoice_data_list: List of PDFInvoiceData objects

        Returns:
            PDF content as bytes
        """
        buffer = io.BytesIO()
        doc = BaseDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=0,
            leftMargin=0,
            topMargin=0,
            bottomMargin=0,
        )

        # Create frames for 2x2 layout
        frames = []
        for i, (x, y) in enumerate(self.positions):
            frame = Frame(
                x,
                y,
                self.invoice_width,
                self.invoice_height,
                leftPadding=3 * mm,
                rightPadding=3 * mm,
                topPadding=3 * mm,
                bottomPadding=3 * mm,
                id=f"invoice_{i}",
            )
            frames.append(frame)

        # Create page template with crop marks
        page_template = PageTemplate(
            id="a6_layout", frames=frames, onPage=self._draw_crop_marks
        )
        doc.addPageTemplates([page_template])

        # Build story with all invoices
        story = []

        for i, invoice_data in enumerate(invoice_data_list):
            # Add invoice story
            invoice_story = self._create_single_invoice_story(invoice_data)
            story.extend(invoice_story)

            # Add FrameBreak to move to next frame, except for the last invoice
            if i < len(invoice_data_list) - 1:
                # Every 4th invoice starts a new page
                if (i + 1) % 4 == 0:
                    story.append(PageBreak())  # New page after 4 invoices
                else:
                    story.append(FrameBreak())  # Move to next frame on same page

        # Fill remaining positions on last page with empty content if needed
        remaining_positions = (4 - (len(invoice_data_list) % 4)) % 4
        for _ in range(remaining_positions):
            story.append(Spacer(1, 1))  # Minimal empty content
            if (
                _ < remaining_positions - 1
            ):  # Don't add FrameBreak after the last position
                story.append(FrameBreak())

        # Build PDF
        doc.build(story)

        # Get PDF content
        pdf_content = buffer.getvalue()
        buffer.close()

        return pdf_content
