import os
import pytest
from src.converter import PDFToWordConverter, PDFConversionError
from local_test import generate_sample_pdf

@pytest.fixture
def sample_pdf(tmp_path):
    pdf_path = str(tmp_path / "test.pdf")
    generate_sample_pdf(pdf_path)
    return pdf_path

def test_convert_file(sample_pdf, tmp_path):
    output_docx = str(tmp_path / "test.docx")
    result = PDFToWordConverter.convert(sample_pdf, output_docx)
    
    assert os.path.exists(result)
    assert os.path.getsize(result) > 0

def test_convert_nonexistent_file(tmp_path):
    fake_path = str(tmp_path / "does_not_exist.pdf")
    output_docx = str(tmp_path / "output.docx")
    
    with pytest.raises(FileNotFoundError):
        PDFToWordConverter.convert(fake_path, output_docx)

def test_convert_bytes(sample_pdf, tmp_path):
    with open(sample_pdf, "rb") as f:
        pdf_bytes = f.read()

    temp_docx, docx_bytes = PDFToWordConverter.convert_bytes(pdf_bytes, temp_dir=str(tmp_path))
    assert len(docx_bytes) > 0
