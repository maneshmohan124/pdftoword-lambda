#!/usr/bin/env python3
"""
Local test runner for PDF to Word conversion.
Usage:
    python local_test.py
    python local_test.py --pdf path/to/document.pdf
"""

import os
import sys
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.converter import PDFToWordConverter


def generate_sample_pdf(output_path: str) -> str:
    """Generate a clean sample PDF using pypdf or reportlab or minimal PDF bytes."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet

        doc = SimpleDocTemplate(output_path, pagesize=letter)
        styles = getSampleStyleSheet()
        story = [
            Paragraph("AWS Lambda PDF to Word Converter Test Document", styles['Heading1']),
            Spacer(1, 12),
            Paragraph("This is a sample PDF generated to verify PDF to Word (.docx) conversion.", styles['BodyText']),
            Spacer(1, 12),
            Paragraph("Features:", styles['Heading2']),
            Paragraph("• Python 3.14 AWS Lambda compatibility", styles['BodyText']),
            Paragraph("• Automatic S3 event trigger support", styles['BodyText']),
            Paragraph("• High-fidelity DOCX document generation", styles['BodyText']),
            Spacer(1, 12),
            Paragraph("Automated deployment configured via GitHub Actions.", styles['Italic'])
        ]
        doc.build(story)
        print(f"Generated sample PDF via ReportLab: {output_path}")
        return output_path
    except ImportError:
        # Minimal valid PDF file fallback
        minimal_pdf = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj
3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>/Contents 4 0 R>>endobj
4 0 obj<</Length 51>>stream
BT
/F1 18 Tf
100 700 Td
(Hello from Python 3.14 AWS Lambda Converter!) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000052 00000 n 
0000000101 00000 n 
0000000213 00000 n 
trailer<</Size 5/Root 1 0 R>>
startxref
314
%%EOF"""
        with open(output_path, "wb") as f:
            f.write(minimal_pdf)
        print(f"Generated minimal valid PDF fallback: {output_path}")
        return output_path


def main():
    parser = argparse.ArgumentParser(description="Test PDF to Word (.docx) conversion locally.")
    parser.add_argument("--pdf", type=str, help="Path to input PDF file (generates a test PDF if omitted)")
    parser.add_argument("--out", type=str, help="Path to output DOCX file (defaults to ./output_converted.docx)")
    args = parser.parse_args()

    input_pdf = args.pdf
    if not input_pdf:
        test_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_artifacts")
        os.makedirs(test_dir, exist_ok=True)
        input_pdf = os.path.join(test_dir, "sample_input.pdf")
        generate_sample_pdf(input_pdf)

    output_docx = args.out or os.path.splitext(input_pdf)[0] + ".docx"

    print(f"\n--- Testing PDF to DOCX Conversion ---")
    print(f"Input:  {input_pdf}")
    print(f"Output: {output_docx}")

    try:
        result_path = PDFToWordConverter.convert(input_pdf, output_docx)
        print(f"\nSUCCESS! Converted file saved to: {result_path}")
        print(f"File size: {os.path.getsize(result_path)} bytes")
    except Exception as e:
        print(f"\nERROR during conversion: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
