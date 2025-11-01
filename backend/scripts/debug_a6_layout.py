#!/usr/bin/env python3
"""
Debug script to show exact positioning calculations for A6 layout.

This utility helps verify that the A6 invoices are properly positioned
on the A4 page with correct margins and spacing.
"""

import os
import sys

from reportlab.lib.pagesizes import A4, A6
from reportlab.lib.units import mm

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.pdf_a6_generator_simple import PDFA6GeneratorSimple


def main():
    """Show positioning calculations"""
    print("📐 A6 PDF Layout Debug Information")
    print("=" * 50)

    # A4 and A6 dimensions
    a4_width_mm = A4[0] / mm
    a4_height_mm = A4[1] / mm
    a6_width_mm = A6[0] / mm
    a6_height_mm = A6[1] / mm

    print(f"A4 Size: {a4_width_mm:.1f} x {a4_height_mm:.1f} mm")
    print(f"A6 Size: {a6_width_mm:.1f} x {a6_height_mm:.1f} mm")
    print()

    # Create generator to get calculated positions
    generator = PDFA6GeneratorSimple()

    # Show margin calculations
    total_content_width_mm = (2 * A6[0]) / mm
    total_content_height_mm = (2 * A6[1]) / mm

    margin_x_mm = generator.page_margin_x / mm
    margin_y_mm = generator.page_margin_y / mm

    print(f"Total content size (2x A6 width): {total_content_width_mm:.1f} mm")
    print(f"Total content size (2x A6 height): {total_content_height_mm:.1f} mm")
    print()
    print(f"Calculated margins:")
    print(f"  Left/Right margin: {margin_x_mm:.1f} mm")
    print(f"  Top/Bottom margin: {margin_y_mm:.1f} mm")
    print()

    # Show positions
    print("Invoice positions (from bottom-left corner in mm):")
    for i, (x, y) in enumerate(generator.positions):
        x_mm = x / mm
        y_mm = y / mm
        position_names = ["Bottom-Left", "Bottom-Right", "Top-Left", "Top-Right"]
        print(f"  Position {i+1} ({position_names[i]}): x={x_mm:.1f}, y={y_mm:.1f}")

    print()
    print("Expected layout:")
    print("┌─────────────────────────────────────────┐")
    print("│              A4 Page                    │")
    print(
        f"│  ┌──────────┐  ┌──────────┐  ← {margin_y_mm + a6_height_mm:.1f}mm from bottom"
    )
    print("│  │  Top-L   │  │  Top-R   │            │")
    print("│  │ Invoice  │  │ Invoice  │            │")
    print("│  │    3     │  │    4     │            │")
    print("│  └──────────┘  └──────────┘            │")
    print(f"│  ┌──────────┐  ┌──────────┐  ← {margin_y_mm:.1f}mm from bottom")
    print("│  │ Bottom-L │  │ Bottom-R │            │")
    print("│  │ Invoice  │  │ Invoice  │            │")
    print("│  │    1     │  │    2     │            │")
    print("│  └──────────┘  └──────────┘            │")
    print("└─────────────────────────────────────────┘")
    print(f"   ↑{margin_x_mm:.1f}mm    ↑{margin_x_mm + a6_width_mm:.1f}mm")
    print()
    print("💡 Use this information to verify PDF layout positioning.")


if __name__ == "__main__":
    main()
