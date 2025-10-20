from typing import Optional, List
from sqlmodel import Session, select
from datetime import datetime, date

from models import Invoice, Profile, Customer, SummaryInvoice, SummaryInvoiceLink, InvoiceRead, InvoiceItemRead, SummaryInvoiceRead
from .pdf_data_structures import PDFInvoiceData, PDFSummaryInvoiceData


class PDFDataService:
    """
    Service for preparing PDF data from database entities.
    
    This service retrieves and transforms database entities (Invoice, SummaryInvoice)
    into structured data objects ready for PDF generation.
    """
    
    def __init__(self, session: Session):
        self.session = session
    
    def get_invoice_pdf_data_from_model(self, invoice: InvoiceRead, profile: Profile, customer: Customer) -> PDFInvoiceData:
        """
        Create PDF data directly from model objects.
        
        Args:
            invoice: InvoiceRead model object
            profile: Profile model object  
            customer: Customer model object
            
        Returns:
            PDFInvoiceData object ready for PDF generation
        """
        # Convert string date to date object
        if isinstance(invoice.date, str):
            # Handle both date formats: "YYYY-MM-DD" and ISO format with time
            if "T" in invoice.date:
                invoice_date = datetime.fromisoformat(invoice.date.replace('Z', '+00:00')).date()
            else:
                invoice_date = datetime.strptime(invoice.date, "%Y-%m-%d").date()
        else:
            invoice_date = invoice.date

        # Prepare sender address
        sender_address = self._format_address(profile.address, profile.city)
        
        # Prepare customer address
        customer_address = self._format_address(customer.address, customer.city, customer.name)
        
        # Calculate amounts based on invoice settings
        total_net, total_tax, total_gross = self._calculate_amounts(
            invoice.total_amount,
            invoice.tax_rate or profile.default_tax_rate,
            invoice.is_gross_amount,
            invoice.include_tax if invoice.include_tax is not None else profile.include_tax
        )
        
        # Prepare items data
        items_data = []
        for item in invoice.invoice_items:
            items_data.append({
                "description": item.description,
                "quantity": item.quantity,
                "price": item.price
            })
        
        return PDFInvoiceData(
            invoice_number=invoice.number,
            date=invoice_date,
            sender_name=profile.name,
            sender_address=sender_address,
            customer_name=customer.name,
            customer_address=customer_address,
            total_net=total_net,
            total_tax=total_tax,
            total_gross=total_gross,
            tax_rate=invoice.tax_rate or profile.default_tax_rate,
            items=items_data,
            sender_bank_data=profile.bank_data,
            sender_tax_number=profile.tax_number
        )
    
    def get_summary_invoice_pdf_data_from_model(
        self, 
        summary_invoice: SummaryInvoiceRead, 
        profile: Profile, 
        customer: Customer,
        invoice_numbers: List[str]
    ) -> PDFSummaryInvoiceData:
        """
        Create PDF data directly from model objects.
        
        Args:
            summary_invoice: SummaryInvoiceRead model object
            profile: Profile model object
            customer: Customer model object
            invoice_numbers: List of invoice numbers included in summary
            
        Returns:
            PDFSummaryInvoiceData object ready for PDF generation
        """
        # Convert string date to date object
        if isinstance(summary_invoice.date, str):
            # Handle both date formats: "YYYY-MM-DD" and ISO format with time
            if "T" in summary_invoice.date:
                summary_date = datetime.fromisoformat(summary_invoice.date.replace('Z', '+00:00')).date()
            else:
                summary_date = datetime.strptime(summary_invoice.date, "%Y-%m-%d").date()
        else:
            summary_date = summary_invoice.date

        # Prepare addresses
        sender_address = self._format_address(profile.address, profile.city)
        customer_address = self._format_address(customer.address, customer.city, customer.name)
        
        return PDFSummaryInvoiceData(
            range_text=summary_invoice.range_text,
            date=summary_date,
            sender_name=profile.name,
            sender_address=sender_address,
            customer_name=customer.name,
            customer_address=customer_address,
            total_net=summary_invoice.total_net,
            total_tax=summary_invoice.total_tax,
            total_gross=summary_invoice.total_gross,
            invoice_numbers=invoice_numbers,
            sender_bank_data=profile.bank_data,
            sender_tax_number=profile.tax_number
        )
    
    def get_invoice_pdf_data(self, invoice_id: int) -> PDFInvoiceData:
        """
        Retrieve and prepare invoice data for PDF generation.
        
        Args:
            invoice_id: ID of the invoice to prepare
            
        Returns:
            PDFInvoiceData object with all necessary information
            
        Raises:
            ValueError: If invoice is not found
        """
        # Get invoice with related data
        invoice = self.session.get(Invoice, invoice_id)
        if not invoice:
            raise ValueError("Invoice not found")
        
        # Get profile and customer
        profile = self.session.get(Profile, invoice.profile_id)
        customer = self.session.get(Customer, invoice.customer_id)
        
        if not profile:
            raise ValueError("Profile not found")
        if not customer:
            raise ValueError("Customer not found")
        
        # Get invoice items
        from models import InvoiceItem
        items_query = select(InvoiceItem).where(InvoiceItem.invoice_id == invoice_id)
        invoice_items = self.session.exec(items_query).all()
        
        # Prepare sender address
        sender_address = self._format_address(profile.address, profile.city)
        
        # Prepare customer address
        customer_address = self._format_address(customer.address, customer.city, customer.name)
        
        # Calculate amounts based on is_gross_amount flag
        total_net, total_tax, total_gross = self._calculate_amounts(
            invoice.total_amount,
            invoice.tax_rate or 0.0,
            invoice.is_gross_amount,
            invoice.include_tax or False
        )
        
        # Prepare items data
        items_data = []
        for item in invoice_items:
            items_data.append({
                "description": item.description,
                "quantity": item.quantity,
                "price": item.price
            })
        
        # Convert string date to date object
        if isinstance(invoice.date, str):
            # Handle both date formats: "YYYY-MM-DD" and ISO format with time
            if "T" in invoice.date:
                invoice_date = datetime.fromisoformat(invoice.date.replace('Z', '+00:00')).date()
            else:
                invoice_date = datetime.strptime(invoice.date, "%Y-%m-%d").date()
        else:
            invoice_date = invoice.date
        
        return PDFInvoiceData(
            invoice_number=invoice.number,
            date=invoice_date,
            sender_name=profile.name,
            sender_address=sender_address,
            customer_name=customer.name,
            customer_address=customer_address,
            total_net=total_net,
            total_tax=total_tax,
            total_gross=total_gross,
            tax_rate=invoice.tax_rate or 0.0,
            items=items_data,
            sender_bank_data=profile.bank_data,
            sender_tax_number=profile.tax_number
        )
    
    def get_summary_invoice_pdf_data(
        self, 
        summary_invoice_id: int, 
        customer_id: int
    ) -> PDFSummaryInvoiceData:
        """
        Retrieve and prepare summary invoice data for PDF generation.
        
        Args:
            summary_invoice_id: ID of the summary invoice
            customer_id: ID of the customer for the PDF (can be different from invoice customers)
            
        Returns:
            PDFSummaryInvoiceData object with all necessary information
            
        Raises:
            ValueError: If summary invoice or customer is not found
        """
        # Get summary invoice
        summary_invoice = self.session.get(SummaryInvoice, summary_invoice_id)
        if not summary_invoice:
            raise ValueError("Summary invoice not found")
        
        # Get profile and customer
        profile = self.session.get(Profile, summary_invoice.profile_id)
        customer = self.session.get(Customer, customer_id)
        
        if not profile:
            raise ValueError("Profile not found")
        if not customer:
            raise ValueError("Customer not found")
        
        # Get linked invoice numbers
        links_query = select(SummaryInvoiceLink).where(
            SummaryInvoiceLink.summary_invoice_id == summary_invoice_id
        )
        links = self.session.exec(links_query).all()
        
        invoice_numbers = []
        for link in links:
            invoice = self.session.get(Invoice, link.invoice_id)
            if invoice:
                invoice_numbers.append(invoice.number)
        
        # Prepare addresses
        sender_address = self._format_address(profile.address, profile.city)
        customer_address = self._format_address(customer.address, customer.city, customer.name)
        
        # Convert string date to date object
        if isinstance(summary_invoice.date, str):
            # Handle both date formats: "YYYY-MM-DD" and ISO format with time
            if "T" in summary_invoice.date:
                summary_date = datetime.fromisoformat(summary_invoice.date.replace('Z', '+00:00')).date()
            else:
                summary_date = datetime.strptime(summary_invoice.date, "%Y-%m-%d").date()
        else:
            summary_date = summary_invoice.date
        
        return PDFSummaryInvoiceData(
            range_text=summary_invoice.range_text,
            date=summary_date,
            sender_name=profile.name,
            sender_address=sender_address,
            customer_name=customer.name,
            customer_address=customer_address,
            total_net=summary_invoice.total_net,
            total_tax=summary_invoice.total_tax,
            total_gross=summary_invoice.total_gross,
            invoice_numbers=invoice_numbers,
            sender_bank_data=profile.bank_data,
            sender_tax_number=profile.tax_number
        )
    
    def _format_address(
        self, 
        address: Optional[str], 
        city: Optional[str], 
        name: Optional[str] = None
    ) -> str:
        """
        Format address components into a multi-line string.
        
        Args:
            address: Street address
            city: City with postal code
            name: Optional name (for customers)
            
        Returns:
            Formatted multi-line address string
        """
        parts = []
        
        if name:
            parts.append(name)
        if address:
            parts.append(address)
        if city:
            parts.append(city)
        
        return "\n".join(parts) if parts else ""
    
    def _calculate_amounts(
        self, 
        total_amount: float, 
        tax_rate: float, 
        is_gross_amount: bool,
        include_tax: bool
    ) -> tuple[float, float, float]:
        """
        Calculate net, tax, and gross amounts based on invoice settings.
        
        Args:
            total_amount: The stored total amount
            tax_rate: Tax rate (e.g., 0.19 for 19%)
            is_gross_amount: Whether total_amount includes tax
            include_tax: Whether tax should be calculated at all
            
        Returns:
            Tuple of (net_amount, tax_amount, gross_amount)
        """
        if not include_tax or tax_rate == 0.0:
            # No tax case (§19 UStG)
            return total_amount, 0.0, total_amount
        
        if is_gross_amount:
            # Total amount includes tax -> calculate net
            gross_amount = total_amount
            net_amount = gross_amount / (1 + tax_rate)
            tax_amount = gross_amount - net_amount
        else:
            # Total amount is net -> calculate gross
            net_amount = total_amount
            tax_amount = net_amount * tax_rate
            gross_amount = net_amount + tax_amount
        
        # Round to 2 decimal places
        return (
            round(net_amount, 2),
            round(tax_amount, 2), 
            round(gross_amount, 2)
        )