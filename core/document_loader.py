from pypdf import PdfReader
from xml.etree import ElementTree
from zipfile import ZipFile
from functools import lru_cache


def _chunk_text_blocks(blocks, max_chars: int = 3500):
    pages = []
    current = []
    current_len = 0
    page_num = 1

    for block in blocks:
        text = (block or "").strip()
        if not text:
            continue
        projected = current_len + len(text) + (2 if current else 0)
        if current and projected > max_chars:
            pages.append({"page": page_num, "text": "\n\n".join(current)})
            page_num += 1
            current = [text]
            current_len = len(text)
        else:
            current.append(text)
            current_len = projected

    if current:
        pages.append({"page": page_num, "text": "\n\n".join(current)})
    return pages


# Extract text page-by-page so downstream analysis can preserve page context.
@lru_cache(maxsize=24)
def _load_pdf_pages_from_bytes(file_bytes: bytes):
    from io import BytesIO

    reader = PdfReader(BytesIO(file_bytes))
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        pages.append({"page": i, "text": text})
    return tuple((page["page"], page["text"]) for page in pages)


def load_pdf_pages(file):
    file.seek(0)
    file_bytes = file.read()
    cached_pages = _load_pdf_pages_from_bytes(file_bytes)
    return [{"page": page_num, "text": text} for page_num, text in cached_pages]


@lru_cache(maxsize=24)
def _load_docx_pages_from_bytes(file_bytes: bytes):
    from io import BytesIO

    blocks = []
    with ZipFile(BytesIO(file_bytes)) as archive:
        xml_bytes = archive.read("word/document.xml")

    root = ElementTree.fromstring(xml_bytes)
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

    for paragraph in root.findall(".//w:p", namespace):
        runs = [node.text for node in paragraph.findall(".//w:t", namespace) if node.text]
        text = "".join(runs).strip()
        if text:
            blocks.append(text)

    # Basic table extraction keeps row content analyzable even without python-docx.
    for table in root.findall(".//w:tbl", namespace):
        for row in table.findall(".//w:tr", namespace):
            cells = []
            for cell in row.findall(".//w:tc", namespace):
                parts = [node.text for node in cell.findall(".//w:t", namespace) if node.text]
                cell_text = "".join(parts).strip()
                if cell_text:
                    cells.append(cell_text)
            if cells:
                blocks.append(" | ".join(cells))

    pages = _chunk_text_blocks(blocks)
    if not pages:
        pages = [{"page": 1, "text": ""}]
    return tuple((page["page"], page["text"]) for page in pages)


def load_docx_pages(file):
    file.seek(0)
    file_bytes = file.read()
    cached_pages = _load_docx_pages_from_bytes(file_bytes)
    return [{"page": page_num, "text": text} for page_num, text in cached_pages]

# Keep legacy callers working by returning one concatenated text string.
def load_pdf(file):
    # Backwards-compatible: returns all pages concatenated
    pages = load_pdf_pages(file)
    return "".join(p["text"] for p in pages)


# Join extracted page text into one analyzable contract body.
def parse_contract_text(pages):
    return "\n".join(p.get("text", "") for p in pages if p.get("text"))


# Split long contracts into overlapping chunks to improve retrieval quality.
def chunk_contract_text(text: str, chunk_size: int = 1200, chunk_overlap: int = 150):
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        chunks = splitter.split_text(text or "")
    except Exception:
        chunks = []
        source = text or ""
        start = 0
        while start < len(source):
            end = min(start + chunk_size, len(source))
            chunks.append(source[start:end])
            if end == len(source):
                break
            start = max(0, end - chunk_overlap)

    return [c.strip() for c in chunks if c and c.strip()]
