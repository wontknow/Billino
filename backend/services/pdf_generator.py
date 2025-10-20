import io
from typing import BinaryIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER

from .pdf_data_structures import PDFInvoiceData, PDFSummaryInvoiceData


class PDFGenerator:
    """
    Service for generating PDF documents from prepared data.
    
    This service takes structured data objects and creates properly formatted
    PDF documents using ReportLab.
    """
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles for PDF generation."""
        # Header style
        self.styles.add(ParagraphStyle(
            name='Header',
            parent=self.styles['Heading1'],
            fontSize=16,
            spaceAfter=20,
            alignment=TA_CENTER
        ))
        
        # Address style
        self.styles.add(ParagraphStyle(
            name='Address',
            parent=self.styles['Normal'],
            fontSize=10,
            leading=12
        ))
        
        # Right aligned style for amounts
        self.styles.add(ParagraphStyle(
            name='RightAlign',
            parent=self.styles['Normal'],
            alignment=TA_RIGHT
        ))
    
    def generate_invoice_pdf(self, data: PDFInvoiceData) -> bytes:
        """
        Generate PDF for a single invoice.
        
        Args:
            data: PDFInvoiceData object with all necessary information
            
        Returns:
            PDF content as bytes
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        
        # Build PDF content
        story = []
        
        # Header
        story.append(Paragraph(f"Rechnung {data.invoice_number}", self.styles['Header']))
        story.append(Spacer(1, 20))
        
        # Sender and customer information table
        address_data = [
            [
                Paragraph(f"<b>Rechnungssteller:</b><br/>{data.sender_name}<br/>{data.sender_address}", self.styles['Address']),
                Paragraph(f"<b>Rechnungsempfänger:</b><br/>{data.customer_address}", self.styles['Address'])
            ]
        ]
        
        address_table = Table(address_data, colWidths=[8*cm, 8*cm])
        address_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(address_table)
        story.append(Spacer(1, 20))
        
        # Invoice details
        story.append(Paragraph(f"<b>Rechnungsdatum:</b> {data.date.strftime('%d.%m.%Y')}", self.styles['Normal']))
        
        # Add tax number if available
        if data.sender_tax_number:
            story.append(Paragraph(f"<b>Steuernummer:</b> {data.sender_tax_number}", self.styles['Normal']))
        
        story.append(Spacer(1, 20))
        
        # Items table if available
        if data.items:
            items_data = [["Beschreibung", "Menge", "Preis", "Gesamt"]]
            
            for item in data.items:
                total = item["quantity"] * item["price"]
                items_data.append([
                    item["description"],
                    str(item["quantity"]),
                    f"{item['price']:.2f} €",
                    f"{total:.2f} €"
                ])
            
            items_table = Table(items_data, colWidths=[8*cm, 2*cm, 3*cm, 3*cm])
            items_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(items_table)
            story.append(Spacer(1, 20))
        
        # Totals
        if data.total_tax > 0:
            # Show net, tax, and gross
            totals_data = [
                ["Nettobetrag:", f"{data.total_net:.2f} €"],
                [f"Umsatzsteuer ({data.tax_rate*100:.0f}%):", f"{data.total_tax:.2f} €"],
                ["Gesamtbetrag:", f"{data.total_gross:.2f} €"]
            ]
        else:
            # §19 UStG case - no tax
            totals_data = [
                ["Gesamtbetrag:", f"{data.total_gross:.2f} €"],
                ["", "Gemäß §19 UStG wird keine Umsatzsteuer erhoben."]
            ]
        
        totals_table = Table(totals_data, colWidths=[10*cm, 6*cm])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, -1), (1, -1), 'Helvetica-Bold'),
            ('LINEABOVE', (0, -1), (1, -1), 1, colors.black),
        ]))
        story.append(totals_table)
        
        # Bank data if available
        if data.sender_bank_data:
            story.append(Spacer(1, 30))
            story.append(Paragraph("<b>Bankverbindung:</b>", self.styles['Normal']))
            story.append(Paragraph(data.sender_bank_data, self.styles['Normal']))
        
        # Build PDF
        doc.build(story)
        
        # Get PDF content
        pdf_content = buffer.getvalue()
        buffer.close()
        
        return pdf_content
    
    def generate_summary_invoice_pdf(self, data: PDFSummaryInvoiceData) -> bytes:
        """
        Generate PDF for a summary invoice.
        
        Args:
            data: PDFSummaryInvoiceData object with all necessary information
            
        Returns:
            PDF content as bytes
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        
        # Build PDF content
        story = []
        
        # Header
        story.append(Paragraph(f"Sammelrechnung {data.range_text}", self.styles['Header']))
        story.append(Spacer(1, 20))
        
        # Sender and customer information table
        address_data = [
            [
                Paragraph(f"<b>Rechnungssteller:</b><br/>{data.sender_name}<br/>{data.sender_address}", self.styles['Address']),
                Paragraph(f"<b>Rechnungsempfänger:</b><br/>{data.customer_address}", self.styles['Address'])
            ]
        ]
        
        address_table = Table(address_data, colWidths=[8*cm, 8*cm])
        address_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(address_table)
        story.append(Spacer(1, 20))
        
        # Invoice details
        story.append(Paragraph(f"<b>Rechnungsdatum:</b> {data.date.strftime('%d.%m.%Y')}", self.styles['Normal']))
        
        # Add tax number if available
        if data.sender_tax_number:
            story.append(Paragraph(f"<b>Steuernummer:</b> {data.sender_tax_number}", self.styles['Normal']))
        
        story.append(Spacer(1, 20))
        
        # Included invoices
        if data.invoice_numbers:
            story.append(Paragraph("<b>Enthaltene Rechnungen:</b>", self.styles['Normal']))
            for number in data.invoice_numbers:
                story.append(Paragraph(f"• Rechnung {number}", self.styles['Normal']))
            story.append(Spacer(1, 20))
        
        # Totals
        if data.total_tax > 0:
            # Show net, tax, and gross
            totals_data = [
                ["Nettobetrag:", f"{data.total_net:.2f} €"],
                ["Umsatzsteuer:", f"{data.total_tax:.2f} €"],
                ["Gesamtbetrag:", f"{data.total_gross:.2f} €"]
            ]
        else:
            # §19 UStG case - no tax
            totals_data = [
                ["Gesamtbetrag:", f"{data.total_gross:.2f} €"],
                ["", "Gemäß §19 UStG wird keine Umsatzsteuer erhoben."]
            ]
        
        totals_table = Table(totals_data, colWidths=[10*cm, 6*cm])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, -1), (1, -1), 'Helvetica-Bold'),
            ('LINEABOVE', (0, -1), (1, -1), 1, colors.black),
        ]))
        story.append(totals_table)
        
        # Bank data if available
        if data.sender_bank_data:
            story.append(Spacer(1, 30))
            story.append(Paragraph("<b>Bankverbindung:</b>", self.styles['Normal']))
            story.append(Paragraph(data.sender_bank_data, self.styles['Normal']))
        
        # Build PDF
        doc.build(story)
        
        # Get PDF content
        pdf_content = buffer.getvalue()
        buffer.close()
        
        return pdf_content