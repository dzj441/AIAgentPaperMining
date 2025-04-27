# parser.py

import re
import fitz  # PyMuPDF

def extract_text_and_links(pdf_bytes: bytes) -> tuple:
    """Extract full text and all external URLs from a PDF."""
    text = []
    links = []
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    for page in doc:
        text.append(page.get_text())
        for link in page.get_links():
            uri = link.get('uri')
            if uri:
                links.append(uri)
    doc.close()
    full_text = "\n".join(text)

    # regex find extra URLs
    extra_urls = re.findall(r'(?:http[s]?://|www\.)\S+', full_text)
    for url in extra_urls:
        url = url.rstrip('；。；，,."]')
        links.append(url)

    # dedupe preserving order
    seen = set()
    unique = []
    for url in links:
        if url not in seen:
            seen.add(url)
            unique.append(url)
    return full_text, unique
