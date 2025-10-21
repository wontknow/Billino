"""
Tests for invoice creation model validation scenarios.
Covers edge cases and validation logic that were missing test coverage.
"""

import pytest
from pydantic import ValidationError

from models.invoice_create import InvoiceCreate, InvoiceCreateWithNumber, InvoiceItemCreate


class TestInvoiceCreateValidation:
    """Test validation scenarios for InvoiceCreate model"""
    
    def get_valid_invoice_data(self):
        """Helper to get valid invoice data"""
        return {
            "date": "2025-10-20",
            "customer_id": 1,
            "profile_id": 1,
            "total_amount": 100.0,
            "invoice_items": [
                {"quantity": 1, "description": "Test Item", "price": 100.0}
            ]
        }
    
    def test_valid_invoice_creation(self):
        """Test that valid invoice data creates successfully"""
        data = self.get_valid_invoice_data()
        invoice = InvoiceCreate(**data)
        assert invoice.total_amount == 100.0
        assert len(invoice.invoice_items) == 1
    
    def test_negative_total_amount_validation(self):
        """Test validation fails for negative total amount"""
        data = self.get_valid_invoice_data()
        data["total_amount"] = -50.0
        
        with pytest.raises(ValueError, match="total_amount must be non-negative"):
            InvoiceCreate(**data)
    
    def test_empty_invoice_items_validation(self):
        """Test validation fails for empty invoice items"""
        data = self.get_valid_invoice_data()
        data["invoice_items"] = []
        
        with pytest.raises(ValueError, match="Invoice must have at least one item"):
            InvoiceCreate(**data)
    
    def test_none_invoice_items_validation(self):
        """Test validation fails when invoice_items is None"""
        data = self.get_valid_invoice_data()
        data["invoice_items"] = None
        
        # Pydantic raises ValidationError for type validation, not ValueError
        with pytest.raises(ValidationError, match="Input should be a valid list"):
            InvoiceCreate(**data)
    
    def test_is_gross_amount_without_include_tax_validation(self):
        """Test validation fails when is_gross_amount=True but include_tax=False"""
        data = self.get_valid_invoice_data()
        data["is_gross_amount"] = True
        data["include_tax"] = False
        data["tax_rate"] = 0.19
        
        with pytest.raises(ValueError, match="is_gross_amount can only be True if include_tax is True"):
            InvoiceCreate(**data)
    
    def test_is_gross_amount_without_tax_rate_validation(self):
        """Test validation fails when is_gross_amount=True but tax_rate is None"""
        data = self.get_valid_invoice_data()
        data["is_gross_amount"] = True
        data["include_tax"] = True
        data["tax_rate"] = None
        
        with pytest.raises(ValueError, match="tax_rate must be provided if is_gross_amount is True"):
            InvoiceCreate(**data)
    
    def test_include_tax_false_with_nonzero_tax_rate_validation(self):
        """Test validation fails when include_tax=False but tax_rate is not 0"""
        data = self.get_valid_invoice_data()
        data["include_tax"] = False
        data["tax_rate"] = 0.19
        
        with pytest.raises(ValueError, match="tax_rate must be 0 if include_tax is False"):
            InvoiceCreate(**data)
    
    def test_include_tax_true_without_tax_rate_validation(self):
        """Test validation fails when include_tax=True but tax_rate is None"""
        data = self.get_valid_invoice_data()
        data["include_tax"] = True
        data["tax_rate"] = None
        
        with pytest.raises(ValueError, match="tax_rate must be provided if include_tax is True"):
            InvoiceCreate(**data)
    
    def test_tax_rate_below_zero_validation(self):
        """Test validation fails for negative tax rate"""
        data = self.get_valid_invoice_data()
        data["include_tax"] = True
        data["tax_rate"] = -0.1
        
        with pytest.raises(ValueError, match="tax_rate must be between 0 and 1"):
            InvoiceCreate(**data)
    
    def test_tax_rate_above_one_validation(self):
        """Test validation fails for tax rate above 100%"""
        data = self.get_valid_invoice_data()
        data["include_tax"] = True
        data["tax_rate"] = 1.5
        
        with pytest.raises(ValueError, match="tax_rate must be between 0 and 1"):
            InvoiceCreate(**data)
    
    def test_valid_tax_scenarios(self):
        """Test valid tax configurations"""
        base_data = self.get_valid_invoice_data()
        
        # Valid: include_tax=False, tax_rate=0
        data1 = base_data.copy()
        data1["include_tax"] = False
        data1["tax_rate"] = 0.0
        invoice1 = InvoiceCreate(**data1)
        assert invoice1.include_tax is False
        assert invoice1.tax_rate == 0.0
        
        # Valid: include_tax=False, tax_rate=None
        data2 = base_data.copy()
        data2["include_tax"] = False
        data2["tax_rate"] = None
        invoice2 = InvoiceCreate(**data2)
        assert invoice2.include_tax is False
        assert invoice2.tax_rate is None
        
        # Valid: include_tax=True, tax_rate=0.19
        data3 = base_data.copy()
        data3["include_tax"] = True
        data3["tax_rate"] = 0.19
        invoice3 = InvoiceCreate(**data3)
        assert invoice3.include_tax is True
        assert invoice3.tax_rate == 0.19
        
        # Valid: is_gross_amount=True with proper settings
        data4 = base_data.copy()
        data4["is_gross_amount"] = True
        data4["include_tax"] = True
        data4["tax_rate"] = 0.19
        invoice4 = InvoiceCreate(**data4)
        assert invoice4.is_gross_amount is True


class TestInvoiceCreateWithNumberValidation:
    """Test validation scenarios for InvoiceCreateWithNumber model"""
    
    def get_valid_invoice_with_number_data(self):
        """Helper to get valid invoice data with number"""
        return {
            "number": "25 | 001",
            "date": "2025-10-20",
            "customer_id": 1,
            "profile_id": 1,
            "total_amount": 100.0,
            "invoice_items": [
                {"quantity": 1, "description": "Test Item", "price": 100.0}
            ]
        }
    
    def test_valid_invoice_number_formats(self):
        """Test various valid invoice number formats"""
        base_data = self.get_valid_invoice_with_number_data()
        
        valid_numbers = [
            "25 | 001",
            "24 | 123", 
            "23 | 9999",
            "00 | 000",
            "99 | 100000"
        ]
        
        for number in valid_numbers:
            data = base_data.copy()
            data["number"] = number
            invoice = InvoiceCreateWithNumber(**data)
            assert invoice.number == number
    
    def test_invalid_invoice_number_formats(self):
        """Test various invalid invoice number formats"""
        base_data = self.get_valid_invoice_with_number_data()
        
        invalid_numbers = [
            "25|001",          # Missing spaces
            "25 | 01",         # Too few digits after pipe
            "5 | 001",         # Too few digits before pipe
            "25  | 001",       # Extra space
            "25 |  001",       # Extra space
            "25 || 001",       # Double pipe
            "AB | 001",        # Letters instead of numbers
            "25 | ABC",        # Letters instead of numbers
            "25 - 001",        # Wrong separator
            "25 | 01",         # Less than 3 digits
            "",                # Empty string
            "25001",           # No pipe
        ]
        
        for number in invalid_numbers:
            data = base_data.copy()
            data["number"] = number
            with pytest.raises(ValueError, match="Invoice number must follow format"):
                InvoiceCreateWithNumber(**data)
    
    def test_invoice_with_number_inherits_validation(self):
        """Test that InvoiceCreateWithNumber inherits all validation from base"""
        data = self.get_valid_invoice_with_number_data()
        data["total_amount"] = -50.0
        
        with pytest.raises(ValueError, match="total_amount must be non-negative"):
            InvoiceCreateWithNumber(**data)


class TestInvoiceItemCreateValidation:
    """Test validation scenarios for InvoiceItemCreate model"""
    
    def test_valid_invoice_item_creation(self):
        """Test creating valid invoice item"""
        item = InvoiceItemCreate(
            quantity=2,
            description="Test Item", 
            price=50.0,
            tax_rate=0.19
        )
        assert item.quantity == 2
        assert item.description == "Test Item"
        assert item.price == 50.0
        assert item.tax_rate == 0.19
    
    def test_invoice_item_optional_tax_rate(self):
        """Test invoice item with optional tax_rate"""
        item = InvoiceItemCreate(
            quantity=1,
            description="Test Item",
            price=100.0
        )
        assert item.tax_rate is None
    
    def test_invoice_item_required_fields(self):
        """Test that required fields are enforced"""
        with pytest.raises(ValidationError):
            InvoiceItemCreate()  # Missing all required fields
        
        with pytest.raises(ValidationError):
            InvoiceItemCreate(quantity=1)  # Missing description and price
        
        with pytest.raises(ValidationError):
            InvoiceItemCreate(
                quantity=1, 
                description="Test"
            )  # Missing price
    
    def test_invoice_item_field_types(self):
        """Test field type validation"""
        # quantity should be int
        with pytest.raises(ValidationError):
            InvoiceItemCreate(
                quantity="not_an_int",
                description="Test", 
                price=100.0
            )
        
        # price should be float/numeric
        with pytest.raises(ValidationError):
            InvoiceItemCreate(
                quantity=1,
                description="Test",
                price="not_a_number"
            )
        
        # description should be string
        with pytest.raises(ValidationError):
            InvoiceItemCreate(
                quantity=1,
                description=123,  # Should be string
                price=100.0
            )