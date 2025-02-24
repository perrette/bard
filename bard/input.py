import os
import subprocess
import requests
import pyperclip
from bard.util import logger, CACHE_DIR, is_running_in_termux

def get_text_from_clipboard():
    if is_running_in_termux():
        clipboard = subprocess.check_output(["termux-clipboard-get"]).decode("utf-8")
    else:
        clipboard = pyperclip.paste()
    return clipboard

def set_text_to_clipboard(text):
    if is_running_in_termux():
        subprocess.check_call(["termux-clipboard-set", text])
    else:
        pyperclip.copy(text)

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
    from bard.html import extract_text_from_html

    try:
        response = requests.get(url)

    except requests.exceptions.MissingSchema:
        url = "https://" + url
        response = requests.get(url)

    except requests.exceptions.InvalidSchema:
        if url.startswith("file://"):
            from urllib.request import url2pathname
            filepath = url2pathname(url[7:])
            return extract_text_from_filepath(filepath)

    content_type = response.headers.get('content-type')

    if content_type and 'application/pdf' in content_type:
        tmpfile = os.path.join(CACHE_DIR, "pdfs", os.path.basename(url))
        os.makedirs(os.path.dirname(tmpfile), exist_ok=True)
        with open(tmpfile, "wb") as f:
            f.write(response.content)
        pdf = read_text_from_pdf(tmpfile)
        os.remove(tmpfile)
        return pdf

    return extract_text_from_html(response.content)

def preprocess_input_text(text):
    """Check for text containers such as URL or file paths and extract the relevant text from it
    """
    text = text.strip()

    # URLs
    if text.startswith(("https://", "http://", "file://")):
        url = text
        logger.info(f'Fetch text from {url}')
        return extract_text_from_url(url)

    # file paths
    elif len(text) < 1024 and (text.startswith(os.path.sep) or ":\\" in text) and os.path.exists(text):
        return extract_text_from_filepath(text)

    # HTML content
    elif text[:20].lower().startswith(("<html", "<!doctype html", "<body", "<p")) and text.endswith(("</p>", "</html>", "</body>")):
        from bard.html import extract_text_from_html
        return extract_text_from_html(text)

    return text