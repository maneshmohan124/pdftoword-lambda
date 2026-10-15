import os
import io
import logging
from typing import Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

class PDFConversionError(Exception):
    """Raised when PDF conversion fails."""
    pass

class PDFToWordConverter:
    """
    Handles PDF to Word (.docx) conversion.
    Prefers `pdf2docx` for high-fidelity formatting, tables, and layouts.
    Provides fallback to `pypdf` + `python-docx` for lightweight text extraction
    if pdf2docx encounters issues or is unavailable.
    """

    @staticmethod
    def convert(input_pdf_path: str, output_docx_path: str) -> str:
        """
        Convert a local PDF file to DOCX.
        
        :param input_pdf_path: Path to the input PDF file.
        :param output_docx_path: Path to save the converted DOCX file.
        :return: Path to the generated DOCX file.
        """
        if not os.path.exists(input_pdf_path):
            raise FileNotFoundError(f"Input PDF does not exist: {input_pdf_path}")

        # Ensure parent directory for output exists
        os.makedirs(os.path.dirname(os.path.abspath(output_docx_path)), exist_ok=True)

        logger.info(f"Starting conversion: {input_pdf_path} -> {output_docx_path}")

        # Try high-fidelity conversion using pdf2docx first
        try:
            from pdf2docx import Converter
            logger.info("Using pdf2docx engine for high-fidelity conversion.")
            cv = Converter(input_pdf_path)
            cv.convert(output_docx_path)
            cv.close()
            logger.info(f"Successfully converted using pdf2docx: {output_docx_path}")
            return output_docx_path
        except Exception as e:
            logger.warning(f"pdf2docx conversion failed or not available ({e}). Attempting fallback engine.")

        # Fallback engine: pypdf + docx
        try:
            from pypdf import PdfReader
            from docx import Document
            
            logger.info("Using pypdf + python-docx fallback engine.")
            reader = PdfReader(input_pdf_path)
            doc = Document()
            
            total_pages = len(reader.pages)
            for idx, page in enumerate(reader.pages):
                text = page.extract_text()
                if text:
                    for line in text.splitlines():
                        if line.strip():
                            doc.add_paragraph(line)
                if idx < total_pages - 1:
                    doc.add_page_break()
                    
            doc.save(output_docx_path)
            logger.info(f"Successfully converted using fallback engine: {output_docx_path}")
            return output_docx_path
        except Exception as fallback_err:
            logger.error(f"Fallback conversion also failed: {fallback_err}")
            raise PDFConversionError(f"All conversion engines failed: {fallback_err}") from fallback_err

    @staticmethod
    def convert_bytes(pdf_bytes: bytes, temp_dir: str = "/tmp") -> Tuple[str, bytes]:
        """
        Convert in-memory PDF bytes to Word document bytes.
        
        :param pdf_bytes: Raw bytes of the PDF.
        :param temp_dir: Directory to use for temporary file storage (default /tmp for Lambda).
        :return: Tuple of (temp_docx_path, docx_bytes)
        """
        import uuid
        job_id = str(uuid.uuid4())
        temp_pdf = os.path.join(temp_dir, f"{job_id}_input.pdf")
        temp_docx = os.path.join(temp_dir, f"{job_id}_output.docx")

        try:
            with open(temp_pdf, "wb") as f:
                f.write(pdf_bytes)

            PDFToWordConverter.convert(temp_pdf, temp_docx)

            with open(temp_docx, "rb") as f:
                docx_bytes = f.read()

            return temp_docx, docx_bytes
        finally:
            # Clean up temp input pdf
            if os.path.exists(temp_pdf):
                try:
                    os.remove(temp_pdf)
                except OSError:
                    pass
