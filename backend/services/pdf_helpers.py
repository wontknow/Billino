"""Helper functions for PDF generation to reduce code duplication."""

from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, Table, TableStyle


def create_address_table(
    sender_name: str,
    sender_address: str,
    customer_name: str,
    customer_address: str,
    style: ParagraphStyle,
    col_widths: list,
    row_heights: list,
    bottom_padding: float = 8 * mm,
) -> Table:
    """
    Create a formatted address table with sender and customer information.

    This helper function reduces code duplication across PDF generators by
    centralizing the address formatting logic.

    Args:
        sender_name: Name of the invoice sender
        sender_address: Address of the invoice sender
        customer_name: Name of the invoice recipient
        customer_address: Address of the invoice recipient (optional)
        style: ParagraphStyle to use for formatting the addresses
        col_widths: List of column widths for the table
        row_heights: List of row heights for the table
        bottom_padding: Bottom padding for table cells (default: 8mm)

    Returns:
        Table: A ReportLab Table object with formatted address information
    """
    address_data = [
        [
            Paragraph(
                f"<b>Rechnungssteller</b><br/><br/>{sender_name}<br/>{sender_address}",
                style,
            ),
            Paragraph(
                f"<b>Rechnungsempfänger</b><br/><br/>{customer_name}{('<br/>' + customer_address) if customer_address else ''}",
                style,
            ),
        ]
    ]

    address_table = Table(address_data, colWidths=col_widths, rowHeights=row_heights)
    address_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), bottom_padding),
            ]
        )
    )

    return address_table
