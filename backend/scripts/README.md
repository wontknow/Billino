# Scripts Directory

This directory contains utility scripts and demo tools for the Billino backend.

## 📁 Files

### 🔧 Utility Scripts

- **`debug_a6_layout.py`** - Debug tool for A6 PDF layout positioning
  - Shows margin calculations and invoice positions
  - Displays ASCII art layout diagram
  - Useful for verifying layout correctness

### 🎯 Demo Scripts

- **`demo_a6_generator.py`** - Demo of A6 PDF generation
  - Creates a sample PDF with 4 realistic invoices
  - Shows the A6 layout functionality in action
  - Good for testing and presentation purposes

### ⚖️ Comparison Scripts

- **`compare_a6_generators.py`** - Compare both A6 PDF generators
  - Tests Original (Frame-based) vs Simple (Canvas-based) generators
  - Shows file size differences and performance
  - Generates comparison PDFs

### 📄 PDF Generation Demos

- **`demo_pdf_generation.py`** - Demo of standard PDF generation
  - Creates sample individual and summary invoices
  - Showcases professional design and typography
  - Uses realistic mock data for testing

## ✨ Professional PDF Design

All generated PDFs feature a **professional, minimalist design**:

### 🎨 Design Features
- **Elegant Color Palette**: Dark charcoal headers, medium gray labels, subtle accents
- **Professional Typography**: Helvetica family with hierarchical sizing (24pt titles, 12pt headers, 10pt text)
- **Modern Layout**: 25mm margins, structured sections, elegant separator lines
- **Enhanced Tables**: Dark headers with white text, subtle borders, right-aligned amounts

### 📐 Layout Structure  
- **Generous Margins**: Professional 25mm spacing on all sides
- **Clear Sections**: Well-separated areas for addresses, items, and totals
- **Subtle Separators**: HRFlowable elements for elegant section breaks
- **Balanced Spacing**: Optimized distances between all elements

## 🚀 Usage

Run any script from the backend root directory:

```bash
# Debug layout calculations
python scripts/debug_a6_layout.py

# Generate A6 demo PDF
python scripts/demo_a6_generator.py

# Generate standard PDF demos  
python scripts/demo_pdf_generation.py

# Compare both generators
python scripts/compare_a6_generators.py
```

## 📄 Generated Files

Scripts will create PDF files in the `scripts/` directory:

**A6 Layout PDFs:**
- `A6_Demo_4_Invoices.pdf` - A6 layout demo (4 invoices on A4)
- `Comparison_Original_A6.pdf` - Original A6 generator output  
- `Comparison_Simple_A6.pdf` - Simple A6 generator output

**Standard PDFs:**
- `Demo_Individual_Invoice.pdf` - Individual invoice sample
- `Demo_Summary_Invoice.pdf` - Summary invoice sample

## 🧪 Testing

For unit tests, see the `tests/` directory:
- `tests/test_pdf_a6_generator.py` - Comprehensive unit tests for A6 PDF generation