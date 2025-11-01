import io
from typing import List

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, A6
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.pdfgen import canvas
from reportlab.platypus import (HRFlowable, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

from .pdf_data_structures import PDFInvoiceData


class PDFA6GeneratorSimple:
    """
    Simplified A6 PDF generator using canvas drawing.

    This creates a proper 2x2 layout by drawing each invoice manually
    on the canvas at specific positions.
    """

    def __init__(self):
        self.styles = getSampleStyleSheet()

        # A6 dimensions
        self.a6_width = A6[0]  # 105 mm = ~298 points
        self.a6_height = A6[1]  # 148 mm = ~420 points

        # A4 layout settings - calculate margins for centered layout
        a4_width = A4[0]  # ~595 points
        a4_height = A4[1]  # ~842 points

        # Calculate margins to center the 2x2 grid on A4
        total_content_width = 2 * self.a6_width
        total_content_height = 2 * self.a6_height

        margin_x = (a4_width - total_content_width) / 2
        margin_y = (a4_height - total_content_height) / 2

        self.page_margin_x = margin_x
        self.page_margin_y = margin_y
        self.crop_mark_length = 5 * mm
        self.crop_mark_offset = 2 * mm

        # Grid positions for 2x2 layout (x, y from bottom-left)
        # Corrected positions with proper margins
        self.positions = [
            # Bottom row (y-coordinate is lower)
            (self.page_margin_x, self.page_margin_y),  # Bottom-left
            (self.page_margin_x + self.a6_width, self.page_margin_y),  # Bottom-right
            # Top row (y-coordinate is higher)
            (self.page_margin_x, self.page_margin_y + self.a6_height),  # Top-left
            (
                self.page_margin_x + self.a6_width,
                self.page_margin_y + self.a6_height,
            ),  # Top-right
        ]

        # Colors
        self.colors = {
            "primary": colors.Color(0.2, 0.2, 0.2),
            "secondary": colors.Color(0.4, 0.4, 0.4),
            "accent": colors.Color(0.85, 0.85, 0.85),
            "text": colors.Color(0.15, 0.15, 0.15),
            "crop_mark": colors.Color(0.0, 0.0, 0.0),
        }

        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Setup compact styles for A6 format."""
        # A6 Title
        self.styles.add(
            ParagraphStyle(
                name="A6Title",
                parent=self.styles["Heading1"],
                fontSize=12,
                fontName="Helvetica-Bold",
                textColor=self.colors["primary"],
                spaceAfter=2 * mm,
                alignment=TA_LEFT,
            )
        )

        # A6 Section
        self.styles.add(
            ParagraphStyle(
                name="A6Section",
                parent=self.styles["Heading2"],
                fontSize=8,
                fontName="Helvetica-Bold",
                textColor=self.colors["primary"],
                spaceAfter=1 * mm,
                spaceBefore=2 * mm,
            )
        )

        # A6 Text
        self.styles.add(
            ParagraphStyle(
                name="A6Text",
                parent=self.styles["Normal"],
                fontSize=7,
                fontName="Helvetica",
                leading=8,
                textColor=self.colors["text"],
            )
        )

        # A6 Small text
        self.styles.add(
            ParagraphStyle(
                name="A6Small",
                parent=self.styles["Normal"],
                fontSize=6,
                fontName="Helvetica",
                leading=7,
                textColor=self.colors["secondary"],
            )
        )

    def _draw_single_invoice(self, canvas_obj, x, y, data: PDFInvoiceData):
        """Draw a single invoice at the specified position."""
        # Create a mini-document for this invoice
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=(self.a6_width, self.a6_height),
            rightMargin=3 * mm,
            leftMargin=3 * mm,
            topMargin=3 * mm,
            bottomMargin=3 * mm,
        )

        story = []

        # Title
        story.append(
            Paragraph(f"Rechnung {data.invoice_number}", self.styles["A6Title"])
        )

        # Separator
        story.append(
            HRFlowable(
                width="100%",
                thickness=0.25,
                color=self.colors["accent"],
                spaceAfter=2 * mm,
            )
        )

        # Addresses in compact table
        address_data = [
            [f"Von: {data.sender_name}", f"An: {data.customer_name}"],
        ]
        address_table = Table(address_data, colWidths=[4 * cm, 4 * cm])
        address_table.setStyle(
            TableStyle(
                [
                    ("FONTSIZE", (0, 0), (-1, -1), 6),
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )
        story.append(address_table)
        story.append(Spacer(1, 2 * mm))

        # Date
        story.append(
            Paragraph(
                f"Datum: {data.date.strftime('%d.%m.%Y')}", self.styles["A6Small"]
            )
        )
        story.append(Spacer(1, 2 * mm))

        # Items (compact)
        if data.items:
            story.append(Paragraph("Leistungen:", self.styles["A6Section"]))
            for item in data.items[:3]:  # Limit to 3 items for space
                desc = (
                    item["description"][:20] + "..."
                    if len(item["description"]) > 20
                    else item["description"]
                )
                total = item["quantity"] * item["price"]
                story.append(
                    Paragraph(
                        f"{item['quantity']}x {desc}: {total:.2f} €",
                        self.styles["A6Small"],
                    )
                )
            story.append(Spacer(1, 2 * mm))

        # Total
        story.append(Paragraph("Summe:", self.styles["A6Section"]))
        if data.total_tax > 0:
            story.append(
                Paragraph(f"Netto: {data.total_net:.2f} €", self.styles["A6Small"])
            )
            story.append(
                Paragraph(f"MwSt: {data.total_tax:.2f} €", self.styles["A6Small"])
            )
        story.append(
            Paragraph(f"Gesamt: {data.total_gross:.2f} €", self.styles["A6Text"])
        )

        # Build the mini-document
        doc.build(story)

        # Get the PDF data and overlay it on the main canvas
        mini_pdf_data = buffer.getvalue()
        buffer.close()

        # Save canvas state
        canvas_obj.saveState()

        # Draw a border for this invoice area (for debugging)
        canvas_obj.setStrokeColor(self.colors["accent"])
        canvas_obj.setLineWidth(0.5)
        canvas_obj.rect(x, y, self.a6_width, self.a6_height)

        # For now, we'll draw a simplified version directly on canvas
        canvas_obj.setFont("Helvetica-Bold", 10)
        canvas_obj.drawString(
            x + 5 * mm, y + self.a6_height - 10 * mm, f"Rechnung {data.invoice_number}"
        )

        canvas_obj.setFont("Helvetica", 7)
        canvas_obj.drawString(
            x + 5 * mm, y + self.a6_height - 20 * mm, f"An: {data.customer_name}"
        )
        canvas_obj.drawString(
            x + 5 * mm,
            y + self.a6_height - 30 * mm,
            f"Datum: {data.date.strftime('%d.%m.%Y')}",
        )
        canvas_obj.drawString(
            x + 5 * mm,
            y + self.a6_height - 40 * mm,
            f"Gesamt: {data.total_gross:.2f} €",
        )

        # Restore canvas state
        canvas_obj.restoreState()

    def _draw_crop_marks(self, canvas_obj):
        """Draw crop marks for cutting."""
        canvas_obj.saveState()
        canvas_obj.setStrokeColor(self.colors["crop_mark"])
        canvas_obj.setLineWidth(0.5)

        # Vertical cut line (between left and right columns)
        x_center = self.page_margin_x + self.a6_width
        y_positions = [
            self.page_margin_y,  # Bottom
            self.page_margin_y + self.a6_height,  # Middle
            self.page_margin_y + 2 * self.a6_height,  # Top
        ]

        for y_pos in y_positions:
            canvas_obj.line(
                x_center - self.crop_mark_length / 2,
                y_pos,
                x_center + self.crop_mark_length / 2,
                y_pos,
            )

        # Horizontal cut line (between top and bottom rows)
        y_center = self.page_margin_y + self.a6_height
        x_positions = [
            self.page_margin_x,  # Left
            self.page_margin_x + self.a6_width,  # Middle
            self.page_margin_x + 2 * self.a6_width,  # Right
        ]

        for x_pos in x_positions:
            canvas_obj.line(
                x_pos,
                y_center - self.crop_mark_length / 2,
                x_pos,
                y_center + self.crop_mark_length / 2,
            )

        canvas_obj.restoreState()

    def generate_a6_invoices_pdf(
        self, invoice_data_list: List[PDFInvoiceData]
    ) -> bytes:
        """Generate A6 layout PDF using direct canvas drawing."""
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)

        invoice_count = len(invoice_data_list)
        invoices_per_page = 4
        pages_needed = (invoice_count + invoices_per_page - 1) // invoices_per_page

        for page in range(pages_needed):
            if page > 0:
                c.showPage()  # Start new page

            # Draw crop marks
            self._draw_crop_marks(c)

            # Draw invoices for this page (up to 4)
            start_idx = page * invoices_per_page
            end_idx = min(start_idx + invoices_per_page, invoice_count)

            for i in range(start_idx, end_idx):
                position_idx = i % invoices_per_page
                x, y = self.positions[position_idx]
                self._draw_single_invoice(c, x, y, invoice_data_list[i])

        c.save()
        pdf_content = buffer.getvalue()
        buffer.close()

        return pdf_content
