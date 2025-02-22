import os
import subprocess

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