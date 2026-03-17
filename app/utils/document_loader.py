
from PyPDF2 import PdfReader
from docx import Document
import os
import re


CHUNK_SIZE = 800
CHUNK_OVERLAP = 150


def extract_text_from_pdf(file_path: str):
    reader = PdfReader(file_path)
    text = ""

    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"

    return text


def extract_text_from_docx(file_path: str):
    doc = Document(file_path)
    text = ""

    for para in doc.paragraphs:
        if para.text.strip():
            text += para.text + "\n"

    return text


def extract_text_from_txt(file_path: str):
    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()


def clean_text(text: str):
    # Remove excessive whitespace
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def chunk_text(text: str):
    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + CHUNK_SIZE
        chunk = text[start:end]
        chunks.append(chunk)
        start += CHUNK_SIZE - CHUNK_OVERLAP

    return chunks


def load_document(file_path: str):
    _, extension = os.path.splitext(file_path)

    if extension.lower() == ".pdf":
        text = extract_text_from_pdf(file_path)

    elif extension.lower() == ".docx":
        text = extract_text_from_docx(file_path)

    elif extension.lower() == ".txt":
        text = extract_text_from_txt(file_path)

    else:
        raise ValueError("Unsupported file format")

    cleaned_text = clean_text(text)

    chunks = chunk_text(cleaned_text)

    return chunks