from pypdf import PdfReader

# Extract text page-by-page so downstream analysis can preserve page context.
def load_pdf_pages(file):
    reader = PdfReader(file)
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        pages.append({"page": i, "text": text})
    return pages

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
