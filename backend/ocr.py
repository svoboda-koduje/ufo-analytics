import fitz  # PyMuPDF

def extract_text_from_pdf(pdf_path: str):
    """
    Otevře PDF a extrahuje z něj text.
    """
    try:
        doc = fitz.open(pdf_path)
        full_text = ""
        for page in doc:
            full_text += page.get_text()
        return full_text
    except Exception as e:
        return f"Chyba při zpracování PDF: {str(e)}"