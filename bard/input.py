import os
import subprocess
import requests
from bard.util import logger, CACHE_DIR


def pdftotext(pdf_path, text_path):
    # Call pdftotext using subprocess
    result = subprocess.run(
        ["pdftotext", pdf_path, text_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    # Check for errors
    if result.returncode != 0:
        print(f"Error: {result.stderr.decode('utf-8')}")
    else:
        print("Text extracted successfully.")


def read_text_from_pdf(pdf_path):
    # Create a temporary file to store the extracted text
    text_path = os.path.join(CACHE_DIR, os.path.basename(pdf_path) + ".txt")

    # Extract text from the PDF
    pdftotext(pdf_path, text_path)

    # Read the extracted text
    with open(text_path, "r") as file:
        text = file.read()

    # Clean up the temporary file
    os.remove(text_path)

    return text

def extract_text_from_filepath(filepath):
    _, ext = os.path.splitext(filepath)
    if ext == ".pdf":
        return read_text_from_pdf(filepath)
    elif ext in (".html", ".htm", ".xhtml"):
        from bard.html import extract_text_from_html
        return extract_text_from_html(open(filepath).read())
    else:
        return open(filepath).read()

def extract_text_from_url(url):
    try:
        response = requests.get(url)
    except requests.exceptions.MissingSchema:
        url = "https://" + url
        response = requests.get(url)
    except requests.exceptions.InvalidSchema:
        if url.startswith("file://"):
            return extract_text_from_filepath(url[7:])

    from bard.html import extract_text_from_html
    return extract_text_from_html(response.content)

def preprocess_input_text(text):
    """Check for text containers such as URL or file paths and extract the relevant text from it
    """
    text = text.strip()

    # URLs
    if text.startswith(("https://", "http://", "file://")):
        url = text
        logger.info(f'Fetch text from {url}')
        from bard.html import extract_text_from_url
        return extract_text_from_url(url)

    # file paths
    elif len(text) < 1024 and (text.startswith(os.path.sep) or ":\\" in text) and os.path.exists(text):
        return extract_text_from_filepath(text)

    return text